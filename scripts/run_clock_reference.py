"""One predeclared 30-interval native-C/Windows-QPC diagnostic, no matrix launch."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from autotuner.core import sha256_file,utc_now
from scripts.p3_clock_contract import atomic_write_json,load,qpc,capture
from scripts.p3_clock_reference import CONDITIONS,CRITERIA,check_interval


def collect(directory):
    if os.name!='nt': raise ValueError('Real diagnostic requires Windows QPC, not POSIX fallback')
    directory=Path(directory)
    manifest=load(directory/'manifest.json')
    if (directory/'intervals.jsonl').exists(): raise ValueError('No overwriting or repeated diagnostic')
    assert manifest['conditions']==CONDITIONS and manifest['criteria']==CRITERIA
    for path,digest in manifest['source_sha256'].items(): assert sha256_file(ROOT/path)==digest,path
    deadline=time.perf_counter()+480
    collection_start,collection_frequency=qpc()
    capture(manifest['metadata_command'],directory,'wsl_environment',manifest['batch_id'],
            sha256_file(directory/'manifest.json'),timeout=40)
    command=manifest['probe_command']
    env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'); env.pop('PYTHONPATH',None)
    started_qpc,frequency=qpc()
    assert frequency==collection_frequency
    raw_stdout=(directory/'native.stdout.txt').open('wb')
    raw_stderr=(directory/'native.stderr.txt').open('wb')
    messages=(directory/'messages.jsonl').open('wb')
    intervals=(directory/'intervals.jsonl').open('wb')
    received=queue.Queue()
    child=None; errors=[]; count=0; sequence=0; hello=None; returncode='unknown'; readers=[]
    operation={'schema':'clock-reference-process-v1','command':command,'pid':'unknown',
        'started_at':utc_now(),'qpc_start':started_qpc,'qpc_frequency':frequency,'returncode':'unknown',
        'manifest_sha256':sha256_file(directory/'manifest.json'),'timeout_seconds':480,
        'collection_start_qpc':collection_start}

    def append(handle,value):
        handle.write((json.dumps(value,allow_nan=False)+'\n').encode('utf-8')); handle.flush()

    def stdout_reader():
        try:
            for line in iter(child.stdout.readline,b''):
                stamp,freq=qpc()
                raw_stdout.write(line); raw_stdout.flush()
                received.put((stamp,freq,line))
        finally: received.put(None)

    def stderr_reader():
        for line in iter(child.stderr.readline,b''):
            raw_stderr.write(line); raw_stderr.flush()

    def receive(send,request):
        item=received.get(timeout=max(0.001,min(15,deadline-time.perf_counter())))
        if item is None: raise ValueError('Native process ended before expected response')
        stamp,freq,line=item
        if freq!=frequency: raise ValueError('QPC frequency changed')
        value=json.loads(line,parse_constant=lambda x: (_ for _ in ()).throw(ValueError('Nonfinite native JSON')))
        record={'command':request,'send_qpc':send,'recv_qpc':stamp,'response':value}
        append(messages,record)
        return record

    def request(op,args=''):
        nonlocal sequence
        if time.perf_counter()>=deadline: raise TimeoutError('480-second collection budget exhausted')
        sequence+=1
        command_line=f'{op} {sequence}'+(' '+args if args else '')+'\n'
        sent,freq=qpc()
        if freq!=frequency: raise ValueError('QPC frequency changed')
        child.stdin.write(command_line.encode('ascii')); child.stdin.flush()
        record=receive(sent,command_line); answer=record['response']
        if answer.get('schema')!='native-clock-endpoint-v1' or answer.get('op')!=op or \
                type(answer.get('seq')) is not int or answer['seq']!=sequence or answer.get('pid')!=hello['pid']:
            raise ValueError('Native schema/PID/sequence/op mismatch')
        return record

    try:
        child=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,
                               creationflags=subprocess.CREATE_NO_WINDOW)
        operation['pid']=child.pid
        atomic_write_json(directory/'native_process.json',operation)
        readers=[threading.Thread(target=stdout_reader,daemon=True),threading.Thread(target=stderr_reader,daemon=True)]
        for thread in readers: thread.start()
        hello=receive(started_qpc,'START_PROCESS')['response']
        if hello.get('op')!='HELLO' or hello.get('seq')!=0 or type(hello.get('pid')) is not int or \
                not hello.get('allowed_cpus'): raise ValueError('Invalid native hello')
        for condition in CONDITIONS:
            selected=hello['allowed_cpus'][0] if condition['affinity']=='first_allowed' else -1
            request('MODE',f"{condition['path']} {selected}")
            for index in range(condition['count']):
                first=sequence+1
                start=request('READ')
                waited=request('WAIT',condition['workload'])
                if waited['response'].get('workload')!=condition['workload']: raise ValueError('Wrong workload response')
                end=request('READ')
                row={'schema':'qpc-bounded-clock-interval-v1','condition':condition['name'],'index':index,
                    'selected_cpu':selected,'qpc_frequency':frequency,'start':start,'wait':waited,'end':end}
                row['check']=check_interval(row,frequency,condition,hello['pid'],first,hello['allowed_cpus'])
                append(intervals,row); count+=1
                print(json.dumps({'condition':condition['name'],'index':index,'saved_intervals':count,
                    'reference_match_pass':row['check']['reference_match_pass'],
                    'uncertainty_seconds':row['check'].get('uncertainty_seconds'),'warnings':row['check']['warnings']}),flush=True)
        request('QUIT')
        returncode=child.wait(timeout=max(0.001,min(10,deadline-time.perf_counter())))
        if returncode!=0: errors.append('Native exit is not zero')
        for thread in readers: thread.join(timeout=2)
        if not received.empty():
            extras=[]
            while not received.empty():
                item=received.get_nowait()
                if item is not None: extras.append(item[2].decode('utf-8',errors='backslashreplace'))
            if extras: errors.append('Unexpected extra native output: '+repr(extras))
    except (ValueError,OSError,KeyError,TypeError,TimeoutError,queue.Empty,subprocess.TimeoutExpired) as error:
        errors.append(type(error).__name__+': '+str(error))
    finally:
        if child is not None and child.poll() is None:
            child.stdin.close() # Request EOF first; do not leave an idle native child waiting.
            try: returncode=child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.terminate() # Own wsl.exe child only; inner timeout also bounds native lifetime.
                try: returncode=child.wait(timeout=5)
                except subprocess.TimeoutExpired: errors.append('Owned child exit unknown')
        elif child is not None:
            returncode=child.returncode
        if child is not None:
            for thread in readers: thread.join(timeout=2)
        for handle in (raw_stdout,raw_stderr,messages,intervals): handle.flush(); handle.close()
        ended,freq=qpc()
        operation.update(qpc_end=ended,qpc_seconds=(ended-started_qpc)/frequency,returncode=returncode,
            saved_intervals=count,errors=errors,hello=hello,
            stream_sha256={name:sha256_file(directory/name) for name in
                ('native.stdout.txt','native.stderr.txt','messages.jsonl','intervals.jsonl')})
        atomic_write_json(directory/'native_process.json',operation)
    return 0 if count==30 and not errors else 2


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,required=True)
    raise SystemExit(collect(parser.parse_args().directory))
