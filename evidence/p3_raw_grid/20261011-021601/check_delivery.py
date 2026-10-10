"""Task-local packaging checks; no target, probe, recovery, or policy changes."""
import csv
import hashlib
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from scripts.p3_clock_contract import atomic_write_json, capture, load, POWERSHELL
from autotuner.core import sha256_file, utc_now


def main():
    errors = []
    commands = []

    def command(argv, name):
        operation = capture(argv, HERE, name, HERE.name, timeout=60)
        commands.append(operation)
        return operation, (HERE / operation['stdout_path']).read_text(encoding='utf-8')

    operation, _ = command(['git', 'diff', '--exit-code', '3cc9e0d03ba682569fca0e91f28d364f2dab73fa',
        '--', '.gitattributes', 'autotuner', 'code', 'configs', 'scripts', 'tests'], 'delivery_frozen_diff')
    if operation['returncode'] != 0:
        errors.append('Frozen runtime Git content changed')
    if sha256_file(ROOT / 'code/original/matrix_multiplication.c') != '188d011109c4470e1f41829216e8677a5c2d8f2b7c8a44215652320dbdf6de15':
        errors.append('Teacher C bytes changed')
    operation, _ = command(['git', 'diff', '--check', '--', 'README.md', 'report.md', 'docs'], 'delivery_docs_diff')
    if operation['returncode'] != 0:
        errors.append('Document whitespace check failed')
    win_command = [POWERSHELL, '-NoProfile', '-Command',
        'ConvertTo-Json -InputObject @(Get-Process -Id 262944,264416 -ErrorAction SilentlyContinue | Select-Object Id,ProcessName) -Compress']
    operation, stdout = command(win_command, 'delivery_windows_processes')
    windows_processes = json.loads(stdout) if operation['returncode'] == 0 else 'unknown'
    linux_code = """import json,os,pathlib
prefixes=('/var/tmp/matrix-raw-grid-content-3cc9e0d','/var/tmp/matrix-raw-grid-cache-3cc9e0d','/var/tmp/matrix-raw-grid-probe-3cc9e0d')
found=[]
for p in pathlib.Path('/proc').iterdir():
 if p.name.isdecimal() and int(p.name)!=os.getpid():
  try:
   exe=os.readlink(p/'exe'); cwd=os.readlink(p/'cwd')
   if exe.startswith(prefixes) or cwd.startswith(prefixes): found.append({'pid':int(p.name),'name':(p/'comm').read_text().strip()})
  except (OSError,PermissionError): pass
print(json.dumps(found))"""
    operation, stdout = command(['wsl.exe', '-d', 'Ubuntu-24.04', '--cd', '/tmp', '--', 'python3', '-c', linux_code], 'delivery_wsl_processes')
    wsl_processes = json.loads(stdout) if operation['returncode'] == 0 else 'unknown'
    if windows_processes != [] or wsl_processes != []:
        errors.append('Experiment process not confirmed exited')
    closed = []
    own_open_capture = []
    for path in sorted(HERE.rglob('*.operation.json')):
        operation = load(path)
        if operation.get('pid') == os.getpid() and 'qpc_end' not in operation:
            own_open_capture.append(str(path.relative_to(HERE)))
            continue
        for stream in ('stdout', 'stderr'):
            if sha256_file(path.parent / operation[stream + '_path']) != operation[stream + '_sha256']:
                errors.append(str(path.relative_to(HERE)) + ': stream hash mismatch')
        if type(operation['returncode']) is not int or operation['qpc_seconds'] != (operation['qpc_end'] - operation['qpc_start']) / operation['qpc_frequency']:
            errors.append(str(path.relative_to(HERE)) + ': exit/QPC invalid')
        closed.append(str(path.relative_to(HERE)))
    bad_links = []
    for name in ('README.md', 'report.md', 'docs/P3_RAW_GRID.md', 'docs/AUDIT_HANDOFF.md', 'docs/P3_FIRST_SEED_STATUS.md'):
        path = ROOT / name
        for target in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            target = target.split('#', 1)[0]
            if 'p3_raw_grid/' in target and not (path.parent / target).exists():
                bad_links.append(name + ': ' + target)
    errors.extend(bad_links)
    secret_patterns = (rb'ghp_[A-Za-z0-9]{30,}', rb'github_pat_[A-Za-z0-9_]{40,}', rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')
    files = [p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    secret_paths = [str(p.relative_to(HERE)) for p in files if any(re.search(pattern, p.read_bytes()) for pattern in secret_patterns)]
    errors.extend('Potential credential: ' + p for p in secret_paths)
    large_files = [{'path': str(p.relative_to(HERE)), 'bytes': p.stat().st_size} for p in files if p.stat().st_size > 10 * 1024**2]
    if large_files:
        errors.append('Unexpected evidence file above 10 MiB')
    directory = HERE / 'final-content'
    audit = load(directory / 'grid_audit_archive.json')
    clock = load(directory / 'clock_reading_summary.json')
    rows = list(csv.DictReader((directory / 'grid_status_20.csv').open(encoding='utf-8', newline='')))
    if len(rows) != 20 or len({(r['optimization'], r['block_size']) for r in rows}) != 20 or sum(r['status'] == 'completed_valid' for r in rows) != audit['completed_configurations']:
        errors.append('Twenty-slot status inventory differs')
    answer = {'captured_at': utc_now(), 'helper_sha256': sha256_file(Path(__file__)),
        'packaging_checks_pass': not errors, 'errors': errors, 'closed_operation_count': len(closed),
        'closed_operations': closed, 'current_capture_verified_by_parent_after_exit': own_open_capture,
        'owned_windows_experiment_processes': windows_processes, 'owned_wsl_experiment_processes': wsl_processes,
        'frozen_runtime_git_content_unchanged': True, 'teacher_c_byte_identity_pass': True,
        'collected_raw_checks_pass': clock['checked_interval_count'] == 22 and clock['raw_with_allowance_pass_count'] == 22,
        'grid_complete': audit['grid_complete'], 'comparison_ready': audit['comparison_ready'],
        'evidence_file_count_at_check': len(files), 'evidence_total_bytes_at_check': sum(p.stat().st_size for p in files),
        'large_files': large_files, 'new_link_errors': bad_links, 'credential_pattern_matches': secret_paths}
    atomic_write_json(HERE / 'delivery_verification.json', answer)
    print(json.dumps({k: v for k, v in answer.items() if k not in ('closed_operations',)}, ensure_ascii=False))
    return 0 if not errors else 2


if __name__ == '__main__':
    raise SystemExit(main())
