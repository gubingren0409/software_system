"""Controlled clocks/target: test accounting boundaries, never performance evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from autotuner.campaign import _run_campaign, prefix_results, strategy_for
from autotuner.core import ConfigSpace, sha256_file
from autotuner.measurement import ConfigurationEvaluator
from test_campaign import SyntheticExecutor

ROOT = Path(__file__).resolve().parents[1]


class CostRegressionTests(unittest.TestCase):
    def test_failed_configuration_gate_pause_then_success_preserves_session_cost_not_prefix(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            root, output = work / "archive", work / "campaign"
            for name in ("configs", "autotuner", "code"):
                shutil.copytree(ROOT / name, root / name, ignore=shutil.ignore_patterns("__pycache__"))
            # This is the audited legacy accounting example, not the new 120s gate.
            for saved, name in (("protocol.json", "measurement_protocol.json"), ("campaign_protocol.json", "p3_campaign_protocol.json")):
                shutil.copyfile(ROOT / "evidence/p3/campaign-e308bfb" / saved, root / "configs" / name)
            files = {}
            for path in (root / "configs").glob("*.json"):
                data = path.read_bytes()
                files[str(path.relative_to(root))] = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
            identity = work / "identity.json"
            identity.write_text(json.dumps({"content_sha": "controlled", "files": files}))
            campaign = json.loads((root / "configs/p3_campaign_protocol.json").read_text())
            space = ConfigSpace.load(root / "configs/config_space.json")
            target = MagicMock()
            target.compiler, target._compiler_version = Path("/controlled/compiler"), "controlled compiler"
            build = work / "controlled_build"
            build.mkdir()
            (build / "manifest.json").write_text('{}')
            artifact = SimpleNamespace(binary=build / "binary", binary_sha256="0" * 64)
            target.build_candidate.return_value = artifact
            target.build_reference_generator.return_value = artifact
            target.get_reference.return_value = SimpleNamespace(reference_key="controlled",
                data_sha256=campaign["expected_reference_data_sha256"], metadata={})
            clock = SimpleNamespace(now=0.0, gate_calls=0)
            passed = {"schema": "p2-resource-gate-v2", "mode": "Formal", "formal_gate": "PASS",
                      "host_minimum_available_bytes": 3 * 1024**3, "wsl_available_bytes": 3 * 1024**3,
                      "wsl_root_free_bytes": 2 * 1024**3, "host_cpu_average_percent": 0,
                      "host_cpu_maximum_percent": 0}

            def advance(seconds): clock.now += seconds
            def hash_file(path):
                return campaign["compiler_sha256"] if path == target.compiler else sha256_file(path)
            def command_run(command, **kwargs):
                if command[0] == "wslpath": return subprocess.CompletedProcess(command, 0, 'controlled.ps1\n', '')
                advance(1)
                clock.gate_calls += 1
                record = dict(passed)
                if 2 <= clock.gate_calls <= 17:
                    record.update(formal_gate="REJECT", host_minimum_available_bytes=1024)
                return subprocess.CompletedProcess(command, 0, json.dumps(record), '')
            class Executor(SyntheticExecutor):
                def evaluate(self, config, context):
                    record = super().evaluate(config, context)
                    record["target_result"].update(n=4096, checked_entries=4096**2)
                    record["raw_stdout"] = json.dumps(record["target_result"])
                    advance(record["process_wall_seconds"] + 1)
                    return record
            def measure_factory(executor, protocol, protocol_hash, destination, callback):
                return ConfigurationEvaluator(Executor(space), protocol, protocol_hash, destination, callback)
            def printed(value, **kwargs):
                event = json.loads(value)
                if event.get("event") == "configuration_complete" and event["unique_count"] == 4:
                    (output / "PAUSE_REQUEST").write_text('controlled stop after four complete groups')

            with patch("autotuner.campaign.TargetAdapter.load", return_value=target), \
                 patch("autotuner.campaign.sha256_file", side_effect=hash_file), \
                 patch("autotuner.campaign.subprocess.run", side_effect=command_run), \
                 patch("autotuner.campaign.time.monotonic", side_effect=lambda: clock.now), \
                 patch("autotuner.campaign.time.sleep", side_effect=advance), \
                 patch("autotuner.campaign.ConfigurationEvaluator", side_effect=measure_factory), \
                 patch("builtins.print", side_effect=printed):
                self.assertEqual(_run_campaign(root, output, "controlled", identity, False, 1, None, None), 2)
                paused = json.loads((output / "checkpoint.json").read_text())
                self.assertEqual(paused["status"], "resource_paused")
                self.assertEqual(paused["wait_seconds"], 467)  # setup 1 + failed gate 16 + sleeps 15*30
                self.assertEqual(_run_campaign(root, output, "controlled", identity, True, 1, None, None), 2)
            checkpoint = json.loads((output / "checkpoint.json").read_text())
            state = json.loads((output / "trajectories/00_random_20261008/checkpoint.json").read_text())
            groups = state["observations"]
            self.assertEqual(len(groups), 4)
            self.assertTrue(all(row["classification"] == "success" for row in groups))
            self.assertEqual(checkpoint["wait_seconds"], 472)  # prior 467 + resume setup 1 + four gates
            self.assertEqual(checkpoint["session_id"], paused["session_id"])
            self.assertEqual(len({row["config"]["optimization"] + str(row["config"]["block_size"]) for row in groups}), 4)
            prefix = prefix_results(strategy_for(space, "random", 12, 20261008), groups, [4])[0]
            evaluation_cost = sum(row["evaluation_wall_seconds"] for row in groups)
            self.assertEqual(prefix["configuration_evaluation_seconds"], evaluation_cost)
            self.assertEqual(prefix["configuration_start_gate_seconds"], 4)
            self.assertEqual(prefix["configuration_total_wall_seconds"], evaluation_cost + 4)
            self.assertEqual(checkpoint["active_total_seconds"], evaluation_cost + 472)
            self.assertEqual(checkpoint["active_total_seconds"] - prefix["configuration_total_wall_seconds"], 468)


if __name__ == "__main__":
    unittest.main()
