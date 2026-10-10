"""New admission/session binding; synthetic clocks and mocked setup, never long tests."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from autotuner.campaign import _run_campaign
from autotuner.core import sha256_file, sha256_json
from scripts.p3_clock_contract import (ROOT, atomic_write_json, batch_identity, load,
    probe_command, verify_clock_evidence, verify_recovery)
from test_p3_clock_contract import recovery_fixture, operation
from test_resource_policy import record, snapshot, PROTOCOL


def new_recovery_fixture(directory):
    manifest, saved = recovery_fixture(directory)
    content, session = "a" * 40, "b" * 32
    archive = "/var/tmp/matrix-autotuner-p3-policy-content-" + content
    manifest.update(schema="p3-clock-batch-v3", formal_content_commit=content, session_id=session,
        archive_directory=archive, resource_gate_purpose="Recovery",
        measurement_protocol_hash=sha256_json(PROTOCOL), resource_policy_hash=PROTOCOL["resource_gate"]["policy_hash"],
        auxiliary_files={"scripts/check_p2_resources.ps1": {"executed_sha256": sha256_file(ROOT / "scripts/check_p2_resources.ps1")}})
    saved["checkpoint"] = {"session_id": session, "preflight_identity": {"content_commit": content}}
    for name in ("campaign_before", "campaign_after"):
        atomic_write_json(directory / (name + ".json"), saved)
    manifest["campaign_before_sha256"] = sha256_file(directory / "campaign_before.json")
    atomic_write_json(directory / "measurement_protocol.json", PROTOCOL)
    policy = load(directory / "policy.json")
    policy.update(schema="p3-clock-recovery-policy-v3", resource_policy_hash=manifest["resource_policy_hash"])
    atomic_write_json(directory / "policy.json", policy)
    manifest["policy_sha256"] = sha256_file(directory / "policy.json")
    for name in ("window_A", "window_B"):
        manifest["operations"][name]["command"] = probe_command(directory / (name + ".wsl.json"), 10, archive=archive)
    atomic_write_json(directory / "manifest.json", manifest)
    atomic_write_json(directory / "resources.stdout.txt", record(snapshot((70,) * 5), "Recovery"))
    for name in ("window_A", "window_B", "resources", "frozen_files"):
        operation(directory, name, manifest)
    for name in ("window_A", "window_B"):
        atomic_write_json(directory / (name + ".check.json"), verify_clock_evidence(directory, name, check_saved=False))
    return manifest, saved


class NewSessionTests(unittest.TestCase):
    def test_recovery_warning_pass_does_not_certify_formal(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            manifest, saved = new_recovery_fixture(directory)
            result = verify_recovery(directory, saved)
            self.assertTrue(result["evidence_integrity_pass"], result)
            self.assertTrue(result["recovery_eligible"], result)
            self.assertTrue(result["recovery_resource_gate_pass"])
            self.assertIsNone(result["formal_resource_gate_pass"])
            self.assertEqual(sum(len(v["checks"]) for v in result["windows"].values()), 20)
            changed = copy.deepcopy(saved); changed["checkpoint_lf_sha256"] = "new-checkpoint"
            self.assertFalse(verify_recovery(directory, changed)["recovery_eligible"])

    def test_new_identity_and_resource_purpose_are_strict(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary); manifest, saved = new_recovery_fixture(directory)
            manifest["resource_gate_purpose"] = "Formal"
            atomic_write_json(directory / "manifest.json", manifest)
            for name in ("window_A", "window_B", "resources", "frozen_files"):
                operation(directory, name, manifest)
            self.assertFalse(verify_recovery(directory, saved)["recovery_eligible"])
        for field, value in (("session_id", "dc1c292900654d44b36a72548b95a610"),
                             ("formal_content_commit", "e308bfb873e6811c50ad685a979af345302fda8d"),
                             ("session_id", "bad"), ("archive_directory", "/mnt/e/old")):
            changed = dict(manifest); changed[field] = value
            with self.assertRaises(ValueError): batch_identity(changed)

    def test_new_session_initialization_is_fresh_bound_and_noncomputing(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary); root, output = work / "archive", work / "new-campaign"
            for name in ("configs", "autotuner", "code"):
                shutil.copytree(ROOT / name, root / name, ignore=shutil.ignore_patterns("__pycache__"))
            files = {}
            for path in (root / "configs").glob("*.json"):
                data = path.read_bytes()
                files[str(path.relative_to(root))] = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
            identity = work / "identity.json"
            identity.write_text(json.dumps({"content_sha": "new-content", "files": files}), encoding="utf-8")
            target = MagicMock(); target.compiler = Path("/controlled/compiler"); target._compiler_version = "controlled"
            campaign = json.loads((root / "configs/p3_campaign_protocol.json").read_text(encoding="utf-8"))
            def file_hash(path):
                return campaign["compiler_sha256"] if path == target.compiler else sha256_file(path)
            with patch("autotuner.campaign.TargetAdapter.load", return_value=target), \
                    patch("autotuner.campaign.sha256_file", side_effect=file_hash), \
                    patch("autotuner.campaign.subprocess.run") as run, patch("builtins.print"):
                self.assertEqual(_run_campaign(root, output, "new-content", identity, False, 2, None, None,
                                               initialize_only=True, session_id="1" * 32), 0)
                state = load(output / "checkpoint.json")
                self.assertEqual(state["session_id"], "1" * 32)
                self.assertEqual(state["preflight_identity"]["content_commit"], "new-content")
                self.assertEqual(state["completed_trajectories"], [])
                self.assertEqual(state["status"], "initialized")
                target.build_candidate.assert_not_called(); target.get_reference.assert_not_called(); run.assert_not_called()
                with self.assertRaises(ValueError):
                    _run_campaign(root, output, "new-content", identity, True, 2, None, None,
                                  initialize_only=True, session_id="2" * 32)


if __name__ == "__main__":
    unittest.main()
