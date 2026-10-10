"""Formal RAW admission: recompute original persistent-native/QPC evidence."""
from __future__ import annotations
import json,os,re
from pathlib import Path
from autotuner.core import sha256_file,sha256_json
from autotuner.session import source_identity
from autotuner.timing import FORMAL_RAW_VERSION,measurement_timing
from scripts.p3_clock_contract import load,wsl_path
from scripts.p3_fixed_work_clock import check_interval,integer

ROOT=Path(__file__).resolve().parents[1]


def local_path(value):
    value=str(value)
    if os.name=='nt' and re.match(r'^/mnt/[a-z]/',value):
        return Path(value[5].upper()+':'+value[6:].replace('/','\\'))
    if os.name=='nt' and value.startswith('/'):
        return Path('\\\\wsl.localhost\\Ubuntu-24.04'+value.replace('/','\\'))
    if os.name!='nt' and len(value)>2 and value[1]==':': return Path(wsl_path(value))
    return Path(value)


def raw_schedule(kind):
    if kind not in ('recovery','before','after'): raise ValueError('Unknown RAW clock purpose')
    rows=[]
    for number in range(1,11 if kind=='recovery' else 2):
        rows.append({'index':len(rows),'round':number,'condition':'LU','path':'libc',
                     'selected_cpu':-1,'updates':1_000_000_000,'long':False})
        if kind=='recovery' and number in (5,10):
            rows.append({'index':len(rows),'round':number,'condition':'LU-long','path':'libc',
                         'selected_cpu':-1,'updates':10_000_000_000,'long':True})
    return rows


def validate_manifest(manifest,root=ROOT):
    if manifest.get('schema')!='raw-grid-clock-manifest-v1' or \
            manifest.get('timing_version')!=FORMAL_RAW_VERSION:
        raise ValueError('Not a formal RAW manifest')
    protocol=load(Path(root)/'configs/measurement_protocol.json')
    timing=measurement_timing(protocol,root)
    context=manifest['context']
    if manifest['measurement_protocol_hash']!=sha256_json(protocol) or \
            manifest['timing_protocol_hash']!=sha256_json(timing) or \
            manifest['resource_policy_hash']!=protocol['resource_gate']['policy_hash'] or \
            not re.fullmatch('[0-9a-f]{40}',context['content_commit']) or \
            not re.fullmatch('[0-9a-f]{32}',context['session_id']):
        raise ValueError('RAW manifest protocol/content/session differs')
    purpose=manifest['purpose']; planned=raw_schedule(purpose)
    if manifest['schedule']!=planned or manifest['interval_count']!=len(planned) or \
            manifest['criteria']!=timing['admission'] or \
            manifest['collection_budget_seconds']!=(240 if purpose=='recovery' else 60):
        raise ValueError('RAW manifest criteria/schedule/budget differs')
    build=manifest['probe_build']
    if build['content_commit']!=context['content_commit'] or build['binary']!=manifest['probe_binary'] or \
            build['binary_sha256']!=manifest['binary_sha256'] or \
            build['source_sha256']!=manifest['source_sha256']['code/diagnostics/clock_fixed_work_probe.c'] or \
            build['compiler_sha256']!=sha256_file(local_path('/usr/bin/x86_64-linux-gnu-gcc-13')) or \
            build['compile_command']!=['/usr/bin/gcc','-std=c11','-O2','-Wall','-Wextra','-Werror',build['source_path'],'-o',build['binary']]:
        raise ValueError('Compiled probe/source binding differs')
    files=source_identity(Path(root),manifest['git_files'])
    required={'autotuner/raw_grid.py','autotuner/timing.py','scripts/start_raw_grid.py',
              'scripts/raw_clock_contract.py','scripts/run_fixed_work_clock.py',
              'scripts/p3_fixed_work_clock.py','code/diagnostics/clock_fixed_work_probe.c',
              'configs/raw_formal_timing_protocol.json','code/original/matrix_multiplication.c'}
    if not required<=files.keys() or manifest['source_sha256']!={p:v['executed_sha256'] for p,v in files.items()}:
        raise ValueError('RAW source closure or bytes differ')
    binary=local_path(manifest['probe_binary'])
    if sha256_file(binary)!=manifest['binary_sha256']:
        raise ValueError('RAW compiled probe identity differs')


def audit_clock(directory,expected_context=None):
    directory=local_path(directory)
    result={'evidence_integrity_pass':False,'clock_complete':False,'raw_reference_pass':False,
            'interval_count':0,'response_count':0,'checks':[],'errors':[]}
    try:
        manifest=load(directory/'manifest.json'); validate_manifest(manifest)
        if expected_context is not None and manifest['context']!=expected_context:
            raise ValueError('Clock batch is stale or belongs to another group/content/session')
        operation=load(directory/'native_process.json'); planned=raw_schedule(manifest['purpose'])
        if operation['schema']!='fixed-work-clock-process-v1' or \
                operation['manifest_sha256']!=sha256_file(directory/'manifest.json') or \
                operation['command']!=manifest['probe_command'] or \
                operation['collection_budget_seconds']!=manifest['collection_budget_seconds'] or \
                set(operation['stream_sha256'])!={'native.stdout.txt','native.stderr.txt','messages.jsonl','intervals.jsonl'}:
            raise ValueError('Clock process/manifest/command differs')
        for name,digest in operation['stream_sha256'].items():
            if sha256_file(directory/name)!=digest: raise ValueError('Clock stream changed: '+name)
        def lines(name):
            return [json.loads(line,parse_constant=lambda token: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
                    for line in (directory/name).read_bytes().splitlines() if line]
        messages=lines('messages.jsonl'); rows=lines('intervals.jsonl'); native=lines('native.stdout.txt')
        result.update(interval_count=len(rows),response_count=len(messages))
        if not messages or [record['response'] for record in messages]!=native:
            raise ValueError('Native/message stream differs or empty')
        hello=messages[0]['response']; pid=integer(hello['pid'],'PID')
        if hello!=operation['hello'] or hello['op']!='HELLO' or hello['seq']!=0 or \
                hello['allowed_cpus']!=manifest['cpu_selection']['allowed_cpus']:
            raise ValueError('HELLO/allowed CPU differs')
        frequency=integer(operation['qpc_frequency'],'QPC frequency')
        previous=integer(operation['qpc_start'],'QPC start'); prior_raw=None
        for sequence,record in enumerate(messages):
            ep=record['response']; send=integer(record['send_qpc'],'send'); recv=integer(record['recv_qpc'],'recv')
            if not previous<=send<=recv or type(ep['seq']) is not int or ep['seq']!=sequence or \
                    type(ep['pid']) is not int or ep['pid']!=pid or ep['schema']!='fixed-work-clock-endpoint-v1':
                raise ValueError('Message sequence/PID/QPC differs')
            previous=recv
            if ep['op']=='READ':
                if prior_raw is not None and integer(ep['raw1_ns'],'RAW1')<prior_raw:
                    raise ValueError('Global RAW rollback')
                prior_raw=integer(ep['raw2_ns'],'RAW2')
        end=integer(operation['qpc_end'],'QPC end')
        if end<previous or operation['qpc_seconds']!=(end-operation['qpc_start'])/frequency or \
                (end-integer(operation['collection_start_qpc'],'collection start'))/frequency>manifest['collection_budget_seconds']:
            raise ValueError('Clock process timing/budget differs')
        for index,row in enumerate(rows):
            if index>=len(planned): raise ValueError('Extra clock interval')
            pointer=index*4+1; mode=messages[pointer]; plan=planned[index]
            if mode['command']!=f'MODE {pointer} libc -1\n' or mode['response']['op']!='MODE' or \
                    mode['response']['path']!='libc' or mode['response']['selected_cpu']!=-1 or \
                    [row['start'],row['work'],row['end']]!=messages[pointer+1:pointer+4]:
                raise ValueError('MODE or original interval binding differs')
            checked=check_interval(row,frequency,plan,pid,pointer+1,hello['allowed_cpus'])
            if checked!=row['check']: raise ValueError('Saved PASS contradicts raw recomputation')
            result['checks'].append({'index':index,**checked})
        integrity=all(check['evidence_integrity_pass'] for check in result['checks'])
        complete=len(rows)==len(planned) and len(messages)==len(planned)*4+2 and \
            type(operation['returncode']) is int and operation['returncode']==0 and not operation['errors']
        if complete and (messages[-1]['command']!=f'QUIT {len(messages)-1}\n' or messages[-1]['response']['op']!='QUIT'):
            raise ValueError('QUIT differs')
        result.update(evidence_integrity_pass=integrity,clock_complete=complete,
            raw_reference_pass=integrity and complete and all(check['raw_pass'] for check in result['checks']),
            raw_failure_indices=[c['index'] for c in result['checks'] if not c['raw_pass']],
            monotonic_warning_indices=[c['index'] for c in result['checks'] if not c.get('within_host_with_allowance',{}).get('monotonic')],
            manifest_sha256=sha256_file(directory/'manifest.json'),native_elapsed_qpc_seconds=operation['qpc_seconds'])
        if not complete: result['errors'].append('Incomplete RAW check; no replacement or retry')
    except (ValueError,KeyError,TypeError,OSError,IndexError) as error:
        result['errors'].append(str(error))
    return result


def checked_operation(directory,name):
    """Original closed operation streams, integer QPC duration and reliable exit."""
    directory=local_path(directory); record=load(directory/(name+'.operation.json'))
    for stream in ('stdout','stderr'):
        if sha256_file(directory/record[stream+'_path'])!=record[stream+'_sha256']:
            raise ValueError('Operation stream changed')
    for field in ('qpc_start','qpc_end','qpc_frequency'): integer(record[field],field)
    if record['qpc_end']<record['qpc_start'] or record['qpc_seconds']!=(record['qpc_end']-record['qpc_start'])/record['qpc_frequency']:
        raise ValueError('Operation QPC duration differs')
    return record


def audit_gate(directory,protocol,purpose,context):
    from autotuner.resources import valid_gate
    directory=local_path(directory); manifest=load(directory/'gate_manifest.json')
    if manifest['schema']!='raw-grid-resource-batch-v1' or manifest['purpose']!=purpose or \
            manifest['context']!=context or manifest['policy_hash']!=protocol['resource_gate']['policy_hash']:
        raise ValueError('Resource purpose/policy/group binding differs')
    if purpose=='Formal' and manifest['budget_seconds']!=120: raise ValueError('Formal gate budget differs')
    outcome=load(directory/'gate_outcome.json'); records=[]
    for name in outcome['operations']:
        op=checked_operation(directory,name)
        if op['command']!=manifest['command']: raise ValueError('Resource command differs')
        parsed=load(directory/op['stdout_path'])
        records.append((op,valid_gate(parsed,protocol,purpose)))
    start=integer(outcome['qpc_start'],'gate start'); end=integer(outcome['qpc_end'],'gate end')
    frequency=integer(outcome['qpc_frequency'],'gate frequency')
    if not records or end<start or outcome['qpc_seconds']!=(end-start)/frequency or \
            outcome['qpc_seconds']>manifest['budget_seconds'] or \
            any(not start<=op['qpc_start']<=op['qpc_end']<=end for op,_ in records):
        raise ValueError('Resource window/count/budget differs')
    passed=records[-1][0]['returncode']==0 and not records[-1][0]['timed_out'] and records[-1][1]
    if type(outcome.get('admitted')) is not bool or outcome['admitted']!=passed:
        raise ValueError('Saved resource decision differs from recomputation')
    return passed


def audit_recovery(directory,plan,initial_checkpoint):
    from autotuner.resources import valid_gate
    directory=local_path(directory); manifest=load(directory/'manifest.json')
    expected={'content_commit':plan['content_commit'],'session_id':plan['session_id'],
              'initial_checkpoint_sha256':sha256_file(local_path(initial_checkpoint))}
    result=audit_clock(directory,expected)
    protocol=load(ROOT/'configs/measurement_protocol.json')
    try:
        gate=checked_operation(directory,'resources'); parsed=load(directory/gate['stdout_path'])
        if gate['command']!=manifest['resource_command'] or gate['returncode']!=0 or gate['timed_out'] or \
                not valid_gate(parsed,protocol,'Recovery'):
            raise ValueError('Recovery resource gate failed or mismatched')
        envelope=load(directory/'recovery_operation.json')
        frequency=integer(envelope['qpc_frequency'],'recovery QPC frequency')
        start=integer(envelope['qpc_start'],'recovery start'); end=integer(envelope['qpc_end'],'recovery end')
        if not start<=gate['qpc_start']<=gate['qpc_end']<=end or end<start or \
                envelope['qpc_seconds']!=(end-start)/frequency or envelope['qpc_seconds']>240:
            raise ValueError('Recovery 240s resource+collection budget exceeded or invalid')
        result['recovery_resource_pass']=True
    except (ValueError,KeyError,TypeError,OSError) as error:
        result['errors'].append(str(error)); result['recovery_resource_pass']=False
    result['recovery_eligible']=result['evidence_integrity_pass'] and result['raw_reference_pass'] and result['recovery_resource_pass'] and not result['errors']
    return result


def require_certificate(directory,plan,initial_checkpoint):
    directory=local_path(directory); certificate=load(directory/'certificate.json')
    recomputed=audit_recovery(directory,plan,initial_checkpoint)
    expected={'schema':'raw-grid-recovery-certificate-v1','content_commit':plan['content_commit'],
        'session_id':plan['session_id'],'timing_protocol_hash':plan['timing_protocol_hash'],
        'measurement_protocol_hash':plan['measurement_protocol_hash'],
        'initial_checkpoint_sha256':sha256_file(local_path(initial_checkpoint)),
        'manifest_sha256':sha256_file(directory/'manifest.json'),'audit':recomputed}
    if certificate!=expected or recomputed['recovery_eligible'] is not True:
        raise ValueError('Missing/old/foreign/invalid RAW recovery certificate')
    return recomputed


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--plan',type=Path); parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=audit_recovery(args.directory,load(args.plan),local_path(load(args.plan)['session_directory'])/'initial_checkpoint.json') if args.plan else audit_clock(args.directory)
    from scripts.p3_clock_contract import atomic_write_json
    atomic_write_json(args.output,result); print(json.dumps(result)); raise SystemExit(0 if result.get('recovery_eligible',result['raw_reference_pass']) else 2)
