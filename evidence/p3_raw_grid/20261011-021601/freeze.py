"""Export exact committed content, independently verify both archives and initialize empty Grid."""
import json,os,re,subprocess,sys,tarfile,tempfile,uuid
from pathlib import Path
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[2]; sys.path.insert(0,str(ROOT))
from autotuner.core import sha256_file,sha256_json
from autotuner.session import source_identity
from scripts.p3_clock_contract import capture,load,atomic_write_json,wsl_path


def run(name,command,timeout=240):
    op=capture(command,HERE,name,HERE.name,timeout=timeout)
    print(json.dumps({'operation':name,'returncode':op['returncode'],'qpc_seconds':op['qpc_seconds']}),flush=True)
    if op['returncode']!=0: raise ValueError(name+' failed')
    return op
def linux(command,archive='/tmp'):
    return ['wsl.exe','-d','Ubuntu-24.04','--cd',archive,'--','env','-u','PYTHONPATH','PYTHONDONTWRITEBYTECODE=1',*command]


def export(sha):
    if not re.fullmatch('[0-9a-f]{40}',sha): raise ValueError('Full SHA required')
    run('content_tree',['git','ls-tree','-r',sha,'--','autotuner','scripts','tests','configs','code','.gitattributes'])
    identities={}
    for line in (HERE/'content_tree.stdout.txt').read_text().splitlines():
        info,relative=line.split('\t',1)
        if re.fullmatch(r'(autotuner/.*\.py|scripts/.*\.(py|ps1)|tests/.*\.(py|c|json)|configs/.*\.json|code/(working|diagnostics)/.*\.[ch]|code/original/matrix_multiplication\.c|\.gitattributes)',relative):
            identities[relative]=info.split()[2]
    assert {'autotuner/core.py','autotuner/raw_grid.py','scripts/start_raw_grid.py'}<=identities.keys()
    identity={'content_sha':sha,'files':identities}; atomic_write_json(HERE/'git_identity.json',identity)
    tar=Path(tempfile.gettempdir())/('matrix-raw-grid-'+sha+'.tar')
    windows=Path(tempfile.gettempdir())/('matrix-raw-grid-'+sha)
    archive='/var/tmp/matrix-raw-grid-content-'+sha
    if tar.exists() or windows.exists(): raise ValueError('Export must be new, no stale archive')
    run('archive_content',['git','archive','--format=tar','-o',str(tar),sha])
    windows.mkdir()
    with tarfile.open(tar) as stream: stream.extractall(windows,filter='data')
    run('create_linux_archive',linux(['mkdir','--',archive]))
    run('extract_linux_archive',linux(['tar','-xf',wsl_path(tar),'-C',archive]))
    win_files=source_identity(windows,identities)
    script="import json; from pathlib import Path; from autotuner.session import source_identity; p=Path("+repr(wsl_path(HERE/'git_identity.json'))+"); print(json.dumps(source_identity(Path.cwd(),json.load(p.open())['files'])))"
    run('linux_execution_identity',linux(['python3','-c',script],archive))
    lin_files=load(HERE/'linux_execution_identity.stdout.txt')
    run('compiler_version',linux(['/usr/bin/gcc','--version'],archive))
    run('compiler_identity',linux(['sha256sum','/usr/bin/x86_64-linux-gnu-gcc-13'],archive))
    compiler_sha=(HERE/'compiler_identity.stdout.txt').read_text().split()[0]
    run('allowed_cpus',linux(['python3','-c','import os,json; print(json.dumps(sorted(os.sched_getaffinity(0))))'],archive))
    run('python_wsl_version',linux(['python3','--version'],archive))
    run('python_windows_version',[sys.executable,'--version'])
    run('git_version',['git','--version'])
    run('wsl_version',['wsl.exe','--version'])
    build='/var/tmp/matrix-raw-grid-probe-'+sha
    run('create_probe_build',linux(['mkdir','--',build],archive))
    binary=build+'/probe'
    cmd=['/usr/bin/gcc','-std=c11','-O2','-Wall','-Wextra','-Werror',archive+'/code/diagnostics/clock_fixed_work_probe.c','-o',binary]
    run('compile_probe',linux(cmd,archive))
    run('probe_binary_identity',linux(['sha256sum',binary],archive))
    probe={'content_commit':sha,'compile_command':cmd,'compiler_sha256':compiler_sha,
        'binary':binary,'binary_sha256':(HERE/'probe_binary_identity.stdout.txt').read_text().split()[0],
        'source_sha256':lin_files['code/diagnostics/clock_fixed_work_probe.c']['executed_sha256'],
        'source_path':archive+'/code/diagnostics/clock_fixed_work_probe.c',
        'compile_operation_sha256':sha256_file(HERE/'compile_probe.operation.json')}
    atomic_write_json(HERE/'probe_build.json',probe)
    protocol=load(windows/'configs/measurement_protocol.json')
    plan={'schema':'raw-grid-plan-v1','content_commit':sha,'session_id':uuid.uuid4().hex,
        'archive_directory':archive,'windows_archive_directory':str(windows),
        'git_identity':str(HERE/'git_identity.json'),'git_identity_sha256':sha256_file(HERE/'git_identity.json'),
        'windows_source_identity':win_files,'linux_source_identity':lin_files,
        'cache_directory':'/var/tmp/matrix-raw-grid-cache-'+sha,
        'measurement_protocol_hash':sha256_json(protocol),'timing_protocol_hash':protocol['timing_protocol']['hash'],
        'probe_build_manifest':str(HERE/'probe_build.json'),'compiler_sha256':compiler_sha,
        'allowed_cpus':load(HERE/'allowed_cpus.stdout.txt'),
        'recovery_directory':str(HERE/'recovery'),'source_archive_tar_sha256':sha256_file(tar)}
    plan['session_directory']=str(HERE/('grid-'+plan['session_id'][:8]))
    atomic_write_json(HERE/'plan.json',plan)
    print(json.dumps({k:plan[k] for k in ('content_commit','session_id','archive_directory','session_directory')}),flush=True)


def validate():
    plan=load(HERE/'plan.json'); windows=Path(plan['windows_archive_directory']); archive=plan['archive_directory']
    for name,command in (
       ('clean_windows_regressions',[sys.executable,'-B','-X','utf8',str(windows/'scripts/verify_raw_grid_code.py')]),
       ('clean_wsl_regressions',linux(['python3','scripts/verify_raw_grid_code.py'],archive)),
       ('clean_cli_help',linux(['python3','-m','autotuner','--help'],archive)),
       ('clean_raw_grid_help',[sys.executable,'-B','-X','utf8',str(windows/'scripts/start_raw_grid.py'),'--help']),
       ('clean_list_configs',linux(['python3','-m','autotuner','list-configs'],archive))): run(name,command)
    configs=load(HERE/'clean_list_configs.stdout.txt'); assert len(configs)==20 and len({tuple(sorted(c.items())) for c in configs})==20
    isolation="import os,pathlib,json; print(json.dumps({'git_absent':not pathlib.Path('.git').exists(),'pycache_count':len(list(pathlib.Path('.').rglob('__pycache__'))),'pythonpath_present':'PYTHONPATH' in os.environ}))"
    run('clean_isolation',linux(['python3','-c',isolation],archive))
    isolated=load(HERE/'clean_isolation.stdout.txt'); assert isolated=={'git_absent':True,'pycache_count':0,'pythonpath_present':False}
    # One explicit n17 fresh diagnostic, separate from session and all 4096 counts.
    target=load(windows/'configs/target.json')
    for key in ('candidate_source','reference_source'): target[key]=archive+'/code/working/'+Path(target[key]).name
    target['shared_sources']=[archive+'/code/working/matrix_input.h']
    target['timing_protocol']['file']=archive+'/configs/raw_formal_timing_protocol.json'
    target['cache_root']='/var/tmp/matrix-raw-grid-n17-cache-'+plan['content_commit']
    run('small_cache_initially_absent',linux(['test','!','-e',target['cache_root']],archive))
    atomic_write_json(HERE/'n17_target.json',target)
    command=linux(['python3','-m','autotuner','--target',wsl_path(HERE/'n17_target.json'),'--evidence-root',wsl_path(HERE/'n17'),
        'evaluate','--size','17','--optimization','O2','--block-size','8','--seed','20261008','--input','random',
        '--timeout','30','--label','raw_formal_n17_diagnostic','--protocol-hash',plan['measurement_protocol_hash']],archive)
    run('clean_n17_fresh',command)
    from autotuner.core import classify_execution
    sample=load(HERE/'clean_n17_fresh.stdout.txt')
    assert sample['classification']=='success' and sample['source']=='fresh_measurement' and sample['context']['force_remeasure'] is True
    assert classify_execution(sample['returncode'],sample['timed_out'],sample['raw_stdout'],'matrix-multiplication-result-v2')[0]=='success'
    assert sample['target_result']['checked_entries']==289
    command=[sys.executable,'-B','-X','utf8',str(windows/'scripts/start_raw_grid.py'),'--plan',str(HERE/'plan.json'),'initialize']
    run('initialize_empty_grid',command)
    initial=load(Path(plan['session_directory'])/'initial_checkpoint.json')
    assert initial['completed']==[] and initial['active'] is None and initial['target_executions']==0 and initial['reference_generation_calls']==0
    atomic_write_json(HERE/'clean_validation.json',{'content_commit':plan['content_commit'],'source_archive_tar_sha256':plan['source_archive_tar_sha256'],
        'isolated':isolated,'configuration_count':len(configs),'small_diagnostic_target_executions':1,
        'small_diagnostic_run_id':sample['run_id'],'small_correctness_pass':True,'checked_entries':289,
        'small_reference_generator_calls':1,
        'small_raw_result':sample['target_result'],'formal_target_executions':0,'session_initialization_pass':True,
        'session_id':plan['session_id'],'initial_checkpoint_sha256':sha256_file(Path(plan['session_directory'])/'initial_checkpoint.json')})


if __name__=='__main__':
    # A superseded preflight export is preserved, never overwritten by a new content freeze.
    if sys.argv[1]=='export' and len(sys.argv)>3: HERE=Path(sys.argv[3]).resolve()
    elif sys.argv[1]=='validate' and len(sys.argv)>2: HERE=Path(sys.argv[2]).resolve()
    HERE.mkdir(parents=True,exist_ok=True)
    if sys.argv[1]=='export': export(sys.argv[2])
    elif sys.argv[1]=='validate': validate()
    else: raise ValueError('Unknown action')
