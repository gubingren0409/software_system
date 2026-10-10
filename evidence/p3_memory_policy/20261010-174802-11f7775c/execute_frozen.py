"""One authorized memory-policy recovery, conditionally one first-seed batch."""
import json
import subprocess
import sys
import uuid
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT))
from autotuner.core import sha256_file,utc_now
from scripts.p3_clock_contract import atomic_write_json,load,wsl_path,capture


def run(name,command,timeout=120):
    result=capture(command,HERE,name,HERE.name,timeout=timeout)
    print(json.dumps({'operation':name,'returncode':result['returncode'],'qpc_seconds':result['qpc_seconds']}),flush=True)
    return result


def linux(directory,command):
    return ['wsl.exe','-d','Ubuntu-24.04','--cd',directory,'--','env','-u','PYTHONPATH','PYTHONDONTWRITEBYTECODE=1',*command]


def entry(plan,mode):
    args=[sys.executable,'-X','utf8','scripts/start_p3_first_seed.py','--mode',mode]
    for flag,key in (('--content-sha','content_commit'),('--auxiliary-sha','content_commit'),
            ('--archive-directory','archive_directory'),('--campaign-directory','campaign_directory'),
            ('--git-identity','git_identity'),('--session-id','session_id')):
        args.extend([flag,plan[key]])
    args.extend(['--output',plan['recovery_directory'] if mode=='recover' else plan['resume_directory']])
    if mode=='resume': args.extend(['--recovery-directory',plan['recovery_directory']])
    return args


phase=sys.argv[1]
if phase=='freeze':
    content=sys.argv[2]
    assert subprocess.check_output(['git','rev-parse',content],cwd=ROOT,text=True).strip()==content
    archive='/var/tmp/matrix-autotuner-p3-memory-content-'+content
    campaign=HERE/('campaign-'+content[:8])
    tree=subprocess.check_output(['git','ls-tree','-r','--format=%(objectname)%x09%(path)',content,'--','autotuner','code','configs','scripts'],cwd=ROOT,text=True)
    files={path:blob for blob,path in (line.split('\t',1) for line in tree.splitlines())
           if (path.startswith(('autotuner/','configs/','scripts/','code/working/')) and path.endswith(('.py','.json','.ps1','.sh','.c','.h')))
           or path=='code/original/matrix_multiplication.c'}
    identity=HERE/'git_identity.json'
    atomic_write_json(identity,{'content_sha':content,'files':files})
    tar_path=ROOT/'build'/('memory-content-'+content+'.tar')
    tar_path.parent.mkdir(parents=True,exist_ok=True)
    assert run('git_archive',['git','archive','--format=tar','-o',str(tar_path),content,'--','autotuner','code','configs','scripts','tests',
        'evidence/p3/campaign-e308bfb/protocol.json','evidence/p3/campaign-e308bfb/campaign_protocol.json'])['returncode']==0
    assert run('create_clean_archive',linux('/tmp',['mkdir','--',archive]))['returncode']==0
    assert run('extract_clean_archive',linux('/tmp',['tar','-xf',wsl_path(tar_path),'-C',archive]))['returncode']==0
    output=HERE/'clean'
    assert run('clean_validation',linux(archive,['python3',wsl_path(HERE/'clean_validate.py'),archive,wsl_path(identity),wsl_path(output)]),timeout=240)['returncode']==0
    session=uuid.uuid4().hex
    command=linux(archive,['python3','-m','autotuner','campaign','--content-sha',content,'--git-identity',wsl_path(identity),
        '--campaign-directory',wsl_path(campaign),'--session-id',session,'--initialize-only','--trajectory-limit','2'])
    assert run('initialize_new_session',command,timeout=90)['returncode']==0
    plan={'declared_at':utc_now(),'content_commit':content,'session_id':session,'archive_directory':archive,
          'campaign_directory':str(campaign),'git_identity':str(identity),'git_identity_sha256':sha256_file(identity),
          'recovery_directory':str(HERE/'recovery'),'resume_directory':str(HERE/'resume'),
          'orchestration_sha256':sha256_file(Path(__file__)),'recovery_limit':1,'trajectory_limit':2,
          'old_observations_imported':False,'runtime_file_count':len(files)}
    atomic_write_json(HERE/'session_plan.json',plan)
    print(json.dumps(plan))
elif phase in ('recover','resume'):
    plan=load(HERE/'session_plan.json')
    if phase=='resume':
        review=load(HERE/'independent_recovery.json')
        assert review['evidence_integrity_pass'] is True and review['timing_checks_pass'] is True
        assert review['clock_recovery_reevaluation']['recovery_eligible'] is True
    result=run(phase+'_entry',entry(plan,phase),timeout=480 if phase=='recover' else None)
    raise SystemExit(result['returncode'] if type(result['returncode']) is int else 1)
elif phase in ('audit-recover','audit-resume'):
    plan=load(HERE/'session_plan.json'); mode=phase.removeprefix('audit-')
    name='independent_recovery' if mode=='recover' else 'independent_resume'
    command=[sys.executable,'-B','-X','utf8','scripts/audit_p3_first_seed.py','--batch',plan['recovery_directory'] if mode=='recover' else plan['resume_directory'],
             '--output',str(HERE/(name+'.json')),'--require-two']
    if mode=='resume': command.extend(['--clock-recovery',plan['recovery_directory']])
    result=run(name,command,timeout=240)
    raise SystemExit(result['returncode'] if type(result['returncode']) is int else 1)
elif phase=='git-fetch':
    helper='credential.helper=/mnt/c/Program'+chr(92)+' Files/Git/mingw64/bin/git-credential-manager.exe'
    command=['wsl.exe','-d','Ubuntu-24.04','--cd','/tmp','--','env',
        'GIT_DIR=/mnt/e/software_system/course_repo/.git/worktrees/project01',
        'GIT_WORK_TREE=/mnt/e/software_system/project01','timeout','90','git','-c',helper,'fetch','github']
    result=run('github_fetch',command,timeout=110)
    raise SystemExit(result['returncode'] if type(result['returncode']) is int else 1)
else:
    raise ValueError('Unknown phase')
