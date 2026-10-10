"""Read-only reproduction of the runner's resource collector launch; no targets."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.p3_clock_contract import capture, load

batch = Path(__file__).resolve().parents[1]
archive = load(batch / "execution_plan.json")["archive_directory"]
code = """
import json, subprocess
from pathlib import Path
root = Path.cwd()
script = subprocess.run(['wslpath','-w',str(root/'scripts/check_p2_resources.ps1')],capture_output=True,text=True,check=True).stdout.strip()
command = ['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe','-NoProfile','-File',script,'-Mode','Formal','-RuntimeRoot',str(root)]
result = subprocess.run(command,capture_output=True,timeout=60)
print(json.dumps({'command':command,'returncode':result.returncode,'stdout_hex':result.stdout.hex(),
    'stderr_hex':result.stderr.hex(),'stdout_gb18030':result.stdout.decode('gb18030',errors='backslashreplace'),
    'stderr_gb18030':result.stderr.decode('gb18030',errors='backslashreplace')}))
"""
result = capture(['wsl.exe','-d','Ubuntu-24.04','--cd',archive,'--','env','-u','PYTHONPATH',
                  'PYTHONDONTWRITEBYTECODE=1','python3','-c',code],
                 batch/'diagnosis','exact_gate_launch_bytes','policy-defect-e0353bf',timeout=90)
print(result['returncode'])
