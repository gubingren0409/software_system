"""Task-local operations and immutable history protection; no target in snapshot."""
import json,os,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT))
from autotuner.core import sha256_file,sha256_json,utc_now
from scripts.p3_clock_contract import atomic_write_json,capture,load,snapshot_campaign

PREFIXES=('code/original','evidence/p0','evidence/p1','evidence/p1_revision1','evidence/p2','evidence/p3',
 'evidence/p3_clock_repair','evidence/p3_clock_contract','evidence/p3_resource_policy',
 'evidence/p3_memory_policy','evidence/p3_clock_reference','evidence/p3_raw_candidate')
def hashes():
    files=[]
    for prefix in PREFIXES:
        files+=subprocess.check_output(['git','ls-files','--',prefix],cwd=ROOT,text=True).splitlines()
    return {p:sha256_file(ROOT/p) for p in files}
def run(name,command,timeout=180):
    op=capture(command,HERE,name,HERE.name,timeout=timeout)
    print(json.dumps({'name':name,'returncode':op['returncode'],'qpc_seconds':op['qpc_seconds']}),flush=True)
    return op
def before():
    for name,args in (('head_before',['rev-parse','HEAD']),('status_before',['status','--porcelain=v1']),
       ('branch_before',['branch','--show-current']),('remotes_before',['remote','-v']),
       ('ancestry',['merge-base','--is-ancestor','3755c4a9d1c387e891fdcc89151250020895370a','HEAD'])):
        assert run(name,['git',*args])['returncode']==0
    atomic_write_json(HERE/'history_before.json',{'captured_at':utc_now(),'files':hashes()})
    for name,path in (('d6811cad','evidence/p3_memory_policy/20261010-174802-11f7775c/campaign-d6811cad'),
      ('7405fcc3','evidence/p3_resource_policy/20261010-143415/campaign-7405fcc3'),
      ('e308bfb','evidence/p3/campaign-e308bfb')):
        atomic_write_json(HERE/(name+'_before.json'),snapshot_campaign(ROOT/path))
    command=['wsl.exe','-d','Ubuntu-24.04','--','python3','-c',
     "import pathlib,hashlib,json; r=pathlib.Path('/var/tmp/matrix-autotuner-p3-memory-content-d6811cadda8ecd7b46225ebe65c51831278694a0'); print(json.dumps({str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in r.rglob('*') if p.is_file() and '__pycache__' not in str(p) and p.parts[len(r.parts)] in ('autotuner','code','configs','scripts')}))"]
    assert run('d681_archive_before',command)['returncode']==0
def after():
    old=load(HERE/'history_before.json')['files']; changed=[p for p,h in old.items() if sha256_file(ROOT/p)!=h]
    result={'captured_at':utc_now(),'protected_file_count':len(old),'changed':changed,'history_byte_protection_pass':not changed}
    atomic_write_json(HERE/'history_protection.json',result); print(json.dumps(result)); assert not changed
if __name__=='__main__':
    if sys.argv[1]=='before': before()
    elif sys.argv[1]=='after': after()
    else: raise ValueError('Unknown phase')
