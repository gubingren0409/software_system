#!/usr/bin/env python3
"""Exercise P1-R1 seed parsing and reference sample-coordinate boundaries."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UINT64_MAX_TEXT = "18446744073709551615"
INVALID_SEEDS = ("-1", " -1", "", "18446744073709551616", "+1", "1 ", "1x")


def run(command: list[str], *, environment: dict[str, str], cwd: Path) -> dict[str, object]:
    started = time.monotonic()
    completed = subprocess.run(
        command, cwd=cwd, env=environment, text=True, capture_output=True, check=False
    )
    return {
        "command": command,
        "cwd": str(cwd),
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "process_wall_seconds": time.monotonic() - started,
    }


def require(record: dict[str, object], expected: int, label: str) -> None:
    if record["returncode"] != expected:
        raise RuntimeError(f"{label}: expected exit {expected}, got {record['returncode']}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)

    environment = os.environ.copy()
    environment["ASAN_OPTIONS"] = "detect_leaks=1:halt_on_error=1"
    environment["UBSAN_OPTIONS"] = "halt_on_error=1:print_stacktrace=1"
    records: list[dict[str, object]] = []
    parsed_results: dict[str, object] = {}

    with tempfile.TemporaryDirectory(prefix="matrix-p1-r1-boundaries-") as temporary_text:
        temporary = Path(temporary_text)
        common = [
            "/usr/bin/gcc", "-std=c11", "-Wall", "-Wextra", "-Wpedantic",
            "-Wconversion", "-O1", "-g", "-fsanitize=address,undefined",
            "-fno-omit-frame-pointer",
        ]

        for matrix_n in (1, 2):
            harness = temporary / f"sample_harness_n{matrix_n}"
            compile_harness = run(
                [*common, f"-DMATRIX_N={matrix_n}",
                 str(ROOT / "tests/reference_sample_harness.c"), "-lm", "-o", str(harness)],
                environment=environment, cwd=ROOT,
            )
            records.append({"label": f"compile_sample_harness_n{matrix_n}", **compile_harness})
            require(compile_harness, 0, f"compile sample harness n={matrix_n}")
            harness_run = run([str(harness)], environment=environment, cwd=ROOT)
            records.append({"label": f"run_sample_harness_n{matrix_n}", **harness_run})
            require(harness_run, 0, f"sample harness n={matrix_n}")

            reference = temporary / f"reference_n{matrix_n}"
            compile_reference = run(
                [*common, f"-DMATRIX_N={matrix_n}",
                 str(ROOT / "code/working/reference_generator.c"), "-lm", "-o", str(reference)],
                environment=environment, cwd=ROOT,
            )
            records.append({"label": f"compile_reference_n{matrix_n}", **compile_reference})
            require(compile_reference, 0, f"compile reference n={matrix_n}")

            for seed in ("0", UINT64_MAX_TEXT):
                data = temporary / f"reference_n{matrix_n}_seed{seed}.bin"
                reference_run = run(
                    [str(reference), "--seed", seed, "--input", "random", "--output",
                     str(data), "--accumulator", "long-double"],
                    environment=environment, cwd=ROOT,
                )
                label = f"reference_n{matrix_n}_seed_{seed}"
                records.append({"label": label, **reference_run})
                require(reference_run, 0, label)
                parsed = json.loads(str(reference_run["stdout"]))
                expected_samples = 1 if matrix_n == 1 else 4
                if parsed["sample_count"] != expected_samples or parsed["sample_mismatch_count"] != 0:
                    raise RuntimeError(f"unexpected reference samples for n={matrix_n}")
                parsed_results[label] = parsed

        harness_4096 = temporary / "sample_harness_n4096"
        compile_4096 = run(
            ["/usr/bin/gcc", "-std=c11", "-O1", "-DMATRIX_N=4096",
             str(ROOT / "tests/reference_sample_harness.c"), "-lm", "-o", str(harness_4096)],
            environment=environment, cwd=ROOT,
        )
        records.append({"label": "compile_sample_harness_n4096", **compile_4096})
        require(compile_4096, 0, "compile sample harness n=4096")
        run_4096 = run([str(harness_4096)], environment=environment, cwd=ROOT)
        records.append({"label": "run_sample_harness_n4096", **run_4096})
        require(run_4096, 0, "sample harness n=4096")
        parsed_results["sample_harness_n4096"] = json.loads(str(run_4096["stdout"]))

        reference_n2 = temporary / "reference_n2"
        candidate_n2 = temporary / "candidate_n2"
        compile_candidate = run(
            [*common, "-DMATRIX_N=2", str(ROOT / "code/working/matrix_multiplication.c"),
             "-lm", "-o", str(candidate_n2)],
            environment=environment, cwd=ROOT,
        )
        records.append({"label": "compile_candidate_n2", **compile_candidate})
        require(compile_candidate, 0, "compile candidate n=2")

        valid_reference = temporary / "reference_n2_seed0.bin"
        for seed in ("0", UINT64_MAX_TEXT):
            data = temporary / f"candidate_reference_seed{seed}.bin"
            make_reference = run(
                [str(reference_n2), "--seed", seed, "--input", "random", "--output",
                 str(data), "--accumulator", "long-double"],
                environment=environment, cwd=ROOT,
            )
            records.append({"label": f"candidate_reference_seed_{seed}", **make_reference})
            require(make_reference, 0, f"candidate reference seed {seed}")
            candidate_run = run(
                [str(candidate_n2), "--block-size", "1", "--seed", seed, "--input",
                 "random", "--reference", str(data)],
                environment=environment, cwd=ROOT,
            )
            label = f"candidate_n2_seed_{seed}"
            records.append({"label": label, **candidate_run})
            require(candidate_run, 0, label)
            parsed = json.loads(str(candidate_run["stdout"]))
            if not parsed["validation"]:
                raise RuntimeError(f"candidate valid seed failed: {seed}")
            parsed_results[label] = parsed

        for index, seed in enumerate(INVALID_SEEDS):
            reference_bad = run(
                [str(reference_n2), "--seed", seed, "--input", "random", "--output",
                 str(temporary / f"invalid_{index}.bin"), "--accumulator", "long-double"],
                environment=environment, cwd=ROOT,
            )
            records.append({"label": f"reference_invalid_seed_{index}", "seed": seed,
                            **reference_bad})
            require(reference_bad, 64, f"reference invalid seed {seed!r}")
            candidate_bad = run(
                [str(candidate_n2), "--block-size", "1", "--seed", seed, "--input",
                 "random", "--reference", str(valid_reference)],
                environment=environment, cwd=ROOT,
            )
            records.append({"label": f"candidate_invalid_seed_{index}", "seed": seed,
                            **candidate_bad})
            require(candidate_bad, 64, f"candidate invalid seed {seed!r}")

    result = {
        "schema": "p1-r1-boundary-regressions-v1",
        "status": "PASS",
        "valid_seeds": ["0", UINT64_MAX_TEXT],
        "invalid_seeds": list(INVALID_SEEDS),
        "reference_sanitized_sizes": [1, 2],
        "normal_size_sample_count": parsed_results["sample_harness_n4096"]["sample_count"],
        "parsed_results": parsed_results,
        "records": records,
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in (
        "status", "valid_seeds", "invalid_seeds", "reference_sanitized_sizes",
        "normal_size_sample_count")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
