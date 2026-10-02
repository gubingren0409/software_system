#!/usr/bin/env python3
"""Independent integrity checks for the optional-study enhancement."""

import csv
import hashlib
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / "analysis" / "jvm_parameter"
EXPECTED_FORMAL_RAW_SHA256 = "4ae651e312061d09760743ab9908129b633e9ce1e5b5b296c13d4a30605e05ad"
EXPECTED_MAX = {
    "default": 1977614336,
    "xmx512m": 536870912,
    "xmx1024m": 1073741824,
    "xmx2560m": 2684354560,
}


def read(name):
    with (ANALYSIS / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def close(a, b, tolerance=1e-6):
    return abs(float(a) - float(b)) <= tolerance


def main():
    formal = ROOT / "specjvm2008" / "results" / "SPECjvm2008.007" / "SPECjvm2008.007.raw"
    require(hashlib.sha256(formal.read_bytes()).hexdigest() == EXPECTED_FORMAL_RAW_SHA256,
            "Formal .007 raw has changed")

    old_events = read("gc_events.csv")
    memory = read("gc_memory_behavior.csv")
    require(len(memory) == len(old_events) == 118230, "GC event count changed or enhancement is incomplete")
    old_by_key = {(r["run_key"], r["event_index"]): r for r in old_events}
    for row in memory:
        source = old_by_key[(row["run_key"], row["event_index"])]
        before = float(source["heap_before_kib"]) / 1024
        after = float(source["heap_after_kib"]) / 1024
        logged = float(source["heap_capacity_kib"]) / 1024
        require(close(row["before_used_mib"], before), "before-used calculation mismatch")
        require(close(row["after_used_mib"], after), "after-used calculation mismatch")
        require(close(row["logged_capacity_mib"], logged), "logged-capacity calculation mismatch")
        require(close(row["after_logged_capacity_percent"], after / logged * 100),
                "post-GC committed-capacity utilization mismatch")
        require(close(row["reclaimed_mib"], before - after), "reclaimed-memory calculation mismatch")
        require(0 <= float(row["after_max_heap_percent"]) <= 100.001,
                "post-GC use exceeds configured maximum heap")

    phases = Counter(row["phase_estimate"] for row in memory)
    require(phases["measurement"] == 51217, "Measurement phase count changed")
    require(phases["boundary_uncertain"] == 1575, "Boundary uncertainty count changed")
    require(phases["unavailable_invalid_run"] == 38605, "Invalid-run phase handling changed")

    boundaries = read("gc_phase_boundaries.csv")
    require(len(boundaries) == 48, "Expected one boundary record per planned attempt")
    require(sum(r["phase_availability"] == "estimated_for_complete_valid_run" for r in boundaries) == 39,
            "Expected 39 phase-aligned valid attempts")
    require(sum(r["phase_availability"] == "unavailable_incomplete_invalid_run" for r in boundaries) == 9,
            "Expected 9 incomplete invalid attempts")

    summary = read("gc_measurement_summary.csv")
    require(len(summary) == 16, "Expected 16 workload/configuration summaries")
    derby = {(r["heap_config"]): r for r in summary if r["workload"] == "derby"}
    require(derby["xmx512m"]["valid_n"] == "0" and not derby["xmx512m"]["mean_score_ops_per_min"],
            "Derby 512 MiB failure was converted into a score")
    require(close(derby["xmx1024m"]["mean_measurement_full_gc_count"], 1861.667, .001),
            "Derby 1024 MiB Full GC mean changed")
    require(close(derby["xmx1024m"]["score_change_vs_default_percent"], -68.547, .001),
            "Derby effect size changed")

    flags = read("jvm_flag_snapshot.csv")
    require(len(flags) == 4, "Expected four flag snapshots")
    for row in flags:
        heap = row["heap_config"]
        require(int(row["max_heap_size_bytes"]) == EXPECTED_MAX[heap], f"Wrong MaxHeapSize: {heap}")
        require(row["use_parallel_gc"] == row["use_parallel_old_gc"] ==
                row["use_adaptive_size_policy"] == "true", f"Collector flags changed: {heap}")
        raw = ROOT / row["raw_log_path"]
        require(raw.is_file() and "SPECjvm2008.jar" not in raw.read_text(encoding="utf-8"),
                f"Flag snapshot is missing or mixed with a benchmark: {heap}")

    for name in ("heap_vs_gc_frequency.png", "derby_case_study.png"):
        require((ROOT / "images" / "jvm_parameter" / name).is_file(), f"Missing figure: {name}")
    for name in ("enhancement_audit.md", "heap_pressure_analysis.md", "derby_case_study.md"):
        require((ANALYSIS / name).is_file(), f"Missing analysis: {name}")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for heading in ("### Motivation", "### Experimental Design", "### Results",
                    "### JVM Behavior Analysis", "### Workload Case Study",
                    "### Limitations", "### Conclusion"):
        require(heading in readme, f"Optional README subsection missing: {heading}")
    require("SPECjvm2008.007" in readme and "421.24" in readme,
            "Formal Base identity was not retained")
    print("PASS: enhancement evidence verified; 118230 events, 51217 measurement events, "
          "four flag snapshots, formal .007 intact")


if __name__ == "__main__":
    main()
