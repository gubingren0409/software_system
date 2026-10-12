"""Read-only, task-local packaging after the one claimed window has stopped."""
import hashlib, importlib, importlib.util, json, os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main():
    freeze = json.loads((HERE/'auxiliary_freeze.json').read_bytes())
    spec = importlib.util.spec_from_file_location('committed_segment_helper', freeze['helper'])
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    auth = helper.read(HERE/'window/authorization.json'); plan = helper.read(auth['plan_file'])
    f = helper.frozen(plan); closed = importlib.import_module('scripts.raw_clock_contract').checked_operation
    resources = importlib.import_module('autotuner.resources')
    policy, policy_path, collector_lf = resources.protocol_policy(f.validate_plan(plan)[0])
    window = helper.read(HERE/'window/window.json'); session = Path(plan['session_directory'])
    state = helper.read(session/'checkpoint.json'); errors = []
    helper.verify_protection(auth, plan, initial=True)
    matches = {name: helper.digest(session/name) == helper.digest(HERE/'window/preserved'/name)
        for name in ('controller.json','checkpoint.json','initial_checkpoint.json','samples.jsonl','grid_summary.csv','progress.json')}
    if not all(matches.values()): errors.append('Accepted original snapshot changed')
    original = helper.read(ROOT/'evidence/p3_raw_grid/20261011-021601/history_before.json')['files']
    changed = [name for name, value in original.items() if not (ROOT/name).exists() or helper.digest(ROOT/name) != value]
    if changed: errors.append('Older protected history changed')
    old_tree = subprocess.run(['git','ls-tree','-r','--name-only','f19f9f84b19a5a7c2b71ba38ffab206499ffff54','--','evidence'],
        cwd=ROOT,capture_output=True,check=True).stdout.decode().splitlines()
    modified = subprocess.run(['git','diff','f19f9f84','--name-only','--','evidence'],cwd=ROOT,capture_output=True,check=True).stdout.decode().splitlines()
    old_evidence_changes = sorted(set(old_tree) & set(modified))
    if old_evidence_changes: errors.append('Accepted Git evidence changed')
    frozen_changes = subprocess.run(['git','diff','3cc9e0d03ba682569fca0e91f28d364f2dab73fa','--name-only',
        '--','.gitattributes','autotuner','code','configs','scripts','tests'],cwd=ROOT,capture_output=True,check=True).stdout.decode().splitlines()
    if set(frozen_changes) != {'scripts/raw_grid_segment.py','tests/test_raw_grid_segment.py'}:
        errors.append('Unexpected change to frozen worktree content')
    gate = HERE/'window/preflight_gate'; outcome = helper.read(gate/'gate_outcome.json'); decisions = []
    for name in outcome['operations']:
        op = closed(gate,name); stdout = (gate/op['stdout_path']).read_bytes()
        row = {'operation':name,'returncode':op['returncode'],'timed_out':op['timed_out'],'qpc_seconds':op['qpc_seconds']}
        if stdout:
            saved = json.loads(stdout); judged = resources.judge(saved,policy,'Formal',helper.digest(policy_path))
            fields = ('checks','warnings','rejection_reasons','decision','policy_hash','policy_version')
            if any(saved[key] != judged[key] for key in fields) or saved['collector_lf_sha256'] != collector_lf:
                errors.append('Resource independent recomputation differs: '+name)
            row.update(host_minimum_available_bytes=judged['host_minimum_available_bytes'],
                host_minimum_commit_headroom_bytes=judged['host_minimum_commit_headroom_bytes'],
                wsl_available_bytes=judged['wsl_available_bytes'],host_cpu_average_percent=judged['host_cpu_average_percent'],
                host_cpu_maximum_percent=judged['host_cpu_maximum_percent'],checks=judged['checks'],warnings=judged['warnings'],
                decision=judged['decision'],rejection_reasons=judged['rejection_reasons'],sample_count=len(judged['host_samples']))
        else: row.update(decision='unknown; collection timed out with no stdout',rejection_reasons=['collection_timeout'])
        decisions.append(row)
    if outcome['admitted'] is not False or window['formal_invoked'] or (HERE/'window/admission').exists():
        errors.append('Unexpected formal/admission activity after gate rejection')
    f.atomic_write_json(HERE/'resource_rejection_recomputed.json', {'decisions':decisions,'gate_qpc_seconds':outcome['qpc_seconds'],
        'declared_wait_budget_seconds':120,'observed_shutdown_overrun_seconds':max(0,outcome['qpc_seconds']-120),
        'scope':'Original frozen gate stops at its deadline; observed 0.152s return/cancellation overrun is disclosed, not treated as a pass.',
        'independent_decisions_match':not any('Resource' in error for error in errors)})
    win_code = "[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false); $o=Get-CimInstance Win32_OperatingSystem; [ordered]@{at=[DateTimeOffset]::Now.ToString('o');available_bytes=[int64]$o.FreePhysicalMemory*1KB;controller_processes=@(Get-Process -Id "+str(window['controller_pid'])+" -ErrorAction SilentlyContinue | Select-Object Id,ProcessName);top_memory=@(Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 12 Id,ProcessName,WorkingSet64);vmmem=@(Get-Process VmmemWSL,Vmmem -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,WorkingSet64)} | ConvertTo-Json -Depth 5"
    op = f.capture([f.POWERSHELL,'-NoProfile','-Command',win_code],HERE/'operations','post_windows','segment-finalize',timeout=40)
    host = helper.read(HERE/'operations'/op['stdout_path']) if op['returncode']==0 else {'controller_processes':'unknown'}
    linux_code = """import json,os,pathlib
prefixes=('/var/tmp/matrix-raw-grid-content-3cc9e0d','/var/tmp/matrix-raw-grid-cache-3cc9e0d','/var/tmp/matrix-raw-grid-probe-3cc9e0d')
found=[]
for p in pathlib.Path('/proc').iterdir():
 if p.name.isdecimal() and int(p.name)!=os.getpid():
  try:
   exe=os.readlink(p/'exe'); cwd=os.readlink(p/'cwd')
   if exe.startswith(prefixes) or cwd.startswith(prefixes): found.append({'pid':int(p.name),'name':(p/'comm').read_text().strip()})
  except (OSError,PermissionError): pass
print(json.dumps({'processes':found,'meminfo':pathlib.Path('/proc/meminfo').read_text(),'vmstat':pathlib.Path('/proc/vmstat').read_text(),'boot_id':pathlib.Path('/proc/sys/kernel/random/boot_id').read_text()}))"""
    op = f.capture(['wsl.exe','-d','Ubuntu-24.04','--cd','/tmp','--','python3','-c',linux_code],HERE/'operations','post_wsl','segment-finalize',timeout=40)
    guest = helper.read(HERE/'operations'/op['stdout_path']) if op['returncode']==0 else {'processes':'unknown'}
    if host['controller_processes'] != [] or guest['processes'] != []: errors.append('Owned experiment processes not confirmed exited')
    checked = []; own_open = []
    for path in HERE.rglob('*.operation.json'):
        value = helper.read(path)
        if value.get('pid') == os.getpid() and 'qpc_end' not in value:
            own_open.append(str(path.relative_to(HERE))); continue
        closed(path.parent,path.name.removesuffix('.operation.json'))
        checked.append({'path':path.relative_to(HERE).as_posix(),'qpc_start':value['qpc_start'],
            'qpc_end':value['qpc_end'],'qpc_frequency':value['qpc_frequency'],'qpc_seconds':value['qpc_seconds'],'returncode':value['returncode']})
    auxiliary = [item for item in checked if item['path'].startswith(('operations/','tests/')) and item['path']!='operations/segment_run.operation.json']
    run_op = helper.read(HERE/'operations/segment_run.operation.json')
    costs = {'first_segment_qpc_seconds':helper.FIRST_SECONDS,'continuation_qpc_seconds':window['window_qpc_seconds'],
        'cumulative_active_qpc_seconds':window['cumulative_active_qpc_seconds'],'continuation_resource_wait_nested_qpc_seconds':outcome['qpc_seconds'],
        'outer_launch_capture_qpc_seconds':run_op['qpc_seconds'],
        'outer_launch_extra_qpc_seconds':run_op['qpc_seconds']-window['window_qpc_seconds'],
        'closed_auxiliary_operations_qpc_seconds':sum(item['qpc_seconds'] for item in auxiliary),
        'auxiliary_operations':auxiliary,'pause':helper.read(HERE/'window/epoch_and_pause.json'),
        'new_target_core_seconds':0,'new_group_evaluation_seconds':0,'new_reference_generation_calls':0,
        'new_clock_collection_seconds':0,'new_retest_seconds':0,'new_abandoned_attempt_seconds':0,
        'inclusion':'Gate wait is inside continuation; continuation is inside outer capture. Auxiliary operations are separate, but own finalizer/edits/push not fully timed. Do not sum nested ranges; no whole-turn cost claimed.'}
    f.atomic_write_json(HERE/'costs.json',costs)
    result = {'packaging_checks_pass':not errors,'errors':errors,'postprocessor_sha256':helper.digest(Path(__file__)),
        'protected_accepted_file_count':len(auth['protected_session_files']),'accepted_snapshot_byte_matches':matches,
        'older_history_file_count':len(original),'older_history_byte_changes':changed,'older_git_evidence_changes':old_evidence_changes,
        'frozen_worktree_content_changes':frozen_changes,'closed_operation_count':len(checked),'closed_operations':checked,
        'own_parent_operation_closed_and_checked_after_exit':own_open,'owned_windows_controller_processes':host['controller_processes'],
        'owned_wsl_experiment_processes':guest['processes'],'session_id':plan['session_id'],'content_commit':plan['content_commit'],
        'auxiliary_content_commit':freeze['auxiliary_content_commit'],'completed_configurations':len(state['completed']),
        'target_executions':state['target_executions'],'new_target_executions':0,'new_probe_intervals':0,'new_group_clock_checks':0,
        'active':state['active'],'abandoned_attempts':state['abandoned_attempts'],'reference_generation_calls':state['reference_generation_calls'],
        'formal_resource_gate':'failed: host_memory; last collection timed out','current_clock_check':'not_performed',
        'evidence_integrity_pass':not errors,'grid_complete':False,'execution_complete':False,'timing_checks_pass':False,'comparison_ready':False}
    f.atomic_write_json(HERE/'delivery_verification.json',result)
    print(json.dumps({key:value for key,value in result.items() if key!='closed_operations'}),flush=True)
    return 0 if not errors else 2


if __name__=='__main__': raise SystemExit(main())
