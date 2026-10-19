"""One explicitly user-authorized first-seed continuation; import the frozen 776b1117 runner."""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

CONTENT='776b11171d796c8071e69824ffe463c4faf8ba57'
SESSION='c1bd157c6c8d42439d0fb08f69156ff5'
USED=15841.5879168
TOTAL=43200
REMAINING=TOTAL-USED
SCHEMA='raw-first-seed-manual-continuation-v1'
CLAIM='MANUAL_FIRST_SEED_CONTINUATION_V1.claim.json'
OLD_ATTEMPT='aae9b1505c3c4a53aab33968a288876e'
JOB={'kind':'search','algorithm':'greedy','config':{'optimization':'O3','block_size':128}}
MUTABLE={'checkpoint.json','samples.jsonl','progress.json'}
SELF=Path(__file__).resolve()

def read(path): return json.loads(Path(path).read_bytes())
def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def rows(path): return [json.loads(x) for x in Path(path).read_bytes().splitlines() if x]

def frozen(plan):
    root=Path(plan['windows_archive_directory']).resolve()
    sys.path.insert(0,str(root))
    f=importlib.import_module('scripts.start_raw_comparison')
    c=importlib.import_module('scripts.raw_comparison_contract')
    for name,module in tuple(sys.modules.items()):
        if (name=='autotuner' or name.startswith('autotuner.') or name=='scripts' or name.startswith('scripts.')) and getattr(module,'__file__',None):
            if not Path(module.__file__).resolve().is_relative_to(root):
                raise ValueError('Not the exact 776b1117 archive: '+name)
    f.validate_plan(plan)
    return f,c

def elapsed(window):
    if any(type(window[k]) is not int or window[k]<=0 for k in ('qpc_start','qpc_end','qpc_frequency')):
        raise ValueError('Invalid integer QPC endpoints/frequency')
    value=(window['qpc_end']-window['qpc_start'])/window['qpc_frequency']
    if value<0: raise ValueError('QPC regressed')
    return value

def cumulative(window):
    value=elapsed(window)
    if window['budget_seconds']!=REMAINING or USED+value>TOTAL:
        raise ValueError('Original remaining activity allowance exceeded/reset')
    return USED+value

def check_start(plan,state,samples,old_window):
    if plan['content_commit']!=CONTENT or plan['session_id']!=SESSION or plan['mode']!='search' or state['session_id']!=SESSION or state['mode']!='search':
        raise ValueError('Wrong original content/session/mode')
    own=state['trajectories']
    if set(own)!={'random','greedy'} or len(own['random']['observations'])!=12 or len(own['random']['retests'])!=2 or len(own['greedy']['observations'])!=2 or own['greedy']['retests']:
        raise ValueError('Expected preserved Random12+2 and Greedy2')
    if state['status']!='stopped' or state['active']['attempt_id']!=OLD_ATTEMPT or state['active']['job']!=JOB or state['active']['saved_samples']!=2 or state['active'].get('formal_comparable') is not False:
        raise ValueError('Expected exact interrupted O3/s128 two-sample group')
    if state['target_executions']!=98 or len(samples)!=98 or len({s['run_id'] for s in samples})!=98 or [s['classification'] for s in samples[-2:]]!=['success','timeout'] or any(s['attempt_id']!=OLD_ATTEMPT for s in samples[-2:]):
        raise ValueError('Original 98 records / failed pair differ')
    if old_window['content_commit']!=CONTENT or old_window['session_id']!=SESSION or old_window['status']!='stopped' or old_window['budget_seconds']!=TOTAL or old_window['activity_qpc_seconds']!=USED or elapsed(old_window)!=USED:
        raise ValueError('Original closed activity/budget changed')
    return REMAINING

def check_prefix(path,size,sha):
    with Path(path).open('rb') as stream: value=stream.read(size)
    if len(value)!=size or hashlib.sha256(value).hexdigest()!=sha:
        raise ValueError('Original 98-sample byte prefix changed')

def verify_auth(auth):
    if auth['schema']!=SCHEMA or auth['content_commit']!=CONTENT or auth['session_id']!=SESSION or auth['previous_activity_qpc_seconds']!=USED or auth['remaining_allowance_seconds']!=REMAINING or auth['total_activity_limit_seconds']!=TOTAL or auth['helper_file']!=str(SELF) or auth['helper_sha256']!=digest(SELF):
        raise ValueError('Manual authorization/helper/remaining budget differs')
    if digest(auth['plan_file'])!=auth['plan_sha256']:
        raise ValueError('Frozen execution plan changed')
    content=subprocess.check_output(['git','-C',auth['repository_directory'],'show',auth['auxiliary_content_commit']+':scripts/continue_raw_search.py'])
    if hashlib.sha256(content).hexdigest()!=auth['helper_sha256']:
        raise ValueError('Helper execution bytes differ from its separate content commit')
    old=read(Path(auth['directory'])/'preserved/window.json')
    if elapsed(old)!=USED or digest(Path(auth['directory'])/'preserved/checkpoint.json')!=auth['checkpoint_sha256']:
        raise ValueError('Preserved original window/checkpoint differs')

def verify_preserved(auth,unchanged_checkpoint=False):
    repo=Path(auth['repository_directory']); session=Path(auth['session_directory'])
    for name,sha in auth['protected_files'].items():
        if digest(repo/name)!=sha: raise ValueError('Historical evidence changed: '+name)
    check_prefix(session/'samples.jsonl',auth['samples_prefix_bytes'],auth['samples_prefix_sha256'])
    state=read(session/'checkpoint.json'); old=read(Path(auth['directory'])/'preserved/checkpoint.json')
    for key in ('schema','session_id','fingerprint','mode','validation_groups','artifacts','setup_raw_seconds','reference_generation_calls'):
        if state[key]!=old[key]: raise ValueError('Frozen state/setup identity changed: '+key)
    if state['trajectories']['random']!=old['trajectories']['random'] or state['trajectories']['greedy']['observations'][:2]!=old['trajectories']['greedy']['observations']:
        raise ValueError('Accepted Random or original Greedy observations changed')
    if unchanged_checkpoint and digest(session/'checkpoint.json')!=auth['checkpoint_sha256']:
        raise ValueError('Checkpoint changed before fresh continuation admission')
    return state

def context_for(auth):
    plan=read(auth['plan_file'])
    return {'content_commit':CONTENT,'session_id':SESSION,'comparison_protocol_hash':plan['comparison_protocol_hash'],
        'continuation_authorization_sha256':digest(Path(auth['directory'])/'authorization.json'),
        'starting_checkpoint_sha256':auth['checkpoint_sha256']}

def prepare(plan_path,output,repo,auxiliary_sha):
    plan_path=plan_path.resolve(); output=output.resolve(); repo=repo.resolve()
    if output.exists(): raise ValueError('New continuation directory required')
    if output.name!='continuation' or output.parent.parent!=repo/'evidence/p3_raw_first_seed':
        raise ValueError('Expected a unique first-seed evidence batch/continuation directory')
    if len(auxiliary_sha)!=40 or any(c not in '0123456789abcdef' for c in auxiliary_sha): raise ValueError('Exact helper content SHA required')
    content=subprocess.check_output(['git','-C',str(repo),'show',auxiliary_sha+':scripts/continue_raw_search.py'])
    if hashlib.sha256(content).hexdigest()!=digest(SELF):raise ValueError('Helper not exported from the exact auxiliary commit')
    plan=read(plan_path); f,c=frozen(plan); session=Path(plan['session_directory'])
    samples=rows(session/'samples.jsonl'); state=read(session/'checkpoint.json')
    check_start(plan,state,samples,read(session/'window.json'))
    if (session/CLAIM).exists(): raise ValueError('Manual continuation already claimed; no budget reset')
    previous=c.audit(plan)
    if not previous['evidence_integrity_pass'] or previous['search_groups']!=14 or previous['completed_groups']!=16 or previous['partial_target_samples']!=2:
        raise ValueError('Original frozen independent audit failed')
    output.mkdir(parents=True); preserved=output/'preserved'; preserved.mkdir()
    for name in ('checkpoint.json','samples.jsonl','window.json','ACTIVITY.claim.json','initial_checkpoint.json','progress.json','controller_progress.json'):
        if (session/name).exists(): shutil.copy2(session/name,preserved/name)
    protected={p.relative_to(repo).as_posix():digest(p) for p in (repo/'evidence').rglob('*') if p.is_file() and
        not p.is_relative_to(output.parent) and not (p.is_relative_to(session) and p.relative_to(session).as_posix() in MUTABLE)}
    # Exclude only this task's unique directory, not another historical batch.
    auth={'schema':SCHEMA,'authorized_by':'User after d706a96a: one manual continuation, old used time retained, remaining allowance only',
        'scope':'Greedy remaining ten unique configurations and own deduplicated prefix retests; no Random rerun, extra seed or new budget',
        'content_commit':CONTENT,'session_id':SESSION,'auxiliary_content_commit':auxiliary_sha,
        'helper_file':str(SELF),'helper_sha256':digest(SELF),'directory':str(output),'repository_directory':str(repo),
        'session_directory':str(session),'plan_file':str(plan_path),'plan_sha256':digest(plan_path),
        'previous_activity_qpc_seconds':USED,'remaining_allowance_seconds':REMAINING,'total_activity_limit_seconds':TOTAL,
        'checkpoint_sha256':digest(session/'checkpoint.json'),'samples_prefix_bytes':(session/'samples.jsonl').stat().st_size,
        'samples_prefix_sha256':digest(session/'samples.jsonl'),'old_attempt':OLD_ATTEMPT,'old_partial_run_ids':[s['run_id'] for s in samples[-2:]],
        'protected_files':protected,'original_run_ids':[s['run_id'] for s in samples]}
    f.atomic_write_json(output/'previous_independent_audit.json',previous)
    f.claim(output/'authorization.json',auth)
    print(json.dumps({'authorization':str(output/'authorization.json'),'protected_files':len(protected),'remaining_seconds':REMAINING}),flush=True)

def reactivate(state,auth):
    result=copy.deepcopy(state)
    if result['active']['attempt_id']!=OLD_ATTEMPT or result['active']['job']!=JOB or result['active']['saved_samples']!=2:
        raise ValueError('Only reviewed interrupted group may be abandoned')
    result['manual_resume']={'schema':SCHEMA,'authorization_sha256':digest(Path(auth['directory'])/'authorization.json'),
        'abandoned_attempt':copy.deepcopy(state['active']),'abandoned_run_ids':auth['old_partial_run_ids']}
    result.update(active=None,status='ready')
    result.pop('failure_reason',None)
    return result

def run(auth_path):
    auth=read(auth_path); verify_auth(auth); plan=read(auth['plan_file']); f,c=frozen(plan)
    output=Path(auth['directory']); session=Path(auth['session_directory'])
    state=verify_preserved(auth,True); check_start(plan,state,rows(session/'samples.jsonl'),read(session/'window.json'))
    c.require_certificate(plan) # Preserved original identity only; NEVER the current fresh admission.
    started,hz=f.qpc(); budget=REMAINING
    window={'schema':SCHEMA,'content_commit':CONTENT,'session_id':SESSION,'authorization_sha256':digest(auth_path),
        'qpc_start':started,'qpc_frequency':hz,'budget_seconds':budget,'previous_activity_qpc_seconds':USED,
        'controller_pid':os.getpid(),'status':'running','phase':'preflight','failure_reason':None}
    f.claim(session/CLAIM,window)
    deadline=time.perf_counter()+budget-15; last=-60.
    def progress(force=False):
        nonlocal last
        now,frequency=f.qpc()
        if frequency!=hz: raise ValueError('QPC frequency changed')
        used=(now-started)/hz
        if not force and used-last<60:return
        last=used; cp=read(session/'checkpoint.json')
        sample=read(session/'progress.json') if (session/'progress.json').exists() else None
        if sample and (not cp['active'] or sample['attempt_id']!=cp['active']['attempt_id']): sample=None
        value={**window,'at':f.utc_now(),'activity_qpc_seconds':used,'cumulative_activity_qpc_seconds':USED+used,
            'remaining_budget_seconds':max(0,budget-used),'active':cp['active'],'sample_progress':sample,
            'search_complete':{a:len(t['observations']) for a,t in cp['trajectories'].items()},
            'retest_complete':{a:len(t['retests']) for a,t in cp['trajectories'].items()},'target_executions':cp['target_executions']}
        f.atomic_write_json(output/'progress.json',value); print(json.dumps(value),flush=True)
    try:
        with f.SleepRequest(output/'sleep_request.json'):
            context=context_for(auth)
            f.check_volume(session,output/'evidence_volume_start.json',context)
            f.atomic_write_json(output/'power_event_start.json',f.PowerEvents(output/'power_events').read())
            code='import ctypes,json; s=type("S",(ctypes.Structure,),{"_fields_":[("ac",ctypes.c_ubyte),("flag",ctypes.c_ubyte),("pct",ctypes.c_ubyte),("r",ctypes.c_ubyte),("life",ctypes.c_uint32),("full",ctypes.c_uint32)]})(); ok=ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(s)); print(json.dumps({"ok":bool(ok),"ac":s.ac,"battery_percent":s.pct})); raise SystemExit(0 if ok and s.ac==1 else 2)'
            op=f.capture([sys.executable,'-B','-X','utf8','-c',code],output,'ac_status','manual-search',timeout=15)
            if op['returncode']!=0 or op['timed_out']:raise ValueError('AC power required; keep lid open')
            if (session/'PAUSE_REQUEST').exists():raise ValueError('Pause marker present; preserved')
            window['phase']='formal_preflight';progress(True)
            if not f.gate(plan,output/'admission_resources','Formal',context,min(deadline,time.perf_counter()+119)):
                raise ValueError('Formal preflight exhausted; no new clock/target')
            window['phase']='fresh_short_long_admission';progress(True)
            f.clock_check(plan,output/'admission','admission',context,min(deadline,time.perf_counter()+120))
            admitted=f.audit_clock(output/'admission',context)
            if not admitted['clock_complete'] or not admitted['evidence_integrity_pass'] or not admitted['raw_reference_pass'] or admitted['errors']:
                raise ValueError('Fresh manual admission failed')
            f.atomic_write_json(output/'fresh_admission.json',{'schema':SCHEMA,'context':context,'audit':admitted})
            code='import json,sys; from pathlib import Path; from autotuner.raw_comparison import opened; from autotuner.core import sha256_file; p=json.load(open(sys.argv[1])); o,pr,m,t,s=opened(p); assert s["artifacts"]==p["expected_artifacts"]; assert all(sha256_file(Path(n))==h for n,h in p["verified_cache_files"].items()); print(json.dumps({"verified":True,"setup_invoked":False,"reference_generation_calls":s["reference_generation_calls"]}))'
            op=f.capture(f.linux(plan,['python3','-c',code,f.wsl_path(auth['plan_file'])]),output,'verified_cache_reuse','manual-search',timeout=60)
            if op['returncode']!=0 or op['timed_out']:raise ValueError('Frozen runtime/compiler/cache verification failed')
            state=verify_preserved(auth,True); resumed=reactivate(state,auth)
            space=f.ConfigSpace.load(f.ROOT/'configs/config_space.json'); protocol=f.comparison_protocol()
            if f.next_job(resumed,space,protocol)!=JOB:raise ValueError('Resume would change own search order')
            f.atomic_write_json(output/'abandoned_attempt.json',resumed['manual_resume'])
            f.atomic_write_json(session/'checkpoint.json',resumed)
            while True:
                state=read(session/'checkpoint.json'); job=f.next_job(state,space,protocol)
                if job is None:
                    if state['status']!='complete':raise ValueError('No next job but campaign incomplete')
                    break
                if job['algorithm']!='greedy' or job['kind'] not in ('search','retest'):raise ValueError('Only remaining Greedy work authorized')
                if (session/'PAUSE_REQUEST').exists():raise ValueError('Pause requested; marker preserved')
                if deadline-time.perf_counter()<=60:raise TimeoutError('Insufficient remaining activity budget')
                attempt=uuid.uuid4().hex; checks=session/'group_checks'/attempt;checks.mkdir()
                ctx=f.job_context(plan,job,attempt);window.update(job=job,attempt_id=attempt,phase='group_resources');progress(True)
                f.check_volume(checks,checks/'evidence_volume.json',ctx)
                if not f.gate(plan,checks/'resources','Formal',ctx,min(deadline,time.perf_counter()+119)):raise ValueError('Group Formal gate exhausted')
                window['phase']='before_clock';progress(True)
                f.clock_check(plan,checks/'before','before',{**ctx,'phase':'before'},deadline)
                window['phase']='evaluation';progress(True)
                f.measure(plan,Path(auth['plan_file']),job,attempt,checks,deadline,progress)
                group=session/'configurations'/(job['kind']+'_'+attempt+'.json')
                window['phase']='after_clock';progress(True)
                f.clock_check(plan,checks/'after','after',{**ctx,'phase':'after','group_sha256':digest(group)},deadline)
                seconds=deadline-time.perf_counter()
                op=f.capture(f.linux(plan,['timeout','--signal=TERM','--kill-after=5',str(max(1,seconds-5)),'python3','-m','autotuner.raw_comparison','--plan',f.wsl_path(auth['plan_file']),'accept','--attempt-id',attempt,'--checks-directory',f.wsl_path(checks)]),output/'operations','accept_'+attempt,'manual-search',timeout=seconds,progress=progress)
                if op['returncode']!=0 or op['timed_out']:raise ValueError('Frozen accept failed')
                progress(True)
            verify_preserved(auth);window.update(status='complete',phase='cleanup')
    except (ValueError,KeyError,TypeError,OSError,TimeoutError,KeyboardInterrupt) as error:
        window.update(status='stopped',failure_reason=str(error))
        if (output/'abandoned_attempt.json').exists():
            state=read(session/'checkpoint.json');state.update(status='stopped',failure_reason=str(error))
            if state['active']:state['active'].update(formal_comparable=False,failure_reason=str(error))
            f.atomic_write_json(session/'checkpoint.json',state)
    finally:
        ended,end_hz=f.qpc(); window.update(qpc_end=ended,ended_at=f.utc_now(),activity_qpc_seconds=(ended-started)/hz)
        window.update(cumulative_activity_qpc_seconds=USED+window['activity_qpc_seconds'],budget_pass=end_hz==hz and USED+window['activity_qpc_seconds']<=TOTAL)
        f.atomic_write_json(output/'window.json',window);progress(True)
    return 0 if window['status']=='complete' and window['budget_pass'] else 2

def audit(auth_path):
    auth=read(auth_path); verify_auth(auth); plan=read(auth['plan_file']);f,c=frozen(plan)
    output=Path(auth['directory']);session=Path(auth['session_directory'])
    result={'schema':SCHEMA+'-audit','scope':'first_seed','evidence_integrity_pass':False,'execution_complete':False,
        'timing_checks_pass':False,'comparison_ready':False,'five_seed_execution_complete':False,'errors':[]}
    try:
        state=verify_preserved(auth);window=read(output/'window.json');claim=read(session/CLAIM)
        if any(window[k]!=claim[k] for k in ('authorization_sha256','qpc_start','qpc_frequency','budget_seconds','content_commit','session_id')) or window['authorization_sha256']!=digest(auth_path):raise ValueError('Manual claim/window mismatch')
        total=cumulative(window)
        if total!=window['cumulative_activity_qpc_seconds'] or window['budget_pass'] is not True:raise ValueError('Cumulative budget mismatch')
        power=read(output/'sleep_request.json')
        if not power['acquired'] or not power['released'] or power['thread_id']!=power['release_thread_id']:raise ValueError('Sleep request not released')
        c.require_certificate(plan)
        context=context_for(auth)
        c.audit_volume(output/'evidence_volume_start.json',session,context)
        measurement=read(f.ROOT/'configs/measurement_protocol.json')
        resource=c.audit_gate(output/'admission_resources',measurement,'Formal',context) if (output/'admission_resources/gate_outcome.json').exists() else False
        admission=f.audit_clock(output/'admission',context) if (output/'admission/native_process.json').exists() else None
        fresh=bool(resource and admission and admission['clock_complete'] and admission['evidence_integrity_pass'] and admission['raw_reference_pass'] and not admission['errors'])
        records=rows(session/'samples.jsonl');by_id={s['run_id']:s for s in records}
        if len(by_id)!=len(records) or state['target_executions']!=len(records):raise ValueError('Duplicate/miscounted target records')
        abandoned=set(auth['old_partial_run_ids']);attempts=set();scored=set();ordered=[];filenames=set();groups=[]
        space=f.ConfigSpace.load(f.ROOT/'configs/config_space.json')
        for algorithm in ('random','greedy'):
            own=state['trajectories'][algorithm]
            if len(own['observations'])>12 or len({json.dumps(g['config'],sort_keys=True) for g in own['observations']})!=len(own['observations']):raise ValueError('Nonunique/excess observations')
            c.replay(space,algorithm,own['observations'])
            prefix=c.prefixes(space,algorithm,own['observations'])
            if own['prefixes']!=prefix:raise ValueError('Own prefix differs')
            candidates={json.dumps(p['best_config'],sort_keys=True) for p in prefix}
            retests=[json.dumps(g['config'],sort_keys=True) for g in own['retests']]
            if len(retests)!=len(set(retests)) or not set(retests)<=candidates:raise ValueError('Candidate retests differ')
            mapping=[dict(p,retest_attempt=next((g['attempt_id'] for g in own['retests'] if g['config']==p['best_config']),None)) for p in prefix]
            if own['prefix_retest_mapping']!=mapping:raise ValueError('Retest mapping differs')
            for kind,values in (('search',own['observations']),('retest',own['retests'])):
                for group in values:
                    attempt=group['attempt_id'];job={'kind':kind,'algorithm':algorithm,'config':group['config']}
                    if attempt in attempts or attempt==OLD_ATTEMPT:raise ValueError('Accepted attempt reused/abandoned')
                    attempts.add(attempt); filename=kind+'_'+attempt+'.json';filenames.add(filename)
                    original=read(session/'configurations'/filename)
                    if digest(session/'configurations'/filename)!=group['measured_group_sha256'] or any(group.get(k)!=v for k,v in original.items()):raise ValueError('Accepted raw group changed')
                    if f.local_path(group['checks_directory']).resolve()!=(session/'group_checks'/attempt).resolve():raise ValueError('Wrong checks directory')
                    c.verify_group(plan,job,attempt,group,group['checks_directory']);groups.append(group)
                    for sample in group['samples']:
                        if by_id.get(sample['run_id'])!=sample or sample['run_id'] in scored or sample['run_id'] in abandoned:raise ValueError('Scored sample missing/shared/abandoned')
                        scored.add(sample['run_id']);ordered.append(sample['run_id'])
        filtered=[s['run_id'] for s in records if s['run_id'] not in abandoned]
        if filtered[:len(ordered)]!=ordered:raise ValueError('Chronological accepted record order differs')
        for sample in records:
            run_directory=session/'runs'/Path(sample['run_directory']).name
            if any(sample.get(k)!=v for k,v in read(run_directory/'result.json').items()) or sample['source']!='fresh_measurement' or sample['context']['force_remeasure'] is not True:raise ValueError('Nonfresh or inconsistent raw record')
            if (run_directory/'stdout.txt').read_text()!=sample['raw_stdout'] or (run_directory/'stderr.txt').read_text()!=sample['raw_stderr']:raise ValueError('Raw streams differ')
        extras={p.name for p in (session/'configurations').glob('*.json')}-filenames-{'search_'+OLD_ATTEMPT+'.json'}
        pending=set(by_id)-scored-abandoned
        active=state['active']
        if active and active['attempt_id']!=OLD_ATTEMPT:
            extras.discard(active['job']['kind']+'_'+active['attempt_id']+'.json')
            if active['saved_samples']!=len(pending):raise ValueError('Partial sample count differs')
        elif pending:raise ValueError('Unreferenced target sample')
        if extras or {p.name for p in (session/'runs').iterdir() if p.is_dir()}!={Path(s['run_directory']).name for s in records}:raise ValueError('Extra group or run directory')
        transitioned=(output/'abandoned_attempt.json').exists()
        if transitioned and state.get('manual_resume')!=read(output/'abandoned_attempt.json'):raise ValueError('Abandonment ledger changed')
        if transitioned:
            operation=c.checked_operation(output,'verified_cache_reuse')
            cached=read(output/operation['stdout_path'])
            if operation['returncode']!=0 or operation['timed_out'] or cached!={'verified':True,'setup_invoked':False,'reference_generation_calls':state['reference_generation_calls']}:
                raise ValueError('Frozen runtime/cache reuse proof missing or inconsistent')
        r=sum(len(t['retests']) for t in state['trajectories'].values());n=sum(len(t['observations']) for t in state['trajectories'].values())
        complete=bool(transitioned and state['status']=='complete' and active is None and not pending and window['status']=='complete' and n==24 and 2<=r<=6 and len(groups)==24+r and len(records)==146+6*r and all(len(t['observations'])==12 and [p['budget'] for p in t['prefixes']]==[4,8,12] and {json.dumps(g['config'],sort_keys=True) for g in t['retests']}=={json.dumps(p['best_config'],sort_keys=True) for p in t['prefixes']} and all(p['retest_attempt'] is not None for p in t['prefix_retest_mapping']) for t in state['trajectories'].values()))
        result.update(evidence_integrity_pass=True,execution_complete=complete,timing_checks_pass=complete and fresh,
            comparison_ready=complete and fresh,fresh_admission_pass=fresh,search_groups=n,retest_groups=r,target_executions=len(records),
            accepted_target_samples=len(scored),abandoned_target_samples=2 if transitioned else 0,historical_unaccepted_samples=2,
            new_partial_target_samples=len(pending),previous_activity_qpc_seconds=USED,continuation_activity_qpc_seconds=window['activity_qpc_seconds'],
            cumulative_activity_qpc_seconds=total,failure_reason=window['failure_reason'])
    except (ValueError,KeyError,TypeError,OSError,IndexError) as error:result['errors'].append(str(error))
    f.atomic_write_json(output/'independent_continuation_audit.json',result);print(json.dumps(result),flush=True)
    return 0 if result['comparison_ready'] else 2

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mode',choices=('prepare','run','audit'))
    parser.add_argument('--plan',type=Path);parser.add_argument('--output',type=Path);parser.add_argument('--repository-root',type=Path)
    parser.add_argument('--auxiliary-sha');parser.add_argument('--authorization',type=Path);args=parser.parse_args()
    if args.mode=='prepare':prepare(args.plan,args.output,args.repository_root,args.auxiliary_sha)
    elif args.mode=='run':raise SystemExit(run(args.authorization))
    else:raise SystemExit(audit(args.authorization))
