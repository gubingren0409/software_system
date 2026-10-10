"""One-shot predeclaration/build and old-state protection; no probe samples."""
import json
import subprocess
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT))
from autotuner.core import sha256_file,sha256_json,utc_now
from scripts.p3_clock_contract import capture,atomic_write_json,load,snapshot_campaign,wsl_path
from scripts.p3_clock_reference import CONDITIONS,CRITERIA,SOURCE_FILES


def run(name,command,timeout=90):
    result=capture(command,HERE,name,HERE.name,timeout=timeout)
    print(json.dumps({'operation':name,'returncode':result['returncode'],'qpc_seconds':result['qpc_seconds']}),flush=True)
    assert result['returncode']==0,name
    return result


def linux(command):
    return ['wsl.exe','-d','Ubuntu-24.04','--cd','/tmp','--','env','-u','PYTHONPATH','PYTHONDONTWRITEBYTECODE=1',*command]


if sys.argv[1]=='before':
    for name,command in (('head_before',['git','rev-parse','HEAD']),('status_before',['git','status','--short']),
                         ('branch_before',['git','branch','--show-current']),('remote_before',['git','remote','-v']),
                         ('ancestor',['git','merge-base','--is-ancestor','50cd24e59d6a99304b604560a057a961d06bfb14','HEAD'])):
        run(name,command)
    helper='credential.helper=/mnt/c/Program'+chr(92)+' Files/Git/mingw64/bin/git-credential-manager.exe'
    run('fetch_github',linux(['env','GIT_DIR=/mnt/e/software_system/course_repo/.git/worktrees/project01',
        'GIT_WORK_TREE=/mnt/e/software_system/project01','timeout','90','git','-c',helper,'fetch','github']),110)
    run('github_branch',['git','rev-parse','github/project01'])
    for name,path in (('d6811cad',ROOT/'evidence/p3_memory_policy/20261010-174802-11f7775c/campaign-d6811cad'),
        ('7405fcc3',ROOT/'evidence/p3_resource_policy/20261010-143415/campaign-7405fcc3'),
        ('e308bfb',ROOT/'evidence/p3/campaign-e308bfb')):
        state=snapshot_campaign(path)
        if name=='d6811cad':
            assert not state['trajectories'] and state['checkpoint']['session_id']=='2c270825458a4857a5ac9df5aadf597b'
        atomic_write_json(HERE/(name+'_before.json'),state)
    protection=[]
    for prefix in ('code/original','evidence/p2','evidence/p3','evidence/p3_clock_repair','evidence/p3_clock_contract',
                   'evidence/p3_resource_policy','evidence/p3_memory_policy'):
        paths=subprocess.check_output(['git','ls-files','--',prefix],cwd=ROOT,text=True).splitlines()
        protection.append({'prefix':prefix,'count':len(paths),'raw_map_sha256':sha256_json({p:sha256_file(ROOT/p) for p in paths})})
    atomic_write_json(HERE/'history_protection_before.json',protection)
elif sys.argv[1]=='declare':
    run('targeted_tests',[sys.executable,'-B','-X','utf8','-m','unittest','discover','-s','tests','-p','test_clock_reference.py','-v'])
    build='/var/tmp/matrix-clock-reference-'+HERE.name
    run('create_build_directory',linux(['mkdir','--',build]))
    source='code/diagnostics/clock_reference_probe.c'
    binary=build+'/clock_reference_probe'
    compile_command=linux(['/usr/bin/gcc','-std=c11','-O2','-Wall','-Wextra','-Werror',wsl_path(ROOT/source),'-o',binary])
    run('compile_native',compile_command)
    run('compiler_version',linux(['/usr/bin/gcc','--version']))
    run('dynamic_symbols',linux(['nm','-D',binary]))
    run('binary_identity',linux(['sha256sum',binary,'/usr/bin/x86_64-linux-gnu-gcc-13']))
    binary_sha=(HERE/'binary_identity.stdout.txt').read_text().split()[0]
    wrapper="import hashlib,os; p="+repr(binary)+"; assert hashlib.sha256(open(p,'rb').read()).hexdigest()=="+repr(binary_sha)+"; os.execv(p,[p])"
    probe_command=linux(['timeout','430','python3','-c',wrapper])
    metadata_command=linux(['python3',wsl_path(ROOT/'scripts/collect_clock_reference_environment.py')])
    manifest={'schema':'clock-reference-diagnostic-manifest-v1','batch_id':HERE.name,'declared_at':utc_now(),
        'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'preparation_source_sha256':sha256_file(Path(__file__)),
        'source_sha256':{p:sha256_file(ROOT/p) for p in SOURCE_FILES},'compile_command':compile_command,
        'binary_sha256':binary_sha,'probe_binary':binary,'probe_command':probe_command,'metadata_command':metadata_command,
        'conditions':CONDITIONS,'criteria':CRITERIA,'criteria_hash':sha256_json(CRITERIA),
        'interval_count':30,'default_path_count':20,'seconds_per_interval':3,'collection_budget_seconds':480,
        'sample_policy':'Save every completed interval and all messages/raw streams with immediate flush; no filtering, replacement or second round',
        'stop_rule':'Collect fixed A/B/C/D once unless IO/process/timeout prevents completion. Default A/B must ALL match bounded host reference. Any wide boundary/backwards/invalid/default mismatch blocks certification. C/D never replace A/B.',
        'decision_table':{'default_mono_all_pass_raw_mismatch':'May propose versioned host-bounded admission; RAW warning; new content/archive/empty session and independent recovery required',
                          'probe_bug':'Minimal correction with before/after evidence, old failures unchanged',
                          'default_mono_mismatch_or_backwards_or_wide':'Stop formal execution and hand off exact evidence'},
        'sleep_is_not_accuracy_reference':True,'no_system_changes':True,'matrix_target_execution_limit_during_diagnostic':0,
        'retained_formal_content':'d6811cadda8ecd7b46225ebe65c51831278694a0','retained_session':'2c270825458a4857a5ac9df5aadf597b'}
    atomic_write_json(HERE/'manifest.json',manifest)
    print(json.dumps({'manifest_sha256':sha256_file(HERE/'manifest.json'),'binary_sha256':binary_sha,'budget_seconds':480}),flush=True)
else: raise ValueError('Unknown phase')
