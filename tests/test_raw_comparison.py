"""Only new comparison/control regressions; all matrix evaluations are fake."""
from __future__ import annotations

import copy
import json
import tempfile
import time
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

from autotuner.core import Config, ConfigSpace, sha256_json
from autotuner.measurement import ConfigurationEvaluator
from autotuner.raw_comparison import (comparison_protocol, next_job, commit_observation, replay,
                                     prefixes, opened, accept, initialize)
from autotuner.session import restore_complete_group
from scripts.raw_comparison_contract import continuity, certificate_value, require_certificate
from scripts.raw_comparison_power import SleepRequest, validate_event_record, ES_CONTINUOUS, ES_SYSTEM_REQUIRED
from scripts.start_raw_comparison import claim, validate_plan, run
from scripts.raw_clock_contract import manifest_schedule, raw_schedule
from test_raw_grid import RawStub

ROOT = Path(__file__).resolve().parents[1]


def state_for(mode='search'):
    return {'mode': mode, 'status': 'ready', 'active': None, 'validation_groups': [],
        'trajectories': {a: {'observations': [], 'retests': [], 'prefixes': [], 'prefix_retest_mapping': []}
                         for a in ('random', 'greedy')}}


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.protocol = comparison_protocol()
        self.space = ConfigSpace.load(ROOT / 'configs/config_space.json')

    def run_fake(self):
        state = state_for(); measurement = json.loads((ROOT / 'configs/measurement_protocol.json').read_bytes())
        measurement['target_matrix_n'] = 130
        calls = []; snapshots = {}
        with tempfile.TemporaryDirectory() as temporary:
            executor = RawStub(measurement)
            while (job := next_job(state, self.space, self.protocol)) is not None:
                attempt = 'fake-' + str(len(calls)); state['active'] = {'job': job, 'attempt_id': attempt}
                with patch('autotuner.measurement.execution_clock', side_effect=lambda raw: time.perf_counter()):
                    group = ConfigurationEvaluator(executor, measurement, sha256_json(measurement), Path(temporary)).evaluate(
                        Config(**job['config']), attempt_id=attempt, purpose=job['kind'])
                restore_complete_group(group, measurement)
                if job['kind'] == 'retest':
                    snapshots.setdefault(job['algorithm'], copy.deepcopy(state['trajectories'][job['algorithm']]['observations']))
                commit_observation(state, job, group, self.space, self.protocol); calls.append(job)
            self.assertTrue(all(c.force_remeasure for c in executor.calls))
            self.assertEqual(len(executor.calls), len(calls) * 6)
        return state, calls, snapshots

    def test_two_unique_12_trajectories_prefixes_and_deduplicated_retests(self):
        state, calls, snapshots = self.run_fake()
        for algorithm in ('random', 'greedy'):
            own = state['trajectories'][algorithm]
            self.assertEqual(len(own['observations']), 12)
            self.assertEqual(len({json.dumps(g['config'], sort_keys=True) for g in own['observations']}), 12)
            self.assertEqual([p['budget'] for p in own['prefixes']], [4, 8, 12])
            candidates = {json.dumps(p['best_config'], sort_keys=True) for p in own['prefixes']}
            self.assertEqual(len(own['retests']), len(candidates))
            self.assertTrue(all(p['retest_attempt'] for p in own['prefix_retest_mapping']))
            self.assertEqual(own['observations'], snapshots[algorithm])
            # Fake scores increase, so all prefixes select the first group.
            self.assertEqual(len(own['retests']), 1)
        self.assertEqual(state['status'], 'complete')
        ids = [s['run_id'] for own in state['trajectories'].values() for g in own['observations'] + own['retests'] for s in g['samples']]
        self.assertEqual(len(ids), len(set(ids)))

    def test_replay_uses_only_own_observations_and_not_extra_fields(self):
        state, _, _ = self.run_fake()
        own = state['trajectories']['greedy']['observations']
        poisoned = copy.deepcopy(own[:5])
        for g in poisoned: g.update(grid={'score_seconds': 0}, other_algorithm={'score_seconds': 0}, retest=0)
        self.assertEqual(replay(self.space, 'greedy', own[:5]).ask(), replay(self.space, 'greedy', poisoned).ask())
        self.assertEqual(replay(self.space, 'random', state['trajectories']['random']['observations'][:8]).ask(),
                         Config(**state['trajectories']['random']['observations'][8]['config']))
        invalid = copy.deepcopy(own); invalid[1]['config'] = invalid[0]['config']
        with self.assertRaises(ValueError): replay(self.space, 'greedy', invalid)

    def test_validation_order_is_separate_from_search_observations(self):
        state = state_for('validation'); seen = []
        while (job := next_job(state, self.space, self.protocol)) is not None:
            state['active'] = {'job': job}
            group = {'config': job['config'], 'classification': 'success', 'score_seconds': .1}
            commit_observation(state, job, group, self.space, self.protocol); seen.append(job['config'])
        self.assertEqual(seen, [{'optimization': 'O3', 'block_size': s} for s in (128, 64, 24)])
        self.assertTrue(all(not t['observations'] for t in state['trajectories'].values()))

    def test_partial_and_failed_groups_never_complete_or_retry(self):
        state = state_for(); job = next_job(state, self.space, self.protocol); state['active'] = {'job': job}
        self.assertIsNone(next_job(state, self.space, self.protocol))
        with self.assertRaises(ValueError): commit_observation(state, job,
            {'config': job['config'], 'classification': 'invalid', 'score_seconds': None}, self.space, self.protocol)
        self.assertTrue(all(not t['observations'] for t in state['trajectories'].values()))

    def test_budget_claim_cannot_be_reset_by_second_start(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'claim.json'; claim(path, {'qpc_start': 123, 'budget_seconds': 3600})
            original = path.read_bytes()
            with self.assertRaises(FileExistsError): claim(path, {'qpc_start': 999, 'budget_seconds': 3600})
            self.assertEqual(path.read_bytes(), original)

    def test_wrong_session_or_fingerprint_rejected_before_certificate(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary); (output / 'checkpoint.json').write_text(json.dumps({
                'schema': 'raw-comparison-session-v1', 'fingerprint': {'source': 'wrong'}, 'mode': 'search'}))
            with patch('autotuner.raw_comparison.runtime', return_value=(output, {}, {}, None, {'source': 'right'})), \
                 patch('scripts.raw_comparison_contract.require_certificate') as cert:
                with self.assertRaises(ValueError): opened({'mode': 'search'})
                cert.assert_not_called()

    def test_initialization_empty_does_not_execute_target(self):
        from unittest.mock import MagicMock
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary); target = MagicMock()
            with patch('autotuner.raw_comparison.runtime', return_value=(output, self.protocol, {}, target, {})):
                initialize({'mode': 'validation', 'session_id': 'a' * 32})
                with self.assertRaises(ValueError): initialize({'mode': 'validation', 'session_id': 'a' * 32})
            target.build_candidate.assert_not_called(); target.get_reference.assert_not_called()

    def test_foreign_or_historical_certificate_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); (root / 'initial_checkpoint.json').write_text('{}'); (root / 'manifest.json').write_text('{}')
            plan = {'session_directory': str(root), 'recovery_directory': str(root), 'content_commit': 'a'*40,
                'session_id': 'b'*32, 'comparison_protocol_hash': 'c'*64, 'timing_protocol_hash': 'd'*64,
                'measurement_protocol_hash': 'e'*64}
            audit = {'recovery_eligible': True}; cert = certificate_value(plan, audit)
            with patch('scripts.raw_comparison_contract.audit_admission', return_value=audit):
                for key, value in (('schema', 'raw-grid-recovery-certificate-v1'), ('session_id', 'f'*32),
                                   ('content_commit', 'f'*40), ('comparison_protocol_hash', 'f'*64)):
                    (root / 'certificate.json').write_text(json.dumps({**cert, key: value}))
                    with self.assertRaises(ValueError): require_certificate(plan)
                (root / 'certificate.json').write_text(json.dumps(cert)); self.assertEqual(require_certificate(plan), audit)

    def test_new_admission_two_intervals_legacy_stays_twelve(self):
        context = {'comparison_protocol_hash': sha256_json(self.protocol)}
        manifest = {'schema': 'raw-comparison-clock-manifest-v1', 'comparison_protocol_hash': sha256_json(self.protocol),
                    'context': context, 'purpose': 'admission'}
        self.assertEqual([p['updates'] for p in manifest_schedule(manifest)], [10**9, 10**10])
        self.assertEqual(len(raw_schedule('recovery')), 12)
        manifest['comparison_protocol_hash'] = '0'*64
        with self.assertRaises(ValueError): manifest_schedule(manifest)

    def test_entry_identity_mismatch_refuses_before_activity_claim(self):
        with patch('scripts.start_raw_comparison.validate_base', side_effect=ValueError('source SHA differs')), \
             patch('scripts.start_raw_comparison.claim') as activity:
            with self.assertRaisesRegex(ValueError, 'source SHA'): run({}, Path('unused'))
            activity.assert_not_called()

    def test_entry_requires_exact_comparison_protocol_and_session(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            initial = {'session_id': 'a'*32, 'mode': 'validation', 'fingerprint': {
                'content_commit': 'b'*40, 'comparison_protocol_hash': sha256_json(self.protocol)}}
            (root / 'initial_checkpoint.json').write_text(json.dumps(initial))
            plan = {'schema': 'raw-comparison-plan-v1', 'mode': 'validation', 'content_commit': 'b'*40,
                'measurement_content': self.protocol['inherited_measurement_content'], 'session_id': 'a'*32,
                'comparison_protocol_hash': sha256_json(self.protocol), 'session_directory': str(root)}
            with patch('scripts.start_raw_comparison.validate_base'):
                self.assertEqual(validate_plan(plan), self.protocol)
                for field, value in (('comparison_protocol_hash', 'f'*64), ('session_id', 'f'*32), ('content_commit', 'f'*40)):
                    with self.assertRaises(ValueError): validate_plan({**plan, field: value})

    def test_real_search_entry_requires_separate_authorization_before_claim(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); (root / 'checkpoint.json').write_text(json.dumps(state_for()))
            with patch('scripts.start_raw_comparison.validate_plan', return_value=self.protocol), \
                 patch('scripts.start_raw_comparison.claim') as activity:
                with self.assertRaisesRegex(ValueError, 'separately reviewed'):
                    run({'mode': 'search', 'session_directory': str(root), 'content_commit': 'b'*40,
                         'session_id': 'a'*32, 'comparison_protocol_hash': sha256_json(self.protocol)}, root / 'plan.json')
                activity.assert_not_called()

    def test_post_clock_or_continuity_failure_never_accepts_group(self):
        # The raw group contract is already tested; this test isolates the NEW
        # accept barrier after both old clock checks could have passed.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); (root / 'configurations').mkdir()
            job = {'kind': 'validation', 'config': {'optimization': 'O3', 'block_size': 128}}
            (root / 'configurations/validation_a.json').write_text(json.dumps({'config': job['config']}))
            state = state_for('validation'); state['active'] = {'job': job, 'attempt_id': 'a'}
            with patch('autotuner.raw_comparison.opened', return_value=(root, self.protocol, {}, None, state)), \
                 patch('autotuner.raw_comparison.restore_complete_group'), \
                 patch('scripts.raw_comparison_contract.verify_group', side_effect=ValueError('standby despite passing clocks')):
                with self.assertRaisesRegex(ValueError, 'standby'): accept({}, 'a', root)
            self.assertEqual(state['validation_groups'], [])
            self.assertIsNotNone(state['active'])


class ContinuityTests(unittest.TestCase):
    def values(self, seconds=100):
        return ({'raw_start_ns': 10**18, 'raw_end_ns': 10**18+100*10**9, 'raw_seconds': 100.},
                {'start_qpc': 10**16, 'end_qpc': 10**16+seconds*10**7, 'qpc_frequency': 10**7})

    def test_same_scope_pass_and_standby_with_passing_boundary_checks_fails(self):
        scope, host = self.values()
        self.assertTrue(continuity(scope, host, [])['uninterrupted_execution'])
        events = [{'events': [{'event_id': 506, 'provider': 'Microsoft-Windows-Kernel-Power', 'message': 'Reason: Lid'}]}]
        self.assertFalse(continuity(scope, host, events)['uninterrupted_execution'])

    def test_excess_difference_stops_without_calibrating_score(self):
        scope, host = self.values(131)
        self.assertFalse(continuity(scope, host, [])['uninterrupted_execution'])
        self.assertEqual(scope['raw_seconds'], 100.)
        host['end_qpc'] = host['start_qpc']
        with self.assertRaises(ValueError): continuity(scope, host, [])

    def test_invalid_endpoint_and_mismatched_raw_delta_rejected(self):
        for invalid in (True, 0, -1, 1.5, float('nan')):
            scope, host = self.values(); scope['raw_start_ns'] = invalid
            with self.assertRaises(ValueError): continuity(scope, host, [])
        scope, host = self.values(); scope['raw_seconds'] = 99.
        with self.assertRaises(ValueError): continuity(scope, host, [])

    def test_power_record_reset_missing_messages_and_boot_change_rejected(self):
        good = {'schema': 'raw-comparison-power-events-v1', 'log': 'System', 'cursor_before': 10,
            'cursor_after': 12, 'windows_boot_utc': 'boot', 'events': []}
        validate_event_record(good, 10, 'boot')
        for change in ({'cursor_after': 9}, {'windows_boot_utc': 'other'}, {'events': [{}]}):
            with self.assertRaises((ValueError, KeyError)): validate_event_record({**good, **change}, 10, 'boot')

    def test_exception_releases_sleep_request_on_same_thread_and_saves_evidence(self):
        calls = []
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'sleep.json'
            def api(flags): calls.append(flags); return ES_CONTINUOUS
            with self.assertRaisesRegex(RuntimeError, 'fake executor failed'):
                with SleepRequest(path, api): raise RuntimeError('fake executor failed')
            value = json.loads(path.read_text())
            self.assertTrue(value['acquired'] and value['released'])
            self.assertEqual(value['thread_id'], value['release_thread_id'])
            self.assertIn('fake executor failed', value['exception'])
            self.assertEqual(calls, [ES_CONTINUOUS | ES_SYSTEM_REQUIRED, ES_CONTINUOUS])

    def test_failed_sleep_request_refuses_before_running(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(OSError):
                with SleepRequest(Path(temporary) / 'sleep.json', lambda flags: 0): self.fail('must not execute')


if __name__ == '__main__': unittest.main()
