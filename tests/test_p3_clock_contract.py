"""Synthetic contract regressions: no WSL sleep probes or formal targets."""
import copy
import hashlib
import json
import math
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts.p3_clock_contract import (ARCHIVE, CRITERIA_SHA, FORMAL_CONTENT, PROBE_SHA, ROOT, SESSION,
    TOLERANCES, acceptance, acceptance_exit, atomic_write_json, check_clock_intervals, load,
    campaign_command, probe_command, sha256_file, verify_batch_binding, verify_clock_evidence, verify_recovery, wsl_path)
from scripts.start_p3_first_seed import first_failure
from scripts.audit_p3_first_seed import campaign_timing_certified, first_seed_execution_complete
from scripts.record_p3_first_seed_checks import review_result


def probe(count=3, duration_ns=3_000_000_000):
    base = 1_791_535_359_971_989_073  # Far beyond exactly representable float integers.
    before = {name + "_ns": base for name in ("monotonic", "raw", "realtime", "boottime")}
    after = {key: value + duration_ns for key, value in before.items()}
    delta = {key.removesuffix("_ns") + "_seconds": duration_ns / 1e9 for key in before}
    return {"schema": "p2-clock-probe-v1", "captured_at": "2026-10-09T00:00:00+00:00",
        "script_sha256": PROBE_SHA, "system_settings_modified": False,
        "command": ["python3", "scripts/check_p2_clocks.py"],
        "commands": [{"command": ["cat"], "stdout": "test", "stderr": "", "returncode": 0}],
        "clock_info": {"time": "synthetic", "monotonic": "synthetic"},
        "wsl_intervals": [copy.deepcopy({"before": before, "after": after, "delta": delta}) for _ in range(count)]}


def operation(directory, name, manifest, start=10_000_000, end=20_000_000):
    op = {"schema": "p3-captured-operation-v2", "batch_id": manifest["batch_id"],
        "operation_kind": name, "operation_id": "a" * 32, "command": manifest["operations"][name]["command"],
        "pid": 123, "returncode": 0, "timed_out": False, "timeout_seconds": manifest["operations"][name]["timeout_seconds"],
        "manifest_sha256": sha256_file(directory / "manifest.json"),
        "start_utc_ns": 1_791_535_359_971_989_073, "end_utc_ns": 1_791_535_360_971_989_073,
        "qpc_start": start, "qpc_end": end, "qpc_frequency": 10_000_000, "utc_seconds": 1.0,
        "qpc_seconds": (end - start) / 10_000_000}
    for stream in ("stdout", "stderr"):
        op[stream + "_path"] = name + "." + stream + ".txt"
        op[stream + "_sha256"] = sha256_file(directory / op[stream + "_path"])
        op[stream + "_lf_sha256"] = hashlib.sha256((directory / op[stream + "_path"]).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    atomic_write_json(directory / (name + ".operation.json"), op)
    return op


def fixture(directory, name="clock_before", count=3):
    output = directory / (name + ".wsl.json")
    spec = {"command": probe_command(output, count), "intervals": count, "seconds": 3,
            "output_file": output.name, "timeout_seconds": 120}
    manifest = {"schema": "p3-clock-batch-v2", "batch_id": "b" * 32, "formal_content_commit": FORMAL_CONTENT,
        "repo_root_at_run": str(ROOT), "evidence_directory_at_run": str(directory),
        "session_id": SESSION, "criteria_sha256": CRITERIA_SHA, "probe_script_sha256": PROBE_SHA,
        "checker_sha256": sha256_file(ROOT / "scripts/p3_clock_contract.py"), "operations": {name: spec}}
    atomic_write_json(directory / "manifest.json", manifest)
    raw = probe(count)
    raw["command"] = ["/usr/bin/python3", "scripts/check_p2_clocks.py", "--intervals", str(count), "--seconds", "3",
                      "--skip-host", "--output", wsl_path(output)]
    atomic_write_json(output, raw)
    atomic_write_json(directory / (name + ".stdout.txt"), raw)
    (directory / (name + ".stderr.txt")).write_bytes(b"")
    op = operation(directory, name, manifest)
    return manifest, raw, op


def recovery_fixture(directory, skew=False):
    manifest, raw, _ = fixture(directory, "window_A", 10)
    manifest["purpose"] = "recover"
    manifest["operations"]["window_B"] = {"command": probe_command(directory / "window_B.wsl.json", 10),
        "intervals": 10, "seconds": 3, "output_file": "window_B.wsl.json", "timeout_seconds": 120}
    for name in ("resources", "frozen_files"):
        manifest["operations"][name] = {"command": ["synthetic", name], "timeout_seconds": 90}
    manifest["frozen_files_expected"] = {"synthetic_source": "0" * 64}
    snapshot = {"checkpoint": {"session_id": SESSION, "fingerprint": {"content_commit": FORMAL_CONTENT}},
                "checkpoint_lf_sha256": "s", "trajectories": {}}
    for name in ("campaign_before", "campaign_after"):
        atomic_write_json(directory / (name + ".json"), snapshot)
    manifest["campaign_before_sha256"] = sha256_file(directory / "campaign_before.json")
    policy = {"schema": "p3-clock-recovery-policy-v2", "batch_id": manifest["batch_id"], "windows": 2,
        "intervals_per_window": 10, "seconds_per_interval": 3, "total_interval_count": 20,
        "total_sleep_budget_seconds": 60, "criteria_sha256": CRITERIA_SHA,
        "all_twenty_required": True, "no_extra_recovery_attempts": True}
    atomic_write_json(directory / "policy.json", policy)
    manifest["policy_sha256"] = sha256_file(directory / "policy.json")
    atomic_write_json(directory / "manifest.json", manifest)
    gate = {"schema": "p2-resource-gate-v2", "mode": "Formal", "formal_gate": "PASS",
        "host_minimum_available_bytes": 3 * 2**30, "wsl_available_bytes": 3 * 2**30,
        "wsl_root_free_bytes": 5 * 2**30, "host_cpu_average_percent": 1, "host_cpu_maximum_percent": 2}
    atomic_write_json(directory / "resources.stdout.txt", gate)
    (directory / "frozen_files.stdout.txt").write_text("0" * 64 + "  synthetic_source\n")
    for name in ("resources", "frozen_files"):
        (directory / (name + ".stderr.txt")).write_bytes(b"")
        operation(directory, name, manifest)
    for name in ("window_A", "window_B"):
        value = copy.deepcopy(raw)
        value["command"][-1] = wsl_path(directory / (name + ".wsl.json"))
        if skew and name == "window_B":
            row = value["wsl_intervals"][9]
            row["after"]["monotonic_ns"] += 40_000_000
            row["delta"]["monotonic_seconds"] = 3.04
        atomic_write_json(directory / (name + ".wsl.json"), value)
        atomic_write_json(directory / (name + ".stdout.txt"), value)
        (directory / (name + ".stderr.txt")).write_bytes(b"")
        operation(directory, name, manifest)
        atomic_write_json(directory / (name + ".check.json"), verify_clock_evidence(directory, name, check_saved=False))
    return manifest, snapshot


class StrictClockTests(unittest.TestCase):
    def test_empty_missing_wrong_schema_or_count_rejected(self):
        for value, count in ((probe(0), 3), (probe(2), 3), (probe(4), 3), (probe(), 0), (probe(), True), ({}, 3)):
            self.assertFalse(check_clock_intervals(value, TOLERANCES, count)["pass"])
        for key in ("schema", "clock_info", "commands", "command", "captured_at"):
            value = probe()
            del value[key]
            self.assertFalse(check_clock_intervals(value, TOLERANCES, 3)["pass"])

    def test_nonfinite_zero_negative_wrong_types_rejected(self):
        for invalid in (0, -1, math.nan, math.inf, -math.inf, True, "3", None):
            for clock in ("raw", "monotonic", "realtime", "boottime"):
                value = probe()
                value["wsl_intervals"][0]["delta"][clock + "_seconds"] = invalid
                with self.subTest(invalid=invalid, clock=clock):
                    self.assertFalse(check_clock_intervals(value, TOLERANCES, 3)["pass"])

    def test_integer_ns_precision_and_float_endpoint_rejection(self):
        value = probe(1, 7)
        result = check_clock_intervals(value, TOLERANCES, 1)
        self.assertTrue(result["pass"])
        self.assertEqual(result["checks"][0]["delta"]["raw_seconds"], 7e-9)
        value["wsl_intervals"][0]["before"]["raw_ns"] = float(value["wsl_intervals"][0]["before"]["raw_ns"])
        self.assertFalse(check_clock_intervals(value, TOLERANCES, 1)["pass"])

    def test_saved_delta_and_source_tolerances_must_match(self):
        value = probe()
        value["wsl_intervals"][0]["delta"]["monotonic_seconds"] += 1e-9
        self.assertFalse(check_clock_intervals(value, TOLERANCES, 3)["pass"])
        value = probe()
        value["script_sha256"] = "0" * 64
        self.assertFalse(check_clock_intervals(value, TOLERANCES, 3)["pass"])
        self.assertFalse(check_clock_intervals(probe(), {**TOLERANCES, "monotonic_raw_relative_tolerance": 0.02}, 3)["pass"])

    def test_nonfinite_duplicate_json_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.json"
            for text in ('{"a":NaN}', '{"a":Infinity}', '{"a":1,"a":2}'):
                path.write_text(text)
                with self.assertRaises(ValueError):
                    load(path)


class ClockEvidenceTests(unittest.TestCase):
    def test_archived_eol_conversion_is_distinct_from_stream_content_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            fixture(directory)
            answer = verify_clock_evidence(directory, "clock_before")
            atomic_write_json(directory / "clock_before.check.json", answer)
            stdout = directory / "clock_before.stdout.txt"
            stdout.write_bytes(stdout.read_bytes().replace(b"\n", b"\r\n"))
            self.assertTrue(verify_clock_evidence(directory, "clock_before")["pass"])
            with tempfile.TemporaryDirectory() as moved:
                destination = Path(moved) / "relocated_archive"
                shutil.copytree(directory, destination)
                self.assertTrue(verify_clock_evidence(destination, "clock_before")["pass"])
            stdout.write_bytes(stdout.read_bytes().replace(b"synthetic", b"wrong"))
            self.assertFalse(verify_clock_evidence(directory, "clock_before")["pass"])

    def test_success_and_saved_pass_contradiction(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            fixture(directory)
            answer = verify_clock_evidence(directory, "clock_before")
            self.assertTrue(answer["pass"], answer)
            atomic_write_json(directory / "clock_before.check.json", answer)
            self.assertTrue(verify_clock_evidence(directory, "clock_before")["pass"])
            answer["pass"] = False
            atomic_write_json(directory / "clock_before.check.json", answer)
            result = verify_clock_evidence(directory, "clock_before")
            self.assertFalse(result["evidence_integrity_pass"])
            self.assertIn("contradicts", result["errors"][-1])

    def test_bad_criteria_probe_operation_and_stale_batch(self):
        for key in ("criteria_sha256", "probe_script_sha256", "checker_sha256", "batch_id"):
            with tempfile.TemporaryDirectory() as temp:
                directory = Path(temp)
                manifest, raw, op = fixture(directory)
                manifest[key] = "0" * 64
                atomic_write_json(directory / "manifest.json", manifest)
                result = verify_clock_evidence(directory, "clock_before")
                self.assertFalse(result["pass"], key)
        for change in ({"returncode": 124, "timed_out": True}, {"returncode": "unknown"},
                       {"returncode": False}, {"operation_kind": "old_batch"}):
            with tempfile.TemporaryDirectory() as temp:
                directory = Path(temp)
                manifest, raw, op = fixture(directory)
                op.update(change)
                atomic_write_json(directory / "clock_before.operation.json", op)
                self.assertFalse(verify_clock_evidence(directory, "clock_before")["pass"])

    def test_raw_output_mutation_is_rejected_not_just_saved_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            fixture(directory)
            answer = verify_clock_evidence(directory, "clock_before")
            atomic_write_json(directory / "clock_before.check.json", answer)
            raw = load(directory / "clock_before.wsl.json")
            raw["wsl_intervals"][0]["delta"]["raw_seconds"] = 0
            atomic_write_json(directory / "clock_before.wsl.json", raw)
            self.assertFalse(verify_clock_evidence(directory, "clock_before")["pass"])

    def test_batch_checkpoint_binding_rejects_newer_records(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            snapshot = {"checkpoint": {"session_id": SESSION, "fingerprint": {"content_commit": FORMAL_CONTENT}},
                "checkpoint_sha256": "r", "checkpoint_lf_sha256": "r", "trajectories": {"00_random_20261008": {
                    "checkpoint": {"observations": []}, "checkpoint_sha256": "t", "checkpoint_lf_sha256": "t",
                    "sample_count": 1, "run_ids": ["old"], "sample_line_sha256": ["old_hash"], "samples_lf_sha256": "s"}}}
            atomic_write_json(directory / "campaign_before.json", snapshot)
            atomic_write_json(directory / "campaign_after.json", snapshot)
            atomic_write_json(directory / "manifest.json", {"batch_id": "b", "campaign_before_sha256": sha256_file(directory / "campaign_before.json")})
            atomic_write_json(directory / "controller.json", {"batch_id": "b", "campaign_invoked": False,
                "campaign_after_sha256": sha256_file(directory / "campaign_after.json")})
            self.assertTrue(verify_batch_binding(directory, snapshot)["evidence_integrity_pass"])
            later = copy.deepcopy(snapshot)
            later["trajectories"]["00_random_20261008"]["run_ids"].append("new")
            with self.assertRaisesRegex(ValueError, "Stale"):
                verify_batch_binding(directory, later)

    def test_actual_call_binding_requires_matching_command_and_clock_order(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            manifest, raw, _ = fixture(directory)
            manifest["operations"]["clock_after"] = {"command": probe_command(directory / "clock_after.wsl.json", 3),
                "intervals": 3, "seconds": 3, "output_file": "clock_after.wsl.json", "timeout_seconds": 120}
            manifest["operations"]["campaign"] = {"command": campaign_command(), "timeout_seconds": None}
            before = {"checkpoint": {"session_id": SESSION, "fingerprint": {"content_commit": FORMAL_CONTENT}},
                "checkpoint_sha256": "r1", "checkpoint_lf_sha256": "r1", "trajectories": {"00_random_20261008": {
                    "checkpoint": {"observations": []}, "checkpoint_sha256": "t1", "checkpoint_lf_sha256": "t1",
                    "sample_count": 1, "run_ids": ["old"], "sample_line_sha256": ["h1"], "samples_lf_sha256": "s1"}}}
            after = copy.deepcopy(before)
            after["checkpoint_sha256"] = after["checkpoint_lf_sha256"] = "r2"
            after["trajectories"]["00_random_20261008"].update(sample_count=2, run_ids=["old", "new"],
                sample_line_sha256=["h1", "h2"], samples_lf_sha256="s2")
            atomic_write_json(directory / "campaign_before.json", before)
            atomic_write_json(directory / "campaign_after.json", after)
            manifest["campaign_before_sha256"] = sha256_file(directory / "campaign_before.json")
            atomic_write_json(directory / "manifest.json", manifest)
            for position, name in enumerate(("clock_before", "campaign", "clock_after")):
                if name != "campaign":
                    value = copy.deepcopy(raw)
                    value["command"][-1] = wsl_path(directory / (name + ".wsl.json"))
                    atomic_write_json(directory / (name + ".wsl.json"), value)
                    atomic_write_json(directory / (name + ".stdout.txt"), value)
                else:
                    (directory / (name + ".stdout.txt")).write_bytes(b"")
                (directory / (name + ".stderr.txt")).write_bytes(b"")
                operation(directory, name, manifest, (position * 2 + 1) * 10_000_000,
                          (position * 2 + 2) * 10_000_000)
            atomic_write_json(directory / "controller.json", {"batch_id": manifest["batch_id"],
                "campaign_invoked": True, "campaign_returncode": 0, "pre_clock_pass": True,
                "campaign_after_sha256": sha256_file(directory / "campaign_after.json")})
            for phase in ("clock_before", "clock_after"):
                self.assertTrue(verify_clock_evidence(directory, phase)["pass"])
            self.assertEqual(verify_batch_binding(directory, after)["new_run_ids"], ["new"])
            operation(directory, "campaign", manifest, 70_000_000, 80_000_000)
            with self.assertRaisesRegex(ValueError, "order"):
                verify_batch_binding(directory, after)

    def test_recovery_requires_twenty_intervals_and_current_checkpoint(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            manifest, snapshot = recovery_fixture(directory)
            result = verify_recovery(directory, snapshot)
            self.assertTrue(result["recovery_eligible"], result)
            stale = copy.deepcopy(snapshot)
            stale["checkpoint_lf_sha256"] = "newer"
            self.assertFalse(verify_recovery(directory, stale)["recovery_eligible"])
            manifest["operations"]["window_B"]["intervals"] = 9
            atomic_write_json(directory / "manifest.json", manifest)
            self.assertIn("10x3", verify_recovery(directory)["errors"][0])

    def test_single_bad_interval_rejects_whole_recovery_without_filtering(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            _, snapshot = recovery_fixture(directory, skew=True)
            result = verify_recovery(directory, snapshot)
            self.assertTrue(result["evidence_integrity_pass"], result)
            self.assertFalse(result["timing_checks_pass"])
            self.assertFalse(result["recovery_eligible"])
            self.assertEqual(sum(len(window["checks"]) for window in result["windows"].values()), 20)


class AcceptanceTests(unittest.TestCase):
    def test_recovery_never_substitutes_for_actual_campaign_boundaries(self):
        clocks = {name: {"pass": True} for name in ("clock_before", "clock_after")}
        recovery = {"recovery_eligible": True}
        self.assertFalse(campaign_timing_certified("recover", clocks, recovery, False))
        self.assertFalse(campaign_timing_certified("resume", clocks, recovery, False))
        self.assertFalse(campaign_timing_certified("resume", {}, recovery, True))
        self.assertTrue(campaign_timing_certified("resume", clocks, recovery, True))
        clocks["clock_after"]["pass"] = False
        self.assertFalse(campaign_timing_certified("resume", clocks, recovery, True))

    def test_clock_identity_and_resource_failures_are_not_mislabeled(self):
        from scripts.start_p3_first_seed import recovery_outcome
        self.assertEqual(recovery_outcome(True, True, True), ("P3_RECOVERY_ELIGIBLE", None))
        self.assertEqual(recovery_outcome(True, True, False)[0], "P3_RESOURCE_BLOCKED")
        self.assertEqual(recovery_outcome(False, True, True)[0], "P3_IDENTITY_BLOCKED")
        self.assertEqual(recovery_outcome(False, False, False)[0], "P3_CLOCK_BLOCKED")

    def test_criteria_path_is_auxiliary_not_original_formal_archive(self):
        from scripts.start_p3_first_seed import frozen_source_expectations
        expected = frozen_source_expectations({"existing_formal_file": "original_hash"}, ROOT)
        self.assertNotIn(ARCHIVE + "/configs/timing_audit_protocol.json", expected)
        self.assertEqual(expected[wsl_path(ROOT / "configs/timing_audit_protocol.json")], CRITERIA_SHA)
        self.assertEqual(expected[ARCHIVE + "/scripts/check_p2_clocks.py"], PROBE_SHA)
        self.assertEqual(expected["existing_formal_file"], "original_hash")
        self.assertTrue((ROOT / "configs/timing_audit_protocol.json").is_file())

    def test_recorder_summaries_are_actual_in_both_modes(self):
        finished = acceptance(True, True, True)
        partial = acceptance(True, False, False)
        result = review_result(finished, "complete", True)
        self.assertTrue(result["comparison_ready"])
        self.assertEqual(result["returncode"], 0)
        self.assertEqual(review_result(partial, "complete", True)["returncode"], 2)
        self.assertEqual(review_result(partial, "incomplete", True)["returncode"], 0)
        self.assertFalse(review_result(acceptance(False, True, True), "complete", True)["review_checks_pass"])

    def test_completed_two_trajectories_need_all_six_retested_prefixes(self):
        result = {"completed_trajectory_count": 2, "trajectories": [
            {"name": f"{index:02d}_{algorithm}_20261008", "unique_count": 12,
             "job": {"seed": 20261008}, "trajectory_status": "complete"}
            for index, algorithm in enumerate(("random", "greedy"))], "prefix_rows": [
            {"algorithm": algorithm, "search_seed": 20261008, "budget": budget,
             "own_median_seconds": 2.0, "independent_retest_median_seconds": 2.1}
            for algorithm in ("random", "greedy") for budget in (4, 8, 12)]}
        checkpoint = {"status": "batch_complete"}
        self.assertTrue(first_seed_execution_complete(result, checkpoint))
        self.assertEqual(acceptance_exit(acceptance(True, first_seed_execution_complete(result, checkpoint), True), True), 0)
        for mutation in ("missing_retest", "wrong_seed", "partial", "duplicate_prefix"):
            broken = copy.deepcopy(result)
            if mutation == "missing_retest":
                broken["prefix_rows"][0]["independent_retest_median_seconds"] = None
            elif mutation == "wrong_seed":
                broken["trajectories"][0]["job"]["seed"] = 20261009
            elif mutation == "partial":
                broken["trajectories"][0]["unique_count"] = 3
            else:
                broken["prefix_rows"][0] = copy.deepcopy(broken["prefix_rows"][1])
            self.assertFalse(first_seed_execution_complete(broken, checkpoint), mutation)

    def test_incomplete_and_complete_exit_states(self):
        self.assertEqual(acceptance_exit(acceptance(True, False, True), True), 2)
        self.assertEqual(acceptance_exit(acceptance(True, True, True), True), 0)
        self.assertEqual(acceptance_exit(acceptance(True, True, False), True), 2)
        self.assertEqual(acceptance_exit(acceptance(False, True, True), True), 1)
        with self.assertRaises(ValueError):
            acceptance(1, True, True)

    def test_pre_rejection_reason_survives_post_failure(self):
        state = {"failure_reason": None, "additional_failures": []}
        first_failure(state, "pre rejected")
        first_failure(state, "post failed")
        self.assertEqual(state["failure_reason"], "pre rejected")
        self.assertEqual(state["additional_failures"], ["post failed"])

    @unittest.skipUnless(os.name == "nt", "Actual Windows PowerShell entry is tested on Windows")
    def test_actual_windows_module_entry_and_abnormal_probe_refusal(self):
        with tempfile.TemporaryDirectory(prefix="p3 entry space ") as temp:
            directory = Path(temp)
            cases = [("valid", probe(1), 0), ("empty", probe(0), 2), ("zero", probe(1), 2)]
            cases[-1][1]["wsl_intervals"][0]["delta"]["raw_seconds"] = 0
            with patch.dict(os.environ, {"PSModulePath": "deliberately-invalid-parent-path"}):
                for name, raw, expected in cases:
                    path = directory / (name + " probe.json")
                    atomic_write_json(path, raw)
                    output = directory / (name + " evidence")
                    result = subprocess.run([sys.executable, str(ROOT / "scripts/start_p3_first_seed.py"),
                        "--mode", "check", "--output", str(output), "--probe-file", str(path), "--intervals", "1"],
                        text=True, capture_output=True, timeout=60)
                    self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
                    startup = load(output / "windows_startup.json")
                    self.assertEqual(startup["get_file_hash_source"], "Microsoft.PowerShell.Utility")
                    self.assertIn("WindowsPowerShell", startup["powershell_executable"])
                    operation_record = load(output / "windows_entry.operation.json")
                    self.assertEqual(operation_record["returncode"], expected)
                    self.assertGreater(operation_record["pid"], 0)
                self.assertEqual(os.environ["PSModulePath"], "deliberately-invalid-parent-path")


if __name__ == "__main__":
    unittest.main()
