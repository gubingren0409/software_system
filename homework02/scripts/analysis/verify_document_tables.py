#!/usr/bin/env python3
"""Fail if the analysis Markdown tables drift from their checked source CSVs."""

import csv
import re
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / "analysis"
FOCUS = ("compress", "derby", "sunflow", "crypto.aes", "scimark.fft.small", "scimark.fft.large")
METRICS = ("Composite", "compress", "derby", "sunflow", "crypto", "startup", "scimark.large")


def table_body(body):
    rows = {}
    for line in body.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip().replace("−", "-") for cell in line.strip("|").split("|")]
        if cells and cells[0]:
            rows[cells[0].replace("`", "")] = cells
    return rows


def table(path):
    return table_body(path.read_text(encoding="utf-8"))


def report_section(body, number):
    start = re.search(rf"^## {number}\. ", body, re.MULTILINE)
    end = re.search(rf"^## {number + 1}\. ", body, re.MULTILINE)
    if not start or not end or end.start() <= start.end():
        raise ValueError(f"README section {number} not found")
    return body[start.end():end.start()]


def csv_rows(name):
    with (ANALYSIS / name).open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def equal_score(actual, expected, label):
    if Decimal(actual.rstrip("%")) != Decimal(expected):
        raise ValueError(f"Analysis table differs from CSV at {label}: {actual} != {expected}")


def main():
    workload_rows = table(ANALYSIS / "workload_analysis.md")
    measured = {row["workload"]: row for row in csv_rows("workload_measurements.csv")}
    for name in FOCUS:
        row = measured[name]
        cells = workload_rows.get(name)
        if cells is None or len(cells) < 5:
            raise ValueError(f"Missing workload analysis table row: {name}")
        for position, field in ((1, "warmup_ops_per_min"), (2, "measured_ops_per_min"),
                                (3, "delta_ops_per_min"), (4, "percent_change")):
            equal_score(cells[position], row[field], name + ":" + field)

    local = {row["group"]: Decimal(row["score_ops_per_min"])
             for row in csv_rows("base_result_table.csv")}
    official = {}
    for row in csv_rows("official_group_scores.csv"):
        official[row["reference"], row["metric"]] = Decimal(row["score_ops_per_min"])
    comparison_rows = table(ANALYSIS / "official_comparison.md")
    for metric in METRICS:
        label = metric + " 组" if metric in {"crypto", "startup", "scimark.large"} else metric
        cells = comparison_rows.get(label)
        if cells is None or len(cells) < 6:
            raise ValueError(f"Missing official comparison row: {metric}")
        equal_score(cells[1], local[metric], metric + ":local")
        for offset, reference in ((2, "Huawei RH 2285"), (4, "Sugon I620-G20")):
            score = official[reference, metric]
            equal_score(cells[offset], score, reference + ":" + metric)
            ratio = (score / local[metric]).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
            equal_score(cells[offset + 1], ratio, reference + ":" + metric + ":ratio")

    repeat_rows = table(ANALYSIS / "repeat_test_analysis.md")
    repeats = csv_rows("repeat_statistics.csv")
    for repeat in repeats:
        run = repeat["run"]
        cells = repeat_rows.get(run)
        if cells is None or len(cells) < 6:
            raise ValueError(f"Missing repeat analysis row: {run}")
        result_id = cells[1].strip("`")
        if not re.fullmatch(r"\.0(?:08|09|10)", result_id) or not repeat["result_id"].endswith(result_id[1:]):
            raise ValueError(f"Wrong repeat result ID: {run}")
        for position, field in ((3, "score_ops_per_min"),
                                (4, "deviation_from_mean_ops_per_min"),
                                (5, "deviation_from_mean_percent")):
            equal_score(cells[position], repeat[field], run + ":" + field)

    report = (ROOT / "README.md").read_text(encoding="utf-8")
    base_section = report_section(report, 2)
    reported_groups = {}
    for line in base_section.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip().strip("`*") for cell in line.strip("|").split("|")]
        if len(cells) == 4:
            for name, score in ((cells[0], cells[1]), (cells[2], cells[3])):
                if name in local:
                    reported_groups[name] = score
    if set(reported_groups) != set(local):
        raise ValueError("README does not report all 11 Base groups and Composite")
    for name, score in local.items():
        equal_score(reported_groups[name], score, "README Base:" + name)

    report_workloads = table_body(report_section(report, 3))
    for name in FOCUS:
        cells = report_workloads.get(name)
        if cells is None or len(cells) < 3:
            raise ValueError(f"README workload row missing: {name}")
        phase = re.fullmatch(r"([0-9.]+)\s*→\s*\*\*([0-9.]+)\*\*", cells[1])
        if not phase:
            raise ValueError(f"README workload phases malformed: {name}")
        equal_score(phase.group(1), measured[name]["warmup_ops_per_min"], name + ":README warmup")
        equal_score(phase.group(2), measured[name]["measured_ops_per_min"], name + ":README measured")
        equal_score(cells[2], measured[name]["percent_change"], name + ":README change")

    report_official = table_body(report_section(report, 4))
    for metric in METRICS:
        label = metric + " 组" if metric in {"crypto", "startup", "scimark.large"} else metric
        cells = report_official.get(label)
        if cells is None or len(cells) < 6:
            raise ValueError(f"README official row missing: {metric}")
        equal_score(cells[1], local[metric], metric + ":README local")
        for offset, reference in ((2, "Huawei RH 2285"), (4, "Sugon I620-G20")):
            score = official[reference, metric]
            equal_score(cells[offset], score, reference + ":README score")
            ratio = (score / local[metric]).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
            equal_score(cells[offset + 1], ratio, reference + ":README ratio")

    report_repeats = table_body(report_section(report, 5))
    if set(report_repeats).intersection({"Run1", "Run2", "Run3"}) != {"Run1", "Run2", "Run3"}:
        raise ValueError("README repeat table must have exactly the three original run labels")
    for repeat in repeats:
        run = repeat["run"]
        cells = report_repeats[run]
        if len(cells) < 4 or repeat["result_id"] != "SPECjvm2008" + cells[1].strip("`"):
            raise ValueError(f"README repeat ID mismatch: {run}")
        equal_score(cells[3].strip("*"), repeat["score_ops_per_min"], run + ":README score")
    print("PASS: analysis and README Base, workload, official, repeat tables match source CSVs")


if __name__ == "__main__":
    main()
