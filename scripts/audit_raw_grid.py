"""Independent RAW Grid audit; P3 comparison flags never follow Grid completion."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from autotuner.core import ConfigSpace,sha256_file,sha256_json,classify_execution
from autotuner.session import source_identity,restore_complete_group
from autotuner.raw_grid import verify_group_clocks
from autotuner.timing import require_formal_activation,execution_clock
from scripts.p3_clock_contract import load,atomic_write_json
from scripts.raw_clock_contract import local_path,require_certificate,checked_operation,audit_gate,audit_recovery,audit_clock


def audit_group_clock_inventory(plan,output):
    batches=[]
    for directory in sorted((output/'group_checks').glob('*')):
        for phase in ('before','after'):
            clock=directory/phase
            if not clock.exists(): continue
            manifest=load(clock/'manifest.json'); index=manifest['context']['config_index']
            if type(index) is not int or not 0<=index<20: raise ValueError('Invalid clock group index')
            context={'content_commit':plan['content_commit'],'session_id':plan['session_id'],
                'config_index':index,'attempt_id':directory.name,'phase':phase}
            if phase=='after': context['group_sha256']=sha256_file(output/'configurations'/('grid_'+directory.name+'.json'))
            batches.append({'directory':str(clock),'phase':phase,'config_index':index,
                            'audit':audit_clock(clock,context)})
    return batches


def audit_grid(plan):
    output=local_path(plan['session_directory'])
    result={'schema':'raw-grid-independent-audit-v1','evidence_integrity_pass':False,
        'grid_complete':False,'grid_timing_checks_pass':False,'execution_complete':False,
        'timing_checks_pass':False,'comparison_ready':False,'p3_search_comparison_complete':False,
        'completed_configurations':0,'target_execution_count':0,'complete_trajectory_count':0,
        'independent_retest_groups':0,'errors':[]}
    try:
        protocol=load(ROOT/'configs/measurement_protocol.json'); timing=require_formal_activation(protocol,ROOT)
        identity=load(local_path(plan['git_identity'])); files=source_identity(ROOT,identity['files'])
        if identity['content_sha']!=plan['content_commit'] or sha256_json(protocol)!=plan['measurement_protocol_hash'] or \
                sha256_json(timing)!=plan['timing_protocol_hash']:
            raise ValueError('Grid protocol/content identity differs')
        state=load(output/'checkpoint.json'); initial=load(output/'initial_checkpoint.json')
        if state['session_id']!=plan['session_id'] or initial['completed'] or initial['active'] is not None or \
                initial['target_executions']!=0 or initial['reference_generation_calls']!=0 or \
                state['fingerprint']!=initial['fingerprint'] or \
                state['fingerprint']['files']!=files or \
                state['fingerprint']['compiler_sha256']!=sha256_file(local_path('/usr/bin/x86_64-linux-gnu-gcc-13')):
            raise ValueError('Grid session/source/compiler/empty initial identity differs')
        recovery=audit_recovery(plan['recovery_directory'],plan,output/'initial_checkpoint.json')
        result['recovery_eligible']=recovery['recovery_eligible']
        result['recovery']=recovery
        if not recovery['recovery_eligible']:
            if state['completed'] or state['target_executions']: raise ValueError('Formal target ran without eligible recovery')
            result.update(evidence_integrity_pass=recovery['evidence_integrity_pass'],
                formal_grid_status='not_started_recovery_blocked',content_commit=plan['content_commit'],
                session_id=plan['session_id'],grid_timing_checks_pass=False,
                errors=['Recovery refused; no formal Grid targets executed',*recovery['errors']])
            return result
        require_certificate(plan['recovery_directory'],plan,output/'initial_checkpoint.json')
        configs=ConfigSpace.load(ROOT/'configs/config_space.json').all()
        if len(set(configs))!=20: raise ValueError('Configuration space is not 20 unique configurations')
        samples_path=output/'samples.jsonl'
        records=[json.loads(line) for line in samples_path.read_text().splitlines() if line] if samples_path.exists() else []
        by_id={sample['run_id']:sample for sample in records}
        if len(by_id)!=len(records): raise ValueError('Duplicate raw run IDs')
        result['target_execution_count']=sum(bool(s.get('timed_command')) for s in records)
        if state['target_executions']!=result['target_execution_count']: raise ValueError('Target count differs from raw records')
        for record in records:
            directory=output/'runs'/Path(record['run_directory']).name
            saved=load(directory/'result.json')
            if any(record.get(k)!=v for k,v in saved.items()): raise ValueError('Raw run JSON differs from JSONL')
            for field,name in (('raw_stdout','stdout.txt'),('raw_stderr','stderr.txt'),('raw_resource','resource.txt')):
                raw=(directory/name).read_text() if (directory/name).exists() else ''
                if raw!=record[field]: raise ValueError('Raw stream differs: '+name)
            executed=bool(record.get('timed_command'))
            if record['context']['force_remeasure'] is not True or (executed and record.get('source')!='fresh_measurement'):
                raise ValueError('Formal sample is not fresh')
            if not executed and (record['classification'] not in ('compile_failure','reference_failure','resource_rejected') or record.get('score_seconds') is not None):
                raise ValueError('Unexpected pre-execution record')
            if executed and record.get('timing_protocol_hash')!=plan['timing_protocol_hash']:
                raise ValueError('Raw sample timing binding differs')
            if executed:
                expected={'n':protocol['target_matrix_n'],'block_size':record['config']['block_size'],
                    'seed':protocol['matrix_input_seed'],'input':protocol['input_pattern'],
                    'input_generator':protocol['input_generator'],'abs_tol':protocol['abs_tolerance'],
                    'rel_tol':protocol['rel_tolerance'],'primary_clock':timing['primary_clock'],
                    'timing_protocol_version':timing['version']}
                classification,parsed,_=classify_execution(record['returncode'],record['timed_out'],record['raw_stdout'],
                                                          'matrix-multiplication-result-v2',expected)
                score=parsed.get('elapsed_seconds') if classification=='success' else None
                if classification!=record['classification'] or parsed!=record['target_result'] or score!=record['score_seconds']:
                    raise ValueError('Partial/complete raw execution contract differs')
        completed_ids=[]; summaries=[]
        for index,group in enumerate(state['completed']):
            if index>=20 or group['config']!=configs[index].__dict__: raise ValueError('Grid order/uniqueness differs')
            restore_complete_group(group,protocol)
            original=output/'configurations'/('grid_'+group['attempt_id']+'.json')
            if sha256_file(original)!=group['clock_checked_raw_group_sha256']:
                raise ValueError('Accepted measured group changed after post-check')
            if any(group.get(k)!=v for k,v in load(original).items()): raise ValueError('Accepted aggregate differs')
            verify_group_clocks(plan,index,group['attempt_id'],group,group['clock_checks_directory'])
            for sample_index,sample in enumerate(group['samples']):
                if sample!=by_id.get(sample['run_id']) or sample['attempt_id']!=group['attempt_id'] or \
                        sample['config']!=group['config'] or sample['role']!=('warmup' if sample_index==0 else 'measurement'):
                    raise ValueError('Accepted group/sample identity differs')
                if sample['binary_sha256']!=state['artifacts']['binary_hashes'][group['config']['optimization']] or \
                        sample['reference_sha256']!=state['artifacts']['reference_sha256']:
                    raise ValueError('Sample binary/reference differs from session artifacts')
                completed_ids.append(sample['run_id'])
            summaries.append({'index':index,'config':group['config'],'median_raw_seconds':group['score_seconds'],
                              'statistics':group['statistics'],'attempt_id':group['attempt_id']})
        if len(set(completed_ids))!=len(completed_ids): raise ValueError('Sample shared across configurations')
        if state.get('artifacts'):
            for opt,digest in state['artifacts']['binary_hashes'].items():
                manifest=load(output/'manifests'/('candidate_'+opt+'.json'))
                if manifest['binary_sha256']!=digest or sha256_file(local_path(manifest['command'][-1]))!=digest:
                    raise ValueError('Build manifest/executed binary differs')
            reference=load(output/'manifests/reference.json')
            if reference['data_sha256']!=state['artifacts']['reference_sha256'] or \
                    sha256_file(local_path(plan['cache_directory'])/'reference'/state['artifacts']['reference_key']/'reference.bin')!=reference['data_sha256']:
                raise ValueError('Reference manifest/data identity differs')
            if not audit_gate(output/'setup_gate',protocol,'Formal',{
                'content_commit':plan['content_commit'],'session_id':plan['session_id'],'purpose':'setup'}):
                raise ValueError('Setup gate differs')
        partial=[r for r in records if r['run_id'] not in set(completed_ids)]
        complete=len(summaries)==20 and len(records)==120 and not partial and state['status']=='complete'
        clocks=audit_group_clock_inventory(plan,output)
        integrity=all(batch['audit']['evidence_integrity_pass'] for batch in clocks)
        all_clock_pass=all(batch['audit']['raw_reference_pass'] for batch in clocks)
        if complete and (len(clocks)!=40 or not all_clock_pass): raise ValueError('Complete Grid lacks exactly 40 passing group checks')
        result.update(evidence_integrity_pass=integrity,grid_complete=complete,
            grid_timing_checks_pass=complete and all_clock_pass,group_clock_batches=clocks,
            completed_configurations=len(summaries),valid_configuration_count=len(summaries),
            completed_group_executions=len(completed_ids),partial_or_unaccepted_executions=len(partial),
            abandoned_groups=len(state['abandoned_attempts']),configuration_summaries=summaries,
            content_commit=plan['content_commit'],session_id=plan['session_id'],
            measurement_protocol_hash=plan['measurement_protocol_hash'],timing_protocol_hash=plan['timing_protocol_hash'],
            lowest_median_observation=min(summaries,key=lambda x:x['median_raw_seconds']) if summaries else None,
            costs={'grid_group_evaluation_raw_seconds':sum(g['evaluation_wall_seconds'] for g in state['completed']),
                'all_completed_group_core_raw_seconds':sum(g['compute_total_seconds'] for g in state['completed']),
                'all_completed_group_validation_raw_seconds':sum(g['validation_total_seconds'] for g in state['completed']),
                'setup_raw_seconds':state.get('setup_seconds',0),
                'controller_envelope_qpc_seconds':load(output/'controller.json').get('total_qpc_seconds') if (output/'controller.json').exists() else None,
                'scope':'Core/validation/process/group costs are nested. Setup/resource/clock checks inside QPC envelope. Historical MONOTONIC metadata is not a trusted total. No sums across overlapping scopes.'},
            formal_grid_status='complete' if complete else 'partial_or_not_started',
            p3_status='Random/Greedy not executed in this session; full P3 comparison remains incomplete')
    except (ValueError,KeyError,TypeError,OSError,IndexError) as error: result['errors'].append(str(error))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True); args=parser.parse_args()
    answer=audit_grid(load(args.plan)); atomic_write_json(args.output,answer); print(json.dumps(answer))
    raise SystemExit(0 if answer['grid_complete'] and answer['evidence_integrity_pass'] else 2)
