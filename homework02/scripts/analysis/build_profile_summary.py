#!/usr/bin/env python3
"""Extract separately labelled research profiles from new, noncompliant result IDs."""

import argparse
import csv
import hashlib
import io
import re
from decimal import Decimal
from pathlib import Path

from build_core_data import ROOT, RESULTS, raw_workloads, rounded, text_scores


SAMPLES = (("compress", "015"), ("sunflow", "016"))
OUTPUT = ROOT / "analysis" / "diagnostics" / "profile_summary.csv"


def pattern(body, expression, label):
    found = re.search(expression, body, re.MULTILINE)
    if not found:
        raise ValueError(f"Missing {label} in profile log")
    return found.group(1)


def build():
    rows = []
    for workload, suffix in SAMPLES:
        result_id = "SPECjvm2008." + suffix
        raw = RESULTS / result_id / f"{result_id}.raw"
        log = ROOT / "logs" / "diagnostics" / f"profile_{workload}_{suffix}.log"
        body = log.read_text(encoding="utf-8", errors="replace")
        root, workloads = raw_workloads(result_id)
        values, _, _, report = text_scores(result_id)
        if len(workloads) != 1 or workloads[0][0] != workload:
            raise ValueError(f"Wrong diagnostic workload: {result_id}")
        if "Run is valid, but not compliant" not in report or "WARNING: Run will not be compliant" not in body:
            raise ValueError(f"Diagnostic validity/status mismatch: {result_id}")
        if root.findtext("workload") != "SPECjvm2008 Base":
            raise ValueError("Expected Base mode for a single-workload diagnostic")
        measured = workloads[0][3]["score"]
        score = values[workload, "iteration 1"]
        if rounded(measured) != score:
            raise ValueError(f"Raw and text diagnostic scores disagree: {result_id}")
        if Decimal(pattern(body, rf"^Score on {workload}:\s+([0-9.]+) ops/m$", "score")) != score:
            raise ValueError(f"Log and raw diagnostic scores disagree: {result_id}")
        if pattern(body, r"^EXPECTED_RESULT_ID=(.+)$", "result ID") != result_id:
            raise ValueError("Expected diagnostic ID differs from raw file")
        if pattern(body, r"^EXIT_STATUS=(\d+)$", "exit status") != "0":
            raise ValueError("Diagnostic process did not exit cleanly")
        counters = {}
        for event in ("cycles:u", "instructions:u", "cache-misses:u"):
            counters[event] = pattern(body, rf"^\s*([0-9]+)\s+{re.escape(event)}\s", event)
        rows.append({
            "purpose": "diagnostic_only_noncompliant",
            "result_id": result_id,
            "workload": workload,
            "measured_score_ops_per_min": str(score),
            "raw_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
            "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest(),
            "elapsed_wall_clock": pattern(body, r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\):\s*(.+)$", "elapsed"),
            "user_time_s": pattern(body, r"User time \(seconds\):\s*([0-9.]+)$", "user time"),
            "system_time_s": pattern(body, r"System time \(seconds\):\s*([0-9.]+)$", "system time"),
            "cpu_percent": pattern(body, r"Percent of CPU this job got:\s*([0-9]+)%$", "CPU percent"),
            "max_rss_kb": pattern(body, r"Maximum resident set size \(kbytes\):\s*([0-9]+)$", "RSS"),
            "major_page_faults": pattern(body, r"Major \(requiring I/O\) page faults:\s*([0-9]+)$", "major faults"),
            "minor_page_faults": pattern(body, r"Minor \(reclaiming a frame\) page faults:\s*([0-9]+)$", "minor faults"),
            "voluntary_context_switches": pattern(body, r"Voluntary context switches:\s*([0-9]+)$", "voluntary context switches"),
            "involuntary_context_switches": pattern(body, r"Involuntary context switches:\s*([0-9]+)$", "involuntary context switches"),
            "user_cycles": counters["cycles:u"],
            "user_instructions": counters["instructions:u"],
            "user_cache_misses": counters["cache-misses:u"],
        })
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content = build()
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != content:
            raise ValueError("Profile summary differs from new raw/log evidence")
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(content, encoding="utf-8", newline="")
    print("PASS: two noncompliant diagnostic profiles match raw, text, and logs")


if __name__ == "__main__":
    main()
