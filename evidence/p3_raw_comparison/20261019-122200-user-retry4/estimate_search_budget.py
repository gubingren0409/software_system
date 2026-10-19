"""Offline cost scenarios only; never imports or provides observations to a strategy."""
import hashlib
import json
from pathlib import Path

out=Path(__file__).resolve().parent
grid=out.parents[2]/'evidence/p3_raw_grid/20261011-021601/final-content/grid-f705a488/checkpoint.json'
state=json.loads(grid.read_bytes())
scores=sorted(g['score_seconds'] for g in state['completed'])
if len(scores)!=20: raise ValueError('Expected the closed historical 20-configuration table')
result=dict(
    source=str(grid),source_sha256=hashlib.sha256(grid.read_bytes()).hexdigest(),
    purpose='Offline budget scenario, not strategy input, observations, or new measured search costs',
    uniform_without_replacement_one_trajectory_12_core_seconds=12*6*sum(scores)/20,
    historical_fastest12_one_trajectory_core_seconds=6*sum(scores[:12]),
    historical_slowest12_one_trajectory_core_seconds=6*sum(scores[-12:]),
    six_distinct_candidate_groups_at_historical_slowest_core_seconds=6*6*max(scores),
    maximum_group_count_including_retests=30,maximum_fresh_target_calls=180,
    proposed_future_activity_budget_qpc_seconds=43200,
    scope='Each core scenario is six times historical medians, not sums of actual warmups. No clock/resource/power overhead included; greedy is not assumed uniform. Historical standby data unchanged. Upper/lower scenarios are not guarantees. Proposed future independent 12h claim includes resource gates, clocks, setup, 24 search groups and at most6 retest groups, cleanup; failure or exhaustion stops without automatic reset. Validation unused allowance is not transferred. No search executed.')
(out/'search_budget_scenarios.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
