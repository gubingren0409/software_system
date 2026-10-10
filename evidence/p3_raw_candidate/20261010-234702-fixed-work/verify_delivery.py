"""Final read-only artifact/source/link checks; does not collect any new clock sample."""
import hashlib,json,os,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from autotuner.core import sha256_file,sha256_json
from scripts.p3_clock_contract import load,atomic_write_json
from autotuner.session import source_identity

summary=load(HERE/'delivery_summary.json'); identity=load(HERE/'candidate_runtime_git_identity.json')
assert summary['candidate_content_commit']==identity['content_sha']
tree=subprocess.check_output(['git','ls-tree','-r','--format=%(objectname)%x09%(path)',identity['content_sha']],cwd=ROOT,text=True)
git_files={p:b for b,p in (line.split('\t',1) for line in tree.splitlines())}
assert all(git_files[p]==b for p,b in identity['files'].items())
actual=source_identity(ROOT,identity['files'])
validation=load(HERE/'candidate_validation.json')
assert set(actual)==set(validation['source_identity'])
for p,value in actual.items():
    assert value['git_content_sha256']==validation['source_identity'][p]['git_content_sha256']
    if p.startswith('code/original/'):
        assert value['executed_sha256']==validation['source_identity'][p]['executed_sha256']
campaign=load(ROOT/'configs/p3_campaign_protocol.json'); measurement=load(ROOT/'configs/measurement_protocol.json')
assert campaign['measurement_protocol_hash']==sha256_json(measurement)
assert campaign['timing_protocol']==measurement['timing_protocol']
assert all(sha256_file(ROOT/p)==h for p,h in campaign['unchanged_source_sha256'].items())
active_self=[]
for path in HERE.glob('*.operation.json'):
    operation=load(path)
    if operation['returncode']=='unknown':
        # capture writes the current child's operation before it finishes. Do not
        # certify this still-open stream, and never excuse another unknown exit.
        assert operation['pid']==os.getpid() and operation['operation_kind'].startswith('delivery_verification')
        active_self.append(path.name)
        continue
    for stream in ('stdout','stderr'):
        assert sha256_file(HERE/operation[stream+'_path'])==operation[stream+'_sha256']
checked_links=0
for name in ('README.md','report.md','docs/P3_RAW_CLOCK_CANDIDATE.md','docs/P3_FIRST_SEED_STATUS.md',
             'docs/P3_CLOCK_CONTRACT.md','docs/AUDIT_HANDOFF.md'):
    path=ROOT/name
    for target in re.findall(r'\]\(([^)\n]+)\)',path.read_text(encoding='utf-8')):
        if '://' in target or target.startswith('#') or '<' in target: continue
        target=target.split('#',1)[0]
        if not target: continue
        assert (path.parent/target).exists(),name+': '+target
        checked_links+=1
assert summary['formal_4096_execution_count']==summary['recovery_interval_count']==0
assert summary['evidence_integrity_pass'] and not any(summary[k] for k in ('execution_complete','timing_checks_pass','comparison_ready'))
operations={path.name:load(path) for path in HERE.glob('*.operation.json')}
assert operations['collection.operation.json']['returncode']==0
assert operations['clean_n17_independent_audit.operation.json']['returncode']==1
assert operations['clean_n17_independent_audit_corrected_identity.operation.json']['returncode']==0
result={'pass':True,'candidate_content_commit':identity['content_sha'],'current_source_identity':actual,
    'runtime_identity_sha256':sha256_file(HERE/'candidate_runtime_git_identity.json'),
    'original_rejected_identity_sha256':sha256_file(HERE/'candidate_git_identity.json'),
    'git_identity_selection_correction_sha256':sha256_file(HERE/'identity_selection_correction.json'),
    'small_matrix_execution_count':len(list((HERE/'small_evaluation/runs').glob('*/result.json'))),
    'source_git_content_equal':True,'teacher_c_runtime_bytes_equal':True,
    'checked_relative_links':checked_links,'raw_streams_match_recorded_hashes':True,
    'current_capture_not_yet_closed':active_self,
    'runtime_files_committed':True,'helper_sha256':sha256_file(Path(__file__))}
assert result['small_matrix_execution_count']==1
atomic_write_json(HERE/'delivery_verification.json',result)
print(json.dumps({k:v for k,v in result.items() if k!='current_source_identity'},sort_keys=True))
