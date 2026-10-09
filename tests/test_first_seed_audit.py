"""Postprocessing costs must not silently become end-to-end prefix costs."""
import unittest
import math
import hashlib
from pathlib import Path
import tempfile

from scripts.audit_p3_first_seed import activity_costs, check_clock_intervals, verify_sample_prefix


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


class FirstSeedPrefixTests(unittest.TestCase):
    def test_git_line_ending_conversion_is_explicit_but_content_changes_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            sample = Path(temporary) / "samples.jsonl"
            identity = Path(temporary) / "identity.json"
            original = b'{"run_id":"first","stdout":"a\\nb"}\r\n'
            prefix = {"bytes": len(original), "sha256": hashlib.sha256(original).hexdigest()}
            sample.write_bytes(original + b'{"run_id":"later"}\n')
            self.assertTrue(verify_sample_prefix(sample, prefix, identity)["raw_bytes_match"])
            sample.write_bytes(original.replace(b"\r\n", b"\n") + b'{"run_id":"later"}\n')
            result = verify_sample_prefix(sample, prefix, identity)
            self.assertFalse(result["raw_bytes_match"])
            self.assertTrue(result["lf_normalized_text_match"])
            sample.write_bytes(sample.read_bytes().replace(b'first', b'wrong'))
            with self.assertRaisesRegex(ValueError, "content differs"):
                verify_sample_prefix(sample, prefix, identity)

    def test_missing_normalized_identity_cannot_bless_different_runtime_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            sample = Path(temporary) / "samples.jsonl"
            sample.write_bytes(b'{"run_id":"wrong"}\n')
            with self.assertRaisesRegex(ValueError, "raw sample prefix differs"):
                verify_sample_prefix(sample, {"bytes": 1, "sha256": "0" * 64},
                                     Path(temporary) / "identity.json")


if __name__ == "__main__":
    unittest.main()
