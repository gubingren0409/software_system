"""Read-only review of the stopped activity. Does not start targets or rewrite the session."""
import collections
import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent
plan = json.loads((OUT / 'content/search_plan.json').read_bytes())
sys.path.insert(0, plan['windows_archive_directory'])
from autotuner.core import sha256_file
from scripts.p3_clock_contract import atomic_write_json, capture, load
from scripts.raw_comparison_power import standby_events, validate_event_record

session = Path(plan['session_directory'])
state = load(session / 'checkpoint.json')
window = load(session / 'window.json')
attempt = state['active']['attempt_id']
checks = session / 'group_checks' / attempt
power_directory = checks / 'power_events'
power_paths = sorted(power_directory.glob('events_*.stdout.txt'), key=lambda p: int(p.name.split('_')[1].split('.')[0]))
records = [load(path) for path in power_paths]
validation = []
cursor = -1
boot = None
for path, record in zip(power_paths, records):
    try:
        validate_event_record(record, cursor, boot)
        accepted = True
        reason = None
    except (ValueError, KeyError, TypeError) as error:
        accepted = False
        reason = str(error)
    validation.append(dict(file=str(path.relative_to(OUT)), sha256=sha256_file(path),
        identity_accepted=accepted, reason=reason, boot_utc=record['windows_boot_utc'],
        cursor_before=record['cursor_before'], cursor_after=record['cursor_after']))
    if accepted:
        cursor = record['cursor_after']
        boot = record['windows_boot_utc']

samples = [json.loads(line) for line in (session / 'samples.jsonl').read_bytes().splitlines() if line]
scored = [g for t in state['trajectories'].values() for g in t['observations'] + t['retests']]
accepted_ids = {s['run_id'] for g in scored for s in g['samples']}
partial = [s for s in samples if s['run_id'] not in accepted_ids]
clock_files = list(session.rglob('native_process.json'))
gates = [load(path) for path in session.rglob('gate_outcome.json')]
gate_stdout = list(session.rglob('resources/sample_*.stdout.txt'))
snapshot_summaries = []
for path in gate_stdout:
    value = load(path)
    snapshot_summaries.append(dict(file=str(path.relative_to(OUT)),
        warnings=value.get('warnings'), purpose=value.get('purpose'),
        formal_gate=value.get('formal_gate'), recovery_gate=value.get('recovery_gate')))

process_command = [
    'C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe', '-NoProfile', '-Command',
    "[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false); "
    "$ownedWindows=@(Get-Process -Id 48912,70360 -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,StartTime); "
    "$wslText=@(& wsl.exe -d Ubuntu-24.04 -- ps -eo pid,ppid,stat,args); $wslExit=$LASTEXITCODE; "
    "$ownedWsl=@($wslText | Select-String -Pattern 'matrix-raw-comparison-(content|cache)-776b111|p3_raw_first_seed/20261019-132400|^\\s*11952\\s' | ForEach-Object { $_.Line }); "
    "[ordered]@{windows_processes=$ownedWindows;wsl_ps_returncode=$wslExit;matching_wsl_processes=$ownedWsl;at=[DateTimeOffset]::Now.ToString('o')} | ConvertTo-Json -Depth 5; "
    "if ($wslExit -ne 0) {exit 2}"
]
operation = capture(process_command, OUT / 'stop_processes', 'owned_processes', 'stopped-first-seed', timeout=30)
process_snapshot = load(OUT / 'stop_processes' / operation['stdout_path'])
continuity = load(checks / 'continuity.json')
scope = load(checks / 'evaluation_scope.json')
result = dict(schema='first-seed-stop-review-v1', stop_reason=window['failure_reason'],
    controller_returncode=load(OUT / 'operations/search_activity.operation.json')['returncode'],
    content_commit=plan['content_commit'], session_id=plan['session_id'], active=state['active'],
    sample_classifications=dict(collections.Counter(s['classification'] for s in samples)),
    targets=len(samples), unique_run_ids=len({s['run_id'] for s in samples}),
    scored_target_samples=len(accepted_ids), unaccepted_samples=[
        {key: s.get(key) for key in ('run_id', 'classification', 'returncode', 'score_seconds', 'process_wall_seconds')}
        for s in partial],
    power_identity_recomputation=validation,
    standby_records=standby_events(records),
    power_messages=[{key: event[key] for key in ('record_id','event_id','provider','time_utc','message')}
        for record in records for event in record['events']],
    power_note='Modern Standby is proven by raw System 506/507 messages including Lid. Boot-time estimate string changed; that alone does not prove a reboot or log reset. Frozen controller refused identity before its standby-message branch. No source change or retry.',
    partial_evaluation_raw_seconds=scope['raw_seconds'],
    partial_process_qpc_seconds=(continuity['process_end_qpc']-continuity['process_start_qpc'])/continuity['qpc_frequency'],
    partial_cost_note='Guest evaluation RAW covers the failed two-sample group. Host process QPC also includes startup and stop. Missing matched FINISHED envelope means no valid same-scope continuity comparison; do not subtract these ranges or refund standby.',
    native_processes=len(clock_files), native_intervals=sum(load(p)['saved_intervals'] for p in clock_files),
    completed_group_checks=2*len(scored), partial_group_checks=1,
    gate_calls=len(gates), gate_rejections=sum(not g['admitted'] for g in gates),
    gate_qpc_seconds=sum(g['qpc_seconds'] for g in gates), resource_snapshot_summaries=snapshot_summaries,
    owned_process_snapshot=process_snapshot, owned_process_operation=operation,
    all_owned_experiment_processes_exited=(operation['returncode']==0 and not process_snapshot['windows_processes'] and not process_snapshot['matching_wsl_processes']),
    auxiliary_source_sha256=sha256_file(Path(__file__)))
atomic_write_json(OUT / 'stop_review.json', result)
print(json.dumps({key: value for key, value in result.items() if key not in
    ('standby_records','resource_snapshot_summaries','owned_process_operation')}, ensure_ascii=False))
raise SystemExit(0 if result['all_owned_experiment_processes_exited'] else 2)
