"""Read-only postprocessing for this diagnosis batch, not a recovery certificate.

Reuses the frozen checker on the ORIGINAL 20 intervals. Does not launch clocks
or matrices, rewrite old files, calibrate results, or change search observations.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
from autotuner.core import utc_now
from autotuner.session import valid_formal_gate
from scripts.p3_clock_contract import (atomic_write_json, load, snapshot_campaign,
                                       verify_clock_evidence)
from scripts.start_p3_first_seed import auxiliary_identity

OUT = Path(__file__).resolve().parent
OPS = OUT / "operations"
OLD = ROOT / "evidence/p3_clock_contract/20261009-180810-0491a4ec/recovery"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    if (OUT / "diagnosis_analysis.json").exists():
        raise ValueError("Preserve previous analysis; use a new filename for further review")
    commands = load(OUT / "diagnostic_commands.json")
    source_hash = digest((OUT / "diagnose.py").read_bytes())
    assert source_hash == commands["collector_sha256"]
    assert digest((OUT / "read_adjtimex.c").read_bytes()) == commands["adjtimex_source_sha256"]
    declared = {item["name"]: item for item in commands["commands"]}
    operation_errors, operations, unavailable = [], [], []
    for path in sorted(OPS.glob("*.operation.json")):
        op = load(path)
        name = op["operation_kind"]
        try:
            assert op["batch_id"] == OUT.name and op["schema"] == "p3-captured-operation-v2"
            assert op["returncode"] == "unknown" or type(op["returncode"]) is int
            for stream in ("stdout", "stderr"):
                data = (OPS / op[stream + "_path"]).read_bytes()
                assert digest(data) == op[stream + "_sha256"]
                assert digest(data.replace(b"\r\n", b"\n")) == op[stream + "_lf_sha256"]
                assert len(data) == op[stream + "_byte_count"]
            assert op["qpc_seconds"] == (op["qpc_end"] - op["qpc_start"]) / op["qpc_frequency"]
            assert op["utc_seconds"] == (op["end_utc_ns"] - op["start_utc_ns"]) / 1e9
            if name in declared:
                assert op["command"] == declared[name]["command"]
                assert op["timeout_seconds"] == declared[name]["timeout_seconds"]
        except (AssertionError, KeyError, OSError, ValueError) as error:
            operation_errors.append({"name": name, "error": type(error).__name__ + ": " + str(error)})
        operations.append({"name": name, "operation_sha256": digest(path.read_bytes()),
                           "returncode": op["returncode"], "timed_out": op["timed_out"],
                           "qpc_seconds": op["qpc_seconds"], "qpc_start": op["qpc_start"],
                           "qpc_end": op["qpc_end"], "qpc_frequency": op["qpc_frequency"]})
        if op["returncode"] != 0 or op["timed_out"]:
            unavailable.append({"name": name, "returncode": op["returncode"], "timed_out": op["timed_out"]})
    assert all((OPS / (name + ".operation.json")).exists() for name in declared)

    old_checks, rows = {}, []
    for name in ("window_A", "window_B"):
        old_checks[name] = verify_clock_evidence(OLD, name)
        assert old_checks[name]["evidence_integrity_pass"]
        probe = load(OLD / (name + ".wsl.json"))
        for index, (raw, checked) in enumerate(zip(probe["wsl_intervals"], old_checks[name]["checks"]), 1):
            delta = {clock: (raw["after"][clock + "_ns"] - raw["before"][clock + "_ns"]) / 1e9
                     for clock in ("monotonic", "raw", "realtime", "boottime")}
            rows.append({"window": name, "interval": index, "before": raw["before"], "after": raw["after"],
                         "delta_seconds_recomputed": delta, "checker_row": checked,
                         "apparent_mono_raw_difference_ppm": (delta["monotonic"] - delta["raw"]) / delta["raw"] * 1e6,
                         "realtime_minus_monotonic_seconds": delta["realtime"] - delta["monotonic"],
                         "classification": "Historical diagnostic, not a calibration factor"})
    old = {"source_directory": str(OLD.relative_to(ROOT)),
           "checker_sha256": digest((ROOT / "scripts/p3_clock_contract.py").read_bytes()),
           "windows": old_checks, "intervals": rows, "interval_count": len(rows),
           "monotonic_raw_failed": sum(not r["checker_row"]["monotonic_raw_pass"] for r in rows),
           "realtime_raw_failed": sum(not r["checker_row"]["realtime_raw_pass"] for r in rows),
           "apparent_difference_ppm_min": min(r["apparent_mono_raw_difference_ppm"] for r in rows),
           "apparent_difference_ppm_max": max(r["apparent_mono_raw_difference_ppm"] for r in rows),
           "old_manifest_identity_error_preserved": True,
           "note": "Per-window raw integrity is separate from old whole-manifest failure; no new probe or historical calibration."}
    atomic_write_json(OUT / "old_twenty_recomputed.json", old)

    before = load(OUT / "campaign_before.json")
    after = snapshot_campaign(ROOT / "evidence/p3/campaign-e308bfb")
    protected = load(OUT / "protected_files_before.json")["files"]
    changed = [relative for relative, record in protected.items()
               if not (ROOT / relative).exists() or digest((ROOT / relative).read_bytes()) != record["runtime_sha256"]]
    unchanged = before["checkpoint"] == after["checkpoint"] and before["checkpoint_sha256"] == after["checkpoint_sha256"]
    unchanged = unchanged and before["trajectories"] == after["trajectories"]
    assert unchanged and not changed
    atomic_write_json(OUT / "campaign_after_diagnosis.json", after)
    frozen = load(ROOT / "evidence/p3_clock_contract/20261009-180810-0491a4ec/identity_location_correction.json")["corrected_expected"]
    actual = {}
    for line in (OPS / "formal_frozen_sha.stdout.txt").read_text().splitlines():
        value, path = line.split(maxsplit=1)
        actual[path.strip()] = value
    identity_pass = actual == frozen and load(OPS / "formal_frozen_sha.operation.json")["returncode"] == 0
    aux = auxiliary_identity("fa597017c2317772a0f7f34faa75194ffecec8f2")

    service = load(OPS / "windows_service_privileges.stdout.txt")
    status = (OPS / "windows_time_status_before.stdout.txt").read_bytes().decode("gb18030")
    peers = (OPS / "windows_time_peers.stdout.txt").read_bytes().decode("gb18030")
    events = json.loads((OPS / "windows_events.stdout.txt").read_bytes().decode("gb18030"))
    resource = load(OPS / "resource_gate.stdout.txt")
    resource_pass = load(OPS / "resource_gate.operation.json")["returncode"] == 0 and valid_formal_gate(resource, load(ROOT / "configs/measurement_protocol.json"))
    adjtimex = load(OPS / "readonly_adjtimex.stdout.txt")
    assert adjtimex["requested_modes"] == 0 and adjtimex["returned_modes"] == 0
    assert abs(adjtimex["freq_ppm"] - adjtimex["freq"] / 65536) < 1e-10
    assert load(OPS / "compile_readonly_adjtimex.operation.json")["returncode"] == 0
    assert load(OPS / "readonly_adjtimex.operation.json")["returncode"] == 0
    corrected = load(OPS / "wsl_readonly_supplement.stdout.txt")
    assert all(c["returncode"] == 0 for c in corrected["commands"])
    configuration_rc = load(OPS / "windows_time_configuration.operation.json")["returncode"]
    source_rc = load(OPS / "windows_time_source_before.operation.json")["returncode"]
    assert configuration_rc == 0x80070005 and source_rc == 0x80070005
    assert service["current_token_administrator"] is False and service["status"] == "Running"
    assert "Leap" in status and "3(" in status and "time.windows.com,0x9" in status
    configs = load(OPS / "unique_configurations.stdout.txt")
    assert len(configs) == 20 and len({(c["optimization"], c["block_size"]) for c in configs}) == 20
    for name, count in (("clock_regressions", 21), ("first_seed_regressions", 7)):
        assert load(OPS / (name + ".operation.json"))["returncode"] == 0
        text = (OPS / (name + ".stderr.txt")).read_text()
        assert f"Ran {count} tests" in text and text.rstrip().endswith("OK")

    retests = sum(len(t["checkpoint"]["independent_retests"]) for t in after["trajectories"].values())
    completed = sum(len(t["checkpoint"]["observations"]) for t in after["trajectories"].values())
    counts = {name: {"observations": len(t["checkpoint"]["observations"]), "raw_executions": t["sample_count"],
                     "abandoned_attempts": t["checkpoint"]["abandoned_attempts"], "active": t["checkpoint"]["active"]}
              for name, t in after["trajectories"].items()}
    decision = {"status": "P3_CLOCK_BLOCKED", "recorded_at": utc_now(),
                "treatment_performed": False, "resync_invocations": 0,
                "reason": "W32Time unsynchronized; current token not elevated; source/configuration queries denied 0x80070005. No authorized effective treatment, so no new recovery.",
                "recovery_invocations": 0, "resume_invocations": 0, "formal_matrix_invocations": 0,
                "no_permission_bypass": True, "system_settings_modified": False,
                "additional_blocker": "Formal resource gate rejected host memory", "formal_resource_gate_pass": resource_pass,
                "required_operator_step": "In an administrator Windows PowerShell, inspect W32Time and w32tm status/source/configuration/peers. Only if existing configuration is appropriate, issue w32tm /resync /rediscover once; archive before/after output. Do not change NTP server or policy. Return evidence for external review before a new limited recovery."}
    atomic_write_json(OUT / "treatment_decision.json", decision)
    integrity = not operation_errors and identity_pass and unchanged and not changed
    assert len({op["qpc_frequency"] for op in operations}) == 1
    merged = []
    for start, end in sorted((op["qpc_start"], op["qpc_end"]) for op in operations):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    union_seconds = sum(end - start for start, end in merged) / operations[0]["qpc_frequency"]
    result = {"schema": "p3-clock-repair-diagnosis-v1", "batch": OUT.name, "analyzed_at": utc_now(),
              "postprocessor_sha256": digest(Path(__file__).read_bytes()),
              "formal_content_commit": after["checkpoint"]["fingerprint"]["content_commit"],
              "session_id": after["checkpoint"]["session_id"],
              "auxiliary_content_commit": "fa597017c2317772a0f7f34faa75194ffecec8f2", "auxiliary_identity": aux,
              "validation": {"clock_contract_tests_passed": 21, "first_seed_tests_passed": 7,
                             "unique_configurations": 20, "cli_help_returncode": load(OPS / "cli_help.operation.json")["returncode"],
                             "no_real_probe_in_synthetic_tests": True},
              "evidence_integrity_pass": integrity, "execution_complete": False,
              "timing_checks_pass": False, "comparison_ready": False,
              "acceptance_scope": "New diagnosis evidence integrity and preserved history, NOT a recovery/formal campaign clock certificate",
              "new_timing_check_status": "not_performed_no_effective_treatment", "decision": decision,
              "frozen_identity_pass": identity_pass, "frozen_file_count": len(frozen),
              "protected_file_count": len(protected), "changed_protected_files": changed,
              "campaign_unchanged": unchanged, "campaign_status": after["checkpoint"]["status"],
              "completed_configurations": completed, "completed_trajectories": 0,
              "raw_execution_count": sum(t["sample_count"] for t in after["trajectories"].values()),
              "independent_retest_groups": retests, "trajectory_progress": counts,
              "partial_samples_are_not_scored": True, "windows_service_and_privileges": service,
              "windows_time_status_decoding": "GB18030, strict decoding of original raw bytes",
              "windows_time_status": status, "windows_time_peers": peers,
              "windows_event_counts": {"system": len(events["system_events"]), "time_service_operational": len(events["time_service_events"])},
              "windows_event_log_state": events["time_service_log"],
              "windows_events_query_errors": [events["system_query_error"], events["time_service_query_error"]],
              "readonly_adjtimex": adjtimex, "wsl_clocksource_and_kernel_events": corrected,
              "formal_resource_gate_pass": resource_pass, "formal_resource_gate": resource,
              "historical_clock_statistics": {k: old[k] for k in ("interval_count", "monotonic_raw_failed", "realtime_raw_failed", "apparent_difference_ppm_min", "apparent_difference_ppm_max")},
              "operations": operations, "operation_integrity_errors": operation_errors,
              "failed_or_missing_queries": unavailable,
              "known_unavailable": ["Current Windows source/configuration (access denied)",
                  "Old interval adjtimex frequency/tick and per-update discipline log (not collected then)",
                  "Independent physical clock accuracy/root cause (unknown)",
                  "chrony/chronyd/ntp/ntpsec services not installed (LoadState=not-found)"],
              "campaign_costs_unchanged": {key: after["checkpoint"][key] for key in ("active_total_seconds", "wait_seconds")},
              "auxiliary_recorded_operation_duration_sum_seconds": sum(op["qpc_seconds"] for op in operations),
              "auxiliary_recorded_qpc_seconds": union_seconds,
              "auxiliary_recorded_operation_overlap_seconds": sum(op["qpc_seconds"] for op in operations) - union_seconds,
              "cost_scope": "Union of recorded top-level QPC intervals at analysis time; overlapping initial fetch and metadata are counted once. Duration sum is separate, not elapsed time. Nested WSL commands, whole diagnostic wrapper, editing/model/commit/push/offline time not added. Historical campaign costs unchanged."}
    atomic_write_json(OUT / "diagnosis_analysis.json", result)
    print(json.dumps({key: result[key] for key in ("evidence_integrity_pass", "execution_complete", "timing_checks_pass", "comparison_ready", "completed_configurations", "raw_execution_count", "protected_file_count", "auxiliary_recorded_qpc_seconds")}))
    return 0 if integrity else 1


if __name__ == "__main__":
    raise SystemExit(main())
