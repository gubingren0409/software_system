"""One-shot auxiliary launcher. Formal implementations always run from frozen archive."""
import json,os,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[2]; sys.path.insert(0,str(ROOT))
from autotuner.core import sha256_file,utc_now
from scripts.p3_clock_contract import capture,load,atomic_write_json


def main():
    directory=HERE/'final-content'; plan_path=directory/'plan.json'; plan=load(plan_path)
    marker=directory/'launch_manifest.json'
    if marker.exists(): raise ValueError('One-shot launch already exists; no repeated recovery')
    windows=Path(plan['windows_archive_directory']); session=Path(plan['session_directory'])
    entry=[sys.executable,'-B','-X','utf8',str(windows/'scripts/start_raw_grid.py'),'--plan',str(plan_path)]
    commands={'recovery':[*entry,'recover'],
      'recovery_independent':[sys.executable,'-B','-X','utf8',str(windows/'scripts/raw_clock_contract.py'),
         '--directory',plan['recovery_directory'],'--plan',str(plan_path),'--output',str(directory/'recovery_recomputed.json')],
      'formal_grid':[*entry,'run'],
      'grid_independent':[sys.executable,'-B','-X','utf8',str(windows/'scripts/audit_raw_grid.py'),
         '--plan',str(plan_path),'--output',str(directory/'grid_independent_audit.json')]}
    atomic_write_json(marker,{'schema':'raw-grid-one-shot-launch-v1','content_commit':plan['content_commit'],
        'session_id':plan['session_id'],'launcher_pid':os.getpid(),'helper_sha256':sha256_file(Path(__file__)),
        'helper_role':'Auxiliary orchestration only; all collection/admission/Grid/audit code from exact frozen archive',
        'declared_at':utc_now(),'commands':commands,'recovery_limit':1,'formal_grid_limit':1,
        'random_greedy_execution_limit':0})
    state={'content_commit':plan['content_commit'],'session_id':plan['session_id'],
           'recovery_invoked':False,'formal_invoked':False,'recovery_returncode':'unknown',
           'formal_returncode':'unknown','failure_reason':None}
    last=0
    def progress():
        nonlocal last
        if time.perf_counter()-last<60: return
        last=time.perf_counter()
        payload={'at':utc_now(),'phase':'formal' if state['formal_invoked'] else 'recovery','process_state':'captured child running'}
        for key,path in (('recovery_progress',Path(plan['recovery_directory'])/'progress.json'),
                         ('checkpoint',session/'checkpoint.json'),('target_progress',session/'progress.json'),
                         ('host_progress',session/'host_progress.json')):
            if path.exists():
                saved=load(path)
                if key=='checkpoint': saved={'status':saved['status'],'completed_count':len(saved['completed']),
                    'target_execution_count':saved['target_executions'],'active':saved['active'],'last_saved':saved.get('updated_at',saved['created_at'])}
                payload[key]=saved
        payload['elapsed_scope']='Host progress process elapsed is current captured WSL group/setup child, not matrix core; core samples use RAW.'
        atomic_write_json(directory/'launcher_progress.json',payload); print(json.dumps(payload),flush=True)
    def run(name,timeout):
        op=capture(commands[name],directory,name,plan['session_id'],timeout=timeout,progress=progress)
        print(json.dumps({'operation':name,'returncode':op['returncode'],'qpc_seconds':op['qpc_seconds']}),flush=True)
        return op['returncode']
    try:
        state['recovery_invoked']=True; state['recovery_returncode']=run('recovery',270)
        audit_code=run('recovery_independent',60)
        checked=load(directory/'recovery_recomputed.json')
        eligible=state['recovery_returncode']==0 and audit_code==0 and \
            all(checked.get(k) is True for k in ('evidence_integrity_pass','clock_complete','raw_reference_pass','recovery_eligible')) and \
            checked.get('interval_count')==12 and checked.get('response_count')==50 and not checked['errors']
        if not eligible:
            state['failure_reason']='Fresh RAW recovery rejected; no Formal or matrix target started'
        else:
            state['formal_invoked']=True; state['formal_returncode']=run('formal_grid',28830)
            if state['formal_returncode']!=0: state['failure_reason']='Formal Grid stopped/partial; see original controller and checkpoint'
        run('grid_independent',180)
    except (ValueError,KeyError,OSError) as error: state['failure_reason']=str(error)
    finally:
        state['ended_at']=utc_now(); atomic_write_json(directory/'launch_result.json',state)
        print(json.dumps(state),flush=True)
    return 0 if state['formal_returncode']==0 and state['failure_reason'] is None else 2


if __name__=='__main__': raise SystemExit(main())
