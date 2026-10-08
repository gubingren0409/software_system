"""P3 orchestration. Strategies never receive Grid or another trajectory's results."""
from __future__ import annotations

import json
import math
import subprocess
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .core import (Config, ConfigSpace, Evaluator, TargetAdapter, atomic_write_json,
                   classify_execution, sha256_file, sha256_json, sha256_text, utc_now)
from .measurement import ConfigurationEvaluator, summarize_group
from .search import RandomSearch, RestartGreedySearch, SearchStrategy
from .session import restore_complete_group, source_identity, valid_formal_gate


def strategy_for(space: ConfigSpace, algorithm: str, budget: int, seed: int) -> SearchStrategy:
    kinds = {"random": RandomSearch, "greedy": RestartGreedySearch}
    if algorithm not in kinds:
        raise ValueError("unknown P3 algorithm")
    return kinds[algorithm](space, budget, seed)


def validate_terminal(group: dict[str, Any], protocol: dict[str, Any]) -> None:
    """Restore complete successes; failures retain evidence but can never score."""
    config = Config(**group["config"])
    samples = group["samples"]
    if not samples or any(sample.get("sample_index") != index or
                          sample.get("attempt_id") != group["attempt_id"] or
                          sample.get("config") != group["config"] or
                          sample.get("role") != ("warmup" if index == 0 else "measurement") or
                          sample.get("context", {}).get("protocol_hash") != sha256_json(protocol)
                          for index, sample in enumerate(samples)):
        raise ValueError("invalid terminal sample sequence or identity")
    aggregate = summarize_group(config, group["attempt_id"], samples,
                                protocol["measurement"]["measured_runs"], group["evaluation_wall_seconds"])
    for field in ("classification", "score_seconds", "statistics", "measured_compute_seconds",
                  "process_wall_seconds", "compute_total_seconds", "validation_total_seconds"):
        if group[field] != aggregate[field]:
            raise ValueError(f"terminal aggregate differs: {field}")
    for field in ("configuration_start_gate_seconds", "configuration_total_wall_seconds"):
        if field in group and (type(group[field]) not in (int, float) or
                               not math.isfinite(group[field]) or group[field] < 0):
            raise ValueError("invalid configuration cost")
    if group["classification"] == "success":
        restore_complete_group(group, protocol)
        return
    if group["score_seconds"] is not None or samples[-1]["classification"] == "success":
        raise ValueError("failed terminal observation has a score or no actual failure")
    expected = {"n": protocol["target_matrix_n"], "block_size": config.block_size,
                "seed": protocol["matrix_input_seed"], "input": protocol["input_pattern"],
                "input_generator": protocol["input_generator"],
                "abs_tol": protocol["abs_tolerance"], "rel_tol": protocol["rel_tolerance"]}
    for sample in samples:
        if sample["classification"] in ("compile_failure", "reference_failure", "resource_rejected"):
            if sample.get("score_seconds") is not None:
                raise ValueError("pre-execution failure has a score")
            continue
        classification, _, _ = classify_execution(sample.get("returncode", -1),
                                                  sample.get("timed_out", True),
                                                  sample.get("raw_stdout", ""), expected=expected)
        if classification != sample["classification"]:
            raise ValueError("failed observation's raw contract differs")


def replay_trajectory(space: ConfigSpace, job: dict[str, Any], budget: int,
                      observations: list[dict[str, Any]], protocol: dict[str, Any]) -> SearchStrategy:
    strategy = strategy_for(space, job["algorithm"], budget, job["seed"])
    for group in observations:
        validate_terminal(group, protocol)
        config = strategy.ask()
        if config is None or asdict(config) != group["config"]:
            raise ValueError("saved trajectory differs from own seeded observations")
        strategy.tell(config, group)
    return strategy


def prefix_results(strategy: SearchStrategy, observations: list[dict[str, Any]],
                   budgets: list[int]) -> list[dict[str, Any]]:
    results = []
    for budget in budgets:
        if len(observations) < budget:
            continue
        valid = [group for group in observations[:budget] if group["classification"] == "success"]
        best = min(valid, key=lambda group: (group["score_seconds"],
                    strategy.configs.index(Config(**group["config"])))) if valid else None
        results.append({"budget": budget, "valid_count": len(valid),
                        "best_config": best["config"] if best else None,
                        "median_seconds": best["score_seconds"] if best else None,
                        "configuration_evaluation_seconds": sum(group["evaluation_wall_seconds"]
                                                                  for group in observations[:budget]),
                        "configuration_total_wall_seconds": sum(group.get("configuration_total_wall_seconds",
                                                                    group["evaluation_wall_seconds"])
                                                                 for group in observations[:budget]),
                        "configuration_start_gate_seconds": sum(group.get("configuration_start_gate_seconds", 0)
                                                                  for group in observations[:budget]),
                        "core_compute_seconds": sum(group["compute_total_seconds"]
                                                    for group in observations[:budget])})
    return results


def audit_trajectory(destination: Path, state: dict[str, Any], space: ConfigSpace,
                     budget: int, protocol: dict[str, Any]) -> dict[str, Any]:
    strategy = replay_trajectory(space, state["job"], budget, state["observations"], protocol)
    sample_path = destination / "samples.jsonl"
    records = [json.loads(line) for line in sample_path.read_text().splitlines() if line] \
        if sample_path.exists() else []
    by_id = {record["run_id"]: record for record in records}
    if len(by_id) != len(records):
        raise ValueError("duplicate execution ID within trajectory")
    for record in records:
        if record["context"]["force_remeasure"] is not True:
            raise ValueError("trajectory sample was not force-remeasured")
        directory = destination / "runs" / Path(record["run_directory"]).name
        saved = json.loads((directory / "result.json").read_text())
        if any(record.get(key) != value for key, value in saved.items()):
            raise ValueError("run result differs from trajectory JSONL")
        for field, filename in (("raw_stdout", "stdout.txt"), ("raw_stderr", "stderr.txt")):
            if (directory / filename).read_text() != record[field]:
                raise ValueError("raw output differs from JSONL")
            if record.get(field.removeprefix("raw_") + "_sha256") is not None and \
                    sha256_text(record[field]) != record[field.removeprefix("raw_") + "_sha256"]:
                raise ValueError("raw output checksum differs")
        if record.get("raw_resource") and (directory / "resource.txt").read_text() != record["raw_resource"]:
            raise ValueError("raw resource output differs from JSONL")
    groups = [*state["observations"]]
    candidates = [row["best_config"] for row in prefix_results(strategy, state["observations"], [4, 8, 12])
                  if row["best_config"] is not None]
    retests = state.get("independent_retests", [])
    unique_retests = set()
    for retest in retests:
        validate_terminal(retest, protocol)
        groups.append(retest)
        key = Config(**retest["config"])
        if retest["config"] not in candidates or key in unique_retests:
            raise ValueError("retest does not uniquely match an own prefix candidate")
        unique_retests.add(key)
    if state["status"] == "complete" and ({Config(**config) for config in candidates} != unique_retests or
            any(group["classification"] != "success" for group in retests)):
        raise ValueError("complete trajectory lacks successful independent prefix retests")
    scored_ids = set()
    for group in groups:
        for sample in group["samples"]:
            if sample != by_id.get(sample["run_id"]):
                raise ValueError("checkpoint differs from raw JSONL")
            if sample["run_id"] in scored_ids:
                raise ValueError("execution reused across groups")
            scored_ids.add(sample["run_id"])
    prefixes = prefix_results(strategy, state["observations"], [4, 8, 12])
    if state.get("prefixes", prefixes) != prefixes:
        raise ValueError("saved prefix aggregates differ")
    return {"status": "PASS", "job": state["job"], "unique_count": len(strategy.observations),
            "prefixes": prefixes, "raw_execution_count": len(records),
            "nonterminal_raw_execution_count": len(set(by_id) - scored_ids),
            "failed_terminal_group_count": sum(group["classification"] != "success" for group in groups),
            "independent_retest_group_count": len(retests),
            "incomplete_run_directories": [str(path.relative_to(destination))
                for path in (destination / "runs").glob("*") if not (path / "result.json").exists()],
            "process_wall_seconds": sum(record.get("process_wall_seconds", 0) for record in records),
            "configuration_evaluation_seconds": sum(group["evaluation_wall_seconds"] for group in groups)}


class CampaignPaused(Exception):
    pass


def run_campaign(root: Path, output: Path, content_sha: str, git_identity_path: Path,
                 *, resume: bool = False, trajectory_limit: int = 2,
                 diagnostic_size: int | None = None, cache_root: Path | None = None) -> int:
    import fcntl
    lock_path = Path("/var/tmp/matrix-autotuner-p3-10245102457.runner.lock")
    with lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return _run_campaign(root.resolve(), output.resolve(), content_sha, git_identity_path,
                             resume, trajectory_limit, diagnostic_size, cache_root)


def _run_campaign(root: Path, output: Path, content_sha: str, git_identity_path: Path,
                  resume: bool, trajectory_limit: int, diagnostic_size: int | None,
                  cache_root: Path | None) -> int:
    campaign = json.loads((root / "configs/p3_campaign_protocol.json").read_text())
    protocol = json.loads((root / "configs/measurement_protocol.json").read_text())
    search = json.loads((root / "configs/search_protocol.json").read_text())
    if sha256_json(protocol) != campaign["measurement_protocol_hash"] or \
            sha256_json(search) != campaign["search_protocol_hash"]:
        raise ValueError("P2 frozen measurement/search protocol changed")
    if not 1 <= trajectory_limit <= len(campaign["schedule"]):
        raise ValueError("trajectory limit must be between 1 and schedule length")
    for relative, expected in campaign["unchanged_source_sha256"].items():
        if sha256_file(root / relative) != expected:
            raise ValueError(f"P2 source changed: {relative}")
    if diagnostic_size is not None:
        if diagnostic_size != 130 or cache_root is None:
            raise ValueError("diagnostic mode requires n=130 and an explicit isolated cache")
        protocol["target_matrix_n"] = diagnostic_size
        protocol["resource_gate"]["formal_wsl_minimum_available_bytes"] = 0
    elif cache_root is not None or (root / ".git").exists() or list(root.rglob("__pycache__")):
        raise ValueError("formal mode requires committed archive, no pycache and fixed WSL cache")
    identity = json.loads(git_identity_path.read_text())
    if identity["content_sha"] != content_sha:
        raise ValueError("Git identity belongs to a different commit")
    files = source_identity(root, identity["files"])
    space = ConfigSpace.load(root / "configs/config_space.json")
    budget = campaign["unique_budget_per_trajectory"]
    if budget != max(search["budgets"]) or campaign["reported_prefix_budgets"] != search["budgets"]:
        raise ValueError("P3 prefix budgets differ from frozen search protocol")
    expected_jobs = {(algorithm, seed) for algorithm in ("random", "greedy") for seed in search["search_seeds"]}
    actual_jobs = [(job["algorithm"], job["seed"]) for job in campaign["schedule"]]
    if len(actual_jobs) != len(expected_jobs) or set(actual_jobs) != expected_jobs:
        raise ValueError("campaign schedule does not contain each algorithm/seed exactly once")
    output.mkdir(parents=True, exist_ok=True)
    checkpoint_path = output / "checkpoint.json"
    if not resume and checkpoint_path.exists():
        raise ValueError("campaign exists; use --resume or a new directory")
    target_data = json.loads((root / "configs/target.json").read_text())
    target_data.update(candidate_source=str(root / "code/working/matrix_multiplication.c"),
                       reference_source=str(root / "code/working/reference_generator.c"),
                       shared_sources=[str(root / "code/working/matrix_input.h")],
                       cache_root=str(cache_root.resolve()) if cache_root else
                                  "/var/tmp/matrix-autotuner-p3-10245102457/cache")
    if target_data["abs_tolerance"] != protocol["abs_tolerance"] or \
            target_data["rel_tolerance"] != protocol["rel_tolerance"]:
        raise ValueError("target/protocol tolerances differ")
    atomic_write_json(output / "effective_target.json", target_data)
    target = TargetAdapter.load(output / "effective_target.json", evidence_root=output / "setup")
    if sha256_file(target.compiler) != campaign["compiler_sha256"]:
        raise ValueError("compiler differs from P2")
    preflight = {"content_commit": content_sha, "files": files,
                 "measurement_protocol_hash": sha256_json(protocol),
                 "campaign_protocol_hash": sha256_json(campaign), "search_protocol_hash": sha256_json(search),
                 "effective_target_hash": sha256_json(target_data),
                 "compiler_sha256": sha256_file(target.compiler), "compiler_version": target._compiler_version,
                 "diagnostic_only": diagnostic_size is not None}
    checkpoint = json.loads(checkpoint_path.read_text()) if resume else {
        "session_id": uuid.uuid4().hex, "status": "created", "completed_trajectories": [],
        "active_total_seconds": 0.0, "wait_seconds": 0.0, "created_at": utc_now()}
    if resume and checkpoint.get("preflight_identity") != preflight:
        raise ValueError("campaign resume preflight identity changed")
    if resume and (output / "PAUSE_REQUEST").exists():
        request = output / "PAUSE_REQUEST"
        atomic_write_json(output / "pause_requests" / f"{uuid.uuid4().hex}.json",
                          {"cleared_at": utc_now(), "request": request.read_text(),
                           "reason": "explicit CLI --resume"})
        request.unlink()
    checkpoint["preflight_identity"] = preflight
    started, prior_total = time.monotonic(), checkpoint["active_total_seconds"]

    def save() -> None:
        checkpoint["active_total_seconds"] = prior_total + time.monotonic() - started
        checkpoint["updated_at"] = utc_now()
        atomic_write_json(checkpoint_path, checkpoint)

    host_command = None
    if diagnostic_size is None:
        windows_script = subprocess.run(["wslpath", "-w", str(root / "scripts/check_p2_resources.ps1")],
                                        capture_output=True, text=True, check=True).stdout.strip()
        host_command = ["/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe",
                        "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", windows_script]

    def gate(config: Config, purpose: str) -> bool:
        gate_started = time.monotonic()
        for retry in range(16):
            if (output / "PAUSE_REQUEST").exists():
                checkpoint["status"] = "user_paused"
                checkpoint["wait_seconds"] += time.monotonic() - gate_started
                save()
                return False
            if host_command is None:
                return True
            command = [*host_command, "-Mode", "Formal"]
            try:
                result = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
                parsed = json.loads(result.stdout.lstrip("\ufeff"))
            except subprocess.TimeoutExpired:
                result = subprocess.CompletedProcess(command, 124, "", "resource collection timeout")
                parsed = {}
            except ValueError:
                parsed = {}
            atomic_write_json(output / "gates" / f"{uuid.uuid4().hex}.json",
                              {"captured_at": utc_now(), "command": command, "stdout": result.stdout,
                               "stderr": result.stderr, "returncode": result.returncode, "parsed": parsed,
                               "config": asdict(config), "purpose": purpose})
            if result.returncode == 0 and valid_formal_gate(parsed, protocol):
                checkpoint["wait_seconds"] += time.monotonic() - gate_started
                save()
                return True
            checkpoint["status"] = "resource_paused"
            save()
            print(json.dumps({"event": "resource_paused", "purpose": purpose, "gate": parsed}), flush=True)
            if retry < 15:
                time.sleep(30)
        checkpoint["wait_seconds"] += time.monotonic() - gate_started
        save()
        return False

    save()
    if not gate(space.all()[0], "setup"):
        return 2
    setup_started = time.monotonic()
    binaries = {}
    build_seconds = 0.0
    for optimization in space.optimization_levels:
        build_started = time.monotonic()
        artifact = target.build_candidate(protocol["target_matrix_n"], optimization)
        build_seconds += time.monotonic() - build_started
        binaries[optimization] = artifact.binary_sha256
        atomic_write_json(output / "manifests" / f"candidate_{optimization}.json",
                          json.loads((artifact.binary.parent / "manifest.json").read_text()))
    reference_started = time.monotonic()
    reference = target.get_reference(protocol["target_matrix_n"], protocol["matrix_input_seed"],
                                     protocol["input_pattern"], 600)
    if diagnostic_size is None and reference.data_sha256 != campaign["expected_reference_data_sha256"]:
        raise ValueError("P3 reference data differs from P2 input/reference")
    reference_generator = target.build_reference_generator(protocol["target_matrix_n"])
    atomic_write_json(output / "manifests/reference_build.json",
                      json.loads((reference_generator.binary.parent / "manifest.json").read_text()))
    atomic_write_json(output / "manifests/reference.json", reference.metadata)
    reference_seconds = time.monotonic() - reference_started
    fingerprint = {**preflight, "binary_hashes": binaries, "reference_key": reference.reference_key,
                   "reference_sha256": reference.data_sha256}
    if resume and "fingerprint" in checkpoint and checkpoint["fingerprint"] != fingerprint:
        raise ValueError("campaign resume binaries/reference identity changed")
    if "fingerprint" not in checkpoint:
        checkpoint.update(fingerprint=fingerprint, setup_seconds=time.monotonic() - setup_started,
                          candidate_build_setup_seconds=build_seconds, reference_setup_seconds=reference_seconds,
                          resume_setup_records=[])
        atomic_write_json(output / "session.json", {"created_at": checkpoint["created_at"],
                                                   "fingerprint": fingerprint, "schedule": campaign["schedule"]})
        atomic_write_json(output / "protocol.json", protocol)
        atomic_write_json(output / "campaign_protocol.json", campaign)
        atomic_write_json(output / "search_protocol.json", search)
    else:
        checkpoint["resume_setup_records"].append({"captured_at": utc_now(),
            "setup_seconds": time.monotonic() - setup_started,
            "candidate_build_lookup_seconds": build_seconds, "reference_lookup_seconds": reference_seconds})
    save()
    for index, job in enumerate(campaign["schedule"][:trajectory_limit]):
        name = f"{index:02d}_{job['algorithm']}_{job['seed']}"
        destination = output / "trajectories" / name
        destination.mkdir(parents=True, exist_ok=True)
        path = destination / "checkpoint.json"
        completed = checkpoint["completed_trajectories"]
        if index < len(completed) and (not path.exists() or
                sha256_file(path) != completed[index]["checkpoint_sha256"]):
            raise ValueError("completed trajectory checkpoint is missing or changed")
        state = json.loads(path.read_text()) if path.exists() else {
            "job": job, "fingerprint_hash": sha256_json(fingerprint), "observations": [],
            "active": None, "abandoned_attempts": [], "status": "created", "independent_retests": []}
        if state["job"] != job or state["fingerprint_hash"] != sha256_json(fingerprint):
            raise ValueError("trajectory identity changed")
        strategy = replay_trajectory(space, job, budget, state["observations"], protocol)
        audit_trajectory(destination, state, space, budget, protocol)
        if index < len(completed):
            if state["status"] != "complete" or len(strategy.observations) != budget:
                raise ValueError("completed trajectory is not actually complete")
            continue
        if state["active"]:
            state["abandoned_attempts"].append({**state["active"], "reason": "restart interrupted full group"})
            state["active"] = None

        def save_trajectory() -> None:
            state["updated_at"] = utc_now()
            atomic_write_json(path, state)
            checkpoint["active_trajectory"] = name
            save()

        if any(group["classification"] != "success" for group in state["independent_retests"]):
            state["status"] = checkpoint["status"] = "retest_failure"
            save_trajectory()
            return 3

        def sampled(sample: dict[str, Any]) -> None:
            state["active"]["sample_count"] = sample["sample_index"] + 1
            save_trajectory()
            print(json.dumps({"event": "sample", "trajectory": name, "config": sample["config"],
                              "index": sample["sample_index"], "classification": sample["classification"],
                              "compute_seconds": sample.get("score_seconds")}), flush=True)
            if (output / "PAUSE_REQUEST").exists():
                state["status"] = checkpoint["status"] = "user_paused"
                save_trajectory()
                raise CampaignPaused()

        executor = Evaluator(TargetAdapter.load(output / "effective_target.json", evidence_root=destination),
                             [*host_command, "-Mode", "Snapshot"] if host_command else None)
        measure = ConfigurationEvaluator(executor, protocol, sha256_json(protocol), destination, sampled)
        save_trajectory()
        try:
            while (config := strategy.ask()) is not None:
                configuration_started = time.monotonic()
                prior_wait = checkpoint["wait_seconds"]
                if not gate(config, f"{name}/search"):
                    return 2
                attempt = uuid.uuid4().hex
                state.update(status="running", active={"config": asdict(config), "attempt_id": attempt,
                                                       "purpose": "search", "sample_count": 0})
                checkpoint["status"] = "running"
                save_trajectory()
                group = measure.evaluate(config, attempt_id=attempt, purpose="search")
                group["configuration_start_gate_seconds"] = checkpoint["wait_seconds"] - prior_wait
                group["configuration_total_wall_seconds"] = time.monotonic() - configuration_started
                atomic_write_json(destination / "configurations" / f"search_{attempt}.json", group)
                validate_terminal(group, protocol)
                state["observations"].append(group)
                state["active"] = None
                strategy.tell(config, group)
                state["prefixes"] = prefix_results(strategy, state["observations"], search["budgets"])
                save_trajectory()
                print(json.dumps({"event": "configuration_complete", "trajectory": name,
                                  "unique_count": len(strategy.observations), "config": asdict(config),
                                  "classification": group["classification"], "median_seconds": group["score_seconds"]}),
                      flush=True)
            best = strategy.best()
            candidates = []
            for prefix in state["prefixes"]:
                if prefix["best_config"] is not None and Config(**prefix["best_config"]) not in candidates:
                    candidates.append(Config(**prefix["best_config"]))
            for candidate in candidates:
                if any(group["config"] == asdict(candidate) for group in state["independent_retests"]):
                    continue
                retest_started = time.monotonic()
                prior_wait = checkpoint["wait_seconds"]
                if not gate(candidate, f"{name}/independent_retest"):
                    return 2
                attempt = uuid.uuid4().hex
                state["active"] = {"config": asdict(candidate), "attempt_id": attempt, "purpose": "retest"}
                checkpoint["status"] = "retesting"
                save_trajectory()
                retest = measure.evaluate(candidate, attempt_id=attempt, purpose="retest")
                retest["configuration_start_gate_seconds"] = checkpoint["wait_seconds"] - prior_wait
                retest["configuration_total_wall_seconds"] = time.monotonic() - retest_started
                atomic_write_json(destination / "configurations" / f"retest_{attempt}.json", retest)
                validate_terminal(retest, protocol)
                state["independent_retests"].append(retest)
                state["active"] = None
                atomic_write_json(destination / "independent_retests.json", state["independent_retests"])
                if retest["classification"] != "success":
                    state["status"] = checkpoint["status"] = "retest_failure"
                    save_trajectory()
                    return 3
            for retest in state["independent_retests"]:
                validate_terminal(retest, protocol)
                if retest["classification"] != "success":
                    state["status"] = checkpoint["status"] = "retest_failure"
                    save_trajectory()
                    return 3
            state["status"] = "complete"
            state["best_config"] = asdict(best) if best else None
            state["best_median_seconds"] = strategy.score(best) if best else None
            save_trajectory()
            summary = {"name": name, "job": job, "unique_count": len(strategy.observations),
                       "valid_count": sum(math.isfinite(strategy.score(config)) for config in strategy.observations),
                       "best_config": state["best_config"], "best_median_seconds": state["best_median_seconds"],
                       "prefixes": state["prefixes"], "checkpoint_sha256": sha256_file(path)}
            summaries = checkpoint["completed_trajectories"]
            if index < len(summaries):
                if summaries[index]["name"] != name:
                    raise ValueError("completed trajectory schedule differs")
                summaries[index] = summary
            else:
                summaries.append(summary)
            save()
            print(json.dumps({"event": "trajectory_complete", **summary}), flush=True)
        except CampaignPaused:
            return 2
    checkpoint["active_trajectory"] = None
    checkpoint["status"] = "complete" if len(checkpoint["completed_trajectories"]) == len(campaign["schedule"]) \
                           else "batch_complete"
    save()
    atomic_write_json(output / "summary.json", {key: checkpoint[key] for key in
                      ("status", "completed_trajectories", "active_total_seconds", "wait_seconds", "setup_seconds")})
    print(json.dumps({"event": checkpoint["status"], "completed_trajectories":
                      len(checkpoint["completed_trajectories"]), "content_commit": content_sha}), flush=True)
    return 0
