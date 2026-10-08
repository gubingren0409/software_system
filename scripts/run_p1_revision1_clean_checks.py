#!/usr/bin/env python3
"""Run the P1-R1 acceptance checks from an exported, clean commit tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECOVERED_CORE_SHA256 = "1675f682e45103b5fb4d1be2bb8fe08fb6c8f8ba7f206c02a04f4c3549c84ccd"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--content-sha", required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_directory.resolve()
    output.mkdir(parents=True, exist_ok=True)

    if (ROOT / ".git").exists():
        raise RuntimeError("clean validation must run from git archive or an independent checkout")
    initial_pycache = [str(path.relative_to(ROOT)) for path in ROOT.rglob("__pycache__")]
    if initial_pycache:
        raise RuntimeError(f"clean tree unexpectedly contains bytecode caches: {initial_pycache}")

    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    commands_directory = output / "commands"
    command_records: list[dict[str, object]] = []

    def execute(name: str, command: list[str], cwd: Path = ROOT) -> dict[str, object]:
        started = time.monotonic()
        completed = subprocess.run(
            command, cwd=cwd, env=environment, text=True, capture_output=True, check=False
        )
        record: dict[str, object] = {
            "name": name,
            "command": command,
            "cwd": str(cwd),
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "process_wall_seconds": time.monotonic() - started,
        }
        command_records.append(record)
        write_json(commands_directory / f"{len(command_records):02d}_{name}.json", record)
        return record

    def expect(record: dict[str, object], expected: int = 0) -> None:
        if record["returncode"] != expected:
            raise RuntimeError(
                f"{record['name']} returned {record['returncode']}, expected {expected}"
            )

    hash_paths = [
        "autotuner/__init__.py",
        "autotuner/__main__.py",
        "autotuner/cli.py",
        "autotuner/core.py",
        "code/original/matrix_multiplication.c",
        "code/working/matrix_input.h",
        "code/working/matrix_multiplication.c",
        "code/working/reference_generator.c",
        "configs/config_space.json",
        "configs/measurement_protocol.json",
        "configs/search_protocol.json",
        "configs/target.json",
        "scripts/run_p1_correctness.py",
        "scripts/run_p1_revision1_regressions.py",
        "scripts/verify_p1.py",
        "tests/reference_sample_harness.c",
        "tests/test_runner.py",
    ]
    hashes = {relative: sha256(ROOT / relative) for relative in hash_paths}
    write_json(
        output / "source_hashes.json",
        {
            "content_commit": args.content_sha,
            "recovered_core_pre_revision_sha256": RECOVERED_CORE_SHA256,
            "verified_files": hashes,
        },
    )

    for name, command in (
        ("python_version", [sys.executable, "--version"]),
        ("gcc_version", ["/usr/bin/gcc", "--version"]),
        ("git_version", ["git", "--version"]),
        ("uname", ["uname", "-a"]),
        ("cli_help", [sys.executable, "-m", "autotuner", "--help"]),
        ("list_configs", [sys.executable, "-m", "autotuner", "list-configs"]),
        ("unit_tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]),
        ("verify_p1", [sys.executable, "scripts/verify_p1.py"]),
    ):
        record = execute(name, command)
        expect(record)

    list_record = next(item for item in command_records if item["name"] == "list_configs")
    listed = json.loads(str(list_record["stdout"]))
    if len(listed) != 20 or len({(item["optimization"], item["block_size"]) for item in listed}) != 20:
        raise RuntimeError("CLI did not list 20 unique configurations")

    with tempfile.TemporaryDirectory(prefix="matrix-p1-r1-clean-") as temporary_text:
        temporary = Path(temporary_text)
        missing_core = temporary / "missing-core-tree"
        shutil.copytree(ROOT, missing_core, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        (missing_core / "autotuner/core.py").unlink()
        missing_record = execute(
            "verify_missing_core_expected_failure",
            [sys.executable, "scripts/verify_p1.py"],
            cwd=missing_core,
        )
        if missing_record["returncode"] == 0:
            raise RuntimeError("verification unexpectedly passed without autotuner/core.py")

        base_target = json.loads((ROOT / "configs/target.json").read_text(encoding="utf-8"))

        def clean_target(name: str, cache: Path) -> Path:
            data = dict(base_target)
            data["candidate_source"] = str((ROOT / "code/working/matrix_multiplication.c").resolve())
            data["reference_source"] = str((ROOT / "code/working/reference_generator.c").resolve())
            data["shared_sources"] = [str((ROOT / "code/working/matrix_input.h").resolve())]
            data["cache_root"] = str(cache.resolve())
            path = temporary / name
            write_json(path, data)
            return path

        evaluate_cache = temporary / "evaluate-cache"
        evaluate_evidence = temporary / "evaluate-evidence"
        target_evaluate = clean_target("target-evaluate.json", evaluate_cache)
        if evaluate_cache.exists() or evaluate_evidence.exists():
            raise RuntimeError("evaluate cache/evidence was not empty before execution")
        evaluate = execute(
            "evaluate_n17_o2_s8",
            [
                sys.executable, "-m", "autotuner", "--target", str(target_evaluate),
                "--space", str(ROOT / "configs/config_space.json"), "--evidence-root",
                str(evaluate_evidence), "evaluate", "--size", "17", "--optimization", "O2",
                "--block-size", "8", "--seed", "20261008", "--input", "random",
                "--timeout", "30", "--label", "clean_n17_o2_s8",
            ],
        )
        expect(evaluate)
        evaluation = json.loads(str(evaluate["stdout"]))
        if (evaluation["source"] != "fresh_measurement" or
                evaluation["classification"] != "success" or
                not evaluation["target_result"]["validation"]):
            raise RuntimeError("clean n=17 evaluation was not a fresh validated success")

        boundary_output = output / "boundary_regressions.json"
        boundary = execute(
            "boundary_regressions",
            [sys.executable, "scripts/run_p1_revision1_regressions.py", "--output",
             str(boundary_output)],
        )
        expect(boundary)

        correctness_cache = temporary / "correctness-cache"
        correctness_runtime = temporary / "correctness-runtime"
        target_correctness = clean_target("target-correctness.json", correctness_cache)
        if correctness_cache.exists() or correctness_runtime.exists():
            raise RuntimeError("correctness cache/evidence was not empty before execution")
        correctness = execute(
            "small_correctness_and_faults",
            [
                sys.executable, "scripts/run_p1_correctness.py", "--target",
                str(target_correctness), "--space", str(ROOT / "configs/config_space.json"),
                "--output-directory", str(output / "correctness"),
                "--runtime-evidence-root", str(correctness_runtime),
            ],
        )
        expect(correctness)
        correctness_summary = json.loads(
            (output / "correctness/summary.json").read_text(encoding="utf-8")
        )
        if correctness_summary["status"] != "PASS":
            raise RuntimeError("small correctness suite did not pass")

        clean_target_record = {
            "evaluate_target": json.loads(target_evaluate.read_text(encoding="utf-8")),
            "correctness_target": json.loads(target_correctness.read_text(encoding="utf-8")),
            "source_paths_are_in_clean_tree": True,
            "evaluate_cache_initially_empty": True,
            "correctness_cache_initially_empty": True,
        }
        write_json(output / "clean_target_configs.json", clean_target_record)

    write_json(output / "commands/index.json", command_records)
    summary = {
        "schema": "p1-r1-clean-validation-v1",
        "status": "PASS",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "content_commit": args.content_sha,
        "clean_root": str(ROOT),
        "clean_tree_has_git_metadata": False,
        "initial_pycache_count": 0,
        "pythonpath_removed": True,
        "command_count": len(command_records),
        "core_import_and_cli": "PASS",
        "unique_configurations": 20,
        "missing_core_negative_test": "EXPECTED_NONZERO",
        "fresh_evaluation": {
            "classification": evaluation["classification"],
            "source": evaluation["source"],
            "validation": evaluation["target_result"]["validation"],
        },
        "boundary_regressions": "PASS",
        "small_correctness": {
            "success": correctness_summary["small_success_count"],
            "total": correctness_summary["small_case_count"],
            "fault_rejections": correctness_summary["fault_rejection_count"],
            "fault_total": correctness_summary["fault_case_count"],
        },
    }
    write_json(output / "summary.json", summary)
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
