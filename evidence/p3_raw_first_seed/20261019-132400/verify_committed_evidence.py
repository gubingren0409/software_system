"""Verify committed raw evidence byte-for-byte, writing the post-commit proof outside the repo."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--commit',required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
commit=subprocess.check_output(['git','rev-parse',args.commit+'^{commit}'],cwd=ROOT,text=True).strip()
prefix=OUT.relative_to(ROOT).as_posix()
tree=subprocess.check_output(['git','ls-tree','-rz','--full-tree',commit,'--',prefix,'code/original/matrix_multiplication.c'],cwd=ROOT)
reader=subprocess.Popen(['git','cat-file','--batch'],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
changed=[]
count=0
committed_names=set()
try:
    for record in tree.split(b'\0'):
        if not record:continue
        metadata,name=record.split(b'\t',1)
        oid=metadata.split()[2]
        reader.stdin.write(oid+b'\n');reader.stdin.flush()
        header=reader.stdout.readline().split()
        if len(header)!=3 or header[0]!=oid or header[1]!=b'blob':raise ValueError('Git object response differs')
        data=reader.stdout.read(int(header[2]))
        if reader.stdout.read(1)!=b'\n':raise ValueError('Missing Git object delimiter')
        local=ROOT/name.decode('utf-8')
        committed_names.add(name.decode('utf-8'))
        if hashlib.sha256(data).digest()!=hashlib.sha256(local.read_bytes()).digest():changed.append(name.decode('utf-8'))
        count+=1
finally:
    reader.stdin.close();reader.wait(timeout=10)
scientific_diff=subprocess.check_output(['git','diff','--name-only','776b11171d796c8071e69824ffe463c4faf8ba57',commit,'--','code','autotuner','configs','scripts','tests'],cwd=ROOT,text=True)
local_names={path.relative_to(ROOT).as_posix() for path in OUT.rglob('*') if path.is_file()}
missing=sorted(local_names-committed_names)
result=dict(commit=commit,verified_raw_evidence_and_original_files=count,byte_mismatches=changed,
    local_evidence_files=len(local_names),uncommitted_evidence_files=missing,
    frozen_runtime_source_diff=scientific_diff,pass_checks=not changed and not scientific_diff and not missing,
    verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result));raise SystemExit(0 if result['pass_checks'] else 2)
