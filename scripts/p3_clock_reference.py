"""Proposed diagnostic standard, NOT an official physical accuracy guarantee."""
from __future__ import annotations

CONDITIONS = [
    {"name":"A","path":"libc","affinity":"unbound","workload":"idle","count":10},
    {"name":"B","path":"libc","affinity":"unbound","workload":"busy","count":10},
    {"name":"C","path":"syscall","affinity":"unbound","workload":"idle","count":5},
    {"name":"D","path":"libc","affinity":"first_allowed","workload":"idle","count":5}]
CRITERIA = {"version":"qpc-bounded-reference-diagnostic-v1", "maximum_uncertainty_ns":20_000_000,
    "absolute_allowance_ns":5_000_000,"relative_allowance_percent":1,
    "maximum_read_span_ns":20_000_000,
    "scope":"Current cross-domain duration consistency only; not absolute physical clock certification"}
SOURCE_FILES = ('code/diagnostics/clock_reference_probe.c','scripts/run_clock_reference.py',
    'scripts/p3_clock_reference.py','scripts/collect_clock_reference_environment.py','tests/test_clock_reference.py',
    'configs/resource_policy.json','code/working/matrix_multiplication.c','code/working/reference_generator.c',
    'code/working/matrix_input.h','autotuner/core.py','autotuner/measurement.py','autotuner/search.py')


def integer(value, label, positive=True):
    if type(value) is not int or not (0 < value <= 2**63-1 if positive else 0 <= value <= 2**63-1):
        raise ValueError("Invalid integer: "+label)
    return value


def check_interval(row, frequency, condition, pid, first_sequence, allowed_cpus):
    """Subtract integers first; test inequalities by integer cross-multiplication."""
    try:
        integer(frequency,'frequency')
        integer(pid,'pid'); integer(first_sequence,'sequence')
        if not isinstance(allowed_cpus,list) or not allowed_cpus or \
                any(type(cpu) is not int or cpu<0 for cpu in allowed_cpus) or sorted(set(allowed_cpus))!=allowed_cpus:
            raise ValueError('Invalid allowed CPUs')
        if row['condition']!=condition['name'] or row['schema']!='qpc-bounded-clock-interval-v1':
            raise ValueError('Wrong condition/schema')
        reads=[row['start'],row['end']]
        for index, read in enumerate(reads):
            if read['command']!=f'READ {first_sequence+index*2}\n':
                raise ValueError('Unexpected request sequence')
            send, recv=integer(read['send_qpc'],'send'),integer(read['recv_qpc'],'recv')
            if recv<send: raise ValueError('Host boundary backwards')
            endpoint=read['response']
            if endpoint['schema']!='native-clock-endpoint-v1' or endpoint['op']!='READ' or \
                    type(endpoint['pid']) is not int or endpoint['pid']!=pid or \
                    type(endpoint['seq']) is not int or endpoint['seq']!=first_sequence+index*2 or \
                    endpoint['path']!=condition['path'] or type(endpoint['selected_cpu']) is not int or \
                    endpoint['selected_cpu']!=row['selected_cpu']:
                raise ValueError('Endpoint schema/PID/sequence/path/affinity differs')
            for field in ('m1_ns','raw_ns','m2_ns','realtime_ns','boottime_ns'):
                integer(endpoint[field],field)
            if endpoint['m2_ns']<endpoint['m1_ns']: raise ValueError('MONOTONIC read backwards')
            for field in ('cpu_before','cpu_after'):
                if type(endpoint[field]) is not int or endpoint[field] not in allowed_cpus:
                    raise ValueError('Invalid CPU number')
                if row['selected_cpu']!=-1 and endpoint[field]!=row['selected_cpu']:
                    raise ValueError('Pinned CPU differs')
        expected_cpu=allowed_cpus[0] if condition['affinity']=='first_allowed' else -1
        if type(row['selected_cpu']) is not int or row['selected_cpu']!=expected_cpu:
            raise ValueError('Affinity condition differs')
        waited=row['wait']; ack=waited['response']
        if waited['command']!=f"WAIT {first_sequence+1} {condition['workload']}\n" or \
                ack['schema']!='native-clock-endpoint-v1' or ack['op']!='WAIT' or \
                type(ack['pid']) is not int or ack['pid']!=pid or type(ack['seq']) is not int or \
                ack['seq']!=first_sequence+1 or ack['path']!=condition['path'] or \
                type(ack['selected_cpu']) is not int or ack['selected_cpu']!=expected_cpu or \
                ack['workload']!=condition['workload'] or type(ack['work_checksum']) is not int or \
                not 0<=ack['work_checksum']<2**64:
            raise ValueError('WAIT identity/sequence/workload differs')
        if not reads[0]['recv_qpc']<=integer(waited['send_qpc'],'wait_send')<= \
                integer(waited['recv_qpc'],'wait_recv')<=reads[1]['send_qpc']:
            raise ValueError('Request/response order differs')
        s,e=[item['response'] for item in reads]
        low=reads[1]['send_qpc']-reads[0]['recv_qpc']
        high=reads[1]['recv_qpc']-reads[0]['send_qpc']
        if low<=0 or high<low: raise ValueError('Host interval order differs')
        durations={'monotonic_low_ns':e['m1_ns']-s['m2_ns'],
                   'monotonic_high_ns':e['m2_ns']-s['m1_ns'],
                   **{clock+'_ns':e[clock+'_ns']-s[clock+'_ns'] for clock in ('raw','realtime','boottime')}}
        if any(value<=0 for value in durations.values()): raise ValueError('Guest duration backwards/nonpositive')
        spans=[endpoint['m2_ns']-endpoint['m1_ns'] for endpoint in (s,e)]
        uncertainty_ok=(high-low)*1_000_000_000<=CRITERIA['maximum_uncertainty_ns']*frequency
        span_ok=max(spans)<=CRITERIA['maximum_read_span_ns']
        # Scale by 100*Frequency to avoid floating endpoints or allowance rounding.
        lower=low*100*1_000_000_000-CRITERIA['absolute_allowance_ns']*100*frequency-high*1_000_000_000
        upper=high*100*1_000_000_000+CRITERIA['absolute_allowance_ns']*100*frequency+high*1_000_000_000
        matched={key:lower<=value*100*frequency<=upper for key,value in durations.items()}
        mono=matched['monotonic_low_ns'] and matched['monotonic_high_ns']
        result={'evidence_integrity_pass':True,'reference_determinate':uncertainty_ok and span_ok,
            'reference_match_pass':uncertainty_ok and span_ok and mono,
            'monotonic_within_host':mono,'raw_within_host':matched['raw_ns'],
            'realtime_within_host':matched['realtime_ns'],'boottime_within_host':matched['boottime_ns'],
            'host_lower_qpc_ticks':low,'host_upper_qpc_ticks':high,'host_lower_seconds':low/frequency,
            'host_upper_seconds':high/frequency,'uncertainty_seconds':(high-low)/frequency,
            'allowance_seconds':0.005+0.01*high/frequency,'guest_durations_ns':durations,
            'read_spans_ns':spans,'warnings':[],'errors':[]}
        if not uncertainty_ok: result['warnings'].append('host_boundary_too_wide_indeterminate')
        if not span_ok: result['warnings'].append('guest_read_span_too_wide_indeterminate')
        if not matched['raw_ns']: result['warnings'].append('RAW_host_mismatch_diagnostic_only')
        return result
    except (KeyError,TypeError,ValueError,OverflowError) as error:
        return {'evidence_integrity_pass':False,'reference_determinate':False,'reference_match_pass':False,
                'errors':[str(error)],'warnings':[]}


def audit_diagnostic(directory):
    """Recompute all 30 intervals from original messages, not their saved PASS flags."""
    import json
    from pathlib import Path
    import subprocess
    from autotuner.core import sha256_file,sha256_json
    from scripts.p3_clock_contract import load
    directory=Path(directory)
    answer={'evidence_integrity_pass':False,'diagnostic_complete':False,'default_reference_match_pass':False,
        'diagnostic_certifiable':False,'interval_count':0,'checks':[],'errors':[]}
    try:
        manifest=load(directory/'manifest.json'); operation=load(directory/'native_process.json')
        if manifest['schema']!='clock-reference-diagnostic-manifest-v1' or manifest['conditions']!=CONDITIONS or \
                manifest['criteria']!=CRITERIA or manifest['criteria_hash']!=sha256_json(CRITERIA) or \
                manifest['interval_count']!=30 or manifest['collection_budget_seconds']!=480:
            raise ValueError('Manifest criteria/count/budget differs')
        root=Path(__file__).resolve().parents[1]
        if set(manifest['source_sha256'])!=set(SOURCE_FILES): raise ValueError('Missing/unexpected source identity')
        for path,digest in manifest['source_sha256'].items():
            original=subprocess.check_output(['git','show',manifest['source_commit']+':'+path],cwd=root)
            import hashlib
            normalized=original.replace(b'\r\n',b'\n')
            if digest not in {hashlib.sha256(data).hexdigest() for data in
                             (original,normalized,normalized.replace(b'\n',b'\r\n'))}:
                raise ValueError('Diagnostic source/Git/raw identity differs: '+path)
        if operation['schema']!='clock-reference-process-v1' or operation['command']!=manifest['probe_command'] or \
                operation['manifest_sha256']!=sha256_file(directory/'manifest.json'):
            raise ValueError('Native process/manifest differs')
        if set(operation['stream_sha256'])!={'native.stdout.txt','native.stderr.txt','messages.jsonl','intervals.jsonl'}:
            raise ValueError('Missing raw stream identity')
        for name,digest in operation['stream_sha256'].items():
            if sha256_file(directory/name)!=digest: raise ValueError('Raw stream hash differs: '+name)
        def lines(name):
            return [json.loads(line,parse_constant=lambda token: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
                    for line in (directory/name).read_bytes().splitlines() if line]
        messages=lines('messages.jsonl'); rows=lines('intervals.jsonl'); native=lines('native.stdout.txt')
        answer['interval_count']=len(rows)
        if [item['response'] for item in messages]!=native: raise ValueError('Messages differ from native raw stream')
        hello=messages[0]['response']; pid=integer(hello['pid'],'native PID')
        if hello['op']!='HELLO' or type(hello['seq']) is not int or hello['seq']!=0 or hello!=operation['hello']:
            raise ValueError('Native hello differs')
        frequency=integer(operation['qpc_frequency'],'frequency')
        previous=integer(operation['qpc_start'],'qpc_start')
        prior_read=None
        for sequence,record in enumerate(messages):
            endpoint=record['response']
            send,recv=integer(record['send_qpc'],'send'),integer(record['recv_qpc'],'recv')
            if not previous<=send<=recv or type(endpoint['seq']) is not int or endpoint['seq']!=sequence or \
                    type(endpoint['pid']) is not int or endpoint['pid']!=pid:
                raise ValueError('Global message order/PID/sequence differs')
            previous=recv
            if endpoint.get('op')=='READ':
                if prior_read is not None and (endpoint['m1_ns']<prior_read['m2_ns'] or any(
                        endpoint[key]<prior_read[key] for key in ('raw_ns','realtime_ns','boottime_ns'))):
                    raise ValueError('Guest clock backwards across messages')
                prior_read=endpoint
        end=integer(operation['qpc_end'],'qpc_end')
        if end<previous or operation['qpc_seconds']!=(end-operation['qpc_start'])/frequency:
            raise ValueError('Process end precedes last response or saved elapsed differs')
        if (end-integer(operation['collection_start_qpc'],'collection_start'))/frequency>480:
            raise ValueError('Collection exceeded 480-second budget')
        if len(rows)!=30 or len(messages)!=96: raise ValueError('Incomplete fixed 30-interval diagnostic')
        pointer=1; row_index=0
        for condition in CONDITIONS:
            mode=messages[pointer]; selected=hello['allowed_cpus'][0] if condition['affinity']=='first_allowed' else -1
            if mode['command']!=f"MODE {pointer} {condition['path']} {selected}\n" or \
                    mode['response']['op']!='MODE' or mode['response']['path']!=condition['path'] or \
                    mode['response']['selected_cpu']!=selected:
                raise ValueError('Condition MODE differs')
            pointer+=1
            for index in range(condition['count']):
                row=rows[row_index]
                if type(row['index']) is not int or row['index']!=index or row['qpc_frequency']!=frequency or \
                        [row['start'],row['wait'],row['end']]!=messages[pointer:pointer+3]:
                    raise ValueError('Interval does not match original messages/order')
                checked=check_interval(row,frequency,condition,pid,pointer,hello['allowed_cpus'])
                if row['check']!=checked: raise ValueError('Saved check contradicts original endpoints')
                answer['checks'].append({'condition':condition['name'],'index':index,**checked})
                pointer+=3; row_index+=1
        if messages[pointer]['command']!=f'QUIT {pointer}\n' or messages[pointer]['response']['op']!='QUIT':
            raise ValueError('Final QUIT differs')
        integrity=all(item['evidence_integrity_pass'] for item in answer['checks'])
        complete=type(operation['returncode']) is int and operation['returncode']==0 and not operation['errors']
        default=answer['checks'][:20]
        answer.update(evidence_integrity_pass=integrity,diagnostic_complete=complete,
            default_reference_match_pass=all(item['reference_match_pass'] for item in default),
            diagnostic_certifiable=integrity and complete and all(item['reference_determinate'] for item in answer['checks'])
                and all(item['reference_match_pass'] for item in default),
            default_raw_host_mismatch_count=sum(not item.get('raw_within_host',False) for item in default),
            all_raw_host_mismatch_count=sum(not item.get('raw_within_host',False) for item in answer['checks']),
            indeterminate_count=sum(not item['reference_determinate'] for item in answer['checks']),
            native_pid=pid,host_wsl_pid=operation['pid'],native_elapsed_qpc_seconds=operation['qpc_seconds'],
            physical_clock_accuracy='unknown',manifest_sha256=sha256_file(directory/'manifest.json'))
    except (KeyError,TypeError,ValueError,OSError,IndexError,subprocess.CalledProcessError) as error:
        answer['errors'].append(str(error))
    return answer
