"""User-authorized NEW validation session, without modifying frozen 35a60b0 content.

Data preparation and identity checks only. No gate/probe/target/search execution.
"""
import copy
import hashlib
import json
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from autotuner.core import sha256_file, utc_now
from autotuner.session import source_identity
from scripts.p3_clock_contract import atomic_write_json, capture, load, wsl_path

BASELINE = 'c08184e2cd6ac90af9d22aafdd3cd6b2ab09dd06'
CONTENT = '35a60b090b728d2ec3b6a8ea014beac69fe3766d'
OLD = ROOT / 'evidence/p3_raw_comparison/20261014-102833'


def main():
    if (OUT / 'validation_plan.json').exists():
        raise ValueError('Preparation already used; never replace the plan/session')
    def operation(command, name, maximum=60):
        result = capture(command, OUT / 'operations', name, 'new-ac-validation-preparation', timeout=maximum)
        if result['returncode'] != 0 or result['timed_out']:
            raise ValueError(name + ' failed; no formal activity started')
        return (OUT / 'operations' / result['stdout_path']).read_text(encoding='utf-8')
    head = operation(['git', 'rev-parse', 'HEAD'], 'initial_head').strip()
    branch = operation(['git', 'branch', '--show-current'], 'initial_branch').strip()
    status = operation(['git', 'status', '--porcelain=v1'], 'initial_status')
    operation(['git', 'merge-base', '--is-ancestor', BASELINE, 'HEAD'], 'baseline_ancestor')
    operation(['git', 'remote', '-v'], 'initial_remotes')
    if branch != 'project01':
        raise ValueError('Wrong branch')
    # Preserve every pre-existing evidence file, including both old validation
    # and search sessions, closed Grid and all older failed/partial records.
    preserved = {}
    for path in (ROOT / 'evidence').rglob('*'):
        if path.is_file() and OUT not in path.parents:
            preserved[path.relative_to(ROOT).as_posix()] = {'sha256': sha256_file(path), 'bytes': path.stat().st_size}
    atomic_write_json(OUT / 'history_before.json', {'at': utc_now(), 'files': preserved,
        'root_head': head, 'branch': branch, 'initial_status': status,
        'scope': 'All evidence existing before this new activity; excluded only this new directory'})
    original = load(OLD / 'content/validation_plan.json')
    if original['content_commit'] != CONTENT or original['mode'] != 'validation':
        raise ValueError('Wrong inherited runner identity')
    identity = load(Path(original['git_identity']))
    archive = Path(original['windows_archive_directory'])
    if sha256_file(Path(original['git_identity'])) != original['git_identity_sha256'] or \
            identity['content_sha'] != CONTENT or source_identity(archive, identity['files']) != original['windows_source_identity']:
        raise ValueError('Windows clean archive/Git identity differs')
    session = uuid.uuid4().hex
    plan = copy.deepcopy(original)
    plan.update(session_id=session, plan_file=str(OUT / 'validation_plan.json'),
        session_directory=str(OUT / ('validation-' + session[:8])),
        recovery_directory=str(OUT / ('validation-' + session[:8]) / 'admission'))
    if Path(plan['session_directory']).exists():
        raise ValueError('New empty output directory required')
    old_session = Path(original['session_directory'])
    old_window = load(old_session / 'window.json')
    authorization = {'schema': 'raw-comparison-new-validation-authorization-v1', 'at': utc_now(),
        'authorized_by': 'User explicitly connected AC/opened lid, based on c08184e, and authorized one NEW limited validation session',
        'baseline': BASELINE, 'starting_head': head, 'execution_content': CONTENT,
        'session_id': session, 'mode': 'validation', 'activity_budget_qpc_seconds': 3600,
        'order': [{'optimization': 'O3', 'block_size': s} for s in (128, 64, 24)],
        'warmup_count_per_group': 1, 'fresh_measurements_per_group': 5, 'planned_target_executions': 18,
        'one_short_long_admission_only': True, 'search_authorized': False, 'failure_action': 'Save and stop; no retry',
        'old_validation_session': original['session_id'], 'old_claim_sha256': sha256_file(old_session / 'ACTIVITY.claim.json'),
        'old_window_sha256': sha256_file(old_session / 'window.json'), 'old_used_qpc_seconds': old_window['activity_qpc_seconds'],
        'old_claim_preserved': True, 'new_window_is_explicitly_authorized_not_reset': True,
        'inherited_plan_sha256': sha256_file(OLD / 'content/validation_plan.json'),
        'preparation_source_sha256': sha256_file(Path(__file__)), 'scientific_protocol_changes': False}
    atomic_write_json(OUT / 'authorization.json', authorization)
    atomic_write_json(OUT / 'validation_plan.json', plan)
    def linux(args):
        return ['wsl.exe', '-d', 'Ubuntu-24.04', '--cd', plan['archive_directory'], '--',
                'env', '-u', 'PYTHONPATH', 'PYTHONDONTWRITEBYTECODE=1', *args]
    checks = """import json,pathlib,os,platform
from autotuner.session import source_identity
from autotuner.core import sha256_file
plan=json.load(open(PLAN)); identity=json.load(open(IDENTITY)); root=pathlib.Path.cwd()
assert source_identity(root,identity['files'])==plan['linux_source_identity']
assert sha256_file(pathlib.Path('/usr/bin/gcc'))==plan['compiler_sha256']
for name,expected in plan['verified_cache_files'].items():
 assert sha256_file(pathlib.Path(name))==expected,name
for name,expected in plan['inherited_measurement_files'].items():
 assert sha256_file(root/name)==sha256_file(pathlib.Path(plan['measurement_archive_directory'])/name)==expected,name
probe=json.load(open(PROBE)); assert sha256_file(pathlib.Path(probe['binary']))==probe['binary_sha256']
allowed=sorted(os.sched_getaffinity(0)); assert allowed==plan['allowed_cpus']
print(json.dumps({'identity_pass':True,'compiler_sha256':plan['compiler_sha256'],'cached_files_verified':len(plan['verified_cache_files']),
 'kernel':platform.release(),'boot_id':pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'allowed_cpus':allowed,'source_file_count':len(identity['files']),'initialization_target_executions':0}))
""".replace('PLAN', repr(wsl_path(OUT / 'validation_plan.json'))).replace('IDENTITY', repr(wsl_path(plan['git_identity']))).replace('PROBE', repr(wsl_path(plan['probe_build_manifest'])))
    checked = json.loads(operation(linux(['python3', '-c', checks]), 'wsl_archive_compiler_cache_identity', 120))
    operation(linux(['python3', '-m', 'autotuner.raw_comparison', '--plan', wsl_path(OUT / 'validation_plan.json'), 'init']),
              'initialize_new_validation', 120)
    initial = load(Path(plan['session_directory']) / 'checkpoint.json')
    if initial['target_executions'] or initial['validation_groups'] or initial['active'] is not None or \
            any(t['observations'] for t in initial['trajectories'].values()):
        raise ValueError('Initialization not empty')
    atomic_write_json(OUT / 'preparation_summary.json', {'at': utc_now(), 'content_commit': CONTENT, 'session_id': session,
        'validation_plan': plan['plan_file'], 'preparation_source_sha256': sha256_file(Path(__file__)),
        'windows_source_identity_pass': True, 'linux_cache_identity': checked,
        'historical_evidence_files_preserved': len(preserved), 'new_initial_checkpoint_sha256': sha256_file(Path(plan['session_directory']) / 'initial_checkpoint.json'),
        'old_claim_unchanged': sha256_file(old_session / 'ACTIVITY.claim.json') == authorization['old_claim_sha256'],
        'target_executions': 0, 'clock_intervals': 0, 'reference_generation_calls': 0,
        'tests_reused': str(OLD / 'content/prepare_summary.json')})
    print(json.dumps({'content_commit': CONTENT, 'session_id': session, 'plan': plan['plan_file'], 'initial_target_executions': 0}), flush=True)


if __name__ == '__main__': main()
