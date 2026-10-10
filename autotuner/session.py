from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import subprocess
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .core import (Config, ConfigSpace, Evaluator, TargetAdapter, atomic_write_json,
                   atomic_write_text, classify_execution, sha256_file, sha256_json, utc_now)
from .measurement import ConfigurationEvaluator, summarize_group
from .search import GridSearch
from .timing import RAW_RESULT_SCHEMA, measurement_timing, require_formal_activation


def source_identity(root: Path, git_identity: dict[str, str]) -> dict[str, Any]:
    result = {}
    for relative, blob in git_identity.items():
        data = (root / relative).read_bytes()
        actual_blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        git_bytes = data
        if actual_blob != blob:
            # Git archive applies eol attributes/core.autocrlf on Windows. Accept only
            # the verified newline conversion, and preserve both byte identities.
            git_bytes = data.replace(b"\r\n", b"\n")
            normalized_blob = hashlib.sha1(b"blob " + str(len(git_bytes)).encode() + b"\0" + git_bytes).hexdigest()
            if relative.startswith("code/original/") or normalized_blob != blob:
                raise ValueError(f"executed bytes differ from content commit: {relative}")
        result[relative] = {"git_blob_sha1": blob, "executed_sha256": hashlib.sha256(data).hexdigest(),
                            "git_content_sha256": hashlib.sha256(git_bytes).hexdigest(),
                            "byte_count": len(data), "crlf_count": data.count(b"\r\n"),
                            "lf_count": data.count(b"\n")}
    return result


def valid_formal_gate(record: dict[str, Any], protocol: dict[str, Any]) -> bool:
    if "policy_hash" in protocol["resource_gate"]:
        from .resources import valid_gate
        return valid_gate(record, protocol, "Formal")
    limits = protocol["resource_gate"]
    requirements = {
        "host_minimum_available_bytes": limits["formal_host_minimum_available_bytes"],
        "wsl_available_bytes": limits["formal_wsl_minimum_available_bytes"],
        "wsl_root_free_bytes": limits["formal_wsl_root_minimum_free_bytes"],
    }
    return record.get("schema") == "p2-resource-gate-v2" and record.get("mode") == "Formal" and record.get("formal_gate") == "PASS" and all(
        type(record.get(field)) in (int, float) and record[field] >= minimum
        for field, minimum in requirements.items()
    ) and type(record.get("host_cpu_average_percent")) in (int, float) and 0 <= record["host_cpu_average_percent"] <= limits["formal_host_cpu_average_maximum_percent"] and type(record.get("host_cpu_maximum_percent")) in (int, float) and 0 <= record["host_cpu_maximum_percent"] <= limits["formal_host_cpu_single_sample_maximum_percent"]


def restore_complete_group(group: dict[str, Any], protocol: dict[str, Any]) -> dict[str, Any]:
    config = Config(**group["config"])
    samples = group["samples"]
    expected = {"n": protocol["target_matrix_n"], "block_size": config.block_size,
                "seed": protocol["matrix_input_seed"], "input": protocol["input_pattern"],
                "input_generator": protocol["input_generator"],
                "abs_tol": protocol["abs_tolerance"], "rel_tol": protocol["rel_tolerance"]}
    timing = measurement_timing(protocol, Path(__file__).resolve().parents[1])
    if timing is not None:
        expected.update(primary_clock=timing["primary_clock"], timing_protocol_version=timing["version"])
    for index, sample in enumerate(samples):
        classification, parsed, _ = classify_execution(sample.get("returncode", -1), sample.get("timed_out", True),
            sample.get("raw_stdout", ""), expected_schema=RAW_RESULT_SCHEMA if timing else "matrix-multiplication-result-v1", expected=expected)
        if classification != "success" or sample.get("sample_index") != index or sample.get("context", {}).get("protocol_hash") != sha256_json(protocol) or parsed != sample.get("target_result") or parsed.get("elapsed_seconds") != sample.get("score_seconds"):
            raise ValueError("checkpoint contains invalid/mismatched raw samples")
    restored = summarize_group(config, group["attempt_id"], samples,
                               protocol["measurement"]["measured_runs"], group["evaluation_wall_seconds"])
    if restored["classification"] != "success" or restored["score_seconds"] != group["score_seconds"]:
        raise ValueError("checkpoint group is incomplete or aggregate differs from raw samples")
    return group


def run_grid(root: Path, output: Path, content_sha: str, git_identity_path: Path,
             *, resume: bool = False) -> int:
    protocol = json.loads((root / "configs/measurement_protocol.json").read_text())
    require_formal_activation(protocol, root)
    output.mkdir(parents=True, exist_ok=True)
    space = ConfigSpace.load(root / "configs/config_space.json")
    protocol_hash = sha256_json(protocol)
    identity = json.loads(git_identity_path.read_text())
    if identity["content_sha"] != content_sha:
        raise ValueError("Git identity belongs to a different commit")
    files = source_identity(root, identity["files"])
    target_config = json.loads((root / "configs/target.json").read_text())
    target_config.update(candidate_source=str(root / "code/working/matrix_multiplication.c"),
                         reference_source=str(root / "code/working/reference_generator.c"),
                         shared_sources=[str(root / "code/working/matrix_input.h")],
                         cache_root="/var/tmp/matrix-autotuner-p2-10245102457/cache")
    if target_config["abs_tolerance"] != protocol["abs_tolerance"] or target_config["rel_tolerance"] != protocol["rel_tolerance"]:
        raise ValueError("target/protocol tolerances differ")
    atomic_write_json(output / "effective_target.json", target_config)
    target = TargetAdapter.load(output / "effective_target.json", evidence_root=output)
    powershell = "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
    script_windows = subprocess.run(["wslpath", "-w", str(root / "scripts/check_p2_resources.ps1")],
                                    text=True, capture_output=True, check=True).stdout.strip()
    host_command = [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script_windows]
    checkpoint_path = output / "checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_text()) if resume else {
        "session_id": uuid.uuid4().hex, "status": "created", "completed": [], "active": None,
        "abandoned_attempts": [], "wait_seconds": 0.0, "active_total_seconds": 0.0,
    }
    preflight_identity = {"content_commit": content_sha, "files": files,
                          "protocol_hash": protocol_hash,
                          "target_config_hash": sha256_json(target_config),
                          "compiler_version": target._compiler_version,
                          "compiler_sha256": sha256_file(target.compiler)}
    if resume and checkpoint.get("preflight_identity") != preflight_identity:
        raise ValueError("resume preflight identity differs from checkpoint")
    checkpoint["preflight_identity"] = preflight_identity
    if not resume and checkpoint_path.exists():
        raise ValueError("session exists; use --resume or a new directory")
    started = time.monotonic()
    prior_total = checkpoint["active_total_seconds"]

    def save() -> None:
        checkpoint["active_total_seconds"] = prior_total + time.monotonic() - started
        checkpoint["updated_at"] = utc_now()
        atomic_write_json(checkpoint_path, checkpoint)

    def gate(config: Config, purpose: str) -> bool:
        if "policy_hash" in protocol["resource_gate"]:
            from .resources import wait_formal
            def recorded(record):
                record.update(config=asdict(config), purpose=purpose)
                atomic_write_json(output / "gates" / f"{uuid.uuid4().hex}.json", record)
                if not record["admission_pass"]:
                    checkpoint["status"] = "resource_paused"
                    save()
                    print(json.dumps({"event": "resource_paused", **record}), flush=True)
            passed, elapsed = wait_formal([*host_command, "-Mode", "Formal", "-RuntimeRoot", str(root)], protocol, recorded)
            checkpoint["wait_seconds"] += elapsed
            save()
            return passed
        gate_started = time.monotonic()
        for retry in range(16):
            try:
                completed = subprocess.run([*host_command, "-Mode", "Formal"], text=True,
                                           capture_output=True, check=False, timeout=60)
            except subprocess.TimeoutExpired:
                completed = subprocess.CompletedProcess([*host_command, "-Mode", "Formal"],
                                                         124, "", "resource collection timeout")
            try:
                parsed = json.loads(completed.stdout.lstrip("\ufeff"))
            except ValueError:
                parsed = {"formal_gate": "ERROR"}
            record = {"command": [*host_command, "-Mode", "Formal"],
                      "returncode": completed.returncode, "stdout": completed.stdout,
                      "stderr": completed.stderr, "parsed": parsed,
                      "config": asdict(config), "purpose": purpose, "captured_at": utc_now()}
            atomic_write_json(output / "gates" / f"{uuid.uuid4().hex}.json", record)
            if valid_formal_gate(parsed, protocol):
                checkpoint["wait_seconds"] += time.monotonic() - gate_started
                save()
                return True
            checkpoint["status"] = "resource_paused"
            save()
            print(json.dumps({"event": "resource_paused", "config": asdict(config),
                              "gate": parsed, "checkpoint": str(checkpoint_path)}), flush=True)
            if retry < 15:
                time.sleep(30)
        checkpoint["wait_seconds"] += time.monotonic() - gate_started
        save()
        return False

    # Setup also follows the formal gate before allocating a default-size reference.
    if not gate(space.all()[len(checkpoint["completed"]) % 20], "setup"):
        return 2
    setup_started = time.monotonic()
    binaries = {}
    build_seconds = 0.0
    for optimization in space.optimization_levels:
        build_started = time.monotonic()
        artifact = target.build_candidate(protocol["target_matrix_n"], optimization)
        build_seconds += time.monotonic() - build_started
        metadata_path = artifact.binary.parent / "manifest.json"
        metadata = json.loads(metadata_path.read_text())
        atomic_write_json(output / "manifests" / f"candidate_{optimization}.json", metadata)
        binaries[optimization] = artifact.binary_sha256
    reference_started = time.monotonic()
    reference = target.get_reference(protocol["target_matrix_n"], protocol["matrix_input_seed"],
                                     protocol["input_pattern"], 600)
    reference_setup_seconds = time.monotonic() - reference_started
    reference_metadata = reference.metadata
    reference_generator = target.build_reference_generator(protocol["target_matrix_n"])
    atomic_write_json(output / "manifests/reference_build.json",
                      json.loads((reference_generator.binary.parent / "manifest.json").read_text()))
    atomic_write_json(output / "manifests/reference.json", reference_metadata)
    fingerprint = {"content_commit": content_sha, "files": files,
                   "protocol_hash": protocol_hash, "target_config_hash": sha256_json(target_config),
                   "compiler_path": str(target.compiler), "compiler_version": target._compiler_version,
                   "compiler_sha256": sha256_file(target.compiler), "binary_hashes": binaries,
                   "reference_key": reference.reference_key, "reference_sha256": reference.data_sha256,
                   "search_protocol_hash": sha256_json(json.loads((root / "configs/search_protocol.json").read_text()))}
    if resume and "fingerprint" in checkpoint:
        if checkpoint["fingerprint"] != fingerprint:
            raise ValueError("resume identity differs: commit/source/compiler/input/reference/protocol")
        for group in checkpoint["completed"]:
            restore_complete_group(group, protocol)
        if checkpoint["active"]:
            abandoned = checkpoint["active"]
            abandoned["reason"] = "interrupted configuration: restart full warmup plus five samples"
            checkpoint["abandoned_attempts"].append(abandoned)
            atomic_write_json(output / "abandoned" / f"{abandoned['attempt_id']}.json", abandoned)
            checkpoint["active"] = None
    else:
        checkpoint["fingerprint"] = fingerprint
        checkpoint["setup_seconds"] = time.monotonic() - setup_started
        checkpoint["build_setup_seconds"] = build_seconds
        checkpoint["reference_setup_seconds"] = reference_setup_seconds
        atomic_write_json(output / "session.json", {"created_at": utc_now(), "fingerprint": fingerprint,
                                                   "canonical_configurations": [asdict(config) for config in space.all()]})
        atomic_write_json(output / "protocol.json", protocol)
    save()
    if checkpoint.get("independent_retest"):
        restore_complete_group(checkpoint["independent_retest"], protocol)
    strategy = GridSearch(space)
    for group in checkpoint["completed"]:
        config = strategy.ask()
        if asdict(config) != group["config"]:
            raise ValueError("checkpoint configurations are not in canonical Grid order")
        strategy.tell(config, group)

    def sampled(sample: dict[str, Any]) -> None:
        checkpoint["active"]["sample_count"] = sample["sample_index"] + 1
        save()
        print(json.dumps({"event": "sample", "config": sample["config"], "role": sample["role"],
                          "index": sample["sample_index"], "compute_seconds": sample["score_seconds"],
                          "classification": sample["classification"]}), flush=True)

    measure = ConfigurationEvaluator(Evaluator(target, [*host_command, "-Mode", "Snapshot"]),
                                     protocol, protocol_hash, output, sampled)
    while (config := strategy.ask()) is not None:
        if not gate(config, "grid"):
            return 2
        attempt_id = uuid.uuid4().hex
        checkpoint.update(status="running", active={"config": asdict(config), "attempt_id": attempt_id})
        save()
        result = measure.evaluate(config, attempt_id=attempt_id, purpose="grid")
        if result["classification"] != "success":
            checkpoint["status"] = "execution_failure"
            save()
            return 3
        checkpoint["completed"].append(result)
        checkpoint["active"] = None
        strategy.tell(config, result)
        save()
        export_grid(output, checkpoint["completed"])
        average = sum(group["evaluation_wall_seconds"] for group in checkpoint["completed"]) / len(checkpoint["completed"])
        print(json.dumps({"event": "configuration_complete", "completed": len(checkpoint["completed"]),
                          "config": asdict(config), "median_seconds": result["score_seconds"],
                          "estimated_remaining_seconds": average * (20 - len(checkpoint["completed"]))}), flush=True)
    best = strategy.best()
    if best is None:
        raise ValueError("Grid has no valid configuration")
    if not checkpoint.get("independent_retest"):
        if not gate(best, "independent_retest"):
            return 2
        attempt_id = uuid.uuid4().hex
        checkpoint["active"] = {"config": asdict(best), "attempt_id": attempt_id, "purpose": "retest"}
        save()
        retest = measure.evaluate(best, attempt_id=attempt_id, purpose="retest")
        if retest["classification"] != "success":
            checkpoint["status"] = "retest_failure"
            save()
            return 3
        checkpoint["independent_retest"] = retest
        checkpoint["active"] = None
        atomic_write_json(output / "independent_retest.json", retest)
    checkpoint["status"] = "complete"
    save()
    export_grid(output, checkpoint["completed"])
    summary = {"status": "complete", "content_commit": content_sha,
               "completed_count": len(checkpoint["completed"]), "valid_count": len(checkpoint["completed"]),
               "lowest_median_config": asdict(best), "grid_median_seconds": strategy.score(best),
               "retest_median_seconds": checkpoint["independent_retest"]["score_seconds"],
               "active_total_seconds": checkpoint["active_total_seconds"],
               "resource_gate_and_wait_seconds": checkpoint["wait_seconds"],
               "setup_seconds": checkpoint["setup_seconds"],
               "build_setup_seconds": checkpoint["build_setup_seconds"],
               "reference_setup_seconds": checkpoint["reference_setup_seconds"],
               "reference_generation_seconds": reference_metadata["generation_seconds"],
               "grid_compute_total_seconds": sum(item["compute_total_seconds"] for item in checkpoint["completed"]),
               "grid_validation_total_seconds": sum(item["validation_total_seconds"] for item in checkpoint["completed"])}
    atomic_write_json(output / "summary.json", summary)
    print(json.dumps(summary), flush=True)
    return 0


def export_grid(output: Path, completed: list[dict[str, Any]]) -> None:
    stream = io.StringIO()
    fields = ["optimization", "block_size", "valid", "median_seconds", "mean_seconds", "minimum_seconds",
              "maximum_seconds", "sample_stdev_seconds", "coefficient_of_variation",
              "median_absolute_deviation_seconds", "relative_mad", "process_wall_seconds", "attempt_id"]
    writer = csv.DictWriter(stream, fields)
    writer.writeheader()
    for group in completed:
        writer.writerow({**group["config"], "valid": group["classification"] == "success",
                         **group["statistics"], "process_wall_seconds": group["process_wall_seconds"],
                         "attempt_id": group["attempt_id"]})
    atomic_write_text(output / "grid_summary.csv", stream.getvalue())
