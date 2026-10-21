"""Read-only first-seed reporting. No strategy/evaluator invocation or historical writes."""
import csv
import importlib.util
import json
import sys
from pathlib import Path

OUT=Path(__file__).resolve().parent; ROOT=OUT.parents[2]
auth_path=OUT/'continuation/authorization.json'
auth=json.loads(auth_path.read_bytes())
plan=json.loads(Path(auth['plan_file']).read_bytes())
sys.path.insert(0,plan['windows_archive_directory'])
from autotuner.core import sha256_file, utc_now
from scripts.p3_clock_contract import atomic_write_json, load


def main():
    session=Path(plan['session_directory']); state=load(session/'checkpoint.json')
    window=load(OUT/'continuation/window.json')
    if window['status']=='running': raise ValueError('Postprocessing waits for controller exit')
    spec=importlib.util.spec_from_file_location('manual_first_seed_auditor',auth['helper_file'])
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    helper.audit(auth_path)
    independent=load(OUT/'continuation/independent_continuation_audit.json')
    atomic_write_json(OUT/'independent_first_seed_audit.json',independent)
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
    new_ids={s['run_id'] for s in samples}-set(auth['original_run_ids'])
    abandoned_count=6 if state.get('finish_resume') else 2
    gates=[]
    for path in session.rglob('gate_outcome.json'):
        if path.relative_to(ROOT).as_posix() in auth['protected_files']:continue
        value=load(path);gates.append(dict(path=str(path),qpc_seconds=value['qpc_seconds'],admitted=value['admitted']))
    if (OUT/'continuation/admission_resources/gate_outcome.json').exists():
        path=OUT/'continuation/admission_resources/gate_outcome.json';value=load(path)
        gates.append(dict(path=str(path),qpc_seconds=value['qpc_seconds'],admitted=value['admitted']))
    clocks=[]
    for path in session.rglob('native_process.json'):
        if path.relative_to(ROOT).as_posix() in auth['protected_files']:continue
        value=load(path);clocks.append(dict(path=str(path),qpc_seconds=value['qpc_seconds'],returncode=value['returncode'],intervals=value['saved_intervals']))
    if (OUT/'continuation/admission/native_process.json').exists():
        path=OUT/'continuation/admission/native_process.json';value=load(path)
        clocks.append(dict(path=str(path),qpc_seconds=value['qpc_seconds'],returncode=value['returncode'],intervals=value['saved_intervals']))
    first_group_gates=[load(g['path']) for g in gates if Path(g['path']).is_relative_to(session)]
    preparation_end=min(g['qpc_start'] for g in first_group_gates) if first_group_gates else None
    previous_costs=load(Path(auth['previous_authorization_file']).parent.parent/'costs.json')
    costs=dict(activity_qpc_seconds=window['activity_qpc_seconds'],previous_activity_qpc_seconds=auth['previous_activity_qpc_seconds'],
        cumulative_activity_qpc_seconds=window['cumulative_activity_qpc_seconds'],budget_qpc_seconds=43200,
        remaining_allowance_at_start=auth['remaining_allowance_seconds'],
        shared_preparation_qpc_seconds=(preparation_end-window['qpc_start'])/window['qpc_frequency'] if preparation_end else None,
        shared_preparation_scope='Continuation start through first group gate start, includes fresh admission/cache/protection/first evidence-volume check; nested in continuation',
        original_setup_raw_seconds_preserved=state.get('setup_raw_seconds'),setup_invoked=False,
        search_terminal_configuration_evaluation_raw_seconds=search_raw,
        candidate_retest_evaluation_raw_seconds=retest_raw,
        all_accepted_core_raw_seconds_including_warmups=sum(g['compute_total_seconds'] for g in accepted),
        gates=gates,clock_processes=clocks,
        known_historical_abandoned_samples=abandoned_count,
        new_unaccepted_target_samples=len(new_ids-accepted_ids),
        unaccepted_known_saved_core_raw_seconds=sum(s['score_seconds'] for s in samples if s['run_id'] not in accepted_ids and s.get('score_seconds') is not None),
        unaccepted_missing_core_count=sum(s.get('score_seconds') is None for s in samples if s['run_id'] not in accepted_ids),
        previous_closed_windows=auth['previous_windows'],original_costs=previous_costs,
        offline_prepare_process_qpc_seconds=load(OUT/'operations/prepare_finish.operation.json')['qpc_seconds'],
        scope='Cumulative activity is the sum of three separate verified QPC envelopes, includes old standby/failed attempt, excludes review pause. Preparation/gates/clocks/evaluation/core are nested, NOT added again. Original legacy MONOTONIC fields are diagnostic only. Offline tests/export/protection/postprocessing/Git excluded; no Grid QPC speedup claim.')
    atomic_write_json(OUT/'costs.json',costs)
    atomic_write_json(OUT/'source_identity.json',dict(execution_content_sha=plan['content_commit'],session_id=plan['session_id'],
        auxiliary_content_sha=auth['auxiliary_content_commit'],auxiliary_source_sha256=auth['helper_sha256'],
        authorization_sha256=sha256_file(auth_path),starting_checkpoint_sha256=auth['checkpoint_sha256'],abandonments=auth['abandonments'],
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
        new_target_executions=len(new_ids),target_executions=len(samples),checkpoint_target_executions=state['target_executions'],unique_run_ids=len({s['run_id'] for s in samples}),partial_target_samples=len(samples)-len(accepted_ids)-abandoned_count,
        unreferenced_run_directories=sorted(p.name for p in (session/'runs').iterdir() if p.is_dir() and p.name not in {Path(s['run_directory']).name for s in samples}),
        abandoned_target_samples=abandoned_count,new_unaccepted_target_samples=len(new_ids-accepted_ids),
        auxiliary_content_sha=auth['auxiliary_content_commit'],
        active=state['active'],failure_reason=window['failure_reason'],controller_returncode=load(OUT/'operations/finish_activity.operation.json')['returncode'],
        costs=costs,screenshot='No verified visible terminal capture; raw captured stdout/stderr retained, no fabricated screenshot')
    atomic_write_json(OUT/'delivery_summary.json',summary);print(json.dumps(summary))
    return 0 if independent['comparison_ready'] else 2


if __name__=='__main__': raise SystemExit(main())
