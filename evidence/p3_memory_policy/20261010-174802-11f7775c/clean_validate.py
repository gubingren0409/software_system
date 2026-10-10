"""Small, committed-archive validation only; never run Grid or n=4096 here."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT, IDENTITY, OUTPUT = map(Path, sys.argv[1:4])
sys.path.insert(0, str(ROOT))
from autotuner.core import sha256_file, utc_now
from autotuner.session import source_identity
from scripts.p3_clock_contract import atomic_write_json, load

assert not (ROOT / '.git').exists() and not list(ROOT.rglob('__pycache__'))
identity = load(IDENTITY)
files = source_identity(ROOT, identity['files'])
atomic_write_json(OUTPUT / 'executed_source_identity.json', files)
commands = []
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
env.pop('PYTHONPATH', None)


def run(command):
    index = len(commands)
    started = time.monotonic()
    captured = utc_now()
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, timeout=180, check=False)
    stdout, stderr = OUTPUT / f'{index:02d}.stdout.txt', OUTPUT / f'{index:02d}.stderr.txt'
    stdout.parent.mkdir(parents=True, exist_ok=True)
    stdout.write_bytes(result.stdout); stderr.write_bytes(result.stderr)
    commands.append({'command':command, 'cwd':str(ROOT), 'captured_at':captured,
        'returncode':result.returncode,'process_wall_seconds':time.monotonic()-started,
        'stdout':stdout.name,'stderr':stderr.name,'stdout_sha256':sha256_file(stdout),'stderr_sha256':sha256_file(stderr)})
    atomic_write_json(OUTPUT / 'commands.json', commands)
    assert result.returncode == 0, command
    return result.stdout.decode('utf-8')


run([sys.executable,'--version']); run(['/usr/bin/gcc','--version'])
run([sys.executable,'-m','autotuner','--help'])
configs=json.loads(run([sys.executable,'-m','autotuner','list-configs']))
assert len(configs)==20 and len({tuple(sorted(item.items())) for item in configs})==20
for pattern in ('test_resource_policy.py','test_campaign.py','test_campaign_costs.py'):
    run([sys.executable,'-m','unittest','discover','-s','tests','-p',pattern,'-v'])
cache=Path('/var/tmp')/('matrix-autotuner-memory-n17-'+identity['content_sha'])
assert not cache.exists(), 'n17 validation requires an empty isolated cache'
target=load(ROOT/'configs/target.json')
target.update(candidate_source=str(ROOT/'code/working/matrix_multiplication.c'),
              reference_source=str(ROOT/'code/working/reference_generator.c'),
              shared_sources=[str(ROOT/'code/working/matrix_input.h')],cache_root=str(cache))
atomic_write_json(OUTPUT/'target.json',target)
n17=json.loads(run([sys.executable,'-m','autotuner','--target',str(OUTPUT/'target.json'),
    '--evidence-root',str(OUTPUT/'n17'),'evaluate','--size','17','--optimization','O2','--block-size','8',
    '--seed','20261008','--input','random','--timeout','30','--label','memory-policy-clean-n17',
    '--min-wsl-available-bytes','268435456']))
assert n17['classification']=='success' and n17['source']=='fresh_measurement'
assert n17['target_result']['checked_entries']==289
atomic_write_json(OUTPUT/'summary.json',{'status':'PASS','content_commit':identity['content_sha'],
    'executed_validator_sha256':sha256_file(Path(__file__)), 'command_count':len(commands),
    'runtime_file_count':len(files),'unique_configurations':20,'n17_source':n17['source'],
    'n17_classification':n17['classification'],'checked_entries':289,
    'no_grid_or_formal_target_executed':True,'cache':str(cache),'scope':'Archive correctness/entry/regressions only, not performance evidence'})
print(json.dumps({'status':'PASS','commands':len(commands),'content_commit':identity['content_sha']}))
