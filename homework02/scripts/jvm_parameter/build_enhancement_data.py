#!/usr/bin/env python3
"""Derive heap-occupancy, phase-estimate, and JVM-flag evidence.

The script reads preserved optional-study CSVs, SPEC raw files, GC logs already
parsed into gc_events.csv, and non-benchmark PrintFlagsFinal snapshots. It does
not run SPEC or alter any result directory.
"""

import argparse
import csv
import io
import re
import statistics
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / "analysis" / "jvm_parameter"
FLAG_LOGS = ROOT / "logs" / "jvm_parameter" / "flags"
HEAPS = ("default", "xmx512m", "xmx1024m", "xmx2560m")
ALIGNMENT_UNCERTAINTY_S = Decimal("1.000")

MEMORY_FIELDS = (
    "workload", "heap_config", "run_id", "run_key", "status", "result_id",
    "event_index", "gc_type", "uptime_s", "pause_s", "phase_estimate",
    "phase_alignment_uncertainty_s", "before_used_mib", "after_used_mib",
    "logged_capacity_mib", "max_heap_mib", "before_max_heap_percent",
    "after_max_heap_percent", "after_logged_capacity_percent", "reclaimed_mib",
    "source_line",
)
BOUNDARY_FIELDS = (
    "workload", "heap_config", "run_id", "run_key", "status", "result_id",
    "raw_run_start_epoch_ms", "metadata_start_epoch_ms",
    "raw_start_minus_metadata_start_s", "warmup_start_epoch_ms",
    "warmup_end_epoch_ms", "measurement_start_epoch_ms",
    "measurement_end_epoch_ms", "phase_alignment_method",
    "phase_alignment_uncertainty_s", "phase_availability",
)
MEASUREMENT_FIELDS = (
    "workload", "heap_config", "planned_n", "valid_n", "invalid_n",
    "mean_score_ops_per_min", "score_sample_sd", "score_cv_percent",
    "score_change_vs_default_percent", "mean_measurement_gc_count",
    "mean_measurement_full_gc_count", "mean_measurement_gc_pause_s",
    "mean_measurement_pre_gc_max_heap_percent",
    "mean_measurement_post_gc_max_heap_percent",
    "boundary_uncertain_events_total", "phase_alignment_method",
)
FLAG_FIELDS = (
    "heap_config", "xmx_argument", "collected_at", "java_path",
    "max_heap_size_bytes", "initial_heap_size_bytes", "new_ratio",
    "survivor_ratio", "use_parallel_gc", "use_parallel_old_gc",
    "use_adaptive_size_policy", "raw_log_path",
)


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def csv_text(fields, rows):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def raw_phase_boundaries(attempt):
    if attempt["status"] != "valid":
        return None
    raw = ROOT / attempt["raw_path"]
    root = ET.parse(raw).getroot()
    benchmark = next(
        node for node in root.findall("./benchmark-results/benchmark-result")
        if node.attrib.get("name") == attempt["workload"]
    )
    warmup = benchmark.find("./warmup-result/iteration-result")
    measured = benchmark.find("./iterations/iteration-result")
    if warmup is None or measured is None:
        raise ValueError(f"Missing complete phase boundaries: {attempt['run_key']}")
    run_date = root.findtext("./run-info/spec.jvm2008.report.run.date")
    match = re.fullmatch(r"\w{3} (\w{3}) (\d{2}) (\d{2}:\d{2}:\d{2}) CST (\d{4})", run_date or "")
    if not match:
        raise ValueError(f"Unparseable SPEC run date: {attempt['run_key']}: {run_date}")
    raw_start = datetime.strptime(
        f"{match.group(1)} {match.group(2)} {match.group(3)} {match.group(4)}",
        "%b %d %H:%M:%S %Y",
    ).replace(tzinfo=timezone(timedelta(hours=8)))
    metadata_start = datetime.fromisoformat(attempt["start_time"])
    delta_s = (raw_start - metadata_start).total_seconds()
    if delta_s < 0 or delta_s > 2:
        raise ValueError(f"SPEC/meta start alignment exceeds two seconds: {attempt['run_key']}: {delta_s}")
    return {
        "raw_run_start_epoch_ms": int(raw_start.timestamp() * 1000),
        "metadata_start_epoch_ms": int(metadata_start.timestamp() * 1000),
        "raw_start_minus_metadata_start_s": f"{delta_s:.3f}",
        "warmup_start_epoch_ms": int(warmup.attrib["startTime"]),
        "warmup_end_epoch_ms": int(warmup.attrib["endTime"]),
        "measurement_start_epoch_ms": int(measured.attrib["startTime"]),
        "measurement_end_epoch_ms": int(measured.attrib["endTime"]),
    }


def classify_phase(event_start_ms, event_end_ms, boundary):
    uncertainty_ms = int(ALIGNMENT_UNCERTAINTY_S * 1000)
    lower = event_start_ms - uncertainty_ms
    upper = event_end_ms + uncertainty_ms
    warmup_start = boundary["warmup_start_epoch_ms"]
    warmup_end = boundary["warmup_end_epoch_ms"]
    measure_start = boundary["measurement_start_epoch_ms"]
    measure_end = boundary["measurement_end_epoch_ms"]
    if upper < warmup_start:
        return "pre_warmup"
    if lower >= warmup_start and upper <= warmup_end:
        return "warmup"
    if lower > warmup_end and upper < measure_start:
        return "between_warmup_and_measurement"
    if lower >= measure_start and upper <= measure_end:
        return "measurement"
    if lower > measure_end:
        return "post_measurement"
    return "boundary_uncertain"


def memory_rows(attempts, events):
    by_key = {row["run_key"]: row for row in attempts}
    boundaries = {key: raw_phase_boundaries(row) for key, row in by_key.items()}
    output = []
    for event in events:
        attempt = by_key[event["run_key"]]
        before = Decimal(event["heap_before_kib"]) / Decimal(1024)
        after = Decimal(event["heap_after_kib"]) / Decimal(1024)
        logged_capacity = Decimal(event["heap_capacity_kib"]) / Decimal(1024)
        max_heap = Decimal(attempt["max_heap_bytes"]) / Decimal(1024 * 1024)
        phase = "unavailable_invalid_run"
        boundary = boundaries[event["run_key"]]
        if boundary:
            event_start_ms = boundary["raw_run_start_epoch_ms"] + int(Decimal(event["uptime_s"]) * 1000)
            event_end_ms = event_start_ms + int(Decimal(event["pause_s"]) * 1000)
            phase = classify_phase(event_start_ms, event_end_ms, boundary)
        output.append({
            "workload": attempt["workload"],
            "heap_config": attempt["heap_config"],
            "run_id": attempt["run_id"],
            "run_key": event["run_key"],
            "status": attempt["status"],
            "result_id": attempt["result_id"],
            "event_index": event["event_index"],
            "gc_type": event["event_type"],
            "uptime_s": event["uptime_s"],
            "pause_s": event["pause_s"],
            "phase_estimate": phase,
            "phase_alignment_uncertainty_s": str(ALIGNMENT_UNCERTAINTY_S) if boundary else "",
            "before_used_mib": f"{before:.6f}",
            "after_used_mib": f"{after:.6f}",
            "logged_capacity_mib": f"{logged_capacity:.6f}",
            "max_heap_mib": f"{max_heap:.6f}",
            "before_max_heap_percent": f"{before / max_heap * 100:.6f}",
            "after_max_heap_percent": f"{after / max_heap * 100:.6f}",
            # HotSpot 7's total-heap tuple can report a post-GC resized capacity;
            # therefore only the post-GC used/capacity ratio is presented.
            "after_logged_capacity_percent": f"{after / logged_capacity * 100:.6f}",
            "reclaimed_mib": f"{before - after:.6f}",
            "source_line": event["source_line"],
        })
    return output, boundaries


def boundary_rows(attempts, boundaries):
    output = []
    for attempt in attempts:
        boundary = boundaries[attempt["run_key"]]
        row = {field: "" for field in BOUNDARY_FIELDS}
        row.update({field: attempt[field] for field in
                    ("workload", "heap_config", "run_id", "run_key", "status", "result_id")})
        if boundary:
            row.update(boundary)
            row.update(
                phase_alignment_method="SPEC raw run-date second + GC uptime; 1 s conservative boundary",
                phase_alignment_uncertainty_s=str(ALIGNMENT_UNCERTAINTY_S),
                phase_availability="estimated_for_complete_valid_run",
            )
        else:
            row["phase_availability"] = "unavailable_incomplete_invalid_run"
        output.append(row)
    return output


def fmt(value, digits=3):
    return f"{value:.{digits}f}" if value is not None else ""


def measurement_summary(attempts, memory):
    by_run = {}
    uncertain = {}
    for row in memory:
        key = row["run_key"]
        if row["phase_estimate"] == "measurement":
            by_run.setdefault(key, []).append(row)
        elif row["phase_estimate"] == "boundary_uncertain":
            uncertain[key] = uncertain.get(key, 0) + 1
    output = []
    for workload in ("compress", "derby", "sunflow", "scimark.fft.large"):
        groups = {heap: [r for r in attempts if r["workload"] == workload and r["heap_config"] == heap]
                  for heap in HEAPS}
        default_scores = [float(r["score_ops_per_min"]) for r in groups["default"] if r["status"] == "valid"]
        default_mean = statistics.mean(default_scores)
        for heap in HEAPS:
            valid = [r for r in groups[heap] if r["status"] == "valid"]
            scores = [float(r["score_ops_per_min"]) for r in valid]
            per_run = []
            for attempt in valid:
                events = by_run.get(attempt["run_key"], [])
                per_run.append({
                    "count": len(events),
                    "full": sum(e["gc_type"] == "full" for e in events),
                    "pause": sum(float(e["pause_s"]) for e in events),
                    "before": statistics.mean(float(e["before_max_heap_percent"]) for e in events)
                        if events else None,
                    "after": statistics.mean(float(e["after_max_heap_percent"]) for e in events)
                        if events else None,
                })
            sd = statistics.stdev(scores) if len(scores) > 1 else None
            output.append({
                "workload": workload,
                "heap_config": heap,
                "planned_n": len(groups[heap]),
                "valid_n": len(valid),
                "invalid_n": len(groups[heap]) - len(valid),
                "mean_score_ops_per_min": fmt(statistics.mean(scores) if scores else None),
                "score_sample_sd": fmt(sd),
                "score_cv_percent": fmt(sd / statistics.mean(scores) * 100) if sd is not None else "",
                "score_change_vs_default_percent": fmt((statistics.mean(scores) / default_mean - 1) * 100)
                    if scores else "",
                "mean_measurement_gc_count": fmt(statistics.mean(x["count"] for x in per_run))
                    if per_run else "",
                "mean_measurement_full_gc_count": fmt(statistics.mean(x["full"] for x in per_run))
                    if per_run else "",
                "mean_measurement_gc_pause_s": fmt(statistics.mean(x["pause"] for x in per_run), 6)
                    if per_run else "",
                "mean_measurement_pre_gc_max_heap_percent": fmt(
                    statistics.mean(x["before"] for x in per_run if x["before"] is not None), 3)
                    if any(x["before"] is not None for x in per_run) else "",
                "mean_measurement_post_gc_max_heap_percent": fmt(
                    statistics.mean(x["after"] for x in per_run if x["after"] is not None), 3)
                    if any(x["after"] is not None for x in per_run) else "",
                "boundary_uncertain_events_total": sum(uncertain.get(r["run_key"], 0) for r in valid),
                "phase_alignment_method": "estimated; ±1 s boundary excluded" if valid else "",
            })
    return output


def flag_snapshot_rows():
    output = []
    wanted = {
        "MaxHeapSize": "max_heap_size_bytes",
        "InitialHeapSize": "initial_heap_size_bytes",
        "NewRatio": "new_ratio",
        "SurvivorRatio": "survivor_ratio",
        "UseParallelGC": "use_parallel_gc",
        "UseParallelOldGC": "use_parallel_old_gc",
        "UseAdaptiveSizePolicy": "use_adaptive_size_policy",
    }
    for heap in HEAPS:
        path = FLAG_LOGS / f"{heap}.flags.log"
        text = path.read_text(encoding="utf-8")
        metadata = {}
        for line in text.splitlines()[:5]:
            key, sep, value = line.partition("=")
            if sep:
                metadata[key] = value
        flags = {}
        for name, value in re.findall(r"^\s*(?:u?intx|bool)\s+(\w+)\s+(?::=|=)\s+(\S+)", text, re.M):
            if name in wanted:
                flags[name] = value
        missing = set(wanted) - set(flags)
        if missing:
            raise ValueError(f"Missing flags in {path}: {sorted(missing)}")
        row = {field: "" for field in FLAG_FIELDS}
        row.update(
            heap_config=heap,
            xmx_argument=metadata.get("xmx_argument", ""),
            collected_at=metadata.get("collected_at", ""),
            java_path=metadata.get("java_path", ""),
            raw_log_path=path.relative_to(ROOT).as_posix(),
        )
        row.update({target: flags[source] for source, target in wanted.items()})
        output.append(row)
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    attempts = read_csv(ANALYSIS / "heap_parameter_results.csv")
    events = read_csv(ANALYSIS / "gc_events.csv")
    if len(attempts) != 48 or len({row["run_key"] for row in attempts}) != 48:
        raise ValueError("Expected 48 unique optional attempts")
    memory, boundaries = memory_rows(attempts, events)
    tables = (
        (ANALYSIS / "gc_memory_behavior.csv", MEMORY_FIELDS, memory),
        (ANALYSIS / "gc_phase_boundaries.csv", BOUNDARY_FIELDS, boundary_rows(attempts, boundaries)),
        (ANALYSIS / "gc_measurement_summary.csv", MEASUREMENT_FIELDS,
         measurement_summary(attempts, memory)),
        (ANALYSIS / "jvm_flag_snapshot.csv", FLAG_FIELDS, flag_snapshot_rows()),
    )
    for path, fields, rows in tables:
        content = csv_text(fields, rows)
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                raise ValueError(f"Derived CSV differs from evidence: {path}")
        else:
            path.write_text(content, encoding="utf-8", newline="")
    phase_counts = {}
    for row in memory:
        phase_counts[row["phase_estimate"]] = phase_counts.get(row["phase_estimate"], 0) + 1
    print(f"PASS: {len(memory)} GC memory rows; phases={phase_counts}; four JVM flag snapshots")


if __name__ == "__main__":
    main()
