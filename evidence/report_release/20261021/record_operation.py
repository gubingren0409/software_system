"""Record report-only commands. No experiment or authorization decisions."""
import argparse
import ctypes
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess


def qpc():
    counter, frequency = ctypes.c_longlong(), ctypes.c_longlong()
    ctypes.windll.kernel32.QueryPerformanceCounter(ctypes.byref(counter))
    ctypes.windll.kernel32.QueryPerformanceFrequency(ctypes.byref(frequency))
    return counter.value, frequency.value


parser = argparse.ArgumentParser()
parser.add_argument('--name', required=True)
parser.add_argument('command', nargs=argparse.REMAINDER)
args = parser.parse_args()
command = args.command[1:] if args.command[0] == '--' else args.command
directory = Path(__file__).parent / 'operations'
directory.mkdir(exist_ok=True)
path = directory / (args.name + '.operation.json')
if path.exists():
    raise SystemExit('Refusing to overwrite an operation')
environment = os.environ.copy()
environment.pop('PYTHONPATH', None)
environment['PYTHONDONTWRITEBYTECODE'] = '1'
started, frequency = qpc()
record = dict(command=command, cwd=os.getcwd(), returncode='unknown', qpc_start=started,
              qpc_frequency=frequency, started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              recorder_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
with (directory / (args.name + '.stdout.txt')).open('xb') as output, (directory / (args.name + '.stderr.txt')).open('xb') as error:
    process = subprocess.Popen(command, env=environment, stdout=output, stderr=error,
                               creationflags=subprocess.CREATE_NO_WINDOW)
    record['pid'] = process.pid
    path.write_text(json.dumps(record, indent=2), encoding='utf-8')
    record['returncode'] = process.wait()
ended, end_frequency = qpc()
record.update(qpc_end=ended, qpc_seconds=(ended-started)/frequency,
              frequency_unchanged=frequency == end_frequency,
              ended_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
path.write_text(json.dumps(record, indent=2), encoding='utf-8')
print(json.dumps(record))
raise SystemExit(record['returncode'])
