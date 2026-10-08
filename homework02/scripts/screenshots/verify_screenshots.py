#!/usr/bin/env python3
"""Read-only integrity and report checks for native terminal screenshots."""

import csv
import hashlib
import json
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SESSION = "2026-10-08-set2"
EVIDENCE = ROOT / "evidence/terminal_screenshots" / SESSION
VIEWS = ("historicalenvironment", "currentenvironment", "base", "repeats",
         "heapmatrix", "derbygc", "oomsummary", "oomraw")
ALLOWED_METHOD_EDITS = {
    "scripts/analysis/build_evidence_manifest.py",
    "scripts/analysis/verify_document_tables.py",
    "scripts/jvm_parameter/verify_optional.py",
    "scripts/verify_submission.ps1",
}
SCREENSHOT_DISCLOSURE = "截图说明：前序实验进行时忘记截取即时的终端输出"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    report = (ROOT / "README.md").read_text(encoding="utf-8")
    require(re.findall(r"^## (\d+)\.", report, re.M) == list("1234567"),
            "Report must correspond to instructor questions 1-7")
    sources = set()
    method_hash = digest(ROOT / "scripts/screenshots/show_terminal_evidence.ps1")
    transcripts = {}
    for view in VIEWS:
        record = json.loads((EVIDENCE / f"{view}.json").read_text(encoding="utf-8-sig"))
        require(record["native_screen_capture"] is True and
                "CopyFromScreen" in record["capture_api"], f"Not a native screen capture: {view}")
        require(record["display_script_sha256"] == method_hash, f"Display method changed: {view}")
        require(record["historical"] is (view != "currentenvironment"), f"Mislabelled history: {view}")
        require(record["rendered_rows"] < record["visible_rows"], f"Output scrolled off screen: {view}")
        require(record["commands"], f"Actual commands missing: {view}")
        screenshot = ROOT / record["screenshot"]
        require(digest(screenshot) == record["screenshot_sha256"], f"Screenshot hash mismatch: {view}")
        header = screenshot.read_bytes()[:24]
        require(header[:8] == b"\x89PNG\r\n\x1a\n", f"Not PNG: {view}")
        width, height = struct.unpack(">II", header[16:24])
        rect = record["window_rect"]
        require((width, height) == (rect["right"] - rect["left"], rect["bottom"] - rect["top"]),
                f"Image dimensions differ from captured screen rectangle: {view}")
        require(width >= 1200 and height >= 600, f"Unexpected small screenshot: {view}")
        require(f"]({record['screenshot']})" in report, f"Screenshot not embedded: {view}")
        transcript = (ROOT / record["transcript"]).read_text(encoding="utf-8-sig")
        require("Read-only evidence display complete" in transcript and
                "PowerShell transcript end" in transcript, f"Incomplete terminal log: {view}")
        transcripts[view] = transcript
        for source in record["sources"]:
            require(digest(ROOT / source["path"]) == source["sha256"],
                    f"Input content changed: {source['path']}")
            sources.add(source["path"])
        print(f"PASS: {view}: native screen {width}x{height}; "
              f"{len(record['sources'])} input hashes; visible output; README image")
    introduction = report.split("## 1.", 1)[0]
    require(introduction.count(SCREENSHOT_DISCLOSURE) == 1 and
            "重新执行读取、汇总与验证命令" in introduction and
            "此次未重新运行性能实验" in introduction,
            "Expected one introductory disclosure of retrospective screenshot collection without benchmark rerun")
    for token in ("SPECjvm2008 Base", "Run is compliant", "421.24", "Wed Sep 30"):
        require(token in transcripts["base"], f"Missing original Base output: {token}")
    for token in ("557.34", "545.48", "522.15", "541.657", "17.904", "3.305%"):
        require(token in transcripts["repeats"], f"Missing actual repeat output: {token}")
    require("48/48 captured attempts; 39 valid scores" in transcripts["heapmatrix"], "Matrix was not checked")
    for token in ("measurement phase", "1 s uncertain", "WHOLE JAVA PROCESS", "1861.667", "164.416770"):
        require(token in transcripts["derbygc"], f"Missing Derby scope/data: {token}")
    for number in range(66, 75):
        require(f"SPECjvm2008.{number:03d}" in transcripts["oomsummary"], f"Missing OOM recheck ID {number}")
    for token in ("OutOfMemoryError", "NOT VALID", "java_exit_status=0", "reporter_exit_status=0", "SPECjvm2008.069"):
        require(token in transcripts["oomraw"], f"Missing unmodified OOM evidence: {token}")
    require('openjdk version "17.0.20.1"' in transcripts["currentenvironment"] and
            'openjdk version "1.7.0_75"' in transcripts["currentenvironment"], "Current Java stdout/stderr not retained")

    baseline = ROOT / "evidence/terminal_screenshots/2026-10-08/original_evidence_manifest.csv"
    with baseline.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    protected = 0
    for row in rows:
        if row["relative_path"] in ALLOWED_METHOD_EDITS:
            continue
        path = ROOT / row["relative_path"]
        require(path.is_file() and path.stat().st_size == int(row["bytes"]) and
                digest(path) == row["sha256"], f"Original evidence was modified: {row['relative_path']}")
        protected += 1
    print(f"PASS: {protected}/{len(rows)} original evidence artifacts unchanged; "
          "only four explicitly listed verifier/method edits exempted")
    print(f"PASS: 8/8 screenshots, {len(sources)} distinct input hashes, one introductory screenshot disclosure; no pending screenshot")


if __name__ == "__main__":
    main()
