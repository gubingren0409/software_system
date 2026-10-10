"""Record actual verification commands; never launch recovery or formal targets."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from scripts.p3_clock_contract import capture
HERE=Path(__file__).resolve().parent

if sys.argv[1]=='fixture-failure':
    code="import sys,unittest;sys.path.insert(0,'tests');r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(['test_search_measurement.MeasurementTests.test_formal_gate_is_not_inferred_from_exit_status','test_search_measurement.MeasurementTests.test_resource_blocked_checkpoint_has_identity_before_setup_and_resumes']));sys.exit(0 if r.wasSuccessful() else 1)"
    result=capture([sys.executable,'-B','-X','utf8','-c',code],HERE,'legacy_fixture_failure',HERE.name,timeout=30)
elif sys.argv[1]=='tests':
    result=capture([sys.executable,'-B','-X','utf8','scripts/verify_raw_candidate_code.py'],HERE,'candidate_tests_windows',HERE.name,timeout=120)
else: raise ValueError('Unknown phase')
print(json.dumps({'returncode':result['returncode'],'qpc_seconds':result['qpc_seconds']}))
