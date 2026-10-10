"""Preserve history, select CPU before data, compile and declare one diagnostic."""
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT))
from autotuner.core import sha256_file,sha256_json,utc_now
from scripts.p3_clock_contract import capture,atomic_write_json,load,snapshot_campaign,wsl_path


def linux(command):
    return ['wsl.exe','-d','Ubuntu-24.04','--cd','/tmp','--','env','-u','PYTHONPATH','PYTHONDONTWRITEBYTECODE=1',*command]


def run(name,command,timeout=90):
    result=capture(command,HERE,name,HERE.name,timeout=timeout)
    print(json.dumps({'operation':name,'returncode':result['returncode'],'qpc_seconds':result['qpc_seconds']}),flush=True)
    assert result['returncode']==0,name
    return result


if sys.argv[1]=='before':
    for name,command in (('head_before',['git','rev-parse','HEAD']),('status_before',['git','status','--short']),
        ('branch_before',['git','branch','--show-current']),('remote_before',['git','remote','-v']),
        ('ancestor',['git','merge-base','--is-ancestor','da0afd87bbfe594fa69ca98ddfdcc048c2de4770','HEAD'])):
        run(name,command)
    helper='credential.helper=/mnt/c/Program'+chr(92)+' Files/Git/mingw64/bin/git-credential-manager.exe'
    run('fetch_github',linux(['env','GIT_DIR=/mnt/e/software_system/course_repo/.git/worktrees/project01',
        'GIT_WORK_TREE=/mnt/e/software_system/project01','timeout','90','git','-c',helper,'fetch','github']),110)
    run('github_branch',['git','rev-parse','github/project01'])
    run('allowed_cpus',linux(['python3','-c','import os,json; print(json.dumps(sorted(os.sched_getaffinity(0))))']))
    allowed=load(HERE/'allowed_cpus.stdout.txt')
    assert allowed and all(type(cpu) is int and cpu>=0 for cpu in allowed)
    atomic_write_json(HERE/'cpu_selection.json',{'allowed_cpus':allowed,'selected_cpu':17 if 17 in allowed else allowed[0],
        'reason':'Requested CPU17 is allowed' if 17 in allowed else 'CPU17 unavailable; select first allowed CPU before sampling',
        'selected_at':utc_now(),'no_posthoc_changes':True})
    for name,path in (('d6811cad',ROOT/'evidence/p3_memory_policy/20261010-174802-11f7775c/campaign-d6811cad'),
        ('7405fcc3',ROOT/'evidence/p3_resource_policy/20261010-143415/campaign-7405fcc3'),
        ('e308bfb',ROOT/'evidence/p3/campaign-e308bfb')):
        atomic_write_json(HERE/(name+'_before.json'),snapshot_campaign(path))
    protection=[]
    for prefix in ('code/original','evidence/p2','evidence/p3','evidence/p3_clock_repair','evidence/p3_clock_contract',
                   'evidence/p3_resource_policy','evidence/p3_memory_policy','evidence/p3_clock_reference'):
        paths=subprocess.check_output(['git','ls-files','--',prefix],cwd=ROOT,text=True).splitlines()
        protection.append({'prefix':prefix,'count':len(paths),'raw_map_sha256':sha256_json({p:sha256_file(ROOT/p) for p in paths})})
    atomic_write_json(HERE/'history_protection_before.json',protection)
elif sys.argv[1]=='declare':
    from scripts.p3_fixed_work_clock import CRITERIA,SOURCE_FILES,schedule
    run('targeted_tests',[sys.executable,'-B','-X','utf8','-m','unittest','discover','-s','tests','-p','test_fixed_work_clock.py','-v'])
    build='/var/tmp/matrix-fixed-work-clock-'+HERE.name
    run('create_build_directory',linux(['mkdir','--',build]))
    binary=build+'/fixed_work_probe'
    command=linux(['/usr/bin/gcc','-std=c11','-O2','-Wall','-Wextra','-Werror',
        wsl_path(ROOT/'code/diagnostics/clock_fixed_work_probe.c'),'-o',binary])
    run('compile_native',command)
    run('compiler_version',linux(['/usr/bin/gcc','--version']))
    run('binary_identity',linux(['sha256sum',binary,'/usr/bin/x86_64-linux-gnu-gcc-13']))
    sha=(HERE/'binary_identity.stdout.txt').read_text().split()[0]
    wrapper="import hashlib,os; p="+repr(binary)+"; assert hashlib.sha256(open(p,'rb').read()).hexdigest()=="+repr(sha)+"; os.execv(p,[p])"
    selection=load(HERE/'cpu_selection.json')
    manifest={'schema':'fixed-work-clock-manifest-v1','batch_id':HERE.name,'declared_at':utc_now(),
        'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'source_sha256':{p:sha256_file(ROOT/p) for p in SOURCE_FILES},
        'cpu_selection':selection,'cpu_selection_sha256':sha256_file(HERE/'cpu_selection.json'),
        'criteria':CRITERIA,'criteria_hash':sha256_json(CRITERIA),'schedule':schedule(selection['selected_cpu']),
        'compile_command':command,'binary_sha256':sha,'probe_binary':binary,
        'probe_command':linux(['timeout','470','python3','-c',wrapper]),
        'metadata_command':linux(['python3',wsl_path(ROOT/'scripts/collect_clock_reference_environment.py')]),
        'collection_budget_seconds':480,'interval_count':22,'short_updates':1000000000,'long_updates':10000000000,
        'stop_rule':'One fixed round only; flush every record. IO/timeout stops and preserves partial data. Any incomplete, indeterminate, rollback or RAW failure prevents candidate. No replacement/filter/calibration/recovery/formal targets.',
        'decision_table':{'all_22_raw_pass':'May implement RAW candidate; not a formal timing certificate',
            'otherwise':'P3_CLOCK_BLOCKED; no candidate and no additional diagnostic round'},
        'formal_content_commit':'d6811cadda8ecd7b46225ebe65c51831278694a0',
        'formal_session_id':'2c270825458a4857a5ac9df5aadf597b','formal_target_execution_limit':0,
        'recovery_limit':0,'system_settings_modified':False}
    atomic_write_json(HERE/'manifest.json',manifest)
    print(json.dumps({'manifest_sha256':sha256_file(HERE/'manifest.json'),'binary_sha256':sha,'intervals':22}),flush=True)
else: raise ValueError('Unknown phase')
