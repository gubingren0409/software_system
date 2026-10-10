"""Use capture and module CLI from the exact archive, not the worktree ROOT."""
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIRECTORY = HERE / 'final-content'
PLAN_PATH = DIRECTORY / 'plan.json'
PLAN = json.loads(PLAN_PATH.read_text(encoding='utf-8'))
ARCHIVE = Path(PLAN['windows_archive_directory'])
sys.path.insert(0, str(ARCHIVE))
from autotuner.core import sha256_file, utc_now
from scripts.p3_clock_contract import ROOT as CAPTURE_ROOT, atomic_write_json, capture, load


def main():
    if CAPTURE_ROOT.resolve() != ARCHIVE.resolve():
        raise ValueError('Auxiliary capture ROOT must be the frozen archive')
    for name in ('launch_result.json', 'continuation_result.json'):
        if load(DIRECTORY / name)['formal_invoked'] is not False:
            raise ValueError('Prior formal invocation exists; cannot retry')
    marker = DIRECTORY / 'frozen_cwd_manifest.json'
    if marker.exists():
        raise ValueError('This one-shot formal continuation already exists')
    commands = {
        'recovery_recompute_archive': [sys.executable, '-B', '-X', 'utf8', '-m',
            'scripts.raw_clock_contract', '--directory', PLAN['recovery_directory'],
            '--plan', str(PLAN_PATH), '--output', str(DIRECTORY / 'recovery_recomputed_archive.json')],
        'formal_grid': [sys.executable, '-B', '-X', 'utf8', '-m', 'scripts.start_raw_grid',
            '--plan', str(PLAN_PATH), 'run'],
        'grid_audit_archive': [sys.executable, '-B', '-X', 'utf8', '-m', 'scripts.audit_raw_grid',
            '--plan', str(PLAN_PATH), '--output', str(DIRECTORY / 'grid_audit_archive.json')],
    }
    atomic_write_json(marker, {'schema': 'raw-grid-auxiliary-frozen-cwd-v1',
        'created_at': utc_now(), 'helper_sha256': sha256_file(Path(__file__)),
        'pid': os.getpid(), 'capture_root': str(CAPTURE_ROOT), 'commands': commands,
        'content_commit': PLAN['content_commit'], 'session_id': PLAN['session_id'],
        'recovery_invocations': 0, 'formal_attempt_limit': 1,
        'reason': 'Prior readonly invocation imported worktree due to capture ROOT. Exact archived capture sets correct cwd; old failures retained.'})
    state = {'recovery_recomputed': False, 'formal_invoked': False,
             'formal_returncode': 'unknown', 'failure_reason': None}
    last = 0

    def progress():
        nonlocal last
        if time.perf_counter() - last < 60:
            return
        last = time.perf_counter()
        output = Path(PLAN['session_directory'])
        payload = {'at': utc_now(), 'process_state': 'captured child running'}
        for key, name in (('checkpoint', 'checkpoint.json'), ('target_progress', 'progress.json'),
                          ('host_progress', 'host_progress.json')):
            if (output / name).exists():
                item = load(output / name)
                if key == 'checkpoint':
                    item = {**{k: item.get(k) for k in ('status', 'active', 'target_executions', 'updated_at')},
                            'completed_count': len(item['completed'])}
                payload[key] = item
        atomic_write_json(DIRECTORY / 'frozen_cwd_progress.json', payload)
        print(json.dumps(payload), flush=True)

    def run(name, timeout):
        op = capture(commands[name], DIRECTORY, name, PLAN['session_id'], timeout=timeout, progress=progress)
        print(json.dumps({'operation': name, 'returncode': op['returncode'], 'qpc_seconds': op['qpc_seconds']}), flush=True)
        return op['returncode']

    try:
        code = run('recovery_recompute_archive', 60)
        checked = load(DIRECTORY / 'recovery_recomputed_archive.json')
        eligible = code == 0 and all(checked.get(k) is True for k in
            ('evidence_integrity_pass', 'clock_complete', 'raw_reference_pass', 'recovery_eligible')) \
            and checked.get('interval_count') == 12 and checked.get('response_count') == 50 and not checked['errors']
        state['recovery_recomputed'] = eligible
        if eligible:
            state['formal_invoked'] = True
            state['formal_returncode'] = run('formal_grid', 28830)
            if state['formal_returncode'] != 0:
                state['failure_reason'] = 'Formal Grid stopped; no retries authorized'
        else:
            state['failure_reason'] = 'Exact-archive independent recomputation rejected; no formal execution'
        state['grid_audit_returncode'] = run('grid_audit_archive', 180)
    except (ValueError, KeyError, OSError) as error:
        state['failure_reason'] = str(error)
    finally:
        state['ended_at'] = utc_now()
        atomic_write_json(DIRECTORY / 'frozen_cwd_result.json', state)
        print(json.dumps(state), flush=True)
    return 0 if state['formal_returncode'] == 0 and state['failure_reason'] is None else 2


if __name__ == '__main__':
    raise SystemExit(main())
