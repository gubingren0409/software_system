#!/usr/bin/env python3
"""Check selected official comparison CSV cells against saved SPEC HTML reports."""

import csv
import hashlib
import re
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / "analysis"
SOURCES = {
    "Huawei RH 2285": (
        "official_reference_huawei.html",
        "35d27a41756762e642e4699a5a42846474ca57642b4f665f6d11fc28dcc41e95",
    ),
    "Sugon I620-G20": (
        "official_reference_base.html",
        "8472daef33df919535faf0b21b02b7ecc3a8c72b92bd8f49002e56d4faf016b3",
    ),
}
METRICS = {"Composite", "compress", "derby", "sunflow", "crypto", "startup", "scimark.large"}


def read_csv(name):
    with (ANALYSIS / name).open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def html_scores(name, expected_hash):
    path = ANALYSIS / name
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
        raise ValueError(f"Official report snapshot hash changed: {name}")
    body = path.read_text(encoding="latin-1")
    if "Run is compliant" not in body or "SPECjvm2008 1.01" not in body:
        raise ValueError(f"Official report is not a compliant 1.01 Base: {name}")
    composite = re.search(r"Composite result:\s*([0-9.]+) SPECjvm2008 Base ops/m", body)
    if not composite:
        raise ValueError(f"Missing official composite: {name}")
    scores = {"Composite": Decimal(composite.group(1))}
    for metric in METRICS - {"Composite"}:
        pattern = rf"<TD\s+ALIGN=LEFT>{re.escape(metric)}</TD>\s*<TD\s+ALIGN=LEFT>([0-9.]+)</TD>"
        found = re.search(pattern, body)
        if not found:
            raise ValueError(f"Missing {metric} in {name}")
        scores[metric] = Decimal(found.group(1))
    return scores


def main():
    candidates = read_csv("official_reference_candidates.csv")
    if len(candidates) != 6 or len({row["result_url"] for row in candidates}) != 6:
        raise ValueError("Expected all six distinct published Base results")
    if sum(row["suite_version"] == "1.01" and "7" in row["jvm"] for row in candidates) != 3:
        raise ValueError("Expected three 1.01/Java 7 candidates")
    if any(row["compliant"] != "yes" or not row["result_url"].startswith("https://www.spec.org/")
           for row in candidates):
        raise ValueError("Invalid official candidate provenance")

    indexed = {}
    for row in read_csv("official_group_scores.csv"):
        reference, metric = row["reference"], row["metric"]
        if reference not in SOURCES or metric not in METRICS or (reference, metric) in indexed:
            raise ValueError(f"Unexpected or duplicate official metric: {reference}, {metric}")
        matching = [item for item in candidates if item["machine"] == reference]
        if len(matching) != 1 or matching[0]["result_url"] != row["result_url"]:
            raise ValueError(f"Official URL mismatch: {reference}")
        indexed[reference, metric] = Decimal(row["score_ops_per_min"])
    if len(indexed) != len(SOURCES) * len(METRICS):
        raise ValueError("Incomplete official metric table")
    for reference, (filename, expected_hash) in SOURCES.items():
        for metric, score in html_scores(filename, expected_hash).items():
            if indexed[reference, metric] != score:
                raise ValueError(f"Official CSV differs from snapshot: {reference}, {metric}")
    print("PASS: 14 selected official scores match two immutable SPEC report snapshots")


if __name__ == "__main__":
    main()
