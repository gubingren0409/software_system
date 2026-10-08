"""Read-only audit of a P2 session; never supply observations to a strategy."""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from autotuner.core import Config, ConfigSpace, atomic_write_json, sha256_file, sha256_json, sha256_text, utc_now
from autotuner.measurement import summarize_group
from autotuner.session import restore_complete_group, valid_formal_gate


def audit(session: Path) -> dict:
    checkpoint = json.loads((session / "checkpoint.json").read_text())
    protocol = json.loads((session / "protocol.json").read_text())
    fingerprint = checkpoint["fingerprint"]
    assert sha256_json(protocol) == fingerprint["protocol_hash"], "protocol hash mismatch"
    records = [json.loads(line) for line in (session / "samples.jsonl").read_text().splitlines() if line]
    by_id = {record["run_id"]: record for record in records}
    assert len(by_id) == len(records), "duplicate execution ID"
    peak_rss_kib = 0
    process_major_faults = []
    resources = []
    for record in records:
        assert record["context"]["force_remeasure"] is True
        assert record["context"]["protocol_hash"] == fingerprint["protocol_hash"]
        assert record["binary_sha256"] == fingerprint["binary_hashes"][record["config"]["optimization"]]
        assert record["reference_sha256"] == fingerprint["reference_sha256"]
        run = session / "runs" / Path(record["run_directory"]).name
        assert run.is_dir(), f"missing run evidence: {run}"
        saved = json.loads((run / "result.json").read_text())
        assert all(record.get(key) == value for key, value in saved.items()), "run result/sample mismatch"
        for field, filename in (("raw_stdout", "stdout.txt"), ("raw_stderr", "stderr.txt"),
                                ("raw_resource", "resource.txt")):
            assert (run / filename).read_text() == record[field], f"raw evidence mismatch: {run}/{filename}"
        assert sha256_text(record["raw_stdout"]) == record["stdout_sha256"]
        assert sha256_text(record["raw_stderr"]) == record["stderr_sha256"]
        match = re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", record["raw_resource"])
        if match:
            peak_rss_kib = max(peak_rss_kib, int(match[1]))
        match = re.search(r"Major \(requiring I/O\) page faults:\s*(\d+)", record["raw_resource"])
        if match:
            process_major_faults.append(int(match[1]))
        resources.extend(record.get("resource_samples", []))
    completed = checkpoint["completed"]
    canonical = ConfigSpace.load(ROOT / "configs/config_space.json").all()
    for index, group in enumerate(completed):
        restore_complete_group(group, protocol)
        aggregate = summarize_group(Config(**group["config"]), group["attempt_id"], group["samples"],
                                    protocol["measurement"]["measured_runs"], group["evaluation_wall_seconds"])
        for field in ("statistics", "measured_compute_seconds", "process_wall_seconds",
                      "compute_total_seconds", "validation_total_seconds"):
            assert group[field] == aggregate[field], f"aggregate mismatch: {field}"
        assert group["config"] == {"optimization": canonical[index].optimization,
                                  "block_size": canonical[index].block_size}
        for sample in group["samples"]:
            assert sample == by_id[sample["run_id"]], "checkpoint/sample JSONL mismatch"
    retest = checkpoint.get("independent_retest")
    if retest:
        restore_complete_group(retest, protocol)
        aggregate = summarize_group(Config(**retest["config"]), retest["attempt_id"], retest["samples"],
                                    protocol["measurement"]["measured_runs"], retest["evaluation_wall_seconds"])
        assert retest["statistics"] == aggregate["statistics"], "retest statistics mismatch"
        for sample in retest["samples"]:
            assert sample == by_id[sample["run_id"]]
        assert retest["config"] == min(completed, key=lambda group: group["score_seconds"])["config"]
    grid_ids = {sample["run_id"] for group in completed for sample in group["samples"]}
    retest_ids = {sample["run_id"] for sample in retest["samples"]} if retest else set()
    unscored_records = [record for record in records if record["run_id"] not in grid_ids | retest_ids]
    if (session / "grid_summary.csv").exists():
        table = list(csv.DictReader((session / "grid_summary.csv").open(newline="")))
        assert len(table) == len(completed)
        for row, group in zip(table, completed):
            assert row["optimization"] == group["config"]["optimization"]
            assert int(row["block_size"]) == group["config"]["block_size"]
            assert float(row["median_seconds"]) == group["score_seconds"]
            for field, value in group["statistics"].items():
                assert float(row[field]) == value, f"CSV statistic mismatch: {field}"
            assert float(row["process_wall_seconds"]) == group["process_wall_seconds"]
            assert row["valid"] == "True"
    gates = [json.loads(path.read_text()) for path in (session / "gates").glob("*.json")]
    grid_gates = [item for item in gates if item["purpose"] == "grid" and
                  valid_formal_gate(item["parsed"], protocol)]
    for group in completed:
        assert any(item["config"] == group["config"] for item in grid_gates), "missing passed formal gate"
    if retest:
        assert any(item["purpose"] == "independent_retest" and item["config"] == retest["config"] and
                   valid_formal_gate(item["parsed"], protocol) for item in gates), "missing retest gate"
    host_samples = [item for sample in resources for item in sample.get("host", {}).get("host_samples", [])]
    # The laptop/WSL restarted between attempts. System counters cannot be subtracted
    # across boots; sum each recorded run's before/after differences instead.
    vmstat_deltas = []
    for record in records:
        before = record["resource_before"]["vmstat"]
        after = record["resource_after"]["vmstat"]
        assert all(after[key] >= before[key] for key in ("pswpin", "pswpout", "pgmajfault")), \
            "vmstat reset within a supposedly complete execution"
        vmstat_deltas.append({key: after[key] - before[key] for key in before})
    interruptions_path = session / "interruption_record.json"
    interruption = json.loads(interruptions_path.read_text()) if interruptions_path.exists() else None
    minimum_host = min((sample["available_memory_bytes"] for sample in host_samples), default=None)
    minimum_wsl = min((sample["mem_available_bytes"] for sample in resources), default=None)
    complete = len(completed) == 20 and retest is not None and checkpoint["status"] == "complete"
    return {
        "schema": "p2-evidence-audit-v2", "captured_at": utc_now(),
        "auditor_sha256": sha256_file(Path(__file__)),
        "command_argv": [sys.executable, *sys.argv],
        "audit_scope": "raw consistency, scoring contract, sample completeness; "
                       "not independent clock calibration or stationary-resource assurance",
        "evidence_audit": "PASS", "grid_complete": complete,
        "content_commit": fingerprint["content_commit"], "protocol_hash": fingerprint["protocol_hash"],
        "checkpoint_status": checkpoint["status"], "completed_count": len(completed),
        "valid_count": len(completed), "remaining_count": 20 - len(completed),
        "raw_execution_count": len(records),
        "grid_execution_count": sum(record["purpose"] == "grid" for record in records),
        "retest_execution_count": sum(record["purpose"] == "retest" for record in records),
        "completed_grid_execution_count": len(grid_ids),
        "completed_grid_measurement_count": sum(by_id[run_id]["role"] == "measurement" for run_id in grid_ids),
        "completed_retest_execution_count": len(retest_ids),
        "unscored_complete_execution_count": len(unscored_records),
        "interrupted_execution_without_complete_result": interruption,
        "abandoned_attempts": checkpoint["abandoned_attempts"],
        "all_samples_are_fresh": all(record.get("source") == "fresh_measurement" for record in records),
        "process_peak_rss_kib": peak_rss_kib,
        "process_major_fault_record_count": len(process_major_faults),
        "process_major_fault_total": sum(process_major_faults),
        "runtime_host_minimum_available_bytes": minimum_host,
        "runtime_wsl_minimum_available_bytes": minimum_wsl,
        "wsl_swap_peak_used_bytes": max((sample["swap_total_bytes"] - sample["swap_free_bytes"]
                                         for sample in resources), default=None),
        "wsl_swap_in_delta_pages_during_recorded_runs": sum(item["pswpin"] for item in vmstat_deltas),
        "wsl_swap_out_delta_pages_during_recorded_runs": sum(item["pswpout"] for item in vmstat_deltas),
        "wsl_major_fault_delta_during_recorded_runs": sum(item["pgmajfault"] for item in vmstat_deltas),
        "vmstat_scope": "system-wide deltas summed only within complete executions; excludes gaps and interrupted execution",
        "runtime_host_samples_below_start_memory_gate": sum(sample["available_memory_bytes"] <
            protocol["resource_gate"]["formal_host_minimum_available_bytes"] for sample in host_samples),
        "runtime_host_maximum_cpu_percent": max((sample["cpu_percent"] for sample in host_samples), default=None),
        "runtime_host_samples_above_start_cpu_gate": sum(sample["cpu_percent"] >
            protocol["resource_gate"]["formal_host_cpu_single_sample_maximum_percent"] for sample in host_samples),
        "runtime_host_maximum_commit_percent": max((sample["percent_committed_bytes_in_use"]
                                                    for sample in host_samples), default=None),
        "runtime_host_maximum_pages_per_second": max((sample["pages_per_second"]
                                                      for sample in host_samples), default=None),
        "runtime_host_maximum_page_reads_per_second": max((sample["page_reads_per_second"]
                                                           for sample in host_samples), default=None),
        "formal_gate_check_count": len(gates),
        "formal_gate_pass_count": sum(valid_formal_gate(item["parsed"], protocol) for item in gates),
        "resource_sample_count": len(resources), "host_resource_sample_count": len(host_samples),
        "cost_seconds": {
            "session_active_wall": checkpoint["active_total_seconds"],
            "gates_and_wait": checkpoint["wait_seconds"],
            "initial_build_setup": checkpoint["build_setup_seconds"],
            "initial_reference_setup": checkpoint["reference_setup_seconds"],
            "all_target_process_wall": sum(record.get("process_wall_seconds", 0) for record in records),
            "all_core_compute": sum(record.get("target_result", {}).get("elapsed_seconds", 0) for record in records),
            "all_validation": sum(record.get("target_result", {}).get("validation_seconds", 0) for record in records),
            "unscored_complete_process_wall": sum(record.get("process_wall_seconds", 0)
                                                   for record in unscored_records),
            "interrupted_process_wall_lower_bound": interruption["last_observed_process_elapsed_seconds"]
                if interruption else 0,
            "per_run_build_lookup": sum(record.get("build_lookup_seconds", 0) for record in records),
            "per_run_reference_lookup": sum(record.get("reference_lookup_seconds", 0) for record in records),
        },
        "cost_caveat": "checkpoint active wall excludes uncheckpointed time before shutdown; "
                       "an interrupted execution has only an observed lower bound, not exact final cost; "
                       "target/process/active timings use CLOCK_MONOTONIC, UTC/time-v use a distinct clock domain",
        "clock_precision_note": "docs/P2_TIMING_NOTE.md",
        "unknown_metrics": ["CPU temperature", "reliable boost/throttling", "hardware performance counters"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    result = audit(args.session)
    if args.output:
        atomic_write_json(args.output, result)
    print(json.dumps(result, indent=2))
    return 2 if args.require_complete and not result["grid_complete"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
