#!/usr/bin/env python3
"""Rebuild A2 core tables from preserved SPEC raw results and check the reports."""

import argparse
import csv
import hashlib
import io
import math
import re
import statistics
import xml.etree.ElementTree as ET
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "specjvm2008" / "results"
ANALYSIS = ROOT / "analysis"
BASE_ID = "SPECjvm2008.007"
GROUPS = (
    "compiler", "compress", "crypto", "derby", "mpegaudio",
    "scimark.large", "scimark.small", "serial", "startup", "sunflow", "xml",
)
REPEAT_IDS = ("SPECjvm2008.008", "SPECjvm2008.009", "SPECjvm2008.010")


def rounded(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def result_path(result_id, extension):
    return RESULTS / result_id / f"{result_id}.{extension}"


def groups_for(name):
    if name.startswith("startup."):
        return ("startup",)
    if name.startswith("compiler."):
        return ("compiler",)
    if name.startswith("crypto."):
        return ("crypto",)
    if name.startswith("xml."):
        return ("xml",)
    if name == "scimark.monte_carlo":
        return ("scimark.large", "scimark.small")
    if name.startswith("scimark."):
        return ("scimark.large",) if name.endswith(".large") else ("scimark.small",)
    return (name,)


def iteration_data(element):
    if element is None:
        return None
    duration = int(element.attrib["endTime"]) - int(element.attrib["startTime"])
    if duration <= 0:
        raise ValueError("Nonpositive iteration duration in raw result")
    operations = Decimal(element.attrib["operations"])
    score = operations * 60000 / duration
    return {"duration_ms": duration, "operations": operations, "score": score}


def raw_workloads(result_id):
    tree = ET.parse(result_path(result_id, "raw"))
    root = tree.getroot()
    rows = []
    for benchmark in root.findall("./benchmark-results/benchmark-result"):
        name = benchmark.attrib["name"]
        if name == "check":
            continue
        warmup = iteration_data(benchmark.find("./warmup-result/iteration-result"))
        measured = iteration_data(benchmark.find("./iterations/iteration-result"))
        if measured is None or len(benchmark.findall("./iterations/iteration-result")) != 1:
            raise ValueError(f"Expected one measured iteration for {name} in {result_id}")
        rows.append((name, int(benchmark.attrib["numberBmThreads"]), warmup, measured))
    return root, rows


def text_scores(result_id):
    body = result_path(result_id, "txt").read_text(encoding="latin-1")
    row_pattern = re.compile(
        r"^([\w.]+)\s+(warmup|iteration 1)\s+(?:\d+|null)\s+\d+\s+"
        r"\d+(?:\.\d+)?\s+(\d+(?:\.\d+)?)\s*$", re.MULTILINE
    )
    values = {(name, phase): Decimal(score) for name, phase, score in row_pattern.findall(body)}
    group_pattern = re.compile(r"^([\w.]+)\s+(\d+(?:\.\d+)?)\s*$", re.MULTILINE)
    header = body.split("Composite result:", 1)[0]
    groups = {name: Decimal(score) for name, score in group_pattern.findall(header) if name in GROUPS}
    composite_match = re.search(r"Composite result:\s+(\d+(?:\.\d+)?)", body)
    composite = Decimal(composite_match.group(1)) if composite_match else None
    return values, groups, composite, body


def check_text_rows(rows, values, result_id):
    expected = set()
    for name, _, warmup, measured in rows:
        for phase, item in (("warmup", warmup), ("iteration 1", measured)):
            if item is None:
                continue
            key = name, phase
            expected.add(key)
            if key not in values or abs(rounded(item["score"]) - values[key]) > Decimal("0.01"):
                raise ValueError(f"Raw and text disagree: {result_id} {name} {phase}")
    if expected != set(values):
        raise ValueError(f"Raw/text workload sets differ in {result_id}")


def csv_text(fields, rows):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def emit(path, content, check):
    if check:
        if not path.is_file() or path.read_text(encoding="utf-8") != content:
            raise ValueError(f"Generated table differs from raw evidence: {path}")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Verify generated CSVs without writing")
    args = parser.parse_args()

    root, rows = raw_workloads(BASE_ID)
    if root.findtext("workload") != "SPECjvm2008 Base":
        raise ValueError(".007 is not a Base run")
    if root.findtext("suite-build-version") != "SPECjvm2008 1.01 (20090519)":
        raise ValueError("Unexpected SPECjvm2008 version")
    if [x.text for x in root.findall("./configs/config")] != ["specjvm.benchmark.threads=16"]:
        raise ValueError("Unexpected .007 benchmark thread configuration")
    if len(rows) != 38 or len({row[0] for row in rows}) != 38:
        raise ValueError(".007 must contain 38 distinct scored workloads")
    raw_results = root.findall("./benchmark-results/benchmark-result")
    if len(raw_results) != 39 or raw_results[0].attrib.get("name") != "check":
        raise ValueError(".007 must contain the functional check plus 38 workloads")
    check_iteration = raw_results[0].find("./iterations/iteration-result")
    if check_iteration is None or Decimal(check_iteration.attrib.get("operations", "0")) != 1:
        raise ValueError(".007 functional check result is missing")
    for name, threads, warmup, measured in rows:
        if name.startswith("startup."):
            if threads != 1 or warmup is not None:
                raise ValueError(f"Unexpected startup configuration: {name}")
        elif threads != 16 or warmup is None or warmup["duration_ms"] != 120000 or measured["duration_ms"] != 240000:
            raise ValueError(f"Unexpected Base throughput configuration: {name}")

    text_values, reported_groups, reported_composite, body = text_scores(BASE_ID)
    if "Run is compliant" not in body or "NOT VALID" in body or reported_composite is None:
        raise ValueError(".007 text report is not compliant")
    check_text_rows(rows, text_values, BASE_ID)

    grouped = {group: [] for group in GROUPS}
    measurement_rows = []
    raw_hash = hashlib.sha256(result_path(BASE_ID, "raw").read_bytes()).hexdigest()
    for name, threads, warmup, measured in rows:
        names = groups_for(name)
        for group in names:
            grouped[group].append(float(measured["score"]))
        delta = measured["score"] - warmup["score"] if warmup else None
        measurement_rows.append({
            "result_id": BASE_ID,
            "workload": name,
            "group": ";".join(names),
            "kind": "startup" if warmup is None else "throughput",
            "benchmark_threads": threads,
            "warmup_duration_ms": warmup["duration_ms"] if warmup else "",
            "warmup_operations": str(warmup["operations"]) if warmup else "",
            "warmup_ops_per_min": str(rounded(warmup["score"])) if warmup else "",
            "measured_duration_ms": measured["duration_ms"],
            "measured_operations": str(measured["operations"]),
            "measured_ops_per_min": str(rounded(measured["score"])),
            "delta_ops_per_min": str(rounded(delta)) if delta is not None else "",
            "percent_change": str(rounded(delta / warmup["score"] * 100)) if delta is not None else "",
        })

    if set(reported_groups) != set(GROUPS):
        raise ValueError("Text report does not contain all 11 groups")
    table_rows = []
    for group in GROUPS:
        calculated = math.exp(sum(math.log(x) for x in grouped[group]) / len(grouped[group]))
        if abs(calculated - float(reported_groups[group])) > 0.02:
            raise ValueError(f"Raw and report group scores disagree: {group}")
        table_rows.append({"result_id": BASE_ID, "group": group,
                           "member_count": len(grouped[group]),
                           "score_ops_per_min": str(reported_groups[group]), "raw_sha256": raw_hash})
    calculated_composite = math.exp(
        sum(math.log(float(reported_groups[group])) for group in GROUPS) / len(GROUPS)
    )
    if abs(calculated_composite - float(reported_composite)) > 0.02 or reported_composite != Decimal("421.24"):
        raise ValueError("Composite score is inconsistent")
    table_rows.append({"result_id": BASE_ID, "group": "Composite", "member_count": len(GROUPS),
                       "score_ops_per_min": str(reported_composite), "raw_sha256": raw_hash})

    repeat_source = list(csv.DictReader((ANALYSIS / "repeat_test_results.csv").open(encoding="utf-8", newline="")))
    if tuple(row["result_id"] for row in repeat_source) != REPEAT_IDS:
        raise ValueError("Original repeat IDs or order changed")
    repeat_scores = []
    for row in repeat_source:
        _, workloads = raw_workloads(row["result_id"])
        values, _, _, repeat_body = text_scores(row["result_id"])
        if len(workloads) != 1 or workloads[0][0] != "compress":
            raise ValueError(f"Repeat {row['result_id']} is not compress-only")
        check_text_rows(workloads, values, row["result_id"])
        if "Run is valid, but not compliant" not in repeat_body:
            raise ValueError(f"Unexpected repeat validity: {row['result_id']}")
        score = Decimal(row["score_ops_per_min"])
        if score != values["compress", "iteration 1"]:
            raise ValueError(f"Repeat CSV differs from raw/text: {row['result_id']}")
        repeat_scores.append(float(score))
    mean = statistics.mean(repeat_scores)
    median = statistics.median(repeat_scores)
    sd = statistics.stdev(repeat_scores)
    repeat_rows = []
    for row, score in zip(repeat_source, repeat_scores):
        repeat_rows.append({
            "run": row["run"], "result_id": row["result_id"], "score_ops_per_min": f"{score:.2f}",
            "n": len(repeat_scores), "mean_ops_per_min": f"{mean:.3f}",
            "median_ops_per_min": f"{median:.2f}", "min_ops_per_min": f"{min(repeat_scores):.2f}",
            "max_ops_per_min": f"{max(repeat_scores):.2f}",
            "range_ops_per_min": f"{max(repeat_scores) - min(repeat_scores):.2f}",
            "sample_sd_ops_per_min": f"{sd:.3f}", "cv_percent": f"{sd / mean * 100:.3f}",
            "deviation_from_mean_ops_per_min": f"{score - mean:+.3f}",
            "deviation_from_mean_percent": f"{(score - mean) / mean * 100:+.3f}",
        })

    outputs = (
        (ANALYSIS / "base_result_table.csv", csv_text(list(table_rows[0]), table_rows)),
        (ANALYSIS / "workload_measurements.csv", csv_text(list(measurement_rows[0]), measurement_rows)),
        (ANALYSIS / "repeat_statistics.csv", csv_text(list(repeat_rows[0]), repeat_rows)),
    )
    for path, content in outputs:
        emit(path, content, args.check)
    print(f"PASS: {len(rows)} workloads, 11 groups, Base {reported_composite}; repeats {repeat_scores}")
    print(f".007 raw SHA-256: {raw_hash}")


if __name__ == "__main__":
    main()
