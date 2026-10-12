"""Read-only packaging of the one manually authorized remaining-budget attempt."""
import hashlib, importlib, importlib.util, json, os, re, shutil, subprocess
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main():
    freeze = json.loads((HERE / 'auxiliary_freeze.json').read_bytes())
    spec = importlib.util.spec_from_file_location('frozen_segment_helper',
        Path(freeze['archive_directory']) / 'scripts/raw_grid_segment.py')
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    auth = helper.read(HERE / 'window/authorization.json'); plan = helper.read(auth['plan_file'])
    f = helper.frozen(plan); closed = importlib.import_module('scripts.raw_clock_contract').checked_operation
    resource = importlib.import_module('autotuner.resources')
    policy, policy_path, collector_lf = resource.protocol_policy(f.validate_plan(plan)[0])
    session = Path(plan['session_directory']); state = helper.read(session / 'checkpoint.json')
    window = helper.read(HERE / 'window/window.json')
    audit = helper.read(HERE / 'window/independent_segment_audit.json')
    base = helper.read(HERE / 'window/frozen_measurement_audit.json')
    records = helper.rows(session / 'samples.jsonl'); errors = []
    helper.verify_protection(auth, plan)
    if not audit['evidence_integrity_pass']: errors.append('Independent segment audit failed')
    historical = helper.read(ROOT / 'evidence/p3_raw_grid/20261011-021601/history_before.json')['files']
    changed = [p for p, value in historical.items() if not (ROOT / p).exists() or helper.digest(ROOT / p) != value]
    if changed: errors.append('Older protected history changed')
    def git(*args):
        return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, check=True).stdout
    old_paths = set(git('ls-tree', '-r', '--name-only', helper.MANUAL_BASELINE, '--', 'evidence').decode().splitlines())
    modifications = set(git('diff', helper.MANUAL_BASELINE, '--name-only', '--', 'evidence').decode().splitlines())
    allowed = {str((session / p).relative_to(ROOT)).replace('\\', '/')
        for p in ('checkpoint.json', 'samples.jsonl', 'grid_summary.csv', 'progress.json')}
    unexpected = sorted((modifications & old_paths) - allowed)
    if unexpected: errors.append('Unapproved historical evidence modifications')
    frozen_changes = git('diff', helper.CONTENT, '--name-only', '--', '.gitattributes', 'autotuner', 'code', 'configs', 'scripts', 'tests').decode().splitlines()
    if set(frozen_changes) != {'scripts/raw_grid_segment.py', 'tests/test_raw_grid_segment.py'}:
        errors.append('Frozen measurement worktree changed')
    static_matches = {p: helper.digest(session / p) == helper.digest(HERE / 'window/preserved' / p)
        for p in ('controller.json', 'initial_checkpoint.json')}
    if not all(static_matches.values()): errors.append('Historical controller/initial checkpoint changed')
    shutil.copy2(session / 'grid_summary.csv', HERE / 'grid_summary_20.csv')
    groups = state['completed']; best = min(groups, key=lambda g: g['score_seconds']) if groups else None
    table = ['| Index | Configuration | Median RAW s | CV % | MAD s |', '| --- | --- | ---: | ---: | ---: |']
    for i, g in enumerate(groups):
        s = g['statistics']; c = g['config']
        table.append(f"| {i} | {c['optimization']}/s{c['block_size']} | {g['score_seconds']:.9f} | {100*s['coefficient_of_variation']:.3f} | {s['median_absolute_deviation_seconds']:.9f} |")
    (HERE / 'grid_table.md').write_text('\n'.join(table) + '\n', encoding='utf-8')
    # The real Windows event messages identify a lid-triggered Modern Standby.
    # UTC label difference is descriptive, never subtracted from the QPC budget.
    event_path = HERE / 'operations/monitor_gap_power_events.stdout.txt'
    events = helper.read(event_path); endpoints = {}
    for event in events['events']:
        match = re.fullmatch(r'/Date\((\d+)\)/', event['TimeCreated'])
        if event['Id'] in (506, 507) and match:
            endpoints[event['Id']] = int(match.group(1))
    affected = next(g for g in groups if g['config'] == {'optimization': 'O3', 'block_size': 24})
    sample = affected['samples'][5]
    operation = closed(HERE / 'window/operations', 'measure_' + affected['attempt_id'])
    before = datetime.fromisoformat(sample['resource_before']['captured_at'])
    after = datetime.fromisoformat(sample['resource_after']['captured_at'])
    if set(endpoints) != {506, 507} or not before.timestamp()*1000 < endpoints[506] < endpoints[507] < after.timestamp()*1000:
        errors.append('Standby event/sample temporal binding failed')
    sleep = {'event_source_sha256': helper.digest(event_path), 'events': events,
        'event_utc_start': datetime.fromtimestamp(endpoints[506]/1000, timezone.utc).isoformat(),
        'event_utc_end': datetime.fromtimestamp(endpoints[507]/1000, timezone.utc).isoformat(),
        'event_utc_label_gap_seconds': (endpoints[507]-endpoints[506])/1000,
        'affected_config': affected['config'], 'attempt_id': affected['attempt_id'], 'run_id': sample['run_id'],
        'sample_index': sample['sample_index'], 'sample_role': sample['role'],
        'sample_resource_utc_label_span_seconds': (after-before).total_seconds(),
        'sample_core_raw_seconds': sample['score_seconds'], 'sample_process_raw_seconds': sample['process_wall_seconds'],
        'sample_validation_raw_seconds': sample['target_result']['validation_seconds'],
        'group_measure_operation_qpc_seconds': operation['qpc_seconds'],
        'group_evaluation_raw_seconds': affected['evaluation_wall_seconds'],
        'sample_result_sha256': helper.digest(session / 'runs' / Path(sample['run_directory']).name / 'result.json'),
        'group_before_after_raw_checks_pass': all(b['audit']['raw_reference_pass'] for b in base['group_clock_batches'] if b['config_index']==17),
        'assessment': 'Confirmed lid-triggered standby inside sample 5. Frozen RAW contracts and group checks passed; this is not an uninterrupted benchmark. No sample removed, repeated, calibrated or replaced; no protocol changed.',
        'budget_action': 'Entire QPC envelope retained. No refund/reset; exact QPC-only suspend duration unknown (event timestamps are UTC labels).',
        'quality_limitation': 'Group-boundary probes do not certify continuity inside a matrix execution. Best observation/ranking is descriptive, not an independent stability claim.'}
    f.atomic_write_json(HERE / 'standby_analysis.json', sleep)
    gate_rows = []
    gate_directories = [HERE / 'window/preflight_gate'] + [session / 'group_checks' / g['attempt_id'] / 'resources' for g in groups[5:]]
    for directory in gate_directories:
        outcome = helper.read(directory / 'gate_outcome.json')
        for name in outcome['operations']:
            op = closed(directory, name); saved = helper.read(directory / op['stdout_path'])
            judged = resource.judge(saved, policy, 'Formal', helper.digest(policy_path))
            if any(saved[k] != judged[k] for k in ('checks', 'warnings', 'decision', 'rejection_reasons', 'policy_version', 'policy_hash')) or saved['collector_lf_sha256'] != collector_lf:
                errors.append('Resource recomputation differs: ' + str(directory))
            keys = ('decision', 'warnings', 'rejection_reasons', 'host_minimum_available_bytes',
                'host_minimum_commit_headroom_bytes', 'wsl_available_bytes', 'host_cpu_average_percent', 'host_cpu_maximum_percent')
            gate_rows.append({'path': str(directory.relative_to(ROOT)), 'operation': name,
                'returncode': op['returncode'], 'sample_count': len(saved['host_samples']), **{k: judged[k] for k in keys}})
    snapshots = [snap for r in records[30:] for snap in [r['resource_before'], *r['resource_samples'], r['resource_after']]]
    hosts = [s['host'] for s in snapshots if isinstance(s.get('host'), dict)]
    rss = [int(m.group(1)) for r in records[30:] if (m := re.search(r'Maximum resident set size \(kbytes\): (\d+)', r['raw_resource']))]
    quality = {'new_formal_gates': gate_rows, 'independent_resource_decisions_match': not any('Resource' in e for e in errors),
        'target_maximum_rss_kib': max(rss, default=0), 'guest_snapshot_count': len(snapshots), 'host_snapshot_count': len(hosts),
        'minimum_sampled_guest_available_bytes': min(s['mem_available_bytes'] for s in snapshots),
        'maximum_sampled_guest_swap_used_bytes': max(s['swap_total_bytes']-s['swap_free_bytes'] for s in snapshots),
        'maximum_guest_pswpin': max(s['vmstat']['pswpin'] for s in snapshots),
        'maximum_guest_pswpout': max(s['vmstat']['pswpout'] for s in snapshots),
        'minimum_runtime_host_available_bytes': min(h['host_minimum_available_bytes'] for h in hosts),
        'runtime_warning': 'Host <2GiB warnings and page activity retained. Snapshot is quality metadata, not a new Formal gate; CPU includes target load. Admission does not prove stable performance.'}
    f.atomic_write_json(HERE / 'resource_quality.json', quality)
    win = "[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false); [ordered]@{at=[DateTimeOffset]::Now.ToString('o');boot=(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime().ToString('o');controller_processes=@(Get-Process -Id " + str(window['controller_pid']) + " -ErrorAction SilentlyContinue | Select-Object Id,ProcessName);top_memory=@(Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 10 Id,ProcessName,WorkingSet64);vmmem=@(Get-Process VmmemWSL,Vmmem -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,WorkingSet64)} | ConvertTo-Json -Depth 5"
    op = f.capture([f.POWERSHELL, '-NoProfile', '-Command', win], HERE / 'operations', 'post_windows', 'remaining-finalize', timeout=40)
    host = helper.read(HERE / 'operations' / op['stdout_path']) if op['returncode']==0 else {'controller_processes':'unknown'}
    linux = """import os,json,pathlib
prefixes=('/var/tmp/matrix-raw-grid-content-3cc9e0d','/var/tmp/matrix-raw-grid-cache-3cc9e0d','/var/tmp/matrix-raw-grid-probe-3cc9e0d'); found=[]
for p in pathlib.Path('/proc').iterdir():
 if p.name.isdecimal() and int(p.name)!=os.getpid():
  try:
   if os.readlink(p/'exe').startswith(prefixes) or os.readlink(p/'cwd').startswith(prefixes): found.append({'pid':int(p.name),'name':(p/'comm').read_text().strip()})
  except (OSError,PermissionError): pass
print(json.dumps({'processes':found,'boot_id':pathlib.Path('/proc/sys/kernel/random/boot_id').read_text(),'meminfo':pathlib.Path('/proc/meminfo').read_text(),'vmstat':pathlib.Path('/proc/vmstat').read_text()}))"""
    op = f.capture(['wsl.exe','-d','Ubuntu-24.04','--cd','/tmp','--','python3','-c',linux], HERE / 'operations', 'post_wsl', 'remaining-finalize', timeout=40)
    guest = helper.read(HERE / 'operations' / op['stdout_path']) if op['returncode']==0 else {'processes':'unknown'}
    if host['controller_processes'] != [] or guest['processes'] != []: errors.append('Owned processes not confirmed exited')
    checked = []; own_open = []
    for path in HERE.rglob('*.operation.json'):
        value = helper.read(path)
        if value.get('pid') == os.getpid() and 'qpc_end' not in value:
            own_open.append(str(path.relative_to(HERE))); continue
        closed(path.parent, path.name.removesuffix('.operation.json'))
        checked.append({'path': path.relative_to(HERE).as_posix(), **{k: value[k] for k in ('qpc_start', 'qpc_end', 'qpc_frequency', 'qpc_seconds', 'returncode')}})
    auxiliary = [o for o in checked if o['path'].startswith('operations/') and o['path'] != 'operations/manual_run.operation.json']
    new_groups = groups[5:]; run_op = helper.read(HERE / 'operations/manual_run.operation.json')
    admission = helper.read(HERE/'window/independent_admission.json')
    costs = {'first_segment_qpc_seconds': helper.FIRST_SECONDS, 'previous_attempt_qpc_seconds': helper.PRIOR_USED_SECONDS,
        'manual_attempt_qpc_seconds': window['window_qpc_seconds'], 'second_window_qpc_seconds': window['second_window_activity_seconds'],
        'cumulative_qpc_envelope_seconds': window['cumulative_active_qpc_seconds'],
        'remaining_second_window_seconds': 14400-window['second_window_activity_seconds'],
        'continuation_preflight_gate_qpc_seconds': helper.read(HERE/'window/preflight_gate/gate_outcome.json')['qpc_seconds'],
        'continuation_admission_qpc_seconds': (admission['qpc_end']-admission['qpc_start'])/admission['qpc_frequency'],
        'new_group_gates_qpc_seconds': sum(helper.read(d/'gate_outcome.json')['qpc_seconds'] for d in gate_directories[1:]),
        'new_group_evaluation_raw_seconds': sum(g['evaluation_wall_seconds'] for g in new_groups),
        'new_target_core_raw_seconds': sum(g['compute_total_seconds'] for g in new_groups),
        'new_target_validation_raw_seconds': sum(g['validation_total_seconds'] for g in new_groups),
        'all_grid_nested_raw_costs': base['costs'], 'original_setup_raw_seconds': state['setup_seconds'],
        'new_build_seconds': 0, 'new_reference_generation_calls': 0, 'new_retest_seconds': 0, 'new_abandoned_attempt_seconds': 0,
        'outer_launch_capture_qpc_seconds': run_op['qpc_seconds'],
        'closed_helper_operations_qpc_seconds_not_deduplicated': sum(o['qpc_seconds'] for o in auxiliary), 'helper_operation_intervals_for_deduplication': auxiliary,
        'offline_pause_labels': helper.read(HERE/'window/epoch_and_pause.json'),
        'inclusion': 'Sum first + prior failed attempt + manual attempt QPC durations only; never absolute endpoints across epochs. Envelopes include gates/checks/setup and this manual standby. RAW costs, resource wait and outer wrapper are nested: do not add. Standby UTC duration is descriptive, not a QPC refund; offline review excluded. Listed helper intervals are an intermediate snapshot, NOT deduplicated (power event query is inside manual execution; post snapshots are inside finalizer). Use final_cost_index.json for non-overlapping auxiliary envelopes; edits/model/push excluded, not a whole-turn total.'}
    f.atomic_write_json(HERE / 'costs.json', costs)
    result = {**{k:audit[k] for k in ('grid_complete','grid_timing_checks_pass','execution_complete','timing_checks_pass','comparison_ready')},
        'evidence_integrity_pass': not errors, 'errors': errors, 'packaging_checks_pass': not errors,
        'postprocessor_sha256': helper.digest(Path(__file__)), 'content_commit': plan['content_commit'], 'session_id': plan['session_id'],
        'auxiliary_content_commit': freeze['auxiliary_content_commit'], 'completed_configurations': len(groups),
        'new_configurations': len(new_groups), 'target_executions': state['target_executions'], 'new_target_executions': len(records)-30,
        'unique_run_ids': len({r['run_id'] for r in records}), 'warmups': sum(r['role']=='warmup' for r in records),
        'measurements': sum(r['role']=='measurement' for r in records), 'group_clock_checks': len(base['group_clock_batches']),
        'fresh_continuation_intervals': len(helper.rows(HERE/'window/admission/intervals.jsonl')), 'first_recovery_intervals': 12,
        'partial_or_unaccepted_executions': base['partial_or_unaccepted_executions'], 'abandoned_attempts': state['abandoned_attempts'], 'active': state['active'],
        'independent_retest_groups': 0, 'search_trajectories': 0, 'small_matrix_executions_this_turn': 0,
        'reference_generation_calls': state['reference_generation_calls'], 'new_reference_generation_calls': 0,
        'protected_session_files': len(auth['protected_session_files']), 'protected_previous_files': len(auth['protected_previous_files']),
        'older_history_file_count': len(historical), 'older_history_changes': changed, 'unexpected_old_git_evidence_changes': unexpected,
        'allowed_live_append_state_changes': sorted(modifications & allowed), 'static_snapshot_byte_matches': static_matches,
        'frozen_worktree_content_changes': frozen_changes, 'teacher_sha256': helper.digest(ROOT/'code/original/matrix_multiplication.c'),
        'samples_prefix_sha256': hashlib.sha256((session/'samples.jsonl').read_bytes()[:auth['samples_prefix_bytes']]).hexdigest(),
        'lowest_median_observation': None if not best else {k:best[k] for k in ('config','score_seconds','statistics','attempt_id')},
        'owned_windows_controller_processes': host['controller_processes'], 'owned_wsl_experiment_processes': guest['processes'],
        'closed_operation_count': len(checked), 'closed_operations': checked, 'own_open_parent_operations': own_open,
        'quality_warning': 'Confirmed Modern Standby inside O3/s24 measurement5; unchanged frozen acceptance, no deletion/retest/calibration. Grid complete does not establish uninterrupted or stable performance.',
        'p3_status': 'Random/Greedy not run; P3 search comparison incomplete'}
    f.atomic_write_json(HERE / 'delivery_verification.json', result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('closed_operations',)}, ensure_ascii=False), flush=True)
    return 0 if not errors else 1


if __name__ == '__main__':
    raise SystemExit(main())
