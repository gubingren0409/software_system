"""Offline recomputation only: validate preserved evidence and write new summaries."""
import argparse
import collections
import csv
import difflib
import hashlib
import json
from pathlib import Path
import re
import statistics
import zipfile

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--out", type=Path, default=ROOT / "results/stage-a", help="preserved raw result directory")
parser.add_argument("--destination", type=Path, help="new directory for derived files")
args = parser.parse_args()
OUT = args.out.resolve()
DEST = (args.destination or OUT / "summary").resolve()


def cg_read(path):
    events, summary, filename = None, None, None
    files = collections.defaultdict(collections.Counter)
    lines = collections.defaultdict(collections.Counter)
    descriptions = []
    for text in path.read_text().splitlines():
        if text.startswith("desc:"):
            descriptions.append(text[6:])
        elif text.startswith("events:"):
            events = text.split()[1:]
        elif text.startswith("summary:"):
            summary = dict(zip(events, map(int, text.split()[1:])))
        elif text.startswith("fl="):
            filename = text[3:]
        elif re.match(r"^\d+\s", text):
            position, *values = map(int, text.split())
            assert len(values) == len(events), path
            counts = dict(zip(events, values))
            files[filename].update(counts)
            lines[(filename, position)].update(counts)
    assert summary is not None and events is not None
    aggregate = collections.Counter()
    for counts in files.values():
        aggregate.update(counts)
    assert dict(aggregate) == summary, f"Unparsed Cachegrind records in {path}"
    return summary, files, lines, descriptions


def csv_write(name, rows):
    with (DEST / name).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


manifest = json.loads((OUT / "build-manifest.json").read_text())
for name, expected in manifest.items():
    assert hashlib.sha256((OUT / name).read_bytes()).hexdigest() == expected, name
for section in ("homework", "recitation"):
    for source in (OUT / "source" / section).iterdir():
        if source.suffix in (".c", ".h") or source.name == "Makefile":
            assert source.read_bytes() == (ROOT / section / source.name).read_bytes(), source
assert json.loads((OUT / "preflight/verification.json").read_text())["perf_real_samples_readable_by_report_and_annotate"]

native_rows = []
native_summary = {}
for mode in ("debug", "release"):
    means = collections.defaultdict(list)
    for iteration in range(1, 6):
        directory = OUT / f"writeup1/native-{mode}-{iteration}"
        assert json.loads((directory / "metadata.json").read_text())["returncode"] == 0
        text = (directory / "stdout.txt").read_text()
        assert "Initial rand_r seed: 42; sort versions: 1; trials per input: 5" in text
        records = re.findall(r"TIMING input=(\w+) trial=(\d+) function=sort_a seconds=([\d.]+)", text)
        assert len(records) == 10 and text.count("Arrays are sorted: yes") == 2
        reported = [float(v) for v in re.findall(r"Elapsed execution time: ([\d.]+)", text)]
        for index, kind in enumerate(("random", "inverted")):
            group = [(int(trial), float(seconds)) for inp, trial, seconds in records if inp == kind]
            assert [trial for trial, seconds in group] == [1, 2, 3, 4, 5]
            average = statistics.mean(seconds for trial, seconds in group)
            assert abs(average - reported[index]) < 1.1e-9
            means[kind].append(average)
            for trial, seconds in group:
                native_rows.append(dict(mode=mode, process=iteration, input=kind, trial=trial, seconds=seconds))
    native_summary[mode] = {kind: {"process_means_seconds": values,
        "median_seconds": statistics.median(values), "min_seconds": min(values), "max_seconds": max(values)}
        for kind, values in means.items()}

wup = {}
for mode in ("debug", "release"):
    stats, files, lines, descriptions = cg_read(OUT / f"writeup1/cachegrind-{mode}.out")
    assert json.loads((OUT / f"writeup1/cachegrind-{mode}/metadata.json").read_text())["returncode"] == 0
    sort_counts = [dict(counts) for name, counts in files.items() if name.endswith("/homework/sort_a.c")]
    assert len(sort_counts) == 1
    wup[mode] = {"whole_process": stats, "sort_a_c_exclusive": sort_counts[0], "simulated_caches": descriptions}

parameters = json.loads((OUT / "checkoff2/parameters.json").read_text())
array_line = next(i for i, text in enumerate((ROOT / "recitation/sum.c").read_text().splitlines(), 1)
                  if "val = (val + data[l])" in text)
sum_rows = []
for config in parameters["configs"]:
    u, n = config["U"], config["N"]
    label = f"u{u}-n{n}"
    stats, files, lines, descriptions = cg_read(OUT / f"checkoff2/cachegrind-{label}.out")
    for command in (f"checkoff2/cachegrind-{label}", f"checkoff2/native-{label}", f"checkoff2/annotate-{label}"):
        assert json.loads((OUT / command / "metadata.json").read_text())["returncode"] == 0
    native_text = (OUT / f"checkoff2/native-{label}/stdout.txt").read_text()
    assert native_text == (OUT / f"checkoff2/cachegrind-{label}/stdout.txt").read_text()
    array_counts = [dict(counts) for (name, position), counts in lines.items()
                    if name.endswith("/recitation/sum.c") and position == array_line]
    assert len(array_counts) == 1
    array = array_counts[0]
    accesses = stats["Dr"] + stats["Dw"]
    d1, ll = stats["D1mr"] + stats["D1mw"], stats["DLmr"] + stats["DLmw"]
    sum_rows.append(dict(U=u, N=n, array_bytes=4*u, Ir=stats["Ir"], Dr=stats["Dr"], Dw=stats["Dw"],
        D_refs=accesses, D1mr=stats["D1mr"], D1mw=stats["D1mw"], D1_misses=d1, D1_rate_percent=100*d1/accesses,
        DLmr=stats["DLmr"], DLmw=stats["DLmw"], LLd_misses=ll, LLd_rate_percent=100*ll/accesses,
        array_line=array_line, array_Dr=array["Dr"], array_D1mr=array["D1mr"], array_DLmr=array["DLmr"],
        array_D1_read_rate_percent=100*array["D1mr"]/array["Dr"],
        array_LL_read_rate_percent=100*array["DLmr"]/array["Dr"],
        Bc=stats["Bc"], Bcm=stats["Bcm"], Bi=stats["Bi"], Bim=stats["Bim"],
        signed_printed_value=int(re.search(r"Value = (-?\d+)", native_text)[1])))
    assert descriptions == wup["debug"]["simulated_caches"]

hardware = {}
for row in csv.reader((OUT / "checkoff1/perf-stat/stderr.txt").read_text().splitlines()):
    if len(row) >= 5 and row[2] in ("cycles:u", "instructions:u", "branches:u", "branch-misses:u"):
        hardware[row[2]] = int(row[0])
        assert float(row[4]) == 100.0, "Multiplexed event: disclose running percentage"
assert len(hardware) == 4
report = (OUT / "checkoff1/perf-report/stdout.txt").read_text()
assert "Total Lost Samples: 0" in report
sample_count = int(re.search(r"# Samples:\s+(\d+)", report)[1])
annotation = (OUT / "checkoff1/perf-annotate/stdout.txt").read_text()
hotlines = [{"line": int(line), "local_period_percent": float(percent)}
            for percent, line in re.findall(r"^\s*([\d.]+) isort\.c:(\d+)\s*$", annotation, re.M)]
instructions = [{"address": "0x" + address, "local_period_percent": float(percent), "instruction": instruction}
                for percent, address, instruction in re.findall(r"^\s*([\d.]+)\s*:\s*([0-9a-f]+):\s+(.+)$", annotation, re.M)]
assert hotlines and instructions
periods = collections.Counter()
hits = collections.Counter()
offset_periods = collections.Counter()
isort_period = 0
observed_samples = 0
sample = None
for text in (OUT / "checkoff1/perf-script/stdout.txt").read_text().splitlines():
    match = re.match(r"\s*(\d+)\s+cycles:u:\s+([0-9a-f]+)\s+(\S+)", text)
    if match:
        period, ip, symbol = match.groups()
        sample = (int(period), symbol)
        observed_samples += 1
        if symbol.startswith("isort+"):
            isort_period += int(period)
            offset_periods[int(symbol.split("+")[1], 16)] += int(period)
    elif sample and sample[1].startswith("isort+") and re.match(r"\s*isort\.c:\d+", text):
        position = int(text.split(":")[-1])
        periods[position] += sample[0]
        hits[position] += 1
assert observed_samples == sample_count
top_line = max(periods, key=periods.get)
assert top_line == hotlines[0]["line"]
assert sum(periods.values()) == isort_period == sum(offset_periods.values())
symbol_address = int(re.search(r"([0-9a-f]+) <isort>:", annotation)[1], 16)
top_offset = max(offset_periods, key=offset_periods.get)
top_instruction = next(item.copy() for item in instructions if int(item["address"], 16) == symbol_address + top_offset)
assert top_instruction["address"] == max(instructions, key=lambda item: item["local_period_percent"])["address"]
top_instruction["annotate_reported_local_period_percent"] = top_instruction.pop("local_period_percent")
top_instruction["script_local_period_percent"] = 100*offset_periods[top_offset]/isort_period
top_instruction["period_weight"] = offset_periods[top_offset]
line_text = (ROOT / "recitation/isort.c").read_text().splitlines()[top_line - 1]

summary = {"all_manifest_hashes_match": True, "working_sources_equal_measured_snapshot": True,
    "checkoff1": {"hardware_user_events": hardware, "samples": sample_count, "lost_samples": 0,
        "isort_symbol_period_percent": float(re.search(r"([\d.]+)%\s+\[\.\] isort", report)[1]),
        "annotate_source_summary": hotlines, "hottest_source_line": top_line, "source_line_text": line_text,
        "source_line_script_local_period_percent": 100*periods[top_line]/isort_period,
        "hottest_instruction": top_instruction,
        "source_period_totals": dict(periods), "source_sample_counts": dict(hits),
        "branch_miss_percent": 100*hardware["branch-misses:u"]/hardware["branches:u"]},
    "checkoff2": {"simulated_caches": descriptions, "configs": sum_rows},
    "writeup1": {"native": native_summary, "cachegrind": wup,
        "native_speedup_debug_over_release": {kind: native_summary["debug"][kind]["median_seconds"] /
            native_summary["release"][kind]["median_seconds"] for kind in ("random", "inverted")}}}
DEST.mkdir(parents=True, exist_ok=False)
(DEST / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
csv_write("native-trials.csv", native_rows)
csv_write("sum-cachegrind.csv", sum_rows)
csv_write("isort-source-periods.csv", [dict(source_line=line, period=period, samples=hits[line], local_period_percent=100*period/isort_period)
    for line, period in periods.most_common()])
patches = []
with zipfile.ZipFile(ROOT / "original/MIT6_172F18_hw2.zip") as archive:
    for name in sorted(archive.namelist()):
        path = ROOT / name
        if name.startswith(("homework/", "recitation/")) and path.is_file():
            patches.extend(difflib.unified_diff(archive.read(name).decode().splitlines(True), path.read_text().splitlines(True),
                fromfile="official/" + name, tofile="working/" + name))
(DEST / "official-source-diff.patch").write_text("".join(patches))
print(json.dumps(summary, indent=2))
