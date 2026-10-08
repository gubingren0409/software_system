from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from autotuner.core import (  # noqa: E402
    Config,
    ConfigSpace,
    EvaluationContext,
    Evaluator,
    TargetAdapter,
    atomic_write_json,
    atomic_write_text,
    classify_execution,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the complete P1 small correctness suite")
    parser.add_argument("--target", type=Path, default=REPO / "configs/target.json")
    parser.add_argument("--space", type=Path, default=REPO / "configs/config_space.json")
    parser.add_argument(
        "--output-directory", type=Path, default=REPO / "evidence/p1/correctness"
    )
    parser.add_argument(
        "--runtime-evidence-root",
        type=Path,
        default=Path("/var/tmp/matrix-autotuner-p1-10245102457/sessions/p1-correctness"),
    )
    args = parser.parse_args()
    raw_evidence = args.runtime_evidence_root.resolve()
    target = TargetAdapter.load(args.target, evidence_root=raw_evidence)
    space = ConfigSpace.load(args.space)
    configs = space.all()
    if len(configs) != 20 or len(set(configs)) != 20:
        raise RuntimeError("configuration space is not the required 20 unique combinations")
    evaluator = Evaluator(target)

    groups = (
        (129, "random", 20261008),
        (129, "random", 20261009),
        (129, "zero", 20261008),
        (129, "identity", 20261008),
        (130, "random", 20261008),
        (130, "random", 20261009),
        (130, "zero", 20261008),
        (130, "identity", 20261008),
    )
    records: list[dict[str, object]] = []
    for matrix_n, input_pattern, seed in groups:
        for config in configs:
            label = (
                f"small_n{matrix_n}_{input_pattern}_seed{seed}_"
                f"{config.optimization}_s{config.block_size}"
            )
            record = evaluator.evaluate(
                config,
                EvaluationContext(
                    matrix_n=matrix_n,
                    seed=seed,
                    input_pattern=input_pattern,
                    timeout_seconds=30.0,
                    evidence_label=label,
                    protocol_hash="p1-small-correctness-v1",
                ),
            )
            records.append(attach_raw_evidence(record, raw_evidence / "runs" / label))
            if record["classification"] != "success":
                raise RuntimeError(f"small correctness failed: {label}: {record['classification']}")

    fault_records: list[dict[str, object]] = []
    fault_names = {
        1: "finite_mismatch",
        2: "result_nan",
        3: "result_inf",
        4: "reference_nan",
        5: "elapsed_nan",
        6: "checksum_nan",
        7: "error_nan",
    }
    for fault, name in fault_names.items():
        record = evaluator.evaluate(
            Config("O2", 24),
            EvaluationContext(
                matrix_n=129,
                seed=20261008,
                input_pattern="random",
                timeout_seconds=30.0,
                evidence_label=f"fault_{fault}_{name}",
                fault_injection=fault,
                protocol_hash="p1-fault-injection-v1",
            ),
        )
        fault_records.append(
            attach_raw_evidence(record, raw_evidence / "runs" / f"fault_{fault}_{name}")
        )
        if record["classification"] != "validation_failure" or record["score_seconds"] is not None:
            raise RuntimeError(f"fault was not rejected: {name}: {record['classification']}")

    strict_cli_records = run_strict_cli_checks(target)

    summary = {
        "schema": "p1-correctness-summary-v1",
        "config_count": len(configs),
        "group_count": len(groups),
        "small_case_count": len(records),
        "small_success_count": sum(record["classification"] == "success" for record in records),
        "fault_case_count": len(fault_records),
        "fault_rejection_count": sum(
            record["classification"] == "validation_failure" for record in fault_records
        ),
        "strict_cli_case_count": len(strict_cli_records),
        "strict_cli_rejection_count": sum(
            record["classification"] == "parameter_rejected" for record in strict_cli_records
        ),
        "matrix_sizes": [129, 130],
        "random_seeds": [20261008, 20261009],
        "input_patterns": ["random", "zero", "identity"],
        "abs_tolerance": target.config["abs_tolerance"],
        "rel_tolerance": target.config["rel_tolerance"],
        "status": "PASS",
    }
    output_directory = args.output_directory.resolve()
    atomic_write_json(output_directory / "summary.json", summary)
    atomic_write_json(output_directory / "faults.json", fault_records)
    atomic_write_json(output_directory / "strict_cli.json", strict_cli_records)
    atomic_write_text(
        output_directory / "small_cases.jsonl",
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
    )
    reference_keys = sorted({str(record["reference_key"]) for record in records})
    reference_manifests = [
        json.loads(
            (target.cache_root / "reference" / key / "manifest.json").read_text(
                encoding="utf-8"
            )
        )
        for key in reference_keys
    ]
    atomic_write_json(output_directory / "reference_manifests.json", reference_manifests)
    write_csv(output_directory / "small_cases.csv", records)
    print(json.dumps(summary, sort_keys=True))
    return 0


def run_strict_cli_checks(target: TargetAdapter) -> list[dict[str, object]]:
    artifact = target.build_candidate(129, "O2")
    reference = target.get_reference(129, 20261008, "random", 30.0)
    base = [
        str(artifact.binary),
        "--block-size",
        "24",
        "--seed",
        "20261008",
        "--input",
        "random",
        "--reference",
        str(reference.data_path),
    ]
    variants = {
        "block_zero": [*base[:2], "0", *base[3:]],
        "block_above_n": [*base[:2], "130", *base[3:]],
        "block_trailing_text": [*base[:2], "24junk", *base[3:]],
        "negative_seed": [*base[:4], "-1", *base[5:]],
        "missing_argument": base[:-2],
        "extra_argument": [*base, "--unknown", "value"],
    }
    records: list[dict[str, object]] = []
    for name, command in variants.items():
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
        classification, parsed, detail = classify_execution(
            completed.returncode, False, completed.stdout
        )
        record: dict[str, object] = {
            "name": name,
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "classification": classification,
            "classification_detail": detail,
            "parsed": parsed,
            "score_seconds": None,
        }
        records.append(record)
        if classification != "parameter_rejected":
            raise RuntimeError(f"strict CLI case was not rejected: {name}: {classification}")
    return records


def attach_raw_evidence(
    record: dict[str, object], run_directory: Path
) -> dict[str, object]:
    run_directory = Path(str(record.get("run_directory", run_directory)))
    enriched = dict(record)
    for key, filename in (
        ("raw_stdout", "stdout.txt"),
        ("raw_stderr", "stderr.txt"),
        ("raw_resource", "resource.txt"),
    ):
        path = run_directory / filename
        enriched[key] = path.read_text(encoding="utf-8") if path.exists() else ""
    return enriched


def write_csv(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=(
                "matrix_n",
                "input",
                "seed",
                "optimization",
                "block_size",
                "classification",
                "score_seconds",
                "max_abs_error",
                "max_rel_error",
                "build_key",
                "reference_key",
            ),
        )
        writer.writeheader()
        for record in records:
            context = record["context"]
            config = record["config"]
            target_result = record["target_result"]
            writer.writerow(
                {
                    "matrix_n": context["matrix_n"],
                    "input": context["input_pattern"],
                    "seed": context["seed"],
                    "optimization": config["optimization"],
                    "block_size": config["block_size"],
                    "classification": record["classification"],
                    "score_seconds": record["score_seconds"],
                    "max_abs_error": target_result["max_abs_error"],
                    "max_rel_error": target_result["max_rel_error"],
                    "build_key": record["build_key"],
                    "reference_key": record["reference_key"],
                }
            )
    temporary.replace(path)


if __name__ == "__main__":
    raise SystemExit(main())
