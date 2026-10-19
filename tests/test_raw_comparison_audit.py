"""Controlled audit/storage regressions; no native clocks or matrix executables.

Group clock/performance checks are stubbed ONLY for these audit-structure fixtures;
the unchanged raw group contract and fake evaluator are tested separately.
"""
import copy
import io
import json
import tempfile
import unittest
from contextlib import ExitStack, redirect_stdout
from dataclasses import asdict
from pathlib import Path
from unittest.mock import MagicMock, patch

from autotuner.core import ConfigSpace, sha256_file, sha256_json
from autotuner.raw_comparison import comparison_protocol, prefixes, replay
from scripts import raw_comparison_contract as contract
from scripts import start_raw_comparison as controller
from scripts.evidence_volume import check_volume, audit_volume
from scripts.raw_comparison_power import SleepRequest, ES_CONTINUOUS

ROOT=Path(__file__).resolve().parents[1]


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


class SearchAuditTests(unittest.TestCase):
    def fixture(self, directory, *, retests=True, counts=(12,12)):
        protocol=comparison_protocol(); space=ConfigSpace.load(ROOT/'configs/config_space.json')
        source_files={name: {'executed_sha256':'controlled-test-only'} for name in (
            'autotuner/raw_comparison.py','autotuner/search.py','autotuner/measurement.py',
            'scripts/raw_comparison_contract.py','scripts/start_raw_comparison.py',
            'code/original/matrix_multiplication.c','code/working/matrix_multiplication.c')}
        plan=dict(schema='raw-comparison-plan-v1',mode='search',session_directory=str(directory),
            plan_file=str(directory/'plan.json'),git_identity=str(directory/'identity.json'),
            recovery_directory=str(directory/'admission'),content_commit='a'*40,session_id='b'*32,
            measurement_content=protocol['inherited_measurement_content'],
            measurement_protocol_hash=protocol['measurement_protocol_hash'],timing_protocol_hash=protocol['timing_protocol_hash'],
            comparison_protocol_hash=sha256_json(protocol),compiler_sha256='c'*64,
            windows_source_identity=source_files,linux_source_identity=source_files)
        fingerprint={k:plan[k] for k in ('content_commit','session_id','measurement_content','measurement_protocol_hash','comparison_protocol_hash','compiler_sha256')}
        fingerprint.update(files=source_files,target_hash=sha256_json({'synthetic_target':True}))
        state=dict(schema='raw-comparison-session-v1',mode='search',session_id=plan['session_id'],fingerprint=fingerprint,
            status='initialized',active=None,validation_groups=[],target_executions=0,
            trajectories={a:dict(observations=[],retests=[],prefixes=[],prefix_retest_mapping=[]) for a in ('random','greedy')})
        write(directory/'initial_checkpoint.json',state); write(directory/'effective_target.json',{'synthetic_target':True})
        write(directory/'identity.json',dict(content_sha=plan['content_commit'],files={k:'synthetic-blob' for k in source_files}))
        rows=[]; groups=[]
        def group(config, kind):
            attempt='synthetic-'+str(len(groups)); samples=[]
            for index in range(6):
                run=directory/'runs'/(attempt+'-'+str(index)); run.mkdir(parents=True)
                sample=dict(run_id=attempt+'-'+str(index),source='fresh_measurement',context={'force_remeasure':True},
                    run_directory=str(run),raw_stdout='synthetic stdout\n',raw_stderr='')
                write(run/'result.json',sample); (run/'stdout.txt').write_text(sample['raw_stdout']); (run/'stderr.txt').write_text('')
                samples.append(sample); rows.append(sample)
            original=dict(attempt_id=attempt,config=config,classification='success',score_seconds=float(len(groups)+1),
                evaluation_wall_seconds=float(len(groups)+10),samples=samples)
            filename=directory/'configurations'/(kind+'_'+attempt+'.json'); write(filename,original)
            checks=directory/'group_checks'/attempt; checks.mkdir(parents=True)
            accepted=dict(original,checks_directory=str(checks),measured_group_sha256=sha256_file(filename))
            groups.append(accepted); return accepted
        for algorithm,count in zip(('random','greedy'),counts):
            own=state['trajectories'][algorithm]
            for _ in range(count):
                config=asdict(replay(space,algorithm,own['observations']).ask())
                own['observations'].append(group(config,'search'))
            own['prefixes']=prefixes(space,algorithm,own['observations'])
            for row in own['prefixes'] if retests else []:
                if row['best_config'] not in [g['config'] for g in own['retests']]:
                    own['retests'].append(group(row['best_config'],'retest'))
            own['prefix_retest_mapping']=[dict(row,retest_attempt=next((g['attempt_id'] for g in own['retests'] if g['config']==row['best_config']),None)) for row in own['prefixes']]
        state.update(status='complete',target_executions=len(rows)); write(directory/'checkpoint.json',state)
        (directory/'samples.jsonl').write_text(''.join(json.dumps(s)+'\n' for s in rows))
        write(directory/'admission/certificate.json',{'synthetic':True}); write(directory/'plan.json',plan)
        authorization=directory/'authorization.json'; write(authorization,contract.search_authorization_value(plan))
        window=dict(schema='raw-comparison-activity-v1',mode='search',scope='first_seed',content_commit=plan['content_commit'],
            session_id=plan['session_id'],matrix_input_seed=20261008,search_seed=20261008,
            search_authorization_file=str(authorization),search_authorization_sha256=sha256_file(authorization),
            qpc_start=10**16,qpc_end=10**16+100*10**7,qpc_frequency=10**7,activity_qpc_seconds=100.,budget_seconds=43200,
            plan_sha256=sha256_file(directory/'plan.json'),status='complete',budget_pass=True,failure_reason=None)
        write(directory/'window.json',window); write(directory/'ACTIVITY.claim.json',window)
        write(directory/'sleep_request.json',dict(acquired=True,released=True,thread_id=1,release_thread_id=1))
        check_volume(directory,directory/'evidence_volume_start.json',dict(content_commit=plan['content_commit'],
            session_id=plan['session_id'],plan_sha256=window['plan_sha256'],phase='start'))
        return plan,state,source_files

    def audited(self, plan, files, *, cli=False):
        with patch('autotuner.session.source_identity',return_value=files), \
             patch.object(contract,'verify_group',return_value={'uninterrupted_execution':True}), \
             patch.object(contract,'require_certificate',return_value={'recovery_eligible':True}):
            if cli:
                with redirect_stdout(io.StringIO()):
                    code=contract.main(['--plan',plan['plan_file'],'--output',str(Path(plan['session_directory'])/'audit.json')])
                return code,json.loads((Path(plan['session_directory'])/'audit.json').read_bytes())
            return contract.audit(plan)

    def test_complete_first_seed_search_real_audit_cli_returns_zero(self):
        with tempfile.TemporaryDirectory() as temporary:
            plan,state,files=self.fixture(Path(temporary)); code,result=self.audited(plan,files,cli=True)
            self.assertEqual(code,0); self.assertTrue(result['comparison_ready']); self.assertTrue(result['first_seed_complete'])
            self.assertEqual(result['scope'],'first_seed'); self.assertFalse(result['five_seed_execution_complete'])
            self.assertEqual(result['search_groups'],24); self.assertEqual(result['independent_retest_groups'],2)
            self.assertEqual(result['target_executions'],156)

    def test_empty_or_missing_trajectory_cannot_complete(self):
        for change in ('empty','missing'):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as temporary:
                root=Path(temporary); plan,state,files=self.fixture(root)
                if change=='empty': state['trajectories']={}
                else: del state['trajectories']['greedy']
                write(root/'checkpoint.json',state); code,result=self.audited(plan,files,cli=True)
                self.assertEqual(code,2); self.assertFalse(result['comparison_ready'])

    def test_one_completed_or_short_second_trajectory_cannot_complete(self):
        for counts in ((12,0),(12,4)):
            with self.subTest(counts=counts),tempfile.TemporaryDirectory() as temporary:
                plan,state,files=self.fixture(Path(temporary),counts=counts)
                result=self.audited(plan,files)
                self.assertTrue(result['evidence_integrity_pass'],result['errors']); self.assertFalse(result['execution_complete'])

    def test_complete_search_trajectories_without_retests_return_nonzero(self):
        with tempfile.TemporaryDirectory() as temporary:
            plan,state,files=self.fixture(Path(temporary),retests=False); code,result=self.audited(plan,files,cli=True)
            self.assertTrue(result['evidence_integrity_pass'],result['errors'])
            self.assertEqual(result['search_groups'],24); self.assertEqual(result['partial_target_samples'],0)
            self.assertFalse(result['comparison_ready']); self.assertEqual(code,2)

    def test_extra_unaccepted_target_is_not_comparison_ready(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);plan,state,files=self.fixture(root)
            sample=copy.deepcopy(state['trajectories']['greedy']['retests'][0]['samples'][0])
            sample.update(run_id='extra',run_directory=str(root/'runs/extra'))
            write(root/'runs/extra/result.json',sample);(root/'runs/extra/stdout.txt').write_text(sample['raw_stdout']);(root/'runs/extra/stderr.txt').write_text('')
            with (root/'samples.jsonl').open('a') as stream: stream.write(json.dumps(sample)+'\n')
            state['target_executions']+=1;write(root/'checkpoint.json',state)
            code,result=self.audited(plan,files,cli=True)
            self.assertTrue(result['evidence_integrity_pass'],result['errors']);self.assertEqual(result['partial_target_samples'],1)
            self.assertFalse(result['comparison_ready']);self.assertEqual(code,2)

    def test_stopped_checkpoint_window_or_budget_flag_cannot_complete(self):
        for change in ('checkpoint','window','budget'):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as temporary:
                root=Path(temporary);plan,state,files=self.fixture(root)
                if change=='checkpoint': state['status']='stopped';write(root/'checkpoint.json',state)
                else:
                    window=json.loads((root/'window.json').read_bytes())
                    window['status' if change=='window' else 'budget_pass']='stopped' if change=='window' else False
                    write(root/'window.json',window)
                self.assertFalse(self.audited(plan,files)['comparison_ready'])

    def test_validation_exit_status_is_separate_from_search(self):
        result=dict(mode='validation',evidence_integrity_pass=True,validation_complete=True,validation_timing_checks_pass=True,
            execution_complete=False,timing_checks_pass=False,comparison_ready=False)
        self.assertEqual(contract.audit_exit_code(result,'validation'),0)
        self.assertEqual(contract.audit_exit_code(result,'search'),2)
        result['validation_complete']=False;self.assertEqual(contract.audit_exit_code(result,'validation'),2)


class EvidenceVolumeTests(unittest.TestCase):
    def test_real_small_write_fsync_readback_and_wrong_context(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); context={'session':'controlled'}
            check_volume(root,root/'check.json',context)
            self.assertTrue(audit_volume(root/'check.json',root,context)['passed'])
            with self.assertRaises(ValueError): audit_volume(root/'check.json',root,{'session':'other'})

    def test_low_space_or_write_failure_stops_before_any_gate_or_target(self):
        for failure in (ValueError('Evidence volume free space below 1 GiB: 1024'),OSError(28,'Controlled write failure')):
            with self.subTest(failure=str(failure)),tempfile.TemporaryDirectory() as temporary:
                root=Path(temporary);protocol=comparison_protocol()
                state=dict(active=None,status='initialized',validation_groups=[],target_executions=0,
                    trajectories={a:dict(observations=[],retests=[]) for a in ('random','greedy')})
                write(root/'checkpoint.json',state)
                plan=dict(mode='search',session_directory=str(root),session_id='b'*32,content_commit='a'*40,
                    comparison_protocol_hash=sha256_json(protocol))
                path=root/'plan.json';write(path,plan);auth=root/'authorization.json';write(auth,contract.search_authorization_value(plan))
                with patch.object(controller,'validate_plan',return_value=protocol), \
                     patch.object(controller,'qpc',side_effect=[(100000,10**7),(110000,10**7),(120000,10**7)]), \
                     patch.object(controller,'SleepRequest',side_effect=lambda path:SleepRequest(path,lambda flags:ES_CONTINUOUS)), \
                     patch('scripts.evidence_volume.evidence_preflight',side_effect=failure), \
                     patch.object(controller,'gate') as gate,patch.object(controller,'clock_check') as clock, \
                     patch.object(controller,'measure') as measure,redirect_stdout(io.StringIO()):
                    self.assertEqual(controller.run(plan,path,auth),2)
                gate.assert_not_called();clock.assert_not_called();measure.assert_not_called()
                self.assertEqual(json.loads((root/'checkpoint.json').read_bytes())['target_executions'],0)
                self.assertFalse(json.loads((root/'evidence_volume_start.json').read_bytes())['passed'])
                self.assertTrue(json.loads((root/'sleep_request.json').read_bytes())['released'])
