"""Corrected read-only process check; earlier embedded-NUL launch failure is kept."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.p3_clock_contract import capture

code = """
from pathlib import Path
import fcntl, json
found=[]
for path in Path('/proc').glob('[0-9]*/cmdline'):
    try:
        args=[v.decode(errors='backslashreplace') for v in path.read_bytes().split(bytes([0])) if v]
        if args and (('campaign' in args and 'autotuner' in args) or
            (Path(args[0]).name in ('candidate','reference_generator') and args[0].startswith('/var/tmp/matrix-autotuner-'))):
            found.append({'pid':int(path.parent.name),'command':args})
    except (OSError, ValueError): pass
with Path('/var/tmp/matrix-autotuner-p3-10245102457.runner.lock').open('r') as stream:
    try:
        fcntl.flock(stream, fcntl.LOCK_EX|fcntl.LOCK_NB); available=True
        fcntl.flock(stream, fcntl.LOCK_UN)
    except BlockingIOError: available=False
print(json.dumps({'formal_processes':found,'runner_lock_available':available}))
"""
result = capture(['wsl.exe','-d','Ubuntu-24.04','--cd','/tmp','--','python3','-c',code],
    Path(__file__).resolve().parent,'process_state_corrected','policy-final',timeout=30)
print(result['returncode'])
