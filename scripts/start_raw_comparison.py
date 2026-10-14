"""Windows-only new RAW validation/search controller with explicit independent identity."""
from __future__ import annotations

import argparse
import json
import os
import queue
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autotuner.core import ConfigSpace, sha256_file, sha256_json, utc_now
from autotuner.raw_comparison import comparison_protocol, next_job, job_context
from scripts.p3_clock_contract import atomic_write_json, capture, load, qpc, wsl_path
from scripts.raw_clock_contract import local_path, audit_clock, manifest_schedule
from scripts.raw_comparison_contract import audit_admission, certificate_value, continuity
from scripts.raw_comparison_power import SleepRequest, PowerEvents, standby_events
from scripts.start_raw_grid import linux, gate, validate_plan as validate_base


def validate_plan(plan):
    validate_base(plan)
    protocol = comparison_protocol()
    if plan['schema'] != 'raw-comparison-plan-v1' or sha256_json(protocol) != plan['comparison_protocol_hash'] or \
            plan['mode'] not in ('validation', 'search') or \
            plan['measurement_content'] != protocol['inherited_measurement_content']:
        raise ValueError('Comparison plan authorization differs')
    initial = load(local_path(plan['session_directory']) / 'initial_checkpoint.json')
    if initial['session_id'] != plan['session_id'] or initial['mode'] != plan['mode'] or \
            initial['fingerprint']['content_commit'] != plan['content_commit'] or \
            initial['fingerprint']['comparison_protocol_hash'] != plan['comparison_protocol_hash']:
        raise ValueError('Wrong session/content/protocol')
    return protocol


def claim(path, value):
    # A process restart must not silently buy another activity window.
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.flush(); os.fsync(stream.fileno())


def clock_check(plan, directory, purpose, context, deadline):
    directory.mkdir(parents=True, exist_ok=False)
    build = load(local_path(plan['probe_build_manifest']))
    protocol = comparison_protocol(); timing = load(ROOT / 'configs/raw_formal_timing_protocol.json')
    budget = protocol['admission']['collection_budget_seconds'] if purpose == 'admission' else 60
    binary = build['binary']
    wrapper = 'import hashlib,os; p=' + repr(binary) + '; assert hashlib.sha256(open(p,"rb").read()).hexdigest()==' + repr(build['binary_sha256']) + '; os.execv(p,[p])'
    manifest = {'schema': 'raw-comparison-clock-manifest-v1', 'batch_id': directory.name,
        'declared_at': utc_now(), 'purpose': purpose, 'context': context,
        'comparison_protocol_hash': plan['comparison_protocol_hash'],
        'timing_version': timing['version'], 'timing_protocol_hash': plan['timing_protocol_hash'],
        'measurement_protocol_hash': plan['measurement_protocol_hash'],
        'resource_policy_hash': protocol['resource_policy_hash'], 'criteria': timing['admission'],
        'collection_budget_seconds': budget, 'cpu_selection': {'selected_cpu': -1, 'allowed_cpus': plan['allowed_cpus']},
        'git_files': load(local_path(plan['git_identity']))['files'],
        'source_sha256': {name: value['executed_sha256'] for name, value in plan['windows_source_identity'].items()},
        'probe_binary': binary, 'binary_sha256': build['binary_sha256'], 'probe_build': build,
        'probe_command': linux(plan, ['timeout', '--signal=TERM', '--kill-after=5', str(budget - 5), 'python3', '-c', wrapper]),
        'stop_rule': 'No replacement/retry/filtering/calibration; any failed or indeterminate interval stops'}
    manifest['schedule'] = manifest_schedule(manifest)
    manifest['interval_count'] = len(manifest['schedule'])
    atomic_write_json(directory / 'manifest.json', manifest)
    from scripts.run_fixed_work_clock import collect
    code = collect(directory, formal=True, deadline=deadline)
    result = audit_clock(directory, context)
    atomic_write_json(directory / 'independent_check.json', result)
    if code != 0 or not result['evidence_integrity_pass'] or not result['raw_reference_pass'] or result['errors']:
        raise ValueError(purpose + ' RAW check failed: ' + json.dumps(result))
    return result


def measure(plan, plan_path, job, attempt, checks, deadline, progress):
    """QPC starts only after READY, before RUN; ends immediately on FINISHED receipt."""
    command = linux(plan, ['timeout', '--signal=TERM', '--kill-after=10', str(max(1, deadline - time.perf_counter() - 5)),
        'python3', '-m', 'autotuner.raw_comparison', '--plan', wsl_path(plan_path), 'measure',
        '--attempt-id', attempt, '--checks-directory', wsl_path(checks)])
    events = PowerEvents(checks / 'power_events')
    baseline = events.read(); cursor = events.cursor
    received = queue.Queue(); child = None; threads = []; finished = None; ready = None
    host = None; timed_out = False; errors = []; observations = []; event_names = []
    output = (checks / 'measure.stdout.txt').open('wb'); error = (checks / 'measure.stderr.txt').open('wb')
    process_start, frequency = qpc(); rc = 'unknown'
    def read_output():
        for line in iter(child.stdout.readline, b''):
            stamp, hz = qpc()  # Stamp before parsing and file IO.
            output.write(line); output.flush(); received.put((stamp, hz, line))
        received.put(None)
    def read_error():
        for line in iter(child.stderr.readline, b''): error.write(line); error.flush()
    def poll_events():
        value = events.read(); event_names.append(value['operation_name']); observations.append(value['record'])
        if standby_events(observations): raise ValueError('Standby during evaluation; preserve disturbed group and stop')
    try:
        env = os.environ.copy(); env.pop('PYTHONPATH', None); env['PYTHONDONTWRITEBYTECODE'] = '1'
        child = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=ROOT, env=env, creationflags=subprocess.CREATE_NO_WINDOW)
        threads = [threading.Thread(target=read_output, daemon=True), threading.Thread(target=read_error, daemon=True)]
        for thread in threads: thread.start()
        last_poll = time.perf_counter()
        while time.perf_counter() < deadline:
            progress()
            try: item = received.get(timeout=min(1, max(.001, deadline - time.perf_counter())))
            except queue.Empty:
                if host and time.perf_counter() - last_poll >= 30:
                    poll_events(); last_poll = time.perf_counter()
                continue
            if item is None: break
            stamp, hz, line = item
            if hz != frequency: raise ValueError('QPC frequency changed')
            message = json.loads(line)
            if message.get('event') == 'READY':
                if ready is not None or message['job'] != job or message['attempt_id'] != attempt:
                    raise ValueError('Wrong or duplicate READY identity')
                ready = message
                progress(True)  # Complete file IO BEFORE tightly stamped request.
                start, hz = qpc(); request = 'RUN ' + attempt + '\n'
                child.stdin.write(request.encode('ascii')); child.stdin.flush()
                host = {'start_qpc': start, 'qpc_frequency': hz, 'command': request,
                        'ready_recv_qpc': stamp, 'command_argv': command}
            elif message.get('event') == 'FINISHED':
                if not host or finished is not None: raise ValueError('FINISHED out of order')
                host['end_qpc'] = stamp
                finished = {k: v for k, v in message.items() if k != 'event'}
                break
        if finished is None:
            timed_out = time.perf_counter() >= deadline
            raise ValueError('Evaluation did not finish; timeout=' + str(timed_out))
        rc = child.wait(timeout=max(.001, min(10, deadline - time.perf_counter())))
        poll_events()
        if rc != 0: raise ValueError('Evaluation returned ' + str(rc))
        checked = continuity(finished, host, observations)
        if not checked['uninterrupted_execution']:
            raise ValueError('QPC/RAW evaluation envelope mismatch')
    except (OSError, ValueError, KeyError, TypeError, TimeoutError, subprocess.TimeoutExpired) as failure:
        errors.append(str(failure))
    finally:
        if child is not None and child.poll() is None:
            if ready is not None:
                cleanup = capture(linux(plan, ['kill', '-TERM', str(ready['pid'])]), checks, 'owned_runner_stop',
                                  'raw-comparison', timeout=5)
            try: rc = child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.terminate()
                try: rc = child.wait(timeout=3)
                except subprocess.TimeoutExpired: errors.append('Owned process exit unknown')
        elif child is not None: rc = child.returncode
        for thread in threads: thread.join(timeout=2)
        output.close(); error.close()
        record = {'schema': 'raw-comparison-continuity-v1', 'context': job_context(plan, job, attempt),
            'scope': finished, 'host': host, 'event_cursor_before': cursor, 'event_cursor_after': events.cursor,
            'baseline_operation': baseline['operation_name'], 'event_operations': event_names,
            'returncode': rc, 'timed_out': timed_out, 'errors': errors, 'host_pid': None if child is None else child.pid,
            'stdout_sha256': sha256_file(checks / 'measure.stdout.txt'), 'stderr_sha256': sha256_file(checks / 'measure.stderr.txt'),
            'process_start_qpc': process_start, 'process_end_qpc': qpc()[0], 'qpc_frequency': frequency,
            'result': continuity(finished, host, observations) if finished and host and 'end_qpc' in host else None}
        atomic_write_json(checks / 'continuity.json', record)
    if errors: raise ValueError('; '.join(errors))
    return record


def run(plan, plan_path, search_authorization=None):
    protocol = validate_plan(plan)
    output = local_path(plan['session_directory'])
    state = load(output / 'checkpoint.json')
    if state['active'] or state['validation_groups'] or any(t['observations'] for t in state['trajectories'].values()):
        raise ValueError('This first-window entry requires its initialized empty session; no silent retry')
    if plan['mode'] == 'search':
        expected = {'schema': 'raw-comparison-search-authorization-v1', 'content_commit': plan['content_commit'],
            'session_id': plan['session_id'], 'comparison_protocol_hash': plan['comparison_protocol_hash'],
            'scope': 'first-seed-random-greedy-12-with-prefix-retests', 'budget_seconds': 43200}
        if search_authorization is None or load(search_authorization) != expected:
            raise ValueError('Real search requires separately reviewed explicit authorization; not authorized this stage')
    budget = protocol['budget']['validation_activity_seconds' if plan['mode'] == 'validation' else 'proposed_first_seed_activity_seconds']
    started, frequency = qpc()
    window = {'schema': 'raw-comparison-activity-v1', 'content_commit': plan['content_commit'], 'session_id': plan['session_id'],
        'qpc_start': started, 'qpc_frequency': frequency, 'budget_seconds': budget, 'plan_sha256': sha256_file(plan_path),
        'phase': 'admission_resource_gate', 'status': 'running', 'failure_reason': None, 'controller_pid': os.getpid()}
    claim(output / 'ACTIVITY.claim.json', window)
    atomic_write_json(output / 'window.json', window)
    deadline = time.perf_counter() + budget - protocol['budget']['cleanup_reserve_seconds']
    last = 0
    def progress(force=False):
        nonlocal last
        now, hz = qpc()
        if hz != frequency: raise ValueError('QPC frequency changed')
        used = (now - started) / frequency
        if not force and used - last < 60: return
        last = used; checkpoint = load(output / 'checkpoint.json')
        payload = {'at': utc_now(), 'phase': window['phase'], 'active': checkpoint['active'],
            'validation_complete': len(checkpoint['validation_groups']),
            'search_complete': {k: len(v['observations']) for k, v in checkpoint['trajectories'].items()},
            'sample_progress': load(output / 'progress.json') if (output / 'progress.json').exists() else None,
            'activity_qpc_seconds': used, 'remaining_budget_seconds': max(0, budget - used), 'controller_pid': os.getpid()}
        atomic_write_json(output / 'controller_progress.json', payload); print(json.dumps(payload), flush=True)
    def operation(mode, attempt=None, checks=None):
        argv = ['python3', '-m', 'autotuner.raw_comparison', '--plan', wsl_path(plan_path), mode]
        if attempt is not None: argv += ['--attempt-id', attempt, '--checks-directory', wsl_path(checks)]
        seconds = deadline - time.perf_counter()
        if seconds <= 5: raise TimeoutError('Activity budget exhausted')
        result = capture(linux(plan, ['timeout', '--signal=TERM', '--kill-after=5', str(max(1, seconds - 5)), *argv]),
                         output / 'operations', mode + ('_' + attempt if attempt else ''), 'raw-comparison',
                         timeout=seconds, progress=progress)
        if result['returncode'] != 0 or result['timed_out']: raise ValueError(mode + ' failed: ' + str(result['returncode']))
    try:
        with SleepRequest(output / 'sleep_request.json'):
            power = PowerEvents(output / 'power_events'); initial_power = power.read()
            atomic_write_json(output / 'power_event_start.json', initial_power)
            # Read-only metadata, no global power changes. AC is checked once;
            # the user must keep the lid open throughout the activity.
            from ctypes import Structure, c_ubyte, c_uint32, WinDLL, byref
            class Status(Structure):
                _fields_ = [('ac', c_ubyte), ('battery_flag', c_ubyte), ('battery_percent', c_ubyte),
                            ('system_status', c_ubyte), ('life', c_uint32), ('full_life', c_uint32)]
            status = Status(); ok = WinDLL('kernel32').GetSystemPowerStatus(byref(status))
            atomic_write_json(output / 'ac_status.json', {'api_success': bool(ok), 'ac_line_status': status.ac,
                'battery_percent': status.battery_percent, 'limitation': 'No guarantee against lid closure'})
            if not ok or status.ac != 1: raise ValueError('Keep AC connected and lid open; power status not AC')
            context = {'content_commit': plan['content_commit'], 'session_id': plan['session_id'],
                'comparison_protocol_hash': plan['comparison_protocol_hash'],
                'initial_checkpoint_sha256': sha256_file(output / 'initial_checkpoint.json')}
            progress(True)
            if not gate(plan, output / 'admission_resources', 'Recovery', context, deadline):
                raise ValueError('Recovery resource gate rejected; no clock/target started')
            window['phase'] = 'fresh_short_long_admission'; progress(True)
            clock_check(plan, local_path(plan['recovery_directory']), 'admission', context, deadline)
            admission = audit_admission(plan)
            atomic_write_json(output / 'independent_admission.json', admission)
            if not admission['recovery_eligible']: raise ValueError('Independent admission ineligible')
            atomic_write_json(local_path(plan['recovery_directory']) / 'certificate.json', certificate_value(plan, admission))
            window['phase'] = 'setup_gate'; progress(True)
            setup_context = {'content_commit': plan['content_commit'], 'session_id': plan['session_id'],
                             'comparison_protocol_hash': plan['comparison_protocol_hash'], 'purpose': 'setup'}
            if not gate(plan, output / 'setup_resources', 'Formal', setup_context, deadline): raise ValueError('Setup Formal gate refused')
            operation('setup')
            space = ConfigSpace.load(ROOT / 'configs/config_space.json')
            while True:
                state = load(output / 'checkpoint.json'); job = next_job(state, space, protocol)
                if job is None: break
                if (output / 'PAUSE_REQUEST').exists(): raise ValueError('Pause requested; marker preserved')
                if deadline - time.perf_counter() <= 60: raise TimeoutError('Insufficient activity budget for next group')
                attempt = uuid.uuid4().hex; checks = output / 'group_checks' / attempt; checks.mkdir(parents=True)
                context = job_context(plan, job, attempt)
                window.update(phase='group_resources', job=job, attempt_id=attempt); progress(True)
                if not gate(plan, checks / 'resources', 'Formal', context, deadline): raise ValueError('Configuration Formal gate exhausted')
                window['phase'] = 'before_clock'; progress(True)
                clock_check(plan, checks / 'before', 'before', {**context, 'phase': 'before'}, deadline)
                window['phase'] = 'evaluation'; progress(True)
                measure(plan, plan_path, job, attempt, checks, deadline, progress)
                filename = output / 'configurations' / (job['kind'] + '_' + attempt + '.json')
                window['phase'] = 'after_clock'; progress(True)
                clock_check(plan, checks / 'after', 'after', {**context, 'phase': 'after', 'group_sha256': sha256_file(filename)}, deadline)
                operation('accept', attempt, checks); progress(True)
            window.update(status='complete', phase='cleanup')
    except (ValueError, KeyError, TypeError, OSError, TimeoutError, KeyboardInterrupt) as failure:
        window.update(status='stopped', failure_reason=str(failure))
        state = load(output / 'checkpoint.json')
        state.update(status='stopped', failure_reason=str(failure))
        if state['active']:
            state['active']['formal_comparable'] = False
            state['active']['failure_reason'] = str(failure)
        atomic_write_json(output / 'checkpoint.json', state)
    finally:
        ended, hz = qpc()
        window.update(qpc_end=ended, activity_qpc_seconds=(ended - started) / frequency,
            budget_pass=hz == frequency and (ended - started) / frequency <= budget, ended_at=utc_now())
        atomic_write_json(output / 'window.json', window); progress(True)
        print(json.dumps(window), flush=True)
    return 0 if window['status'] == 'complete' and window['budget_pass'] else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--search-authorization', type=Path)
    args = parser.parse_args(); raise SystemExit(run(load(args.plan), args.plan.resolve(), args.search_authorization))
