"""Postprocessing only: replay private trajectories, then compare with the P2 table."""
from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autotuner.campaign import audit_trajectory
from autotuner.core import ConfigSpace, atomic_write_json, atomic_write_text, sha256_file, sha256_json, utc_now
from autotuner.session import valid_formal_gate


def audit(campaign_root: Path, grid_root: Path | None = None) -> dict:
    checkpoint = json.loads((campaign_root / "checkpoint.json").read_text())
    protocol = json.loads((campaign_root / "protocol.json").read_text())
    campaign = json.loads((campaign_root / "campaign_protocol.json").read_text())
    fingerprint = checkpoint["fingerprint"]
    if sha256_json(protocol) != fingerprint["measurement_protocol_hash"] or \
            sha256_json(campaign) != fingerprint["campaign_protocol_hash"]:
        raise ValueError("campaign protocol hashes differ")
    diagnostic = fingerprint["diagnostic_only"]
    if diagnostic and grid_root is not None:
        raise ValueError("diagnostic n=130 cannot be compared with formal n=4096 Grid")
    space = ConfigSpace.load(ROOT / "configs/config_space.json")
    gates = [json.loads(path.read_text()) for path in (campaign_root / "gates").glob("*.json")]
    results, prefix_rows, configuration_rows, all_ids, resources = [], [], [], set(), []
    for index, job in enumerate(campaign["schedule"]):
        name = f"{index:02d}_{job['algorithm']}_{job['seed']}"
        destination = campaign_root / "trajectories" / name
        path = destination / "checkpoint.json"
        if not path.exists():
            continue
        state = json.loads(path.read_text())
        if state["job"] != job or state["fingerprint_hash"] != sha256_json(fingerprint):
            raise ValueError("trajectory fingerprint differs")
        result = audit_trajectory(destination, state, space, campaign["unique_budget_per_trajectory"], protocol)
        result.update(name=name, trajectory_status=state["status"], checkpoint_sha256=sha256_file(path))
        results.append(result)
        sample_path = destination / "samples.jsonl"
        records = [json.loads(line) for line in sample_path.read_text().splitlines() if line] \
                  if sample_path.exists() else []
        for record in records:
            if record["run_id"] in all_ids:
                raise ValueError("execution ID reused across trajectories")
            all_ids.add(record["run_id"])
            if "binary_sha256" in record and record["binary_sha256"] != \
                    fingerprint["binary_hashes"][record["config"]["optimization"]]:
                raise ValueError("candidate binary differs from campaign")
            if "reference_sha256" in record and record["reference_sha256"] != fingerprint["reference_sha256"]:
                raise ValueError("reference data differs from campaign")
            resources.extend(record.get("resource_samples", []))
        for position, group in enumerate(state["observations"], 1):
            if not diagnostic and not any(item["purpose"] == f"{name}/search" and
                    item["config"] == group["config"] and item["returncode"] == 0 and
                    valid_formal_gate(item["parsed"], protocol) for item in gates):
                raise ValueError("missing passed formal configuration start gate")
            configuration_rows.append({"algorithm": job["algorithm"], "search_seed": job["seed"],
                "evaluation_index": position, **group["config"], "classification": group["classification"],
                "median_seconds": group["score_seconds"], "attempt_id": group["attempt_id"],
                "configuration_evaluation_seconds": group["evaluation_wall_seconds"],
                "configuration_total_wall_seconds": group.get("configuration_total_wall_seconds"),
                "diagnostic_only": diagnostic})
        retests = state.get("independent_retests", [])
        for retest in retests:
            if not diagnostic and not any(item["purpose"] == f"{name}/independent_retest" and
                    item["config"] == retest["config"] and item["returncode"] == 0 and
                    valid_formal_gate(item["parsed"], protocol) for item in gates):
                raise ValueError("missing passed retest gate")
        for row in result["prefixes"]:
            config = row["best_config"] or {}
            retest = next((group for group in retests if group["config"] == config), None)
            prefix_rows.append({"algorithm": job["algorithm"], "search_seed": job["seed"],
                "budget": row["budget"], "valid_count": row["valid_count"],
                "optimization": config.get("optimization"), "block_size": config.get("block_size"),
                "own_median_seconds": row["median_seconds"],
                "configuration_evaluation_seconds": row["configuration_evaluation_seconds"],
                "configuration_total_wall_seconds": row["configuration_total_wall_seconds"],
                "configuration_start_gate_seconds": row["configuration_start_gate_seconds"],
                "p2_selected_configuration_median_seconds": None,
                "selection_gap_in_p2_table_percent": None, "own_time_gap_to_p2_minimum_percent": None,
                "independent_retest_median_seconds": retest["score_seconds"]
                    if retest and retest["classification"] == "success" else None,
                "diagnostic_only": diagnostic})
    grid_identity = None
    if grid_root is not None:
        from scripts.audit_p2_evidence import audit as audit_grid
        grid_audit = audit_grid(grid_root)
        if not grid_audit["grid_complete"] or grid_audit["protocol_hash"] != fingerprint["measurement_protocol_hash"]:
            raise ValueError("Grid is incomplete or uses a different measurement protocol")
        grid_checkpoint = json.loads((grid_root / "checkpoint.json").read_text())
        grid_fingerprint = grid_checkpoint["fingerprint"]
        if grid_fingerprint["reference_sha256"] != fingerprint["reference_sha256"] or \
                grid_fingerprint["compiler_sha256"] != fingerprint["compiler_sha256"]:
            raise ValueError("Grid input/reference/compiler differs")
        for relative in campaign["unchanged_source_sha256"]:
            if grid_fingerprint["files"][relative]["executed_sha256"] != fingerprint["files"][relative]["executed_sha256"]:
                raise ValueError("Grid target/measurement/strategy sources differ")
        grid_groups = grid_checkpoint["completed"]
        best_time = min(group["score_seconds"] for group in grid_groups)
        for row in prefix_rows:
            if row["own_median_seconds"] is None:
                continue
            group = next(group for group in grid_groups if group["config"] ==
                         {"optimization": row["optimization"], "block_size": row["block_size"]})
            row["p2_selected_configuration_median_seconds"] = group["score_seconds"]
            row["selection_gap_in_p2_table_percent"] = 100 * (group["score_seconds"] / best_time - 1)
            row["own_time_gap_to_p2_minimum_percent"] = 100 * (row["own_median_seconds"] / best_time - 1)
        grid_identity = {"content_commit": grid_fingerprint["content_commit"],
                         "checkpoint_sha256": sha256_file(grid_root / "checkpoint.json"),
                         "lowest_median_seconds": best_time,
                         "scope": "post-hoc reference only; never provided to a SearchStrategy"}
    completed = sum(item["trajectory_status"] == "complete" for item in results)
    for saved in checkpoint["completed_trajectories"]:
        actual = next((item for item in results if item["name"] == saved["name"]), None)
        if actual is None or actual["checkpoint_sha256"] != saved["checkpoint_sha256"]:
            raise ValueError("campaign/trajectory checkpoint hashes differ")
    host_samples = [item for resource in resources for item in resource.get("host", {}).get("host_samples", [])]
    aggregates = []
    for algorithm in ("random", "greedy"):
        for budget in (4, 8, 12):
            selected = [row for row in prefix_rows if row["algorithm"] == algorithm and row["budget"] == budget]
            values = [row["own_median_seconds"] for row in selected if row["own_median_seconds"] is not None]
            aggregates.append({"algorithm": algorithm, "budget": budget, "observed_seed_count": len(selected),
                "valid_seed_count": len(values), "mean_best_median_seconds": statistics.mean(values) if values else None,
                "sample_stdev_best_median_seconds": statistics.stdev(values) if len(values) > 1 else None,
                "scope": "partial unless all five frozen seeds are present; n=1 dispersion is unknown, not zero"})
    return {"schema": "p3-evidence-audit-v1", "captured_at": utc_now(), "status": "PASS",
        "auditor_sha256": sha256_file(Path(__file__)), "content_commit": fingerprint["content_commit"],
        "campaign_status": checkpoint["status"], "diagnostic_only": diagnostic,
        "completed_trajectory_count": completed, "remaining_trajectory_count": 10 - completed,
        "unique_configuration_count": sum(item["unique_count"] for item in results),
        "raw_execution_count": len(all_ids), "trajectories": results,
        "prefix_rows": prefix_rows, "configuration_rows": configuration_rows, "aggregates": aggregates,
        "p2_comparison_reference": grid_identity, "resource_sample_count": len(resources),
        "host_resource_sample_count": len(host_samples),
        "runtime_host_minimum_available_bytes": min((item["available_memory_bytes"] for item in host_samples), default=None),
        "runtime_host_maximum_cpu_percent": max((item["cpu_percent"] for item in host_samples), default=None),
        "cost_seconds": {"campaign_active_wall": checkpoint["active_total_seconds"],
                         "resource_gate_and_wait": checkpoint["wait_seconds"], "setup": checkpoint["setup_seconds"],
                         "candidate_build_setup": checkpoint["candidate_build_setup_seconds"],
                         "reference_setup": checkpoint["reference_setup_seconds"],
                         "resume_setup": sum(row["setup_seconds"] for row in checkpoint["resume_setup_records"]),
                         "all_complete_process_wall": sum(item["process_wall_seconds"] for item in results),
                         "all_terminal_configuration_evaluation": sum(item["configuration_evaluation_seconds"]
                                                                      for item in results)},
        "limitations": ["P2/P3 clock is uncalibrated MONOTONIC", "start gates do not ensure stationary resources",
                        "negative own-time gap can reflect cross-session variation, not a new oracle minimum"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--grid", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    result = audit(args.campaign, args.grid)
    args.output.mkdir(parents=True, exist_ok=True)
    for key, filename in (("prefix_rows", "prefix_summary.csv"), ("configuration_rows", "configuration_summary.csv")):
        rows = result[key]
        if rows:
            stream = io.StringIO()
            writer = csv.DictWriter(stream, list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
            atomic_write_text(args.output / filename, stream.getvalue())
    atomic_write_json(args.output / "audit.json", result)
    print(json.dumps({key: result[key] for key in
                     ("status", "campaign_status", "completed_trajectory_count", "unique_configuration_count", "raw_execution_count")}))
    return 2 if args.require_complete and result["completed_trajectory_count"] != 10 else 0


if __name__ == "__main__":
    raise SystemExit(main())
