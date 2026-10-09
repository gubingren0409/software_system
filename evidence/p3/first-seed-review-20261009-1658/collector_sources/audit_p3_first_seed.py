"""Host-side postprocessing only; Git must understand the Windows worktree file."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autotuner.core import atomic_write_json, sha256_file
from scripts.audit_p3_evidence import audit

BASELINE = "e46b96cff35e7ea3b23c0b1eaef5fc66b03399ec"
CAMPAIGN = ROOT / "evidence/p3/campaign-e308bfb"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def committed(relative):
    data = subprocess.check_output(["git", "-C", str(ROOT), "show", BASELINE + ":" + relative])
    return json.loads(data.decode("utf-8"))


def unchanged_original_files():
    protected = ["autotuner", "code", "configs", "evidence/p2/grid-session-0d3dd52",
                 "evidence/p3/content-e308bfb", "evidence/p3_audit_0023ceed"]
    modified = subprocess.check_output(
        ["git", "-C", str(ROOT), "diff", "--name-only", BASELINE, "--", *protected], text=True)
    if modified.strip():
        raise ValueError("Protected original files changed: " + modified)
    campaign_path = "evidence/p3/campaign-e308bfb"
    originals = set(subprocess.check_output(
        ["git", "-C", str(ROOT), "ls-tree", "-r", "--name-only", BASELINE, "--", campaign_path],
        text=True).splitlines())
    changed = set(subprocess.check_output(
        ["git", "-C", str(ROOT), "diff", "--name-only", BASELINE, "--", campaign_path],
        text=True).splitlines())
    permitted = {campaign_path + "/" + name for name in (
        "checkpoint.json", "PAUSE_REQUEST", "trajectories/00_random_20261008/checkpoint.json",
        "trajectories/00_random_20261008/samples.jsonl")}
    if (changed & originals) - permitted:
        raise ValueError("Original campaign material changed: " + str((changed & originals) - permitted))
    return {"protected_paths": protected, "original_campaign_file_count": len(originals),
            "permitted_mutable_paths": sorted(permitted), "status": "PASS"}


def activity_costs(checkpoint, baseline, states):
    """Separate nested campaign cost from terminal search and retest calls."""
    return {"clock": "uncalibrated CLOCK_MONOTONIC seconds",
            "campaign_active_seconds": checkpoint["active_total_seconds"],
            "campaign_gate_and_wait_seconds": checkpoint["wait_seconds"],
            "this_batch_checkpoint_active_delta_seconds":
                checkpoint["active_total_seconds"] - baseline["active_total_seconds"],
            "this_batch_checkpoint_gate_and_wait_delta_seconds":
                checkpoint["wait_seconds"] - baseline["wait_seconds"],
            "trajectories": [{"job": state["job"],
                "terminal_search_evaluator_seconds": sum(group["evaluation_wall_seconds"]
                    for group in state["observations"]),
                "independent_retest_evaluator_seconds": sum(group["evaluation_wall_seconds"]
                    for group in state["independent_retests"])} for state in states],
            "scope": "Campaign active includes gates/setup/abandoned attempts/retests and prior "
                "invocations; excludes offline pauses and uncheckpointed interruption tails. "
                "Gate/wait and terminal calls are nested, not additive to campaign active."}


def check_clock_intervals(probe, criteria, expected_count):
    """Same audit criteria, without importing the POSIX-only diagnostic runner."""
    checks = []
    for index, sample in enumerate(probe["wsl_intervals"]):
        delta = sample["delta"]
        raw = delta["raw_seconds"]
        row = {"interval_index": index, "delta": delta}
        for clock, rule in (("monotonic", "monotonic"), ("realtime", "realtime")):
            value = delta[clock + "_seconds"]
            row[clock + "_raw_pass"] = all(math.isfinite(v) and v > 0 for v in (value, raw)) and \
                abs(value - raw) <= criteria[rule + "_raw_absolute_allowance_seconds"] + \
                    criteria[rule + "_raw_relative_tolerance"] * raw
        checks.append(row)
    return {"pass": expected_count > 0 and len(checks) == expected_count and
            all(row["monotonic_raw_pass"] and row["realtime_raw_pass"] for row in checks),
            "expected_interval_count": expected_count, "checks": checks}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-two", action="store_true")
    parser.add_argument("--clock-recovery", type=Path)
    args = parser.parse_args()
    protection = unchanged_original_files()
    result = audit(CAMPAIGN, ROOT / "evidence/p2/grid-session-0d3dd52")
    checkpoint = read(CAMPAIGN / "checkpoint.json")
    original = committed("evidence/p3/campaign-e308bfb/checkpoint.json")
    if checkpoint["session_id"] != original["session_id"] or checkpoint["fingerprint"] != original["fingerprint"]:
        raise ValueError("Original campaign identity changed")
    name = "00_random_20261008"
    directory = CAMPAIGN / "trajectories" / name
    state = read(directory / "checkpoint.json")
    before = committed("evidence/p3/campaign-e308bfb/trajectories/" + name + "/checkpoint.json")
    if state["observations"][:len(before["observations"])] != before["observations"]:
        raise ValueError("An existing complete observation changed")
    prefix = read(args.batch / "samples_prefix_before.json")
    if hashlib.sha256((directory / "samples.jsonl").read_bytes()[:prefix["bytes"]]).hexdigest() != prefix["sha256"]:
        raise ValueError("The original raw sample prefix changed")
    partial_id = before["active"]["attempt_id"]
    partial = read(directory / "configurations" / ("search_" + partial_id + ".json"))
    if partial != committed("evidence/p3/campaign-e308bfb/trajectories/" + name + "/configurations/search_" + partial_id + ".json"):
        raise ValueError("Original partial attempt changed")
    if len(partial["samples"]) != 3:
        raise ValueError("Original O0/s8 partial count differs")
    abandoned = any(item["attempt_id"] == partial_id and item["sample_count"] == 3
                    for item in state["abandoned_attempts"])
    complete = result["completed_trajectory_count"] == 2 and checkpoint["status"] == "batch_complete"
    if complete and (not abandoned or len(result["prefix_rows"]) != 6 or
                     [item["name"] for item in result["trajectories"]] !=
                     ["00_random_20261008", "01_greedy_20261008"] or
                     any(item["unique_count"] != 12 or item["job"]["seed"] != 20261008 or
                         item["trajectory_status"] != "complete"
                         for item in result["trajectories"])):
        raise ValueError("First-seed trajectory or abandoned-attempt contract differs")
    partial_cost = {"process_wall_seconds": sum(sample["process_wall_seconds"] for sample in partial["samples"]),
                    "core_seconds": sum(sample["target_result"]["elapsed_seconds"] for sample in partial["samples"])}
    for row in result["prefix_rows"]:
        if row["independent_retest_median_seconds"] is not None:
            row["retest_change_from_own_percent"] = 100 * (row["independent_retest_median_seconds"] / row["own_median_seconds"] - 1)
    retests, states = [], []
    for item in result["trajectories"]:
        trajectory = read(CAMPAIGN / "trajectories" / item["name"] / "checkpoint.json")
        states.append(trajectory)
        for group in trajectory["independent_retests"]:
            retests.append({"trajectory": item["name"], "config": group["config"],
                            "attempt_id": group["attempt_id"], "median_seconds": group["score_seconds"],
                            "evaluator_seconds": group["evaluation_wall_seconds"],
                            "process_wall_seconds": group["process_wall_seconds"],
                            "core_seconds_including_warmup": group["compute_total_seconds"]})
    diagnostic_sources, host_samples, intervals = [], [], []
    for path in sorted((ROOT / "evidence/p3_audit_0023ceed/session-0d57f8c/groups").glob("*/samples.jsonl")):
        diagnostic_sources.append({"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)})
        for line in path.read_text().splitlines():
            sample = json.loads(line)
            hosts = [host for point in sample["resource_samples"]
                     for host in point.get("host", {}).get("host_samples", [])]
            host_samples.extend(hosts)
            intervals.extend((datetime.fromisoformat(b["timestamp"]) - datetime.fromisoformat(a["timestamp"])).total_seconds()
                             for a, b in zip(hosts, hosts[1:]))
    clocks = {phase: read(args.batch / (phase + ".check.json"))
              for phase in ("clock_before", "clock_after") if (args.batch / (phase + ".check.json")).exists()}
    clocks_pass = len(clocks) == 2 and all(item["pass"] for item in clocks.values())
    recovery = None
    if args.clock_recovery:
        recovery_policy = read(args.clock_recovery / "policy.json")
        criteria_path = ROOT / "configs/timing_audit_protocol.json"
        if sha256_file(criteria_path) != recovery_policy["criteria_file_sha256"]:
            raise ValueError("Clock recovery criteria changed")
        recovery = check_clock_intervals(read(args.clock_recovery / "probe.json"),
            read(criteria_path)["diagnostic_criteria"], recovery_policy["intervals"])
        recovery.update(probe_sha256=sha256_file(args.clock_recovery / "probe.json"),
                        policy_sha256=sha256_file(args.clock_recovery / "policy.json"))
    nonterminal = []
    scored_ids = {sample["run_id"] for group in [*state["observations"], *state["independent_retests"]]
                  for sample in group["samples"]}
    attempts = [*state["abandoned_attempts"], *([state["active"]] if state["active"] else [])]
    for attempt in attempts:
        path = directory / "configurations" / (attempt["purpose"] + "_" + attempt["attempt_id"] + ".json")
        if not path.exists():
            continue
        group = read(path)
        if any(sample["run_id"] in scored_ids for sample in group["samples"]):
            raise ValueError("A partial attempt contributed to a terminal score")
        nonterminal.append({"attempt_id": attempt["attempt_id"], "config": attempt["config"],
            "sample_count": len(group["samples"]), "group_sha256": sha256_file(path),
            "state": "abandoned" if attempt in state["abandoned_attempts"] else "interrupted_pending_restart",
            "process_wall_seconds": sum(sample["process_wall_seconds"] for sample in group["samples"]),
            "core_seconds": sum(sample["target_result"]["elapsed_seconds"] for sample in group["samples"])})
    first_seed = {"audit_baseline": BASELINE, "formal_first_seed_complete": complete,
        "campaign_audit": result, "independent_retests": retests,
        "activity_costs": activity_costs(checkpoint, read(args.batch / "campaign_checkpoint_before.json"), states),
        "original_file_protection": protection, "old_partial_cost": partial_cost,
        "nonterminal_attempts": nonterminal, "clock_recovery_reevaluation": recovery,
        "since_audit_baseline_active_delta_seconds": checkpoint["active_total_seconds"] - original["active_total_seconds"],
        "old_complete_observations_unchanged": len(before["observations"]),
        "old_raw_sample_prefix_unchanged": True, "old_partial_samples_preserved": 3,
        "old_partial_marked_abandoned": abandoned, "boundary_clock_checks": clocks,
        "both_boundary_clock_checks_pass": clocks_pass,
        "historical_windows_sampling_correction": {"sources": diagnostic_sources,
            "runtime_host_samples": len(host_samples), "interval_min_seconds": min(intervals),
            "interval_max_seconds": max(intervals), "interval_median_seconds": statistics.median(intervals),
            "minimum_available_bytes": min(item["available_memory_bytes"] for item in host_samples),
            "below_2gib_count": sum(item["available_memory_bytes"] < 2147483648 for item in host_samples),
            "maximum_cpu_percent": max(item["cpu_percent"] for item in host_samples)},
        "cost_scope": "Prefix evaluator totals exclude gates/setup/abandoned attempts/retests/offline waits; campaign checkpoint active cost is separate and includes prior invocations. Nested time scopes must not be added.",
        "postprocessor_sha256": sha256_file(Path(__file__))}
    atomic_write_json(args.output, first_seed)
    print(json.dumps({key: first_seed[key] for key in ("formal_first_seed_complete", "old_complete_observations_unchanged",
        "old_raw_sample_prefix_unchanged", "old_partial_samples_preserved", "old_partial_marked_abandoned")}))
    return 2 if args.require_two and not (complete and clocks_pass and (recovery is None or recovery["pass"])) else 0


if __name__ == "__main__":
    raise SystemExit(main())
