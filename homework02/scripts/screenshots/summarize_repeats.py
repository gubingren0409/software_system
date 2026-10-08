#!/usr/bin/env python3
"""Read original repeat raw/TXT and calculate statistics; never run a benchmark."""

import importlib.util
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("core", ROOT / "scripts/analysis/build_core_data.py")
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
scores = []
for result_id in core.REPEAT_IDS:
    raw = core.result_path(result_id, "raw")
    txt = core.result_path(result_id, "txt")
    root, rows = core.raw_workloads(result_id)
    values, _, _, body = core.text_scores(result_id)
    core.check_text_rows(rows, values, result_id)
    assert len(rows) == 1 and rows[0][0] == "compress"
    score = values["compress", "iteration 1"]
    scores.append(float(score))
    print(f"Source: {txt.relative_to(ROOT).as_posix()}")
    print(f"Raw:    {raw.relative_to(ROOT).as_posix()}")
    for line in body.splitlines():
        if line.startswith(("Tested by:", "Run is", "compress ")):
            print(line.rstrip())
    print(f"Raw/TXT score cross-check: PASS ({score} ops/min)\n")
mean = statistics.mean(scores)
sd = statistics.stdev(scores)
print(f"n={len(scores)}; mean={mean:.3f} ops/min")
print(f"Sample SD (n-1)={sd:.3f} ops/min; CV=100*SD/mean={100*sd/mean:.3f}%")
print(f"Range={max(scores)-min(scores):.2f} ops/min; median={statistics.median(scores):.2f} ops/min")
