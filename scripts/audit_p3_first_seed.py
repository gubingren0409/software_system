"""Host-side postprocessing only; Git must understand the Windows worktree file."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autotuner.core import sha256_file
from scripts.audit_p3_evidence import audit
from scripts.p3_clock_contract import (acceptance, acceptance_exit, atomic_write_json, check_clock_intervals,
    load, snapshot_campaign, verify_batch_binding, verify_clock_evidence, verify_recovery, verify_setup_evidence)

BASELINE = "fdeed77c43dcbbf74de46968055677f97fed8faf"
LEGACY_BASELINE = "e46b96cff35e7ea3b23c0b1eaef5fc66b03399ec"
CAMPAIGN = ROOT / "evidence/p3/campaign-e308bfb"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def committed(relative, commit=BASELINE):
    data = subprocess.check_output(["git", "-C", str(ROOT), "show", commit + ":" + relative])
    return json.loads(data.decode("utf-8"))


def verify_sample_prefix(path, prefix, identity_path):
    """Bind runtime bytes first; allow only documented Git CRLF/LF conversion later."""
    data = path.read_bytes()
    raw_prefix = data[:prefix["bytes"]]
    raw_match = hashlib.sha256(raw_prefix).hexdigest() == prefix["sha256"]
    if not identity_path.exists():
        if not raw_match or not raw_prefix.endswith(b"\n"):
            raise ValueError("Original raw sample prefix differs")
        atomic_write_json(identity_path, {"runtime_bytes": prefix["bytes"],
            "runtime_sha256": prefix["sha256"], "line_count": raw_prefix.count(b"\n"),
            "lf_normalized_sha256": hashlib.sha256(raw_prefix.replace(b"\r\n", b"\n")).hexdigest(),
            "scope": "Outer JSONL line endings only; embedded stdout/stderr strings are not changed"})
    identity = read(identity_path)
    if (identity["runtime_bytes"], identity["runtime_sha256"]) != (prefix["bytes"], prefix["sha256"]):
        raise ValueError("Prefix identity belongs to another snapshot")
    lines = data.splitlines(keepends=True)
    normalized = b"".join(lines[:identity["line_count"]]).replace(b"\r\n", b"\n")
    if len(lines) < identity["line_count"] or \
            hashlib.sha256(normalized).hexdigest() != identity["lf_normalized_sha256"]:
        raise ValueError("Original sample prefix content differs")
    return {"raw_bytes_match": raw_match, "lf_normalized_text_match": True, "identity": identity}


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


def first_seed_execution_complete(result, checkpoint):
    trajectories = result["trajectories"]
    rows = result["prefix_rows"]
    return checkpoint["status"] == "batch_complete" and result["completed_trajectory_count"] == 2 and \
        [row["name"] for row in trajectories] == ["00_random_20261008", "01_greedy_20261008"] and \
        all(row["unique_count"] == 12 and row["job"]["seed"] == 20261008 and
            row["trajectory_status"] == "complete" for row in trajectories) and len(rows) == 6 and \
        {(row["algorithm"], row["search_seed"], row["budget"]) for row in rows} == \
        {(algorithm, 20261008, budget) for algorithm in ("random", "greedy") for budget in (4, 8, 12)} and \
        all(row["own_median_seconds"] is not None and row["independent_retest_median_seconds"] is not None for row in rows)


def campaign_timing_certified(purpose, clocks, recovery, campaign_invoked):
    """Recovery alone never certifies the timing of an actual campaign batch."""
    return purpose == "resume" and campaign_invoked is True and \
        set(clocks) == {"clock_before", "clock_after"} and all(item["pass"] for item in clocks.values()) and \
        recovery is not None and recovery.get("recovery_eligible") is True


def audit_first_seed(args):
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
    new_batch = (args.batch / "manifest.json").exists()
    if new_batch:
        previous = load(args.batch / "campaign_before.json")["trajectories"][name]
        prefix = {"bytes": previous["sample_bytes"], "sha256": previous["samples_sha256"]}
    else:
        prefix = read(args.batch / "samples_prefix_before.json")
    prefix_check = verify_sample_prefix(directory / "samples.jsonl", prefix,
                                       args.batch / "samples_prefix_normalized_identity.json")
    old_state = committed("evidence/p3/campaign-e308bfb/trajectories/" + name + "/checkpoint.json", LEGACY_BASELINE)
    partial_id = old_state["active"]["attempt_id"]
    partial = read(directory / "configurations" / ("search_" + partial_id + ".json"))
    if partial != committed("evidence/p3/campaign-e308bfb/trajectories/" + name + "/configurations/search_" + partial_id + ".json", LEGACY_BASELINE):
        raise ValueError("Original partial attempt changed")
    if len(partial["samples"]) != 3:
        raise ValueError("Original O0/s8 partial count differs")
    abandoned = any(item["attempt_id"] == partial_id and item["sample_count"] == 3
                    for item in state["abandoned_attempts"])
    complete = first_seed_execution_complete(result, checkpoint)
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
    clocks, binding = {}, None
    clock_integrity, clocks_pass = True, False
    if new_batch and load(args.batch / "manifest.json")["purpose"] == "resume":
        binding = verify_batch_binding(args.batch, snapshot_campaign(CAMPAIGN))
        setup = verify_setup_evidence(args.batch, load(args.batch / "manifest.json"))
        clocks = {phase: verify_clock_evidence(args.batch, phase) for phase in ("clock_before", "clock_after")
                  if (args.batch / (phase + ".operation.json")).exists()}
        clock_integrity = setup["frozen_identity_pass"] and all(item["evidence_integrity_pass"] for item in clocks.values())
        clocks_pass = len(clocks) == 2 and all(item["pass"] for item in clocks.values())
        controller = load(args.batch / "controller.json")
        for phase, field in (("clock_before", "pre_clock_pass"), ("clock_after", "post_clock_pass")):
            if phase in clocks and controller[field] != clocks[phase]["pass"]:
                clock_integrity = False
        if binding["campaign_invoked"] and controller["campaign_returncode"] != 0:
            complete = False
        if binding["campaign_invoked"] and not setup["formal_resource_gate_pass"]:
            raise ValueError("Formal campaign invoked without passed resource gate")
    elif not new_batch:
        for phase in ("clock_before", "clock_after"):
            path = args.batch / (phase + ".wsl.json")
            if path.exists():
                clocks[phase] = check_clock_intervals(load(path), read(ROOT / "configs/timing_audit_protocol.json")["diagnostic_criteria"], 3)
                saved = read(args.batch / (phase + ".check.json"))
                clock_integrity = clock_integrity and clocks[phase]["evidence_integrity_pass"] and saved["pass"] == clocks[phase]["pass"]
        # v1 lacks the new invocation/checkpoint binding. It cannot certify a newer batch.
    recovery = None
    if args.clock_recovery:
        recovery_policy = read(args.clock_recovery / "policy.json")
        criteria_path = ROOT / "configs/timing_audit_protocol.json"
        if sha256_file(criteria_path) != recovery_policy.get("criteria_sha256", recovery_policy.get("criteria_file_sha256")):
            raise ValueError("Clock recovery criteria changed")
        if (args.clock_recovery / "manifest.json").exists():
            if new_batch and load(args.batch / "manifest.json")["purpose"] == "resume" and \
                    load(args.batch / "manifest.json")["recovery_manifest_sha256"] != sha256_file(args.clock_recovery / "manifest.json"):
                raise ValueError("Recovery evidence does not belong to this batch")
            recovery = verify_recovery(args.clock_recovery,
                load(args.batch / "campaign_before.json") if new_batch else None)
        else:
            recovery = check_clock_intervals(load(args.clock_recovery / "probe.json"),
                read(criteria_path)["diagnostic_criteria"], recovery_policy["intervals"])
            recovery.update(recovery_eligible=False, legacy_scope="Historical 10-interval diagnostic, not this round's 20-interval authorization")
        clock_integrity = clock_integrity and recovery["evidence_integrity_pass"]
    if new_batch and load(args.batch / "manifest.json")["purpose"] == "recover":
        recovery = verify_recovery(args.batch, snapshot_campaign(CAMPAIGN))
        clock_integrity = recovery["evidence_integrity_pass"]
    if new_batch:
        clocks_pass = campaign_timing_certified(load(args.batch / "manifest.json")["purpose"], clocks,
                                                recovery, binding is not None and binding["campaign_invoked"])
    nonterminal = []
    for trajectory, info in zip(states, result["trajectories"]):
        trajectory_name = info["name"]
        destination = CAMPAIGN / "trajectories" / trajectory_name
        scored_ids = {sample["run_id"] for group in [*trajectory["observations"], *trajectory["independent_retests"]]
                      for sample in group["samples"]}
        attempts = [*trajectory["abandoned_attempts"], *([trajectory["active"]] if trajectory["active"] else [])]
        for attempt in attempts:
            path = destination / "configurations" / (attempt["purpose"] + "_" + attempt["attempt_id"] + ".json")
            if not path.exists():
                continue
            group = read(path)
            if any(sample["run_id"] in scored_ids for sample in group["samples"]):
                raise ValueError("A partial attempt contributed to a terminal score")
            nonterminal.append({"trajectory": trajectory_name, "attempt_id": attempt["attempt_id"], "config": attempt["config"],
                "sample_count": len(group["samples"]), "group_sha256": sha256_file(path),
                "state": "abandoned" if attempt in trajectory["abandoned_attempts"] else "interrupted_pending_restart",
                "process_wall_seconds": sum(sample["process_wall_seconds"] for sample in group["samples"]),
                "core_seconds": sum(sample["target_result"]["elapsed_seconds"] for sample in group["samples"])})
    status = acceptance(clock_integrity, complete, clocks_pass)
    first_seed = {**status, "audit_baseline": BASELINE, "formal_first_seed_complete": complete,
        "campaign_audit": result, "independent_retests": retests,
        "activity_costs": activity_costs(checkpoint, load(args.batch / "campaign_before.json")["checkpoint"]
                                       if new_batch else read(args.batch / "campaign_checkpoint_before.json"), states),
        "original_file_protection": protection, "old_partial_cost": partial_cost,
        "nonterminal_attempts": nonterminal, "clock_recovery_reevaluation": recovery,
        "since_audit_baseline_active_delta_seconds": checkpoint["active_total_seconds"] - original["active_total_seconds"],
        "old_complete_observations_unchanged": len(before["observations"]),
        "old_raw_sample_prefix_unchanged": prefix_check["raw_bytes_match"],
        "old_sample_prefix_text_unchanged": prefix_check["lf_normalized_text_match"],
        "sample_prefix_identity": prefix_check["identity"], "old_partial_samples_preserved": 3,
        "old_partial_marked_abandoned": abandoned, "boundary_clock_checks": clocks,
        "both_boundary_clock_checks_pass": clocks_pass,
        "batch_binding": binding, "legacy_clock_evidence_not_a_new_batch_certificate": not new_batch,
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
    if args.acceptance_mode == "incomplete" and complete:
        return 1
    return acceptance_exit(status, args.require_two or args.acceptance_mode == "complete")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-two", action="store_true")
    parser.add_argument("--clock-recovery", type=Path)
    parser.add_argument("--acceptance-mode", choices=("incomplete", "complete"))
    args = parser.parse_args()
    try:
        return audit_first_seed(args)
    except (ValueError, OSError, KeyError, TypeError) as error:
        atomic_write_json(args.output, {**acceptance(False, False, False), "failure_reason": str(error),
                                       "completion_not_verified": True})
        print(json.dumps({"evidence_integrity_pass": False, "failure_reason": str(error)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
