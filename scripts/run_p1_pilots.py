from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from autotuner.core import (  # noqa: E402
    Config,
    EvaluationContext,
    Evaluator,
    TargetAdapter,
    atomic_write_json,
    atomic_write_text,
    sha256_file,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resource-gate", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    resource_gate = json.loads(args.resource_gate.read_text(encoding="utf-8"))

    evidence = REPO / "evidence/p1/pilots"
    raw_evidence = Path("/var/tmp/matrix-autotuner-p1-10245102457/sessions/p1-pilots")
    target = TargetAdapter.load(REPO / "configs/target.json", evidence_root=raw_evidence)
    evaluator = Evaluator(target)
    representative_block = 64
    seed = 20261008
    input_pattern = "random"
    wsl_gate = 2 * 1024 * 1024 * 1024

    medium_records: list[dict[str, object]] = []
    for optimization in ("O0", "O1", "O2", "O3"):
        label = f"medium_n512_{optimization}_s{representative_block}"
        record = evaluator.evaluate(
            Config(optimization, representative_block),
            EvaluationContext(
                matrix_n=512,
                seed=seed,
                input_pattern=input_pattern,
                timeout_seconds=120.0,
                evidence_label=label,
                min_wsl_available_bytes=wsl_gate,
                protocol_hash="p1-medium-pilot-v1",
            ),
        )
        medium_records.append(attach_raw(record, raw_evidence / "runs" / label))
        require_success(record, label)

    timeout_plan: dict[str, int] = {}
    projections: dict[str, float] = {}
    for record in medium_records:
        optimization = str(record["config"]["optimization"])
        projected = float(record["score_seconds"]) * 512.0
        projections[optimization] = projected
        timeout_plan[optimization] = math.ceil(max(60.0, min(1800.0, projected * 3.0)))
    pre_default_plan = {
        "schema": "p1-pre-default-plan-v1",
        "basis": "n=512 compute_seconds scaled by (4096/512)^3 = 512",
        "representative_block_size": representative_block,
        "seed": seed,
        "input": input_pattern,
        "projected_compute_seconds": projections,
        "timeout_seconds": timeout_plan,
        "resource_gate_sha256": sha256_file(args.resource_gate),
    }
    atomic_write_json(evidence / "pre_default_plan.json", pre_default_plan)

    if resource_gate.get("functional_gate") != "PASS":
        blocked = {
            "schema": "p1-default-resource-block-v1",
            "status": "RESOURCE_REJECTED",
            "reason": "host/WSL functional resource gate did not pass",
            "resource_gate": resource_gate,
            "medium_success_count": len(medium_records),
            "timeout_plan": timeout_plan,
        }
        atomic_write_json(evidence / "resource_blocked.json", blocked)
        atomic_write_text(
            evidence / "medium_runs.jsonl",
            "".join(json.dumps(record, sort_keys=True) + "\n" for record in medium_records),
        )
        write_csv(evidence / "medium_runs.csv", medium_records)
        print(json.dumps(blocked, sort_keys=True))
        return 2

    default_records: list[dict[str, object]] = []
    for optimization in ("O0", "O1", "O2", "O3"):
        label = f"default_n4096_{optimization}_s{representative_block}_pilot"
        record = evaluator.evaluate(
            Config(optimization, representative_block),
            EvaluationContext(
                matrix_n=4096,
                seed=seed,
                input_pattern=input_pattern,
                timeout_seconds=float(timeout_plan[optimization]),
                evidence_label=label,
                min_wsl_available_bytes=wsl_gate,
                protocol_hash="p1-default-pilot-v1",
            ),
        )
        default_records.append(attach_raw(record, raw_evidence / "runs" / label))
        require_success(record, label)

    warmup_label = f"default_n4096_O3_s{representative_block}_warmup"
    warmup = evaluator.evaluate(
        Config("O3", representative_block),
        EvaluationContext(
            matrix_n=4096,
            seed=seed,
            input_pattern=input_pattern,
            timeout_seconds=float(timeout_plan["O3"]),
            evidence_label=warmup_label,
            min_wsl_available_bytes=wsl_gate,
            protocol_hash="p1-repeatability-v1",
        ),
    )
    warmup = attach_raw(warmup, raw_evidence / "runs" / warmup_label)
    require_success(warmup, warmup_label)

    repeats: list[dict[str, object]] = []
    for index in range(1, 6):
        label = f"default_n4096_O3_s{representative_block}_repeat{index}"
        record = evaluator.evaluate(
            Config("O3", representative_block),
            EvaluationContext(
                matrix_n=4096,
                seed=seed,
                input_pattern=input_pattern,
                timeout_seconds=float(timeout_plan["O3"]),
                evidence_label=label,
                min_wsl_available_bytes=wsl_gate,
                protocol_hash="p1-repeatability-v1",
            ),
        )
        repeats.append(attach_raw(record, raw_evidence / "runs" / label))
        require_success(record, label)

    values = [float(record["score_seconds"]) for record in repeats]
    median = statistics.median(values)
    mean = statistics.fmean(values)
    stdev = statistics.stdev(values)
    mad = statistics.median(abs(value - median) for value in values)
    variability = {
        "count": len(values),
        "values_seconds": values,
        "minimum_seconds": min(values),
        "maximum_seconds": max(values),
        "mean_seconds": mean,
        "median_seconds": median,
        "sample_stdev_seconds": stdev,
        "coefficient_of_variation": stdev / mean,
        "median_absolute_deviation_seconds": mad,
        "relative_mad": mad / median,
    }

    all_records = [*medium_records, *default_records, warmup, *repeats]
    reference_key = str(default_records[0]["reference_key"])
    reference_manifest = json.loads(
        (target.cache_root / "reference" / reference_key / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    atomic_write_json(evidence / "reference_manifest.json", reference_manifest)
    atomic_write_text(
        evidence / "runs.jsonl",
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in all_records),
    )
    write_csv(evidence / "runs.csv", all_records)
    summary = {
        "schema": "p1-pilot-summary-v1",
        "status": "PASS",
        "medium_success_count": len(medium_records),
        "default_success_count": len(default_records),
        "warmup_success": warmup["classification"] == "success",
        "repeat_success_count": len(repeats),
        "representative_block_size": representative_block,
        "seed": seed,
        "input": input_pattern,
        "medium": summarize_by_optimization(medium_records),
        "default": summarize_by_optimization(default_records),
        "repeatability": variability,
        "pre_default_timeout_plan": timeout_plan,
        "reference_key": reference_key,
        "reference_sha256": default_records[0]["reference_sha256"],
        "resource_gate_sha256": sha256_file(args.resource_gate),
    }
    atomic_write_json(evidence / "summary.json", summary)
    print(json.dumps(summary, sort_keys=True))
    return 0


def attach_raw(record: dict[str, object], directory: Path) -> dict[str, object]:
    enriched = dict(record)
    for key, filename in (
        ("raw_stdout", "stdout.txt"),
        ("raw_stderr", "stderr.txt"),
        ("raw_resource", "resource.txt"),
    ):
        path = directory / filename
        enriched[key] = path.read_text(encoding="utf-8") if path.exists() else ""
    return enriched


def require_success(record: dict[str, object], label: str) -> None:
    if record["classification"] != "success":
        raise RuntimeError(f"pilot failed: {label}: {record['classification']}")


def summarize_by_optimization(records: list[dict[str, object]]) -> dict[str, object]:
    return {
        str(record["config"]["optimization"]): {
            "compute_seconds": record["score_seconds"],
            "process_wall_seconds": record["process_wall_seconds"],
            "build_key": record["build_key"],
            "reference_key": record["reference_key"],
            "max_abs_error": record["target_result"]["max_abs_error"],
        }
        for record in records
    }


def write_csv(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=(
                "label",
                "matrix_n",
                "optimization",
                "block_size",
                "classification",
                "compute_seconds",
                "process_wall_seconds",
                "max_abs_error",
                "max_rel_error",
                "build_key",
                "reference_key",
            ),
        )
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "label": record["context"]["evidence_label"],
                    "matrix_n": record["context"]["matrix_n"],
                    "optimization": record["config"]["optimization"],
                    "block_size": record["config"]["block_size"],
                    "classification": record["classification"],
                    "compute_seconds": record["score_seconds"],
                    "process_wall_seconds": record["process_wall_seconds"],
                    "max_abs_error": record["target_result"]["max_abs_error"],
                    "max_rel_error": record["target_result"]["max_rel_error"],
                    "build_key": record["build_key"],
                    "reference_key": record["reference_key"],
                }
            )
    temporary.replace(path)


if __name__ == "__main__":
    raise SystemExit(main())
