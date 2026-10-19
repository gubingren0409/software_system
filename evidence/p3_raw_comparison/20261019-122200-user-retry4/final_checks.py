"""Read-only delivery checks plus generated JSON; no experiment invocation."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

OUT=Path(__file__).resolve().parent; REPO=OUT.parents[2]
auth=json.loads((OUT/'continuation/authorization.json').read_bytes())
session=Path(auth['session_directory']); errors=[]
digest=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for name,expected in auth['protected_session_files'].items():
    if digest(session/name)!=expected: errors.append('Protected session changed: '+name)
for name,expected in auth['protected_history_files'].items():
    if digest(REPO/name)!=expected: errors.append('Protected history changed: '+name)
state=json.loads((session/'checkpoint.json').read_bytes()); previous=json.loads((OUT/'continuation/preserved/checkpoint.json').read_bytes())
if state['validation_groups'][:2]!=previous['validation_groups']: errors.append('Previous two accepted groups changed')
prefix=(session/'samples.jsonl').read_bytes()[:auth['samples_prefix_bytes']]
if len(prefix)!=auth['samples_prefix_bytes'] or hashlib.sha256(prefix).hexdigest()!=auth['samples_prefix_sha256']: errors.append('Original twelve-line byte prefix changed')
original=REPO/'code/original/matrix_multiplication.c'; expected_original='188d011109c4470e1f41829216e8677a5c2d8f2b7c8a44215652320dbdf6de15'
if digest(original)!=expected_original: errors.append('Teacher bytes changed')
identity=json.loads((OUT/'source_identity.json').read_bytes())
if not all(x['bytes_equal'] for x in identity['auxiliary'] if x['path'].endswith('.py')): errors.append('Auxiliary executable/test Git bytes differ')
if not all(x['normalized_LF_equal'] for x in identity['auxiliary']): errors.append('Auxiliary normalized Git content differs')
links=[]
for path in (REPO/'README.md',REPO/'docs/P3_FIRST_SEED_STATUS.md',REPO/'docs/AUDIT_HANDOFF.md',REPO/'docs/P3_RAW_VALIDATION_CONTINUATION.md',REPO/'docs/P3_RAW_COMPARISON.md',REPO/'report.md',OUT/'README.md'):
    text=path.read_text(encoding='utf-8')
    for target in re.findall(r'\]\(([^)]+)\)',text):
        if '://' in target or target.startswith('#') or '<' in target: continue
        local=target.split('#')[0]
        # This result is produced by this invocation, not a required pre-existing input.
        if local and not (path.parent/local).exists() and (path.parent/local).resolve()!=(OUT/'final_checks.json').resolve():
            errors.append('Missing link '+str(path)+': '+target)
        links.append(dict(document=str(path.relative_to(REPO)),target=target))
window=json.loads((OUT/'continuation/window.json').read_bytes())
newfiles=list(OUT.rglob('*'))
if window.get('checks_directory'): newfiles+=list(Path(window['checks_directory']).rglob('*'))
sensitive=[]; large=[]
for path in newfiles:
    if not path.is_file(): continue
    if path.stat().st_size>5*1024**2: large.append(str(path))
    if path.suffix in ('.py','.ps1','.txt','.json','.jsonl','.md'):
        text=path.read_text(encoding='utf-8-sig',errors='replace')
        if re.search(r'gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',text): sensitive.append(str(path))
if large or sensitive: errors.append('Large/sensitive candidate files need review')
# Exact owned Windows PIDs only, not an instruction to terminate anything.
operation=json.loads((OUT/'operations/continuation_activity.operation.json').read_bytes())
checks=subprocess.run(['powershell.exe','-NoProfile','-Command',f"@(Get-Process -Id {operation['pid']} -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,StartTime) | ConvertTo-Json"],capture_output=True,text=True)
if checks.stdout.strip(): errors.append('Owned controller PID still exists; verify identity')
git_status=subprocess.check_output(['git','status','--short','--branch'],cwd=REPO,text=True)
result=dict(pass_checks=not errors,errors=errors,auditor_sha256=digest(Path(__file__)),teacher_sha256=digest(original),
    protected_session_files=len(auth['protected_session_files']),protected_history_files=len(auth['protected_history_files']),
    previous_two_groups_unchanged=state['validation_groups'][:2]==previous['validation_groups'],original_twelve_line_prefix_unchanged=True,
    checkpoint_bytes_unchanged=digest(session/'checkpoint.json')==auth['checkpoint_sha256'],
    executable_and_test_bytes_equal=all(x['bytes_equal'] for x in identity['auxiliary'] if x['path'].endswith('.py')),
    all_auxiliary_normalized_content_equal=all(x['normalized_LF_equal'] for x in identity['auxiliary']),
    nonexecuted_documentation_CRLF_difference=[x['path'] for x in identity['auxiliary'] if not x['bytes_equal']],
    links_checked=len(links),links=links,large_files=large,sensitive_signature_matches=sensitive,
    controller_returncode=operation['returncode'],owned_controller_pid=operation['pid'],owned_controller_running=bool(checks.stdout.strip()),
    git_status=git_status,process_check_stdout=checks.stdout,process_check_stderr=checks.stderr,process_check_returncode=checks.returncode)
(OUT/'final_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='links'},ensure_ascii=False)); raise SystemExit(0 if not errors else 1)
