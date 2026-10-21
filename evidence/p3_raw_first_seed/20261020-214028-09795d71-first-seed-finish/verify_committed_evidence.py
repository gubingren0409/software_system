"""Post-commit byte proof; write output outside Git to avoid self-SHA commit loops."""
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
if args.output.resolve().is_relative_to(ROOT):raise ValueError('Post-commit proof must stay outside the repository')
commit=subprocess.check_output(['git','rev-parse',args.commit+'^{commit}'],cwd=ROOT,text=True).strip()
auth=json.loads((OUT/'continuation/authorization.json').read_bytes())
session=Path(auth['session_directory'])
prefixes=[OUT.relative_to(ROOT).as_posix(),session.relative_to(ROOT).as_posix(),'code/original/matrix_multiplication.c']
tree=subprocess.check_output(['git','ls-tree','-rz','--full-tree',commit,'--',*prefixes],cwd=ROOT)
reader=subprocess.Popen(['git','cat-file','--batch'],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
changed=[]
count=0
names=set()
try:
    for record in tree.split(b'\0'):
        if not record:continue
        metadata,name=record.split(b'\t',1);oid=metadata.split()[2]
        reader.stdin.write(oid+b'\n');reader.stdin.flush()
        header=reader.stdout.readline().split()
        if len(header)!=3 or header[0]!=oid or header[1]!=b'blob':raise ValueError('Unexpected Git object response')
        data=reader.stdout.read(int(header[2]))
        if reader.stdout.read(1)!=b'\n':raise ValueError('Missing object delimiter')
        name=name.decode('utf-8');names.add(name)
        if hashlib.sha256(data).digest()!=hashlib.sha256((ROOT/name).read_bytes()).digest():changed.append(name)
        count+=1
finally:
    reader.stdin.close();reader.wait(timeout=10)
source_diff=subprocess.check_output(['git','diff','--name-only',auth['auxiliary_content_commit'],commit,'--','code','autotuner','configs','scripts','tests'],cwd=ROOT,text=True)
local_names={p.relative_to(ROOT).as_posix() for folder in (OUT,session) for p in folder.rglob('*') if p.is_file()}
missing=sorted(local_names-names)
result=dict(commit=commit,verified_raw_evidence_and_original_files=count,byte_mismatches=changed,
    local_evidence_files=len(local_names),uncommitted_evidence_files=missing,frozen_source_diff=source_diff,
    pass_checks=not changed and not source_diff and not missing,
    verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result));raise SystemExit(0 if result['pass_checks'] else 2)
