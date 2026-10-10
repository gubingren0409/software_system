"""Focused integration/regressions only, all controlled; no large matrix/search."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
if __name__=='__main__':
    names=['test_raw_grid','test_raw_timing','test_fixed_work_clock','test_runner.ClassificationTests',
           'test_runner.StrictJsonTests','test_runner.ConfigSpaceTests','test_search_measurement',
           'test_campaign','test_campaign_costs','test_new_session_binding','test_p3_clock_contract','test_resource_policy']
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(names))
    raise SystemExit(0 if result.wasSuccessful() else 1)
