"""Read-only derivation after AC refusal; never runs target, probe, gate or search."""
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from autotuner.core import sha256_file, sha256_json, utc_now
from scripts.p3_clock_contract import atomic_write_json

OUT = Path(__file__).resolve().parent


def load(path):
    return json.loads(Path(path).read_bytes())


def main():
    plan = load(OUT / 'content/validation_plan.json')
    search_plan = load(OUT / 'content/search_plan.json')
    session = Path(plan['session_directory']); state = load(session / 'checkpoint.json')
    search = load(Path(search_plan['session_directory']) / 'checkpoint.json')
    window = load(session / 'window.json'); independent = load(OUT / 'independent_validation_audit.json')
    old_plan = load(ROOT / 'evidence/p3_raw_grid/20261011-021601/final-content/plan.json')
    old_state = load(Path(old_plan['session_directory']) / 'checkpoint.json')
    old_audit = load(OUT / 'closed_grid_readonly_audit.json')
    before = load(OUT / 'history_before.json')
    changed = [name for name, value in before['files'].items()
               if not (ROOT / name).is_file() or sha256_file(ROOT / name) != value['sha256']]
    assert not changed, changed
    assert old_audit['evidence_integrity_pass'] and old_audit['grid_complete'] and old_audit['target_execution_count'] == 120
    assert state['target_executions'] == search['target_executions'] == 0 and not state['validation_groups']
    assert independent['evidence_integrity_pass'] and not independent['validation_complete']
    protection = {'at': utc_now(), 'protected_files': len(before['files']), 'all_bytes_unchanged': True,
        'changed_files': changed, 'old_grid_configurations': len(old_state['completed']),
        'old_grid_executions': old_state['target_executions'], 'old_samples_sha256': sha256_file(Path(old_plan['session_directory']) / 'samples.jsonl'),
        'old_initial_checkpoint_sha256': sha256_file(Path(old_plan['session_directory']) / 'initial_checkpoint.json'),
        'old_certificate_sha256': sha256_file(Path(old_plan['recovery_directory']) / 'certificate.json'),
        'teacher_original_sha256': sha256_file(ROOT / 'code/original/matrix_multiplication.c'),
        'old_grid_mutated': False, 'old_standby_sample_preserved': True,
        'old_d681_session_unchanged': True, 'scope': 'All files listed in history_before; closed Grid including checkpoints/controllers/claims/certificates/records, memory-policy and clock-repair histories; other history has no Git diff'}
    atomic_write_json(OUT / 'history_after.json', protection)
    annotation = []
    for group in old_state['completed']:
        interrupted = group['config'] == {'optimization': 'O3', 'block_size': 24}
        annotation.append({'config': group['config'], 'original_attempt': group['attempt_id'],
            'correctness_pass': True, 'timing_contract_pass': True,
            'uninterrupted_execution': False if interrupted else 'unknown',
            'reason': 'Historical Kernel-Power506/507 during measurement5, run6948e9aca2aa4b8eaf4b2085ef068731' if interrupted else 'No group-internal continuity certification in frozen Grid',
            'score_changed': False})
    atomic_write_json(OUT / 'closed_grid_quality_annotation.json', {'scope': 'Derived only; not a change to original acceptance/scores',
        'source_grid_audit_sha256': sha256_file(OUT / 'closed_grid_readonly_audit.json'),
        'source_standby_analysis_sha256': sha256_file(ROOT / 'evidence/p3_raw_grid/20261012-181149-manual-remaining/standby_analysis.json'),
        'groups': annotation})
    selected = [next(g for g in old_state['completed'] if g['config'] == {'optimization': 'O3', 'block_size': s}) for s in (128, 64, 24)]
    rows = []
    for group in selected:
        rows.append({'optimization': 'O3', 'block_size': group['config']['block_size'],
            'grid_median_raw_seconds': group['score_seconds'],
            'grid_cv': group['statistics']['coefficient_of_variation'],
            'grid_mad_seconds': group['statistics']['median_absolute_deviation_seconds'],
            'independent_median_raw_seconds': None, 'independent_cv': None, 'independent_mad_seconds': None,
            'change_percent': None, 'new_correctness_pass': 'not_executed', 'new_continuity_pass': 'not_executed',
            'status': 'not_executed_AC_power_refusal'})
    with (OUT / 'three_configuration_comparison.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, list(rows[0])); writer.writeheader(); writer.writerows(rows)
    atomic_write_json(OUT / 'three_configuration_comparison.json', rows)
    placeholders = [{'algorithm': a, 'budget': b, 'status': 'not_executed', 'unique_evaluations': 0,
        'candidate': None, 'own_median_seconds': None, 'independent_retest_median_seconds': None,
        'cv': None, 'mad_seconds': None, 'terminal_configuration_raw_seconds': None,
        'host_qpc_envelope_seconds': None, 'scope': 'Search results only; independent validation never feeds strategies'}
        for a in ('random', 'greedy') for b in (4, 8, 12)]
    atomic_write_json(OUT / 'first_seed_six_row_template.json', placeholders)
    with (OUT / 'first_seed_six_row_template.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, list(placeholders[0])); writer.writeheader(); writer.writerows(placeholders)
    # Operation envelopes can contain other captured operations. Select maximal
    # disjoint captured ranges only; the still-running finalizer is not included.
    operations = []
    for path in OUT.rglob('*.operation.json'):
        op = load(path)
        if type(op.get('qpc_end')) is int and type(op.get('qpc_start')) is int:
            operations.append((path, op))
    maximal = []
    for path, op in operations:
        if not any(other != path and other_op['qpc_frequency'] == op['qpc_frequency'] and
                other_op['qpc_start'] <= op['qpc_start'] and op['qpc_end'] <= other_op['qpc_end']
                for other, other_op in operations):
            maximal.append((path, op))
    activity_capture = next(op for path, op in operations if path.name == 'validation_activity.operation.json')
    auxiliary = [(path, op) for path, op in maximal if path.name != 'validation_activity.operation.json']
    costs = {'activity_windows': [{'session_id': plan['session_id'], 'qpc_seconds': window['activity_qpc_seconds'],
        'budget_seconds': window['budget_seconds'], 'status': window['status'], 'no_reset_or_refund': True}],
        'validation_process_qpc_seconds': activity_capture['qpc_seconds'],
        'formal_target_executions': 0, 'core_raw_seconds': 0, 'evaluation_raw_seconds': 0,
        'gate_wait_seconds': 0, 'clock_collection_seconds': 0, 'reference_generation_calls': 0,
        'independent_retest_seconds': 0, 'abandoned_target_attempt_seconds': 0,
        'auxiliary_closed_captured_maximal_qpc_seconds': sum(op['qpc_seconds'] for _, op in auxiliary),
        'auxiliary_index': [{'file': path.relative_to(OUT).as_posix(), 'qpc_seconds': op['qpc_seconds']} for path, op in auxiliary],
        'excluded': 'Uncaptured edits/model time, this finalizer, later documentation/git/push; not entire turn total',
        'inclusion': 'Activity window is inside validation process envelope. Nested power queries are inside window. Do not add these together; no history standby refund.'}
    atomic_write_json(OUT / 'costs.json', costs)
    estimate = sum(g['evaluation_wall_seconds'] for g in old_state['completed']) * 24 / 20
    atomic_write_json(OUT / 'later_search_budget_proposal.json', {'status': 'proposal_only_not_executed_or_authorized',
        'first_seed': 20261008, 'trajectories': 2, 'unique_evaluations': 24, 'target_executions_search': 144,
        'deduplicated_retest_groups_range': [2, 6], 'target_executions_retests_range': [12, 36],
        'rough_search_evaluation_raw_seconds': estimate, 'rough_activity_hours_range': [7, 10],
        'fixed_qpc_activity_ceiling_seconds': 43200, 'automatic_extension': False,
        'basis': '24/20 times historical RAW group total is a planning heuristic only; greedy composition and resource waits can differ, no physical calibration or promise of completion. Add setup, 2-6 retests, gates and boundary probes. Clock or standby failure stops regardless of remaining budget.'})
    summary = {'status': 'P3_RAW_COMPARISON_PARTIAL_AC_POWER_BLOCKED', 'at': utc_now(),
        'audit_baseline': 'e1b3a7ee26da346efa50da564199e53ec91cccda', 'execution_content_sha': plan['content_commit'],
        'measurement_content_sha': plan['measurement_content'], 'validation_session': plan['session_id'],
        'search_session': search_plan['session_id'], 'archive': plan['archive_directory'],
        'comparison_protocol_hash': plan['comparison_protocol_hash'],
        'evidence_integrity_pass': independent['evidence_integrity_pass'],
        'execution_complete': False, 'timing_checks_pass': False, 'comparison_ready': False,
        'validation_complete': False, 'validation_timing_checks_pass': False,
        'focused_tests_windows': 19, 'focused_tests_wsl': 19, 'unique_configurations': 20,
        'resource_recovery_gate': 'not_executed', 'resource_formal_gate': 'not_executed',
        'fresh_admission_intervals': 0, 'required_admission_intervals': 2, 'boundary_check_intervals': 0,
        'target_4096_executions': 0, 'planned_target_4096_executions': 18, 'small_matrix_executions': 0,
        'reference_generation_calls': 0, 'completed_validation_groups': 0, 'search_evaluations': 0,
        'completed_search_trajectories': 0, 'candidate_retests': 0, 'partial_target_samples': 0,
        'power': load(session / 'ac_status.json'), 'sleep_request': load(session / 'sleep_request.json'),
        'activity_qpc_seconds': window['activity_qpc_seconds'], 'stop_reason': window['failure_reason'],
        'historical_grid_configs': 20, 'historical_grid_target_executions': 120,
        'history_protection_pass': not changed, 'task_experiment_processes': 0,
        'next_step': 'External review; connect AC/open lid, explicitly authorize a fresh limited validation attempt while preserving current closed claim. Do not re-run current one-shot plan or start search.'}
    atomic_write_json(OUT / 'delivery_summary.json', summary)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__': main()
