"""Read-only live Windows-QPC monitoring of this single manual continuation."""
import ctypes
import datetime
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent
directory=OUT/'continuation'
auth=json.loads((directory/'authorization.json').read_bytes())
session=Path(auth['session_directory'])
state=json.loads((session/'checkpoint.json').read_bytes())
path=directory/'window.json'
if not path.exists():path=directory/'progress.json'
if not path.exists():path=session/'MANUAL_FIRST_SEED_FINISH_V2.claim.json'
window=json.loads(path.read_bytes())
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
now=ctypes.c_longlong();frequency=ctypes.c_longlong()
kernel.QueryPerformanceCounter(ctypes.byref(now));kernel.QueryPerformanceFrequency(ctypes.byref(frequency))
if frequency.value!=window['qpc_frequency']:raise ValueError('Monitoring QPC frequency changed')
used=((window['qpc_end'] if 'qpc_end' in window else now.value)-window['qpc_start'])/frequency.value
kernel.OpenProcess.argtypes=[ctypes.c_uint32,ctypes.c_int,ctypes.c_uint32];kernel.OpenProcess.restype=ctypes.c_void_p
kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint32];kernel.WaitForSingleObject.restype=ctypes.c_uint32
kernel.CloseHandle.argtypes=[ctypes.c_void_p]
handle=kernel.OpenProcess(0x100000,False,window['controller_pid'])
if handle:
    wait=kernel.WaitForSingleObject(handle,0);kernel.CloseHandle(handle)
    status='running' if wait==258 else 'exited' if wait==0 else 'unknown'
else:status='exited' if ctypes.get_last_error()==87 else 'unknown'
sample=json.loads((session/'progress.json').read_bytes()) if (session/'progress.json').exists() else None
if not state['active'] or sample and sample['attempt_id']!=state['active']['attempt_id']:sample=None
value=dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),phase=window['phase'],
    status=window['status'],failure_reason=window['failure_reason'],process=status,
    job=window.get('job'),active=state['active'],sample=sample,
    search_groups={a:len(t['observations']) for a,t in state['trajectories'].items()},
    retest_groups={a:len(t['retests']) for a,t in state['trajectories'].items()},
    target_executions=state['target_executions'],activity_qpc_seconds=used,
    cumulative_activity_qpc_seconds=auth['previous_activity_qpc_seconds']+used,
    remaining_budget_seconds=max(0,auth['remaining_allowance_seconds']-used),controller_pid=window['controller_pid'])
with (OUT/'monitoring.jsonl').open('a',encoding='utf-8') as stream:stream.write(json.dumps(value)+'\n');stream.flush()
print(json.dumps(value))
