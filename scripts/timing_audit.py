"""Independent audit operations; frozen search/target measurement code is not changed."""
from __future__ import annotations

import argparse
import fcntl
import json
import math
import platform
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autotuner.campaign import validate_terminal
from autotuner.core import Config, Evaluator, TargetAdapter, atomic_write_json, sha256_file, sha256_json
from autotuner.measurement import ConfigurationEvaluator
from autotuner.session import source_identity


def readings() -> dict[str, str]:
    return {name: str(time.clock_gettime_ns(clock)) for name, clock in (
        ("monotonic_ns", time.CLOCK_MONOTONIC), ("raw_ns", time.CLOCK_MONOTONIC_RAW),
        ("realtime_ns", time.CLOCK_REALTIME), ("boottime_ns", time.CLOCK_BOOTTIME))}


def interval(start: dict[str, str], end: dict[str, str]) -> dict[str, float]:
    return {name.removesuffix("_ns") + "_seconds": (int(end[name]) - int(value)) / 1e9
            for name, value in start.items()}


def agreement(left: float, right: float, relative: float, absolute: float) -> bool:
    return all(math.isfinite(value) and value > 0 for value in (left, right)) and \
        abs(left - right) <= absolute + relative * right


def load_session(output: Path, content_sha: str) -> tuple[dict, dict, TargetAdapter]:
    audit = json.loads((ROOT / "configs/timing_audit_protocol.json").read_text())
    protocol = json.loads((ROOT / "configs/measurement_protocol.json").read_text())
    session = json.loads((output / "session.json").read_text())
    if session["content_commit"] != content_sha or session["audit_protocol_hash"] != sha256_json(audit) or \
            sha256_json(protocol) != audit["measurement_protocol_hash"]:
        raise ValueError("diagnostic session/content/protocol changed")
    identity = json.loads((output / "git_identity.json").read_text())
    if source_identity(ROOT, identity["files"]) != session["source_identity"]:
        raise ValueError("diagnostic execution files changed")
    return audit, protocol, TargetAdapter.load(output / "target.json", evidence_root=output / "setup")


def setup(output: Path, content_sha: str, identity_path: Path) -> dict:
    if (ROOT / ".git").exists() or list(ROOT.rglob("__pycache__")):
        raise ValueError("diagnostics must execute a clean committed archive")
    if (output / "session.json").exists():
        raise ValueError("new diagnostics need an independent empty session directory")
    identity = json.loads(identity_path.read_text())
    if identity["content_sha"] != content_sha:
        raise ValueError("content identity mismatch")
    audit = json.loads((ROOT / "configs/timing_audit_protocol.json").read_text())
    protocol = json.loads((ROOT / "configs/measurement_protocol.json").read_text())
    campaign = json.loads((ROOT / "configs/p3_campaign_protocol.json").read_text())
    if sha256_json(protocol) != audit["measurement_protocol_hash"]:
        raise ValueError("frozen measurement protocol differs")
    for relative, expected in campaign["unchanged_source_sha256"].items():
        if sha256_file(ROOT / relative) != expected:
            raise ValueError("frozen P2/P3 source differs: " + relative)
    output.mkdir(parents=True, exist_ok=True)
    atomic_write_json(output / "git_identity.json", identity)
    atomic_write_json(output / "protocol.json", audit)
    target_data = json.loads((ROOT / "configs/target.json").read_text())
    target_data.update(candidate_source=str(ROOT / "code/working/matrix_multiplication.c"),
                       reference_source=str(ROOT / "code/working/reference_generator.c"),
                       shared_sources=[str(ROOT / "code/working/matrix_input.h")],
                       cache_root="/var/tmp/matrix-autotuner-audit-0023ceed-" + content_sha[:12] + "/cache")
    atomic_write_json(output / "target.json", target_data)
    target = TargetAdapter.load(output / "target.json", evidence_root=output / "setup")
    if sha256_file(target.compiler) != campaign["compiler_sha256"]:
        raise ValueError("compiler changed")
    start = readings()
    binaries = {}
    for level in ("O1", "O2", "O3"):
        artifact = target.build_candidate(4096, level)
        binaries[level] = artifact.binary_sha256
        atomic_write_json(output / "manifests" / (level + ".json"),
                          json.loads((artifact.binary.parent / "manifest.json").read_text()))
    reference = target.get_reference(4096, 20261008, "random", 600)
    if reference.data_sha256 != campaign["expected_reference_data_sha256"]:
        raise ValueError("reference differs from the preserved P2/P3 input")
    ref_build = target.build_reference_generator(4096)
    atomic_write_json(output / "manifests/reference_build.json",
                      json.loads((ref_build.binary.parent / "manifest.json").read_text()))
    atomic_write_json(output / "manifests/reference.json", reference.metadata)
    end = readings()
    session = {"schema": "timing-audit-session-v1", "diagnostic_only": True,
               "content_commit": content_sha, "audit_baseline": audit["audit_baseline_commit"],
               "audit_protocol_hash": sha256_json(audit), "measurement_protocol_hash": sha256_json(protocol),
               "source_identity": source_identity(ROOT, identity["files"]), "binary_hashes": binaries,
               "compiler_sha256": sha256_file(target.compiler), "compiler_version": target._compiler_version,
               "python_version": sys.version, "platform": platform.platform(),
               "reference_key": reference.reference_key, "reference_sha256": reference.data_sha256,
               "start": start, "end": end, "interval": interval(start, end)}
    atomic_write_json(output / "session.json", session)
    return {"status": "setup_complete", "content_commit": content_sha}


class AuditExecutor(Evaluator):
    def evaluate(self, config, context):
        start = readings()
        result = super().evaluate(config, context)
        end = readings()
        atomic_write_json(self.audit_directory / "clocks" / (result["run_id"] + ".json"),
                          {"run_id": result["run_id"], "scope": "complete Evaluator call, not core",
                           "start": start, "end": end, "interval": interval(start, end)})
        return result


def group(output: Path, content_sha: str, index: int) -> dict:
    audit, protocol, _ = load_session(output, content_sha)
    job = audit["groups"][index]
    destination = output / "groups" / job["id"]
    if destination.exists():
        raise ValueError("group directory already exists; keep old attempt and use a new diagnostic session")
    target = TargetAdapter.load(output / "target.json", evidence_root=destination)
    script = subprocess_script_path(ROOT / "scripts/check_p2_resources.ps1")
    executor = AuditExecutor(target, ["/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe",
                                    "-NoProfile", "-File", script, "-Mode", "Snapshot"])
    executor.audit_directory = destination
    def sampled(sample):
        print(json.dumps({"event": "diagnostic_sample", "group": job["id"], "index": sample["sample_index"],
                          "classification": sample["classification"], "compute_seconds": sample["score_seconds"]}),
              flush=True)
    evaluator = ConfigurationEvaluator(executor, protocol, sha256_json(protocol), destination, sampled)
    start = readings()
    result = evaluator.evaluate(Config(job["optimization"], audit["target"]["block_size"]),
                                purpose="diagnostic")
    end = readings()
    validate_terminal(result, protocol)
    record = {"schema": "timing-audit-group-v1", "diagnostic_only": True, "job": job,
              "start": start, "end": end, "interval": interval(start, end), "evaluation": result}
    atomic_write_json(destination / "final.json", record)
    return {"status": result["classification"], "group": job["id"], "median_seconds": result["score_seconds"]}


def subprocess_script_path(path: Path) -> str:
    import subprocess
    return subprocess.run(["wslpath", "-w", str(path)], text=True, capture_output=True,
                          check=True).stdout.strip()


def probe(output: Path, content_sha: str, name: str) -> dict:
    audit, _, _ = load_session(output, content_sha)
    start = readings()
    time.sleep(audit["clock_probes"]["seconds"])
    end = readings()
    record = {"schema": "timing-audit-probe-v1", "id": name, "start": start,
              "end": end, "interval": interval(start, end), "requested_sleep_seconds": audit["clock_probes"]["seconds"]}
    atomic_write_json(output / "probes" / (name + ".json"), record)
    return record


def analyze(output: Path, content_sha: str) -> dict:
    audit, protocol, _ = load_session(output, content_sha)
    criteria = audit["diagnostic_criteria"]
    clock_checks, groups, sample_clock_checks, all_samples, run_ids = [], [], [], [], set()
    session = json.loads((output / "session.json").read_text())
    operation_ids = ["before" + str(i) for i in range(audit["clock_probes"]["before_count"])] + \
                    [job["id"] for job in audit["groups"]] + \
                    ["after" + str(i) for i in range(audit["clock_probes"]["after_count"])]
    for name in operation_ids:
        path = output / "probes" / (name + ".json") if name.startswith(("before", "after")) else \
               output / "groups" / name / "final.json"
        record = json.loads(path.read_text())
        host = json.loads((output / "host_operations" / (name + ".json")).read_text(encoding="utf-8-sig"))
        if host["returncode"] != 0:
            raise ValueError("host operation did not succeed: " + name)
        elapsed = record["interval"]
        clock_checks.append({"id": name, **elapsed, "host_stopwatch_seconds": host["stopwatch_seconds"],
            "host_utc_seconds": host["utc_seconds"],
            "mono_raw_agree": agreement(elapsed["monotonic_seconds"], elapsed["raw_seconds"],
                                        criteria["monotonic_raw_relative_tolerance"],
                                        criteria["monotonic_raw_absolute_allowance_seconds"]),
            "host_raw_agree": agreement(host["stopwatch_seconds"], elapsed["raw_seconds"],
                                        criteria["host_raw_relative_tolerance"],
                                        criteria["host_launch_and_collection_allowance_seconds"]),
            "realtime_raw_agree": agreement(elapsed["realtime_seconds"], elapsed["raw_seconds"],
                                             criteria["realtime_raw_relative_tolerance"],
                                             criteria["realtime_raw_absolute_allowance_seconds"])})
        if not name.startswith(("before", "after")):
            evaluation = record["evaluation"]
            validate_terminal(evaluation, protocol)
            if evaluation["classification"] != "success":
                raise ValueError("incomplete/invalid group: " + name)
            for sample in evaluation["samples"]:
                run_id = sample["run_id"]
                if run_id in run_ids or sample["binary_sha256"] != session["binary_hashes"][sample["config"]["optimization"]] or \
                        sample["reference_sha256"] != session["reference_sha256"]:
                    raise ValueError("reused run ID or execution identity mismatch")
                run_ids.add(run_id)
                directory = output / "groups" / name / "runs" / Path(sample["run_directory"]).name
                saved = json.loads((directory / "result.json").read_text())
                if any(sample.get(key) != value for key, value in saved.items()):
                    raise ValueError("raw result differs from grouped sample")
                for field, filename in (("raw_stdout", "stdout.txt"), ("raw_stderr", "stderr.txt"),
                                        ("raw_resource", "resource.txt")):
                    if (directory / filename).read_text() != sample[field]:
                        raise ValueError("raw stream differs from grouped sample")
                all_samples.append(sample)
                clock = json.loads((output / "groups" / name / "clocks" / (run_id + ".json")).read_text())
                measured = clock["interval"]
                sample_clock_checks.append({"group": name, "run_id": run_id, **measured,
                    "mono_raw_agree": agreement(measured["monotonic_seconds"], measured["raw_seconds"],
                                                criteria["monotonic_raw_relative_tolerance"],
                                                criteria["monotonic_raw_absolute_allowance_seconds"]),
                    "realtime_raw_agree": agreement(measured["realtime_seconds"], measured["raw_seconds"],
                                                     criteria["realtime_raw_relative_tolerance"],
                                                     criteria["realtime_raw_absolute_allowance_seconds"])})
            groups.append({**record["job"], "statistics": evaluation["statistics"],
                           "samples": evaluation["measured_compute_seconds"],
                           "process_wall_seconds": evaluation["process_wall_seconds"],
                           "evaluation_wall_seconds": evaluation["evaluation_wall_seconds"]})
    ranks, gaps = {}, {}
    for round_number in (1, 2):
        ordered = sorted((row for row in groups if row["round"] == round_number),
                         key=lambda row: row["statistics"]["median_seconds"])
        ranks[str(round_number)] = [row["optimization"] for row in ordered]
        gaps[str(round_number)] = [ordered[i + 1]["statistics"]["median_seconds"] /
                                  ordered[i]["statistics"]["median_seconds"] - 1 for i in range(2)]
    drift = {level: next(row for row in groups if row["round"] == 2 and row["optimization"] == level)
                   ["statistics"]["median_seconds"] /
                   next(row for row in groups if row["round"] == 1 and row["optimization"] == level)
                   ["statistics"]["median_seconds"] - 1 for level in ("O1", "O2", "O3")}
    all_clock_checks_pass = all(row["mono_raw_agree"] and row["host_raw_agree"] and row["realtime_raw_agree"]
                                for row in clock_checks) and all(row["mono_raw_agree"] and row["realtime_raw_agree"]
                                                                 for row in sample_clock_checks)
    resources = [point for sample in all_samples for point in
                 [sample["resource_before"], *sample["resource_samples"], sample["resource_after"]]]
    hosts = [host for point in resources for host in point.get("host", {}).get("host_samples", [])]
    peak_rss = [int(match.group(1)) for sample in all_samples
                if (match := re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", sample["raw_resource"]))]
    runtime_resource_warning = not hosts or any(point["mem_available_bytes"] < 2147483648 or
                                                point["swap_total_bytes"] != point["swap_free_bytes"]
                                                for point in resources) or \
                               any(point["available_memory_bytes"] < 2147483648 or point["cpu_percent"] > 20
                                   for point in hosts)
    result = {"schema": "timing-audit-analysis-v1", "diagnostic_only": True, "groups": groups,
              "clock_checks": clock_checks, "all_clock_checks_pass": all_clock_checks_pass,
              "sample_clock_checks": sample_clock_checks, "raw_run_count": len(run_ids),
              "runtime_resource_warning": runtime_resource_warning,
              "resources": {"peak_target_rss_kib": max(peak_rss, default=None),
                            "wsl_minimum_available_bytes": min(point["mem_available_bytes"] for point in resources),
                            "wsl_maximum_swap_used_bytes": max(point["swap_total_bytes"] - point["swap_free_bytes"] for point in resources),
                            "pswpin_start_end": [resources[0]["vmstat"]["pswpin"], resources[-1]["vmstat"]["pswpin"]],
                            "pswpout_start_end": [resources[0]["vmstat"]["pswpout"], resources[-1]["vmstat"]["pswpout"]],
                            "host_minimum_available_bytes": min((point["available_memory_bytes"] for point in hosts), default=None),
                            "host_maximum_cpu_percent": max((point["cpu_percent"] for point in hosts), default=None),
                            "host_maximum_percent_committed": max((point["percent_committed_bytes_in_use"] for point in hosts), default=None),
                            "host_maximum_pages_per_second": max((point["pages_per_second"] for point in hosts), default=None),
                            "host_maximum_page_reads_per_second": max((point["page_reads_per_second"] for point in hosts), default=None),
                            "host_compressed_memory_temperature_throttling": "unknown"},
              "observed_ranks": ranks, "adjacent_relative_gaps": gaps, "cross_round_median_drift": drift,
              "same_observed_ranking": ranks["1"] == ranks["2"],
              "drift_warning": any(abs(value) > criteria["cross_round_median_drift_warning"] for value in drift.values()),
              "cv_warning": any(row["statistics"]["coefficient_of_variation"] > criteria["group_cv_warning"] for row in groups),
              "rank_margin_pass": all(value >= criteria["adjacent_rank_gap_minimum"] for values in gaps.values() for value in values),
              "calibration_applied": False, "fed_to_search": False,
              "limitations": ["Only two rounds; central O3 adjacency", "Resource gates are not stationary-resource certification",
                              "Host QPC and WSL RAW are not an independent physical clock calibration",
                              "No RAW core times were measured; whole-operation intervals cannot calibrate old core samples"]}
    result["robust_ranking_criteria_pass"] = all_clock_checks_pass and not runtime_resource_warning and \
        result["same_observed_ranking"] and not result["drift_warning"] and not result["cv_warning"] and result["rank_margin_pass"]
    atomic_write_json(output / "analysis.json", result)
    return {key: result[key] for key in ("all_clock_checks_pass", "observed_ranks", "cross_round_median_drift", "calibration_applied")}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", choices=("setup", "probe", "group", "analyze"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--content-sha", required=True)
    parser.add_argument("--git-identity", type=Path)
    parser.add_argument("--probe-id")
    parser.add_argument("--group-index", type=int)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.content_sha):
        parser.error("content SHA must contain 40 lowercase hexadecimal characters")
    if args.action == "group" and (args.group_index is None or not 0 <= args.group_index < 6):
        parser.error("group index must be 0..5")
    if args.action == "probe" and args.probe_id not in {kind + str(i) for kind in ("before", "after") for i in range(3)}:
        parser.error("unknown frozen probe ID")
    if args.action == "setup" and args.git_identity is None:
        parser.error("setup requires Git identity")
    with Path("/var/tmp/matrix-autotuner-p3-10245102457.runner.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.action == "setup": result = setup(args.output, args.content_sha, args.git_identity)
        elif args.action == "probe": result = probe(args.output, args.content_sha, args.probe_id)
        elif args.action == "group": result = group(args.output, args.content_sha, args.group_index)
        else: result = analyze(args.output, args.content_sha)
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0 if result.get("status", "success") in ("success", "setup_complete") else 1


if __name__ == "__main__":
    raise SystemExit(main())
