"""One explicitly authorized disk-failure continuation; frozen measurement stays untouched."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import shutil
import sys
import time
import uuid
from pathlib import Path

CONTENT = '35a60b090b728d2ec3b6a8ea014beac69fe3766d'
SESSION = '9332ead2881a4c1e91b966e90a0d2057'
OLD_SECONDS = 846.073676
TOTAL_SECONDS = 3600.
SELF = Path(__file__).resolve()
JOB = {'kind': 'validation', 'config': {'optimization': 'O3', 'block_size': 24}}
MUTABLE = {'checkpoint.json', 'samples.jsonl', 'progress.json'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def frozen(plan):
    root = Path(plan['windows_archive_directory']).resolve()
    sys.path.insert(0, str(root))
    f = importlib.import_module('scripts.start_raw_comparison')
    c = importlib.import_module('scripts.raw_comparison_contract')
    for name, module in tuple(sys.modules.items()):
        if (name == 'autotuner' or name.startswith('autotuner.') or name == 'scripts' or name.startswith('scripts.')) and getattr(module, '__file__', None):
            if not Path(module.__file__).resolve().is_relative_to(root):
                raise ValueError('Shadow import, not the exact 35a60b0 archive: ' + name)
    f.validate_plan(plan)
    return f, c


def check_start(plan, state, samples, window):
    if plan['content_commit'] != CONTENT or plan['session_id'] != SESSION or plan['mode'] != 'validation':
        raise ValueError('Wrong measurement content/session/mode')
    expected = [{'optimization': 'O3', 'block_size': s} for s in (128, 64)]
    if state['session_id'] != SESSION or state['active'] is not None or state['status'] != 'ready' or \
            [g['config'] for g in state['validation_groups']] != expected or state['target_executions'] != 12 or \
            len(samples) != 12 or len({r['run_id'] for r in samples}) != 12 or \
            any(t['observations'] or t['retests'] for t in state['trajectories'].values()):
        raise ValueError('Expected exactly two accepted groups / twelve unique runs / no active group')
    for key in ('qpc_start', 'qpc_end', 'qpc_frequency'):
        if type(window[key]) is not int or window[key] <= 0:
            raise ValueError('Invalid previous QPC endpoint')
    used = (window['qpc_end'] - window['qpc_start']) / window['qpc_frequency']
    if window['status'] != 'stopped' or window['budget_seconds'] != TOTAL_SECONDS or used != OLD_SECONDS or \
            window['activity_qpc_seconds'] != used:
        raise ValueError('Previous window is not the preserved disk-failure window')
    return TOTAL_SECONDS - used


def check_prefix(path, expected_bytes, expected_sha):
    with Path(path).open('rb') as stream:
        prefix = stream.read(expected_bytes)
    if len(prefix) != expected_bytes or hashlib.sha256(prefix).hexdigest() != expected_sha:
        raise ValueError('Original sample byte prefix changed')


def cumulative(old_seconds, window):
    if any(type(window[k]) is not int or window[k] <= 0 for k in ('qpc_start', 'qpc_end', 'qpc_frequency')):
        raise ValueError('Invalid continuation QPC endpoints')
    elapsed = (window['qpc_end'] - window['qpc_start']) / window['qpc_frequency']
    if elapsed < 0 or old_seconds != OLD_SECONDS or old_seconds + elapsed > TOTAL_SECONDS:
        raise ValueError('Remaining allowance exceeded; no reset or third window')
    # Sum individually measured durations, never absolute endpoints from different epochs.
    return old_seconds + elapsed


def evidence_preflight(directory, minimum=1024**3):
    directory = Path(directory)
    free = shutil.disk_usage(directory).free
    if free < minimum:
        raise ValueError('Evidence volume free space below 1 GiB: ' + str(free))
    probe = directory / ('write-probe-' + uuid.uuid4().hex + '.txt')
    value = b'owned evidence-volume write/fsync/read-back probe\n'
    with probe.open('xb') as stream:
        stream.write(value); stream.flush(); os.fsync(stream.fileno())
    if probe.read_bytes() != value:
        raise ValueError('Evidence volume read-back differs')
    return {'free_bytes': free, 'minimum_free_bytes': minimum, 'write_probe': str(probe), 'sha256': digest(probe)}


def verify_preserved(auth, completed=False):
    session = Path(auth['session_directory'])
    for name, expected in auth['protected_session_files'].items():
        if digest(session / name) != expected:
            raise ValueError('Protected session evidence changed: ' + name)
    for name, expected in auth['protected_history_files'].items():
        if digest(Path(auth['repository_directory']) / name) != expected:
            raise ValueError('Historical evidence changed: ' + name)
    check_prefix(session / 'samples.jsonl', auth['samples_prefix_bytes'], auth['samples_prefix_sha256'])
    state = read(session / 'checkpoint.json'); previous = read(Path(auth['directory']) / 'preserved/checkpoint.json')
    if state['validation_groups'][:2] != previous['validation_groups'] or \
            any(state[k] != previous[k] for k in ('fingerprint', 'artifacts', 'setup_raw_seconds', 'reference_generation_calls', 'trajectories')):
        raise ValueError('Accepted groups, setup, identity or empty search observations changed')
    if not completed and digest(session / 'checkpoint.json') != auth['checkpoint_sha256']:
        raise ValueError('Checkpoint changed before continuation admission')
    return state


def verify_auth(auth):
    if auth['schema'] != 'raw-validation-disk-continuation-v1' or auth['content_commit'] != CONTENT or \
            auth['session_id'] != SESSION or auth['previous_activity_qpc_seconds'] != OLD_SECONDS or \
            auth['remaining_allowance_seconds'] != TOTAL_SECONDS - OLD_SECONDS or auth['only_job'] != JOB or \
            auth['helper_sha256'] != digest(SELF) or auth['helper_file'] != str(SELF):
        raise ValueError('Continuation authorization/helper identity differs')
    if digest(auth['plan_file']) != auth['plan_sha256']:
        raise ValueError('Original plan changed')


def prepare(plan_path, directory, auxiliary_sha):
    plan_path = plan_path.resolve(); directory = directory.resolve()
    if directory.exists(): raise ValueError('New unique continuation directory required')
    plan = read(plan_path); f, c = frozen(plan); session = f.local_path(plan['session_directory'])
    state = read(session / 'checkpoint.json'); sample_path = session / 'samples.jsonl'
    rows = [json.loads(line) for line in sample_path.read_bytes().splitlines() if line]
    remaining = check_start(plan, state, rows, read(session / 'window.json'))
    old_audit = c.audit(plan)
    if not old_audit['evidence_integrity_pass'] or old_audit['completed_groups'] != 2 or old_audit['partial_target_samples']:
        raise ValueError('Existing accepted evidence failed independent audit')
    if not len(auxiliary_sha) == 40 or any(c not in '0123456789abcdef' for c in auxiliary_sha):
        raise ValueError('Full auxiliary content commit required')
    directory.mkdir(parents=True); preserved = directory / 'preserved'; preserved.mkdir()
    for name in ('checkpoint.json', 'samples.jsonl', 'window.json', 'ACTIVITY.claim.json', 'initial_checkpoint.json'):
        shutil.copy2(session / name, preserved / name)
    repo = plan_path.parents[3]
    protected = {p.relative_to(session).as_posix(): digest(p) for p in session.rglob('*')
                 if p.is_file() and p.relative_to(session).as_posix() not in MUTABLE}
    history = {p.relative_to(repo).as_posix(): digest(p) for p in (repo / 'evidence').rglob('*')
               if p.is_file() and not p.is_relative_to(session) and not p.is_relative_to(directory.parent)}
    auth = {'schema': 'raw-validation-disk-continuation-v1', 'authorized_by': 'User: E disk space released; complete the disk-interrupted validation only',
        'scope': 'One continuation of O3/s24, no repeat of accepted groups, no search, no allowance reset',
        'content_commit': CONTENT, 'session_id': SESSION, 'auxiliary_content_commit': auxiliary_sha,
        'helper_file': str(SELF), 'helper_sha256': digest(SELF), 'directory': str(directory),
        'repository_directory': str(repo), 'session_directory': str(session), 'plan_file': str(plan_path),
        'plan_sha256': digest(plan_path), 'checkpoint_sha256': digest(session / 'checkpoint.json'),
        'samples_prefix_bytes': sample_path.stat().st_size, 'samples_prefix_sha256': digest(sample_path),
        'original_run_ids': [r['run_id'] for r in rows], 'protected_session_files': protected,
        'protected_history_files': history, 'previous_activity_qpc_seconds': OLD_SECONDS,
        'remaining_allowance_seconds': remaining, 'total_allowance_seconds': TOTAL_SECONDS, 'only_job': JOB,
        'start_index': 2, 'stop_index': 3, 'skip_setup': True, 'performance_cache_allowed': False,
        'fresh_admission': 'One short 1e9 then one long 1e10 default-libc/unbound attachment; original certificate untouched',
        'activity_scope': 'New admission resource gate through cleanup. Add to prior 846.073676 s; off-line review/preparation separate',
        'evidence_volume_preflight': 'External scheduling safeguard only; >=1 GiB free plus fsync/read-back. Scientific resource v2 unchanged'}
    f.atomic_write_json(directory / 'previous_independent_audit.json', old_audit)
    f.claim(directory / 'authorization.json', auth)
    print(json.dumps({'authorization': str(directory / 'authorization.json'), 'protected_session_files': len(protected),
        'protected_history_files': len(history), 'remaining_allowance_seconds': remaining}), flush=True)


def run(auth_path):
    auth = read(auth_path); verify_auth(auth)
    plan = read(auth['plan_file']); f, c = frozen(plan); output = Path(auth['directory']); session = Path(auth['session_directory'])
    state = verify_preserved(auth)
    check_start(plan, state, [json.loads(s) for s in (session / 'samples.jsonl').read_bytes().splitlines()], read(session / 'window.json'))
    c.require_certificate(plan)
    started, hz = f.qpc(); budget = auth['remaining_allowance_seconds']
    window = {'schema': auth['schema'], 'content_commit': CONTENT, 'session_id': SESSION,
        'authorization_sha256': digest(auth_path), 'qpc_start': started, 'qpc_frequency': hz, 'controller_pid': os.getpid(),
        'budget_seconds': budget, 'phase': 'preflight', 'status': 'running', 'failure_reason': None}
    f.claim(session / 'DISK_CONTINUATION_V1.claim.json', window)
    deadline = time.perf_counter() + budget - 15; last = -60.
    def progress(force=False):
        nonlocal last
        now, frequency = f.qpc()
        if frequency != hz: raise ValueError('QPC frequency changed')
        elapsed = (now - started) / hz
        if not force and elapsed - last < 60: return
        last = elapsed; checkpoint = read(session / 'checkpoint.json')
        value = {**window, 'at': f.utc_now(), 'activity_qpc_seconds': elapsed,
            'cumulative_activity_qpc_seconds': OLD_SECONDS + elapsed, 'remaining_budget_seconds': max(0, budget - elapsed),
            'completed_groups': len(checkpoint['validation_groups']), 'target_executions': checkpoint['target_executions'],
            'active': checkpoint['active'], 'sample_progress': read(session / 'progress.json') if (session / 'progress.json').exists() else None}
        f.atomic_write_json(output / 'progress.json', value); print(json.dumps(value), flush=True)
    try:
        with f.SleepRequest(output / 'sleep_request.json'):
            f.atomic_write_json(output / 'evidence_volume_preflight.json', evidence_preflight(session))
            power = f.PowerEvents(output / 'power_events'); power.read()
            operation = f.capture([sys.executable, '-B', '-X', 'utf8', '-c',
                'import ctypes,json; s=type("S",(ctypes.Structure,),{"_fields_":[("ac",ctypes.c_ubyte),("flag",ctypes.c_ubyte),("pct",ctypes.c_ubyte),("reserved",ctypes.c_ubyte),("life",ctypes.c_uint32),("full",ctypes.c_uint32)]})(); ok=ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(s)); print(json.dumps({"ok":bool(ok),"ac":s.ac,"battery_percent":s.pct})); raise SystemExit(0 if ok and s.ac==1 else 2)'],
                output, 'ac_status', 'disk-continuation', timeout=15)
            if operation['returncode'] != 0 or operation['timed_out']: raise ValueError('AC power required; keep lid open')
            context = {'content_commit': CONTENT, 'session_id': SESSION, 'comparison_protocol_hash': plan['comparison_protocol_hash'],
                'continuation_authorization_sha256': digest(auth_path), 'starting_checkpoint_sha256': auth['checkpoint_sha256']}
            window['phase'] = 'formal_preflight'; progress(True)
            if not f.gate(plan, output / 'admission_resources', 'Formal', context, deadline): raise ValueError('Formal resource preflight refused')
            window['phase'] = 'fresh_continuation_admission'; progress(True)
            f.clock_check(plan, output / 'admission', 'admission', context, min(deadline, time.perf_counter() + 120))
            checked = f.audit_clock(output / 'admission', context)
            if not checked['clock_complete'] or not checked['raw_reference_pass'] or not checked['evidence_integrity_pass'] or checked['errors']:
                raise ValueError('Current continuation admission failed')
            verify_preserved(auth)
            # Verify real Linux sources/compiler/cache hashes without setup, build, reference generation or target invocation.
            code = 'import json,sys; from pathlib import Path; from autotuner.raw_comparison import opened; from autotuner.core import sha256_file; p=json.load(open(sys.argv[1])); o,pr,m,t,s=opened(p); assert s["artifacts"]==p["expected_artifacts"]; [(None if sha256_file(Path(n))==h else (_ for _ in ()).throw(ValueError("Cache changed: "+n))) for n,h in p["verified_cache_files"].items()]; print(json.dumps({"verified":True,"setup_invoked":False,"reference_generation_calls":s["reference_generation_calls"]}))'
            operation = f.capture(f.linux(plan, ['python3', '-c', code, f.wsl_path(auth['plan_file'])]), output, 'verified_cache_reuse', 'disk-continuation', timeout=60)
            if operation['returncode'] != 0 or operation['timed_out']: raise ValueError('Runtime/source/compiler/cache identity failed')
            if (session / 'PAUSE_REQUEST').exists(): raise ValueError('Pause request present; marker preserved')
            if f.next_job(read(session / 'checkpoint.json'), f.ConfigSpace.load(f.ROOT / 'configs/config_space.json'), f.comparison_protocol()) != JOB:
                raise ValueError('Only O3/s24 is authorized')
            attempt = uuid.uuid4().hex; checks = session / 'group_checks' / attempt; checks.mkdir()
            window.update(attempt_id=attempt, checks_directory=str(checks), phase='group_resources'); progress(True)
            job_context = f.job_context(plan, JOB, attempt)
            f.atomic_write_json(output / 'evidence_volume_before_group.json', evidence_preflight(session))
            if not f.gate(plan, checks / 'resources', 'Formal', job_context, deadline): raise ValueError('Group Formal gate refused')
            window['phase'] = 'before_clock'; progress(True)
            f.clock_check(plan, checks / 'before', 'before', {**job_context, 'phase': 'before'}, deadline)
            window['phase'] = 'evaluation'; progress(True)
            f.measure(plan, Path(auth['plan_file']), JOB, attempt, checks, deadline, progress)
            group = session / 'configurations' / ('validation_' + attempt + '.json')
            window['phase'] = 'after_clock'; progress(True)
            f.clock_check(plan, checks / 'after', 'after', {**job_context, 'phase': 'after', 'group_sha256': digest(group)}, deadline)
            operation = f.capture(f.linux(plan, ['python3', '-m', 'autotuner.raw_comparison', '--plan',
                f.wsl_path(auth['plan_file']), 'accept', '--attempt-id', attempt, '--checks-directory', f.wsl_path(checks)]),
                output, 'accept', 'disk-continuation', timeout=min(60, max(.001, deadline - time.perf_counter())))
            if operation['returncode'] != 0 or operation['timed_out']: raise ValueError('Frozen group acceptance failed')
            verify_preserved(auth, completed=True)
            power.read(); window.update(status='complete', phase='cleanup')
    except (ValueError, KeyError, TypeError, OSError, TimeoutError, KeyboardInterrupt) as error:
        window.update(status='stopped', failure_reason=str(error))
        # Do not rewrite history or mark a failed/partial group complete. The outer record is authoritative.
    finally:
        ended, end_hz = f.qpc(); window.update(qpc_end=ended, ended_at=f.utc_now(), activity_qpc_seconds=(ended-started)/hz)
        window['budget_pass'] = end_hz == hz and OLD_SECONDS + window['activity_qpc_seconds'] <= TOTAL_SECONDS
        window['cumulative_activity_qpc_seconds'] = OLD_SECONDS + window['activity_qpc_seconds']
        f.atomic_write_json(output / 'window.json', window); progress(True)
    return 0 if window['status'] == 'complete' and window['budget_pass'] else 2


def audit(auth_path):
    auth = read(auth_path); verify_auth(auth); plan = read(auth['plan_file']); f, c = frozen(plan)
    output = Path(auth['directory']); session = Path(auth['session_directory'])
    result = {'evidence_integrity_pass': False, 'validation_complete': False, 'validation_timing_checks_pass': False,
        'execution_complete': False, 'timing_checks_pass': False, 'comparison_ready': False, 'errors': []}
    try:
        state = verify_preserved(auth, completed=True); window = read(output / 'window.json')
        claim = read(session / 'DISK_CONTINUATION_V1.claim.json')
        if any(claim[k] != window[k] for k in ('authorization_sha256', 'qpc_start', 'qpc_frequency', 'budget_seconds')) or \
                window['authorization_sha256'] != digest(auth_path) or window['budget_seconds'] != auth['remaining_allowance_seconds']:
            raise ValueError('Continuation budget claim changed')
        total = cumulative(OLD_SECONDS, window)
        if total != window['cumulative_activity_qpc_seconds']: raise ValueError('Cumulative cost differs')
        power = read(output / 'sleep_request.json')
        if not power['acquired'] or not power['released'] or power['thread_id'] != power['release_thread_id']:
            raise ValueError('Sleep request not acquired/released')
        base = c.audit(plan); f.atomic_write_json(output / 'base_independent_audit.json', base)
        if not base['evidence_integrity_pass']: raise ValueError('Frozen evidence audit failed: ' + str(base['errors']))
        context = {'content_commit': CONTENT, 'session_id': SESSION, 'comparison_protocol_hash': plan['comparison_protocol_hash'],
            'continuation_authorization_sha256': digest(auth_path), 'starting_checkpoint_sha256': auth['checkpoint_sha256']}
        from scripts.raw_clock_contract import audit_gate
        admitted = audit_gate(output / 'admission_resources', read(f.ROOT / 'configs/measurement_protocol.json'), 'Formal', context)
        clock = f.audit_clock(output / 'admission', context)
        f.atomic_write_json(output / 'independent_continuation_admission.json', clock)
        complete = base['validation_complete'] and len(state['validation_groups']) == 3 and state['validation_groups'][2]['attempt_id'] == window.get('attempt_id')
        timing = complete and admitted and clock['clock_complete'] and clock['evidence_integrity_pass'] and clock['raw_reference_pass'] and not clock['errors']
        if complete and window['status'] != 'complete': timing = False
        result.update(evidence_integrity_pass=True, validation_complete=complete, validation_timing_checks_pass=bool(timing),
            formal_resource_pass=admitted, fresh_admission_pass=clock['raw_reference_pass'],
            target_executions=base['target_executions'], completed_groups=base['completed_groups'],
            partial_target_samples=base['partial_target_samples'], original_runs_preserved=len(auth['original_run_ids']),
            protected_session_files=len(auth['protected_session_files']), protected_history_files=len(auth['protected_history_files']),
            previous_activity_qpc_seconds=OLD_SECONDS, continuation_activity_qpc_seconds=window['activity_qpc_seconds'],
            cumulative_activity_qpc_seconds=total, failure_reason=window['failure_reason'])
    except (ValueError, KeyError, TypeError, OSError) as error:
        result['errors'].append(str(error))
    f.atomic_write_json(output / 'independent_continuation_audit.json', result)
    print(json.dumps(result), flush=True)
    return 0 if result['evidence_integrity_pass'] and result['validation_complete'] and result['validation_timing_checks_pass'] else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare', 'run', 'audit'))
    parser.add_argument('--plan', type=Path); parser.add_argument('--output', type=Path)
    parser.add_argument('--auxiliary-sha'); parser.add_argument('--authorization', type=Path)
    args = parser.parse_args()
    if args.mode == 'prepare': prepare(args.plan, args.output, args.auxiliary_sha)
    elif args.mode == 'run': raise SystemExit(run(args.authorization))
    else: raise SystemExit(audit(args.authorization))
