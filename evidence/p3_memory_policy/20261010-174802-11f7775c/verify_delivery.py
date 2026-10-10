"""Read-only delivery consistency; PASS is not formal comparison acceptance."""
import ast
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT))
from autotuner.core import sha256_file,utc_now
from scripts.p3_clock_contract import atomic_write_json,load,verify_recovery,snapshot_campaign

plan=load(HERE/'session_plan.json')
recovery=Path(plan['recovery_directory'])
review=verify_recovery(recovery,snapshot_campaign(Path(plan['campaign_directory'])))
assert review==load(HERE/'independent_recovery.json')['clock_recovery_reevaluation']
assert review['evidence_integrity_pass'] and not review['recovery_eligible']
assert len([p for p in HERE.iterdir() if p.name=='recovery'])==1 and not Path(plan['resume_directory']).exists()
assert load(HERE/'delivery_summary.json')['analysis_source_sha256']==sha256_file(HERE/'finalize.py')
assert subprocess.check_output(['git','diff',plan['content_commit'],'--','autotuner','code','configs','scripts','tests'],cwd=ROOT)==b''

operations=0
for path in HERE.rglob('*.operation.json'):
    record=load(path)
    # The capture running this verifier has not finished yet, so cannot be sealed here.
    if 'qpc_end' not in record: continue
    for stream in ('stdout','stderr'):
        assert sha256_file(path.parent/record[stream+'_path'])==record[stream+'_sha256'],str(path)
    operations+=1
json_count=0
for path in HERE.rglob('*.json'):
    load(path); json_count+=1
sources=list(HERE.glob('*.py'))
for path in sources: ast.parse(path.read_text(encoding='utf-8'))
links=0
documents=[ROOT/'README.md',ROOT/'report.md',*[ROOT/'docs'/name for name in
    ('P3_MEMORY_POLICY.md','P3_RESOURCE_POLICY.md','P3_FIRST_SEED_STATUS.md','AUDIT_HANDOFF.md','WORK_LOG.md')]]
for path in documents:
    for target in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
        if '://' in target or target.startswith('#'): continue
        destination=(path.parent/unquote(target.split('#',1)[0].strip('<>'))).resolve()
        assert destination.exists(),(path,target)
        links+=1
oversize=[p.relative_to(HERE).as_posix() for p in HERE.rglob('*') if p.is_file() and p.stat().st_size>2*1024*1024]
assert not oversize,oversize
for path in HERE.rglob('*'):
    if path.is_file():
        assert not re.search(rb'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{30,}',path.read_bytes()),'credential-like content detected'
result={'status':'PASS','scope':'Delivery consistency only, not timing or algorithm completion',
    'recorded_at':utc_now(),'executed_verifier_sha256':sha256_file(Path(__file__)),
    'runtime_content_commit':plan['content_commit'],'sealed_operations':operations,'json_files':json_count,
    'evidence_python_ast_files':len(sources),'local_document_links':links,'files_over_2MiB':oversize,
    'independent_recovery_unchanged':True,'runtime_sources_unchanged':True,'teacher_byte_identity_preserved':True}
atomic_write_json(HERE/'delivery_consistency.json',result)
print(json.dumps(result))
