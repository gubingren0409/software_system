"""Record real commands/streams/return codes; no experimental or budget decisions."""
import argparse
import ctypes
import datetime
import hashlib
import json
import os
import subprocess
from pathlib import Path

def qpc():
    value=ctypes.c_longlong(); frequency=ctypes.c_longlong()
    ctypes.windll.kernel32.QueryPerformanceCounter(ctypes.byref(value))
    ctypes.windll.kernel32.QueryPerformanceFrequency(ctypes.byref(frequency))
    return value.value, frequency.value

def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()

parser=argparse.ArgumentParser(); parser.add_argument('--name',required=True); parser.add_argument('--cwd',required=True)
parser.add_argument('command',nargs=argparse.REMAINDER); args=parser.parse_args()
command=args.command[1:] if args.command[0]=='--' else args.command
directory=Path(__file__).parent/'operations'; directory.mkdir(exist_ok=True)
path=directory/(args.name+'.operation.json')
if path.exists(): raise SystemExit('Operation name already exists; refusing overwrite')
env=os.environ.copy(); env.pop('PYTHONPATH',None); env['PYTHONDONTWRITEBYTECODE']='1'
started,hz=qpc(); record=dict(command=command,cwd=args.cwd,started_at=now(),qpc_start=started,qpc_frequency=hz,
    returncode='unknown',recorder_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
with (directory/(args.name+'.stdout.txt')).open('xb') as output,(directory/(args.name+'.stderr.txt')).open('xb') as error:
    child=subprocess.Popen(command,cwd=args.cwd,env=env,stdout=output,stderr=error,creationflags=subprocess.CREATE_NO_WINDOW)
    record['pid']=child.pid; path.write_text(json.dumps(record,indent=2),encoding='utf-8')
    code=child.wait()
ended,end_hz=qpc(); record.update(returncode=code,qpc_end=ended,ended_at=now(),qpc_seconds=(ended-started)/hz,qpc_frequency_unchanged=end_hz==hz)
path.write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps(record)); raise SystemExit(code)
