"""One read-only progress snapshot plus a flushed monitoring JSONL; no control actions."""
import ctypes
import datetime
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent
plan=json.loads((OUT/'content/search_plan.json').read_bytes());session=Path(plan['session_directory'])
def read(path): return json.loads(path.read_bytes())
state=read(session/'checkpoint.json');window=read(session/'window.json')
progress=read(session/'controller_progress.json') if (session/'controller_progress.json').exists() else {}
operation=read(OUT/'operations/search_activity.operation.json')
counter=ctypes.c_longlong();frequency=ctypes.c_longlong()
ctypes.windll.kernel32.QueryPerformanceCounter(ctypes.byref(counter))
ctypes.windll.kernel32.QueryPerformanceFrequency(ctypes.byref(frequency))
if frequency.value!=window['qpc_frequency'] or counter.value<window['qpc_start']:
    raise SystemExit('Monitoring QPC epoch/frequency differs; do not subtract across epochs')
elapsed=(window.get('qpc_end',counter.value)-window['qpc_start'])/frequency.value
active=state['active'];job=active['job'] if active else None
if job is None and progress.get('phase')=='group_resources':
    gates=list((session/'group_checks').glob('*/resources/gate_manifest.json'))
    if gates: job=read(max(gates,key=lambda p:p.stat().st_mtime))['context'].get('job')
sample=read(session/'progress.json') if active and (session/'progress.json').exists() else None
if sample and sample['attempt_id']!=active['attempt_id']: sample=None
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
kernel.OpenProcess.argtypes=[ctypes.c_uint32,ctypes.c_int,ctypes.c_uint32];kernel.OpenProcess.restype=ctypes.c_void_p
kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint32];kernel.WaitForSingleObject.restype=ctypes.c_uint32
kernel.CloseHandle.argtypes=[ctypes.c_void_p]
handle=kernel.OpenProcess(0x1000|0x100000,False,window['controller_pid'])
process='unknown'
if handle:
    wait_code=kernel.WaitForSingleObject(handle,0)
    process={258:'running',0:'exited'}.get(wait_code,'unknown wait result '+str(wait_code))
    kernel.CloseHandle(handle)
elif operation['returncode']!='unknown': process='exited (captured returncode)'
value=dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='monitoring_only',phase=progress.get('phase'),
    status=window['status'],algorithm=job.get('algorithm') if job else None,kind=job.get('kind') if job else None,
    config=job.get('config') if job else None,stage=sample['stage'] if sample else None,
    sample_index=sample['sample_index'] if sample else None,saved_current=active['saved_samples'] if active else None,
    search_groups={a:len(t['observations']) for a,t in state['trajectories'].items()},
    retest_groups={a:len(t['retests']) for a,t in state['trajectories'].items()},target_executions=state['target_executions'],
    activity_qpc_seconds=elapsed,remaining_budget_seconds=max(0,43200-elapsed),last_saved=progress.get('at'),
    controller_pid=window['controller_pid'],controller_process=process,controller_returncode=operation['returncode'])
with (OUT/'monitoring.jsonl').open('a',encoding='utf-8') as stream:
    stream.write(json.dumps(value)+'\n');stream.flush()
print(json.dumps(value),flush=True)
