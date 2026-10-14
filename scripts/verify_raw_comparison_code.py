"""Focused fake-executor regressions; zero native probes or matrix targets."""
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromName('test_raw_comparison')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
