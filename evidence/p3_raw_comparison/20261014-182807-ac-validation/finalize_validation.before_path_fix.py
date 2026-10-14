"""Postprocess only after the one-shot controller exits; no experiment execution."""
import csv
import json
import re
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent
REPOSITORY = Path('E:/software_system/project01')
plan = json.loads((OUT / 'validation_plan.json').read_bytes())
sys.path.insert(0, plan['windows_archive_directory'])
from autotuner.core import sha256_file, utc_now, classify_execution
from scripts.p3_clock_contract import atomic_write_json, load
from scripts.raw_clock_contract import audit_clock, audit_gate
from scripts.raw_comparison_contract import audit_admission


def main():
    session = Path(plan['session_directory'])
    state = load(session / 'checkpoint.json'); window = load(session / 'window.json')
    independent = load(OUT / 'independent_validation_audit.json')
    if window['status'] == 'running': raise ValueError('Controller must exit before postprocessing')
    before = load(OUT / 'history_before.json')
    changed = [name for name, value in before['files'].items() if not (REPOSITORY / name).is_file() or
               sha256_file(REPOSITORY / name) != value['sha256']]
    if changed: raise ValueError('Historical evidence changed: ' + repr(changed))
    atomic_write_json(OUT / 'history_after.json', {'at': utc_now(), 'all_bytes_unchanged': True,
        'preserved_file_count': len(before['files']), 'changed': changed,
        'old_claim_and_AC_refusal_preserved': True, 'closed_grid_preserved': True,
        'teacher_original_sha256': sha256_file(REPOSITORY / 'code/original/matrix_multiplication.c')})
    old = load(REPOSITORY / 'evidence/p3_raw_grid/20261011-021601/final-content/grid-f705a488/checkpoint.json')
    samples = [json.loads(line) for line in (session / 'samples.jsonl').read_bytes().splitlines() if line] \
              if (session / 'samples.jsonl').exists() else []
    if len({s['run_id'] for s in samples}) != len(samples): raise ValueError('Duplicate run_id')
    rows = []
    for size in (128, 64, 24):
        config = {'optimization': 'O3', 'block_size': size}
        previous = next(g for g in old['completed'] if g['config'] == config)
        current = next((g for g in state['validation_groups'] if g['config'] == config), None)
        continuity = None
        if current:
            continuity = load(Path(current['checks_directory']) / 'continuity.json')['result']
        rows.append({'optimization': 'O3', 'block_size': size,
            'historical_grid_median_raw_seconds': previous['score_seconds'],
            'historical_grid_cv_percent': previous['statistics']['coefficient_of_variation'] * 100,
            'historical_grid_mad_seconds': previous['statistics']['median_absolute_deviation_seconds'],
            'independent_median_raw_seconds': current['score_seconds'] if current else None,
            'independent_cv_percent': current['statistics']['coefficient_of_variation'] * 100 if current else None,
            'independent_mad_seconds': current['statistics']['median_absolute_deviation_seconds'] if current else None,
            'median_change_percent': (current['score_seconds']/previous['score_seconds'] - 1) * 100 if current else None,
            'correctness_pass': all(s['classification'] == 'success' and s['target_result']['checked_entries'] == 4096**2
                                    for s in current['samples']) if current else 'not_accepted',
            'timing_contract_pass': bool(current),
            'uninterrupted_execution': continuity['uninterrupted_execution'] if continuity else 'not_certified',
            'group_evaluation_raw_seconds': current['evaluation_wall_seconds'] if current else None,
            'group_QPC_envelope_seconds': continuity['evaluation_qpc_seconds'] if continuity else None,
            'same_scope_RAW_seconds': continuity['evaluation_raw_seconds'] if continuity else None,
            'group_QPC_RAW_difference_seconds': continuity['absolute_difference_seconds'] if continuity else None,
            'status': 'accepted' if current else 'not_accepted'})
    atomic_write_json(OUT / 'three_configuration_comparison.json', rows)
    with (OUT / 'three_configuration_comparison.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, list(rows[0])); writer.writeheader(); writer.writerows(rows)
    clock_results = []
    for directory in sorted(session.rglob('manifest.json')):
        manifest = load(directory)
        if manifest.get('schema') != 'raw-comparison-clock-manifest-v1': continue
        result = audit_clock(directory.parent, manifest['context'])
        clock_results.append({'directory': directory.parent.relative_to(session).as_posix(),
                              'purpose': manifest['purpose'], 'audit': result})
    atomic_write_json(OUT / 'all_clock_checks_independent.json', clock_results)
    gate_results = []
    measurement = load(Path(plan['windows_archive_directory']) / 'configs/measurement_protocol.json')
    for path in sorted(session.rglob('gate_manifest.json')):
        manifest = load(path)
        verified = audit_gate(path.parent, measurement, manifest['purpose'], manifest['context'])
        snapshots = []
        outcome = load(path.parent / 'gate_outcome.json')
        for name in outcome['operations']:
            op = load(path.parent / (name + '.operation.json'))
            raw = load(path.parent / op['stdout_path']) if (path.parent / op['stdout_path']).stat().st_size else {}
            snapshots.append({'operation': name, 'returncode': op['returncode'], 'timed_out': op['timed_out'],
                'host_minimum_available_bytes': raw.get('host_minimum_available_bytes'),
                'host_minimum_commit_headroom_bytes': raw.get('host_minimum_commit_headroom_bytes'),
                'wsl_available_bytes': raw.get('wsl_available_bytes'),
                'host_cpu_average_percent': raw.get('host_cpu_average_percent'),
                'host_cpu_maximum_percent': raw.get('host_cpu_maximum_percent'),
                'warnings': raw.get('warnings'), 'rejection_reasons': raw.get('rejection_reasons')})
        gate_results.append({'directory': path.parent.relative_to(session).as_posix(), 'purpose': manifest['purpose'],
            'pass': verified, 'qpc_seconds': outcome['qpc_seconds'], 'snapshots': snapshots})
    atomic_write_json(OUT / 'all_resource_gates_independent.json', gate_results)
    # Explicit contract recomputation for every saved run, including unaccepted
    # partial groups. Scores are reported only for independently accepted groups.
    checked = []; peaks = []; host_warnings = []; all_contracts = True
    for sample in samples:
        expected = {'n': 4096, 'block_size': sample['config']['block_size'], 'seed': 20261008,
            'input': 'random', 'input_generator': 'splitmix64-interleaved-v1', 'abs_tol': 1e-12,
            'rel_tol': 1e-12, 'primary_clock': 'CLOCK_MONOTONIC_RAW', 'timing_protocol_version': '2026-10-11-raw-formal-v1'}
        classification, parsed, detail = classify_execution(sample['returncode'], sample['timed_out'], sample['raw_stdout'],
            expected_schema='matrix-multiplication-result-v2', expected=expected)
        valid = classification == 'success' and parsed == sample['target_result'] and sample['source'] == 'fresh_measurement' and \
                sample['context']['force_remeasure'] is True
        all_contracts = all_contracts and valid
        run = session / 'runs' / Path(sample['run_directory']).name
        text = (run / 'resource.txt').read_text()
        maximum = re.search(r'Maximum resident set size \(kbytes\):\s*(\d+)', text)
        if maximum: peaks.append(int(maximum.group(1)))
        checked.append({'run_id': sample['run_id'], 'role': sample['role'], 'config': sample['config'],
            'classification': classification, 'detail': detail, 'fresh_and_contract_pass': valid,
            'checked_entries': parsed.get('checked_entries') if parsed else None,
            'raw_start_ns': parsed.get('raw_start_ns') if parsed else None,
            'raw_end_ns': parsed.get('raw_end_ns') if parsed else None})
    atomic_write_json(OUT / 'all_sample_contracts_independent.json', checked)
    target_calls_started = len(list((session / 'runs').glob('*/process.json')))
    accepted_samples = {s['run_id'] for g in state['validation_groups'] for s in g['samples']}
    admission_intervals = sum(v['audit']['interval_count'] for v in clock_results if v['purpose'] == 'admission')
    group_intervals = sum(v['audit']['interval_count'] for v in clock_results if v['purpose'] != 'admission')
    native_seconds = sum(load(session / v['directory'] / 'native_process.json')['qpc_seconds'] for v in clock_results)
    evaluation_seconds = sum(g['evaluation_wall_seconds'] for g in state['validation_groups'])
    core_seconds = sum(s.get('score_seconds') or 0 for s in samples)
    outer = load(OUT / 'operations/validation_activity.operation.json')
    costs = {'activity_qpc_seconds': window['activity_qpc_seconds'], 'activity_budget_seconds': 3600,
        'validation_process_qpc_seconds': outer['qpc_seconds'], 'setup_raw_seconds': state.get('setup_raw_seconds'),
        'accepted_group_evaluation_raw_seconds': evaluation_seconds, 'all_saved_core_raw_seconds_including_warmups': core_seconds,
        'resource_gate_qpc_seconds': sum(v['qpc_seconds'] for v in gate_results), 'native_clock_process_qpc_seconds': native_seconds,
        'candidate_retest_cost_seconds': 0, 'search_cost_seconds': 0,
        'reference_generation_calls': state['reference_generation_calls'],
        'partially_scored_samples': len(samples) - len(accepted_samples),
        'scope': 'Activity QPC includes setup, gates/waits, admission/boundaries, measurement/verification, continuity and cleanup. Process envelope includes activity/startup. Nested RAW/gates/probes are not added to outer envelopes. Preparation/postprocessing/git excluded. No old Grid refunds or calibration.'}
    atomic_write_json(OUT / 'costs.json', costs)
    complete = independent['validation_complete'] and independent['validation_timing_checks_pass'] and all_contracts and window['status'] == 'complete'
    summary = {'status': 'P3_RAW_THREE_CONFIG_VALIDATION_COMPLETE' if complete else 'P3_RAW_VALIDATION_PARTIAL',
        'at': utc_now(), 'execution_content_sha': plan['content_commit'], 'validation_session': plan['session_id'],
        'measurement_content_sha': plan['measurement_content'], 'comparison_protocol_hash': plan['comparison_protocol_hash'],
        'validation_complete': bool(complete), 'validation_timing_checks_pass': independent['validation_timing_checks_pass'],
        'evidence_integrity_pass': independent['evidence_integrity_pass'] and all_contracts,
        'execution_complete': False, 'timing_checks_pass': False, 'comparison_ready': False,
        'target_executions_started': target_calls_started, 'target_executions_recorded': len(samples),
        'warmups': sum(s['role'] == 'warmup' for s in samples), 'measurements': sum(s['role'] == 'measurement' for s in samples),
        'fresh_samples': sum(s['source'] == 'fresh_measurement' and s['context']['force_remeasure'] is True for s in samples),
        'full_matrix_contracts_pass': all_contracts, 'completed_validation_groups': len(state['validation_groups']),
        'admission_intervals': admission_intervals, 'group_clock_intervals': group_intervals,
        'monotonic_warning_intervals': sum(len(v['audit'].get('monotonic_warning_indices', [])) for v in clock_results),
        'partial_samples': len(samples)-len(accepted_samples), 'search_trajectories': 0, 'search_evaluations': 0,
        'prefix_candidate_retests': 0, 'maximum_target_peak_rss_kib': max(peaks) if peaks else None,
        'power': load(session / 'ac_status.json'), 'sleep_request': load(session / 'sleep_request.json'),
        'activity_qpc_seconds': window['activity_qpc_seconds'], 'stop_reason': window['failure_reason'],
        'blocking_condition': 'Evidence drive E: exhausted; WSL checkpoint write EIO then Windows failure checkpoint save ENOSPC',
        'controller_returncode': outer['returncode'],
        'durable_checkpoint_status': state['status'],
        'checkpoint_state_note': 'ready is the last durable two-group checkpoint, not evidence the failed controller completed; not manually rewritten',
        'remaining_configurations': [{'optimization': 'O3', 'block_size': 24}],
        'delivery_worktree': str(OUT.parents[2]), 'original_worktree_preserved': str(REPOSITORY),
        'historical_files_unchanged': len(before['files']), 'postprocess_source_sha256': sha256_file(Path(__file__)),
        'next_step': 'Stop for external audit; no real Random/Greedy search is run or automatically started'}
    atomic_write_json(OUT / 'delivery_summary.json', summary)
    print(json.dumps({'summary': summary, 'comparison_rows': rows, 'costs': costs}, ensure_ascii=False), flush=True)


if __name__ == '__main__': main()
