#!/usr/bin/env python3
"""Verify the committed P1 evidence without rerunning expensive experiments."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_SHA256 = "188d011109c4470e1f41829216e8677a5c2d8f2b7c8a44215652320dbdf6de15"


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    core = ROOT / "autotuner/core.py"
    require(core.is_file(), "required core module is missing")
    imported = subprocess.run(
        [sys.executable, "-c", "import autotuner.core"],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    require(imported.returncode == 0, f"core module import failed: {imported.stderr}")
    cli = subprocess.run(
        [sys.executable, "-m", "autotuner", "--help"],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    require(cli.returncode == 0 and "list-configs" in cli.stdout,
            f"autotuner CLI failed to start: {cli.stderr}")

    sys.path.insert(0, str(ROOT))
    from autotuner.core import ConfigSpace

    original = ROOT / "code/original/matrix_multiplication.c"
    require(hashlib.sha256(original.read_bytes()).hexdigest() == ORIGINAL_SHA256,
            "teacher source hash changed")

    space = ConfigSpace.load(ROOT / "configs/config_space.json")
    configs = space.all()
    require(len(configs) == 20 and len(set(configs)) == 20,
            "configuration space is not 20 unique combinations")

    correctness = load("evidence/p1/correctness/summary.json")
    require(correctness["status"] == "PASS", "correctness suite did not pass")
    require(correctness["small_case_count"] == correctness["small_success_count"] == 160,
            "small correctness case count mismatch")
    require(correctness["fault_case_count"] == correctness["fault_rejection_count"] == 7,
            "fault injection rejection mismatch")
    require(correctness["strict_cli_case_count"] == correctness["strict_cli_rejection_count"] == 6,
            "strict CLI rejection mismatch")

    faults = load("evidence/p1/correctness/faults.json")
    require(len(faults) == 7, "fault evidence count mismatch")
    require(all(item["classification"] == "validation_failure" and item["score_seconds"] is None
                for item in faults), "a fault received a valid score")

    pilot = load("evidence/p1/pilots/summary.json")
    require(pilot["status"] == "PASS", "pilot suite did not pass")
    require(pilot["medium_success_count"] == 4 and pilot["default_success_count"] == 4,
            "optimization-level pilot count mismatch")
    require(pilot["repeat_success_count"] == 5 and pilot["warmup_success"],
            "repeatability evidence incomplete")
    require(all(item["max_abs_error"] == 0 for item in pilot["default"].values()),
            "default-size candidate/reference mismatch")

    reference = load("evidence/p1/pilots/reference_manifest.json")
    require(reference["complete"], "default reference cache was incomplete")
    require(reference["byte_count"] == 4096 * 4096 * 8, "default reference size mismatch")
    require(reference["sample_mismatch_count"] == 0 and reference["sample_count"] == 16,
            "long-double sample check mismatch")
    require(reference["data_sha256"] == pilot["reference_sha256"],
            "reference data hash mismatch")

    protocol = load("configs/measurement_protocol.json")
    require(protocol["measurement"]["warmup_runs"] == 1, "unexpected warm-up count")
    require(protocol["measurement"]["measured_runs"] == 5, "unexpected measured count")
    require(protocol["measurement"]["score_statistic"] == "median compute_seconds",
            "unexpected score statistic")

    evidence_roots = ["autotuner", "code/working", "configs", "docs", "evidence/p1", "scripts", "tests"]
    forbidden = [path for relative in evidence_roots for path in (ROOT / relative).rglob("*")
                 if path.is_file() and path.suffix.lower() in {".bin", ".exe", ".o"}]
    require(not forbidden, f"binary/cache artifact present in P1 deliverables: {forbidden}")
    print("p1_verification=PASS")
    print(f"original_sha256={ORIGINAL_SHA256}")
    print(f"core_sha256={hashlib.sha256(core.read_bytes()).hexdigest()}")
    print("core_import=PASS cli_start=PASS unique_configs=20/20")
    print("small_cases=160/160 faults=7/7 strict_cli=6/6")
    print("medium_optimization_levels=4/4 default_optimization_levels=4/4 repeats=5/5")


if __name__ == "__main__":
    main()
