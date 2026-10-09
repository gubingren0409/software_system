"""One-off read-only analysis of the already collected twenty intervals. No probes."""
from pathlib import Path
import json
import sys

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
from scripts.p3_clock_contract import (ARCHIVE, atomic_write_json, capture, load,
    sha256_file, snapshot_campaign, verify_clock_evidence)
from scripts.start_p3_first_seed import frozen_source_expectations

directory = Path(__file__).resolve().parent
recovery = directory / "recovery"
manifest = load(recovery / "manifest.json")
old = dict(manifest["frozen_files_expected"])
bad_path = ARCHIVE + "/configs/timing_audit_protocol.json"
old.pop(bad_path)  # Only an in-memory correction; never rewrites the original manifest.
expected = frozen_source_expectations(old)
operation = capture(["wsl.exe", "-d", "Ubuntu-24.04", "--", "sha256sum", *expected],
    directory, "supplemental_identity", manifest["batch_id"], sha256_file(recovery / "manifest.json"), timeout=90)
actual = {line.split(maxsplit=1)[1].strip(): line.split()[0]
    for line in (directory / "supplemental_identity.stdout.txt").read_text().splitlines()}
correction = {"schema": "p3-criteria-location-correction-v1", "original_manifest_sha256": sha256_file(recovery / "manifest.json"),
    "old_missing_path": bad_path, "original_identity_pass": False,
    "reason": "Timing diagnostic criteria were introduced after e308bfb and belong to the auxiliary tree",
    "corrected_expected": expected, "actual": actual, "returncode": operation["returncode"],
    "corrected_location_identity_pass": operation["returncode"] == 0 and actual == expected,
    "original_manifest_modified": False, "formal_archive_modified": False,
    "authorizes_resume": False, "additional_clock_intervals": 0,
    "analysis_script_sha256": sha256_file(Path(__file__)),
    "controller_source_sha256": sha256_file(ROOT / "scripts/start_p3_first_seed.py")}
atomic_write_json(directory / "identity_location_correction.json", correction)

windows, rows = {}, []
for name in ("window_A", "window_B"):
    check = verify_clock_evidence(recovery, name)
    if not check["evidence_integrity_pass"]:
        raise ValueError("Raw clock evidence is invalid: " + repr(check))
    for row in check["checks"]:
        rows.append({"window": name, "interval_one_based": row["interval_index"] + 1, **row})
    windows[name] = {"count": len(check["checks"]), "host": check["host_check"],
        "mono_raw_fail_count": sum(not r["monotonic_raw_pass"] for r in check["checks"]),
        "realtime_raw_fail_count": sum(not r["realtime_raw_pass"] for r in check["checks"])}
after = snapshot_campaign(ROOT / "evidence/p3/campaign-e308bfb")
before = load(recovery / "campaign_before.json")
unchanged = before["checkpoint"] == after["checkpoint"] and before["trajectories"] == after["trajectories"]
atomic_write_json(directory / "campaign_final_snapshot.json", after)
costs = {p.name: load(p)["qpc_seconds"] for p in directory.glob("*.operation.json")
    if "qpc_seconds" in load(p)}
costs["recovery/windows_entry.operation.json"] = load(recovery / "windows_entry.operation.json")["qpc_seconds"]
result = {"schema": "p3-twenty-interval-blocked-analysis-v1", "status": "P3_CLOCK_BLOCKED",
    "raw_clock_evidence_integrity_pass": True, "original_manifest_identity_pass": False,
    "corrected_location_identity_pass": correction["corrected_location_identity_pass"],
    "execution_complete": False, "timing_checks_pass": False, "comparison_ready": False,
    "pre_clock_pass": None, "campaign_invoked": False, "campaign_returncode": "unknown", "post_clock_pass": None,
    "boundary_scope": "No campaign batch invoked; no batch pre/post probes performed",
    "failure_reason": "All twenty MONOTONIC/RAW intervals exceed the original tolerance",
    "additional_refusals": ["Two REALTIME/RAW intervals fail", "Host available memory below 2 GiB", "Original auxiliary criteria path absent"],
    "windows": windows, "intervals": rows, "interval_count": len(rows),
    "mono_raw_fail_count": sum(not r["monotonic_raw_pass"] for r in rows),
    "realtime_raw_fail_count": sum(not r["realtime_raw_pass"] for r in rows),
    "mono_raw_difference_ms_range": [1000 * min(r["monotonic_raw_difference_seconds"] for r in rows),
        1000 * max(r["monotonic_raw_difference_seconds"] for r in rows)],
    "mono_raw_limit_ms_range": [1000 * min(r["monotonic_raw_limit_seconds"] for r in rows),
        1000 * max(r["monotonic_raw_limit_seconds"] for r in rows)],
    "resource_gate": load(recovery / "resource_gate.json"), "campaign_unchanged": unchanged,
    "formal_content_commit": manifest["formal_content_commit"], "session_id": manifest["session_id"],
    "clock_review_auxiliary_content_commit": manifest["auxiliary_content_commit"],
    "complete_config_count": sum(len(t["checkpoint"]["observations"]) for t in after["trajectories"].values()),
    "raw_execution_count": sum(t["sample_count"] for t in after["trajectories"].values()),
    "campaign_active_seconds": after["checkpoint"]["active_total_seconds"],
    "campaign_gate_wait_seconds": after["checkpoint"]["wait_seconds"],
    "this_turn_campaign_active_delta_seconds": after["checkpoint"]["active_total_seconds"] - before["checkpoint"]["active_total_seconds"],
    "top_level_auxiliary_operation_qpc_seconds": costs,
    "scope": "Listed top-level auxiliary operations are disjoint; child resource/hash/probe costs are nested. This is not full turn cost; earlier unrecorded overhead is unknown.",
    "clock_anomaly_root_cause": "unknown; tsc/NTP status and event IDs alone do not establish causality",
    "no_calibration_or_sample_filtering": True, "additional_recovery_attempts": 0,
    "source_sha256": sha256_file(Path(__file__))}
if len(rows) != 20 or not unchanged or result["mono_raw_fail_count"] != 20:
    raise ValueError("Observed evidence differs; do not emit the declared blocked summary")
atomic_write_json(directory / "clock_review_analysis.json", result)
print(json.dumps({k: result[k] for k in ("status", "interval_count", "mono_raw_fail_count", "realtime_raw_fail_count",
    "mono_raw_difference_ms_range", "campaign_unchanged", "raw_execution_count", "complete_config_count")}))
