"""Read-only first-seed reporting. No strategy/evaluator invocation or historical writes."""
import csv
import json
import sys
from pathlib import Path

OUT=Path(__file__).resolve().parent; ROOT=OUT.parents[2]
plan=json.loads((OUT/'content/search_plan.json').read_bytes())
sys.path.insert(0,plan['windows_archive_directory'])
from autotuner.core import sha256_file, utc_now
from scripts.raw_comparison_contract import audit, audit_exit_code
from scripts.p3_clock_contract import atomic_write_json, load


def main():
    session=Path(plan['session_directory']); state=load(session/'checkpoint.json')
    window=load(session/'window.json')
    if window['status']=='running': raise ValueError('Postprocessing waits for controller exit')
    independent=audit(plan); atomic_write_json(OUT/'independent_first_seed_audit.json',independent)
    rows=[]; search_raw={}; retest_raw={}; accepted=[]
    for algorithm in ('random','greedy'):
        own=state['trajectories'][algorithm]
        search_raw[algorithm]=sum(g['evaluation_wall_seconds'] for g in own['observations'])
        retest_raw[algorithm]=sum(g['evaluation_wall_seconds'] for g in own['retests'])
        accepted.extend(own['observations']+own['retests'])
        for budget in (4,8,12):
            prefix=next((p for p in own['prefixes'] if p['budget']==budget),None)
            candidate=prefix['best_config'] if prefix else None
            retest=next((g for g in own['retests'] if g['config']==candidate),None)
            selected=next((g for g in own['observations'][:budget] if g['config']==candidate),None)
            rows.append(dict(algorithm=algorithm,search_seed=20261008,matrix_input_seed=20261008,budget=budget,
                evaluated_configurations=min(len(own['observations']),budget),prefix_complete=prefix is not None,
                selected_config=(candidate['optimization']+'/s'+str(candidate['block_size'])) if candidate else None,
                search_median_raw_seconds=prefix['median_seconds'] if prefix else None,
                independent_median_raw_seconds=retest['score_seconds'] if retest else None,
                independent_change_percent=(retest['score_seconds']/prefix['median_seconds']-1)*100 if retest else None,
                search_cv_percent=selected['statistics']['coefficient_of_variation']*100 if selected else None,
                search_mad_seconds=selected['statistics']['median_absolute_deviation_seconds'] if selected else None,
                independent_cv_percent=retest['statistics']['coefficient_of_variation']*100 if retest else None,
                independent_mad_seconds=retest['statistics']['median_absolute_deviation_seconds'] if retest else None,
                terminal_configuration_evaluation_raw_seconds=prefix['terminal_evaluation_raw_seconds'] if prefix else None,
                retest_attempt_id=retest['attempt_id'] if retest else None,
                cost_scope='Own completed configuration evaluations: warmup+5fresh+verification, excludes gates/setup/admission/retests/abandoned attempts',
                status='complete' if prefix and retest else 'prefix complete; retest not executed' if prefix else 'not completed'))
    atomic_write_json(OUT/'first_seed_six_rows.json',rows)
    with (OUT/'first_seed_six_rows.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,list(rows[0]));writer.writeheader();writer.writerows(rows)
    samples=[json.loads(line) for line in (session/'samples.jsonl').read_bytes().splitlines() if line] if (session/'samples.jsonl').exists() else []
    accepted_ids={s['run_id'] for g in accepted for s in g['samples']}
    gates=[]
    for path in session.rglob('gate_outcome.json'):
        value=load(path);gates.append(dict(path=str(path),qpc_seconds=value['qpc_seconds'],admitted=value['admitted']))
    clocks=[]
    for path in session.rglob('native_process.json'):
        value=load(path);clocks.append(dict(path=str(path),qpc_seconds=value['qpc_seconds'],returncode=value['returncode'],intervals=value['saved_intervals']))
    setup_operation=session/'operations/setup.operation.json'
    setup=load(setup_operation) if setup_operation.exists() else None
    if setup and (setup['qpc_frequency']!=window['qpc_frequency'] or not window['qpc_start']<=setup['qpc_end']<=window['qpc_end']):
        raise ValueError('Shared preparation QPC scope/epoch differs')
    costs=dict(activity_qpc_seconds=window['activity_qpc_seconds'],budget_qpc_seconds=43200,
        shared_preparation_qpc_seconds=(setup['qpc_end']-window['qpc_start'])/window['qpc_frequency'] if setup else None,
        shared_preparation_scope='Activity start through successful setup-operation end; includes admission/gates/setup, nested in activity',
        shared_setup_raw_seconds=state.get('setup_raw_seconds'),
        setup_process_qpc_seconds=load(setup_operation)['qpc_seconds'] if setup_operation.exists() else None,
        search_terminal_configuration_evaluation_raw_seconds=search_raw,
        candidate_retest_evaluation_raw_seconds=retest_raw,
        all_accepted_core_raw_seconds_including_warmups=sum(g['compute_total_seconds'] for g in accepted),
        gates=gates,clock_processes=clocks,
        partial_target_samples=len(samples)-len(accepted_ids),
        unaccepted_known_saved_core_raw_seconds=sum(s['score_seconds'] for s in samples if s['run_id'] not in accepted_ids and s.get('score_seconds') is not None),
        unaccepted_missing_core_count=sum(s.get('score_seconds') is None for s in samples if s['run_id'] not in accepted_ids),
        offline_prepare_process_qpc_seconds=load(OUT/'operations/prepare_frozen_search.operation.json')['qpc_seconds'],
        scope='Activity QPC contains admission, setup, gates, targets, retests, checks, failure and cleanup. Setup process contains setup RAW; group evaluation RAW contains core and correctness. Subranges are NOT added again. Offline export/tests/git/postprocessing excluded; no historical Grid QPC speedup claim.')
    atomic_write_json(OUT/'costs.json',costs)
    atomic_write_json(OUT/'source_identity.json',dict(execution_content_sha=plan['content_commit'],session_id=plan['session_id'],
        inherited_measurement_content_sha=plan['measurement_content'],comparison_protocol_hash=plan['comparison_protocol_hash'],
        timing_protocol_hash=plan['timing_protocol_hash'],measurement_protocol_hash=plan['measurement_protocol_hash'],
        compiler_sha256=plan['compiler_sha256'],windows_source_identity=plan['windows_source_identity'],
        linux_source_identity=plan['linux_source_identity'],inherited_measurement_files=plan['inherited_measurement_files'],
        verified_cache_files=plan['verified_cache_files'],expected_artifacts=plan['expected_artifacts'],
        postprocessor_sha256=sha256_file(Path(__file__))))
    summary=dict(at=utc_now(),scope='first_seed',status='FIRST_SEED_RAW_COMPARISON_COMPLETE' if independent['comparison_ready'] else 'FIRST_SEED_RAW_COMPARISON_PARTIAL',
        execution_content_sha=plan['content_commit'],session_id=plan['session_id'],matrix_input_seed=20261008,search_seed=20261008,
        evidence_integrity_pass=independent['evidence_integrity_pass'],execution_complete=independent['execution_complete'],
        timing_checks_pass=independent['timing_checks_pass'],comparison_ready=independent['comparison_ready'],
        five_seed_execution_complete=False,five_seed_comparison_ready=False,
        search_groups={a:len(state['trajectories'][a]['observations']) for a in ('random','greedy')},
        retest_groups={a:len(state['trajectories'][a]['retests']) for a in ('random','greedy')},
        target_executions=len(samples),checkpoint_target_executions=state['target_executions'],unique_run_ids=len({s['run_id'] for s in samples}),partial_target_samples=len(samples)-len(accepted_ids),
        unreferenced_run_directories=independent.get('unreferenced_run_directories'),
        active=state['active'],failure_reason=window['failure_reason'],controller_returncode=load(OUT/'operations/search_activity.operation.json')['returncode'],
        costs=costs,screenshot='No verified visible terminal capture; raw captured stdout/stderr retained, no fabricated screenshot')
    atomic_write_json(OUT/'delivery_summary.json',summary);print(json.dumps(summary))
    return audit_exit_code(independent,'search')


if __name__=='__main__': raise SystemExit(main())
