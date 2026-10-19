"""Focused fake-executor regressions; zero native probes or matrix targets."""
import sys
import json
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
if __name__ == '__main__':
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name)
        for name in ('test_raw_comparison', 'test_raw_comparison_audit'))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({'focused_tests': result.testsRun, 'success': result.wasSuccessful(),
        'real_matrix_targets': 0, 'native_clock_intervals': 0}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
