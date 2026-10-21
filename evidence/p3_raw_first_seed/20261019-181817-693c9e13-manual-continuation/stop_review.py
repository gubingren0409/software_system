"""Read-only review after the single authorized continuation stopped; no target calls."""
import collections
import importlib.util
import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent
auth_path = OUT / 'continuation/authorization.json'
auth = json.loads(auth_path.read_bytes())
plan = json.loads(Path(auth['plan_file']).read_bytes())
sys.path.insert(0, plan['windows_archive_directory'])
from autotuner.core import sha256_file, utc_now
from scripts.p3_clock_contract import atomic_write_json, capture, load
from scripts.raw_comparison_contract import checked_operation
from scripts.raw_comparison_power import standby_events, validate_event_record

session = Path(plan['session_directory'])
state = load(session / 'checkpoint.json')
window = load(OUT / 'continuation/window.json')
checks = session / 'group_checks' / state['active']['attempt_id']
power_paths = sorted((checks / 'power_events').glob('events_*.stdout.txt'),
                     key=lambda p: int(p.name.split('_')[1].split('.')[0]))
records, validation = [], []
cursor, boot = -1, None
for path in power_paths:
    checked_operation(path.parent, path.name.removesuffix('.stdout.txt'))
    record = load(path)
    validate_event_record(record, cursor, boot)
    validation.append(dict(path=str(path), sha256=sha256_file(path), identity_pass=True,
                           cursor_before=record['cursor_before'], cursor_after=record['cursor_after']))
    cursor, boot = record['cursor_after'], record['windows_boot_utc']
    records.append(record)

command = [
    'C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe', '-NoProfile', '-Command',
    "[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false); "
    "$ownedWindows=@(Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='python3.exe' OR Name='wsl.exe'\" | "
    "Where-Object { $_.CommandLine -match 'matrix-raw-comparison-(content|cache)-776b111|matrix-raw-search-continuation-706d239|autotuner.raw_comparison' } | "
    "Select-Object ProcessId,ParentProcessId,Name,CommandLine); "
    "$wslText=@(& wsl.exe -d Ubuntu-24.04 -- ps -eo pid,ppid,stat,args); $wslExit=$LASTEXITCODE; "
    "$ownedWsl=@($wslText | Select-String -Pattern 'matrix-raw-comparison-(content|cache)-776b111|p3_raw_first_seed/20261019-132400' | ForEach-Object { $_.Line }); "
    "[ordered]@{windows_processes=$ownedWindows;wsl_ps_returncode=$wslExit;matching_wsl_processes=$ownedWsl;at=[DateTimeOffset]::Now.ToString('o')} | ConvertTo-Json -Depth 5; "
    "if ($wslExit -ne 0) {exit 2}"
]
operation = capture(command, OUT / 'stop_processes', 'owned_processes', 'manual-continuation-stop', timeout=30)
processes = load(OUT / 'stop_processes' / operation['stdout_path'])

spec = importlib.util.spec_from_file_location('manual_continuation_protection', auth['helper_file'])
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
helper.verify_auth(auth)
helper.verify_preserved(auth)
samples = helper.rows(session / 'samples.jsonl')
accepted_ids = {s['run_id'] for t in state['trajectories'].values()
                for g in t['observations'] + t['retests'] for s in g['samples']}
pending = [s for s in samples if s['run_id'] not in accepted_ids]
scope = load(checks / 'evaluation_scope.json')
continuity = load(checks / 'continuity.json')
result = dict(schema='manual-first-seed-stop-review-v1', at=utc_now(),
    auxiliary_source_sha256=sha256_file(Path(__file__)),
    content_commit=plan['content_commit'], auxiliary_content_commit=auth['auxiliary_content_commit'],
    session_id=plan['session_id'], active=state['active'], stop_reason=window['failure_reason'],
    controller_returncode=load(OUT / 'operations/manual_search_activity.operation.json')['returncode'],
    original_protected_files=len(auth['protected_files']), historical_protection_pass=True,
    original_98_record_prefix_sha256=auth['samples_prefix_sha256'],
    original_98_record_prefix_bytes=auth['samples_prefix_bytes'],
    random_trajectory_unchanged=True, original_greedy_two_observations_unchanged=True,
    sample_classifications=dict(collections.Counter(s['classification'] for s in samples)),
    targets=len(samples), new_targets=len(samples)-98, unique_run_ids=len({s['run_id'] for s in samples}),
    accepted_target_samples=len(accepted_ids), unaccepted_samples=[
        {k:s.get(k) for k in ('run_id','attempt_id','classification','returncode','score_seconds','process_wall_seconds')}
        for s in pending],
    power_identity_recomputation=validation, standby_records=standby_events(records),
    power_messages=[{k:e[k] for k in ('record_id','event_id','provider','time_utc','message')}
                    for r in records for e in r['events']],
    power_note='System 506 explicitly reports Lid; 507 and later 506 report Austerity Battery Drain Budget Exceeded. Raw XML is retained. Initial AC pass is not evidence of continuous AC. No inference about user intent or physical clock calibration.',
    partial_evaluation_raw_seconds=scope['raw_seconds'],
    partial_process_qpc_seconds=(continuity['process_end_qpc']-continuity['process_start_qpc'])/continuity['qpc_frequency'],
    partial_cost_note='No matched FINISHED response; process QPC and evaluation RAW are different scopes. No same-scope calibration, subtraction or standby refund.',
    original_activity_qpc_seconds=auth['previous_activity_qpc_seconds'],
    continuation_activity_qpc_seconds=window['activity_qpc_seconds'],
    cumulative_activity_qpc_seconds=window['cumulative_activity_qpc_seconds'],
    ledger_remaining_seconds=43200-window['cumulative_activity_qpc_seconds'],
    budget_note='Use final window integer endpoints, not the later live-progress reading. Remaining ledger is not permission for another claim.',
    sleep_request=load(OUT/'continuation/sleep_request.json'),
    owned_process_snapshot=processes, owned_process_operation=operation,
    all_owned_experiment_processes_exited=(operation['returncode']==0 and not operation['timed_out']
        and not processes['windows_processes'] and not processes['matching_wsl_processes']))
atomic_write_json(OUT/'stop_review.json',result)
print(json.dumps({k:v for k,v in result.items() if k not in
    ('unaccepted_samples','standby_records','power_identity_recomputation','owned_process_operation')}, ensure_ascii=False))
raise SystemExit(0 if result['all_owned_experiment_processes_exited'] else 2)
