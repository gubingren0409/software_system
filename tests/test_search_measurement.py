from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from autotuner.core import Config, ConfigSpace, sha256_json
from autotuner.measurement import ConfigurationEvaluator, summarize_group
from autotuner.search import GridSearch, RandomSearch, RestartGreedySearch
from autotuner.session import restore_complete_group, valid_formal_gate
from test_runner import valid_result

ROOT = Path(__file__).resolve().parents[1]


class StrategyTests(unittest.TestCase):
    def run_strategy(self, kind, budget, seed=42, failed=False):
        space = ConfigSpace.load(ROOT / "configs/config_space.json")
        strategy = kind(space, budget, seed)
        trajectory = []
        while (config := strategy.ask()) is not None:
            trajectory.append(config)
            strategy.tell(config, {"classification": "invalid" if failed else "success",
                                   "score_seconds": None if failed else 100 - space.all().index(config)})
        return strategy, trajectory

    def test_unique_budget_reproducibility_and_prefixes(self):
        for kind in (GridSearch, RandomSearch, RestartGreedySearch):
            for budget in (4, 8, 12, 20):
                strategy, trajectory = self.run_strategy(kind, budget)
                self.assertEqual(len(trajectory), budget)
                self.assertEqual(len(set(trajectory)), budget)
                self.assertEqual(trajectory, self.run_strategy(kind, budget)[1])
                self.assertEqual(strategy.best(), min(trajectory, key=strategy.score))
            full = self.run_strategy(kind, 12)[1]
            self.assertEqual(self.run_strategy(kind, 4)[1], full[:4])
            self.assertEqual(self.run_strategy(kind, 8)[1], full[:8])

    def test_failed_observations_consume_budget_but_never_win(self):
        for kind in (GridSearch, RandomSearch, RestartGreedySearch):
            strategy, trajectory = self.run_strategy(kind, 12, failed=True)
            self.assertEqual(len(set(trajectory)), 12)
            self.assertIsNone(strategy.best())

    def test_greedy_has_all_seven_single_parameter_neighbors(self):
        space = ConfigSpace.load(ROOT / "configs/config_space.json")
        strategy = RestartGreedySearch(space, 20)
        for config in space.all():
            self.assertEqual(len(strategy.neighbors(config)), 7)
            for other in strategy.neighbors(config):
                self.assertEqual((other.optimization != config.optimization) +
                                 (other.block_size != config.block_size), 1)


class StubExecutor:
    def __init__(self, failure_index=None):
        self.calls = []
        self.failure_index = failure_index

    def evaluate(self, config, context):
        index = len(self.calls)
        self.calls.append(context)
        parsed = valid_result()
        parsed.update(n=130, block_size=config.block_size, seed=20261008, checked_entries=130**2)
        value = float(index + 1)
        parsed["elapsed_seconds"] = value
        failed = index == self.failure_index
        return {"classification": "invalid" if failed else "success",
                "score_seconds": None if failed else value, "source": "fresh_measurement",
                "run_id": str(index), "returncode": 0, "timed_out": False,
                "target_result": parsed, "raw_stdout": json.dumps(parsed),
                "context": {"force_remeasure": context.force_remeasure, "protocol_hash": context.protocol_hash},
                "process_wall_seconds": value}


class MeasurementTests(unittest.TestCase):
    def protocol(self):
        data = json.loads((ROOT / "configs/measurement_protocol.json").read_text())
        data["target_matrix_n"] = 130
        return data

    def evaluate(self, failure=None):
        stub = StubExecutor(failure)
        protocol = self.protocol()
        with tempfile.TemporaryDirectory() as directory:
            result = ConfigurationEvaluator(stub, protocol, sha256_json(protocol), Path(directory)).evaluate(Config("O2", 8))
        return stub, result

    def test_complete_group_is_five_fresh_samples_after_warmup(self):
        stub, result = self.evaluate()
        self.assertEqual(len(stub.calls), 6)
        self.assertTrue(all(item.force_remeasure for item in stub.calls))
        self.assertEqual(result["measured_compute_seconds"], [2., 3., 4., 5., 6.])
        self.assertEqual(result["score_seconds"], 4.)
        self.assertEqual(restore_complete_group(result, self.protocol()), result)

    def test_failure_never_scores_successful_subset(self):
        for index in (0, 3, 5):
            stub, result = self.evaluate(index)
            self.assertIsNone(result["score_seconds"])
            self.assertEqual(len(stub.calls), index + 1)

    def test_checkpoint_rejects_partial_and_cache_and_modified_raw_output(self):
        _, original = self.evaluate()
        for change in ("partial", "cached", "raw"):
            result = copy.deepcopy(original)
            if change == "partial": result["samples"].pop()
            elif change == "cached": result["samples"][2]["source"] = "performance_cache"
            else: result["samples"][2]["raw_stdout"] = "{}"
            with self.assertRaises(ValueError):
                restore_complete_group(result, self.protocol())

    def test_formal_gate_is_not_inferred_from_exit_status(self):
        protocol = self.protocol()
        valid = {"schema": "p2-resource-gate-v2", "mode": "Formal", "formal_gate": "PASS",
                 "host_minimum_available_bytes": 2**31, "wsl_available_bytes": 2**31,
                 "wsl_root_free_bytes": 2**30, "host_cpu_average_percent": 5,
                 "host_cpu_maximum_percent": 10}
        self.assertTrue(valid_formal_gate(valid, protocol))
        for field, value in (("formal_gate", "REJECT"), ("host_minimum_available_bytes", 0),
                             ("mode", "Snapshot"), ("host_cpu_maximum_percent", 21)):
            altered = dict(valid, **{field: value})
            self.assertFalse(valid_formal_gate(altered, protocol))


if __name__ == "__main__":
    unittest.main()
