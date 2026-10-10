"""Correct only auxiliary CLI invocation; never repeat recovery or modify runtime content."""
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from autotuner.core import sha256_file, utc_now
from scripts.p3_clock_contract import atomic_write_json, capture, load


def main():
    directory = HERE / 'final-content'
    plan_path = directory / 'plan.json'
    plan = load(plan_path)
    previous = load(directory / 'launch_result.json')
    if previous['formal_invoked'] is not False or previous['recovery_returncode'] != 0:
        raise ValueError('Not the audited auxiliary-only interruption')
    marker = directory / 'continuation_manifest.json'
    if marker.exists():
        raise ValueError('Formal continuation already attempted; no automatic retries')
    archive = Path(plan['windows_archive_directory'])
    os.chdir(archive)
    os.environ.pop('PYTHONPATH', None)
    commands = {
        'recovery_recompute_cli': [sys.executable, '-B', '-X', 'utf8', '-m',
            'scripts.raw_clock_contract', '--directory', plan['recovery_directory'],
            '--plan', str(plan_path), '--output', str(directory / 'recovery_recomputed.json')],
        'formal_grid': [sys.executable, '-B', '-X', 'utf8', '-m', 'scripts.start_raw_grid',
            '--plan', str(plan_path), 'run'],
        'grid_independent': [sys.executable, '-B', '-X', 'utf8', '-m', 'scripts.audit_raw_grid',
            '--plan', str(plan_path), '--output', str(directory / 'grid_independent_audit.json')],
    }
    atomic_write_json(marker, {
        'schema': 'raw-grid-auxiliary-command-correction-v1', 'created_at': utc_now(),
        'helper_sha256': sha256_file(Path(__file__)), 'pid': os.getpid(),
        'prior_launch_result_sha256': sha256_file(directory / 'launch_result.json'),
        'content_commit': plan['content_commit'], 'session_id': plan['session_id'],
        'archive_cwd': str(archive), 'pythonpath_present': 'PYTHONPATH' in os.environ,
        'commands': commands, 'recovery_invocations': 0, 'formal_attempt_limit': 1,
        'reason': 'Direct script invocation omitted package root. Use Python module invocation from exact archive; no runtime source changes or data recollection.',
    })
    state = {'recovery_recomputed': False, 'formal_invoked': False,
        'formal_returncode': 'unknown', 'failure_reason': None}
    last = 0

    def progress():
        nonlocal last
        if time.perf_counter() - last < 60:
            return
        last = time.perf_counter()
        payload = {'at': utc_now(), 'phase': 'formal' if state['formal_invoked'] else 'independent_recompute'}
        session = Path(plan['session_directory'])
        for key, path in (('checkpoint', session / 'checkpoint.json'),
                          ('target_progress', session / 'progress.json'),
                          ('host_progress', session / 'host_progress.json')):
            if path.exists():
                item = load(path)
                if key == 'checkpoint':
                    item = {k: item.get(k) for k in ('status', 'active', 'target_executions', 'updated_at')}
                    item['completed_count'] = len(load(path)['completed'])
                payload[key] = item
        atomic_write_json(directory / 'continuation_progress.json', payload)
        print(json.dumps(payload), flush=True)

    def run(name, timeout):
        operation = capture(commands[name], directory, name, plan['session_id'],
                            timeout=timeout, progress=progress)
        print(json.dumps({'operation': name, 'returncode': operation['returncode'],
                         'qpc_seconds': operation['qpc_seconds']}), flush=True)
        return operation['returncode']

    try:
        code = run('recovery_recompute_cli', 60)
        checked = load(directory / 'recovery_recomputed.json')
        eligible = code == 0 and all(checked.get(k) is True for k in
            ('evidence_integrity_pass', 'clock_complete', 'raw_reference_pass', 'recovery_eligible')) \
            and checked.get('interval_count') == 12 and checked.get('response_count') == 50 \
            and not checked['errors']
        state['recovery_recomputed'] = eligible
        if eligible:
            state['formal_invoked'] = True
            state['formal_returncode'] = run('formal_grid', 28830)
            if state['formal_returncode'] != 0:
                state['failure_reason'] = 'Formal Grid stopped; preserve checkpoint and do not retry'
        else:
            state['failure_reason'] = 'Independent recovery recomputation rejected; no formal invocation'
        state['grid_audit_returncode'] = run('grid_independent', 180)
    except (ValueError, KeyError, OSError) as error:
        state['failure_reason'] = str(error)
    finally:
        state['ended_at'] = utc_now()
        atomic_write_json(directory / 'continuation_result.json', state)
        print(json.dumps(state), flush=True)
    return 0 if state['formal_returncode'] == 0 and state['failure_reason'] is None else 2


if __name__ == '__main__':
    raise SystemExit(main())
