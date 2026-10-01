#!/usr/bin/env python3
"""Derive optional heap-study tables from each independent SPEC raw/TXT and GC log.

No score is accepted from a controller summary or typed into a table. Invalid
attempts remain in the per-attempt CSV with blank numerical performance fields.
"""

import argparse
import csv
import io
import re
import statistics
import xml.etree.ElementTree as ET
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOGS = ROOT / "logs" / "jvm_parameter"
RESULTS = ROOT / "specjvm2008" / "results"
OUTPUT = ROOT / "analysis" / "jvm_parameter"
WORKLOADS = ("compress", "derby", "sunflow", "scimark.fft.large")
HEAPS = ("default", "xmx512m", "xmx1024m", "xmx2560m")
GC_EVENT = re.compile(r"^\s*(\d+(?:\.\d+)?):\s+\[(Full GC|GC)\b")
GC_PAUSE = re.compile(r",\s*(\d+(?:\.\d+)?) secs\]")
GC_HEAP = re.compile(r"\]\s+(\d+)K->(\d+)K\((\d+)K\)(?=,|\s+\[PSPermGen)")
SCORE_LINE = re.compile(r"^Score on ([\w.]+): (\d+(?:\.\d+)?) ops/m$", re.M)
DETAIL_LINE = re.compile(
    r"^([\w.]+)\s+(warmup|iteration 1)\s+(?:\d+|null)\s+\d+\s+"
    r"\d+(?:\.\d+)?\s+(\d+(?:\.\d+)?)\s*$", re.M,
)
ATTEMPT_FIELDS = (
    "workload", "heap_config", "run_id", "run_key", "status", "invalid_reason",
    "result_id", "score_ops_per_min", "warmup_ops_per_min", "runtime_s",
    "warmup_runtime_s", "attempt_wall_s", "gc_count", "gc_young_count",
    "gc_full_count", "gc_time_s", "gc_max_logged_heap_capacity_mib",
    "gc_scope", "gc_parse_error", "java_exit_status",
    "reporter_exit_status", "start_time", "end_time", "max_heap_bytes",
    "raw_path", "txt_path", "run_log_path", "gc_log_path", "command",
)
SUMMARY_FIELDS = (
    "workload", "heap_config", "planned_n", "attempts", "valid_n", "invalid_n", "not_attempted_n",
    "mean_score_ops_per_min", "sample_std_score_ops_per_min", "cv_score_percent",
    "mean_gc_time_s", "sample_std_gc_time_s", "cv_gc_time_percent",
    "mean_gc_count", "mean_gc_max_logged_heap_capacity_mib",
    "score_change_vs_default_percent",
)
EVENT_FIELDS = (
    "run_key", "event_index", "uptime_s", "event_type", "pause_s",
    "heap_before_kib", "heap_after_kib", "heap_capacity_kib", "source_line",
)


def expected_attempts():
    for workload in WORKLOADS:
        for repetition in (1, 2, 3):
            for heap in HEAPS:
                key = f"{workload.replace('.', '_')}__{heap}__r{repetition}"
                yield workload, heap, repetition, key


def rel(path):
    return path.relative_to(ROOT).as_posix() if path and path.is_file() else ""


def metadata(path):
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.partition("=")
        if not sep or key in result:
            raise ValueError(f"Malformed metadata: {path}: {line}")
        result[key] = value
    return result


def decimal_2(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def iteration_data(element):
    if element is None:
        raise ValueError("Missing iteration in SPEC raw result")
    duration_ms = int(element.attrib["endTime"]) - int(element.attrib["startTime"])
    if duration_ms <= 0:
        raise ValueError("Nonpositive SPEC iteration duration")
    score = Decimal(element.attrib["operations"]) * 60000 / duration_ms
    return duration_ms, score


def spec_result(result_id, workload, log_text):
    if not re.fullmatch(r"SPECjvm2008\.\d{3}", result_id):
        raise ValueError(f"Unsafe or malformed SPEC result ID: {result_id}")
    raw = RESULTS / result_id / f"{result_id}.raw"
    txt = RESULTS / result_id / f"{result_id}.txt"
    if not raw.is_file() or not txt.is_file():
        raise ValueError("Missing raw or reporter TXT")
    root = ET.parse(raw).getroot()
    if root.findtext("workload") != "SPECjvm2008 Base":
        raise ValueError("SPEC raw is not in Base mode")
    if root.findtext("suite-build-version") != "SPECjvm2008 1.01 (20090519)":
        raise ValueError("Unexpected SPEC kit version")
    if [x.text for x in root.findall("./configs/config")] != ["specjvm.benchmark.threads=16"]:
        raise ValueError("Unexpected SPEC benchmark thread configuration")
    benchmarks = root.findall("./benchmark-results/benchmark-result")
    names = [x.attrib.get("name") for x in benchmarks]
    if names != ["check", workload]:
        raise ValueError(f"Unexpected raw workload sequence: {names}")
    check = benchmarks[0].find("./iterations/iteration-result")
    if check is None or Decimal(check.attrib.get("operations", "0")) != 1:
        raise ValueError("SPEC check result is absent or failed")
    benchmark = benchmarks[1]
    if benchmark.attrib.get("numberBmThreads") != "16":
        raise ValueError("Benchmark thread count differs from 16")
    if benchmark.attrib.get("warmupTime") != "120000" or benchmark.attrib.get("iterationTime") != "240s":
        raise ValueError("Warmup or measured duration configuration differs")
    iterations = benchmark.findall("./iterations/iteration-result")
    if len(iterations) != 1:
        raise ValueError("Expected one measured iteration")
    warmup_duration, warmup_raw_score = iteration_data(benchmark.find("./warmup-result/iteration-result"))
    measured_duration, measured_raw_score = iteration_data(iterations[0])
    if warmup_duration != 120000 or measured_duration != 240000:
        raise ValueError("Actual warmup or measurement duration is incomplete")

    report = txt.read_text(encoding="latin-1")
    if "Run is valid, but not compliant" not in report or "NOT VALID" in report:
        raise ValueError("Reporter did not confirm a valid noncompliant partial Base run")
    details = {(name, phase): Decimal(score) for name, phase, score in DETAIL_LINE.findall(report)}
    if set(details) != {(workload, "warmup"), (workload, "iteration 1")}:
        raise ValueError("Reporter workload details are absent or mixed")
    if abs(details[workload, "warmup"] - decimal_2(warmup_raw_score)) > Decimal("0.01"):
        raise ValueError("Reporter warmup score differs from raw")
    if abs(details[workload, "iteration 1"] - decimal_2(measured_raw_score)) > Decimal("0.01"):
        raise ValueError("Reporter measured score differs from raw")
    log_scores = [(name, Decimal(score)) for name, score in SCORE_LINE.findall(log_text)]
    if len(log_scores) != 1 or log_scores[0] != (workload, details[workload, "iteration 1"]):
        raise ValueError("Console score differs from SPEC reporter score")
    if "OutOfMemoryError" in log_text or "NOT VALID" in log_text:
        raise ValueError("OOM or invalid marker in console log")
    return {
        "score_ops_per_min": str(details[workload, "iteration 1"]),
        "warmup_ops_per_min": str(details[workload, "warmup"]),
        "runtime_s": f"{measured_duration / 1000:.3f}",
        "warmup_runtime_s": f"{warmup_duration / 1000:.3f}",
        "raw_path": rel(raw),
        "txt_path": rel(txt),
    }


def gc_events(path, run_key):
    if not path.is_file():
        return [], "GC log missing"
    events = []
    for line_number, line in enumerate(path.read_text(encoding="latin-1", errors="replace").splitlines(), 1):
        match = GC_EVENT.match(line)
        if not match:
            continue
        pauses = GC_PAUSE.findall(line)
        if not pauses:
            return events, f"GC event at line {line_number} has no parseable pause"
        pause = Decimal(pauses[-1])
        heap = GC_HEAP.findall(line)
        if len(heap) != 1:
            return events, f"GC event at line {line_number} has no unique total-heap reading"
        events.append({
            "run_key": run_key,
            "event_index": len(events) + 1,
            "uptime_s": match.group(1),
            "event_type": "full" if match.group(2) == "Full GC" else "young",
            "pause_s": str(pause),
            "heap_before_kib": heap[0][0],
            "heap_after_kib": heap[0][1],
            "heap_capacity_kib": heap[0][2],
            "source_line": line_number,
        })
    return events, ""


def process_seconds(start, end):
    if not start or not end:
        return ""
    return f"{(datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds():.3f}"


def attempt(workload, heap, repetition, key):
    meta_path = LOGS / heap / f"{key}.meta"
    log_path = LOGS / heap / f"{key}.log"
    gc_path = LOGS / "gc" / f"{key}.gc.log"
    row = dict.fromkeys(ATTEMPT_FIELDS, "")
    row.update(workload=workload, heap_config=heap, run_id=f"Run{repetition}", run_key=key,
               status="not_attempted", gc_scope="whole_java_process",
               run_log_path=rel(log_path), gc_log_path=rel(gc_path))
    if not meta_path.is_file():
        row["invalid_reason"] = "No completed attempt metadata"
        return row, []
    meta = metadata(meta_path)
    for field, expected in (("run_key", key), ("workload", workload),
                            ("heap_config", heap), ("repetition", str(repetition))):
        if meta.get(field) != expected:
            raise ValueError(f"Metadata mismatch: {meta_path}: {field}")
    row.update(status="invalid", result_id=meta.get("result_id", ""),
               java_exit_status=meta.get("java_exit_status", ""),
               reporter_exit_status=meta.get("reporter_exit_status", ""),
               start_time=meta.get("start_time", ""), end_time=meta.get("end_time", ""),
               command=meta.get("command", ""))
    row["attempt_wall_s"] = process_seconds(row["start_time"], row["end_time"])
    if not log_path.is_file():
        row["invalid_reason"] = "Console log missing"
        return row, []
    log_text = log_path.read_text(encoding="latin-1", errors="replace")
    flag = re.search(r"^\s*uintx MaxHeapSize\s*:=?\s*(\d+)\s+\{product\}", log_text, re.M)
    if flag:
        row["max_heap_bytes"] = flag.group(1)
    events, gc_error = gc_events(gc_path, key)
    row["gc_parse_error"] = gc_error
    if events and not gc_error:
        row["gc_count"] = str(len(events))
        row["gc_young_count"] = str(sum(x["event_type"] == "young" for x in events))
        row["gc_full_count"] = str(sum(x["event_type"] == "full" for x in events))
        row["gc_time_s"] = f"{sum(Decimal(x['pause_s']) for x in events):.7f}"
        row["gc_max_logged_heap_capacity_mib"] = f"{max(int(x['heap_capacity_kib']) for x in events) / 1024:.3f}"
    elif gc_path.is_file() and not gc_error:
        row.update(gc_count="0", gc_young_count="0", gc_full_count="0", gc_time_s="0.0000000")
    if not row["result_id"]:
        row["invalid_reason"] = "No new SPEC result directory"
        return row, events
    raw_candidate = RESULTS / row["result_id"] / f"{row['result_id']}.raw"
    txt_candidate = RESULTS / row["result_id"] / f"{row['result_id']}.txt"
    row["raw_path"] = rel(raw_candidate)
    row["txt_path"] = rel(txt_candidate)
    if "OutOfMemoryError" in log_text:
        row["invalid_reason"] = "OutOfMemoryError during incomplete warmup; no measured score"
        return row, events
    if row["java_exit_status"] == "124":
        row["invalid_reason"] = "900-second watchdog expired during incomplete run; no measured score"
        return row, events
    try:
        scores = spec_result(row["result_id"], workload, log_text)
    except (ValueError, ET.ParseError, KeyError, OSError) as exc:
        row["invalid_reason"] = str(exc)
        return row, events
    row.update(scores)
    row["status"] = "valid"
    return row, events


def fmt(value, digits=3):
    return f"{value:.{digits}f}" if value is not None else ""


def summary(rows):
    output = []
    for workload in WORKLOADS:
        groups = {heap: [r for r in rows if r["workload"] == workload and r["heap_config"] == heap]
                  for heap in HEAPS}
        default_scores = [float(r["score_ops_per_min"]) for r in groups["default"] if r["status"] == "valid"]
        default_mean = statistics.mean(default_scores) if default_scores else None
        for heap in HEAPS:
            valid = [r for r in groups[heap] if r["status"] == "valid"]
            observed = [r for r in groups[heap] if r["status"] != "not_attempted"]
            scores = [float(r["score_ops_per_min"]) for r in valid]
            gc_times = [float(r["gc_time_s"]) for r in valid if r["gc_time_s"]]
            gc_counts = [int(r["gc_count"]) for r in valid if r["gc_count"]]
            gc_capacities = [float(r["gc_max_logged_heap_capacity_mib"]) for r in valid
                             if r["gc_max_logged_heap_capacity_mib"]]
            mean_score = statistics.mean(scores) if scores else None
            sd_score = statistics.stdev(scores) if len(scores) > 1 else None
            mean_gc = statistics.mean(gc_times) if gc_times else None
            sd_gc = statistics.stdev(gc_times) if len(gc_times) > 1 else None
            output.append({
                "workload": workload, "heap_config": heap, "planned_n": len(groups[heap]),
                "attempts": len(observed), "valid_n": len(valid),
                "invalid_n": len(observed) - len(valid),
                "not_attempted_n": len(groups[heap]) - len(observed),
                "mean_score_ops_per_min": fmt(mean_score),
                "sample_std_score_ops_per_min": fmt(sd_score),
                "cv_score_percent": fmt(sd_score / mean_score * 100) if sd_score is not None and mean_score else "",
                "mean_gc_time_s": fmt(mean_gc, 6),
                "sample_std_gc_time_s": fmt(sd_gc, 6),
                "cv_gc_time_percent": fmt(sd_gc / mean_gc * 100) if sd_gc is not None and mean_gc else "",
                "mean_gc_count": fmt(statistics.mean(gc_counts), 3) if gc_counts else "",
                "mean_gc_max_logged_heap_capacity_mib": fmt(statistics.mean(gc_capacities))
                    if gc_capacities else "",
                "score_change_vs_default_percent": fmt((mean_score / default_mean - 1) * 100)
                    if mean_score is not None and default_mean else "",
            })
    return output


def csv_text(fields, rows):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Verify CSVs without writing")
    parser.add_argument("--allow-incomplete", action="store_true", help="Generate interim CSVs before 48 attempts")
    args = parser.parse_args()
    rows = []
    events = []
    for spec in expected_attempts():
        row, attempt_events = attempt(*spec)
        rows.append(row)
        events.extend(attempt_events)
    attempted = sum(row["status"] != "not_attempted" for row in rows)
    if attempted != 48 and not args.allow_incomplete:
        raise ValueError(f"Only {attempted}/48 attempts captured; use --allow-incomplete for a clearly interim table")
    if len({r["result_id"] for r in rows if r["result_id"]}) != sum(bool(r["result_id"]) for r in rows):
        raise ValueError("Two attempts reference the same SPEC result ID")
    tables = (
        (OUTPUT / "heap_parameter_results.csv", ATTEMPT_FIELDS, rows),
        (OUTPUT / "heap_parameter_summary.csv", SUMMARY_FIELDS, summary(rows)),
        (OUTPUT / "gc_events.csv", EVENT_FIELDS, events),
    )
    for path, fields, table in tables:
        content = csv_text(fields, table)
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                raise ValueError(f"Derived CSV differs from raw evidence: {path}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="")
    valid = sum(row["status"] == "valid" for row in rows)
    print(f"PASS: {attempted}/48 captured attempts; {valid} valid scores; {len(events)} GC events")


if __name__ == "__main__":
    main()
