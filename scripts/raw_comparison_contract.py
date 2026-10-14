"""Independent verification of new comparison admission, raw groups and continuity."""
from __future__ import annotations

import json
import math
from pathlib import Path

from autotuner.core import sha256_file, sha256_json
from autotuner.raw_comparison import comparison_protocol, job_context, prefixes, replay
from autotuner.session import restore_complete_group
from scripts.p3_clock_contract import atomic_write_json, load
from scripts.raw_clock_contract import audit_clock, audit_gate, checked_operation, local_path
from scripts.raw_comparison_power import standby_events, validate_event_record

ROOT = Path(__file__).resolve().parents[1]


def continuity(scope, host, events):
    for key in ('raw_start_ns', 'raw_end_ns'):
        if type(scope[key]) is not int or scope[key] <= 0:
            raise ValueError('Invalid evaluation RAW endpoint')
    for key in ('start_qpc', 'end_qpc', 'qpc_frequency'):
        if type(host[key]) is not int or host[key] <= 0:
            raise ValueError('Invalid evaluation QPC endpoint')
    raw = (scope['raw_end_ns'] - scope['raw_start_ns']) / 1e9
    qpc_seconds = (host['end_qpc'] - host['start_qpc']) / host['qpc_frequency']
    if raw <= 0 or qpc_seconds <= 0 or scope['raw_seconds'] != raw:
        raise ValueError('Nonpositive or inconsistent same-scope duration')
    limit = max(30., raw * .05)
    interrupted = standby_events(events)
    return {'uninterrupted_execution': not interrupted and abs(qpc_seconds - raw) <= limit,
        'standby_events': interrupted, 'evaluation_raw_seconds': raw, 'evaluation_qpc_seconds': qpc_seconds,
        'absolute_difference_seconds': abs(qpc_seconds - raw), 'difference_limit_seconds': limit,
        'envelope_scope': 'RUN send through FINISHED receive, after READY; guest RAW wraps evaluation only'}


def certificate_value(plan, audit):
    session = local_path(plan['session_directory']); admission = local_path(plan['recovery_directory'])
    return {'schema': 'raw-comparison-admission-certificate-v1', 'content_commit': plan['content_commit'],
        'session_id': plan['session_id'], 'comparison_protocol_hash': plan['comparison_protocol_hash'],
        'timing_protocol_hash': plan['timing_protocol_hash'], 'measurement_protocol_hash': plan['measurement_protocol_hash'],
        'initial_checkpoint_sha256': sha256_file(session / 'initial_checkpoint.json'),
        'manifest_sha256': sha256_file(admission / 'manifest.json'), 'audit': audit}


def audit_admission(plan):
    session = local_path(plan['session_directory']); directory = local_path(plan['recovery_directory'])
    context = {'content_commit': plan['content_commit'], 'session_id': plan['session_id'],
        'comparison_protocol_hash': plan['comparison_protocol_hash'],
        'initial_checkpoint_sha256': sha256_file(session / 'initial_checkpoint.json')}
    result = audit_clock(directory, context)
    measurement = load(ROOT / 'configs/measurement_protocol.json')
    gate = audit_gate(session / 'admission_resources', measurement, 'Recovery', context)
    result['recovery_resource_pass'] = gate
    result['recovery_eligible'] = gate and result['evidence_integrity_pass'] and result['clock_complete'] and \
                                 result['raw_reference_pass'] and not result['errors']
    return result


def require_certificate(plan):
    directory = local_path(plan['recovery_directory'])
    result = audit_admission(plan)
    if load(directory / 'certificate.json') != certificate_value(plan, result) or not result['recovery_eligible']:
        raise ValueError('Missing, foreign, historical or failed comparison admission certificate')
    return result


def verify_group(plan, job, attempt, group, checks):
    checks = local_path(checks); context = job_context(plan, job, attempt)
    measurement = load(ROOT / 'configs/measurement_protocol.json')
    restore_complete_group(group, measurement)
    if not audit_gate(checks / 'resources', measurement, 'Formal', context):
        raise ValueError('Group Formal gate failed')
    filename = job['kind'] + '_' + attempt + '.json'
    for phase in ('before', 'after'):
        expected = {**context, 'phase': phase}
        if phase == 'after':
            expected['group_sha256'] = sha256_file(local_path(plan['session_directory']) / 'configurations' / filename)
        result = audit_clock(checks / phase, expected)
        if not result['raw_reference_pass'] or not result['evidence_integrity_pass'] or result['errors']:
            raise ValueError('Group ' + phase + ' clock failed')
    record = load(checks / 'continuity.json'); scope = load(checks / 'evaluation_scope.json')
    if record['context'] != context or scope['attempt_id'] != attempt or record['scope'] != scope:
        raise ValueError('Continuity scope/session binding differs')
    host = record['host']; events = []
    baseline_op = checked_operation(checks / 'power_events', record['baseline_operation'])
    if baseline_op['returncode'] != 0 or baseline_op['timed_out']:
        raise ValueError('Power event baseline query failed')
    baseline = load(checks / 'power_events' / baseline_op['stdout_path'])
    validate_event_record(baseline, -1)
    before = record['event_cursor_before']; boot = baseline['windows_boot_utc']
    if baseline['cursor_after'] != before:
        raise ValueError('Power event starting RecordId differs')
    for name in record['event_operations']:
        op = checked_operation(checks / 'power_events', name)
        if op['returncode'] != 0 or op['timed_out']:
            raise ValueError('Power query unsuccessful')
        value = load(checks / 'power_events' / op['stdout_path'])
        validate_event_record(value, before, boot)
        before = value['cursor_after']; boot = value['windows_boot_utc']; events.append(value)
    if not events or events[-1]['cursor_after'] != record['event_cursor_after']:
        raise ValueError('Missing power-event coverage')
    # Validate markers against the exact streamed stdout, not a saved PASS flag.
    lines = (checks / 'measure.stdout.txt').read_bytes().splitlines()
    messages = [json.loads(line) for line in lines if line]
    ready = [m for m in messages if m.get('event') == 'READY']
    finished = [m for m in messages if m.get('event') == 'FINISHED']
    if len(ready) != 1 or len(finished) != 1 or ready[0]['attempt_id'] != attempt or ready[0]['job'] != job or \
            {k: v for k, v in finished[0].items() if k != 'event'} != scope or \
            host['command'] != 'RUN ' + attempt + '\n' or record['returncode'] != 0 or record['timed_out'] or record['errors'] or \
            sha256_file(checks / 'measure.stdout.txt') != record['stdout_sha256'] or \
            sha256_file(checks / 'measure.stderr.txt') != record['stderr_sha256']:
        raise ValueError('Evaluation handshake or original stream differs')
    recomputed = continuity(scope, host, events)
    if recomputed != record['result'] or not recomputed['uninterrupted_execution']:
        raise ValueError('Group interrupted or QPC/RAW envelope mismatched')
    if not group['evaluation_wall_seconds'] <= scope['raw_seconds'] <= group['evaluation_wall_seconds'] + 5:
        raise ValueError('RAW scope does not bracket configuration evaluation')
    return recomputed


def audit(plan):
    from autotuner.core import ConfigSpace
    result = {'evidence_integrity_pass': False, 'validation_complete': False,
        'validation_timing_checks_pass': False, 'execution_complete': False,
        'timing_checks_pass': False, 'comparison_ready': False, 'errors': []}
    directory = local_path(plan['session_directory'])
    try:
        protocol = comparison_protocol()
        identity = load(local_path(plan['git_identity']))
        from autotuner.session import source_identity
        if identity['content_sha'] != plan['content_commit'] or \
                source_identity(ROOT, identity['files']) != plan['windows_source_identity'] or \
                sha256_json(protocol) != plan['comparison_protocol_hash']:
            raise ValueError('Independent audit execution identity differs')
        state = load(directory / 'checkpoint.json'); initial = load(directory / 'initial_checkpoint.json')
        if state['session_id'] != plan['session_id'] or initial['fingerprint'] != state['fingerprint'] or \
                initial['target_executions'] != 0 or initial['validation_groups'] or any(t['observations'] for t in initial['trajectories'].values()):
            raise ValueError('New empty session identity differs')
        sample_path = directory / 'samples.jsonl'
        samples = [json.loads(line) for line in sample_path.read_bytes().splitlines() if line] if sample_path.exists() else []
        by_id = {sample['run_id']: sample for sample in samples}
        if len(by_id) != len(samples): raise ValueError('Duplicate target run_id')
        if state['target_executions'] != len(samples): raise ValueError('Target execution counter differs')
        groups = [(dict(kind='validation', config=g['config']), g) for g in state['validation_groups']]
        space = ConfigSpace.load(ROOT / 'configs/config_space.json')
        for algorithm, own in state['trajectories'].items():
            replay(space, algorithm, own['observations'])
            if own['prefixes'] != prefixes(space, algorithm, own['observations']):
                raise ValueError('Prefix differs from own observations')
            candidates = {json.dumps(row['best_config'], sort_keys=True) for row in own['prefixes']}
            retests = [json.dumps(group['config'], sort_keys=True) for group in own['retests']]
            if len(set(retests)) != len(retests) or not set(retests) <= candidates:
                raise ValueError('Retest candidates not independently deduplicated within algorithm')
            mapping = [dict(row, retest_attempt=next((g['attempt_id'] for g in own['retests']
                if g['config'] == row['best_config']), None)) for row in own['prefixes']]
            if own['prefix_retest_mapping'] != mapping:
                raise ValueError('Prefix/retest mapping differs')
            groups += [(dict(kind=kind, algorithm=algorithm, config=g['config']), g)
                       for kind, records in (('search', own['observations']), ('retest', own['retests'])) for g in records]
        scored = set(); continuity_checks = []
        for job, group in groups:
            filename = directory / 'configurations' / (job['kind'] + '_' + group['attempt_id'] + '.json')
            original = load(filename)
            if sha256_file(filename) != group['measured_group_sha256'] or any(group.get(k) != v for k, v in original.items()):
                raise ValueError('Accepted group differs from original')
            continuity_checks.append(verify_group(plan, job, group['attempt_id'], group, group['checks_directory']))
            for sample in group['samples']:
                if by_id.get(sample['run_id']) != sample or sample['run_id'] in scored:
                    raise ValueError('Scored sample missing/reused')
                scored.add(sample['run_id'])
        for sample in samples:
            run = directory / 'runs' / Path(sample['run_directory']).name
            if any(sample.get(k) != v for k, v in load(run / 'result.json').items()):
                raise ValueError('Run record differs')
            for key, filename in (('raw_stdout', 'stdout.txt'), ('raw_stderr', 'stderr.txt')):
                if (run / filename).read_text() != sample[key]: raise ValueError('Run raw output differs')
            if sample['source'] != 'fresh_measurement' or sample['context']['force_remeasure'] is not True:
                raise ValueError('Nonfresh target sample')
        window_path = directory / 'window.json'; window = load(window_path) if window_path.exists() else None
        if window is not None:
            claim = load(directory / 'ACTIVITY.claim.json')
            if any(window[k] != claim[k] for k in ('qpc_start', 'qpc_frequency', 'budget_seconds', 'plan_sha256')):
                raise ValueError('Budget claim changed/reset')
            expected_budget = protocol['budget']['validation_activity_seconds' if plan['mode'] == 'validation' else 'proposed_first_seed_activity_seconds']
            if window['budget_seconds'] != expected_budget or window['plan_sha256'] != sha256_file(local_path(plan['plan_file'])) or \
                    any(type(window[k]) is not int or window[k] <= 0 for k in ('qpc_start','qpc_end','qpc_frequency')):
                raise ValueError('Invalid activity identity/endpoints/budget')
            cost = (window['qpc_end'] - window['qpc_start']) / window['qpc_frequency']
            if cost != window['activity_qpc_seconds'] or not 0 <= cost <= window['budget_seconds']:
                raise ValueError('QPC activity budget exceeded or inconsistent')
            power = load(directory / 'sleep_request.json')
            if not power['acquired'] or not power['released'] or power['thread_id'] != power['release_thread_id']:
                raise ValueError('Temporary sleep request not acquired/released on controller thread')
            result['activity_qpc_seconds'] = cost
        admission = require_certificate(plan) if (local_path(plan['recovery_directory']) / 'certificate.json').exists() else None
        complete = plan['mode'] == 'validation' and len(state['validation_groups']) == 3 and \
                   [g['config'] for g in state['validation_groups']] == protocol['validation_order'] and \
                   len(samples) == 18 and len(scored) == 18 and state['active'] is None
        search_complete = plan['mode'] == 'search' and state['active'] is None and all(
            len(own['observations']) == 12 and len(own['prefixes']) == 3 and
            all(row['retest_attempt'] is not None for row in own['prefix_retest_mapping'])
            for own in state['trajectories'].values())
        search_timing = search_complete and bool(admission and admission['recovery_eligible']) and bool(window and window['status'] == 'complete')
        result.update(evidence_integrity_pass=True, validation_complete=complete,
            validation_timing_checks_pass=complete and bool(admission and admission['recovery_eligible']),
            admission=admission, target_executions=len(samples), completed_groups=len(groups),
            completed_trajectories=sum(len(t['observations']) == 12 for t in state['trajectories'].values()),
            independent_retest_groups=sum(len(t['retests']) for t in state['trajectories'].values()),
            partial_target_samples=len(samples) - len(scored), continuity_checks=continuity_checks,
            execution_complete=search_complete, timing_checks_pass=search_timing, comparison_ready=search_complete and search_timing,
            stop_reason=window.get('failure_reason') if window else 'not invoked')
    except (ValueError, KeyError, TypeError, OSError, IndexError) as error:
        result['errors'].append(str(error))
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True); parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); result = audit(load(args.plan))
    atomic_write_json(args.output, result); print(json.dumps(result))
    raise SystemExit(0 if result['evidence_integrity_pass'] and result['validation_complete'] and result['validation_timing_checks_pass'] else 2)
