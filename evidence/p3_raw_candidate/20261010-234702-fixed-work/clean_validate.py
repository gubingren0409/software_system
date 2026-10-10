"""Export the exact frozen commit, then verify only this RAW candidate and n=17."""
import json,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from autotuner.core import sha256_file,sha256_json
from scripts.p3_clock_contract import atomic_write_json,capture,load,wsl_path


def linux(command,cd='/tmp'):
    return ['wsl.exe','-d','Ubuntu-24.04','--cd',cd,'--','env','-u','PYTHONPATH','PYTHONDONTWRITEBYTECODE=1',*command]


def run(name,command,timeout=120):
    result=capture(command,HERE,name,HERE.name,timeout=timeout)
    print(json.dumps({'operation':name,'returncode':result['returncode'],'qpc_seconds':result['qpc_seconds']}),flush=True)
    if result['returncode']!=0: raise RuntimeError(name+' failed; do not claim candidate ready')
    return result


if sys.argv[1]=='prepare':
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    archive='/var/tmp/matrix-raw-candidate-'+commit
    cache='/var/tmp/matrix-raw-candidate-cache-'+commit
    windows=Path(tempfile.gettempdir())/('matrix-raw-candidate-'+commit)
    tar=Path(tempfile.gettempdir())/('matrix-raw-candidate-'+commit+'.tar')
    if windows.exists() or tar.exists(): raise ValueError('No existing clean destination allowed')
    tree=subprocess.check_output(['git','ls-tree','-r','--format=%(objectname)%x09%(path)',commit,'--',
        'autotuner','configs','code','scripts','tests','.gitattributes'],cwd=ROOT,text=True)
    files={p:b for b,p in (line.split('\t',1) for line in tree.splitlines())}
    assert 'autotuner/core.py' in files and 'autotuner/timing.py' in files
    atomic_write_json(HERE/'candidate_git_identity.json',{'content_sha':commit,'files':files})
    run('candidate_archive',['git','archive','--format=tar','--output',str(tar),commit])
    windows.mkdir()
    run('candidate_windows_extract',['tar','-xf',str(tar),'-C',str(windows)])
    run('candidate_linux_empty_directories',linux(['mkdir','--',archive,cache]))
    run('candidate_linux_extract',linux(['tar','-xf',wsl_path(tar),'-C',archive]))
    data=load(ROOT/'configs/target.json')
    data.update(candidate_source=archive+'/code/working/matrix_multiplication.c',
        reference_source=archive+'/code/working/reference_generator.c',shared_sources=[archive+'/code/working/matrix_input.h'],
        cache_root=cache)
    data['timing_protocol']['file']=archive+'/configs/raw_timing_protocol.json'
    atomic_write_json(HERE/'candidate_target.json',data)
    atomic_write_json(HERE/'clean_plan.json',{'content_commit':commit,'archive_directory':archive,
        'windows_archive_directory':str(windows),'tar_sha256':sha256_file(tar),'cache_directory':cache,
        'cache_initially_empty':True,'evidence_directory':str(HERE/'small_evaluation'),
        'target_config_sha256':sha256_file(HERE/'candidate_target.json'),
        'git_identity_sha256':sha256_file(HERE/'candidate_git_identity.json'),
        'measurement_protocol_hash':sha256_json(load(ROOT/'configs/measurement_protocol.json')),
        'matrix_executions_requested':1,'matrix_n':17,'formal_executions_requested':0,
        'validation_scope':'No .git, PYTHONPATH or preexisting pycache/cache; candidate-only, not recovery or a formal score'})
elif sys.argv[1]=='run':
    plan=load(HERE/'clean_plan.json'); archive=plan['archive_directory']
    run('clean_tools',linux(['python3','--version']))
    run('clean_cli_help',linux(['python3','-B','-X','utf8','-m','autotuner','--help'],archive))
    run('clean_configs',linux(['python3','-B','-X','utf8','-m','autotuner','list-configs'],archive))
    configs=load(HERE/'clean_configs.stdout.txt')
    assert len(configs)==len({(c['optimization'],c['block_size']) for c in configs})==20
    run('clean_tests_wsl',linux(['python3','-B','-X','utf8','scripts/verify_raw_candidate_code.py'],archive))
    run('clean_tests_windows',[sys.executable,'-B','-X','utf8',str(Path(plan['windows_archive_directory'])/'scripts/verify_raw_candidate_code.py')])
    clean_check="from pathlib import Path; import os; assert not Path('.git').exists(); assert not list(Path('.').rglob('__pycache__')); assert 'PYTHONPATH' not in os.environ; print('clean archive has no Git metadata, pycache or PYTHONPATH')"
    run('clean_isolation',linux(['python3','-B','-c',clean_check],archive))
    run('clean_n17_evaluate',linux(['python3','-B','-X','utf8','-m','autotuner','--target',wsl_path(HERE/'candidate_target.json'),
        '--evidence-root',wsl_path(HERE/'small_evaluation'),'evaluate','--size','17','--optimization','O2',
        '--block-size','8','--seed','20261008','--input','random','--timeout','30','--label','raw-candidate-n17',
        '--protocol-hash',plan['measurement_protocol_hash']],archive),90)
    results=list((HERE/'small_evaluation/runs').glob('*/result.json')); assert len(results)==1
    result=load(results[0]); assert result['source']=='fresh_measurement' and result['classification']=='success'
    run('clean_n17_independent_audit',linux(['python3','-B','-X','utf8','scripts/audit_raw_candidate.py',
        '--result',wsl_path(results[0]),'--target',wsl_path(HERE/'candidate_target.json'),
        '--git-identity',wsl_path(HERE/'candidate_git_identity.json'),'--output',wsl_path(HERE/'candidate_validation.json')],archive))
    # Copy only small JSON manifests, never binary/reference/performance cache data.
    copy_code="import json,shutil;from pathlib import Path;p=Path("+repr(plan['cache_directory'])+");out=Path("+repr(wsl_path(HERE/'cache_manifests'))+");out.mkdir();files=list(p.glob('build/*/manifest.json'))+list(p.glob('reference/*/manifest.json'));[(shutil.copyfile(f,out/(f.parent.name+'.json'))) for f in files];print(json.dumps([str(f) for f in files]))"
    run('clean_cache_manifests',linux(['python3','-B','-c',copy_code],archive))
    atomic_write_json(HERE/'clean_validation.json',{'candidate_validation_pass':True,'content_commit':plan['content_commit'],
        'archive_directory':archive,'windows_archive_directory':plan['windows_archive_directory'],
        'unique_configuration_count':20,'small_matrix_execution_count':1,'small_matrix_n':17,'checked_entries':289,
        'fresh_measurement':True,'recovery_count':0,'formal_gate_count':0,'formal_4096_execution_count':0,
        'execution_complete':False,'timing_checks_pass':False,'comparison_ready':False,
        'validation_sha256':sha256_file(HERE/'candidate_validation.json'),'plan_sha256':sha256_file(HERE/'clean_plan.json')})
else: raise ValueError('Unknown phase')
