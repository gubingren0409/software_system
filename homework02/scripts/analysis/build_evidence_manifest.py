#!/usr/bin/env python3
"""Inventory preserved A2 evidence without modifying any source artifact."""

import argparse
import csv
import hashlib
import io
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "audit" / "evidence_manifest.csv"
RESULTS = ROOT / "specjvm2008" / "results"
VERIFICATION_RESULTS = ROOT / "specjvm2008" / "verification_results"


def sources():
    optional_ids = set()
    for meta in (ROOT / "logs" / "jvm_parameter").rglob("*.meta"):
        for line in meta.read_text(encoding="utf-8").splitlines():
            if line.startswith("result_id=") and line[10:]:
                optional_ids.add(line[10:])
    for result in sorted(RESULTS.iterdir()):
        if not result.is_dir() or not result.name.startswith("SPECjvm2008."):
            continue
        if result.name == "SPECjvm2008.007":
            role = "formal-base-result"
        elif result.name in {f"SPECjvm2008.{n:03d}" for n in range(8, 11)}:
            role = "original-repeat-result"
        elif result.name in {"SPECjvm2008.015", "SPECjvm2008.016"}:
            role = "new-diagnostic-result"
        elif result.name in optional_ids:
            role = "optional-heap-result"
        else:
            role = "preserved-other-result"
        for path in sorted(result.rglob("*")):
            if path.is_file():
                yield path, role
    for path in sorted((ROOT / "logs").rglob("*")):
        if not path.is_file() or path.name in {
            "final_core_verification.log", "final_submission_verification.log",
            "optional_final_verification.log", "enhancement_final_verification.log",
            "oom_reverification_final_verification.log",
        }:
            continue  # A verification output cannot include its own digest in the manifest.
        if path.name == "base_run.log":
            role = "formal-base-log"
        elif path.name == "reporter_regeneration.log":
            role = "reporter-log"
        elif path.name == "install.log":
            role = "descriptive-install-record-with-correction"
        elif "diagnostics" in path.parts:
            role = "new-diagnostic-log"
        elif "jvm_parameter" in path.parts:
            role = "optional-heap-log"
        else:
            role = "preserved-other-log"
        yield path, role
    if VERIFICATION_RESULTS.is_dir():
        for path in sorted(VERIFICATION_RESULTS.rglob("*")):
            if path.is_file():
                yield path, "oom-reverification-result"
    for path in sorted((ROOT / "environment").iterdir()):
        if path.is_file():
            yield path, "environment-record"
    for name in (
        "run_base.ps1", "run_base.sh", "regenerate_report.sh",
        "verify_goal1.ps1", "verify_submission.ps1",
    ):
        yield ROOT / "scripts" / name, "method-or-verifier"
    for path in sorted((ROOT / "scripts" / "analysis").iterdir()):
        if path.is_file():
            yield path, "analysis-or-diagnostic-script"
    for path in sorted((ROOT / "scripts" / "jvm_parameter").iterdir()):
        if path.is_file() and path.suffix in {".py", ".ps1", ".sh"}:
            yield path, "optional-heap-method"
    for path in sorted((ROOT / "analysis" / "jvm_parameter").iterdir()):
        if path.is_file():
            yield path, "optional-heap-analysis"
    for path in sorted((ROOT / "images" / "jvm_parameter").iterdir()):
        if path.is_file():
            yield path, "optional-heap-plot"
    yield ROOT / "audit" / "optional_experiment_review.md", "optional-heap-review"
    yield ROOT / "audit" / "optional_enhancement_review.md", "optional-enhancement-review"
    yield ROOT / "analysis" / "repeat_test_results.csv", "original-repeat-index"
    yield ROOT / "analysis" / "official_reference_base.html", "original-official-snapshot"
    yield ROOT / "analysis" / "official_reference_huawei.html", "new-official-snapshot"
    yield ROOT / "images" / "base_scores.jpg", "original-base-chart-copy"


def build():
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(("relative_path", "role", "bytes", "modified_utc", "sha256"))
    count = 0
    for path, role in sources():
        if not path.is_file():
            raise FileNotFoundError(path)
        stat = path.stat()
        writer.writerow((
            path.relative_to(ROOT).as_posix(), role, stat.st_size,
            datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            hashlib.sha256(path.read_bytes()).hexdigest(),
        ))
        count += 1
    return output.getvalue(), count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content, count = build()
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != content:
            raise ValueError("Evidence manifest differs from present source artifacts")
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(content, encoding="utf-8", newline="")
    print(f"PASS: {count} preserved evidence artifacts inventoried")


if __name__ == "__main__":
    main()
