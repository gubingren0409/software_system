"""Final read-only delivery checks, not a performance experiment."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2]
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
summary=json.loads((OUT/'delivery_summary.json').read_bytes())
history=json.loads((OUT/'history_after.json').read_bytes())
plan=json.loads((OUT/'content/search_plan.json').read_bytes());session=Path(plan['session_directory'])
window=json.loads((session/'window.json').read_bytes());errors=[]
if not history['history_integrity_pass']: errors.append('Historical evidence changed')
teacher=ROOT/'code/original/matrix_multiplication.c'
if digest(teacher)!='188d011109c4470e1f41829216e8677a5c2d8f2b7c8a44215652320dbdf6de15': errors.append('Teacher bytes changed')
changed_science=subprocess.check_output(['git','diff','--name-only',plan['content_commit'],'--','code','autotuner','configs'],cwd=ROOT,text=True)
if changed_science.strip(): errors.append('Working-tree science differs from execution content; review without overwriting')
links=[]
for path in (ROOT/'README.md',ROOT/'report.md',ROOT/'docs/AUDIT_HANDOFF.md',ROOT/'docs/P3_FIRST_SEED_STATUS.md',ROOT/'docs/P3_RAW_FIRST_SEED_RUN.md',OUT/'README.md'):
    for target in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
        if '://' in target or target.startswith('#') or '<' in target: continue
        local=target.split('#')[0];resolved=path.parent/local
        if local and not resolved.exists() and resolved.resolve()!=(OUT/'final_checks.json').resolve(): errors.append('Missing link '+str(path)+': '+target)
        links.append(dict(document=str(path.relative_to(ROOT)),target=target))
sensitive=[];large=[]
for path in OUT.rglob('*'):
    if not path.is_file(): continue
    if path.stat().st_size>5*1024**2: large.append(str(path))
    if path.suffix in ('.py','.ps1','.txt','.json','.jsonl','.md'):
        text=path.read_text(encoding='utf-8-sig',errors='replace')
        if re.search(r'gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',text): sensitive.append(str(path))
if sensitive or large: errors.append('Sensitive/large candidates require review')
stop_review=json.loads((OUT/'stop_review.json').read_bytes())
if not stop_review['all_owned_experiment_processes_exited']: errors.append('Owned Windows/WSL experiment process remains or exit status unknown')
check=subprocess.run(['C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe','-NoProfile','-Command',f"@(Get-Process -Id {window['controller_pid']} -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,StartTime) | ConvertTo-Json"],capture_output=True,text=True)
if check.stdout.strip(): errors.append('Owned controller PID still exists; verify identity')
if check.returncode!=0: errors.append('Owned-process check unknown')
result=dict(pass_checks=not errors,errors=errors,teacher_sha256=digest(teacher),history_integrity_pass=history['history_integrity_pass'],
    protected_history_files=history['protected_files'],execution_content_sha=plan['content_commit'],session_id=plan['session_id'],
    current_scientific_diff=changed_science,links_checked=len(links),links=links,large_files=large,sensitive_signatures=sensitive,
    controller_returncode=summary['controller_returncode'],owned_controller_running=bool(check.stdout.strip()),
    process_check_stdout=check.stdout,process_check_stderr=check.stderr,process_check_returncode=check.returncode,
    final_checker_sha256=digest(Path(__file__)),git_status=subprocess.check_output(['git','status','--short','--branch'],cwd=ROOT,text=True))
(OUT/'final_checks.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='links'}));raise SystemExit(0 if not errors else 2)
