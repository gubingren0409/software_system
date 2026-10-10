"""Read-only rechecks and derived delivery evidence. No target/probe launch."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from autotuner.core import sha256_file,sha256_json,utc_now
from scripts.p3_clock_contract import atomic_write_json,capture,load,qpc,snapshot_campaign,wsl_path


def linux(command):
    return ['wsl.exe','-d','Ubuntu-24.04','--cd','/tmp','--','env','-u','PYTHONPATH','PYTHONDONTWRITEBYTECODE=1',*command]


def run(name,command):
    result=capture(command,HERE,name,HERE.name,timeout=90)
    print(json.dumps({'operation':name,'returncode':result['returncode'],'qpc_seconds':result['qpc_seconds']}),flush=True)
    if result['returncode']!=0: raise ValueError(name+' failed')
    return result


run('final_diagnostic_recompute',[sys.executable,'-B','-X','utf8','-m','scripts.p3_fixed_work_clock',
    '--directory',str(HERE),'--output',str(HERE/'final_independent_diagnostic.json')])
formal_archive='/var/tmp/matrix-autotuner-p3-memory-content-d6811cadda8ecd7b46225ebe65c51831278694a0'
code="import hashlib,json;from pathlib import Path;before=json.loads(Path("+repr(wsl_path(HERE/'d6811cad_before.json'))+").read_text());expected=before['checkpoint']['preflight_identity']['files'];root=Path("+repr(formal_archive)+");result={p:{'expected':v['executed_sha256'],'actual':hashlib.sha256((root/p).read_bytes()).hexdigest()} for p,v in expected.items()};print(json.dumps({'archive':str(root),'files':result,'pass':all(v['expected']==v['actual'] for v in result.values())}));assert all(v['expected']==v['actual'] for v in result.values())"
run('retained_archive_identity',linux(['python3','-B','-c',code]))
process_code="import json,os;from pathlib import Path;matches=[];prefixes=('/var/tmp/matrix-fixed-work-clock-20261010-234702-fixed-work/','/var/tmp/matrix-raw-candidate-cache-3c7a4ab11f7e753936ab8735e03364b44b4dd1ef/');\nfor p in Path('/proc').glob('[0-9]*/exe'):\n try:\n  target=os.readlink(p)\n  if target.startswith(prefixes): matches.append({'pid':int(p.parent.name),'exe':target})\n except (OSError,PermissionError): pass\nprint(json.dumps({'owned_experiment_processes':matches}));assert not matches"
run('owned_process_check',linux(['python3','-B','-c',process_code]))

protection=[]
for prior in load(HERE/'history_protection_before.json'):
    paths=subprocess.check_output(['git','ls-files','--',prior['prefix']],cwd=ROOT,text=True).splitlines()
    actual=sha256_json({p:sha256_file(ROOT/p) for p in paths})
    protection.append({**prior,'after_count':len(paths),'after_raw_map_sha256':actual,
        'pass':len(paths)==prior['count'] and actual==prior['raw_map_sha256']})
atomic_write_json(HERE/'history_protection_after.json',protection)
assert all(item['pass'] for item in protection)
snapshots={}
for name,path in (('d6811cad',ROOT/'evidence/p3_memory_policy/20261010-174802-11f7775c/campaign-d6811cad'),
    ('7405fcc3',ROOT/'evidence/p3_resource_policy/20261010-143415/campaign-7405fcc3'),
    ('e308bfb',ROOT/'evidence/p3/campaign-e308bfb')):
    before=load(HERE/(name+'_before.json')); after=snapshot_campaign(path)
    atomic_write_json(HERE/(name+'_after.json'),after)
    passed=before['checkpoint_sha256']==after['checkpoint_sha256'] and before['trajectories']==after['trajectories']
    assert passed,name
    snapshots[name]={'pass':passed,'session_id':after['checkpoint']['session_id'],
        'status':after['checkpoint']['status'],'raw_records':sum(t['sample_count'] for t in after['trajectories'].values()),
        'complete_search_configurations':sum(len(t['checkpoint']['observations']) for t in after['trajectories'].values())}
atomic_write_json(HERE/'campaign_protection.json',snapshots)

baseline='da0afd87bbfe594fa69ca98ddfdcc048c2de4770'
unchanged=('code/original','code/working/matrix_input.h','code/working/reference_generator.c','autotuner/search.py',
           'configs/config_space.json','configs/search_protocol.json','configs/resource_policy.json')
assert not subprocess.check_output(['git','diff','--name-only',baseline,'--',*unchanged],cwd=ROOT,text=True).strip()
old=subprocess.check_output(['git','show',baseline+':code/working/matrix_multiplication.c'],cwd=ROOT)
new=(ROOT/'code/working/matrix_multiplication.c').read_bytes()
def loop(data):
    data=data.replace(b'\r\n',b'\n'); return data.split(b'/* Teacher-provided core loop order and computation semantics. */',1)[1].split(b'\n\n',1)[0]
assert loop(old)==loop(new)
source_protection={'unchanged_paths':list(unchanged),'pass':True,'core_loop_byte_equal_after_lf_normalization':True,
    'core_loop_sha256':hashlib.sha256(loop(new)).hexdigest(),
    'teacher_c_sha256':sha256_file(ROOT/'code/original/matrix_multiplication.c'),
    'working_c_sha256':sha256_file(ROOT/'code/working/matrix_multiplication.c')}
atomic_write_json(HERE/'computation_protection.json',source_protection)

manifest=load(HERE/'manifest.json'); compile_op=load(HERE/'compile_native.operation.json')
assert compile_op['command']==manifest['compile_command'] and compile_op['returncode']==0
assert (HERE/'binary_identity.stdout.txt').read_text().split()[0]==manifest['binary_sha256']
assert manifest['binary_sha256'] in manifest['probe_command'][-1] and manifest['probe_binary'] in manifest['probe_command'][-1]
operations={}
for path in sorted(HERE.glob('*.operation.json')):
    op=load(path)
    for stream in ('stdout','stderr'):
        assert sha256_file(HERE/op[stream+'_path'])==op[stream+'_sha256'],path.name+'/'+stream
    assert type(op['returncode']) is int,path.name
    operations[path.stem]={'returncode':op['returncode'],'qpc_seconds':op['qpc_seconds'],'timed_out':op['timed_out']}
atomic_write_json(HERE/'operation_verification.json',{'pass':True,'operations':operations,
    'expected_rejections':['legacy_fixture_failure.operation','clean_n17_independent_audit.operation'],
    'note':'Rejected operations remain rejected. Corrected identity excludes non-runtime metadata, never teacher C.'})

diagnostic=load(HERE/'final_independent_diagnostic.json'); validation=load(HERE/'clean_validation.json')
assert diagnostic['raw_candidate_eligible'] and validation['candidate_validation_pass']
rows=[json.loads(line) for line in (HERE/'intervals.jsonl').read_text().splitlines()]
by_condition={}
for check in diagnostic['checks']:
    group=by_condition.setdefault(check['condition'],{'count':0,'raw_pass':0,'raw_unpadded_pass':0,'monotonic_pass':0,
        'realtime_pass':0,'boottime_pass':0})
    group['count']+=1; group['raw_pass']+=check['raw_pass']; group['raw_unpadded_pass']+=check['within_host_unpadded']['raw']
    for clock in ('monotonic','realtime','boottime'): group[clock+'_pass']+=check['within_host_with_allowance'][clock]
analysis={'conditions':by_condition,'raw_failure_indices':diagnostic['raw_failure_indices'],
    'raw_unpadded_failure_indices':diagnostic['raw_unpadded_failure_indices'],'monotonic_failure_indices':diagnostic['monotonic_failure_indices'],
    'maximum_uncertainty_seconds':max(c['uncertainty_seconds'] for c in diagnostic['checks']),
    'maximum_raw_read_span_ns':max(max(c['read_spans_ns']['raw']) for c in diagnostic['checks']),
    'adjtimex_freq_ppm':sorted({r[e]['response']['adjtimex'].get('freq_ppm','unknown') for r in rows for e in ('start','end')}),
    'boot_ids':sorted({r[e]['response']['boot_id'] for r in rows for e in ('start','end')}),
    'clocksource':sorted({r[e]['response']['clocksource'] for r in rows for e in ('start','end')}),
    'observation':'RAW all22 including default libc/unbound 5 short+2 long match host, even unpadded. MONOTONIC mismatches retained. syscall busy 10/10 match in THIS round; pinning alone does not fix libc.',
    'inference':'Path-associated intermittent MONOTONIC differences are plausible; endpoint adjtimex observations alone cannot identify the root cause or explain the much larger mismatches.',
    'unknown':'Physical accuracy and underlying virtualization/vDSO/timekeeping cause; no old-data calibration or official precision claim.'}
atomic_write_json(HERE/'diagnostic_analysis.json',analysis)
costs={'clock':'Windows QPC for outer operations; scope is not sum of nested ranges',
    'diagnostic_collection_seconds':load(HERE/'collection.operation.json')['qpc_seconds'],
    'native_process_seconds_nested_in_collection':load(HERE/'native_process.json')['qpc_seconds'],
    'wsl_metadata_seconds_nested_in_collection':load(HERE/'wsl_environment.operation.json')['qpc_seconds'],
    'probe_compile_call_seconds':compile_op['qpc_seconds'],
    'clean_validation_outer_calls_seconds':sum(v['qpc_seconds'] for k,v in operations.items() if k.startswith(('clean_','candidate_'))),
    'small_target_call_seconds_nested_in_clean_validation':load(HERE/'clean_n17_evaluate.operation.json')['qpc_seconds'],
    'formal_execution_seconds':0,'formal_retest_seconds':0,'formal_gate_wait_seconds':0,'formal_abandoned_attempt_seconds':0,
    'historical_campaign_cost_delta_seconds':0,
    'task_elapsed_from_first_saved_head_check_seconds':(qpc()[0]-load(HERE/'head_before.operation.json')['qpc_start'])/qpc()[1],
    'task_elapsed_scope':'Includes implementation, manual tests, inspection, exports and waiting; not pure diagnostic/benchmark cost. Nested components must not be added again.'}
atomic_write_json(HERE/'costs.json',costs)
summary={'schema':'p3-raw-candidate-delivery-v1','status':'P3_RAW_CLOCK_CANDIDATE_READY','created_at':utc_now(),
    'diagnostic_source_commit':manifest['source_commit'],'candidate_content_commit':validation['content_commit'],
    'candidate_archive':validation['archive_directory'],'new_formal_session_count':0,
    'retained_formal_content_commit':manifest['formal_content_commit'],'retained_formal_session_id':manifest['formal_session_id'],
    'diagnostic_interval_count':22,'native_response_count':90,'total_fixed_updates':40_000_000_000,
    'raw_failure_indices':diagnostic['raw_failure_indices'],'raw_unpadded_failure_indices':diagnostic['raw_unpadded_failure_indices'],
    'monotonic_failure_indices':diagnostic['monotonic_failure_indices'],'indeterminate_count':0,
    'small_matrix_execution_count':1,'small_matrix_n':17,'checked_entries':289,
    'formal_4096_execution_count':0,'recovery_interval_count':0,'formal_gate_count':0,
    'new_search_configuration_count':0,'new_complete_trajectory_count':0,'new_retest_count':0,
    'evidence_integrity_pass':True,'candidate_clock_reference_pass':True,'candidate_validation_pass':True,
    'execution_complete':False,'timing_checks_pass':False,'comparison_ready':False,
    'formal_checks_status':'not_executed; candidate-only admission is deliberately disabled',
    'history_protection_file_count':sum(p['count'] for p in protection),'history_protection_pass':True,
    'owned_experiment_process_count':0,'protocol_file_sha256':sha256_file(ROOT/'configs/raw_timing_protocol.json'),
    'timing_protocol_hash':load(ROOT/'configs/measurement_protocol.json')['timing_protocol']['hash'],
    'probe_source_sha256':manifest['source_sha256']['code/diagnostics/clock_fixed_work_probe.c'],
    'probe_binary_sha256':manifest['binary_sha256'],'working_c_sha256':source_protection['working_c_sha256'],
    'postprocessing_source_sha256':sha256_file(Path(__file__)),
    'next_step':'External audit of RAW candidate. Future authorized activation needs fresh QPC/RAW recovery, new session and matching fresh Grid; no automatic Grid/random/greedy.'}
atomic_write_json(HERE/'delivery_summary.json',summary)
print(json.dumps(summary,ensure_ascii=False),flush=True)
