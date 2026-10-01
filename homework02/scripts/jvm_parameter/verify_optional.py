#!/usr/bin/env python3
"""Independent completeness and protocol audit for the optional heap study."""

import csv
import hashlib
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / "analysis" / "jvm_parameter"
LOGS = ROOT / "logs" / "jvm_parameter"
HEAP_FLAGS = {
    "default": "",
    "xmx512m": "-Xmx512m",
    "xmx1024m": "-Xmx1024m",
    "xmx2560m": "-Xmx2560m",
}
WORKLOADS = ("compress", "derby", "sunflow", "scimark.fft.large")
EXPECTED_FORMAL_RAW_SHA256 = "4ae651e312061d09760743ab9908129b633e9ce1e5b5b296c13d4a30605e05ad"
EXPECTED_HISTORICAL_SHA256 = {
    "SPECjvm2008.013": "a17e5f9977dc27895b12ccac7be95f9cc9d99c128cbf052e32f30f9ebf856c30",
    "SPECjvm2008.014": "ea805af7f0f141160b18f580d273b8772c51230dbdfd5c89502f68eab3e3cf52",
}


def read(name):
    with (ANALYSIS / name).open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    formal = ROOT / "specjvm2008" / "results" / "SPECjvm2008.007" / "SPECjvm2008.007.raw"
    require(hashlib.sha256(formal.read_bytes()).hexdigest() == EXPECTED_FORMAL_RAW_SHA256,
            "Formal .007 raw has changed")
    for result_id, digest in EXPECTED_HISTORICAL_SHA256.items():
        old_raw = ROOT / "specjvm2008" / "results" / result_id / f"{result_id}.raw"
        require(hashlib.sha256(old_raw.read_bytes()).hexdigest() == digest,
                f"Historical {result_id} raw has changed")
    rows = read("heap_parameter_results.csv")
    summaries = read("heap_parameter_summary.csv")
    events = read("gc_events.csv")
    require(len(rows) == 48, f"Expected 48 attempts, found {len(rows)}")
    require(len(summaries) == 16, f"Expected 16 configuration summaries, found {len(summaries)}")
    keys = [r["run_key"] for r in rows]
    require(len(set(keys)) == 48, "Repeated run key")
    result_ids = [r["result_id"] for r in rows if r["result_id"]]
    require(len(set(result_ids)) == len(result_ids), "Result ID reused by two attempts")
    require("SPECjvm2008.007" not in result_ids, "Formal result included in optional experiment")
    event_counts = {}
    event_times = {}
    event_capacities = {}
    for event in events:
        key = event["run_key"]
        require(key in keys, f"GC event with unknown run key: {key}")
        event_counts[key] = event_counts.get(key, 0) + 1
        event_times[key] = event_times.get(key, 0) + float(event["pause_s"])
        event_capacities[key] = max(event_capacities.get(key, 0), int(event["heap_capacity_kib"]))
    status_counts = {"valid": 0, "invalid": 0}
    for row in rows:
        key = row["run_key"]
        status = row["status"]
        require(status in status_counts, f"Unattempted or unexpected status: {key}: {status}")
        status_counts[status] += 1
        heap = row["heap_config"]
        require(heap in HEAP_FLAGS and row["workload"] in WORKLOADS, f"Unexpected factor level: {key}")
        require(row["run_id"] in ("Run1", "Run2", "Run3"), f"Unexpected repetition: {key}")
        cmd = row["command"]
        required = ("-XX:+PrintGCDetails", "-XX:+PrintGCTimeStamps", "-Xloggc:",
                    " -jar SPECjvm2008.jar --base -bt 16 " + row["workload"])
        require(all(part in cmd for part in required), f"Protocol option missing: {key}")
        require("--peak" not in cmd and " -wt " not in cmd and " -it " not in cmd,
                f"Unexpected SPEC mode or duration override: {key}")
        used_heaps = re.findall(r"-Xmx\S+", cmd)
        require(used_heaps == ([HEAP_FLAGS[heap]] if HEAP_FLAGS[heap] else []),
                f"Wrong -Xmx factor in command: {key}")
        require((ROOT / row["run_log_path"]).is_file(), f"Missing console log: {key}")
        require((ROOT / row["gc_log_path"]).is_file(), f"Missing GC log: {key}")
        require((LOGS / heap / f"{key}.meta").is_file(), f"Missing run metadata: {key}")
        if row["gc_count"]:
            require(int(row["gc_count"]) == event_counts.get(key, 0), f"GC count mismatch: {key}")
            require(abs(float(row["gc_time_s"]) - event_times.get(key, 0)) < 1e-5,
                    f"GC time mismatch: {key}")
            if event_counts.get(key, 0):
                require(abs(float(row["gc_max_logged_heap_capacity_mib"]) -
                            event_capacities[key] / 1024) < .001,
                        f"Logged heap capacity mismatch: {key}")
        if status == "valid":
            require(not row["invalid_reason"] and row["score_ops_per_min"] and row["warmup_ops_per_min"],
                    f"Valid run lacks score: {key}")
            require((ROOT / row["raw_path"]).is_file() and (ROOT / row["txt_path"]).is_file(),
                    f"Valid run lacks raw or TXT: {key}")
            require(float(row["runtime_s"]) == 240 and float(row["warmup_runtime_s"]) == 120,
                    f"Unexpected benchmark duration: {key}")
        else:
            require(row["invalid_reason"], f"Invalid run lacks explanation: {key}")
    for workload in WORKLOADS:
        for heap in HEAP_FLAGS:
            cell = [r for r in rows if r["workload"] == workload and r["heap_config"] == heap]
            require(len(cell) == 3 and {r["run_id"] for r in cell} == {"Run1", "Run2", "Run3"},
                    f"Incomplete repetition cell: {workload}/{heap}")
    report = (ROOT / "README.md").read_text(encoding="utf-8")
    require("## Optional: JVM Parameter Optimization" in report,
            "Optional README section not yet integrated")
    require("421.24" in report and "SPECjvm2008.007" in report,
            "Mandatory Base result not visibly retained in README")
    for name in ("heap_vs_score.png", "heap_vs_gc_time.png", "heap_vs_score_change.png"):
        require((ROOT / "images" / "jvm_parameter" / name).is_file(), f"Missing plot: {name}")
    print(f"PASS: 48 attempts ({status_counts['valid']} valid, {status_counts['invalid']} invalid), "
          f"{len(result_ids)} unique optional SPEC result IDs, {len(events)} GC events, formal .007 intact")


if __name__ == "__main__":
    main()
