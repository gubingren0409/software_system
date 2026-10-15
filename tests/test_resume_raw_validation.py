"""Controlled disk-continuation regressions; no C processes or performance observations."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts import resume_raw_validation as r


class ValidationContinuationTests(unittest.TestCase):
    def fixture(self):
        plan = dict(content_commit=r.CONTENT, session_id=r.SESSION, mode='validation', comparison_protocol_hash='protocol')
        state = dict(session_id=r.SESSION, active=None, status='ready', target_executions=12,
            validation_groups=[dict(config=dict(optimization='O3', block_size=s)) for s in (128, 64)],
            trajectories={x: dict(observations=[], retests=[]) for x in ('random', 'greedy')})
        samples = [dict(run_id=str(i)) for i in range(12)]
        window = dict(qpc_start=308107090824, qpc_end=316567827584, qpc_frequency=10000000,
            status='stopped', budget_seconds=3600., activity_qpc_seconds=r.OLD_SECONDS)
        return plan, state, samples, window

    def test_only_two_preserved_groups_continue_from_index_two(self):
        plan, state, samples, window = self.fixture()
        self.assertEqual(r.check_start(plan, state, samples, window), 2753.926324)
        self.assertEqual(r.JOB['config'], dict(optimization='O3', block_size=24))
        state['validation_groups'].reverse()
        with self.assertRaises(ValueError): r.check_start(plan, state, samples, window)

    def test_partial_or_duplicate_samples_rejected(self):
        for change in ('active', 'samples', 'duplicate'):
            plan, state, samples, window = self.fixture()
            if change == 'active': state['active'] = dict(saved_samples=1)
            if change == 'samples': samples.append(dict(run_id='extra'))
            if change == 'duplicate': samples[-1] = samples[0]
            with self.assertRaises(ValueError): r.check_start(plan, state, samples, window)

    def test_identity_and_search_observations_rejected(self):
        for change in ('content', 'session', 'mode', 'observations'):
            plan, state, samples, window = self.fixture()
            if change == 'content': plan['content_commit'] = '0'*40
            if change == 'session': plan['session_id'] = 'foreign'
            if change == 'mode': plan['mode'] = 'search'
            if change == 'observations': state['trajectories']['random']['observations'] = [1]
            with self.assertRaises(ValueError): r.check_start(plan, state, samples, window)

    def test_old_window_cannot_reset(self):
        plan, state, samples, window = self.fixture()
        window['qpc_end'] = window['qpc_start']
        window['activity_qpc_seconds'] = 0
        with self.assertRaises(ValueError): r.check_start(plan, state, samples, window)

    def test_durations_sum_without_cross_epoch_subtraction(self):
        # A new epoch can have much smaller absolute endpoints.
        window = dict(qpc_start=10, qpc_end=1000000010, qpc_frequency=10000000)
        self.assertEqual(r.cumulative(r.OLD_SECONDS, window), r.OLD_SECONDS + 100.)
        window['qpc_end'] = 30000000010
        with self.assertRaises(ValueError): r.cumulative(r.OLD_SECONDS, window)
        window['qpc_frequency'] = True
        with self.assertRaises(ValueError): r.cumulative(r.OLD_SECONDS, window)

    def test_only_append_to_original_sample_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'samples'; prefix = b'{"run_id":"old"}\n'
            path.write_bytes(prefix + b'{"run_id":"new"}\n')
            r.check_prefix(path, len(prefix), hashlib.sha256(prefix).hexdigest())
            path.write_bytes(b'!' + path.read_bytes()[1:])
            with self.assertRaises(ValueError): r.check_prefix(path, len(prefix), hashlib.sha256(prefix).hexdigest())

    def test_disk_space_gate_and_real_write_readback(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(r.shutil, 'disk_usage', return_value=SimpleNamespace(free=1024)):
                with self.assertRaisesRegex(ValueError, 'Evidence volume'): r.evidence_preflight(tmp)
            with patch.object(r.shutil, 'disk_usage', return_value=SimpleNamespace(free=2*1024**3)):
                result = r.evidence_preflight(tmp)
                self.assertEqual(r.digest(result['write_probe']), result['sha256'])

    def test_disk_write_error_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(Path, 'open', side_effect=OSError(28, 'No space left on device')):
                with self.assertRaises(OSError): r.evidence_preflight(tmp)

    def test_identity_rejection_before_any_executor_or_claim(self):
        with patch.object(r, 'read', return_value={}), patch.object(r, 'frozen') as executor:
            with self.assertRaises(KeyError): r.run(Path('foreign-authorization.json'))
            executor.assert_not_called()

    def test_group_admission_failure_cannot_invoke_measure(self):
        # Check the operational order, using the real run function and a fake frozen facade.
        plan, state, samples, old = self.fixture()
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp); session=out/'session'; session.mkdir()
            (session/'checkpoint.json').write_text(json.dumps(state))
            (session/'samples.jsonl').write_text('\n'.join(json.dumps(x) for x in samples))
            (session/'window.json').write_text(json.dumps(old))
            auth=dict(schema='raw-validation-disk-continuation-v1',directory=str(out),session_directory=str(session),plan_file='plan',remaining_allowance_seconds=2753.926324, previous_activity_qpc_seconds=r.OLD_SECONDS, checkpoint_sha256='x')
            qpc=iter([(100,10),(110,10),(120,10),(130,10),(140,10),(150,10),(160,10),(170,10)])
            class Sleep:
                def __init__(self,*a): pass
                def __enter__(self): return self
                def __exit__(self,*a): pass
            from unittest.mock import MagicMock
            fake=MagicMock(); fake.qpc.side_effect=lambda:next(qpc); fake.SleepRequest=Sleep
            fake.capture.return_value=dict(returncode=0,timed_out=False); fake.gate.return_value=False; fake.utc_now.return_value='test-only'
            with patch.object(r,'read', side_effect=lambda p: auth if str(p)=='auth' else plan if str(p)=='plan' else json.loads(Path(p).read_text())), \
                    patch.object(r,'verify_auth'), patch.object(r,'verify_preserved',return_value=state), \
                    patch.object(r,'frozen',return_value=(fake,MagicMock())), patch.object(r,'evidence_preflight',return_value={}), patch.object(r,'digest',return_value='test-hash'):
                self.assertEqual(r.run(Path('auth')),2)
            fake.measure.assert_not_called(); fake.clock_check.assert_not_called()
            fake.claim.assert_called_once()
            fake.gate.assert_called_once()

    def test_user_retry_preserves_used_allowance_and_different_epoch(self):
        window=dict(qpc_start=10,qpc_end=1000000010,qpc_frequency=10000000)
        self.assertEqual(r.cumulative(r.PREVIOUS_CUMULATIVE_SECONDS,window),1146.1205449)
        self.assertEqual(r.TOTAL_SECONDS-r.PREVIOUS_CUMULATIVE_SECONDS,2553.8794551)
        with self.assertRaises(ValueError): r.cumulative(0,window)

    def test_retry_claim_is_separate_and_exclusive(self):
        old=r.claim_filename(dict(schema='raw-validation-disk-continuation-v1'))
        new=r.claim_filename(dict(schema=r.RETRY_SCHEMA))
        self.assertNotEqual(old,new)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/new
            with path.open('x') as f: f.write('one attempt')
            with self.assertRaises(FileExistsError): path.open('x')
            self.assertEqual(path.read_text(),'one attempt')

    def test_formal_gate_leaves_cleanup_time_within_120(self):
        from unittest.mock import MagicMock
        f=MagicMock()
        with patch.object(r.time,'perf_counter',return_value=100):
            r.formal_gate(f,{},Path('gate'),{},1000)
        self.assertEqual(f.gate.call_args.args[-1],219)
        self.assertEqual(f.gate.call_args.args[2],'Formal')

    def test_prior_closed_window_cannot_be_refunded_or_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp); (out/'preserved').mkdir(); checkpoint=out/'preserved/checkpoint.json'
            checkpoint.write_text('{}'); prior_path=out/'authorization.json'
            prior=dict(schema='raw-validation-disk-continuation-v1',content_commit=r.CONTENT,session_id=r.SESSION,
                previous_activity_qpc_seconds=r.OLD_SECONDS,auxiliary_content_commit='22fe97c02e2bf1cd56662413e10fc5311113a246',
                directory=str(out),checkpoint_sha256=r.digest(checkpoint))
            prior_path.write_text(json.dumps(prior))
            window=dict(status='stopped',failure_reason='Group Formal gate refused',authorization_sha256=r.digest(prior_path),
                budget_seconds=2753.926324,qpc_start=393789313692,qpc_end=395789782381,qpc_frequency=10000000,
                activity_qpc_seconds=r.PREVIOUS_CONTINUATION_SECONDS,cumulative_activity_qpc_seconds=r.PREVIOUS_CUMULATIVE_SECONDS)
            (out/'window.json').write_text(json.dumps(window))
            (out/'DISK_CONTINUATION_V1.claim.json').write_text(json.dumps(window))
            used,identity=r.previous_allowance(prior_path,out)
            self.assertEqual(used,r.PREVIOUS_CUMULATIVE_SECONDS)
            window['qpc_end']=window['qpc_start']; window['activity_qpc_seconds']=0
            (out/'window.json').write_text(json.dumps(window))
            with self.assertRaises(ValueError): r.previous_allowance(prior_path,out)


if __name__ == '__main__': unittest.main()
