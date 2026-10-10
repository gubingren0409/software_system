"""WSL half of the new RAW Grid: empty initialization and staged group acceptance."""
from __future__ import annotations
import argparse,json,os,signal,sys,uuid
from dataclasses import asdict
from pathlib import Path
from .core import Config,ConfigSpace,Evaluator,TargetAdapter,sha256_file,sha256_json,utc_now
from .measurement import ConfigurationEvaluator
from .session import source_identity,restore_complete_group,export_grid
from .timing import require_formal_activation,relocate_target,execution_clock,FORMAL_RAW_VERSION
from scripts.p3_clock_contract import atomic_write_json,load
from scripts.raw_clock_contract import local_path,require_certificate,audit_clock,audit_gate
ROOT=Path(__file__).resolve().parents[1]


def runtime(plan):
    protocol=load(ROOT/'configs/measurement_protocol.json')
    timing=require_formal_activation(protocol,ROOT)
    if protocol['schema_version']!=6 or timing['version']!=FORMAL_RAW_VERSION or \
            sha256_json(protocol)!=plan['measurement_protocol_hash'] or \
            sha256_json(timing)!=plan['timing_protocol_hash'] or str(ROOT)!=plan['archive_directory']:
        raise ValueError('RAW plan/measurement/timing/archive identity differs')
    identity=load(local_path(plan['git_identity']))
    if identity['content_sha']!=plan['content_commit']: raise ValueError('Content/Git identity differs')
    files=source_identity(ROOT,identity['files'])
    output=local_path(plan['session_directory'])
    target_data=relocate_target(load(ROOT/'configs/target.json'),ROOT/'configs')
    target_data['cache_root']=plan['cache_directory']
    # Resolve from the original directory BEFORE writing into the session directory.
    if target_data['timing_protocol']['hash']!=plan['timing_protocol_hash']:
        raise ValueError('Target timing differs from formal protocol')
    target_path=output/'effective_target.json'
    if target_path.exists() and load(target_path)!=target_data: raise ValueError('Effective target changed')
    if not target_path.exists(): atomic_write_json(target_path,target_data)
    target=TargetAdapter.load(target_path,evidence_root=output)
    fingerprint={'content_commit':plan['content_commit'],'session_id':plan['session_id'],
        'files':files,'measurement_protocol_hash':sha256_json(protocol),
        'timing_protocol_hash':sha256_json(timing),'target_config_hash':sha256_json(target_data),
        'compiler_path':str(target.compiler),'compiler_version':target._compiler_version,
        'compiler_sha256':sha256_file(target.compiler)}
    return output,protocol,target,fingerprint


def initialize(plan):
    output=local_path(plan['session_directory'])
    if (output/'checkpoint.json').exists(): raise ValueError('Refusing to replace an existing session')
    output,protocol,target,fingerprint=runtime(plan)
    if fingerprint['compiler_sha256']!=plan['compiler_sha256']: raise ValueError('Frozen compiler differs')
    space=ConfigSpace.load(ROOT/'configs/config_space.json')
    if len(set(space.all()))!=20: raise ValueError('Not the frozen 20-configuration space')
    state={'schema':'raw-grid-session-v1','session_id':plan['session_id'],'fingerprint':fingerprint,
        'status':'initialized','completed':[],'active':None,'abandoned_attempts':[],
        'created_at':utc_now(),'target_executions':0,'reference_generation_calls':0}
    atomic_write_json(output/'checkpoint.json',state)
    atomic_write_json(output/'initial_checkpoint.json',state)
    atomic_write_json(output/'protocol.json',protocol)
    atomic_write_json(output/'session.json',{'fingerprint':fingerprint,
        'canonical_configurations':[asdict(c) for c in space.all()],
        'initialization_target_executions':0,'initialization_reference_calls':0})
    return 0


def opened(plan):
    output,protocol,target,fingerprint=runtime(plan)
    state=load(output/'checkpoint.json')
    if state['fingerprint']!=fingerprint or state['session_id']!=plan['session_id']:
        raise ValueError('Resume content/source/compiler/target/protocol/session differs')
    require_certificate(plan['recovery_directory'],plan,output/'initial_checkpoint.json')
    for index,group in enumerate(state['completed']):
        restore_complete_group(group,protocol)
        verify_group_clocks(plan,index,group['attempt_id'],group,group['clock_checks_directory'])
    return output,protocol,target,state


def setup(plan):
    output,protocol,target,state=opened(plan)
    if not audit_gate(output/'setup_gate',protocol,'Formal',{
            'content_commit':plan['content_commit'],'session_id':plan['session_id'],'purpose':'setup'}):
        raise ValueError('Setup needs a matching Formal gate')
    started=execution_clock(True); build_started=started
    space=ConfigSpace.load(ROOT/'configs/config_space.json'); binaries={}
    for optimization in space.optimization_levels:
        artifact=target.build_candidate(protocol['target_matrix_n'],optimization)
        binaries[optimization]=artifact.binary_sha256
        atomic_write_json(output/'manifests'/('candidate_'+optimization+'.json'),load(artifact.binary.parent/'manifest.json'))
    build_seconds=execution_clock(True)-build_started; ref_started=execution_clock(True)
    prior_reference_manifests={str(p):sha256_file(p) for p in (target.cache_root/'reference').glob('*/manifest.json')}
    reference=target.get_reference(protocol['target_matrix_n'],protocol['matrix_input_seed'],protocol['input_pattern'],600)
    generator=target.build_reference_generator(protocol['target_matrix_n'])
    atomic_write_json(output/'manifests/reference_build.json',load(generator.binary.parent/'manifest.json'))
    atomic_write_json(output/'manifests/reference.json',reference.metadata)
    fingerprint={'binary_hashes':binaries,'reference_key':reference.reference_key,'reference_sha256':reference.data_sha256}
    if 'artifacts' in state and state['artifacts']!=fingerprint: raise ValueError('Build/reference identities changed')
    state.update(artifacts=fingerprint,status='ready',setup_cost_clock='CLOCK_MONOTONIC_RAW',
        setup_seconds=execution_clock(True)-started,build_setup_seconds=build_seconds,
        reference_setup_seconds=execution_clock(True)-ref_started)
    # Unchanged cached manifests mean no generator execution; replacement/new manifest means one.
    state['reference_generation_calls']=int(prior_reference_manifests.get(str(reference.metadata_path))!=sha256_file(reference.metadata_path))
    atomic_write_json(output/'checkpoint.json',state); return 0


def group_context(plan,index,attempt_id,phase):
    return {'content_commit':plan['content_commit'],'session_id':plan['session_id'],
            'config_index':index,'attempt_id':attempt_id,'phase':phase}


def verify_group_clocks(plan,index,attempt,group,check_directory):
    directory=local_path(check_directory)
    protocol=load(ROOT/'configs/measurement_protocol.json')
    if not audit_gate(directory/'resources',protocol,'Formal',{
        'content_commit':plan['content_commit'],'session_id':plan['session_id'],
        'config_index':index,'attempt_id':attempt}): raise ValueError('Group Formal resource gate invalid')
    for phase in ('before','after'):
        context=group_context(plan,index,attempt,phase)
        if phase=='after': context['group_sha256']=sha256_file(local_path(plan['session_directory'])/'configurations'/f'grid_{attempt}.json')
        audit=audit_clock(directory/phase,context)
        if not audit['evidence_integrity_pass'] or not audit['raw_reference_pass']:
            raise ValueError('Group '+phase+' RAW/QPC check failed')
    if group['classification']!='success': raise ValueError('Failed group cannot complete')


def measure_group(plan,index,attempt,check_directory):
    output,protocol,target,state=opened(plan)
    configs=ConfigSpace.load(ROOT/'configs/config_space.json').all()
    if index!=len(state['completed']) or state['active'] is not None:
        raise ValueError('Unexpected index or unfinished group; no automatic retry')
    if not audit_gate(local_path(check_directory)/'resources',protocol,'Formal',{
        'content_commit':plan['content_commit'],'session_id':plan['session_id'],
        'config_index':index,'attempt_id':attempt}): raise ValueError('Group needs a matching Formal gate')
    before=audit_clock(local_path(check_directory)/'before',group_context(plan,index,attempt,'before'))
    if not before['raw_reference_pass']: raise ValueError('Fresh group-before RAW check required')
    config=configs[index]; stopped={'value':False}
    def stop(signum,frame): stopped['value']=True
    signal.signal(signal.SIGTERM,stop)
    def requested(): return stopped['value'] or (output/'PAUSE_REQUEST').exists()
    state.update(status='running',active={'index':index,'config':asdict(config),'attempt_id':attempt,'saved_samples':0})
    atomic_write_json(output/'checkpoint.json',state)
    def progress(index_of_sample):
        atomic_write_json(output/'progress.json',{'config_index':index,'config':asdict(config),
            'attempt_id':attempt,'sample_index':index_of_sample,'stage':'warmup' if index_of_sample==0 else 'measurement',
            'completed_configurations':len(state['completed']),'runner_pid':os.getpid(),'updated_at':utc_now()})
    def sampled(sample):
        state['active']['saved_samples']=sample['sample_index']+1; state['target_executions']+=bool(sample.get('timed_command'))
        state['updated_at']=utc_now(); atomic_write_json(output/'checkpoint.json',state)
        print(json.dumps({'event':'sample_saved','index':index,'sample_index':sample['sample_index'],
              'classification':sample['classification'],'raw_seconds':sample['score_seconds']}),flush=True)
    powershell='/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe'
    # Snapshot is quality evidence only; it does not impose CPU limits on the running target.
    script=plan['windows_archive_directory'].replace('\\','/')+'/scripts/check_p2_resources.ps1'
    host=[powershell,'-NoProfile','-File',script,'-Mode','Snapshot','-RuntimeRoot',str(ROOT)]
    executor=Evaluator(target,host,requested)
    result=ConfigurationEvaluator(executor,protocol,sha256_json(protocol),output,sampled,progress).evaluate(
        config,attempt_id=attempt,purpose='grid')
    state['status']='awaiting_group_after_check' if result['classification']=='success' else 'measurement_failure'
    atomic_write_json(output/'checkpoint.json',state)
    return 0 if result['classification']=='success' else 3


def accept_group(plan,index,attempt,check_directory):
    output,protocol,target,state=opened(plan)
    group=load(output/'configurations'/f'grid_{attempt}.json')
    restore_complete_group(group,protocol)
    if index!=len(state['completed']) or state['active']['attempt_id']!=attempt:
        raise ValueError('Group checkpoint identity differs')
    verify_group_clocks(plan,index,attempt,group,check_directory)
    group['clock_checks_directory']=str(check_directory)
    group['clock_checked_raw_group_sha256']=sha256_file(output/'configurations'/f'grid_{attempt}.json')
    state['completed'].append(group); state.update(active=None,status='complete' if len(state['completed'])==20 else 'ready',updated_at=utc_now())
    atomic_write_json(output/'checkpoint.json',state); export_grid(output,state['completed'])
    print(json.dumps({'completed':len(state['completed']),'config':group['config'],'median_raw_seconds':group['score_seconds']}),flush=True)
    return 0


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('mode',choices=('initialize','setup','measure','accept'))
    parser.add_argument('--index',type=int); parser.add_argument('--attempt-id'); parser.add_argument('--checks-directory')
    args=parser.parse_args(); plan=load(args.plan)
    if args.mode=='initialize': return initialize(plan)
    if args.mode=='setup': return setup(plan)
    if args.mode=='measure': return measure_group(plan,args.index,args.attempt_id,args.checks_directory)
    return accept_group(plan,args.index,args.attempt_id,args.checks_directory)


if __name__=='__main__': raise SystemExit(main())
