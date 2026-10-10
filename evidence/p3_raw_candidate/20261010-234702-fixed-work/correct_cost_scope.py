"""Separate pre-freeze regression from clean-export validation; no new measurement."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from autotuner.core import sha256_file
from scripts.p3_clock_contract import load,atomic_write_json

original=load(HERE/'costs.json')
excluded='candidate_tests_windows.operation.json'
selected={p.name:load(p)['qpc_seconds'] for p in HERE.glob('*.operation.json')
          if p.stem.startswith(('clean_','candidate_'))}
assert sum(selected.values())==original['clean_validation_outer_calls_seconds']
clean=sum(value for name,value in selected.items() if name!=excluded)
corrected={**original,'clean_validation_outer_calls_seconds':clean,
    'prefreeze_windows_regression_seconds_separate':selected[excluded],
    'archive_and_candidate_validation_outer_calls_seconds_including_prefreeze':sum(selected.values()),
    'clean_validation_scope':'Archive creation/extraction, clean CLI/isolation/tests, n17 execution, both identity audit attempts and cache-manifest copying. Excludes the pre-freeze Windows regression. Raw operations are unchanged.'}
atomic_write_json(HERE/'cost_scope_correction.json',{'original_costs':original,'prior_delivery_commit':'b1a478e39b8f92b389e68e9e5ae20e853229fba0',
    'reason':'candidate_ prefix included the separate pre-freeze regression; split that cost instead of mislabeling it clean validation',
    'excluded_operation':excluded,'excluded_seconds':selected[excluded],
    'clean_validation_operations':{k:v for k,v in selected.items() if k!=excluded},
    'corrected_clean_validation_seconds':clean,'no_raw_record_or_source_change':True,
    'helper_sha256':sha256_file(Path(__file__))})
atomic_write_json(HERE/'costs.json',corrected)
print(json.dumps({'clean_validation_seconds':clean,'prefreeze_windows_regression_seconds':selected[excluded],
                  'broad_total_seconds':sum(selected.values()),'no_new_execution':True}))
