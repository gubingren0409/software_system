"""Postprocessing costs must not silently become end-to-end prefix costs."""
import unittest
import math

from scripts.audit_p3_first_seed import activity_costs, check_clock_intervals


class FirstSeedCostTests(unittest.TestCase):
    def test_campaign_activity_and_retests_remain_separate_from_search(self):
        checkpoint = {"active_total_seconds": 1500, "wait_seconds": 300}
        baseline = {"active_total_seconds": 1000, "wait_seconds": 250}
        states = [{"job": {"algorithm": "random", "seed": 20261008},
                   "observations": [{"evaluation_wall_seconds": 20},
                                    {"evaluation_wall_seconds": 40}],
                   "independent_retests": [{"evaluation_wall_seconds": 15}]}]
        result = activity_costs(checkpoint, baseline, states)
        self.assertEqual(result["campaign_active_seconds"], 1500)
        self.assertEqual(result["campaign_gate_and_wait_seconds"], 300)
        self.assertEqual(result["this_batch_checkpoint_active_delta_seconds"], 500)
        self.assertEqual(result["this_batch_checkpoint_gate_and_wait_delta_seconds"], 50)
        self.assertEqual(result["trajectories"][0]["terminal_search_evaluator_seconds"], 60)
        self.assertEqual(result["trajectories"][0]["independent_retest_evaluator_seconds"], 15)


class FirstSeedClockTests(unittest.TestCase):
    criteria = {"monotonic_raw_relative_tolerance": 0.01,
                "monotonic_raw_absolute_allowance_seconds": 0.005,
                "realtime_raw_relative_tolerance": 0.01,
                "realtime_raw_absolute_allowance_seconds": 0.25}

    def probe(self, monotonic=3, raw=3, realtime=3):
        return {"wsl_intervals": [{"delta": {"monotonic_seconds": monotonic,
                "raw_seconds": raw, "realtime_seconds": realtime}}]}

    def test_expected_count_and_unchanged_boundary(self):
        self.assertTrue(check_clock_intervals(self.probe(3.034), self.criteria, 1)["pass"])
        self.assertFalse(check_clock_intervals(self.probe(3.036), self.criteria, 1)["pass"])
        self.assertFalse(check_clock_intervals(self.probe(), self.criteria, 2)["pass"])
        self.assertFalse(check_clock_intervals({"wsl_intervals": []}, self.criteria, 0)["pass"])

    def test_invalid_or_divergent_clocks_cannot_pass(self):
        for field in ("monotonic", "raw", "realtime"):
            for value in (math.nan, math.inf, -math.inf, 0, -1):
                with self.subTest(field=field, value=value):
                    self.assertFalse(check_clock_intervals(self.probe(**{field: value}), self.criteria, 1)["pass"])
        self.assertFalse(check_clock_intervals(self.probe(realtime=2.7), self.criteria, 1)["pass"])


if __name__ == "__main__":
    unittest.main()
