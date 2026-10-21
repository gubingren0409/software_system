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

from scripts import finish_raw_search as r
from scripts.raw_comparison_contract import replay
from scripts.start_raw_comparison import claim
from autotuner.core import Config,ConfigSpace
from autotuner.raw_comparison import strategy_for,prefixes


class FirstSeedFinishingTests(unittest.TestCase):
    def fixture(self):
        own=lambda n,k:dict(observations=[{'config':i} for i in range(n)],retests=list(range(k)))
        plan=dict(content_commit=r.CONTENT,session_id=r.SESSION,mode='search',comparison_protocol_hash='protocol')
        state=dict(session_id=r.SESSION,mode='search',status='stopped',target_executions=156,
            active=dict(attempt_id=r.OLD_ATTEMPT,job=copy.deepcopy(r.JOB),saved_samples=4,formal_comparable=False),
            trajectories={'random':own(12,2),'greedy':own(11,0)},
            manual_resume=dict(abandoned_attempt=dict(attempt_id=r.FIRST_ATTEMPT),abandoned_run_ids=r.ABANDONED[r.FIRST_ATTEMPT]))
        records=[dict(run_id='original_'+str(i),attempt_id='accepted',classification='success') for i in range(156)]
        for index,(attempt,ids) in enumerate(r.ABANDONED.items()):
            offset=96 if index==0 else 152
            records[offset:offset+len(ids)]=[dict(run_id=run_id,attempt_id=attempt,
                classification='timeout' if i==len(ids)-1 else 'success') for i,run_id in enumerate(ids)]
        old=dict(content_commit=r.CONTENT,session_id=r.SESSION,status='stopped',budget_seconds=43200,
            activity_qpc_seconds=15841.5879168,qpc_start=135832887190,qpc_end=294248766358,qpc_frequency=10000000)
        return plan,state,records,old

    def test_exact_existing_state_and_remaining_budget(self):
        self.assertEqual(r.check_start(*self.fixture()),19870.3388118)

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

    def test_append_second_ledger_without_overwriting_first_or_25_groups(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp)/'authorization.json').write_text('{}')
            plan,state,records,old=self.fixture();before=copy.deepcopy(state)
            auth=dict(directory=tmp,old_partial_run_ids=r.ABANDONED[r.OLD_ATTEMPT])
            resumed=r.reactivate(state,auth)
            self.assertEqual(state,before)
            self.assertEqual(resumed['trajectories'],state['trajectories'])
            self.assertIsNone(resumed['active']);self.assertEqual(resumed['status'],'ready')
            self.assertEqual(resumed['manual_resume'],state['manual_resume'])
            self.assertEqual(resumed['finish_resume']['abandoned_attempt'],state['active'])
            self.assertEqual(resumed['finish_resume']['abandoned_run_ids'],r.ABANDONED[r.OLD_ATTEMPT])
            self.assertEqual(resumed['finish_resume']['exact_combined_abandonments'],r.ABANDONED)

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
                if change=='newbest' and algorithm=='greedy' and kind=='search' and index==11:score=0.00001
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
            for attempt,ids in r.ABANDONED.items():
                part=[]
                for run_id in ids:
                    run_dir=session/'runs'/run_id;run_dir.mkdir()
                    sample=dict(run_id=run_id,attempt_id=attempt,run_directory=str(run_dir),source='fresh_measurement',
                        context=dict(force_remeasure=True),raw_stdout='',raw_stderr='')
                    write(run_dir/'result.json',sample);(run_dir/'stdout.txt').write_text('');(run_dir/'stderr.txt').write_text('')
                    part.append(sample);abandoned.append(sample)
                all_rows[96 if attempt==r.FIRST_ATTEMPT else 152:96 if attempt==r.FIRST_ATTEMPT else 152]=part
                write(session/'configurations'/('search_'+attempt+'.json'),dict(classification='failed'))
            (session/'samples.jsonl').write_text('\n'.join(json.dumps(x) for x in all_rows))
            old_ledger=dict(abandoned_attempt=dict(attempt_id=r.FIRST_ATTEMPT),abandoned_run_ids=r.ABANDONED[r.FIRST_ATTEMPT])
            ledger=dict(exact_combined_abandonments=r.ABANDONED,abandoned_run_ids=r.ABANDONED[r.OLD_ATTEMPT],
                abandoned_attempt=dict(attempt_id=r.OLD_ATTEMPT),
                previous_ledger_sha256=hashlib.sha256(json.dumps(old_ledger,sort_keys=True).encode()).hexdigest())
            state=dict(status='complete',active=None,target_executions=len(all_rows),trajectories=own,
                manual_resume=old_ledger,finish_resume=ledger,reference_generation_calls=0)
            write(out/'abandoned_attempt.json',ledger)
            window=dict(content_commit=r.CONTENT,session_id=r.SESSION,qpc_start=10,qpc_end=100000010,qpc_frequency=10000000,
                budget_seconds=r.REMAINING,activity_qpc_seconds=10,cumulative_activity_qpc_seconds=r.USED+10,status='complete',budget_pass=True,failure_reason=None)
            plan=dict(content_commit=r.CONTENT,session_id=r.SESSION,comparison_protocol_hash='protocol')
            write(root/'plan.json',plan)
            auth=dict(directory=str(out),session_directory=str(session),plan_file=str(root/'plan.json'),
                checkpoint_sha256='old-checkpoint',old_partial_run_ids=r.ABANDONED[r.OLD_ATTEMPT],abandonments=r.ABANDONED)
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
            if change=='replay':state['trajectories']['greedy']['observations'][0]['config']={'optimization':'O0','block_size':8}
            fake=SimpleNamespace(ROOT=project,ConfigSpace=ConfigSpace,local_path=Path,
                audit_clock=Mock(return_value=dict(clock_complete=True,evidence_integrity_pass=True,raw_reference_pass=True,errors=[])),atomic_write_json=write)
            contract=SimpleNamespace(require_certificate=Mock(),audit_volume=Mock(),audit_gate=Mock(return_value=True),
                replay=replay,prefixes=prefixes,verify_group=Mock(),
                checked_operation=Mock(return_value=dict(stdout_path='cache.stdout.json',returncode=0,timed_out=False)))
            with patch.object(r,'verify_auth'),patch.object(r,'verify_preserved',return_value=state),patch.object(r,'frozen',return_value=(fake,contract)):
                rc=r.audit(auth_path)
            result=json.loads((out/'independent_continuation_audit.json').read_bytes())
            return rc,result

    def test_complete_audit_accounts_for_exact_six_abandoned_records_and_real_own_replay(self):
        code,result=self.audited_fixture()
        self.assertEqual(code,0,result);self.assertTrue(result['comparison_ready'])
        self.assertEqual(result['target_executions'],162+6*result['greedy_retest_groups'])
        self.assertEqual(result['accepted_target_samples'],156+6*result['greedy_retest_groups'])
        self.assertEqual(result['abandoned_target_samples'],6)
        self.assertFalse(result['five_seed_execution_complete'])

    def test_extra_sample_missing_retest_or_wrong_prefix_cannot_complete(self):
        for change in ('extra','retest','prefix','replay'):
            code,result=self.audited_fixture(change)
            self.assertNotEqual(code,0);self.assertFalse(result['comparison_ready'])

    def test_new_last_candidate_requires_second_greedy_retest(self):
        code,result=self.audited_fixture('newbest')
        self.assertEqual(code,0,result)
        self.assertEqual(result['greedy_retest_groups'],2)
        self.assertEqual(result['target_executions'],174)
        self.assertEqual(result['accepted_target_samples'],168)

    def test_156_prefix_25_group_protection_including_original_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);session=root/'session';session.mkdir();out=root/'continuation';out.mkdir();(out/'preserved').mkdir()
            _,state,records,_=self.fixture()
            for key in ('schema','fingerprint','validation_groups','artifacts','setup_raw_seconds','reference_generation_calls'):
                state[key]=key
            raw='\n'.join(json.dumps(x) for x in records).encode()
            (session/'samples.jsonl').write_bytes(raw)
            (out/'preserved/checkpoint.json').write_text(json.dumps(state))
            protected=root/'old-claim';protected.write_text('unchanged')
            auth=dict(repository_directory=str(root),session_directory=str(session),directory=str(out),
                protected_files={'old-claim':r.digest(protected)},samples_prefix_bytes=len(raw),samples_prefix_sha256=hashlib.sha256(raw).hexdigest())
            for change in ('none','random','greedy','ledger','prefix','protected'):
                value=copy.deepcopy(state);(session/'samples.jsonl').write_bytes(raw);protected.write_text('unchanged')
                if change in ('random','greedy'):value['trajectories'][change]['observations'][0]['config']='changed'
                if change=='ledger':value['manual_resume']['abandoned_run_ids']=[]
                if change=='prefix':(session/'samples.jsonl').write_bytes(b'!'+raw[1:])
                if change=='protected':protected.write_text('changed')
                (session/'checkpoint.json').write_text(json.dumps(value))
                if change=='none':self.assertEqual(r.verify_preserved(auth),state)
                else:
                    with self.assertRaises(ValueError):r.verify_preserved(auth)

    def test_invalid_budget_or_authorization_map_rejected_before_execution(self):
        for change in ('budget','map','baseline'):
            auth=dict(schema=r.SCHEMA,baseline_commit=r.BASELINE,content_commit=r.CONTENT,session_id=r.SESSION,
                previous_activity_qpc_seconds=r.USED,remaining_allowance_seconds=r.REMAINING,total_activity_limit_seconds=r.TOTAL,
                helper_file=str(r.SELF),helper_sha256=r.digest(r.SELF),abandonments=copy.deepcopy(r.ABANDONED))
            if change=='budget':auth['remaining_allowance_seconds']=43200
            if change=='map':auth['abandonments'][r.OLD_ATTEMPT].append('unknown')
            if change=='baseline':auth['baseline_commit']='0'*40
            with self.assertRaises(ValueError):r.verify_auth(auth)

    def test_old_windows_use_own_epochs_and_exact_accumulated_allowance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);one=root/'first.json';two=root/'second.json';prior=root/'prior.json'
            prior.write_text(json.dumps(dict(old_partial_run_ids=r.ABANDONED[r.FIRST_ATTEMPT])))
            first=self.fixture()[3]
            second=dict(content_commit=r.CONTENT,session_id=r.SESSION,status='stopped',budget_seconds=27358.4120832,
                activity_qpc_seconds=7488.0732714,qpc_start=100,qpc_end=74880732814,qpc_frequency=10000000,
                previous_activity_qpc_seconds=15841.5879168,cumulative_activity_qpc_seconds=r.USED,authorization_sha256=r.digest(prior))
            one.write_text(json.dumps(first));two.write_text(json.dumps(second))
            auth=dict(previous_windows=[dict(file=str(p),sha256=r.digest(p),seconds=r.elapsed(json.loads(p.read_bytes()))) for p in (one,two)],
                previous_authorization_file=str(prior),previous_authorization_sha256=r.digest(prior))
            r.verify_windows(auth)
            second['budget_seconds']=43200;two.write_text(json.dumps(second));auth['previous_windows'][1]['sha256']=r.digest(two)
            with self.assertRaises(ValueError):r.verify_windows(auth)


if __name__=='__main__':unittest.main()
