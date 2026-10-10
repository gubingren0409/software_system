"""Postprocess this one failed recovery; no resource resampling or target launch."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from autotuner.core import sha256_file, sha256_json, utc_now
from autotuner.resources import judge, load_policy, valid_gate
from autotuner.session import source_identity
from scripts.p3_clock_contract import atomic_write_json, capture, load, snapshot_campaign, qpc

plan = load(HERE / 'session_plan.json')
recovery = Path(plan['recovery_directory'])
assert not Path(plan['resume_directory']).exists(), 'Failed clock recovery must not resume'
review = load(HERE / 'independent_recovery.json')
assert review['evidence_integrity_pass'] and not review['timing_checks_pass']
assert not review['clock_recovery_reevaluation']['recovery_eligible']


def run(name, command):
    result = capture(command, HERE, name, HERE.name, timeout=60)
    assert result['returncode'] == 0, name
    return result


# Only inspect processes in our runner namespace; do not terminate anything.
code = r'''import fcntl,json,pathlib,sys,platform
found=[]
for directory in pathlib.Path('/proc').iterdir():
    if not directory.name.isdigit(): continue
    try:
        args=[item.decode(errors='replace') for item in (directory/'cmdline').read_bytes().split(bytes([0])) if item]
        if ('autotuner' in args and 'campaign' in args) or any(a.startswith('/var/tmp/matrix-autotuner-p3-10245102457/cache/') for a in args):
            found.append({'pid':int(directory.name),'command':args})
    except (OSError,ProcessLookupError): pass
lock=pathlib.Path('/var/tmp/matrix-autotuner-p3-10245102457.runner.lock')
available='unknown'
if lock.exists():
    with lock.open('r') as handle:
        try:
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB); available=True
            fcntl.flock(handle,fcntl.LOCK_UN)
        except BlockingIOError: available=False
print(json.dumps({'python':sys.version,'kernel':platform.release(),'formal_processes':found,'runner_lock_available':available}))
'''
run('final_process_state', ['wsl.exe','-d','Ubuntu-24.04','--cd','/tmp','--','timeout','30','python3','-c',code])
process = load(HERE / 'final_process_state.stdout.txt')
assert not process['formal_processes'] and process['runner_lock_available'] is True
run('final_runtime_diff', ['git','diff',plan['content_commit'],'--','autotuner','code','configs','scripts','tests'])
assert not (HERE / 'final_runtime_diff.stdout.txt').read_bytes()

policy_path = ROOT / 'configs/resource_policy.json'
resource = load(recovery / 'resources.stdout.txt')
protocol = load(recovery / 'measurement_protocol.json')
assert judge(resource, load_policy(policy_path), 'Recovery', sha256_file(policy_path)) == resource
assert valid_gate(resource, protocol, 'Recovery') and not valid_gate(resource, protocol, 'Formal')

protected = []
for before_path in sorted(HERE.glob('*_protected.json')):
    before = load(before_path)
    paths = subprocess.check_output(['git','ls-files','--',before['prefix']],cwd=ROOT,text=True).splitlines()
    after = {'prefix':before['prefix'],'count':len(paths),
             'raw_map_sha256':sha256_json({p:sha256_file(ROOT/p) for p in paths})}
    assert after == before, before['prefix']
    protected.append({**after,'byte_identical':True})
for name, directory in (
        ('legacy_e308bfb', ROOT/'evidence/p3/campaign-e308bfb'),
        ('sealed_7405fcc3', ROOT/'evidence/p3_resource_policy/20261010-143415/campaign-7405fcc3')):
    before, after = load(HERE/(name+'_before.json')), snapshot_campaign(directory)
    assert before['checkpoint_sha256'] == after['checkpoint_sha256']
    assert before['trajectories'] == after['trajectories']
    atomic_write_json(HERE/(name+'_after.json'),after)
atomic_write_json(HERE/'history_protection_after.json', {'files':sum(p['count'] for p in protected),'prefixes':protected,
    'old_pause_request_sha256':sha256_file(ROOT/'evidence/p3/campaign-e308bfb/PAUSE_REQUEST')})
campaign_after = snapshot_campaign(Path(plan['campaign_directory']))
before = load(recovery/'campaign_before.json')
assert before['checkpoint_sha256'] == campaign_after['checkpoint_sha256'] and not campaign_after['trajectories']
atomic_write_json(HERE/'campaign_after.json', campaign_after)
identity = load(Path(plan['git_identity']))
atomic_write_json(HERE/'worktree_source_identity_after.json',source_identity(ROOT,identity['files']))
assert sha256_file(ROOT/'code/original/matrix_multiplication.c') == '188d011109c4470e1f41829216e8677a5c2d8f2b7c8a44215652320dbdf6de15'

clock_rows=[]
for window, checked in review['clock_recovery_reevaluation']['windows'].items():
    for item in checked['checks']:
        clock_rows.append({'window':window,**item})
assert len(clock_rows)==20
failed=[r for r in clock_rows if not r['monotonic_raw_pass'] or not r['realtime_raw_pass']]
atomic_write_json(HERE/'clock_analysis.json', {'schema':'p3-memory-policy-clock-analysis-v1',
    'source_independent_audit_sha256':sha256_file(HERE/'independent_recovery.json'),
    'interval_count':20,'monotonic_raw_pass_count':sum(r['monotonic_raw_pass'] for r in clock_rows),
    'realtime_raw_pass_count':sum(r['realtime_raw_pass'] for r in clock_rows),
    'host_same_call_pass_count':sum(w['host_check']['pass'] for w in review['clock_recovery_reevaluation']['windows'].values()),
    'failed_intervals_zero_based':failed,'all_intervals':clock_rows,
    'no_filtering_or_calibration':True,'physical_clock_accuracy':'unknown','root_cause':'unknown'})

operations=[]
for path in sorted(HERE.rglob('*.operation.json')):
    record=load(path)
    if 'qpc_end' not in record: continue  # This postprocessor's parent capture is still running.
    for stream in ('stdout','stderr'):
        assert sha256_file(path.parent/record[stream+'_path']) == record[stream+'_sha256'], str(path)
    operations.append({'path':path.relative_to(HERE).as_posix(), **{key:record[key] for key in
        ('returncode','qpc_start','qpc_end','qpc_frequency','qpc_seconds','timed_out')}})
merged=[]
for start,end in sorted((o['qpc_start']/o['qpc_frequency'],o['qpc_end']/o['qpc_frequency']) for o in operations):
    if not merged or start>merged[-1][1]: merged.append([start,end])
    else: merged[-1][1]=max(merged[-1][1],end)

n17=load(next((HERE/'clean/n17/runs').glob('*/result.json')))
rss=int(re.search(r'Maximum resident set size \(kbytes\):\s+(\d+)',n17['raw_resource']).group(1))
new_check=campaign_after['checkpoint']
flags={key:review[key] for key in ('evidence_integrity_pass','execution_complete','timing_checks_pass','comparison_ready')}
costs={'captured_auxiliary_qpc_interval_union_seconds':sum(end-start for start,end in merged),
    'scope':'Recorded Windows operations only; nested intervals merged. Excludes editing, unwrapped analysis/protection hashing, this finalization parent, later Git/push and offline gaps. Not full project elapsed time.',
    'recovery_entry_seconds':load(HERE/'recover_entry.operation.json')['qpc_seconds'],
    'recovery_resource_collection_seconds':load(recovery/'resources.operation.json')['qpc_seconds'],
    'recovery_two_child_calls_seconds':sum(load(recovery/(w+'.operation.json'))['qpc_seconds'] for w in ('window_A','window_B')),
    'independent_audit_seconds':load(HERE/'independent_recovery.operation.json')['qpc_seconds'],
    'failed_diagnostic_seconds':load(HERE/'paired_memory_diagnosis.operation.json')['qpc_seconds'],
    'clean_validation_seconds':load(HERE/'clean_validation.operation.json')['qpc_seconds'],
    'new_campaign_active_total_seconds':new_check['active_total_seconds'],
    'new_campaign_active_scope':'Initialize-only compiler/source preflight, no target invocation',
    'formal_terminal_configuration_call_seconds':0,'formal_target_seconds':0,'formal_retest_seconds':0,
    'formal_gate_wait_seconds':0,'abandoned_attempt_seconds':0,'nested_costs_must_not_be_added':True,
    'operations':operations}
atomic_write_json(HERE/'costs.json',costs)
result={'schema':'p3-memory-policy-delivery-v1','recorded_at':utc_now(),'status':'P3_CLOCK_BLOCKED',
    'analysis_source_sha256':sha256_file(Path(__file__)),'runtime_content_commit':plan['content_commit'],
    'session_id':plan['session_id'],'archive_directory':plan['archive_directory'], 'campaign_directory':plan['campaign_directory'],
    'policy_version':resource['policy_version'],'policy_hash':resource['policy_hash'],
    'measurement_protocol_hash':new_check['preflight_identity']['measurement_protocol_hash'],
    'campaign_protocol_hash':new_check['preflight_identity']['campaign_protocol_hash'],
    'recovery_entry_returncode':load(HERE/'recover_entry.operation.json')['returncode'],
    'independent_audit_returncode':load(HERE/'independent_recovery.operation.json')['returncode'],
    'recovery_resource_gate_pass':True,'formal_resource_gate_status':'not_performed','recovery_eligible':False,
    'resource_summary':{key:resource[key] for key in ('sampling_window_start','sampling_window_end','host_minimum_available_bytes',
        'host_minimum_commit_headroom_bytes','host_cpu_average_percent','host_cpu_maximum_percent','wsl_available_bytes',
        'wsl_swap_total_bytes','wsl_swap_free_bytes','wsl_root_free_bytes','warnings','rejection_reasons')},
    'acceptance':flags,'clock_interval_count':20,'failed_monotonic_raw_count':len(failed),
    'formal_configurations':0,'completed_trajectories':0,'formal_target_executions':0,'prefix_rows':0,'retests':0,
    'partial_attempts':0,'abandoned_attempts':0,'historical_protected_files':sum(p['count'] for p in protected),
    'historical_campaigns_unchanged':True,'new_checkpoint_unchanged':True,
    'diagnostic_n17':{'source':n17['source'],'classification':n17['classification'],'checked_entries':289,
        'run_id':n17['run_id'],'max_rss_kib':rss,'process_wall_seconds':n17['process_wall_seconds'],
        'resource_before':n17['resource_before'],'resource_after':n17['resource_after'],
        'not_formal_performance':True},
    'formal_processes':process['formal_processes'],'runner_lock_available':process['runner_lock_available'],
    'costs_file':'costs.json',
    'early_orchestration_note':'declaration.json records the original batch.py before the prevalidate phase was appended; that original body was not separately archived. Current helper is committed in the content SHA. Formal runtime source identities are complete and unchanged.'}
atomic_write_json(HERE/'delivery_summary.json',result)
print(json.dumps({'status':result['status'],'acceptance':flags,'failed_intervals':len(failed),
    'history_files':result['historical_protected_files'],'auxiliary_interval_union_seconds':costs['captured_auxiliary_qpc_interval_union_seconds']}))
