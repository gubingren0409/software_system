"""Admission regressions only: synthetic load, no matrix performance experiments."""
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from autotuner.core import sha256_file, sha256_json
from autotuner.resources import ROOT, judge, load_policy, valid_gate, wait_formal, protocol_policy
from autotuner.session import valid_formal_gate

POLICY = load_policy(ROOT / "configs/resource_policy.json")
PROTOCOL = json.loads((ROOT / "configs/measurement_protocol.json").read_text(encoding="utf-8"))


def snapshot(cpus=(13, 9, 16, 18, 15)):
    collector = ROOT / "scripts/check_p2_resources.ps1"
    return {"schema": "p3-resource-snapshot-v2", "collector_sha256": sha256_file(collector),
        "collector_lf_sha256": hashlib.sha256(collector.read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        "host_total_visible_bytes": 16 * 2**30,
        "host_samples": [{"timestamp": f"2026-10-10T14:00:0{i}+08:00", "cpu_percent": cpu,
                          "available_memory_bytes": 3 * 2**30, "committed_bytes": 4 * 2**30,
                          "commit_limit_bytes": 16 * 2**30} for i, cpu in enumerate(cpus)],
        "wsl_total_bytes": 8 * 2**30, "wsl_available_bytes": 4 * 2**30,
        "wsl_swap_total_bytes": 2**30, "wsl_swap_free_bytes": 2**30, "wsl_root_free_bytes": 5 * 2**30}


def record(value=None, purpose="Formal"):
    return judge(value or snapshot(), POLICY, purpose, sha256_file(ROOT / "configs/resource_policy.json"))


class ResourcePolicyTests(unittest.TestCase):
    def test_historical_replay_warns_and_passes_new_policy_without_relabeling_old(self):
        fixture = json.loads((ROOT / "tests/fixtures/ac33d9d_resource_replay.json").read_text())
        original = fixture["record"]
        self.assertEqual(original["decision"], "REJECT")
        self.assertEqual(original["rejection_reasons"], ["host_memory"])
        legacy_policy = load_policy(ROOT / "configs/resource_policy_cpu_v1.json")
        old = judge(original, legacy_policy, "Recovery", sha256_file(ROOT / "configs/resource_policy_cpu_v1.json"))
        self.assertEqual(old, original)
        raw = snapshot()
        for key in ("host_samples", "host_total_visible_bytes", "wsl_total_bytes", "wsl_available_bytes",
                    "wsl_swap_total_bytes", "wsl_swap_free_bytes", "wsl_root_free_bytes"):
            raw[key] = copy.deepcopy(original[key])
        for purpose in ("Recovery", "Formal"):
            result = record(raw, purpose)
            self.assertEqual(result["decision"], "PASS")
            self.assertIn("host_memory below warning threshold", result["warnings"])
            self.assertEqual(result["host_minimum_available_bytes"], 775036928)
            self.assertTrue(valid_gate(result, PROTOCOL, purpose))
        self.assertEqual(fixture["record"]["decision"], "REJECT")

    def test_physical_and_commit_headroom_bounds_are_independent_and_inclusive(self):
        for purpose in ("Recovery", "Formal"):
            raw = snapshot()
            raw["host_samples"][2]["available_memory_bytes"] = 512 * 2**20
            raw["host_samples"][3]["commit_limit_bytes"] = raw["host_samples"][3]["committed_bytes"] + 512 * 2**20
            self.assertEqual(record(raw, purpose)["decision"], "PASS")
            raw["host_samples"][2]["available_memory_bytes"] -= 1
            self.assertEqual(record(raw, purpose)["rejection_reasons"], ["host_memory"])
            raw["host_samples"][2]["available_memory_bytes"] += 1
            raw["host_samples"][3]["commit_limit_bytes"] -= 1
            self.assertEqual(record(raw, purpose)["rejection_reasons"], ["host_commit_headroom"])

    def test_wsl_capacity_has_distinct_purpose_bounds(self):
        for available, recovery_pass, formal_pass in ((256*2**20-1,False,False),
                (256*2**20,True,False),(2*2**30-1,True,False),(2*2**30,True,True)):
            raw=snapshot(); raw["wsl_available_bytes"]=available
            self.assertEqual(record(raw,"Recovery")["decision"]=="PASS", recovery_pass)
            self.assertEqual(record(raw,"Formal")["decision"]=="PASS", formal_pass)

    def test_missing_invalid_or_impossible_commit_counters_are_errors(self):
        for field in ("committed_bytes", "commit_limit_bytes"):
            for value in (None, 0, -1, True, "123", 1.5, math.nan, math.inf, 2**63):
                raw=snapshot(); raw["host_samples"][1][field]=value
                with self.assertRaises(ValueError): record(raw)
            raw=snapshot(); del raw["host_samples"][1][field]
            with self.assertRaises(ValueError): record(raw)
        raw=snapshot(); raw["host_samples"][1]["committed_bytes"]=17*2**30
        with self.assertRaises(ValueError): record(raw)

    def test_saved_commit_headroom_and_duplicate_limits_cannot_be_forged(self):
        value=record(); value["host_minimum_commit_headroom_bytes"]=10**12
        self.assertFalse(valid_formal_gate(value,PROTOCOL))
        for field in ("functional_host_minimum_available_bytes", "formal_host_minimum_available_bytes",
                      "host_minimum_commit_headroom_bytes", "functional_wsl_minimum_available_bytes"):
            protocol=copy.deepcopy(PROTOCOL); protocol["resource_gate"][field]=1
            self.assertFalse(valid_formal_gate(record(),protocol))

    def test_legacy_v3_frozen_policy_remains_auditable(self):
        legacy_policy=load_policy(ROOT/"configs/resource_policy_cpu_v1.json")
        protocol=copy.deepcopy(PROTOCOL)
        protocol["resource_gate"]={"policy_file":"configs/resource_policy.json",
            "policy_version":legacy_policy["version"],"policy_hash":sha256_json(legacy_policy),
            "functional_host_minimum_available_bytes":2*2**30,"formal_host_minimum_available_bytes":2*2**30,
            "functional_wsl_minimum_available_bytes":2*2**30,"formal_wsl_minimum_available_bytes":2*2**30,
            "functional_wsl_root_minimum_free_bytes":2**30,"formal_wsl_root_minimum_free_bytes":2**30,
            "formal_host_cpu_average_maximum_percent":30,"formal_host_cpu_single_sample_maximum_percent":60}
        from autotuner.resources import LEGACY_COLLECTOR_LF_SHA256
        raw=snapshot(); raw["schema"]="p3-resource-snapshot-v1"
        raw["collector_lf_sha256"]=LEGACY_COLLECTOR_LF_SHA256
        result=judge(raw,legacy_policy,"Formal",sha256_file(ROOT/"configs/resource_policy_cpu_v1.json"))
        self.assertTrue(valid_formal_gate(result,protocol))
        raw["host_samples"][0]["available_memory_bytes"]=775036928
        rejected=judge(raw,legacy_policy,"Formal",sha256_file(ROOT/"configs/resource_policy_cpu_v1.json"))
        self.assertEqual(rejected["rejection_reasons"],["host_memory"])
        self.assertFalse(valid_formal_gate(rejected,protocol))

    def test_actual_prior_cpu_samples_pass_new_formal(self):
        result = record()
        self.assertEqual(result["host_cpu_average_percent"], 14.2)
        self.assertEqual(result["host_cpu_maximum_percent"], 18)
        self.assertEqual(result["decision"], "PASS")
        self.assertTrue(valid_formal_gate(result, PROTOCOL))

    def test_above_new_limits_rejects_formal_but_warns_recovery(self):
        value = snapshot((70, 70, 70, 70, 70))
        formal, recovery = record(value), record(value, "Recovery")
        self.assertEqual(formal["decision"], "REJECT")
        self.assertEqual(set(formal["rejection_reasons"]), {"cpu_average", "cpu_maximum"})
        self.assertEqual(recovery["decision"], "PASS")
        self.assertEqual(len(recovery["warnings"]), 2)
        self.assertTrue(valid_gate(recovery, PROTOCOL, "Recovery"))
        self.assertFalse(valid_formal_gate(recovery, PROTOCOL))
        with self.assertRaises(ValueError): record(recovery, "Formal")

    def test_average_and_single_limits_are_independent(self):
        for cpus, reason in (((31, 31, 31, 31, 31), "cpu_average"), ((61, 0, 0, 0, 0), "cpu_maximum")):
            self.assertIn(reason, record(snapshot(cpus))["rejection_reasons"])
        self.assertEqual(record(snapshot((60, 30, 30, 30, 0)))["decision"], "PASS")

    def test_low_memory_and_disk_reject_both_purposes(self):
        for field in ("host", "wsl_available_bytes", "wsl_root_free_bytes"):
            value = snapshot()
            if field == "host": value["host_samples"][2]["available_memory_bytes"] = 1
            else: value[field] = 1
            for purpose in ("Formal", "Recovery"):
                self.assertEqual(record(value, purpose)["decision"], "REJECT")

    def test_empty_missing_nonfinite_or_wrong_types_rejected(self):
        for samples in ([], None, snapshot()["host_samples"][:4], snapshot()["host_samples"] * 2):
            value = snapshot(); value["host_samples"] = samples
            with self.assertRaises(ValueError): record(value)
        for cpu in (math.nan, math.inf, -1, 101, "13", True, None):
            value = snapshot(); value["host_samples"][0]["cpu_percent"] = cpu
            with self.assertRaises(ValueError): record(value)
        for field in ("wsl_total_bytes", "wsl_available_bytes", "wsl_root_free_bytes", "collector_sha256"):
            value = snapshot(); del value[field]
            with self.assertRaises(ValueError): record(value)
        with self.assertRaises(ValueError): record(snapshot(), "unknown")
        for value in (None, [], 0, "PASS"):
            self.assertFalse(valid_formal_gate(value, PROTOCOL))

    def test_saved_pass_aggregates_and_identity_cannot_bypass_raw_values(self):
        original = record()
        for field, value in (("host_cpu_average_percent", 0), ("host_minimum_available_bytes", 10**12),
                             ("policy_hash", "0" * 64), ("policy_version", "unknown"),
                             ("collector_lf_sha256", "0" * 64), ("purpose", "Recovery")):
            changed = copy.deepcopy(original); changed[field] = value
            self.assertFalse(valid_formal_gate(changed, PROTOCOL), field)
        changed = record(snapshot((70,) * 5)); changed.update(decision="PASS", formal_gate="PASS")
        self.assertFalse(valid_formal_gate(changed, PROTOCOL))
        changed = copy.deepcopy(original); changed["host_samples"][0]["cpu_percent"] = math.nan
        self.assertFalse(valid_formal_gate(changed, PROTOCOL))

    def test_v2_records_use_original_limits_not_new_policy(self):
        legacy = json.loads((ROOT / "evidence/p3/campaign-e308bfb/protocol.json").read_text(encoding="utf-8"))
        value = {"schema": "p2-resource-gate-v2", "mode": "Formal", "formal_gate": "PASS",
                 "host_minimum_available_bytes": 3 * 2**30, "wsl_available_bytes": 3 * 2**30,
                 "wsl_root_free_bytes": 2 * 2**30, "host_cpu_average_percent": 14.2,
                 "host_cpu_maximum_percent": 18}
        self.assertFalse(valid_formal_gate(value, legacy))
        self.assertFalse(valid_formal_gate(value, PROTOCOL))
        value["host_cpu_average_percent"] = 9
        self.assertTrue(valid_formal_gate(value, legacy))

    def test_wait_limit_includes_collection_time_and_stops_at_120(self):
        now = [0.0]; timeouts = []; saved = []
        def run(command, **kwargs):
            timeouts.append(kwargs["timeout"]); now[0] += kwargs["timeout"]
            return subprocess.CompletedProcess(command, 2, json.dumps(record(snapshot((70,) * 5))), "")
        with patch("autotuner.resources.time.monotonic", side_effect=lambda: now[0]), \
                patch("autotuner.resources.time.sleep", side_effect=lambda seconds: now.__setitem__(0, now[0] + seconds)), \
                patch("autotuner.resources.subprocess.run", side_effect=run):
            passed, elapsed = wait_formal(["controlled"], PROTOCOL, saved.append)
        self.assertFalse(passed); self.assertEqual(elapsed, 120)
        self.assertEqual(timeouts, [60, 50]); self.assertEqual(len(saved), 2)
        self.assertTrue(all(not row["admission_pass"] for row in saved))

    def test_wait_pass_and_pause_paths(self):
        with patch("autotuner.resources.subprocess.run", return_value=subprocess.CompletedProcess(["x"], 0, json.dumps(record()).encode(), b"")) as run:
            self.assertTrue(wait_formal(["x"], PROTOCOL, lambda row: None)[0])
            self.assertFalse(wait_formal(["x"], PROTOCOL, lambda row: None, lambda: True)[0])
            self.assertEqual(run.call_count, 1)

    def test_invalid_collector_json_and_launch_error_are_saved_without_admission(self):
        for response in (subprocess.CompletedProcess(["x"], 0, "[]", ""), OSError("missing collector"), ValueError("invalid command")):
            saved = []
            with patch("autotuner.resources.subprocess.run", side_effect=response if isinstance(response, Exception) else None,
                       return_value=response), \
                    patch("autotuner.resources.time.sleep"):
                passed, _ = wait_formal(["x"], PROTOCOL, saved.append, lambda: bool(saved))
            self.assertFalse(passed)
            self.assertEqual(len(saved), 1)
            self.assertEqual(saved[0]["parsed"]["decision"], "ERROR")

    def test_non_utf8_native_failure_preserves_exit_and_original_error_bytes(self):
        saved = []
        message = "无法加载文件：未进行数字签名".encode("gb18030")
        with patch("autotuner.resources.subprocess.run", return_value=subprocess.CompletedProcess(["x"], 1, b"", message)), \
                patch("autotuner.resources.time.sleep"):
            passed, _ = wait_formal(["x"], PROTOCOL, saved.append, lambda: bool(saved))
        self.assertFalse(passed)
        self.assertEqual(saved[0]["returncode"], 1)
        self.assertEqual(bytes.fromhex(saved[0]["stderr_raw_hex"]), message)
        self.assertEqual(saved[0]["parsed"]["decision"], "ERROR")

    @unittest.skipUnless(os.name == "nt", "actual Windows entry regression")
    def test_actual_powershell_and_python_use_same_decision(self):
        from scripts.p3_clock_contract import POWERSHELL, MODULE_PATH, wsl_path
        env = dict(os.environ, PSModulePath=MODULE_PATH)
        cases = [(snapshot(), "Formal", 0), (snapshot((70,) * 5), "Formal", 2),
                 (snapshot((70,) * 5), "Recovery", 0)]
        low = snapshot(); low["wsl_available_bytes"] = 1
        cases.extend(((low, "Formal", 2), (low, "Recovery", 2)))
        empty = snapshot(); empty["host_samples"] = []
        cases.append((empty, "Recovery", 3))
        low_host = snapshot(); low_host["host_samples"][0]["available_memory_bytes"] = 775036928
        cases.extend(((low_host,"Formal",0),(low_host,"Recovery",0)))
        low_commit = snapshot(); low_commit["host_samples"][0]["commit_limit_bytes"] = low_commit["host_samples"][0]["committed_bytes"] + 1
        cases.append((low_commit,"Formal",2))
        invalid_commit = snapshot(); del invalid_commit["host_samples"][0]["committed_bytes"]
        cases.append((invalid_commit,"Recovery",3))
        with tempfile.TemporaryDirectory() as temporary:
            for index, (raw, purpose, code) in enumerate(cases):
                path = Path(temporary) / f"{index}.json"
                path.write_text(json.dumps(raw), encoding="utf-8")
                command = [POWERSHELL, "-NoProfile", "-File", str(ROOT / "scripts/check_p2_resources.ps1"),
                           "-Mode", purpose, "-RuntimeRoot", wsl_path(ROOT), "-InputSnapshot", str(path)]
                result = subprocess.run(command, capture_output=True, timeout=90, env=env)
                self.assertEqual(result.returncode, code, result.stderr)
                actual = json.loads(result.stdout)
                if code != 3:
                    expected = record(raw, purpose)
                    self.assertEqual(actual, expected)
                else: self.assertEqual(actual["decision"], "ERROR")


if __name__ == "__main__":
    unittest.main()
