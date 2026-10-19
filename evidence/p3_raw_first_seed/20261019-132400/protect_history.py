"""Record/verify immutable historical evidence; never invokes an experiment."""
import argparse
import hashlib
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent; ROOT=OUT.parents[2]
def digest(path):
    with path.open('rb') as source:
        result=hashlib.sha256()
        for block in iter(lambda:source.read(1024*1024),b''): result.update(block)
    return result.hexdigest()

parser=argparse.ArgumentParser();parser.add_argument('mode',choices=('before','after'));args=parser.parse_args()
path=OUT/'history_before.json'
if args.mode=='before':
    if path.exists(): raise SystemExit('Never overwrite the original protection map')
    files={p.relative_to(ROOT).as_posix():digest(p) for p in (ROOT/'evidence').rglob('*') if p.is_file() and not p.is_relative_to(OUT)}
    value=dict(baseline_commit='efb7f9df9c25dd509e207d67e08d4180c3e779ac',protected_files=files)
    path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(protected_files=len(files),protection_map_sha256=digest(path))))
else:
    before=json.loads(path.read_bytes());errors=[name for name,h in before['protected_files'].items() if not (ROOT/name).is_file() or digest(ROOT/name)!=h]
    value=dict(history_integrity_pass=not errors,protected_files=len(before['protected_files']),changed_files=errors,protection_map_sha256=digest(path))
    (OUT/'history_after.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(value));raise SystemExit(0 if not errors else 2)
