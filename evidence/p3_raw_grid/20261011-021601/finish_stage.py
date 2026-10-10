"""Read-only runtime/history checks and derived handoff after the one-shot stage stops."""
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from autotuner.core import ConfigSpace, sha256_file, utc_now
from scripts.p3_clock_contract import atomic_write_json, capture, load, snapshot_campaign
from autotuner.session import source_identity


def main():
    directory = HERE / 'final-content'
    if not (directory / 'frozen_cwd_result.json').exists():
        raise ValueError('Stage is still active: do not finalize open evidence streams')
    plan = load(directory / 'plan.json')
    session = Path(plan['session_directory'])
    state = load(session / 'checkpoint.json')
    audit = load(directory / 'grid_audit_archive.json')
    recovery = load(directory / 'recovery_recomputed_archive.json')
    manifest = load(directory / 'recovery/manifest.json')
    worktree_files = source_identity(ROOT, manifest['git_files'])
    archive_files = source_identity(Path(plan['windows_archive_directory']), manifest['git_files'])
    correction = {
        'captured_at': utc_now(), 'formal_content_changed': False, 'additional_recovery_invocations': 0,
        'first_failure': 'Absolute direct script CLI lacked package root: ModuleNotFoundError autotuner; original stderr retained.',
        'second_failure': 'Auxiliary capture has module ROOT cwd, so -m imported worktree, not archive. Strict byte check correctly rejected.',
        'corrected_invocation': 'Capture imported from exact archive; module CLI cwd is archive; no PYTHONPATH and no byte normalization bypass.',
        'worktree_byte_differences': [{'path': k, 'worktree_sha256': v['executed_sha256'],
            'archive_sha256': manifest['source_sha256'][k], 'same_git_blob': v['git_blob_sha1'] == manifest['git_files'][k]}
            for k, v in worktree_files.items() if v['executed_sha256'] != manifest['source_sha256'][k]],
        'archive_bytes_still_match_manifest': {k: v['executed_sha256'] for k, v in archive_files.items()} == manifest['source_sha256'],
        'helper_sha256': {name: sha256_file(HERE / name) for name in
            ('execute_stage.py', 'continue_after_audit_invocation.py', 'run_from_frozen_archive.py')},
        'prior_failed_launch_records': ['launch_result.json', 'continuation_result.json'],
        'authoritative_recompute': 'recovery_recomputed_archive.json',
        'postprocessing_correction': {
            'initial_source_sha256': sha256_file(HERE / 'finish_stage_initial.py'),
            'current_source_sha256': sha256_file(Path(__file__)),
            'initial_failed_operation': 'finalize.operation.json',
            'reason': 'The initial finisher included its own still-open parent capture, which has no stdout_path yet.',
            'scope': 'Derived artifact helper only; no formal source edits, target calls, recovery, or resampling.'},
    }
    atomic_write_json(directory / 'auxiliary_invocation_correction.json', correction)
    original = load(HERE / 'history_before.json')['files']
    changed = [p for p, digest in original.items() if not (ROOT / p).exists() or sha256_file(ROOT / p) != digest]
    campaigns = {}
    for label, relative in (
        ('d6811cad', 'evidence/p3_memory_policy/20261010-174802-11f7775c/campaign-d6811cad'),
        ('7405fcc3', 'evidence/p3_resource_policy/20261010-143415/campaign-7405fcc3'),
        ('e308bfb', 'evidence/p3/campaign-e308bfb'),
    ):
        before = load(HERE / (label + '_before.json'))
        after = snapshot_campaign(ROOT / relative)
        atomic_write_json(HERE / (label + '_after.json'), after)
        compare = lambda d: {k: v for k, v in d.items() if k not in ('captured_at', 'captured_qpc')}
        campaigns[label] = {'unchanged': compare(before) == compare(after),
                            'checkpoint_sha256': after['checkpoint_sha256'],
                            'raw_record_count': sum(t['sample_count'] for t in after['trajectories'].values())}
    archive_command = ['wsl.exe', '-d', 'Ubuntu-24.04', '--', 'python3', '-c',
        "import pathlib,hashlib,json; r=pathlib.Path('/var/tmp/matrix-autotuner-p3-memory-content-d6811cadda8ecd7b46225ebe65c51831278694a0'); print(json.dumps({str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in r.rglob('*') if p.is_file() and '__pycache__' not in str(p) and p.parts[len(r.parts)] in ('autotuner','code','configs','scripts')}))"]
    archive_operation_name = 'd681_archive_after_' + str(os.getpid())
    archive_operation = capture(archive_command, HERE, archive_operation_name, HERE.name, timeout=60)
    old_archive = load(HERE / 'd681_archive_before.stdout.txt')
    new_archive = load(HERE / (archive_operation_name + '.stdout.txt')) if archive_operation['returncode'] == 0 else {}
    protection = {'captured_at': utc_now(), 'protected_file_count': len(original),
        'changed': changed, 'campaigns': campaigns, 'old_archive_file_count': len(old_archive),
        'old_archive_unchanged': old_archive == new_archive,
        'history_byte_protection_pass': not changed and old_archive == new_archive and
            all(v['unchanged'] for v in campaigns.values())}
    atomic_write_json(HERE / 'history_protection_after.json', protection)
    if audit['grid_complete'] and audit['evidence_integrity_pass']:
        def linux_path(value):
            value = str(value).replace('\\', '/')
            return '/mnt/' + value[0].lower() + value[2:]
        plot_command = ['wsl.exe', '-d', 'Ubuntu-24.04', '--cd', plan['archive_directory'], '--',
            'env', '-u', 'PYTHONPATH', 'PYTHONDONTWRITEBYTECODE=1', 'python3', 'scripts/plot_p2_results.py',
            '--session-directory', linux_path(session), '--output-directory', linux_path(directory / 'raw_grid_figures')]
        capture(plot_command, HERE, 'raw_grid_plots', HERE.name, timeout=120)
    operations = []
    operation_errors = []
    in_progress_operations = []
    for path in sorted(HERE.rglob('*.operation.json')):
        value = load(path)
        if value.get('pid') == os.getpid() and 'qpc_end' not in value:
            in_progress_operations.append(str(path.relative_to(HERE)))
            continue
        if any(key not in value for key in ('stdout_path', 'stderr_path', 'returncode')):
            operation_errors.append(str(path.relative_to(HERE)) + ': missing closed-operation fields')
            continue
        for key in ('stdout', 'stderr'):
            stream = path.parent / value[key + '_path']
            if sha256_file(stream) != value[key + '_sha256']:
                operation_errors.append(str(path.relative_to(HERE)) + ': ' + key + ' hash')
        expected_seconds = (value['qpc_end'] - value['qpc_start']) / value['qpc_frequency']
        if expected_seconds != value['qpc_seconds'] or type(value['returncode']) is not int:
            operation_errors.append(str(path.relative_to(HERE)) + ': QPC/exit')
        operations.append({'path': str(path.relative_to(HERE)), 'returncode': value['returncode'],
            'timed_out': value['timed_out'], 'qpc_seconds': value['qpc_seconds'],
            'operation_sha256': sha256_file(path), 'command': value['command'], 'pid': value['pid']})
    atomic_write_json(HERE / 'closed_operation_verification.json', {
        'captured_at': utc_now(), 'pass': not operation_errors, 'errors': operation_errors,
        'in_progress_operations': in_progress_operations,
        'scope': 'Closed operations only; the current parent capture is verified after this child exits.',
        'operation_count': len(operations), 'operations': operations})
    records_path = session / 'samples.jsonl'
    records = [json.loads(line) for line in records_path.read_text().splitlines() if line] if records_path.exists() else []
    completed = state['completed']
    config_rows = []
    for index, config in enumerate(ConfigSpace.load(ROOT / 'configs/config_space.json').all()):
        group = next((g for g in completed if g['config'] == config.__dict__), None)
        partial = [r for r in records if r['config'] == config.__dict__ and not group]
        stats = group['statistics'] if group else {}
        config_rows.append({'index': index, **config.__dict__,
            'status': 'completed_valid' if group else ('partial_unscored' if partial else 'not_executed'),
            'raw_target_executions': sum(bool(r.get('timed_command')) for r in records if r['config'] == config.__dict__),
            'score_raw_seconds': group['score_seconds'] if group else None,
            'cv': stats.get('coefficient_of_variation'),
            'mad_raw_seconds': stats.get('median_absolute_deviation_seconds'),
            'minimum_raw_seconds': stats.get('minimum_seconds'), 'maximum_raw_seconds': stats.get('maximum_seconds')})
    with (directory / 'grid_status_20.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(config_rows[0]))
        writer.writeheader()
        writer.writerows(config_rows)
    batches = []
    for path in sorted(directory.rglob('native_process.json')):
        operation = load(path)
        rows = [json.loads(line) for line in (path.parent / 'intervals.jsonl').read_text().splitlines() if line]
        messages = [json.loads(line) for line in (path.parent / 'messages.jsonl').read_text().splitlines() if line]
        batches.append({'directory': str(path.parent.relative_to(directory)),
            'interval_count': len(rows), 'response_count': len(messages),
            'raw_failed_indices': [r['planned']['index'] for r in rows if not r['check']['raw_pass']],
            'qpc_seconds': operation['qpc_seconds'], 'native_pid': operation['hello']['pid'],
            'returncode': operation['returncode']})
    audited_checks = [{'batch': 'recovery', **check} for check in recovery['checks']]
    for batch in audit.get('group_clock_batches', []):
        audited_checks.extend({'batch': batch['directory'], **check} for check in batch['audit']['checks'])
    clock_statistics = {'source': 'Independent exact-archive recomputation, never a saved PASS-only decision',
        'checked_interval_count': len(audited_checks),
        'raw_unpadded_pass_count': sum(c['within_host_unpadded']['raw'] for c in audited_checks),
        'raw_with_allowance_pass_count': sum(c['raw_pass'] for c in audited_checks),
        'maximum_communication_uncertainty_seconds': max((c['uncertainty_seconds'] for c in audited_checks), default=None),
        'maximum_raw_read_span_ns': max((max(c['read_spans_ns']['raw']) for c in audited_checks), default=None),
        'monotonic_warning_intervals': [{'batch': c['batch'], 'index': c['index']} for c in audited_checks
            if not c['within_host_with_allowance']['monotonic']],
        'raw_failed_intervals': [{'batch': c['batch'], 'index': c['index']} for c in audited_checks if not c['raw_pass']],
        'no_monotonic_equality_gate': True, 'calibration_applied': False}
    atomic_write_json(directory / 'clock_reading_summary.json', clock_statistics)
    gate_costs = [load(p)['qpc_seconds'] for p in session.rglob('gate_outcome.json')]
    controller = load(session / 'controller.json') if (session / 'controller.json').exists() else {}
    all_core = sum((r.get('target_result') or {}).get('elapsed_seconds', 0) or 0 for r in records)
    all_validation = sum((r.get('target_result') or {}).get('validation_seconds', 0) or 0 for r in records)
    costs = {'recovery_resource_collection_envelope_qpc_seconds': load(directory / 'recovery/recovery_operation.json')['qpc_seconds'],
        'formal_controller_including_recovery_and_intervening_auxiliary_qpc_seconds': controller.get('total_qpc_seconds'),
        'formal_invocation_qpc_seconds': load(directory / 'formal_grid.operation.json')['qpc_seconds'] if (directory / 'formal_grid.operation.json').exists() else 0,
        'setup_raw_seconds': state.get('setup_seconds', 0),
        'build_setup_raw_seconds': state.get('build_setup_seconds', 0),
        'reference_setup_raw_seconds': state.get('reference_setup_seconds', 0),
        'accepted_configuration_evaluation_raw_seconds': sum(g['evaluation_wall_seconds'] for g in completed),
        'all_saved_target_core_raw_seconds_including_warmups_and_partials': all_core,
        'all_saved_target_validation_raw_seconds': all_validation,
        'formal_gates_including_wait_qpc_seconds': sum(gate_costs),
        'all_native_probe_invocations_qpc_seconds': sum(b['qpc_seconds'] for b in batches),
        'independent_retest_cost_seconds': 0, 'search_cost_seconds': 0,
        'scopes': 'Outer budget begins at recovery and includes auxiliary invocation correction idle time. Formal invocation includes setup/gates/group probes/measurements. Setup contains build/reference. Group includes core/validation/process/lookups. These overlapping fields must not all be added. Auxiliary captured commands are itemized separately in closed_operation_verification.json; no trusted MONOTONIC calibration/total.'}
    atomic_write_json(directory / 'costs.json', costs)
    resource_quality = []
    for record in records:
        def reported_integer(label):
            match = re.search(re.escape(label) + r':\s*(\d+)', record.get('raw_resource', ''))
            return int(match.group(1)) if match else None
        before_resource = record.get('resource_before', {})
        after_resource = record.get('resource_after', {})
        snapshots = [before_resource, *record.get('resource_samples', []), after_resource]
        snapshots = [s for s in snapshots if isinstance(s, dict) and s]
        hosts = [s['host'] for s in snapshots if isinstance(s.get('host'), dict)]
        resource_quality.append({'run_id': record['run_id'], 'config': record['config'],
            'sample_index': record['sample_index'], 'classification': record['classification'],
            'maximum_rss_kib': reported_integer('Maximum resident set size (kbytes)'),
            'major_page_faults': reported_integer('Major (requiring I/O) page faults'),
            'reported_swaps': reported_integer('Swaps'),
            'wsl_snapshot_count': len(snapshots), 'host_snapshot_count': len(hosts),
            'minimum_wsl_available_bytes': min((s['mem_available_bytes'] for s in snapshots if 'mem_available_bytes' in s), default=None),
            'before_swap_free_bytes': before_resource.get('swap_free_bytes', 'unknown'),
            'after_swap_free_bytes': after_resource.get('swap_free_bytes', 'unknown'),
            'before_vmstat': before_resource.get('vmstat', 'unknown'), 'after_vmstat': after_resource.get('vmstat', 'unknown'),
            'host_unknown_count': sum(h.get('status') == 'unknown' for h in hosts)})
    gates = []
    for path in sorted(directory.rglob('*.operation.json')):
        op = load(path)
        if 'stdout_path' not in op:
            continue
        raw = path.parent / op['stdout_path']
        try:
            gate = load(raw)
        except (ValueError, OSError):
            continue
        if not isinstance(gate, dict) or not gate.get('schema', '').startswith('p2-resource-gate'):
            continue
        gates.append({'operation': str(path.relative_to(directory)), 'returncode': op['returncode'],
            'mode': gate.get('mode'), 'admission_gate': gate.get('admission_gate', gate.get('formal_gate')),
            'warnings': gate.get('warnings'), 'rejection_reasons': gate.get('rejection_reasons'),
            'host_minimum_available_bytes': gate.get('host_minimum_available_bytes'),
            'host_minimum_commit_headroom_bytes': gate.get('host_minimum_commit_headroom_bytes'),
            'wsl_available_bytes': gate.get('wsl_available_bytes'),
            'host_cpu_average_percent': gate.get('host_cpu_average_percent'),
            'host_cpu_maximum_percent': gate.get('host_cpu_maximum_percent')})
    atomic_write_json(directory / 'resource_quality.json', {
        'runs': resource_quality, 'gate_samples': gates,
        'scope': 'RSS is per target process, not total system peak. WSL vmstat swap counters are cumulative; before/after retained. Host snapshots are about 30s, WSL about 5s; neither is a continuous guarantee. Missing diagnostics remain unknown. Warning or admission does not prove stable performance; no slow sample filtering.'})
    summary = {'captured_at': utc_now(), 'content_commit': plan['content_commit'], 'session_id': plan['session_id'],
        'archive_directory': plan['archive_directory'], 'timing_protocol_hash': plan['timing_protocol_hash'],
        'measurement_protocol_hash': plan['measurement_protocol_hash'],
        'evidence_integrity_pass': audit['evidence_integrity_pass'] and protection['history_byte_protection_pass'] and not operation_errors,
        'grid_complete': audit['grid_complete'], 'grid_timing_checks_pass': audit['grid_timing_checks_pass'],
        'execution_complete': False, 'timing_checks_pass': False, 'comparison_ready': False,
        'p3_scope': 'Grid only; no Random/Greedy trajectories or independent candidate retests in this stage',
        'recovery_eligible': recovery['recovery_eligible'], 'recovery_attempts': 1,
        'recovery_intervals': recovery['interval_count'], 'recovery_raw_failed_indices': recovery.get('raw_failure_indices'),
        'recovery_monotonic_warning_indices': recovery.get('monotonic_warning_indices'),
        'native_clock_batches': batches, 'native_interval_count': sum(b['interval_count'] for b in batches),
        'native_response_count': sum(b['response_count'] for b in batches),
        'completed_configurations': len(completed), 'valid_configurations': audit.get('valid_configuration_count', 0),
        'saved_formal_target_executions': sum(bool(r.get('timed_command')) for r in records),
        'small_diagnostic_target_executions': 1, 'small_reference_generator_calls': 1,
        'formal_reference_generator_calls': state['reference_generation_calls'],
        'raw_record_count': len(records), 'run_id_count': len({r['run_id'] for r in records}),
        'partial_or_unaccepted_executions': audit.get('partial_or_unaccepted_executions'),
        'abandoned_groups': len(state['abandoned_attempts']),
        'complete_search_trajectories': 0, 'independent_retest_groups': 0,
        'lowest_median_observation': audit.get('lowest_median_observation'),
        'controller_status': controller.get('status'), 'failure_reason': controller.get('failure_reason'),
        'audit_errors': audit['errors'], 'historical_protection_pass': protection['history_byte_protection_pass']}
    atomic_write_json(directory / 'delivery_summary.json', summary)
    print(json.dumps({k: v for k, v in summary.items() if k not in ('native_clock_batches', 'lowest_median_observation')}))
    return 0 if summary['evidence_integrity_pass'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
