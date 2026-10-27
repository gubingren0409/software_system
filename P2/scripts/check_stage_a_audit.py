"""Reproduce the 0.5% annotate source-summary filter from existing samples only."""
import collections
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
samples = ROOT / "results/stage-a/checkoff1/perf-script/stdout.txt"
weights = collections.Counter()
lines = {}
current = None
for text in samples.read_text().splitlines():
    match = re.match(r"\s*(\d+)\s+cycles:u:\s+[0-9a-f]+\s+(\S+)", text)
    if match:
        period, symbol = match.groups()
        current = symbol if symbol.startswith("isort+") else None
        if current:
            weights[current] += int(period)
    elif current and re.match(r"\s*isort\.c:\d+", text):
        position = int(text.split(":")[-1])
        assert current not in lines or lines[current] == position
        lines[current] = position
total = sum(weights.values())
line20 = {pc: value for pc, value in weights.items() if lines.get(pc) == 20}
retained = {pc: value for pc, value in line20.items() if 100*value/total > 0.5}
full, filtered = sum(line20.values()), sum(retained.values())
assert (full, total, filtered, full-filtered) == (1299100602, 1362398487, 1286723959, 12376643)
result = {"source": "https://github.com/gregkh/linux/blob/v6.8.12/tools/perf/util/annotate.c",
          "function": "annotation__calc_lines", "filter": "skip each instruction with percent_max <= 0.5 before merging by source line",
          "full_period": full, "isort_period": total, "full_percent": 100*full/total,
          "filtered_period": filtered, "filtered_percent": 100*filtered/total,
          "excluded_period": full-filtered, "difference_percentage_points": 100*(full-filtered)/total,
          "line20_instructions": [{"symbol_offset": pc, "period": value, "percent": 100*value/total,
                                   "retained": pc in retained} for pc, value in sorted(line20.items())]}
print(json.dumps(result, indent=2))
