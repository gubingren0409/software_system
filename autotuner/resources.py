"""Versioned admission only. The target's own CPU usage is never constrained."""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import time

from .core import sha256_file, sha256_json, utc_now

ROOT = Path(__file__).resolve().parents[1]
LEGACY_CPU_POLICY_HASH = "e191aee4348fa5501bb923dbf1be35741a188c738ebf6fdb4863bc91b0be5671"
LEGACY_COLLECTOR_LF_SHA256 = "83c3ff713297ab58410834e2b514a8c3582de9c424212985e561b7b5117e4626"


def load_policy(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_constant)
    return validate_policy(value)


def validate_policy(value: dict) -> dict:
    if not isinstance(value, dict) or value.get("schema") not in ("p3-resource-policy-v1", "p3-resource-policy-v2") or \
            not isinstance(value.get("version"), str) or not value["version"]:
        raise ValueError("Unknown resource policy schema/version")
    new = value["schema"] == "p3-resource-policy-v2"
    if value.get("sample_count") != 5 or value.get("sample_interval_seconds") != 1:
        raise ValueError("Resource collection must retain five samples and the one-second sleep interval")
    fields = ["host_minimum_available_bytes", "wsl_root_minimum_free_bytes", "formal_wait_budget_seconds",
              "formal_retry_interval_seconds", "collection_timeout_seconds"]
    fields += ["host_warning_available_bytes", "host_minimum_commit_headroom_bytes"] if new else ["wsl_minimum_available_bytes"]
    for field in fields:
        if type(value.get(field)) is not int or value[field] <= 0:
            raise ValueError("Invalid policy field: " + field)
    if set(value.get("purposes", {})) != {"Recovery", "Formal"}:
        raise ValueError("Unknown/missing policy purpose")
    for purpose, rule in value["purposes"].items():
        if not isinstance(rule, dict):
            raise ValueError("Invalid resource purpose rule")
        if new and (type(rule.get("wsl_minimum_available_bytes")) is not int or rule["wsl_minimum_available_bytes"] <= 0):
            raise ValueError("Invalid purpose-specific WSL memory bound")
        if type(rule.get("cpu_reject")) is not bool or rule["cpu_reject"] != (purpose == "Formal"):
            raise ValueError("Invalid CPU admission semantics")
        for field in ("cpu_average_limit_percent", "cpu_maximum_limit_percent"):
            if type(rule.get(field)) not in (int, float) or not math.isfinite(rule[field]) or not 0 < rule[field] <= 100:
                raise ValueError("Invalid CPU policy bound")
    return value


def protocol_policy(protocol: dict) -> tuple[dict, Path, str]:
    """Resolve the frozen version, not current limits, when auditing legacy v3."""
    ref = protocol["resource_gate"]
    if ref["policy_file"] != "configs/resource_policy.json":
        raise ValueError("Unknown resource policy path")
    legacy = ref["policy_hash"] == LEGACY_CPU_POLICY_HASH
    path = ROOT / ("configs/resource_policy_cpu_v1.json" if legacy else ref["policy_file"])
    policy = load_policy(path)
    if sha256_json(policy) != ref["policy_hash"] or policy["version"] != ref["policy_version"]:
        raise ValueError("Frozen resource policy identity differs")
    new = policy["schema"] == "p3-resource-policy-v2"
    expected = {"functional_host_minimum_available_bytes": policy["host_minimum_available_bytes"],
        "formal_host_minimum_available_bytes": policy["host_minimum_available_bytes"],
        "functional_wsl_minimum_available_bytes": policy["purposes"]["Recovery"]["wsl_minimum_available_bytes"] if new else policy["wsl_minimum_available_bytes"],
        "formal_wsl_minimum_available_bytes": policy["purposes"]["Formal"]["wsl_minimum_available_bytes"] if new else policy["wsl_minimum_available_bytes"],
        "functional_wsl_root_minimum_free_bytes": policy["wsl_root_minimum_free_bytes"],
        "formal_wsl_root_minimum_free_bytes": policy["wsl_root_minimum_free_bytes"],
        "formal_host_cpu_average_maximum_percent": policy["purposes"]["Formal"]["cpu_average_limit_percent"],
        "formal_host_cpu_single_sample_maximum_percent": policy["purposes"]["Formal"]["cpu_maximum_limit_percent"]}
    if new:
        expected.update(host_warning_available_bytes=policy["host_warning_available_bytes"],
                        host_minimum_commit_headroom_bytes=policy["host_minimum_commit_headroom_bytes"])
    if any(type(ref.get(key)) not in (int, float) or ref[key] != value for key, value in expected.items()):
        raise ValueError("Protocol resource thresholds differ from central policy")
    collector = (ROOT / "scripts/check_p2_resources.ps1").read_bytes()
    return policy, path, LEGACY_COLLECTOR_LF_SHA256 if legacy else hashlib.sha256(collector.replace(b"\r\n", b"\n")).hexdigest()


def reject_constant(token):
    raise ValueError("Nonfinite JSON: " + token)


def judge(snapshot: dict, policy: dict, purpose: str, policy_file_sha256: str) -> dict:
    validate_policy(policy)
    new = policy["schema"] == "p3-resource-policy-v2"
    if purpose not in policy["purposes"]:
        raise ValueError("Unknown admission purpose: " + str(purpose))
    schemas = ("p3-resource-snapshot-v2", "p3-resource-gate-v4") if new else ("p3-resource-snapshot-v1", "p3-resource-gate-v3")
    if not isinstance(snapshot, dict) or snapshot.get("schema") not in schemas:
        raise ValueError("Invalid resource snapshot schema")
    if snapshot.get("purpose", purpose) != purpose or snapshot.get("mode", purpose) != purpose:
        raise ValueError("Resource evidence cannot be relabeled to another purpose")
    for field in ("collector_sha256", "collector_lf_sha256"):
        if not isinstance(snapshot.get(field), str) or not re.fullmatch(r"[0-9a-f]{64}", snapshot[field]):
            raise ValueError("Missing/invalid collector source identity")
    samples = snapshot.get("host_samples")
    if not isinstance(samples, list) or len(samples) != policy["sample_count"]:
        raise ValueError("Exactly five unfiltered host samples required")
    for sample in samples:
        if not isinstance(sample, dict):
            raise ValueError("Invalid host sample type")
        cpu = sample.get("cpu_percent")
        if type(cpu) not in (int, float) or not math.isfinite(cpu) or not 0 <= cpu <= 100:
            raise ValueError("Invalid/nonfinite CPU sample")
        if type(sample.get("available_memory_bytes")) is not int or sample["available_memory_bytes"] < 0:
            raise ValueError("Invalid/missing host memory sample")
        if new:
            for field in ("committed_bytes", "commit_limit_bytes"):
                if type(sample.get(field)) is not int or not 0 < sample[field] <= 2**63 - 1:
                    raise ValueError("Invalid/missing commit counter: " + field)
            if sample["committed_bytes"] > sample["commit_limit_bytes"]:
                raise ValueError("Committed bytes exceed commit limit")
        if not isinstance(sample.get("timestamp"), str):
            raise ValueError("Missing host sample timestamp")
        datetime.fromisoformat(sample["timestamp"])
    for field in ("host_total_visible_bytes", "wsl_total_bytes", "wsl_available_bytes",
                  "wsl_swap_total_bytes", "wsl_swap_free_bytes", "wsl_root_free_bytes"):
        if type(snapshot.get(field)) is not int or snapshot[field] < 0:
            raise ValueError("Invalid/missing resource field: " + field)
    if snapshot["host_total_visible_bytes"] <= 0 or snapshot["wsl_total_bytes"] <= 0 or \
            snapshot["wsl_available_bytes"] > snapshot["wsl_total_bytes"] or \
            snapshot["wsl_swap_free_bytes"] > snapshot["wsl_swap_total_bytes"] or \
            any(s["available_memory_bytes"] > snapshot["host_total_visible_bytes"] for s in samples):
        raise ValueError("Impossible memory range")
    average = sum(s["cpu_percent"] for s in samples) / len(samples)
    maximum = max(s["cpu_percent"] for s in samples)
    minimum = min(s["available_memory_bytes"] for s in samples)
    aggregates = {"host_cpu_average_percent": average, "host_cpu_maximum_percent": maximum,
                  "host_minimum_available_bytes": minimum}
    if new:
        aggregates["host_minimum_commit_headroom_bytes"] = min(s["commit_limit_bytes"] - s["committed_bytes"] for s in samples)
    for field, recomputed in aggregates.items():
        if field in snapshot and (type(snapshot[field]) not in (int, float) or
                                  not math.isfinite(snapshot[field]) or snapshot[field] != recomputed):
            raise ValueError("Saved aggregate differs from raw samples: " + field)
    rule = policy["purposes"][purpose]
    checks = {"host_memory": minimum >= policy["host_minimum_available_bytes"],
              "wsl_memory": snapshot["wsl_available_bytes"] >= (rule["wsl_minimum_available_bytes"] if new else policy["wsl_minimum_available_bytes"]),
              "root_disk": snapshot["wsl_root_free_bytes"] >= policy["wsl_root_minimum_free_bytes"],
              "cpu_average": average <= rule["cpu_average_limit_percent"],
              "cpu_maximum": maximum <= rule["cpu_maximum_limit_percent"]}
    if new:
        checks["host_commit_headroom"] = aggregates["host_minimum_commit_headroom_bytes"] >= policy["host_minimum_commit_headroom_bytes"]
    reasons = [name for name, passed in checks.items() if not passed and (not name.startswith("cpu_") or rule["cpu_reject"])]
    warnings = [name + " exceeds warning threshold" for name in ("cpu_average", "cpu_maximum")
                if not checks[name] and not rule["cpu_reject"]]
    if new and minimum < policy["host_warning_available_bytes"]:
        warnings.append("host_memory below warning threshold")
    decision = "REJECT" if reasons else "PASS"
    result = {**snapshot, **aggregates, "schema": "p3-resource-gate-v4" if new else "p3-resource-gate-v3", "mode": purpose, "purpose": purpose,
              "policy": policy, "policy_version": policy["version"], "policy_hash": sha256_json(policy),
              "policy_file_sha256": policy_file_sha256, "host_minimum_available_bytes": minimum,
              "host_cpu_average_percent": average, "host_cpu_maximum_percent": maximum,
              "checks": checks, "warnings": warnings, "rejection_reasons": reasons, "decision": decision,
              "formal_gate": decision if purpose == "Formal" else "NOT_APPLICABLE",
              "recovery_gate": decision if purpose == "Recovery" else "NOT_APPLICABLE"}
    return result


def valid_gate(record: dict, protocol: dict, purpose: str) -> bool:
    """Recompute from raw samples; a renamed PASS flag is never sufficient."""
    try:
        if not isinstance(record, dict):
            return False
        ref = protocol["resource_gate"]
        expected_policy, path, collector_lf_sha = protocol_policy(protocol)
        new = expected_policy["schema"] == "p3-resource-policy-v2"
        if record.get("schema") != ("p3-resource-gate-v4" if new else "p3-resource-gate-v3") or record.get("purpose") != purpose or \
                record.get("mode") != purpose or record["policy_hash"] != ref["policy_hash"] or \
                record["policy_version"] != ref["policy_version"]:
            return False
        policy = record["policy"]
        if sha256_json(policy) != ref["policy_hash"] or policy != expected_policy:
            return False
        if record["collector_lf_sha256"] != collector_lf_sha:
            return False
        expected = judge(record, policy, purpose, sha256_file(path))
        fields = [
            "policy_file_sha256", "host_minimum_available_bytes", "host_cpu_average_percent",
            "host_cpu_maximum_percent", "checks", "warnings", "rejection_reasons", "decision",
            "formal_gate", "recovery_gate"]
        if new:
            fields.append("host_minimum_commit_headroom_bytes")
        return all(record.get(field) == expected[field] for field in fields) and expected["decision"] == "PASS"
    except (ValueError, KeyError, TypeError, OSError, OverflowError):
        return False


def wait_formal(command, protocol, on_record, pause_requested=lambda: False):
    """A bounded admission wait, including collection time; no target is running."""
    policy, _, _ = protocol_policy(protocol)
    started = time.monotonic()
    budget = policy["formal_wait_budget_seconds"]
    while time.monotonic() - started < budget:
        if pause_requested():
            return False, time.monotonic() - started
        remaining = budget - (time.monotonic() - started)
        if remaining <= 0:
            break
        result, raw_hex = None, {}
        try:
            raw = subprocess.run(command, capture_output=True,
                                 timeout=min(policy["collection_timeout_seconds"], remaining), check=False)
            streams = {}
            for field in ("stdout", "stderr"):
                value = getattr(raw, field)
                if isinstance(value, bytes):
                    try:
                        value = value.decode("utf-8")
                    except UnicodeDecodeError:
                        raw_hex[field + "_raw_hex"] = value.hex()
                        value = value.decode("utf-8", errors="backslashreplace")
                streams[field] = value
            result = subprocess.CompletedProcess(command, raw.returncode, streams["stdout"], streams["stderr"])
            parsed = json.loads(result.stdout.lstrip("\ufeff"), parse_constant=reject_constant)
            if not isinstance(parsed, dict):
                raise ValueError("Resource JSON must be an object")
        except subprocess.TimeoutExpired:
            result = subprocess.CompletedProcess(command, 124, "", "resource collection timeout")
            parsed = {"decision": "ERROR", "rejection_reasons": ["collection timeout"]}
        except ValueError as error:
            if result is None:
                result = subprocess.CompletedProcess(command, None, "", str(error))
            parsed = {"decision": "ERROR", "rejection_reasons": ["invalid resource JSON"]}
        except OSError as error:
            result = subprocess.CompletedProcess(command, None, "", str(error))
            parsed = {"decision": "ERROR", "rejection_reasons": ["resource collector could not start"]}
        elapsed = time.monotonic() - started
        passed = elapsed <= budget and result.returncode == 0 and valid_gate(parsed, protocol, "Formal")
        on_record({**raw_hex, "captured_at": utc_now(), "command": command, "returncode": result.returncode,
                   "stdout": result.stdout, "stderr": result.stderr, "parsed": parsed,
                   "admission_pass": passed, "wait_elapsed_seconds": elapsed, "wait_budget_seconds": budget})
        if passed:
            return True, elapsed
        remaining = budget - (time.monotonic() - started)
        if remaining <= 0:
            break
        time.sleep(min(policy["formal_retry_interval_seconds"], remaining))
    return False, time.monotonic() - started


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--purpose", required=True)
    args = parser.parse_args()
    error_schema = "p3-resource-gate-v4"
    try:
        policy = load_policy(args.policy)
        error_schema = "p3-resource-gate-v4" if policy["schema"] == "p3-resource-policy-v2" else "p3-resource-gate-v3"
        snapshot = json.load(sys.stdin, parse_constant=reject_constant)
        result = judge(snapshot, policy, args.purpose, sha256_file(args.policy))
        code = 0 if result["decision"] == "PASS" else 2
    except (ValueError, KeyError, TypeError, OSError) as error:
        result = {"schema": error_schema, "purpose": args.purpose, "mode": args.purpose,
                  "decision": "ERROR", "formal_gate": "ERROR", "recovery_gate": "ERROR",
                  "rejection_reasons": [str(error)]}
        code = 3
    print(json.dumps(result, allow_nan=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
