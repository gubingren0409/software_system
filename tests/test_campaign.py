from __future__ import annotations

import copy
import json
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import uuid
from unittest.mock import MagicMock, patch

from autotuner.campaign import _run_campaign, prefix_results, replay_trajectory, strategy_for, validate_terminal
from autotuner.core import ConfigSpace, sha256_json
from autotuner.measurement import ConfigurationEvaluator
from test_runner import valid_result

ROOT = Path(__file__).resolve().parents[1]


class SyntheticExecutor:
    """Opaque controlled target, not measurements or a precomputed Grid oracle."""

    def __init__(self, space, fail_first=False):
        self.space, self.fail_first, self.calls = space, fail_first, 0

    def evaluate(self, config, context):
        failed = self.fail_first and self.calls == 0
        value = float(100 - self.space.all().index(config))
        self.calls += 1
        parsed = valid_result()
        parsed.update(n=130, block_size=config.block_size, seed=20261008,
                      checked_entries=130**2, elapsed_seconds=value)
        return {"config": config.__dict__, "run_id": uuid.uuid4().hex,
                "classification": "crash" if failed else "success",
                "score_seconds": None if failed else value,
                "returncode": -11 if failed else 0, "timed_out": False,
                "target_result": {} if failed else parsed,
                "raw_stdout": "" if failed else json.dumps(parsed), "source": "fresh_measurement",
                "context": {"force_remeasure": context.force_remeasure,
                            "protocol_hash": context.protocol_hash}, "process_wall_seconds": value}


class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.space = ConfigSpace.load(ROOT / "configs/config_space.json")
        self.protocol = json.loads((ROOT / "configs/measurement_protocol.json").read_text())
        self.protocol.pop("timing_protocol", None) # Preserve the synthetic legacy result contract.
        self.protocol["target_matrix_n"] = 130
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)

    def trajectory(self, algorithm, count=12, fail_first=False):
        job = {"algorithm": algorithm, "seed": 20261008}
        strategy = strategy_for(self.space, algorithm, 12, job["seed"])
        evaluator = ConfigurationEvaluator(SyntheticExecutor(self.space, fail_first), self.protocol,
                                           sha256_json(self.protocol), Path(self.temporary.name))
        groups = []
        for _ in range(count):
            config = strategy.ask()
            group = evaluator.evaluate(config)
            validate_terminal(group, self.protocol)
            groups.append(group)
            strategy.tell(config, group)
        return job, strategy, groups

    def test_replay_preserves_own_decisions_and_rng_for_both_algorithms(self):
        for algorithm in ("random", "greedy"):
            job, original, groups = self.trajectory(algorithm)
            for prefix in (0, 1, 4, 8, 12):
                replayed = replay_trajectory(self.space, job, 12, groups[:prefix], self.protocol)
                for group in groups[prefix:]:
                    config = replayed.ask()
                    self.assertEqual(config.__dict__, group["config"])
                    replayed.tell(config, group)
                self.assertIsNone(replayed.ask())
                self.assertEqual(replayed.best(), original.best())

    def test_failed_configuration_consumes_unique_budget_and_does_not_score(self):
        for algorithm in ("random", "greedy"):
            job, strategy, groups = self.trajectory(algorithm, fail_first=True)
            self.assertIsNone(groups[0]["score_seconds"])
            self.assertEqual(len(strategy.observations), 12)
            self.assertEqual(len({tuple(group["config"].values()) for group in groups}), 12)
            self.assertEqual(prefix_results(strategy, groups, [4, 8, 12])[0]["valid_count"], 3)
            replayed = replay_trajectory(self.space, job, 12, groups, self.protocol)
            self.assertEqual(replayed.best(), strategy.best())

    def test_prefixes_use_only_own_successes(self):
        _, strategy, groups = self.trajectory("random")
        for result in prefix_results(strategy, groups, [4, 8, 12]):
            expected = min(groups[:result["budget"]], key=lambda item: item["score_seconds"])
            self.assertEqual(result["best_config"], expected["config"])
            self.assertEqual(result["median_seconds"], expected["score_seconds"])

    def test_equal_scores_choose_canonical_configuration_without_extra_observations(self):
        strategy = strategy_for(self.space, "random", 12, 20261008)
        groups = [{"config": config.__dict__, "classification": "success", "score_seconds": 1.0,
                   "evaluation_wall_seconds": 6.0, "compute_total_seconds": 6.0}
                  for config in reversed(self.space.all()[:12])]
        rows = prefix_results(strategy, groups, [4, 8, 12])
        self.assertEqual(rows[-1]["best_config"], self.space.all()[0].__dict__)
        self.assertEqual(len(strategy.observations), 0)

    def test_modified_statistics_partial_groups_and_performance_cache_are_rejected(self):
        _, _, groups = self.trajectory("random", count=1)
        for change in ("statistic", "partial", "cache", "role", "identity"):
            group = copy.deepcopy(groups[0])
            if change == "statistic": group["statistics"]["mean_seconds"] += 1
            if change == "partial": group["samples"].pop()
            if change == "cache": group["samples"][1]["source"] = "performance_cache"
            if change == "role": group["samples"][0]["role"] = "measurement"
            if change == "identity": group["samples"][0]["config"]["block_size"] = 1
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_terminal(group, self.protocol)

    def test_terminal_failures_cannot_fabricate_score_or_success(self):
        _, _, groups = self.trajectory("random", count=1, fail_first=True)
        for change in ("score", "classification", "raw_exit"):
            group = copy.deepcopy(groups[0])
            if change == "score": group["score_seconds"] = 0.001
            if change == "classification": group["classification"] = "success"
            if change == "raw_exit": group["samples"][0]["returncode"] = 0
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_terminal(group, self.protocol)

    def test_foreign_trajectory_order_cannot_be_restored_as_own(self):
        job, _, groups = self.trajectory("random")
        swapped = [groups[1], groups[0], *groups[2:]]
        with self.assertRaises(ValueError):
            replay_trajectory(self.space, job, 12, swapped, self.protocol)
        other = strategy_for(self.space, "random", 12, 20261009)
        self.assertEqual(len(other.observations), 0)
        self.assertIsNone(other.best())

    def test_campaign_pairs_frozen_seeds_and_keeps_original_measurement(self):
        campaign = json.loads((ROOT / "configs/p3_campaign_protocol.json").read_text())
        search = json.loads((ROOT / "configs/search_protocol.json").read_text())
        protocol = json.loads((ROOT / "configs/measurement_protocol.json").read_text())
        expected = {(algorithm, seed) for algorithm in ("random", "greedy") for seed in search["search_seeds"]}
        actual = [(job["algorithm"], job["seed"]) for job in campaign["schedule"]]
        self.assertEqual(len(actual), 10)
        self.assertEqual(set(actual), expected)
        self.assertEqual(campaign["measurement_protocol_hash"], sha256_json(protocol))
        self.assertEqual(campaign["search_protocol_hash"], sha256_json(search))
        self.assertEqual(campaign["unique_budget_per_trajectory"], 12)

    def test_rejected_setup_saves_identity_and_resumes_without_building_or_measuring(self):
        root = Path(self.temporary.name) / "archive"
        for directory in ("configs", "autotuner", "code"):
            shutil.copytree(ROOT / directory, root / directory, ignore=shutil.ignore_patterns("__pycache__"))
        # Keep this historical 16-attempt regression explicitly on its v2 protocol.
        for saved, name in (("protocol.json", "measurement_protocol.json"), ("campaign_protocol.json", "p3_campaign_protocol.json")):
            shutil.copyfile(ROOT / "evidence/p3/campaign-e308bfb" / saved, root / "configs" / name)
        identity_files = {}
        for path in (root / "configs").glob("*.json"):
            data = path.read_bytes()
            identity_files[str(path.relative_to(root))] = hashlib.sha1(
                b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        identity = Path(self.temporary.name) / "git_identity.json"
        identity.write_text(json.dumps({"content_sha": "controlled", "files": identity_files}))
        target = MagicMock()
        target.compiler = Path("/controlled/compiler")
        target._compiler_version = "controlled compiler"
        campaign = json.loads((root / "configs/p3_campaign_protocol.json").read_text())
        from autotuner.core import sha256_file

        def hash_file(path):
            if path == target.compiler: return campaign["compiler_sha256"]
            relative = str(path.relative_to(root)).replace(chr(92), "/")
            return campaign["unchanged_source_sha256"].get(relative, sha256_file(path))

        def command_run(command, **kwargs):
            if command[0] == "wslpath":
                return subprocess.CompletedProcess(command, 0, "controlled.ps1\n", "")
            return subprocess.CompletedProcess(command, 0, '{"formal_gate":"PASS"}', "")

        output = Path(self.temporary.name) / "campaign"
        with patch("autotuner.campaign.TargetAdapter.load", return_value=target), \
             patch("autotuner.campaign.sha256_file", side_effect=hash_file), \
             patch("autotuner.campaign.subprocess.run", side_effect=command_run), \
             patch("autotuner.campaign.time.sleep"), patch("builtins.print"):
            self.assertEqual(_run_campaign(root, output, "controlled", identity, False, 1, None, None), 2)
            checkpoint = json.loads((output / "checkpoint.json").read_text())
            self.assertEqual(checkpoint["status"], "resource_paused")
            self.assertIn("preflight_identity", checkpoint)
            self.assertNotIn("fingerprint", checkpoint)
            self.assertEqual(_run_campaign(root, output, "controlled", identity, True, 1, None, None), 2)
            self.assertEqual(len(list((output / "gates").glob("*.json"))), 32)
            target.build_candidate.assert_not_called()
            target.get_reference.assert_not_called()


if __name__ == "__main__":
    unittest.main()
