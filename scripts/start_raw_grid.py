"""Windows QPC controller for ONE recovery and a fresh, serial RAW Grid."""
from __future__ import annotations
import argparse,json,os,subprocess,sys,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from autotuner.core import sha256_file,sha256_json,utc_now
from autotuner.session import source_identity
from autotuner.timing import require_formal_activation,FORMAL_RAW_VERSION
from autotuner.resources import valid_gate
from scripts.p3_clock_contract import atomic_write_json,load,qpc,capture,wsl_path,POWERSHELL
from scripts.raw_clock_contract import (local_path,raw_schedule,audit_clock,audit_recovery,
                                      require_certificate,audit_gate)


def validate_plan(plan):
    if os.name!='nt': raise ValueError('This controller requires real Windows QPC')
    if ROOT!=local_path(plan['windows_archive_directory']): raise ValueError('Run the exact clean Windows content archive')
    protocol=load(ROOT/'configs/measurement_protocol.json'); timing=require_formal_activation(protocol,ROOT)
    identity=load(local_path(plan['git_identity']))
    if timing['version']!=FORMAL_RAW_VERSION or identity['content_sha']!=plan['content_commit'] or \
            sha256_json(protocol)!=plan['measurement_protocol_hash'] or sha256_json(timing)!=plan['timing_protocol_hash']:
        raise ValueError('Frozen RAW plan/content/protocol differs')
    actual=source_identity(ROOT,identity['files'])
    if actual!=plan['windows_source_identity']: raise ValueError('Windows execution bytes differ from plan')
    return protocol,timing


def linux(plan,args):
    return ['wsl.exe','-d','Ubuntu-24.04','--cd',plan['archive_directory'],'--','env','-u','PYTHONPATH',
        'PYTHONDONTWRITEBYTECODE=1',*args]


def resource_command(plan,purpose):
    return [POWERSHELL,'-NoProfile','-File',str(ROOT/'scripts/check_p2_resources.ps1'),
            '-Mode',purpose,'-RuntimeRoot',plan['archive_directory']]


def make_clock_manifest(plan,directory,purpose,context):
    directory=local_path(directory)
    if directory.exists(): raise ValueError('New unique clock directory required; no repeated recovery/check')
    directory.mkdir(parents=True)
    _,timing=validate_plan(plan); build=load(local_path(plan['probe_build_manifest']))
    if build['content_commit']!=plan['content_commit']: raise ValueError('Probe build belongs to another content')
    allowed=plan['allowed_cpus']
    binary=build['binary']; digest=build['binary_sha256']
    wrapper='import hashlib,os; p='+repr(binary)+'; assert hashlib.sha256(open(p,"rb").read()).hexdigest()=='+repr(digest)+'; os.execv(p,[p])'
    budget=240 if purpose=='recovery' else 60
    manifest={'schema':'raw-grid-clock-manifest-v1','batch_id':directory.name,'declared_at':utc_now(),
        'purpose':purpose,'context':context,'timing_version':FORMAL_RAW_VERSION,
        'timing_protocol_hash':plan['timing_protocol_hash'],
        'measurement_protocol_hash':plan['measurement_protocol_hash'],
        'resource_policy_hash':load(ROOT/'configs/measurement_protocol.json')['resource_gate']['policy_hash'],
        'criteria':timing['admission'],'schedule':raw_schedule(purpose),'interval_count':len(raw_schedule(purpose)),
        'collection_budget_seconds':budget,'cpu_selection':{'selected_cpu':-1,'allowed_cpus':allowed},
        'git_files':load(local_path(plan['git_identity']))['files'],
        'source_sha256':{p:v['executed_sha256'] for p,v in plan['windows_source_identity'].items()},
        'probe_binary':binary,'binary_sha256':digest,'probe_build':build,
        'probe_command':linux(plan,['timeout','--signal=TERM','--kill-after=5',str(budget-5),'python3','-c',wrapper]),
        'resource_command':resource_command(plan,'Recovery') if purpose=='recovery' else None,
        'stop_rule':'One fixed round; no replacement/filtering/calibration. Any failure or indeterminate interval stops formal work.'}
    atomic_write_json(directory/'manifest.json',manifest)
    return manifest


def collect_check(plan,directory,purpose,context,deadline=None):
    make_clock_manifest(plan,directory,purpose,context)
    from scripts.run_fixed_work_clock import collect
    code=collect(directory,formal=True,deadline=deadline)
    checked=audit_clock(directory,context)
    atomic_write_json(local_path(directory)/'independent_check.json',checked)
    if code!=0 or not checked['raw_reference_pass']: raise ValueError(purpose+' RAW/QPC check failed: '+json.dumps(checked.get('raw_failure_indices',checked['errors'])))
    return checked


def gate(plan,directory,purpose,context,deadline):
    directory=local_path(directory); directory.mkdir(parents=True,exist_ok=False)
    protocol,_=validate_plan(plan); command=resource_command(plan,purpose)
    budget=120 if purpose=='Formal' else min(60,max(0,deadline-time.perf_counter()))
    manifest={'schema':'raw-grid-resource-batch-v1','purpose':purpose,'context':context,'command':command,
              'policy_hash':protocol['resource_gate']['policy_hash'],'budget_seconds':budget}
    atomic_write_json(directory/'gate_manifest.json',manifest)
    started,frequency=qpc(); end_at=min(deadline,time.perf_counter()+budget); names=[]; admitted=False
    while time.perf_counter()<end_at:
        name='sample_'+str(len(names)); names.append(name)
        op=capture(command,directory,name,directory.name,timeout=min(60,end_at-time.perf_counter()))
        try: parsed=load(directory/op['stdout_path'])
        except (ValueError,KeyError,OSError): parsed={}
        admitted=op['returncode']==0 and not op['timed_out'] and valid_gate(parsed,protocol,purpose) and time.perf_counter()<=end_at
        print(json.dumps({'event':'resource_gate','purpose':purpose,'context':context,'admitted':admitted,
              'warnings':parsed.get('warnings'),'reasons':parsed.get('rejection_reasons'),
              'elapsed_qpc_seconds':(qpc()[0]-started)/frequency}),flush=True)
        if admitted or purpose=='Recovery': break
        time.sleep(max(0,min(10,end_at-time.perf_counter())))
    ended=qpc()[0]
    atomic_write_json(directory/'gate_outcome.json',{'operations':names,'qpc_start':started,'qpc_end':ended,
        'qpc_frequency':frequency,'qpc_seconds':(ended-started)/frequency,'admitted':admitted})
    # Independent recomputation, not merely the child exit code or saved PASS.
    return admitted and audit_gate(directory,protocol,purpose,context)


def recovery(plan):
    protocol,timing=validate_plan(plan)
    output=local_path(plan['session_directory']); initial=output/'initial_checkpoint.json'
    if sha256_file(output/'checkpoint.json')!=sha256_file(initial): raise ValueError('Recovery requires unchanged new empty session')
    directory=local_path(plan['recovery_directory'])
    context={'content_commit':plan['content_commit'],'session_id':plan['session_id'],'initial_checkpoint_sha256':sha256_file(initial)}
    started,frequency=qpc(); deadline=time.perf_counter()+240
    make_clock_manifest(plan,directory,'recovery',context)
    envelope={'qpc_start':started,'qpc_frequency':frequency,'status':'running','content_commit':plan['content_commit'],'session_id':plan['session_id']}
    atomic_write_json(directory/'recovery_operation.json',envelope)
    failure=None
    try:
        op=capture(resource_command(plan,'Recovery'),directory,'resources',directory.name,
                   sha256_file(directory/'manifest.json'),timeout=min(60,deadline-time.perf_counter()))
        if op['returncode']!=0 or op['timed_out'] or not valid_gate(load(directory/op['stdout_path']),protocol,'Recovery'):
            raise ValueError('Recovery resource gate rejected; clock intervals not started')
        from scripts.run_fixed_work_clock import collect
        code=collect(directory,formal=True,deadline=deadline)
        if code!=0: failure='Native RAW recovery did not complete normally'
    except (ValueError,KeyError,OSError,TimeoutError) as error: failure=str(error)
    ended=qpc()[0]; envelope.update(qpc_end=ended,qpc_seconds=(ended-started)/frequency,failure_reason=failure,status='returned')
    atomic_write_json(directory/'recovery_operation.json',envelope)
    checked=audit_recovery(directory,plan,initial)
    if sha256_file(output/'checkpoint.json')!=sha256_file(initial):
        checked['recovery_eligible']=False; checked['errors'].append('Session changed during recovery')
    atomic_write_json(directory/'independent_recovery.json',checked)
    if checked['recovery_eligible'] and failure is None:
        certificate={'schema':'raw-grid-recovery-certificate-v1','content_commit':plan['content_commit'],
            'session_id':plan['session_id'],'timing_protocol_hash':plan['timing_protocol_hash'],
            'measurement_protocol_hash':plan['measurement_protocol_hash'],
            'initial_checkpoint_sha256':sha256_file(initial),'manifest_sha256':sha256_file(directory/'manifest.json'),'audit':checked}
        atomic_write_json(directory/'certificate.json',certificate)
    print(json.dumps({'event':'recovery_complete','result':checked,'failure':failure}),flush=True)
    return 0 if checked['recovery_eligible'] and failure is None else 2


def run_grid(plan,plan_path):
    validate_plan(plan); output=local_path(plan['session_directory']); recovery_dir=local_path(plan['recovery_directory'])
    require_certificate(recovery_dir,plan,output/'initial_checkpoint.json')
    start=load(recovery_dir/'recovery_operation.json'); frequency=start['qpc_frequency']; start_ticks=start['qpc_start']
    def remaining(): return 28800-(qpc()[0]-start_ticks)/frequency
    status={'schema':'raw-grid-controller-v1','status':'running','started_qpc':start_ticks,'qpc_frequency':frequency,
            'budget_seconds':28800,'formal_target_invoked':False,'failure_reason':None,'phase':'preflight'}
    def progress():
        state=load(output/'checkpoint.json'); sample=load(output/'progress.json') if (output/'progress.json').exists() else None
        if sample and (not state['active'] or sample['attempt_id']!=state['active']['attempt_id']): sample=None
        payload={'event':'progress','at':utc_now(),'completed':len(state['completed']),'active':state['active'],
            'sample':sample,'child_state':'running','phase':status['phase'],
            'process_elapsed_qpc_seconds':(qpc()[0]-status.get('current_operation_started_qpc',qpc()[0]))/frequency,
            'cumulative_qpc_seconds':28800-remaining(),
            'remaining_budget_seconds':max(0,remaining()),'last_checkpoint_saved':state.get('updated_at',state['created_at'])}
        atomic_write_json(output/'host_progress.json',payload); print(json.dumps(payload),flush=True)
    last=time.perf_counter()
    def heartbeat():
        nonlocal last
        if time.perf_counter()-last>=60: progress(); last=time.perf_counter()
    def operation(mode,name,extra=(),maximum=None):
        seconds=remaining()
        if seconds<=5: raise TimeoutError('8-hour host QPC budget exhausted')
        seconds=min(seconds,maximum or seconds)
        command=linux(plan,['timeout','--signal=TERM','--kill-after=20',str(max(1,seconds-2)),
            'python3','-m','autotuner.raw_grid','--plan',wsl_path(plan_path),mode,*extra])
        status.update(phase=mode,current_operation_started_qpc=qpc()[0],current_operation=name)
        atomic_write_json(output/'controller.json',status)
        record=capture(command,output/'operations',name,plan['session_id'],timeout=seconds,progress=heartbeat)
        if record['returncode']!=0 or record['timed_out']: raise ValueError(name+' returned '+str(record['returncode']))
        return record
    try:
        state=load(output/'checkpoint.json')
        if state['active'] is not None: raise ValueError('Unfinished attempt preserved; this controller never automatically retries failed groups')
        if not state.get('artifacts'):
            context={'content_commit':plan['content_commit'],'session_id':plan['session_id'],'purpose':'setup'}
            if not gate(plan,output/'setup_gate','Formal',context,time.perf_counter()+remaining()): raise ValueError('Setup Formal resource wait exhausted')
            operation('setup','setup',maximum=900)
        for index in range(len(state['completed']),20):
            if (output/'PAUSE_REQUEST').exists(): raise ValueError('User pause request preserved; stopping before next group')
            attempt=uuid.uuid4().hex; checks=output/'group_checks'/attempt
            checks.mkdir(parents=True,exist_ok=False)
            context={'content_commit':plan['content_commit'],'session_id':plan['session_id'],'config_index':index,'attempt_id':attempt}
            status.update(phase='configuration_resource_gate',config_index=index,attempt_id=attempt)
            if not gate(plan,checks/'resources','Formal',context,time.perf_counter()+remaining()): raise ValueError('Configuration Formal resource wait exhausted')
            status['phase']='group_before_clock'
            collect_check(plan,checks/'before','before',{**context,'phase':'before'},time.perf_counter()+remaining())
            status['formal_target_invoked']=True; atomic_write_json(output/'controller.json',status)
            operation('measure','measure_'+attempt,('--index',str(index),'--attempt-id',attempt,'--checks-directory',wsl_path(checks)))
            path=output/'configurations'/f'grid_{attempt}.json'
            status['phase']='group_after_clock'
            collect_check(plan,checks/'after','after',{**context,'phase':'after','group_sha256':sha256_file(path)},time.perf_counter()+remaining())
            operation('accept','accept_'+attempt,('--index',str(index),'--attempt-id',attempt,'--checks-directory',wsl_path(checks)))
            progress()
        status['status']='complete'
    except (ValueError,KeyError,OSError,TimeoutError) as error:
        status.update(status='blocked_or_partial',failure_reason=str(error)); print(json.dumps(status),flush=True)
    finally:
        ended=qpc()[0]; status.update(ended_qpc=ended,total_qpc_seconds=(ended-start_ticks)/frequency,
            remaining_budget_seconds=max(0,remaining()),updated_at=utc_now())
        atomic_write_json(output/'controller.json',status)
    return 0 if status['status']=='complete' else 2


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('mode',choices=('initialize','recover','run','audit'))
    args=parser.parse_args(); plan=load(args.plan); validate_plan(plan)
    if args.mode=='initialize':
        command=linux(plan,['python3','-m','autotuner.raw_grid','--plan',wsl_path(args.plan.resolve()),'initialize'])
        op=capture(command,local_path(plan['session_directory']).parent,'initialize',plan['session_id'],timeout=90)
        return op['returncode'] if type(op['returncode']) is int else 1
    if args.mode=='recover': return recovery(plan)
    if args.mode=='run': return run_grid(plan,args.plan.resolve())
    from scripts.audit_raw_grid import audit_grid
    result=audit_grid(plan); atomic_write_json(local_path(plan['session_directory'])/'independent_audit.json',result)
    print(json.dumps(result)); return 0 if result['grid_complete'] and result['evidence_integrity_pass'] else 2


if __name__=='__main__': raise SystemExit(main())
