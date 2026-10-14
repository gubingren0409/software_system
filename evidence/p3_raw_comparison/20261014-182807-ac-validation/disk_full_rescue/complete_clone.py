"""Complete only missing files in this task-owned partial clone; no overwrites."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT / 'repository'
sys.path.insert(0, r'C:\Users\28489\AppData\Local\Temp\matrix-raw-comparison-35a60b090b728d2ec3b6a8ea014beac69fe3766d')
from scripts.p3_clock_contract import capture, atomic_write_json, qpc


def main():
    def operation(args, name):
        value = capture(['git', '-C', str(REPO), *args], ROOT / 'operations', name, 'disk-full-rescue', timeout=120)
        if value['returncode'] != 0: raise ValueError(name + ' failed')
        return (ROOT / 'operations' / value['stdout_path']).read_text(encoding='utf-8')
    head = operation(['rev-parse', 'HEAD'], 'clone_head').strip()
    if head != 'c08184e2cd6ac90af9d22aafdd3cd6b2ab09dd06': raise ValueError('Unexpected clone HEAD')
    operation(['config', 'core.longpaths', 'true'], 'clone_only_longpaths')
    operation(['read-tree', 'HEAD'], 'initialize_clone_index_only')
    paths = subprocess.run(['git', '-C', str(REPO), 'ls-files', '-z'], capture_output=True, check=True).stdout.split(b'\0')
    missing = [name for name in paths if name and not (REPO / name.decode('utf-8')).exists()]
    payload = b'\0'.join(missing) + (b'\0' if missing else b'')
    (ROOT / 'missing_checkout_paths.nul').write_bytes(payload)
    argv = ['git', '-C', str(REPO), 'checkout-index', '--stdin', '-z']
    start, hz = qpc()
    result = subprocess.run(argv, input=payload, capture_output=True, check=False)
    end, hz2 = qpc()
    (ROOT / 'missing_checkout.stdout.txt').write_bytes(result.stdout)
    (ROOT / 'missing_checkout.stderr.txt').write_bytes(result.stderr)
    atomic_write_json(ROOT / 'missing_checkout_operation.json', {'command': argv, 'stdin_path': 'missing_checkout_paths.nul',
        'qpc_start': start, 'qpc_end': end, 'qpc_frequency': hz, 'qpc_seconds': (end-start)/hz,
        'returncode': result.returncode, 'missing_files_only': len(missing), 'existing_files_overwritten': False})
    if result.returncode != 0: raise ValueError(result.stderr.decode(errors='replace'))
    status = operation(['status', '--porcelain=v1'], 'complete_clone_status')
    if status: raise ValueError('Emergency clone is not clean: ' + status[:1000])
    destination = REPO / 'evidence/p3_raw_comparison/20261014-182807-ac-validation'
    if destination.exists(): raise ValueError('Never replace task evidence')
    shutil.copytree(ROOT / 'activity-backup', destination)
    provenance = destination / 'disk_full_rescue'; provenance.mkdir()
    for name in ('rescue_evidence.py', 'rescue_manifest.json', 'complete_clone.py', 'missing_checkout_paths.nul',
                 'missing_checkout.stdout.txt', 'missing_checkout.stderr.txt', 'missing_checkout_operation.json'):
        shutil.copy2(ROOT / name, provenance / name)
    shutil.copytree(ROOT / 'operations', provenance / 'operations')
    operation(['remote', 'rename', 'origin', 'source-worktree'], 'rename_local_source_remote')
    operation(['remote', 'add', 'github', 'https://github.com/gubingren0409/software_system.git'], 'add_original_github')
    operation(['remote', 'add', 'origin', 'https://gitea.shuishan.net.cn/SSO.James.2026Fall.DASE/10245102457.git'], 'preserve_course_remote')
    print(json.dumps({'repository': str(REPO), 'evidence_directory': str(destination), 'head': head,
        'copied_without_moving_E_files': True, 'completed_missing_files': len(missing)}), flush=True)


if __name__ == '__main__': main()
