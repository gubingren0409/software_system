"""Offline delivery checks only; no target, clock, resource sampling or session writes."""
import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
auth=json.loads((OUT/'continuation/authorization.json').read_bytes())
plan=json.loads(Path(auth['plan_file']).read_bytes())
session=Path(plan['session_directory'])
sha=lambda data:hashlib.sha256(data).hexdigest()
teacher=ROOT/'code/original/matrix_multiplication.c'
teacher_expected='188d011109c4470e1f41829216e8677a5c2d8f2b7c8a44215652320dbdf6de15'
assert sha(teacher.read_bytes())==teacher_expected
assert subprocess.check_output(['git','show',plan['content_commit']+':code/original/matrix_multiplication.c'],cwd=ROOT)==teacher.read_bytes()
assert subprocess.check_output(['git','diff','--name-only',auth['auxiliary_content_commit'],'--','code','autotuner','configs','scripts','tests'],cwd=ROOT)==b''
assert sha(Path(auth['helper_file']).read_bytes())==auth['helper_sha256']==sha((ROOT/'scripts/continue_raw_search.py').read_bytes())
with (session/'samples.jsonl').open('rb') as stream:
    assert sha(stream.read(auth['samples_prefix_bytes']))==auth['samples_prefix_sha256']
samples=[json.loads(line) for line in (session/'samples.jsonl').read_bytes().splitlines() if line]
assert len(samples)==156 and len({s['run_id'] for s in samples})==156
summary=json.loads((OUT/'delivery_summary.json').read_bytes())
assert summary['target_executions']==len(samples) and summary['partial_target_samples']==4
assert summary['search_groups']=={'random':12,'greedy':11} and summary['retest_groups']=={'random':2,'greedy':0}
assert summary['evidence_integrity_pass'] and not any(summary[k] for k in ('execution_complete','timing_checks_pass','comparison_ready'))
assert json.loads((OUT/'stop_review.json').read_bytes())['all_owned_experiment_processes_exited']
rows=json.loads((OUT/'first_seed_six_rows.json').read_bytes())
with (OUT/'first_seed_six_rows.csv').open(encoding='utf-8',newline='') as stream:
    saved=list(csv.DictReader(stream))
assert len(rows)==len(saved)==6
for a,b in zip(rows,saved):
    assert b=={k:'' if v is None else str(v) for k,v in a.items()}
missing=[]
docs=[ROOT/n for n in ('README.md','report.md','docs/AUDIT_HANDOFF.md','docs/P3_FIRST_SEED_STATUS.md','docs/WORK_LOG.md','docs/P3_RAW_SEARCH_CONTINUATION.md')]+[OUT/'README.md']
for path in docs:
    for target in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
        target=target.split('#')[0].strip('<>')
        if not target or re.match(r'^[a-zA-Z][\w+.-]*:',target):continue
        if not (path.parent/unquote(target)).exists():missing.append(dict(file=str(path),target=target))
assert not missing,missing
new_files=subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=ROOT).split(b'\0')
new_paths=[ROOT/p.decode() for p in new_files if p]
assert all(p.is_relative_to(OUT) or p.is_relative_to(session) for p in new_paths),'Unrelated untracked files require review'
forbidden=[str(p) for p in new_paths if p.suffix.lower() in ('.exe','.dll','.o','.so','.a','.bin','.pyc')]
assert not forbidden,forbidden
large=[dict(file=str(p.relative_to(ROOT)),bytes=p.stat().st_size) for p in new_paths if p.stat().st_size>5*1024*1024]
assert not large,large
secret_pattern=re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}')
secret_hits=[str(p.relative_to(ROOT)) for p in new_paths if secret_pattern.search(p.read_bytes())]
assert not secret_hits,secret_hits
result=dict(schema='manual-first-seed-final-offline-checks-v1',teacher_sha256=teacher_expected,
    teacher_git_bytes_exact=True,frozen_runtime_and_auxiliary_source_unchanged=True,
    original_98_sample_prefix_pass=True,six_rows_csv_json_match=True,
    relative_document_links_pass=True,document_count=len(docs),new_evidence_file_count=len(new_paths),
    forbidden_binary_files=forbidden,large_files=large,credential_pattern_hits=secret_hits,
    actual_target_records=len(samples),actual_new_target_records=len(samples)-98,
    new_probe_or_target_calls=0,pass_checks=True,source_sha256=sha(Path(__file__).read_bytes()))
(OUT/'final_checks.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
