import math
import unittest

from scripts.timing_audit import agreement, interval


class TimingAuditTests(unittest.TestCase):
    def test_retains_nanosecond_precision_without_float_endpoints(self):
        start = {"raw_ns": "100000000000000001"}
        end = {"raw_ns": "100000000000000011"}
        self.assertEqual(interval(start, end), {"raw_seconds": 1e-8})

    def test_nonfinite_negative_and_clock_divergence_are_not_agreement(self):
        for value in (math.nan, math.inf, -math.inf, 0, -1, 19):
            with self.subTest(value=value): self.assertFalse(agreement(value, 20, 0.01, 0.005))

    def test_predeclared_relative_and_absolute_boundaries(self):
        self.assertTrue(agreement(20.2, 20, 0.01, 0.005))
        self.assertFalse(agreement(20.3, 20, 0.01, 0.005))
        self.assertTrue(agreement(20.8, 20, 0.01, 1))
        self.assertFalse(agreement(21.3, 20, 0.01, 1))


if __name__ == "__main__":
    unittest.main()
