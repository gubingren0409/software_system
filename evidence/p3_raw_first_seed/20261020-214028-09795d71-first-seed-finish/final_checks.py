"""Offline delivery verification; never invokes a matrix, clock or resource sampler."""
import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2]
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
auth=read(OUT/'continuation/authorization.json');session=Path(auth['session_directory'])
summary=read(OUT/'delivery_summary.json');independent=read(OUT/'independent_first_seed_audit.json')
teacher=ROOT/'code/original/matrix_multiplication.c'
assert sha(teacher)=='188d011109c4470e1f41829216e8677a5c2d8f2b7c8a44215652320dbdf6de15'
assert subprocess.check_output(['git','show',auth['content_commit']+':code/original/matrix_multiplication.c'],cwd=ROOT)==teacher.read_bytes()
assert subprocess.check_output(['git','diff','--name-only',auth['auxiliary_content_commit'],'--','code','autotuner','configs','scripts','tests'],cwd=ROOT)==b''
assert sha(auth['helper_file'])==auth['helper_sha256']==sha(ROOT/'scripts/finish_raw_search.py')
with (session/'samples.jsonl').open('rb') as stream:
    assert hashlib.sha256(stream.read(auth['samples_prefix_bytes'])).hexdigest()==auth['samples_prefix_sha256']
state=read(session/'checkpoint.json');old=read(OUT/'continuation/preserved/checkpoint.json')
assert state['manual_resume']==old['manual_resume']
assert state['trajectories']['random']==old['trajectories']['random']
assert state['trajectories']['greedy']['observations'][:11]==old['trajectories']['greedy']['observations']
samples=[json.loads(line) for line in (session/'samples.jsonl').read_bytes().splitlines() if line]
assert len(samples)==len({s['run_id'] for s in samples})==summary['target_executions']==state['target_executions']
assert summary['new_target_executions']==len(samples)-156
assert not summary['five_seed_execution_complete'] and not summary['five_seed_comparison_ready']
for key in ('evidence_integrity_pass','execution_complete','timing_checks_pass','comparison_ready'):
    assert summary[key] is independent[key]
if summary['comparison_ready']:
    g=summary['retest_groups']['greedy']
    assert g in (1,2) and summary['search_groups']=={'random':12,'greedy':12}
    assert summary['retest_groups']['random']==2 and summary['abandoned_target_samples']==6
    assert len(samples)==162+6*g and summary['new_target_executions']==6+6*g
    assert independent['accepted_target_samples']==156+6*g and independent['search_groups']==24
    assert state['active'] is None and state['status']=='complete' and not summary['partial_target_samples']
assert read(OUT/'stop_review.json')['all_owned_experiment_processes_exited']
rows=read(OUT/'first_seed_six_rows.json')
with (OUT/'first_seed_six_rows.csv').open(encoding='utf-8',newline='') as stream:saved=list(csv.DictReader(stream))
assert len(rows)==len(saved)==6
for a,b in zip(rows,saved):assert b=={k:'' if v is None else str(v) for k,v in a.items()}
docs=[ROOT/n for n in ('README.md','report.md','docs/AUDIT_HANDOFF.md','docs/P3_FIRST_SEED_STATUS.md','docs/WORK_LOG.md','docs/P3_RAW_SEARCH_FINISH.md')]+[OUT/'README.md']
missing=[]
for path in docs:
    for target in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
        target=target.split('#')[0].strip('<>')
        if not target or re.match(r'^[a-zA-Z][\w+.-]*:',target):continue
        if not (path.parent/unquote(target)).exists():missing.append(dict(file=str(path),target=target))
assert not missing,missing
new=subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=ROOT).split(b'\0')
paths=[ROOT/p.decode() for p in new if p]
assert all(p.is_relative_to(OUT) or p.is_relative_to(session) for p in paths)
assert not [p for p in paths if p.suffix.lower() in ('.exe','.dll','.o','.so','.a','.bin','.pyc')]
large=[p for p in paths if p.stat().st_size>5*1024*1024]
# The user requires this exact reviewed checkpoint snapshot, not a truncated substitute.
required_snapshot=OUT/'continuation/preserved/checkpoint.json'
assert all(p==required_snapshot and sha(p)==auth['checkpoint_sha256'] for p in large),large
secrets=re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}')
assert not [p for p in paths if secrets.search(p.read_bytes())]
result=dict(schema='first-seed-finish-offline-checks-v2',pass_checks=True,teacher_sha256=sha(teacher),
    original_156_prefix_pass=True,original_manual_resume_unchanged=True,original_25_groups_preserved=True,
    frozen_and_auxiliary_source_unchanged=True,six_rows_match=True,relative_document_links_pass=True,
    new_evidence_file_count=len(paths),actual_target_records=len(samples),new_targets=len(samples)-156,
    necessary_large_evidence=[dict(file=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=sha(p)) for p in large],
    new_probe_or_target_calls=0,source_sha256=sha(Path(__file__)))
(OUT/'final_checks.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
