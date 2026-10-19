"""Postprocessing only: never evaluates a target, changes scores, or rewrites old summaries."""
import csv
import json
import re
import subprocess
import sys
import importlib.util
from pathlib import Path

OUT = Path(__file__).resolve().parent
REPO = OUT.parents[2]
auth = json.loads((OUT/'continuation/authorization.json').read_bytes())
plan = json.loads(Path(auth['plan_file']).read_bytes())
sys.path.insert(0, plan['windows_archive_directory'])
from autotuner.core import sha256_file, classify_execution, utc_now
from autotuner.session import source_identity
from scripts.p3_clock_contract import atomic_write_json, load
from scripts.raw_clock_contract import local_path, audit_clock, audit_gate, checked_operation


def check_ac_refusal_result(window, operation, ac):
    if window['status']!='stopped' or window['phase']!='preflight' or window['failure_reason']!='AC power required; keep lid open' or \
            operation['returncode']!=2 or operation['timed_out'] or ac.get('ok') is not True or \
            type(ac.get('ac')) is not int or ac['ac']!=0 or type(ac.get('battery_percent')) is not int or \
            not 0<=ac['battery_percent']<=100 or operation['operation_kind']!='ac_status' or \
            operation['qpc_frequency']!=window['qpc_frequency'] or \
            not window['qpc_start']<=operation['qpc_start']<=operation['qpc_end']<=window['qpc_end']:
        raise ValueError('Not a valid captured AC refusal in the same window')


def audit_ac_stop(continuation, session, window):
    """Only certify an intact pre-admission AC refusal, never a clock/target PASS."""
    spec=importlib.util.spec_from_file_location('frozen_continuation_helper',auth['helper_file'])
    helper=importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    helper.verify_auth(auth); helper.verify_preserved(auth)
    claim=load(session/helper.claim_filename(auth))
    if window['status']!='stopped' or window['phase']!='preflight' or window['failure_reason']!='AC power required; keep lid open' or \
            window['authorization_sha256']!=sha256_file(continuation/'authorization.json') or \
            any(window[k]!=claim[k] for k in ('authorization_sha256','qpc_start','qpc_frequency','budget_seconds')) or \
            window['budget_seconds']!=auth['remaining_allowance_seconds'] or \
            helper.cumulative(auth['previous_activity_qpc_seconds'],window)!=window['cumulative_activity_qpc_seconds']:
        raise ValueError('AC refusal authorization/window/budget differs')
    operation=checked_operation(continuation,'ac_status'); ac=load(continuation/operation['stdout_path'])
    check_ac_refusal_result(window,operation,ac)
    if any((continuation/name).exists() for name in ('admission_resources','admission')) or window.get('attempt_id'):
        raise ValueError('AC refusal original result or unexecuted-stage evidence differs')
    sleep=load(continuation/'sleep_request.json')
    if not sleep['acquired'] or not sleep['released'] or sleep['thread_id']!=sleep['release_thread_id']:
        raise ValueError('Temporary sleep request not properly released')
    from scripts.raw_comparison_contract import audit
    base=audit(plan)
    if not base['evidence_integrity_pass'] or base['target_executions']!=12 or base['completed_groups']!=2:
        raise ValueError('Historical accepted-group audit failed')
    result={**base,'validation_complete':False,'validation_timing_checks_pass':False,
        'formal_resource_pass':None,'fresh_admission_pass':None,'resource_status':'not_executed','clock_status':'not_executed',
        'current_ac_check':ac,'failure_reason':window['failure_reason'],'original_runs_preserved':12,
        'protected_session_files':len(auth['protected_session_files']),'protected_history_files':len(auth['protected_history_files']),
        'independent_auditor_source_sha256':sha256_file(Path(__file__)),
        'scope':'Independent audit of AC refusal; original frozen auxiliary audit is preserved separately, not rewritten'}
    atomic_write_json(continuation/'independent_preflight_stop_audit.json',result)
    return result


def main():
    continuation=OUT/'continuation'; session=Path(auth['session_directory'])
    window=load(continuation/'window.json')
    if window['status']=='running': raise ValueError('Postprocessing must wait for controller exit')
    audit=audit_ac_stop(continuation,session,window) if window['failure_reason']=='AC power required; keep lid open' else load(continuation/'independent_continuation_audit.json')
    state=load(session/'checkpoint.json')
    samples=[json.loads(line) for line in (session/'samples.jsonl').read_bytes().splitlines() if line]
    old=load(REPO/'evidence/p3_raw_grid/20261011-021601/final-content/grid-f705a488/checkpoint.json')
    rows=[]; groups=state['validation_groups']
    for block in (128,64,24):
        config=dict(optimization='O3',block_size=block)
        previous=next(g for g in old['completed'] if g['config']==config)
        current=next((g for g in groups if g['config']==config),None)
        continuity=load(local_path(current['checks_directory'])/'continuity.json')['result'] if current else None
        rows.append(dict(optimization='O3',block_size=block,historical_grid_median_raw_seconds=previous['score_seconds'],
            independent_median_raw_seconds=current['score_seconds'] if current else None,
            independent_cv_percent=current['statistics']['coefficient_of_variation']*100 if current else None,
            independent_mad_seconds=current['statistics']['median_absolute_deviation_seconds'] if current else None,
            median_change_percent=(current['score_seconds']/previous['score_seconds']-1)*100 if current else None,
            correctness_pass=all(s['classification']=='success' and s['target_result']['checked_entries']==4096**2 for s in current['samples']) if current else None,
            timing_contract_pass=bool(audit['evidence_integrity_pass']) if current else None,
            uninterrupted_execution=continuity['uninterrupted_execution'] if continuity else None,
            group_evaluation_raw_seconds=current['evaluation_wall_seconds'] if current else None,
            group_QPC_envelope_seconds=continuity['evaluation_qpc_seconds'] if continuity else None,
            same_scope_RAW_seconds=continuity['evaluation_raw_seconds'] if continuity else None,
            group_QPC_RAW_difference_seconds=continuity['absolute_difference_seconds'] if continuity else None))
    atomic_write_json(OUT/'three_configuration_comparison.json',rows)
    with (OUT/'three_configuration_comparison.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,list(rows[0])); writer.writeheader(); writer.writerows(rows)
    clocks=[]; gates=[]; measurement=load(Path(plan['windows_archive_directory'])/'configs/measurement_protocol.json')
    prior=auth; prior_directories=[]; seen=set()
    while prior.get('prior_authorization_file'):
        prior_path=Path(prior['prior_authorization_file']).resolve()
        if prior_path in seen or len(seen)>=4: raise ValueError('Invalid or cyclic closed-activity chain')
        seen.add(prior_path); prior=load(prior_path)
        prior_directories.append(Path(prior['directory']))
    for base in (session,*prior_directories,continuation):
        for path in sorted(base.rglob('manifest.json')):
            manifest=load(path)
            if manifest.get('schema')!='raw-comparison-clock-manifest-v1': continue
            clocks.append(dict(path=str(path.parent),purpose=manifest['purpose'],
                independent=audit_clock(path.parent,manifest['context']),
                process_qpc_seconds=load(path.parent/'native_process.json')['qpc_seconds']))
        for path in sorted(base.rglob('gate_manifest.json')):
            manifest=load(path); outcome=load(path.parent/'gate_outcome.json'); snapshots=[]
            for name in outcome['operations']:
                op=load(path.parent/(name+'.operation.json'))
                raw=load(path.parent/op['stdout_path']) if (path.parent/op['stdout_path']).stat().st_size else {}
                snapshots.append(dict(operation=name,returncode=op['returncode'],timed_out=op['timed_out'],
                    host_minimum_available_bytes=raw.get('host_minimum_available_bytes'),
                    host_minimum_commit_headroom_bytes=raw.get('host_minimum_commit_headroom_bytes'),
                    wsl_available_bytes=raw.get('wsl_available_bytes'),host_cpu_average_percent=raw.get('host_cpu_average_percent'),
                    host_cpu_maximum_percent=raw.get('host_cpu_maximum_percent'),warnings=raw.get('warnings'),rejection_reasons=raw.get('rejection_reasons')))
            gate_error=None
            try: gate_pass=audit_gate(path.parent,measurement,manifest['purpose'],manifest['context'])
            except (ValueError,KeyError,TypeError,OSError) as error:
                gate_pass=False; gate_error=str(error)
            gates.append(dict(path=str(path.parent),purpose=manifest['purpose'],
                independent_pass=gate_pass,independent_error=gate_error,
                qpc_seconds=outcome['qpc_seconds'],budget_seconds=manifest['budget_seconds'],
                budget_overrun_seconds=max(0,outcome['qpc_seconds']-manifest['budget_seconds']),snapshots=snapshots))
    atomic_write_json(OUT/'all_clock_checks_independent.json',clocks)
    atomic_write_json(OUT/'all_resource_gates_independent.json',gates)
    checked=[]; peaks=[]
    for sample in samples:
        expected=dict(n=4096,block_size=sample['config']['block_size'],seed=20261008,input='random',
            input_generator='splitmix64-interleaved-v1',abs_tol=1e-12,rel_tol=1e-12,
            primary_clock='CLOCK_MONOTONIC_RAW',timing_protocol_version='2026-10-11-raw-formal-v1')
        category,parsed,detail=classify_execution(sample['returncode'],sample['timed_out'],sample['raw_stdout'],
            expected_schema='matrix-multiplication-result-v2',expected=expected)
        passed=category=='success' and parsed==sample['target_result'] and sample['source']=='fresh_measurement' and sample['context']['force_remeasure'] is True
        checked.append(dict(run_id=sample['run_id'],role=sample['role'],config=sample['config'],pass_contract=passed,
            checked_entries=parsed.get('checked_entries') if parsed else None,classification=category,detail=detail))
        text=(session/'runs'/Path(sample['run_directory']).name/'resource.txt').read_text()
        match=re.search(r'Maximum resident set size \(kbytes\):\s*(\d+)',text)
        if match: peaks.append(int(match.group(1)))
    atomic_write_json(OUT/'all_sample_contracts_independent.json',checked)
    if len({s['run_id'] for s in samples})!=len(samples) or not all(c['pass_contract'] for c in checked): raise ValueError('Duplicate/invalid/nonfresh samples')
    costs=dict(previous_activity_qpc_seconds=auth['previous_activity_qpc_seconds'],
        continuation_activity_qpc_seconds=window['activity_qpc_seconds'],
        cumulative_activity_qpc_seconds=window['cumulative_activity_qpc_seconds'],
        original_activity_budget_seconds=3600,original_remaining_allowance_seconds=auth['remaining_allowance_seconds'],
        unused_allowance_seconds=3600-window['cumulative_activity_qpc_seconds'],
        continuation_process_envelope_qpc_seconds=load(OUT/'operations/continuation_activity.operation.json')['qpc_seconds'],
        all_accepted_configuration_evaluation_raw_seconds=sum(g['evaluation_wall_seconds'] for g in groups),
        all_target_core_raw_seconds_including_warmups=sum(s.get('score_seconds') or 0 for s in samples),
        resource_gate_qpc_seconds=sum(v['qpc_seconds'] for v in gates),
        native_clock_process_qpc_seconds=sum(v['process_qpc_seconds'] for v in clocks),
        setup_cache_verification_raw_seconds=state['setup_raw_seconds'],reference_generation_calls=state['reference_generation_calls'],
        search_seconds=0,prefix_candidate_retest_seconds=0,
        prior_closed_activities_qpc_seconds=[846.073676]+[load(path/'window.json')['activity_qpc_seconds'] for path in reversed(prior_directories)],
        scope='Sum six separately measured QPC activity envelopes, no cross-epoch subtraction. Gates/probes/core/configuration RAW are nested breakdowns, NOT added to envelopes. Offline human review, code, snapshots, git and postprocessing are excluded. Old disk-failure/refusal/AC costs remain charged; no Grid refunds/calibration.')
    atomic_write_json(OUT/'costs.json',costs)
    identity=load(local_path(plan['git_identity']))
    actual=source_identity(Path(plan['windows_archive_directory']),identity['files'])
    if actual!=plan['windows_source_identity']: raise ValueError('Frozen actual execution bytes changed')
    auxiliary=[]
    for name in ('scripts/resume_raw_validation.py','tests/test_resume_raw_validation.py','docs/P3_RAW_VALIDATION_CONTINUATION.md'):
        data=subprocess.check_output(['git','show',auth['auxiliary_content_commit']+':'+name],cwd=REPO)
        import hashlib
        path=Path(auth['helper_file']).parents[1]/name
        auxiliary.append(dict(path=name,git_blob_id=subprocess.check_output(['git','rev-parse',auth['auxiliary_content_commit']+':'+name],cwd=REPO,text=True).strip(),
            git_content_sha256=hashlib.sha256(data).hexdigest(),executed_or_archived_sha256=sha256_file(path),
            bytes_equal=path.read_bytes()==data,normalized_LF_equal=path.read_bytes().replace(b'\r\n',b'\n')==data.replace(b'\r\n',b'\n'),
            git_CRLF_count=data.count(b'\r\n'),git_LF_count=data.count(b'\n'),archived_CRLF_count=path.read_bytes().count(b'\r\n'),
            identity_requirement='byte-identical executable/test' if name.endswith('.py') else 'non-executable documentation; separately record LF-normalized content'))
    atomic_write_json(OUT/'source_identity.json',dict(execution_content_sha=plan['content_commit'],measurement_content_sha=plan['measurement_content'],
        auxiliary_content_sha=auth['auxiliary_content_commit'],auxiliary=auxiliary,source_files=actual,
        comparison_protocol_hash=plan['comparison_protocol_hash'],timing_protocol_hash=plan['timing_protocol_hash'],
        measurement_protocol_hash=plan['measurement_protocol_hash'],compiler_sha256=plan['compiler_sha256'],
        expected_artifacts=plan['expected_artifacts'],postprocess_sha256=sha256_file(Path(__file__))))
    clock_count=sum(v['independent']['interval_count'] for v in clocks)
    complete=audit['evidence_integrity_pass'] and audit['validation_complete'] and audit['validation_timing_checks_pass'] and window['status']=='complete'
    group_gate=next((g for g in gates if g['path']==str(Path(window.get('checks_directory',''))/'resources')),None)
    current_admission=next((v for v in clocks if v['path']==str(continuation/'admission')),None)
    summary=dict(status='P3_RAW_THREE_CONFIG_VALIDATION_COMPLETE' if complete else 'P3_RAW_VALIDATION_PARTIAL',at=utc_now(),
        execution_content_sha=plan['content_commit'],session_id=plan['session_id'],auxiliary_content_sha=auth['auxiliary_content_commit'],
        evidence_integrity_pass=audit['evidence_integrity_pass'],validation_complete=bool(complete),
        validation_timing_checks_pass=audit['validation_timing_checks_pass'],execution_complete=False,timing_checks_pass=False,comparison_ready=False,
        target_executions=len(samples),new_target_executions=len(samples)-12,completed_groups=len(groups),
        warmups=sum(s['role']=='warmup' for s in samples),measurements=sum(s['role']=='measurement' for s in samples),
        clock_intervals=clock_count,clock_raw_failed_indices=[dict(path=v['path'],indices=v['independent'].get('raw_failure_indices',[])) for v in clocks if not v['independent']['raw_reference_pass']],
        monotonic_warning_intervals=sum(len(v['independent'].get('monotonic_warning_indices',[])) for v in clocks),
        full_matrix_contracts_pass=True,maximum_target_peak_rss_kib=max(peaks) if peaks else None,
        failed_old_group_launches_before_target=1,partial_target_samples=audit['partial_target_samples'],
        search_trajectories=0,search_configurations=0,prefix_retest_groups=0,stop_reason=window['failure_reason'],costs=costs)
    summary.update(formal_preflight_pass=audit.get('formal_resource_pass'),
        group_formal_resource_pass=group_gate['independent_pass'] if group_gate else None,
        continuation_clock_intervals=current_admission['independent']['interval_count'] if current_admission else 0,
        continuation_clock_pass=current_admission['independent']['raw_reference_pass'] if current_admission else None,
        resource_gate_audit_errors=[dict(path=g['path'],error=g['independent_error'],budget_overrun_seconds=g['budget_overrun_seconds']) for g in gates if g['independent_error']],
        cumulative_activity_note='Authoritative window uses saved qpc_end, not the later terminal/progress snapshot timestamp')
    if not complete and window['failure_reason'] in ('Group Formal gate refused','Formal resource preflight refused'):
        summary['status']='P3_RAW_VALIDATION_RESOURCE_BLOCKED'
    if window['failure_reason']=='AC power required; keep lid open':
        summary.update(status='P3_RAW_VALIDATION_AC_POWER_BLOCKED',resource_status='not_executed',clock_status='not_executed',
            independent_audit_file='continuation/independent_preflight_stop_audit.json',ac_check=audit['current_ac_check'])
    atomic_write_json(OUT/'delivery_summary.json',summary)
    print(json.dumps(dict(summary=summary,comparison_rows=rows)),flush=True)


if __name__=='__main__': main()
