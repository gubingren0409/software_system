"""Derive facts from saved data only, never resample resources."""
import hashlib
import json
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT))
from autotuner.resources import judge,load_policy
from autotuner.core import sha256_file,sha256_json
from scripts.p3_clock_contract import atomic_write_json,load

actual=load(HERE/'actual_resource_capture.stdout.txt')
policy_path=ROOT/'configs/resource_policy.json'
assert judge(actual,load_policy(policy_path),'Recovery',sha256_file(policy_path))==actual
original_path=ROOT/'evidence/p3_resource_policy/20261010-161312-30f9a2a1-recovery-7405fcc3/resources.stdout.txt'
fixture=load(ROOT/'tests/fixtures/ac33d9d_resource_replay.json')
assert fixture['record']==load(original_path) and fixture['source_raw_sha256']==sha256_file(original_path)
old=fixture['record']
old_policy_path=ROOT/'configs/resource_policy_cpu_v1.json'
assert judge(old,load_policy(old_policy_path),'Recovery',sha256_file(old_policy_path))==old
keys=('host_total_visible_bytes','host_samples','wsl_available_bytes','wsl_total_bytes',
      'wsl_swap_total_bytes','wsl_swap_free_bytes','wsl_root_free_bytes')
raw={key:old[key] for key in keys}
collector=ROOT/'scripts/check_p2_resources.ps1'
raw.update(schema='p3-resource-snapshot-v2',collector_sha256=sha256_file(collector),
           collector_lf_sha256=hashlib.sha256(collector.read_bytes().replace(b'\r\n',b'\n')).hexdigest())
replays={purpose:judge(raw,load_policy(policy_path),purpose,sha256_file(policy_path)) for purpose in ('Recovery','Formal')}
atomic_write_json(HERE/'historical_replay_results.json',{'classification':'SYNTHETIC_REPLAY_NOT_ADMISSION_OR_PERFORMANCE',
    'source_sha256':sha256_file(original_path),'original_reject_unchanged':True,'old_policy_recomputed_identically':True,
    'new_policy_results':replays})
meminfo={}
for line in actual['wsl_meminfo']:
    parts=line.split()
    if len(parts)>=2 and parts[0].endswith(':'):
        meminfo[parts[0][:-1]]=int(parts[1])*(1024 if len(parts)>2 and parts[2]=='kB' else 1)
version=(HERE/'wsl_version.stdout.txt').read_bytes()
version=version.decode('utf-16-le' if b'\x00' in version else 'utf-8',errors='replace')
result={'schema':'p3-memory-discovery-analysis-v1','analysis_source_sha256':sha256_file(Path(__file__)),
    'diagnostic_attempts':1,'diagnostic_attempt_timed_out':load(HERE/'paired_memory_diagnosis.operation.json')['timed_out'],
    'diagnostic_retry_count':0,'completed_real_resource_collections':1,'cold_start_before_state':'unknown; not captured; WSL not shut down',
    'actual_resource_raw_sha256':sha256_file(HERE/'actual_resource_capture.stdout.txt'),
    'sampling_window':[actual['sampling_window_start'],actual['sampling_window_end']],
    'host_samples':actual['host_samples'],'host_os_crosscheck':actual['host_os_crosscheck'],'vmmem':actual['vmmem'],
    'wsl_meminfo_bytes':meminfo,'wsl_version_decoded_derived':version,'existing_wslconfig':load(HERE/'existing_wslconfig.stdout.txt'),
    'actual_recovery_decision':actual['decision'],'actual_rejection_reasons':actual['rejection_reasons'],'actual_warnings':actual['warnings'],
    'policy_canonical_sha256':sha256_json(load_policy(policy_path)),
    'memory_estimate':{'n':4096,'one_double_matrix_bytes':4096**2*8,'candidate_static_A_B_C_bytes':3*4096**2*8,
        'candidate_validation_row_bytes':4096*8,'reference_A_B_output_bytes':3*4096**2*8,
        'reference_disk_data_bytes':4096**2*8,'execution_order':'Python parent remains resident; candidate builds then reference generation then serial targets; reference generator and candidate are not simultaneous',
        'not_in_estimate':'Python/compiler/loader/stdio, Windows/WSL kernel/services, allocator/page tables and file caches; not an exact RSS or system peak',
        'source_locations':['code/working/matrix_multiplication.c:32-34,188','code/working/reference_generator.c:30-31,154','autotuner/campaign.py:343-365','autotuner/core.py:530-554,632']},
    'causal_status':'Observed concurrent headroom, Vmmem working set and WSL meminfo only; reservation/reclaim explanation unproven. Do not sum Windows available plus Vmmem.'}
atomic_write_json(HERE/'discovery_analysis.json',result)
print(json.dumps({'actual_decision':actual['decision'],'warnings':actual['warnings'],'key_meminfo':{key:meminfo.get(key) for key in ('MemFree','MemAvailable','Cached','SReclaimable','AnonPages','Shmem','Dirty','SwapTotal','SwapFree')},'wsl_version':version}))
