"""Bind this user's first-seed authorization to the exact new empty session."""
import json
import sys
from pathlib import Path

OUT=Path(__file__).resolve().parent
plan=json.loads((OUT/'content/search_plan.json').read_bytes())
sys.path.insert(0,plan['windows_archive_directory'])
from autotuner.core import sha256_file, utc_now
from scripts.start_raw_comparison import validate_plan, claim
from scripts.raw_comparison_contract import audit, search_authorization_value
from scripts.p3_clock_contract import atomic_write_json, load

protocol=validate_plan(plan);session=Path(plan['session_directory']);state=load(session/'checkpoint.json')
if plan['mode']!='search' or state['status']!='initialized' or state['target_executions']!=0 or \
        state['active'] is not None or state['validation_groups'] or (session/'ACTIVITY.claim.json').exists() or \
        any(t[k] for t in state['trajectories'].values() for k in ('observations','retests','prefixes','prefix_retest_mapping')):
    raise SystemExit('Only a new empty search session can be authorized')
checked=audit(plan);atomic_write_json(OUT/'empty_session_independent_audit.json',checked)
if not checked['evidence_integrity_pass'] or checked['execution_complete'] or checked['comparison_ready']:
    raise SystemExit('Empty new session identity or audit differs')
auth=OUT/'search_authorization.json';claim(auth,search_authorization_value(plan))
manifest=dict(declared_at=utc_now(),scope='first_seed',user_authorized_base='efb7f9df9c25dd509e207d67e08d4180c3e779ac',
    execution_content_sha=plan['content_commit'],session_id=plan['session_id'],inherited_measurement_content_sha=plan['measurement_content'],
    windows_archive_directory=plan['windows_archive_directory'],archive_directory=plan['archive_directory'],
    session_directory=plan['session_directory'],plan_sha256=sha256_file(OUT/'content/search_plan.json'),
    authorization_file=str(auth),authorization_sha256=sha256_file(auth),
    initial_checkpoint_sha256=sha256_file(session/'initial_checkpoint.json'),history_map_sha256=sha256_file(OUT/'history_before.json'),
    stage_policy_sha256=sha256_file(OUT/'stage_plan.md'),matrix_input_seed=protocol['matrix_input_seed'],search_seed=protocol['search_seed'],
    activity_budget_qpc_seconds=43200,search_order=['random12','random deduplicated prefix retests','greedy12','greedy deduplicated prefix retests'],
    prefixes=[4,8,12],group_measurement='1 successful warmup +5 fresh; median RAW',
    comparison_protocol_hash=plan['comparison_protocol_hash'],measurement_protocol_hash=plan['measurement_protocol_hash'],
    timing_protocol_hash=plan['timing_protocol_hash'],compiler_sha256=plan['compiler_sha256'],
    probe_build=load(plan['probe_build_manifest']),initial_real_target_executions=0,initial_search_observations=0,
    old_validation_allowance_transferred=False,performance_samples_reused=False,stop_on_any_failure=True)
atomic_write_json(OUT/'run_manifest.json',manifest)
print(json.dumps({k:manifest[k] for k in ('execution_content_sha','session_id','session_directory','activity_budget_qpc_seconds','initial_real_target_executions')}))
