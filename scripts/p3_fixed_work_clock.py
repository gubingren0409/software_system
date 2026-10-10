"""Fixed-work RAW candidate diagnostic; integer-only QPC boundary decisions."""
from __future__ import annotations

CRITERIA = {"version":"fixed-work-raw-qpc-diagnostic-v1", "maximum_uncertainty_ns":20_000_000,
    "maximum_read_span_ns":20_000_000,"absolute_allowance_ns":5_000_000,
    "relative_allowance_percent":1,"collection_budget_seconds":480,
    "scope":"Cross-domain consistency under these conditions only; not physical accuracy or a recovery certificate"}
SOURCE_FILES = ('code/diagnostics/clock_fixed_work_probe.c','scripts/p3_fixed_work_clock.py',
    'scripts/run_fixed_work_clock.py','scripts/collect_clock_reference_environment.py',
    'scripts/p3_clock_contract.py','tests/test_fixed_work_clock.py','configs/resource_policy.json',
    'code/working/matrix_multiplication.c','code/working/reference_generator.c','code/working/matrix_input.h',
    'autotuner/core.py','autotuner/measurement.py','autotuner/search.py',
    'autotuner/__init__.py','docs/P3_RAW_CLOCK_CANDIDATE.md',
    'evidence/p3_raw_candidate/20261010-234702-fixed-work/prepare.py')


def schedule(cpu):
    if type(cpu) is not int or cpu<0: raise ValueError('Invalid preselected CPU')
    conditions=[('LU','libc',-1),('SU','syscall',-1),('LP','libc',cpu),('SP','syscall',cpu)]
    rows=[]
    for round_number in range(1,6):
        for name,path,selected in conditions if round_number%2 else reversed(conditions):
            rows.append({'index':len(rows),'round':round_number,'condition':name,'path':path,
                         'selected_cpu':selected,'updates':1_000_000_000,'long':False})
        if round_number in (2,5):
            rows.append({'index':len(rows),'round':round_number,'condition':'LU-long','path':'libc',
                         'selected_cpu':-1,'updates':10_000_000_000,'long':True})
    return rows


def integer(value,label,positive=True):
    if type(value) is not int or not (0<value<=2**63-1 if positive else 0<=value<=2**63-1):
        raise ValueError('Invalid integer: '+label)
    return value


def check_interval(row,frequency,planned,pid,first_sequence,allowed_cpus):
    try:
        integer(frequency,'frequency'); integer(pid,'pid'); integer(first_sequence,'sequence')
        if not isinstance(allowed_cpus,list) or not allowed_cpus or \
                any(type(cpu) is not int or cpu<0 for cpu in allowed_cpus) or sorted(set(allowed_cpus))!=allowed_cpus:
            raise ValueError('Invalid allowed CPUs')
        if row['schema']!='fixed-work-clock-interval-v1' or row['planned']!=planned or \
                type(row['qpc_frequency']) is not int or row['qpc_frequency']!=frequency:
            raise ValueError('Interval schedule/schema/frequency differs')
        selected=planned['selected_cpu']
        if selected!=-1 and selected not in allowed_cpus: raise ValueError('Pinned CPU not allowed')
        reads=[row['start'],row['end']]
        for index,read in enumerate(reads):
            seq=first_sequence+index*2
            send,recv=integer(read['send_qpc'],'send'),integer(read['recv_qpc'],'recv')
            endpoint=read['response']
            if recv<send or read['command']!=f'READ {seq}\n': raise ValueError('Host boundary/request differs')
            if endpoint['schema']!='fixed-work-clock-endpoint-v1' or endpoint['op']!='READ' or \
                    type(endpoint['pid']) is not int or endpoint['pid']!=pid or \
                    type(endpoint['seq']) is not int or endpoint['seq']!=seq or endpoint['path']!=planned['path'] or \
                    type(endpoint['selected_cpu']) is not int or endpoint['selected_cpu']!=selected:
                raise ValueError('Endpoint identity differs')
            for field in ('m1_ns','raw1_ns','monotonic_ns','raw2_ns','m2_ns','realtime_ns','boottime_ns'):
                integer(endpoint[field],field)
            for field in ('cpu_before','cpu_after'):
                if type(endpoint[field]) is not int or endpoint[field] not in allowed_cpus or \
                        (selected!=-1 and endpoint[field]!=selected): raise ValueError('CPU differs')
            # Metadata availability is not a timing gate. modes must always be read-only.
            if type(endpoint['adjtimex']['modes']) is not int or endpoint['adjtimex']['modes']!=0:
                raise ValueError('adjtimex is not read-only')
            for field in ('boot_id','uptime','clocksource'):
                if not isinstance(endpoint[field],str) or not endpoint[field]: raise ValueError('Missing metadata marker')
        work=row['work']; ack=work['response']; seq=first_sequence+1
        if work['command']!=f"WORK {seq} {planned['updates']}\n" or \
                ack['schema']!='fixed-work-clock-endpoint-v1' or ack['op']!='WORK' or \
                type(ack['pid']) is not int or ack['pid']!=pid or type(ack['seq']) is not int or ack['seq']!=seq or \
                ack['path']!=planned['path'] or type(ack['selected_cpu']) is not int or ack['selected_cpu']!=selected or \
                type(ack['executed_updates']) is not int or ack['executed_updates']!=planned['updates'] or \
                type(ack['work_checksum']) is not int or not 0<=ack['work_checksum']<2**64:
            raise ValueError('Fixed WORK identity/count differs')
        if not reads[0]['recv_qpc']<=integer(work['send_qpc'],'work send')<= \
                integer(work['recv_qpc'],'work recv')<=reads[1]['send_qpc']:
            raise ValueError('Message order differs')
        s,e=[read['response'] for read in reads]
        low=reads[1]['send_qpc']-reads[0]['recv_qpc']
        high=reads[1]['recv_qpc']-reads[0]['send_qpc']
        if low<=0 or high<low: raise ValueError('Nonpositive/backward host duration')
        ranges={'raw':[e['raw1_ns']-s['raw2_ns'],e['raw2_ns']-s['raw1_ns']],
                'monotonic':[e['m1_ns']-s['m2_ns'],e['m2_ns']-s['m1_ns']],
                'realtime':[e['realtime_ns']-s['realtime_ns']]*2,
                'boottime':[e['boottime_ns']-s['boottime_ns']]*2}
        spans={'raw':[p['raw2_ns']-p['raw1_ns'] for p in (s,e)],
               'monotonic':[p['m2_ns']-p['m1_ns'] for p in (s,e)]}
        if any(value<0 for value in spans['raw']) or ranges['raw'][0]<=0:
            raise ValueError('RAW rollback/nonpositive duration')
        uncertainty_ok=(high-low)*1_000_000_000<=20_000_000*frequency
        raw_span_ok=max(spans['raw'])<=20_000_000
        mono_span_ok=all(0<=span<=20_000_000 for span in spans['monotonic'])
        lower=low*100*1_000_000_000-5_000_000*100*frequency-high*1_000_000_000
        upper=high*100*1_000_000_000+5_000_000*100*frequency+high*1_000_000_000
        match={key:values[0]>0 and values[0]<=values[1] and
               lower<=values[0]*100*frequency and values[1]*100*frequency<=upper for key,values in ranges.items()}
        unpadded={key:values[0]>0 and low*1_000_000_000<=values[0]*frequency and
                  values[1]*frequency<=high*1_000_000_000 for key,values in ranges.items()}
        determinate=uncertainty_ok and raw_span_ok
        warnings=[]
        if not uncertainty_ok: warnings.append('host_boundary_too_wide_indeterminate')
        if not raw_span_ok: warnings.append('RAW_read_span_too_wide_indeterminate')
        if not match['monotonic'] or not mono_span_ok: warnings.append('MONOTONIC_mismatch_or_read_span')
        for clock in ('realtime','boottime'):
            if not match[clock]: warnings.append(clock+'_mismatch')
        return {'evidence_integrity_pass':True,'reference_determinate':determinate,
            'raw_pass':determinate and match['raw'],'within_host_with_allowance':match,
            'within_host_unpadded':unpadded,'monotonic_read_span_pass':mono_span_ok,
            'host_lower_qpc_ticks':low,'host_upper_qpc_ticks':high,
            'host_lower_seconds':low/frequency,'host_upper_seconds':high/frequency,
            'uncertainty_seconds':(high-low)/frequency,'allowance_seconds':0.005+0.01*high/frequency,
            'guest_ranges_ns':ranges,'read_spans_ns':spans,'warnings':warnings,'errors':[]}
    except (KeyError,TypeError,ValueError,OverflowError) as error:
        return {'evidence_integrity_pass':False,'reference_determinate':False,'raw_pass':False,
                'warnings':[],'errors':[str(error)]}


def audit_diagnostic(directory):
    """Independent recomputation binds Git source, actual bytes, raw stream and schedule."""
    import hashlib,json,subprocess
    from pathlib import Path
    from autotuner.core import sha256_file,sha256_json
    from scripts.p3_clock_contract import load
    directory=Path(directory); root=Path(__file__).resolve().parents[1]
    answer={'evidence_integrity_pass':False,'diagnostic_complete':False,'raw_candidate_eligible':False,
            'interval_count':0,'response_count':0,'checks':[],'errors':[]}
    try:
        manifest=load(directory/'manifest.json'); op=load(directory/'native_process.json')
        selected=manifest['cpu_selection']['selected_cpu']; planned=schedule(selected)
        if manifest['schema']!='fixed-work-clock-manifest-v1' or manifest['schedule']!=planned or \
                manifest['criteria']!=CRITERIA or manifest['criteria_hash']!=sha256_json(CRITERIA) or \
                manifest['interval_count']!=22 or manifest['collection_budget_seconds']!=480:
            raise ValueError('Manifest plan/criteria/count/budget differs')
        if manifest['cpu_selection_sha256']!=sha256_file(directory/'cpu_selection.json') or \
                manifest['cpu_selection']!=load(directory/'cpu_selection.json'):
            raise ValueError('Preselected CPU differs')
        if set(manifest['source_sha256'])!=set(SOURCE_FILES): raise ValueError('Source closure differs')
        for path,digest in manifest['source_sha256'].items():
            blob=subprocess.check_output(['git','show',manifest['source_commit']+':'+path],cwd=root)
            lf=blob.replace(b'\r\n',b'\n')
            if digest not in {hashlib.sha256(data).hexdigest() for data in (blob,lf,lf.replace(b'\n',b'\r\n'))}:
                raise ValueError('Git/source identity differs: '+path)
        if op['schema']!='fixed-work-clock-process-v1' or op['manifest_sha256']!=sha256_file(directory/'manifest.json') or \
                op['command']!=manifest['probe_command'] or set(op['stream_sha256'])!=\
                {'native.stdout.txt','native.stderr.txt','messages.jsonl','intervals.jsonl'}:
            raise ValueError('Operation/source identity differs')
        for name,digest in op['stream_sha256'].items():
            if sha256_file(directory/name)!=digest: raise ValueError('Raw stream differs: '+name)
        def lines(name):
            return [json.loads(line,parse_constant=lambda token: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
                    for line in (directory/name).read_bytes().splitlines() if line]
        messages=lines('messages.jsonl'); rows=lines('intervals.jsonl'); native=lines('native.stdout.txt')
        answer.update(interval_count=len(rows),response_count=len(messages))
        if [item['response'] for item in messages]!=native: raise ValueError('Native/message stream differs')
        hello=messages[0]['response']; pid=integer(hello['pid'],'native PID')
        if hello['op']!='HELLO' or type(hello['seq']) is not int or hello['seq']!=0 or hello!=op['hello'] or \
                hello['allowed_cpus']!=manifest['cpu_selection']['allowed_cpus']:
            raise ValueError('Hello/affinity differs')
        frequency=integer(op['qpc_frequency'],'frequency'); previous=integer(op['qpc_start'],'start')
        prior_raw=None
        for sequence,record in enumerate(messages):
            ep=record['response']; send=integer(record['send_qpc'],'send'); recv=integer(record['recv_qpc'],'recv')
            if not previous<=send<=recv or type(ep['seq']) is not int or ep['seq']!=sequence or \
                    type(ep['pid']) is not int or ep['pid']!=pid or ep['schema']!='fixed-work-clock-endpoint-v1':
                raise ValueError('Global sequence/PID/QPC/schema differs')
            previous=recv
            if ep['op']=='READ':
                if prior_raw is not None and integer(ep['raw1_ns'],'RAW1')<prior_raw:
                    raise ValueError('Global RAW rollback')
                prior_raw=integer(ep['raw2_ns'],'RAW2')
        end=integer(op['qpc_end'],'end')
        if end<previous or op['qpc_seconds']!=(end-op['qpc_start'])/frequency or \
                (end-integer(op['collection_start_qpc'],'collection start'))/frequency>480:
            raise ValueError('Process interval/budget differs')
        # Preserve and recompute partial rows too; incompleteness never becomes eligible.
        for index,row in enumerate(rows):
            if index>=22: raise ValueError('Unexpected additional interval')
            pointer=4*index+1; mode=messages[pointer]; plan=planned[index]
            if mode['command']!=f"MODE {pointer} {plan['path']} {plan['selected_cpu']}\n" or \
                    mode['response']['op']!='MODE' or mode['response']['path']!=plan['path'] or \
                    mode['response']['selected_cpu']!=plan['selected_cpu']:
                raise ValueError('MODE differs')
            if [row['start'],row['work'],row['end']]!=messages[pointer+1:pointer+4]:
                raise ValueError('Interval differs from original messages')
            checked=check_interval(row,frequency,plan,pid,pointer+1,hello['allowed_cpus'])
            if row['check']!=checked: raise ValueError('Saved check contradicts raw endpoint recomputation')
            answer['checks'].append({'index':index,'condition':plan['condition'],**checked})
        integrity=all(item['evidence_integrity_pass'] for item in answer['checks'])
        complete=len(rows)==22 and len(messages)==90 and type(op['returncode']) is int and op['returncode']==0 and not op['errors']
        if complete and (messages[-1]['command']!='QUIT 89\n' or messages[-1]['response']['op']!='QUIT'):
            raise ValueError('QUIT differs')
        answer.update(evidence_integrity_pass=integrity,diagnostic_complete=complete,
            raw_candidate_eligible=integrity and complete and all(item['raw_pass'] for item in answer['checks']),
            raw_failure_indices=[i['index'] for i in answer['checks'] if not i['raw_pass']],
            raw_unpadded_failure_indices=[i['index'] for i in answer['checks'] if not i.get('within_host_unpadded',{}).get('raw',False)],
            monotonic_failure_indices=[i['index'] for i in answer['checks'] if not i.get('within_host_with_allowance',{}).get('monotonic',False)
                                       or not i.get('monotonic_read_span_pass',False)],
            indeterminate_indices=[i['index'] for i in answer['checks'] if not i['reference_determinate']],
            native_elapsed_qpc_seconds=op['qpc_seconds'],manifest_sha256=sha256_file(directory/'manifest.json'),
            physical_accuracy='unknown',execution_complete=False,timing_checks_pass=False,comparison_ready=False)
        if not complete: answer['errors'].append('Incomplete/aborted fixed round; no candidate permitted')
    except (KeyError,TypeError,ValueError,OSError,IndexError,subprocess.CalledProcessError) as error:
        answer['errors'].append(str(error))
    return answer


if __name__=='__main__':
    import argparse,json
    from pathlib import Path
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args(); result=audit_diagnostic(args.directory)
    if args.output:
        from scripts.p3_clock_contract import atomic_write_json
        atomic_write_json(args.output,result)
    print(json.dumps(result,allow_nan=False))
    raise SystemExit(0 if result['raw_candidate_eligible'] else 2)
