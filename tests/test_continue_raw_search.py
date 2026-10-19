"""Controlled continuation tests: no C, probe, resource sampling or search observations."""
import copy
import hashlib
import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch

from scripts import continue_raw_search as r
from scripts.start_raw_comparison import claim
from autotuner.core import Config,ConfigSpace
from autotuner.raw_comparison import strategy_for,prefixes


class ManualSearchContinuationTests(unittest.TestCase):
    def fixture(self):
        own=lambda n,k:dict(observations=[{'config':i} for i in range(n)],retests=list(range(k)))
        plan=dict(content_commit=r.CONTENT,session_id=r.SESSION,mode='search',comparison_protocol_hash='protocol')
        state=dict(session_id=r.SESSION,mode='search',status='stopped',target_executions=98,
            active=dict(attempt_id=r.OLD_ATTEMPT,job=copy.deepcopy(r.JOB),saved_samples=2,formal_comparable=False),
            trajectories={'random':own(12,2),'greedy':own(2,0)})
        records=[dict(run_id=str(i),attempt_id='old',classification='success') for i in range(98)]
        records[-2].update(attempt_id=r.OLD_ATTEMPT)
        records[-1].update(attempt_id=r.OLD_ATTEMPT,classification='timeout')
        old=dict(content_commit=r.CONTENT,session_id=r.SESSION,status='stopped',budget_seconds=43200,
            activity_qpc_seconds=r.USED,qpc_start=135832887190,qpc_end=294248766358,qpc_frequency=10000000)
        return plan,state,records,old

    def test_exact_existing_state_and_remaining_budget(self):
        self.assertEqual(r.check_start(*self.fixture()),27358.4120832)

    def test_source_session_mode_wrong_rejected(self):
        for key,value in (('content_commit','0'*40),('session_id','foreign'),('mode','validation')):
            plan,state,records,old=self.fixture();plan[key]=value
            with self.assertRaises(ValueError):r.check_start(plan,state,records,old)

    def test_partial_record_identity_or_completed_groups_changed_rejected(self):
        for change in ('count','duplicate','pair','random'):
            plan,state,records,old=self.fixture()
            if change=='count':records.pop()
            if change=='duplicate':records[-1]['run_id']=records[0]['run_id']
            if change=='pair':records[-1]['classification']='success'
            if change=='random':state['trajectories']['random']['observations'].pop()
            with self.assertRaises(ValueError):r.check_start(plan,state,records,old)

    def test_original_used_time_cannot_be_reset(self):
        plan,state,records,old=self.fixture();old.update(qpc_end=old['qpc_start'],activity_qpc_seconds=0)
        with self.assertRaises(ValueError):r.check_start(plan,state,records,old)

    def test_different_epoch_durations_are_summed_not_subtracted(self):
        window=dict(qpc_start=10,qpc_end=1000000010,qpc_frequency=10000000,budget_seconds=r.REMAINING)
        self.assertEqual(r.cumulative(window),r.USED+100)
        window['budget_seconds']=43200
        with self.assertRaises(ValueError):r.cumulative(window)
        window['budget_seconds']=r.REMAINING;window['qpc_end']=10+int((r.REMAINING+1)*10000000)
        with self.assertRaises(ValueError):r.cumulative(window)
        window['qpc_frequency']=True
        with self.assertRaises(ValueError):r.cumulative(window)

    def test_old_samples_only_append(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'samples';original=b'{"run_id":"old"}\r\n';path.write_bytes(original+b'new\n')
            r.check_prefix(path,len(original),hashlib.sha256(original).hexdigest())
            path.write_bytes(b'!'+path.read_bytes()[1:])
            with self.assertRaises(ValueError):r.check_prefix(path,len(original),hashlib.sha256(original).hexdigest())

    def test_abandon_pair_without_altering_original_state_or_random(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp)/'authorization.json').write_text('{}')
            plan,state,records,old=self.fixture();before=copy.deepcopy(state)
            auth=dict(directory=tmp,old_partial_run_ids=['96','97'])
            resumed=r.reactivate(state,auth)
            self.assertEqual(state,before)
            self.assertEqual(resumed['trajectories'],state['trajectories'])
            self.assertIsNone(resumed['active']);self.assertEqual(resumed['status'],'ready')
            self.assertEqual(resumed['manual_resume']['abandoned_attempt'],state['active'])
            self.assertEqual(resumed['manual_resume']['abandoned_run_ids'],['96','97'])

    def test_repeated_claim_never_resets_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/r.CLAIM;value=dict(qpc_start=123,budget_seconds=r.REMAINING)
            claim(path,value)
            with self.assertRaises(FileExistsError):claim(path,dict(qpc_start=999,budget_seconds=43200))
            self.assertEqual(json.loads(path.read_bytes()),value)

    def controlled_run(self,mode):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);session=root/'session';session.mkdir();output=root/'continuation';output.mkdir()
            plan,state,records,old=self.fixture()
            write=lambda path,value:Path(path).write_text(json.dumps(value))
            write(root/'plan.json',plan);write(session/'checkpoint.json',state);write(session/'window.json',old)
            (session/'samples.jsonl').write_text('\n'.join(json.dumps(x) for x in records))
            auth=dict(directory=str(output),session_directory=str(session),plan_file=str(root/'plan.json'),checkpoint_sha256='checkpoint')
            authorization_path=output/'authorization.json'
            write(authorization_path,auth);original=(session/'checkpoint.json').read_bytes();released=[]
            class Sleep:
                def __init__(self,path):pass
                def __enter__(self):return self
                def __exit__(self,*args):released.append(True)
            ticks=iter(range(100,1000,10))
            fake=SimpleNamespace(qpc=lambda:(next(ticks),10),claim=claim,atomic_write_json=write,
                utc_now=lambda:'controlled',SleepRequest=Sleep,PowerEvents=lambda path:SimpleNamespace(read=lambda:{}),
                check_volume=Mock(),capture=Mock(return_value=dict(returncode=0,timed_out=False)),
                gate=Mock(return_value=mode!='gate'),clock_check=Mock(),measure=Mock())
            if mode=='clock':fake.clock_check.side_effect=ValueError('controlled fresh RAW rejection')
            if mode=='disk':fake.check_volume.side_effect=OSError('controlled evidence-volume failure')
            with patch.object(r,'verify_auth'),patch.object(r,'verify_preserved',return_value=state),patch.object(r,'frozen',return_value=(fake,SimpleNamespace(require_certificate=Mock()))):
                self.assertEqual(r.run(authorization_path),2)
                window=json.loads((output/'window.json').read_bytes())
                self.assertEqual(window['budget_seconds'],r.REMAINING)
                self.assertEqual(window['cumulative_activity_qpc_seconds'],r.USED+window['activity_qpc_seconds'])
                self.assertEqual(window['status'],'stopped')
                self.assertIn({'gate':'Formal preflight','clock':'controlled fresh RAW rejection','disk':'controlled evidence-volume failure'}[mode],window['failure_reason'])
                fake.measure.assert_not_called()
                if mode in ('gate','disk'):fake.clock_check.assert_not_called()
                self.assertEqual((session/'checkpoint.json').read_bytes(),original)
                self.assertTrue(released)
                saved=(output/'window.json').read_bytes()
                with self.assertRaises(FileExistsError):r.run(authorization_path)
                self.assertEqual((output/'window.json').read_bytes(),saved)

    def test_formal_rejection_no_clock_target_or_checkpoint_mutation(self):self.controlled_run('gate')
    def test_fresh_clock_rejection_no_target_and_sleep_release(self):self.controlled_run('clock')
    def test_evidence_disk_failure_no_target_and_claim_not_reset(self):self.controlled_run('disk')

    def test_invalid_authorization_rejected_before_frozen_executor(self):
        with patch.object(r,'read',return_value={}),patch.object(r,'frozen') as executor:
            with self.assertRaises(KeyError):r.run(Path('invalid.json'))
            executor.assert_not_called()

    def audited_fixture(self,change=None):
        # Real strategy order with controlled scores, fake group verifiers; no target/probe calls.
        print('CONTROLLED FIXTURE ONLY: no real target, clock or resource execution')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);session=root/'session';session.mkdir();out=root/'continuation';out.mkdir()
            for name in ('runs','configurations','group_checks'):(session/name).mkdir()
            project=Path(__file__).resolve().parents[1]
            space=ConfigSpace.load(project/'configs/config_space.json');all_rows=[];own={}
            write=lambda path,value:Path(path).write_text(json.dumps(value))
            def group(algorithm,kind,config,index):
                attempt=algorithm+'_'+kind+'_'+str(index);samples=[]
                for i in range(6):
                    run_id=attempt+'_'+str(i);run_dir=session/'runs'/run_id;run_dir.mkdir()
                    sample=dict(run_id=run_id,attempt_id=attempt,run_directory=str(run_dir),source='fresh_measurement',
                        context=dict(force_remeasure=True),raw_stdout='{}',raw_stderr='')
                    write(run_dir/'result.json',sample);(run_dir/'stdout.txt').write_text('{}');(run_dir/'stderr.txt').write_text('')
                    samples.append(sample)
                config=asdict(config);score=1/(space.all().index(Config(**config))+1)
                value=dict(attempt_id=attempt,config=config,classification='success',score_seconds=score,evaluation_wall_seconds=6,samples=samples)
                path=session/'configurations'/(kind+'_'+attempt+'.json');write(path,value)
                return {**value,'checks_directory':str(session/'group_checks'/attempt),'measured_group_sha256':r.digest(path)}
            for algorithm in ('random','greedy'):
                strategy=strategy_for(space,algorithm);observations=[]
                for index in range(12):
                    config=strategy.ask();value=group(algorithm,'search',config,index);observations.append(value)
                    strategy.tell(config,dict(classification='success',score_seconds=value['score_seconds']))
                p=prefixes(space,algorithm,observations);retests=[]
                for row in p:
                    if row['best_config'] not in [g['config'] for g in retests]:
                        retests.append(group(algorithm,'retest',Config(**row['best_config']),len(retests)))
                own[algorithm]=dict(observations=observations,retests=retests,prefixes=p,
                    prefix_retest_mapping=[dict(row,retest_attempt=next(g['attempt_id'] for g in retests if g['config']==row['best_config'])) for row in p])
                all_rows.extend(s for g in observations+retests for s in g['samples'])
            abandoned=[]
            for index in range(2):
                run_id='abandoned_'+str(index);run_dir=session/'runs'/run_id;run_dir.mkdir()
                sample=dict(run_id=run_id,attempt_id=r.OLD_ATTEMPT,run_directory=str(run_dir),source='fresh_measurement',
                    context=dict(force_remeasure=True),raw_stdout='',raw_stderr='')
                write(run_dir/'result.json',sample);(run_dir/'stdout.txt').write_text('');(run_dir/'stderr.txt').write_text('');abandoned.append(sample)
            all_rows[96:96]=abandoned
            (session/'samples.jsonl').write_text('\n'.join(json.dumps(x) for x in all_rows))
            write(session/'configurations'/('search_'+r.OLD_ATTEMPT+'.json'),dict(classification='failed'))
            state=dict(status='complete',active=None,target_executions=len(all_rows),trajectories=own,manual_resume=dict(accepted_abandonment=True),reference_generation_calls=0)
            write(out/'abandoned_attempt.json',state['manual_resume'])
            window=dict(content_commit=r.CONTENT,session_id=r.SESSION,qpc_start=10,qpc_end=100000010,qpc_frequency=10000000,
                budget_seconds=r.REMAINING,activity_qpc_seconds=10,cumulative_activity_qpc_seconds=r.USED+10,status='complete',budget_pass=True,failure_reason=None)
            plan=dict(content_commit=r.CONTENT,session_id=r.SESSION,comparison_protocol_hash='protocol')
            write(root/'plan.json',plan)
            auth=dict(directory=str(out),session_directory=str(session),plan_file=str(root/'plan.json'),
                checkpoint_sha256='old-checkpoint',old_partial_run_ids=[s['run_id'] for s in abandoned])
            auth_path=out/'authorization.json';write(auth_path,auth);window['authorization_sha256']=r.digest(auth_path)
            write(out/'window.json',window);write(session/r.CLAIM,window)
            write(out/'sleep_request.json',dict(acquired=True,released=True,thread_id=1,release_thread_id=1))
            (out/'admission_resources').mkdir();write(out/'admission_resources/gate_outcome.json',{})
            (out/'admission').mkdir();write(out/'admission/native_process.json',{})
            write(out/'cache.stdout.json',dict(verified=True,setup_invoked=False,reference_generation_calls=0))
            if change=='retest':state['trajectories']['greedy']['retests'].clear()
            if change=='extra':
                sample=copy.deepcopy(all_rows[-1]);sample['run_id']='extra';all_rows.append(sample)
                (session/'samples.jsonl').write_text('\n'.join(json.dumps(x) for x in all_rows));state['target_executions']+=1
            if change=='prefix':state['trajectories']['greedy']['prefixes'].pop()
            fake=SimpleNamespace(ROOT=project,ConfigSpace=ConfigSpace,local_path=Path,
                audit_clock=Mock(return_value=dict(clock_complete=True,evidence_integrity_pass=True,raw_reference_pass=True,errors=[])),atomic_write_json=write)
            contract=SimpleNamespace(require_certificate=Mock(),audit_volume=Mock(),audit_gate=Mock(return_value=True),
                replay=Mock(),prefixes=prefixes,verify_group=Mock(),
                checked_operation=Mock(return_value=dict(stdout_path='cache.stdout.json',returncode=0,timed_out=False)))
            with patch.object(r,'verify_auth'),patch.object(r,'verify_preserved',return_value=state),patch.object(r,'frozen',return_value=(fake,contract)):
                rc=r.audit(auth_path)
            result=json.loads((out/'independent_continuation_audit.json').read_bytes())
            return rc,result

    def test_complete_audit_accounts_for_two_old_abandoned_records(self):
        code,result=self.audited_fixture()
        self.assertEqual(code,0);self.assertTrue(result['comparison_ready'])
        self.assertEqual(result['target_executions'],146+6*result['retest_groups'])
        self.assertEqual(result['accepted_target_samples'],144+6*result['retest_groups'])
        self.assertEqual(result['abandoned_target_samples'],2)
        self.assertFalse(result['five_seed_execution_complete'])

    def test_extra_sample_missing_retest_or_wrong_prefix_cannot_complete(self):
        for change in ('extra','retest','prefix'):
            code,result=self.audited_fixture(change)
            self.assertNotEqual(code,0);self.assertFalse(result['comparison_ready'])


if __name__=='__main__':unittest.main()
