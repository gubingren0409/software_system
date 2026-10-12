"""One explicitly authorized continuation window; frozen 3cc measurement is unchanged."""
from __future__ import annotations
import argparse, hashlib, importlib, json, os, queue, shutil, subprocess, sys, threading, time, uuid
from datetime import datetime
from pathlib import Path

CONTENT = '3cc9e0d03ba682569fca0e91f28d364f2dab73fa'
SESSION = 'f705a488d7b442789973381e2190c944'
VERSION = 'raw-grid-segment-v1'
MANUAL_VERSION = 'raw-grid-manual-remaining-v1'
MANUAL_BASELINE = '9f714a72f2c59e75839db89a67e870d9b320fe4d'
PRIOR_USED_SECONDS = 133.3351975
REMAINING_SECONDS = 14266.6648025
FIRST_SECONDS = 13883.0691008
WINDOW_SECONDS = 14400
TOTAL_SECONDS = 28800
SELF = Path(__file__).resolve()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes(), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def frozen(plan):
    archive = Path(plan['windows_archive_directory'])
    sys.path.insert(0, str(archive))
    module = importlib.import_module('scripts.start_raw_grid')
    if module.ROOT != archive:
        raise ValueError('Frozen module import shadow')
    module.validate_plan(plan)
    return module


def validate_start(state, records):
    expected = [{'optimization': 'O0', 'block_size': s} for s in (8, 16, 24, 64, 128)]
    if state['session_id'] != SESSION or [g['config'] for g in state['completed']] != expected or \
            state['active'] is not None or state['abandoned_attempts'] or state['target_executions'] != 30 or \
            len(records) != 30 or len({r['run_id'] for r in records}) != 30 or not state.get('artifacts'):
        raise ValueError('Continuation must begin at index 5 with exactly five accepted groups / 30 unique samples')


def active_cost(first, second):
    if not (0 <= first <= TOTAL_SECONDS and 0 <= second <= WINDOW_SECONDS and first + second <= TOTAL_SECONDS):
        raise ValueError('Segment or cumulative active budget exceeded')
    return first + second  # Never subtract absolute QPC values from different windows/epochs.


def elapsed(start, end, frequency, current_frequency):
    if any(type(v) is not int or v <= 0 for v in (start, end, frequency, current_frequency)) or \
            frequency != current_frequency or end < start:
        raise ValueError('Current-window QPC epoch/frequency changed')
    return (end - start) / frequency


def exclusive_claim(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, allow_nan=False, indent=2)
        stream.flush(); os.fsync(stream.fileno())


def rows(path):
    return [json.loads(line) for line in Path(path).read_bytes().splitlines() if line]


def prepare(plan_path, directory, prior_authorization=None):
    plan = read(plan_path); f = frozen(plan)
    if plan['content_commit'] != CONTENT or plan['session_id'] != SESSION:
        raise ValueError('Wrong accepted content/session')
    session = Path(plan['session_directory']); state = read(session / 'checkpoint.json')
    samples = session / 'samples.jsonl'; validate_start(state, rows(samples))
    audit = importlib.import_module('scripts.audit_raw_grid').audit_grid(plan)
    if not audit['evidence_integrity_pass'] or audit['errors'] or audit['valid_configuration_count'] != 5:
        raise ValueError('Accepted measurements/caches failed independent preflight')
    directory.mkdir(parents=True, exist_ok=False)
    snapshots = directory / 'preserved'; snapshots.mkdir()
    mutable = {'checkpoint.json', 'samples.jsonl', 'grid_summary.csv', 'progress.json'}
    protected = {}
    for path in session.rglob('*'):
        if not path.is_file(): continue
        relative = path.relative_to(session).as_posix()
        if relative not in mutable: protected[relative] = digest(path)
    for name in ('controller.json', 'checkpoint.json', 'grid_summary.csv', 'initial_checkpoint.json', 'samples.jsonl', 'progress.json'):
        if (session / name).exists(): shutil.copy2(session / name, snapshots / name)
    original_audit = session.parent / 'grid_audit_archive.json'
    shutil.copy2(original_audit, snapshots / 'first_independent_audit.json')
    shutil.copytree(Path(plan['recovery_directory']), snapshots / 'first_recovery')
    f.atomic_write_json(directory / 'preflight_independent.json', audit)
    old_controller = read(snapshots / 'controller.json')
    if old_controller['total_qpc_seconds'] != FIRST_SECONDS:
        raise ValueError('First accepted QPC envelope differs')
    authorization = {'schema': VERSION, 'authorized_by': 'User continuation after accepted f19f9f84, 2026-10-12',
        'scope': 'One external segmented scheduling window only; frozen measurement/timing/resource policy unchanged',
        'content_commit': CONTENT, 'session_id': SESSION, 'plan_file': str(plan_path), 'plan_sha256': digest(plan_path),
        'directory': str(directory), 'repository_directory': str(plan_path.parents[4]), 'helper_sha256': digest(SELF), 'start_index': 5, 'stop_index': 20,
        'start_checkpoint_sha256': digest(samples.parent / 'checkpoint.json'),
        'samples_prefix_sha256': digest(samples), 'samples_prefix_bytes': samples.stat().st_size,
        'first_segment_qpc_seconds': FIRST_SECONDS, 'new_window_seconds': WINDOW_SECONDS,
        'cumulative_active_ceiling_seconds': TOTAL_SECONDS, 'protected_session_files': protected,
        'accepted_group_sha256': [hashlib.sha256(json.dumps(g, sort_keys=True).encode()).hexdigest() for g in state['completed']],
        'original_run_ids': [r['run_id'] for r in rows(samples)],
        'original_setup': {k: state[k] for k in ('artifacts', 'setup_seconds', 'build_setup_seconds', 'reference_setup_seconds', 'reference_generation_calls')},
        'initial_checkpoint_sha256': digest(session / 'initial_checkpoint.json'),
        'first_certificate_sha256': digest(Path(plan['recovery_directory']) / 'certificate.json'),
        'first_recovery_sha256': {p.relative_to(Path(plan['recovery_directory'])).as_posix(): digest(p)
            for p in Path(plan['recovery_directory']).rglob('*') if p.is_file()},
        'cached_manifest_sha256': {}, 'no_third_window': True,
        'skip_setup_when_artifacts_verified': True, 'performance_cache_allowed': False}
    if prior_authorization is not None:
        prior = read(prior_authorization); previous = Path(prior['directory'])
        claim = session / 'RAW_SEGMENT_WINDOW_V1.claim.json'
        protected_previous = {str(p): digest(p) for p in previous.parent.rglob('*') if p.is_file()}
        protected_previous[str(claim)] = digest(claim)
        authorization.update(schema=MANUAL_VERSION,
            authorized_by='Explicit user confirmation at 9f714a72; one manual use of the remaining allowance',
            scope='Resume the original second-window activity allowance, not a third window or a budget reset',
            prior_authorization_file=str(prior_authorization), prior_window_file=str(previous / 'window.json'),
            prior_claim_file=str(claim), prior_delivery_commit=MANUAL_BASELINE,
            protected_previous_files=protected_previous, prior_used_seconds=PRIOR_USED_SECONDS,
            remaining_allowance_seconds=REMAINING_SECONDS, manual_attempt_limit=1)
        verify_previous(authorization, plan)
    for name in ('candidate_O0', 'candidate_O1', 'candidate_O2', 'candidate_O3', 'reference_build'):
        metadata = read(session / 'manifests' / (name + '.json'))
        path = f.local_path(metadata['command'][-1]).parent / 'manifest.json'
        authorization['cached_manifest_sha256'][str(path)] = digest(path)
    path = f.local_path(plan['cache_directory']) / 'reference' / state['artifacts']['reference_key'] / 'manifest.json'
    authorization['cached_manifest_sha256'][str(path)] = digest(path)
    f.atomic_write_json(directory / 'authorization.json', authorization)
    return authorization


def verify_previous(auth, plan):
    """Preserve the closed rejected attempt; sum durations, never subtract across QPC epochs."""
    if auth['prior_delivery_commit'] != MANUAL_BASELINE or auth['prior_used_seconds'] != PRIOR_USED_SECONDS or \
            auth['remaining_allowance_seconds'] != REMAINING_SECONDS or auth['manual_attempt_limit'] != 1:
        raise ValueError('Manual remaining-budget authorization differs')
    for path, expected in auth['protected_previous_files'].items():
        if digest(path) != expected: raise ValueError('Previous closed attempt changed: ' + path)
    prior = read(auth['prior_authorization_file']); old = read(auth['prior_window_file']); claim = read(auth['prior_claim_file'])
    if prior['schema'] != VERSION or prior['content_commit'] != CONTENT or prior['session_id'] != SESSION or \
            old['schema'] != VERSION or old['status'] != 'partial_or_blocked' or old['budget_pass'] is not True or \
            any(old[k] is not False for k in ('formal_invoked', 'pre_resource_pass', 'continuation_clock_pass')) or \
            old['authorization_sha256'] != digest(auth['prior_authorization_file']) or \
            old['qpc_start'] != claim['qpc_start'] or old['qpc_frequency'] != claim['qpc_frequency'] or \
            old['authorization_sha256'] != claim['authorization_sha256'] or old['helper_sha256'] != claim['helper_sha256'] or \
            old['auxiliary_content_commit'] != claim['auxiliary_content_commit'] or \
            elapsed(old['qpc_start'], old['qpc_end'], old['qpc_frequency'], old['qpc_frequency']) != PRIOR_USED_SECONDS or \
            old['window_qpc_seconds'] != PRIOR_USED_SECONDS or old['cumulative_active_qpc_seconds'] != FIRST_SECONDS + PRIOR_USED_SECONDS or \
            auth['start_checkpoint_sha256'] != prior['start_checkpoint_sha256'] or \
            auth['samples_prefix_sha256'] != prior['samples_prefix_sha256']:
        raise ValueError('Previous closed claim/window/start state differs')
    repository = Path(auth['repository_directory'])
    for path in (auth['prior_authorization_file'], auth['prior_window_file'], auth['prior_claim_file']):
        relative = Path(path).relative_to(repository).as_posix()
        committed = subprocess.run(['git', 'show', MANUAL_BASELINE + ':' + relative], cwd=repository, capture_output=True, check=True).stdout
        if hashlib.sha256(committed).hexdigest() != digest(path): raise ValueError('Previous attempt differs from audited 9f714a72 bytes')
    return PRIOR_USED_SECONDS


def budget_settings(auth, plan):
    if auth['schema'] not in (VERSION, MANUAL_VERSION) or auth['helper_sha256'] != digest(SELF) or \
            auth['content_commit'] != CONTENT or auth['session_id'] != SESSION or auth['start_index'] != 5 or \
            auth['stop_index'] != 20 or auth['performance_cache_allowed'] is not False or \
            auth['new_window_seconds'] != WINDOW_SECONDS or auth['cumulative_active_ceiling_seconds'] != TOTAL_SECONDS or \
            auth['first_segment_qpc_seconds'] != FIRST_SECONDS:
        raise ValueError('Authorization/helper/budget differs')
    if auth['schema'] == VERSION: return 0.0, WINDOW_SECONDS, 'RAW_SEGMENT_WINDOW_V1.claim.json'
    prior = verify_previous(auth, plan)
    if prior + REMAINING_SECONDS != WINDOW_SECONDS: raise ValueError('Remaining allowance does not preserve the original ceiling')
    return prior, REMAINING_SECONDS, 'RAW_SEGMENT_MANUAL_REMAINING_V1.claim.json'


def verify_protection(auth, plan, *, initial=False):
    session = Path(plan['session_directory']); state = read(session / 'checkpoint.json')
    if digest(auth['plan_file']) != auth['plan_sha256'] or plan['content_commit'] != CONTENT or plan['session_id'] != SESSION:
        raise ValueError('Plan/content/session identity changed')
    if initial and digest(session / 'checkpoint.json') != auth['start_checkpoint_sha256']:
        raise ValueError('Starting checkpoint changed')
    if auth['schema'] == MANUAL_VERSION: verify_previous(auth, plan)
    for name, expected in auth['protected_session_files'].items():
        if digest(session / name) != expected: raise ValueError('Historical session file changed: ' + name)
    for name, expected in auth['first_recovery_sha256'].items():
        if digest(Path(plan['recovery_directory']) / name) != expected: raise ValueError('First recovery evidence changed')
    for name, expected in auth['cached_manifest_sha256'].items():
        if digest(name) != expected: raise ValueError('Verified cache changed/rebuilt; extra generation count unknown, stop')
    with (session / 'samples.jsonl').open('rb') as stream:
        prefix = stream.read(auth['samples_prefix_bytes'])
    if hashlib.sha256(prefix).hexdigest() != auth['samples_prefix_sha256']:
        raise ValueError('Original 30-sample byte prefix changed')
    group_hashes = [hashlib.sha256(json.dumps(g, sort_keys=True).encode()).hexdigest() for g in state['completed'][:5]]
    if group_hashes != auth['accepted_group_sha256'] or any(state[k] != value for k, value in auth['original_setup'].items()):
        raise ValueError('Accepted groups/setup/reference counts changed')
    return True


def verify_auxiliary(auth, sha):
    if len(sha) != 40 or any(c not in '0123456789abcdef' for c in sha): raise ValueError('Invalid auxiliary SHA')
    original = subprocess.run(['git', 'show', sha + ':scripts/raw_grid_segment.py'], cwd=auth['repository_directory'],
        capture_output=True, check=True).stdout
    if hashlib.sha256(original).hexdigest() != digest(SELF): raise ValueError('Executed helper differs from committed auxiliary content')


def require_admission(identity_pass, resource_pass, clock_pass):
    if not all(v is True for v in (identity_pass, resource_pass, clock_pass)):
        raise ValueError('Current identity/resource/clock admission required before any target')


def admission_schedule():
    return [{'index': i, 'round': i + 1, 'condition': 'LU' if i == 0 else 'LU-long', 'path': 'libc',
        'selected_cpu': -1, 'updates': 1_000_000_000 if i == 0 else 10_000_000_000, 'long': i == 1} for i in range(2)]


def admission_command(f, plan, build):
    binary = build['binary']
    wrapper = 'import hashlib,os; p=' + repr(binary) + '; assert hashlib.sha256(open(p,"rb").read()).hexdigest()==' + repr(build['binary_sha256']) + '; os.execv(p,[p])'
    return f.linux(plan, ['timeout', '--signal=TERM', '--kill-after=5', '110', 'python3', '-c', wrapper])


def collect_admission(f, plan, auth, directory, deadline):
    """New two-interval attachment, NOT the old empty-session recovery/certificate."""
    directory.mkdir(exist_ok=False)
    build = read(plan['probe_build_manifest']); binary = build['binary']
    manifest = {'schema': 'raw-grid-segment-admission-v1', 'content_commit': CONTENT, 'session_id': SESSION,
        'authorization_sha256': digest(Path(auth['directory']) / 'authorization.json'),
        'checkpoint_sha256': auth['start_checkpoint_sha256'], 'auxiliary_sha256': digest(SELF),
        'criteria': f.validate_plan(plan)[1]['admission'], 'schedule': admission_schedule(),
        'probe_build': build, 'collection_budget_seconds': 120,
        'source_sha256': {p: v['executed_sha256'] for p, v in plan['windows_source_identity'].items()},
        'allowed_cpus': plan['allowed_cpus'],
        'command': admission_command(f, plan, build)}
    if digest(f.local_path(binary)) != build['binary_sha256']: raise ValueError('Admission binary changed')
    f.atomic_write_json(directory / 'manifest.json', manifest)
    checker = importlib.import_module('scripts.p3_fixed_work_clock').check_interval
    send = importlib.import_module('scripts.run_fixed_work_clock').send_request
    start, frequency = f.qpc(); end_at = min(deadline, time.perf_counter() + 115)
    messages = []; intervals = []; errors = []; received = queue.Queue(); child = None; hello = None; rc = 'unknown'; seq = 0
    streams = {name: (directory / name).open('wb') for name in ('native.stdout.txt', 'native.stderr.txt', 'messages.jsonl', 'intervals.jsonl')}
    def append(name, value):
        streams[name].write((json.dumps(value, allow_nan=False) + '\n').encode()); streams[name].flush()
    def reader():
        for line in iter(child.stdout.readline, b''):
            stamp, hz = f.qpc(); streams['native.stdout.txt'].write(line); streams['native.stdout.txt'].flush(); received.put((stamp, hz, line))
        received.put(None)
    def err_reader():
        for line in iter(child.stderr.readline, b''):
            streams['native.stderr.txt'].write(line); streams['native.stderr.txt'].flush()
    def receive(sent, command):
        item = received.get(timeout=max(0.001, end_at - time.perf_counter()))
        if item is None: raise ValueError('Native EOF')
        stamp, hz, line = item
        if hz != frequency: raise ValueError('QPC frequency changed')
        record = {'command': command, 'send_qpc': sent, 'recv_qpc': stamp, 'response': json.loads(line)}
        messages.append(record); append('messages.jsonl', record); return record
    def request(op, arguments=''):
        nonlocal seq
        if time.perf_counter() >= end_at: raise TimeoutError('Admission deadline')
        seq += 1; command = f'{op} {seq}' + (' ' + arguments if arguments else '') + '\n'
        sent, hz = send(child, command, lambda: f.atomic_write_json(directory / 'progress.json', {'seq': seq, 'command': command, 'saved_intervals': len(intervals)}))
        if hz != frequency: raise ValueError('QPC frequency changed')
        record = receive(sent, command); response = record['response']
        if response['pid'] != hello['pid'] or response['seq'] != seq or response['op'] != op: raise ValueError('Native identity/order differs')
        return record
    threads = []
    try:
        env = os.environ.copy(); env.pop('PYTHONPATH', None); env['PYTHONDONTWRITEBYTECODE'] = '1'
        child = subprocess.Popen(manifest['command'], cwd=f.ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=env, creationflags=subprocess.CREATE_NO_WINDOW)
        threads = [threading.Thread(target=reader, daemon=True), threading.Thread(target=err_reader, daemon=True)]
        for thread in threads: thread.start()
        hello = receive(start, 'START_PROCESS')['response']
        if hello['op'] != 'HELLO' or hello['seq'] != 0 or hello['allowed_cpus'] != plan['allowed_cpus']: raise ValueError('HELLO differs')
        for planned in manifest['schedule']:
            request('MODE', 'libc -1'); first = seq + 1
            first_read = request('READ'); work = request('WORK', str(planned['updates'])); last_read = request('READ')
            row = {'schema': 'fixed-work-clock-interval-v1', 'planned': planned, 'qpc_frequency': frequency,
                'start': first_read, 'work': work, 'end': last_read}
            row['check'] = checker(row, frequency, planned, hello['pid'], first, hello['allowed_cpus'])
            intervals.append(row); append('intervals.jsonl', row)
            print(json.dumps({'event': 'segment_clock_interval', 'index': planned['index'], 'raw_pass': row['check']['raw_pass']}), flush=True)
            if not row['check']['raw_pass']: raise ValueError('Segment RAW check failed/indeterminate')
        request('QUIT'); rc = child.wait(timeout=max(0.001, end_at - time.perf_counter()))
    except (ValueError, KeyError, TypeError, OSError, TimeoutError, queue.Empty, subprocess.TimeoutExpired) as error:
        errors.append(str(error))
    finally:
        if child is not None and child.poll() is None:
            if hello and type(hello.get('pid')) is int:
                try: subprocess.run(['wsl.exe', '-d', 'Ubuntu-24.04', '--', 'kill', '-TERM', str(hello['pid'])], capture_output=True, timeout=3)
                except (OSError, subprocess.TimeoutExpired): errors.append('Native cleanup result unknown')
            try: rc = child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                child.terminate(); rc = child.wait(timeout=2)
        elif child is not None: rc = child.returncode
        for thread in threads: thread.join(timeout=1)
        for handle in streams.values(): handle.flush(); handle.close()
        end, hz = f.qpc()
        f.atomic_write_json(directory / 'process.json', {'schema': 'raw-grid-segment-clock-process-v1', 'command': manifest['command'], 'hello': hello, 'returncode': rc,
            'errors': errors, 'qpc_start': start, 'qpc_end': end, 'qpc_frequency': frequency,
            'qpc_seconds': elapsed(start, end, frequency, hz), 'manifest_sha256': digest(directory / 'manifest.json'),
            'stream_sha256': {name: digest(directory / name) for name in streams}})


def audit_admission(f, plan, auth, directory):
    checker = importlib.import_module('scripts.p3_fixed_work_clock').check_interval
    result = {'evidence_integrity_pass': False, 'eligible': False, 'checks': [], 'errors': []}
    try:
        manifest = read(directory / 'manifest.json'); op = read(directory / 'process.json')
        if manifest['schema'] != 'raw-grid-segment-admission-v1' or manifest['content_commit'] != CONTENT or \
                manifest['session_id'] != SESSION or manifest['authorization_sha256'] != digest(Path(auth['directory']) / 'authorization.json') or \
                manifest['checkpoint_sha256'] != auth['start_checkpoint_sha256'] or manifest['auxiliary_sha256'] != digest(SELF) or \
                manifest['criteria'] != f.validate_plan(plan)[1]['admission'] or manifest['schedule'] != admission_schedule() or \
                manifest['collection_budget_seconds'] != 120 or manifest['allowed_cpus'] != plan['allowed_cpus'] or \
                manifest['source_sha256'] != {p: v['executed_sha256'] for p, v in plan['windows_source_identity'].items()} or \
                manifest['probe_build'] != read(plan['probe_build_manifest']) or \
                digest(f.local_path(manifest['probe_build']['binary'])) != manifest['probe_build']['binary_sha256']:
            raise ValueError('Continuation clock source/context/protocol differs')
        if op['schema'] != 'raw-grid-segment-clock-process-v1' or \
                op['manifest_sha256'] != digest(directory / 'manifest.json') or \
                op['command'] != manifest['command'] or manifest['command'] != admission_command(f, plan, manifest['probe_build']) or \
                set(op['stream_sha256']) != {'native.stdout.txt', 'native.stderr.txt', 'messages.jsonl', 'intervals.jsonl'}:
            raise ValueError('Continuation clock operation differs')
        for name, value in op['stream_sha256'].items():
            if digest(directory / name) != value: raise ValueError('Clock stream changed')
        messages = rows(directory / 'messages.jsonl'); intervals = rows(directory / 'intervals.jsonl')
        result.update(interval_count=len(intervals), response_count=len(messages),
            qpc_start=op['qpc_start'], qpc_end=op['qpc_end'], qpc_frequency=op['qpc_frequency'])
        if [m['response'] for m in messages] != rows(directory / 'native.stdout.txt') or not messages: raise ValueError('Native stream differs')
        hello = messages[0]['response']; pid = hello['pid']; previous = op['qpc_start']; prior_raw = None
        if hello != op['hello'] or hello['op'] != 'HELLO' or type(pid) is not int or pid <= 0 or hello['allowed_cpus'] != plan['allowed_cpus']: raise ValueError('HELLO differs')
        for seq, message in enumerate(messages):
            ep = message['response']
            if any(type(message[k]) is not int for k in ('send_qpc', 'recv_qpc')) or not previous <= message['send_qpc'] <= message['recv_qpc'] or \
                    type(ep['seq']) is not int or ep['seq'] != seq or type(ep['pid']) is not int or ep['pid'] != pid or ep['schema'] != 'fixed-work-clock-endpoint-v1':
                raise ValueError('Message PID/sequence/QPC invalid')
            previous = message['recv_qpc']
            if ep['op'] == 'READ':
                if type(ep['raw1_ns']) is not int or type(ep['raw2_ns']) is not int or (prior_raw is not None and ep['raw1_ns'] < prior_raw): raise ValueError('Global RAW rollback/invalid integer')
                prior_raw = ep['raw2_ns']
        if op['qpc_end'] < previous or op['qpc_seconds'] != elapsed(op['qpc_start'], op['qpc_end'], op['qpc_frequency'], op['qpc_frequency']) or op['qpc_seconds'] > 120:
            raise ValueError('Admission QPC budget invalid')
        for index, row in enumerate(intervals):
            if index >= 2: raise ValueError('Extra interval')
            pointer = index * 4 + 1; mode = messages[pointer]
            if mode['command'] != f'MODE {pointer} libc -1\n' or mode['response']['op'] != 'MODE' or mode['response']['path'] != 'libc' or mode['response']['selected_cpu'] != -1 or \
                    [row['start'], row['work'], row['end']] != messages[pointer + 1:pointer + 4]: raise ValueError('MODE/interval binding differs')
            checked = checker(row, op['qpc_frequency'], admission_schedule()[index], pid, pointer + 1, hello['allowed_cpus'])
            if checked != row['check']: raise ValueError('Saved check contradicts original endpoints')
            result['checks'].append(checked)
        complete = len(intervals) == 2 and len(messages) == 10 and messages[-1]['command'] == 'QUIT 9\n' and messages[-1]['response']['op'] == 'QUIT'
        integrity = complete and all(c['evidence_integrity_pass'] for c in result['checks'])
        result.update(evidence_integrity_pass=integrity, eligible=integrity and all(c['raw_pass'] for c in result['checks']) and type(op['returncode']) is int and op['returncode'] == 0 and not op['errors'])
        if not result['eligible']: result['errors'].append('Incomplete, failed, or indeterminate continuation clock')
    except (ValueError, KeyError, TypeError, OSError, IndexError) as error: result['errors'].append(str(error))
    return result


def run(authorization, auxiliary_sha):
    auth = read(authorization); plan = read(auth['plan_file']); f = frozen(plan)
    directory = Path(auth['directory']); session = Path(plan['session_directory'])
    prior_used, allowance, claim_name = budget_settings(auth, plan)
    verify_auxiliary(auth, auxiliary_sha)
    verify_protection(auth, plan, initial=True); validate_start(read(session / 'checkpoint.json'), rows(session / 'samples.jsonl'))
    start, frequency = f.qpc()
    status = {'schema': auth['schema'], 'auxiliary_content_commit': auxiliary_sha, 'helper_sha256': digest(SELF),
        'authorization_sha256': digest(authorization), 'qpc_start': start, 'qpc_frequency': frequency,
        'first_segment_qpc_seconds': FIRST_SECONDS, 'status': 'running', 'phase': 'environment', 'formal_invoked': False,
        'pre_resource_pass': False, 'continuation_clock_pass': False, 'failure_reason': None, 'controller_pid': os.getpid(),
        'prior_used_seconds': prior_used, 'remaining_allowance_seconds': allowance}
    exclusive_claim(session / claim_name, status)
    f.atomic_write_json(directory / 'window.json', status)
    def used():
        now, hz = f.qpc(); return elapsed(start, now, frequency, hz)
    def remaining(): return min(allowance - used(), TOTAL_SECONDS - FIRST_SECONDS - prior_used - used())
    last_progress = 0
    def progress(force=False):
        nonlocal last_progress
        if not force and used() - last_progress < 60: return
        last_progress = used(); state = read(session / 'checkpoint.json')
        sample = read(session / 'progress.json') if state['active'] else None
        payload = {'at': f.utc_now(), 'phase': status['phase'], 'completed': len(state['completed']), 'active': state['active'],
            'sample': sample, 'window_qpc_seconds': used(), 'prior_used_seconds': prior_used,
            'second_window_activity_seconds': prior_used + used(), 'cumulative_active_qpc_seconds': FIRST_SECONDS + (prior_used + used()),
            'remaining_window_seconds': max(0, remaining()), 'current_operation_seconds': used() - status.get('operation_start_seconds', used())}
        f.atomic_write_json(directory / 'progress.json', payload); print(json.dumps(payload), flush=True)
    def capture(argv, name, maximum=None):
        if remaining() <= 30: raise TimeoutError('Continuation window budget exhausted; cleanup reserve')
        status.update(phase=name, operation_start_seconds=used()); f.atomic_write_json(directory / 'window.json', status)
        op = f.capture(argv, directory / 'operations', name, VERSION, timeout=min(maximum or remaining(), remaining() - 25), progress=progress)
        if op['returncode'] != 0 or op['timed_out']: raise ValueError(name + ' returned ' + str(op['returncode']))
        return op
    try:
        env_command = [f.POWERSHELL, '-NoProfile', '-Command',
            "[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false); $o=Get-CimInstance Win32_OperatingSystem; [ordered]@{at=[DateTimeOffset]::Now.ToString('o');windows_boot_utc=$o.LastBootUpTime.ToUniversalTime().ToString('o');windows_version=$o.Version;available_bytes=[int64]$o.FreePhysicalMemory*1KB;top_memory=@(Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 12 Id,ProcessName,WorkingSet64);vmmem=@(Get-Process VmmemWSL,Vmmem -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,WorkingSet64)} | ConvertTo-Json -Depth 5"]
        capture(env_command, 'windows_environment', 40)
        capture(f.linux(plan, ['python3', '-c', "import pathlib,json,platform; print(json.dumps({'kernel':platform.release(),'boot_id':pathlib.Path('/proc/sys/kernel/random/boot_id').read_text(),'uptime':pathlib.Path('/proc/uptime').read_text(),'meminfo':pathlib.Path('/proc/meminfo').read_text(),'vmstat':pathlib.Path('/proc/vmstat').read_text()}))"]), 'wsl_environment', 40)
        old = read(directory / 'preserved/controller.json')
        host = read(directory / 'operations/windows_environment.stdout.txt'); guest = read(directory / 'operations/wsl_environment.stdout.txt')
        f.atomic_write_json(directory / 'epoch_and_pause.json', {'current_windows_boot_utc': host['windows_boot_utc'],
            'current_wsl_boot_id': guest['boot_id'], 'current_qpc_frequency': frequency,
            'first_qpc_frequency': old['qpc_frequency'], 'first_windows_boot_identity': 'unknown',
            'epoch_relation': 'Do not infer equal epochs from equal frequency; durations only are summed',
            'review_pause_start_utc_label': old['updated_at'], 'review_pause_end_utc_label': host['at'],
            'review_pause_utc_label_gap_seconds': (datetime.fromisoformat(host['at']) - datetime.fromisoformat(old['updated_at'])).total_seconds(),
            'trusted_review_pause_duration_seconds': 'unknown; UTC labels may have clock adjustments', 'pause_in_active_cost': False})
        if auth['schema'] == MANUAL_VERSION:
            pause = read(directory / 'epoch_and_pause.json'); previous = read(auth['prior_window_file'])
            pause.update(previous_attempt_qpc_frequency=previous['qpc_frequency'],
                manual_pause_start_utc_label=previous['ended_at'], manual_pause_end_utc_label=host['at'],
                manual_pause_utc_label_gap_seconds=(datetime.fromisoformat(host['at']) - datetime.fromisoformat(previous['ended_at'])).total_seconds(),
                trusted_manual_pause_duration_seconds='unknown; UTC labels only, excluded from activity')
            f.atomic_write_json(directory / 'epoch_and_pause.json', pause)
        context = {'content_commit': CONTENT, 'session_id': SESSION, 'purpose': 'segment-preflight', 'authorization_sha256': digest(authorization)}
        status['phase'] = 'preflight_resource_gate'; progress(True)
        if not f.gate(plan, directory / 'preflight_gate', 'Formal', context, time.perf_counter() + remaining() - 25):
            raise ValueError('Continuation preflight Formal wait exhausted; no clock/target started')
        status['pre_resource_pass'] = True
        collect_admission(f, plan, auth, directory / 'admission', time.perf_counter() + remaining() - 25)
        admission = audit_admission(f, plan, auth, directory / 'admission'); f.atomic_write_json(directory / 'independent_admission.json', admission)
        if not admission['eligible']: raise ValueError('Fresh continuation clock admission failed: ' + json.dumps(admission['errors']))
        status['continuation_clock_pass'] = True; verify_protection(auth, plan, initial=True)
        preflight = importlib.import_module('scripts.audit_raw_grid').audit_grid(plan)
        f.atomic_write_json(directory / 'current_independent_preflight.json', preflight)
        if not preflight['evidence_integrity_pass'] or preflight['errors']: raise ValueError('Frozen measurement/cache identity refused')
        require_admission(preflight['evidence_integrity_pass'], status['pre_resource_pass'], admission['eligible'])
        for index in range(5, 20):
            if remaining() <= 30: raise TimeoutError('Continuation budget exhausted')
            if (session / 'PAUSE_REQUEST').exists(): raise ValueError('Pause requested; marker preserved')
            attempt = uuid.uuid4().hex; checks = session / 'group_checks' / attempt; checks.mkdir()
            status.update(config_index=index, attempt_id=attempt, phase='configuration_resource_gate'); progress(True)
            context = {'content_commit': CONTENT, 'session_id': SESSION, 'config_index': index, 'attempt_id': attempt}
            if not f.gate(plan, checks / 'resources', 'Formal', context, time.perf_counter() + remaining() - 25): raise ValueError('Configuration Formal wait exhausted')
            status['phase'] = 'before_clock'; f.collect_check(plan, checks / 'before', 'before', {**context, 'phase': 'before'}, time.perf_counter() + remaining() - 25)
            status['formal_invoked'] = True
            def operation(mode):
                seconds = remaining() - 30
                argv = f.linux(plan, ['timeout', '--signal=TERM', '--kill-after=15', str(max(1, seconds - 20)),
                    'python3', '-m', 'autotuner.raw_grid', '--plan', f.wsl_path(auth['plan_file']), mode,
                    '--index', str(index), '--attempt-id', attempt, '--checks-directory', f.wsl_path(checks)])
                capture(argv, mode + '_' + attempt)
            operation('measure')
            group = session / 'configurations' / ('grid_' + attempt + '.json')
            status['phase'] = 'after_clock'; f.collect_check(plan, checks / 'after', 'after',
                {**context, 'phase': 'after', 'group_sha256': digest(group)}, time.perf_counter() + remaining() - 25)
            operation('accept'); verify_protection(auth, plan); progress(True)
        status['status'] = 'complete'
    except (ValueError, KeyError, TypeError, OSError, TimeoutError) as error:
        status.update(status='partial_or_blocked', failure_reason=str(error))
    finally:
        end, hz = f.qpc(); duration = elapsed(start, end, frequency, hz)
        status.update(qpc_end=end, window_qpc_seconds=duration, second_window_activity_seconds=prior_used + duration,
            cumulative_active_qpc_seconds=FIRST_SECONDS + (prior_used + duration),
            budget_pass=duration <= allowance and prior_used + duration <= WINDOW_SECONDS and FIRST_SECONDS + prior_used + duration <= TOTAL_SECONDS,
            ended_at=f.utc_now())
        f.atomic_write_json(directory / 'window.json', status); print(json.dumps(status), flush=True)
    return 0 if status['status'] == 'complete' and status['budget_pass'] else 2


def audit(authorization):
    auth = read(authorization); plan = read(auth['plan_file']); f = frozen(plan); directory = Path(auth['directory'])
    result = {'evidence_integrity_pass': False, 'grid_complete': False, 'grid_timing_checks_pass': False,
        'execution_complete': False, 'timing_checks_pass': False, 'comparison_ready': False, 'errors': []}
    try:
        prior_used, allowance, claim_name = budget_settings(auth, plan)
        verify_protection(auth, plan)
        window = read(directory / 'window.json')
        verify_auxiliary(auth, window['auxiliary_content_commit'])
        seconds = elapsed(window['qpc_start'], window['qpc_end'], window['qpc_frequency'], window['qpc_frequency'])
        if seconds > allowance or seconds != window['window_qpc_seconds'] or \
                active_cost(FIRST_SECONDS, prior_used + seconds) != window['cumulative_active_qpc_seconds'] or \
                window['prior_used_seconds'] != prior_used or window['remaining_allowance_seconds'] != allowance or window['schema'] != auth['schema']:
            raise ValueError('Segment activity cost differs')
        claim = read(Path(plan['session_directory']) / claim_name)
        if claim['qpc_start'] != window['qpc_start'] or claim['authorization_sha256'] != digest(authorization) or claim['helper_sha256'] != digest(SELF) or \
                claim['qpc_frequency'] != window['qpc_frequency'] or claim['auxiliary_content_commit'] != window['auxiliary_content_commit'] or \
                claim['prior_used_seconds'] != prior_used or claim['remaining_allowance_seconds'] != allowance:
            raise ValueError('Unique authorization claim differs')
        base = importlib.import_module('scripts.audit_raw_grid').audit_grid(plan)
        f.atomic_write_json(directory / 'frozen_measurement_audit.json', base)
        clock = audit_admission(f, plan, auth, directory / 'admission') if (directory / 'admission').exists() else None
        f.atomic_write_json(directory / 'recomputed_admission.json', clock)
        context = {'content_commit': CONTENT, 'session_id': SESSION, 'purpose': 'segment-preflight', 'authorization_sha256': digest(authorization)}
        gate_pass = f.audit_gate(directory / 'preflight_gate', f.validate_plan(plan)[0], 'Formal', context) if window['pre_resource_pass'] else False
        if window['formal_invoked'] and (not gate_pass or clock is None or not clock['eligible']): raise ValueError('Target invoked without current admission')
        if clock:
            gate = read(directory / 'preflight_gate/gate_outcome.json')
            if clock['qpc_frequency'] != window['qpc_frequency'] or not window['qpc_start'] <= gate['qpc_start'] <= gate['qpc_end'] <= clock['qpc_start'] <= clock['qpc_end'] <= window['qpc_end']:
                raise ValueError('Current admission not inside this window/after its gate')
        state = read(Path(plan['session_directory']) / 'checkpoint.json')
        for group in state['completed'][5:]:
            for mode in ('measure', 'accept'):
                name = mode + '_' + group['attempt_id']
                op = importlib.import_module('scripts.raw_clock_contract').checked_operation(directory / 'operations', name)
                if not clock or not clock['qpc_end'] <= op['qpc_start'] <= op['qpc_end'] <= window['qpc_end'] or \
                        op['qpc_frequency'] != window['qpc_frequency'] or op['returncode'] != 0 or op['timed_out']:
                    raise ValueError('New complete group lacks current-window execution binding')
        if not base['evidence_integrity_pass'] or base['errors']: raise ValueError('Frozen measurement audit failed')
        result.update(evidence_integrity_pass=True, grid_complete=base['grid_complete'],
            grid_timing_checks_pass=base['grid_timing_checks_pass'] and bool(clock and clock['eligible']),
            preflight_resource_pass=gate_pass, current_clock_eligible=bool(clock and clock['eligible']),
            completed_configurations=base['completed_configurations'], target_executions=base['target_execution_count'],
            newly_completed_configurations=base['completed_configurations'] - 5, new_target_executions=base['target_execution_count'] - 30,
            first_segment_qpc_seconds=FIRST_SECONDS, continuation_qpc_seconds=seconds,
            prior_used_seconds=prior_used, second_window_activity_seconds=prior_used + seconds,
            cumulative_active_qpc_seconds=FIRST_SECONDS + (prior_used + seconds), lowest_median_observation=base.get('lowest_median_observation'),
            original_data_protection_pass=True, auxiliary_content_commit=window['auxiliary_content_commit'],
            additional_reference_generation_calls=0,
            auxiliary_sha256=digest(SELF), content_commit=CONTENT, session_id=SESSION,
            original_controller_cost_scope='First segment only; superseded by sum of non-overlapping segment envelopes',
            status=window['status'], failure_reason=window['failure_reason'])
    except (ValueError, KeyError, TypeError, OSError, IndexError) as error: result['errors'].append(str(error))
    f.atomic_write_json(directory / 'independent_segment_audit.json', result); print(json.dumps(result), flush=True)
    return 0 if result['evidence_integrity_pass'] and result['grid_complete'] and result['grid_timing_checks_pass'] else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare', 'run', 'audit'))
    parser.add_argument('--plan', type=Path); parser.add_argument('--directory', type=Path)
    parser.add_argument('--authorization', type=Path); parser.add_argument('--auxiliary-sha')
    parser.add_argument('--prior-authorization', type=Path, help='Explicitly authorized one-time use of the original remaining allowance')
    args = parser.parse_args()
    if args.mode == 'prepare':
        print(json.dumps(prepare(args.plan.resolve(), args.directory.resolve(),
            args.prior_authorization.resolve() if args.prior_authorization else None))); return 0
    if args.mode == 'run': return run(args.authorization.resolve(), args.auxiliary_sha)
    return audit(args.authorization.resolve())


if __name__ == '__main__':
    raise SystemExit(main())
