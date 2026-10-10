"""Collect exactly one predeclared fixed-work round with real Windows QPC."""
from __future__ import annotations
import argparse,json,os,queue,subprocess,sys,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from autotuner.core import sha256_file,utc_now
from scripts.p3_clock_contract import atomic_write_json,load,qpc,capture
from scripts.p3_fixed_work_clock import CRITERIA,SOURCE_FILES,schedule,check_interval


def collect(directory):
    if os.name!='nt': raise ValueError('Real Windows QPC required')
    directory=Path(directory); manifest=load(directory/'manifest.json')
    if (directory/'intervals.jsonl').exists(): raise ValueError('No overwrite/repeated round')
    if manifest['criteria']!=CRITERIA or manifest['schedule']!=schedule(manifest['cpu_selection']['selected_cpu']) or \
            set(manifest['source_sha256'])!=set(SOURCE_FILES): raise ValueError('Declaration differs')
    for path,digest in manifest['source_sha256'].items():
        if sha256_file(ROOT/path)!=digest: raise ValueError('Actual source differs: '+path)
    deadline=time.perf_counter()+480; collection_start,frequency=qpc()
    capture(manifest['metadata_command'],directory,'wsl_environment',manifest['batch_id'],
            sha256_file(directory/'manifest.json'),timeout=min(40,deadline-time.perf_counter()))
    started,freq=qpc()
    if freq!=frequency: raise ValueError('QPC frequency changed')
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'); env.pop('PYTHONPATH',None)
    stdout=(directory/'native.stdout.txt').open('wb'); stderr=(directory/'native.stderr.txt').open('wb')
    messages=(directory/'messages.jsonl').open('wb'); intervals=(directory/'intervals.jsonl').open('wb')
    received=queue.Queue(); child=None; readers=[]; errors=[]; hello=None; seq=0; count=0; rc='unknown'
    operation={'schema':'fixed-work-clock-process-v1','command':manifest['probe_command'],'pid':'unknown',
        'started_at':utc_now(),'qpc_start':started,'qpc_frequency':frequency,'returncode':'unknown',
        'manifest_sha256':sha256_file(directory/'manifest.json'),'collection_start_qpc':collection_start,
        'collection_budget_seconds':480}

    def append(handle,value):
        handle.write((json.dumps(value,allow_nan=False)+'\n').encode()); handle.flush()

    def read_stdout():
        try:
            for line in iter(child.stdout.readline,b''):
                stamp,freq=qpc() # Stamp the response before JSON parsing or disk writes.
                stdout.write(line); stdout.flush(); received.put((stamp,freq,line))
        finally: received.put(None)

    def read_stderr():
        for line in iter(child.stderr.readline,b''): stderr.write(line); stderr.flush()

    def receive(sent,command):
        # Fixed-work long interval is not incorrectly subjected to the old 15s IO cap.
        remaining=deadline-time.perf_counter()
        if remaining<=0: raise TimeoutError('480s collection budget exhausted')
        item=received.get(timeout=remaining)
        if item is None: raise ValueError('Native EOF before expected response')
        stamp,freq,line=item
        if freq!=frequency: raise ValueError('QPC frequency changed')
        answer=json.loads(line,parse_constant=lambda token: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
        record={'command':command,'send_qpc':sent,'recv_qpc':stamp,'response':answer}; append(messages,record)
        return record

    def request(op,args=''):
        nonlocal seq
        if time.perf_counter()>=deadline: raise TimeoutError('480s collection budget exhausted')
        seq+=1; command=f'{op} {seq}'+(' '+args if args else '')+'\n'; sent,freq=qpc()
        if freq!=frequency: raise ValueError('QPC frequency changed')
        atomic_write_json(directory/'progress.json',{'saved_intervals':count,'request':command.strip(),
            'sequence':seq,'native_pid':hello['pid'],'updated_at':utc_now(),'host_child_pid':child.pid})
        child.stdin.write(command.encode('ascii')); child.stdin.flush()
        record=receive(sent,command); value=record['response']
        if value.get('schema')!='fixed-work-clock-endpoint-v1' or value.get('op')!=op or \
                type(value.get('seq')) is not int or value['seq']!=seq or value.get('pid')!=hello['pid']:
            raise ValueError('Native sequence/schema/PID/op differs')
        return record

    try:
        child=subprocess.Popen(manifest['probe_command'],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,env=env,creationflags=subprocess.CREATE_NO_WINDOW)
        operation['pid']=child.pid; atomic_write_json(directory/'native_process.json',operation)
        readers=[threading.Thread(target=read_stdout,daemon=True),threading.Thread(target=read_stderr,daemon=True)]
        for reader in readers: reader.start()
        hello=receive(started,'START_PROCESS')['response']
        if hello.get('schema')!='fixed-work-clock-endpoint-v1' or hello.get('op')!='HELLO' or hello.get('seq')!=0 or \
                type(hello.get('pid')) is not int or hello.get('allowed_cpus')!=manifest['cpu_selection']['allowed_cpus']:
            raise ValueError('Hello/PID/preselected affinity differs')
        for plan in manifest['schedule']:
            request('MODE',f"{plan['path']} {plan['selected_cpu']}")
            first=seq+1; start=request('READ'); work=request('WORK',str(plan['updates'])); end=request('READ')
            row={'schema':'fixed-work-clock-interval-v1','planned':plan,'qpc_frequency':frequency,
                 'start':start,'work':work,'end':end}
            row['check']=check_interval(row,frequency,plan,hello['pid'],first,hello['allowed_cpus'])
            append(intervals,row); count+=1
            print(json.dumps({'saved_intervals':count,'condition':plan['condition'],'updates':plan['updates'],
                'raw_pass':row['check']['raw_pass'],'monotonic_match':row['check'].get('within_host_with_allowance',{}).get('monotonic'),
                'errors':row['check']['errors']}),flush=True)
        request('QUIT'); rc=child.wait(timeout=max(0.001,deadline-time.perf_counter()))
        if rc!=0: errors.append('Native exit not zero')
    except (ValueError,KeyError,TypeError,OSError,TimeoutError,queue.Empty,subprocess.TimeoutExpired) as error:
        errors.append(type(error).__name__+': '+str(error))
    finally:
        if child is not None and child.poll() is None:
            child.stdin.close()
            # Inner native timeout is also bounded. Only terminate the child started here.
            try: rc=child.wait(timeout=max(0.001,min(5,deadline-time.perf_counter())))
            except subprocess.TimeoutExpired:
                child.terminate()
                try: rc=child.wait(timeout=3)
                except subprocess.TimeoutExpired: errors.append('Owned child exit unknown')
        elif child is not None: rc=child.returncode
        for reader in readers: reader.join(timeout=2)
        extras=[]
        while not received.empty():
            item=received.get_nowait()
            if item is not None: extras.append(item[2].decode(errors='backslashreplace'))
        if extras: errors.append('Unexpected extra output: '+repr(extras))
        for handle in (stdout,stderr,messages,intervals): handle.flush(); handle.close()
        ended,freq=qpc()
        operation.update(qpc_end=ended,qpc_seconds=(ended-started)/frequency,returncode=rc,saved_intervals=count,
            errors=errors,hello=hello,stream_sha256={name:sha256_file(directory/name) for name in
                ('native.stdout.txt','native.stderr.txt','messages.jsonl','intervals.jsonl')})
        atomic_write_json(directory/'native_process.json',operation)
    return 0 if count==22 and not errors else 2


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--directory',type=Path,required=True)
    raise SystemExit(collect(parser.parse_args().directory))
