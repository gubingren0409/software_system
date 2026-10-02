#!/usr/bin/env python3
"""Verify isolation and evidence completeness for the nine OOM reruns."""

import csv
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / "analysis" / "jvm_parameter"
EXPECTED_FORMAL = "4ae651e312061d09760743ab9908129b633e9ce1e5b5b296c13d4a30605e05ad"
EXPECTED_MATRIX = "56fe8955ac5b27757bb01e93ae58e471c74ca3dabc22fd46d748abb9701fc09f"


def read(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    formal = ROOT / "specjvm2008" / "results" / "SPECjvm2008.007" / "SPECjvm2008.007.raw"
    matrix_path = ANALYSIS / "heap_parameter_results.csv"
    require(digest(formal) == EXPECTED_FORMAL, "Formal .007 raw changed")
    require(digest(matrix_path) == EXPECTED_MATRIX, "Original 48-attempt matrix changed")
    matrix = read(matrix_path)
    require(len(matrix) == 48, "Original matrix no longer has 48 attempts")
    require(sum(row["status"] == "invalid" for row in matrix) == 9,
            "Original matrix invalid count changed")

    rows = read(ANALYSIS / "oom_reverification_results.csv")
    require(len(rows) == 9, "Expected nine reverification rows")
    require(len({row["verification_result_id"] for row in rows}) == 9,
            "Verification Result IDs are not unique")
    original_ids = {row["result_id"] for row in matrix}
    for row in rows:
        require(row["failure_reproduced"] == "true", f"Failure not reproduced: {row['source_run_key']}")
        require(int(row["verification_oom_occurrences"]) > 0,
                f"OOM absent: {row['source_run_key']}")
        require(row["verification_not_valid"] == "true" and
                row["verification_measured_score_present"] == "false",
                f"Invalidity evidence incomplete: {row['source_run_key']}")
        require(row["verification_result_id"] not in original_ids,
                f"Verification reused an original Result ID: {row['verification_result_id']}")
        require(row["raw_path"].startswith("specjvm2008/verification_results/"),
                "Verification raw is not isolated from original results")
        for field in ("run_log_path", "gc_log_path", "raw_path"):
            require((ROOT / row[field]).is_file(), f"Missing evidence: {row[field]}")
        run_text = (ROOT / row["run_log_path"]).read_text(encoding="latin-1", errors="replace")
        require('openjdk version "1.7.0_75"' in run_text and
                "OpenJDK 64-Bit Server VM (build 24.75-b04" in run_text,
                f"JVM identity mismatch: {row['verification_run_key']}")
        command = row["command"]
        require("--base -bt 16" in command and "-XX:+PrintGCDetails" in command and
                "-XX:+PrintGCTimeStamps" in command and "-Xloggc:" in command,
                f"Protocol mismatch: {row['verification_run_key']}")
        expected_heap = "-Xmx512m" if row["heap_config"] == "xmx512m" else "-Xmx1024m"
        require(expected_heap in command, f"Heap flag mismatch: {row['verification_run_key']}")
        expected_bytes = "536870912" if row["heap_config"] == "xmx512m" else "1073741824"
        require(f"MaxHeapSize                              := {expected_bytes}" in run_text,
                f"Actual MaxHeapSize mismatch: {row['verification_run_key']}")

    report = (ANALYSIS / "oom_reverification_report.md").read_text(encoding="utf-8")
    require("**9/9**" in report and "不属于原 48 次实验矩阵" in report,
            "Verification report lacks verdict or isolation statement")
    print("PASS: 9/9 failures independently reproduced; original matrix and formal .007 intact")


if __name__ == "__main__":
    main()
