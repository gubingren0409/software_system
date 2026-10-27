"""Offline Stage B recomputation: read raw captures, verify identities, emit new tables."""
import argparse
import collections
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--out", type=Path, default=ROOT / "results/stage-b")
parser.add_argument("--destination", type=Path, required=True)
args = parser.parse_args()
OUT, DEST = args.out.resolve(), args.destination.resolve()


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def save(name, value): (DEST / name).write_text(json.dumps(value, indent=2)+"\n", encoding="utf-8")


manifests = {}
for phase in ("selection", "tuning", "final"):
    manifest = read(OUT / phase / "build-manifest.json")
    assert manifest["sources"] == read(OUT / phase / "source-manifest.json")
    source_files = {p.relative_to(OUT / phase).as_posix() for p in (OUT / phase / "source").rglob("*") if p.is_file()}
    binary_files = {p.relative_to(OUT / phase).as_posix() for p in (OUT / phase / "binaries").glob("*.elf")}
    assert set(manifest["sources"]) == source_files and set(manifest["binaries"]) == binary_files
    for name, expected in {**manifest["sources"], **manifest["binaries"]}.items():
        assert digest(OUT / phase / name) == expected, name
    manifests[phase] = manifest
for relative, expected in manifests["final"]["sources"].items():
    working = ROOT / Path(relative).relative_to("source")
    assert digest(working) == expected, f"Working source differs from final measurement: {working}"
for name in ("sort_a.c", "util.c", "util.h"):
    assert (OUT / "final/source/homework" / name).read_bytes() == (ROOT / "results/stage-a/source/homework" / name).read_bytes()


def capture(name, phase, binary_name="release.elf", expected=0):
    directory = OUT / name
    meta, identity = read(directory / "metadata.json"), read(directory / "identity.json")
    assert meta["returncode"] == expected, name
    assert identity["parameters_in_argv"] == meta["argv"]
    assert identity["source_manifest_sha256"] == digest(OUT / phase / "source-manifest.json")
    assert identity["build_manifest_sha256"] == digest(OUT / phase / "build-manifest.json")
    if binary_name is not None:
        assert identity["binary_sha256"] == digest(OUT / phase / "binaries" / binary_name)
        assert Path(identity["executable"]).name == binary_name
    return (directory / "stdout.txt").read_text(), (directory / "stderr.txt").read_text(), meta


trial_rows = []
input_hashes = {}


def timed(name, phase, variant, n, repeats, seed, binary_name="release.elf", formal=False):
    text, errors, meta = capture(name, phase, binary_name)
    assert "FAIL" not in errors and text.count("Arrays are sorted: yes") == 2
    rows = re.findall(r"TIMING input=(\w+) trial=(\d+) function=sort_(\w) seconds=([\d.]+) N=(\d+) R=(\d+) seed=(\d+) fingerprint=([0-9a-f]+)", text)
    assert len(rows) == 2*repeats and all(r[2] == variant for r in rows), name
    assert f"TOTAL variant=sort_{variant} N={n} R={repeats} seed={seed} actual_sort_calls={2*repeats}" in text
    means = {}
    for kind in ("random", "inverted"):
        subset = [r for r in rows if r[0] == kind]
        assert [int(r[1]) for r in subset] == list(range(1, repeats+1))
        assert all((int(r[4]),int(r[5]),int(r[6])) == (n,repeats,seed) for r in subset)
        values = [float(r[3]) for r in subset]
        assert all(math.isfinite(v) and v > 0 for v in values)
        mean = statistics.mean(values)
        printed = re.search(rf"SUMMARY variant=sort_{variant} input={kind} N={n} R={repeats} seed={seed} calls={repeats} mean_seconds=([\d.]+)", text)
        assert printed and abs(mean-float(printed[1])) < 1.1e-9
        key = (n, repeats, seed, kind)
        hashes = [r[7] for r in subset]
        if key in input_hashes: assert input_hashes[key] == hashes, name
        else: input_hashes[key] = hashes
        means[kind] = mean
        if formal:
            assert meta["argv"][:3] == ["taskset", "-c", "0"]
            assert meta["argv"][4:] == ["--variant", variant, "-b", "-s", str(seed), str(n), str(repeats)]
            for r in subset:
                trial_rows.append({"capture": name, "variant": variant, "N": n, "input": kind,
                                   "trial": int(r[1]), "seconds": float(r[3]), "seed": seed, "fingerprint": r[7]})
    return means


def matrix(phase, variants, sizes, processes, repeats, seed, folder="native"):
    result = []
    for n in sizes:
        for v in variants:
            algorithm = "c" if v.startswith("k") else v
            binary_name = v+".elf" if v.startswith("k") else "release.elf"
            by_kind = collections.defaultdict(list)
            for process in range(1, processes+1):
                name = f"{phase}/{folder}/n{n}-{v}-run{process}"
                values = timed(name, phase, algorithm, n, repeats, seed, binary_name, formal=phase=="final")
                for kind, value in values.items(): by_kind[kind].append(value)
            for kind, values in by_kind.items():
                result.append({"variant": v, "N": n, "input": kind, "seed": seed, "R": repeats,
                               "processes": processes, "process_means_seconds": values,
                               "median_ms": 1000*statistics.median(values), "min_ms": 1000*min(values), "max_ms": 1000*max(values)})
    return result


formal = matrix("final", "aipcmf", [131072,1048576], 5, 5, 20261026)
assert len(trial_rows) == 600
for row in formal:
    baseline = next(r for r in formal if (r["variant"],r["N"],r["input"]) == ("a",row["N"],row["input"]))
    previous = {"a":"a","i":"a","p":"i","c":"a","m":"c","f":"m"}[row["variant"]]
    prior = next(r for r in formal if (r["variant"],r["N"],r["input"]) == (previous,row["N"],row["input"]))
    row["speedup_vs_a"] = baseline["median_ms"]/row["median_ms"]
    row["previous_variant"] = previous
    row["speedup_vs_previous"] = prior["median_ms"]/row["median_ms"]
selection = matrix("selection", "aip", [131072,1048576], 5, 5, 42)
tuning = matrix("tuning", [f"k{k}" for k in (8,16,32,64,128)], [131072], 3, 3, 42)
decision = read(OUT / "tuning/decision.json")
confirmation = matrix("tuning", [f'k{decision["chosen_threshold"]}', decision["runner_up"]], [1048576], 1, 5, 43, "confirmation")


def geometric_scores(rows, reference):
    scores = {}
    for variant in sorted({r["variant"] for r in rows}):
        ratios = []
        for row in (r for r in rows if r["variant"] == variant):
            base = next(r for r in rows if (r["variant"],r["N"],r["input"]) == (reference,row["N"],row["input"]))
            ratios.append(row["median_ms"]/base["median_ms"])
        scores[variant] = math.exp(statistics.mean(math.log(v) for v in ratios))
    return scores


selection_scores = geometric_scores(selection, "a")
chosen_base = next(v for v in "aip" if selection_scores[v] <= min(selection_scores.values())*1.03)
assert chosen_base == read(OUT / "selection/decision.json")["chosen_base"] == "a"
tuning_scores = geometric_scores(tuning, "k8")
chosen_cutoff = min(k for k in (8,16,32,64,128) if tuning_scores[f"k{k}"] <= min(tuning_scores.values())*1.03)
assert chosen_cutoff == decision["chosen_threshold"] == read(OUT / "final/configuration.json")["cutoff"]


def cg(path):
    filename = function = None
    files, functions, cache_model = collections.defaultdict(collections.Counter), collections.defaultdict(collections.Counter), []
    for text in path.read_text().splitlines():
        if text.startswith("events:"): events = text.split()[1:]
        elif text.startswith("desc:"): cache_model.append(text[6:])
        elif text.startswith("fl="): filename = text[3:]
        elif text.startswith("fn="): function = text[3:]
        elif text.startswith("summary:"): total = dict(zip(events,map(int,text.split()[1:])))
        elif re.match(r"^\d+\s", text):
            position, *values = map(int,text.split())
            assert len(values) == len(events)
            counts = dict(zip(events,values))
            files[filename].update(counts)
            functions[(filename,function)].update(counts)
    aggregate = collections.Counter()
    for counts in files.values(): aggregate.update(counts)
    assert dict(aggregate) == total
    return total,files,functions,cache_model


profile_rows, source_rows = [], []
model = None
for variant in "aipcmf":
    timed(f"profile/cachegrind-{variant}", "final", variant, 131072, 5, 20261026)
    capture(f"profile/cg-annotate-{variant}", "final")
    total,files,functions,cache_model = cg(OUT / f"profile/cachegrind-{variant}.out")
    if model is None: model = cache_model
    else: assert model == cache_model
    target = [counts for name,counts in files.items() if name.endswith(f"/homework/sort_{variant}.c")]
    assert len(target) == 1
    row = {"variant": variant, "N":131072, "R":5, "seed":20261026, **total,
           "D_refs":total["Dr"]+total["Dw"], "D1_misses":total["D1mr"]+total["D1mw"],
           "LLd_misses":total["DLmr"]+total["DLmw"], "sort_file_Ir":target[0]["Ir"],
           "allocator_file_Ir":sum(c["Ir"] for f,c in files.items() if f.endswith("/malloc.c")),
           "reference_qsort_file_Ir":sum(c["Ir"] for f,c in files.items() if f.endswith("/qsort.c"))}
    profile_rows.append(row)
    source_rows.append({"variant":variant, **dict(target[0])})

perfs = {}
for variant in "if":
    timed(f"profile/perf-stat-{variant}", "final", variant, 1048576, 5, 20261026)
    timed(f"profile/perf-record-{variant}", "final", variant, 1048576, 5, 20261026)
    report,_,_ = capture(f"profile/perf-report-{variant}", "final")
    annotation,annotation_errors,_ = capture(f"profile/perf-annotate-{variant}", "final")
    assert "recursive_"+variant in annotation and "no samples" not in annotation_errors
    counts = {}
    for row in csv.reader((OUT / f"profile/perf-stat-{variant}/stderr.txt").read_text().splitlines()):
        if len(row)>4 and row[2] in ("cycles:u","instructions:u","branches:u","branch-misses:u"):
            counts[row[2]] = int(row[0])
            assert float(row[4]) == 100.0
    assert len(counts) == 4
    copied = read(OUT / f"profile/perf-record-{variant}/copied-artifact.json")
    assert digest(OUT / copied["delivered_at"]) == copied["sha256"]
    assert copied["binary_sha256"] == digest(OUT / "final/binaries/release.elf")
    perfs[variant] = {"user_hardware_counts_whole_process":counts,
        "samples":int(re.search(r"\((\d+) samples\)", (OUT / f"profile/perf-record-{variant}/stderr.txt").read_text())[1]),
        "sample_count_source":"exact perf record stderr; report header uses abbreviated K counts",
        "lost_samples":int(re.search(r"Total Lost Samples:\s+(\d+)",report)[1]),
        "function_period_percent":{name:float(value) for value,name in re.findall(r"^\s*([\d.]+)%\s+\[\.\]\s+(\S+)",report,re.M)}}

correctness = read(OUT / "correctness/verification.json")
assert correctness["all_six_variants_release_and_debug"] and correctness["memcheck_errors"] == 0
for label, binary in (("release","release.elf"),("debug","debug.elf")):
    text,errors,_ = capture(f"correctness/all-{label}", "final", binary)
    assert "FAIL" not in errors
    for v in "aipcmf":
        assert f'PATTERNS variant=sort_{v} cases={correctness["patterns_per_variant"]}' in text
        assert f'TOTAL variant=sort_{v} N=33 R=1 seed=42 actual_sort_calls={correctness["patterns_per_variant"]+4}' in text
_,memcheck,_ = capture("correctness/memcheck", "final")
assert "ERROR SUMMARY: 0 errors" in memcheck and "All heap blocks were freed" in memcheck
capture("correctness/reject-corrupted-elements", "final", "fault.elf", expected=1)
for index in range(8): capture(f"correctness/reject-{index}", "final", expected=1)
allocation_text,_,_ = capture("correctness/allocation-probe", "final", "allocation-probe.elf")
allocations = [json.loads(line) for line in allocation_text.splitlines()]
assert allocations == correctness["allocations"]

DEST.mkdir(parents=True, exist_ok=False)
subprocess.run([sys.executable,ROOT / "scripts/summarize_stage_a.py","--destination",DEST / "stage-a"], stdout=subprocess.DEVNULL,check=True)
old_a, new_a = read(ROOT / "results/stage-a/summary/summary.json"), read(DEST / "stage-a/summary.json")
old_a.pop("working_sources_equal_measured_snapshot")
assert new_a.pop("frozen_sources_covered_by_manifest")
assert old_a == new_a, "Historical Stage A numerical results changed"
subprocess.run([sys.executable,ROOT / "scripts/analyze_inline.py","--out",OUT,"--destination",DEST / "inline"], stdout=subprocess.DEVNULL,check=True)
inline = read(DEST / "inline/inline-analysis.json")
assert inline == read(OUT / "inline-analysis/inline-analysis.json")
audit = json.loads(subprocess.check_output([sys.executable,ROOT / "scripts/check_stage_a_audit.py"], text=True))
assert audit == read(OUT / "audit/annotate-filter/stdout.txt")


def write_csv(name, rows):
    with (DEST / name).open("w",newline="",encoding="utf-8") as stream:
        writer = csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


save("summary.json", {"source_and_binary_manifests_verified":True, "stage_a_offline_recompute_unchanged":True,
    "formal_sort_calls":len(trial_rows), "formal_native":formal, "selection":selection, "selection_scores":selection_scores,
    "chosen_base":chosen_base, "tuning":tuning, "tuning_scores":tuning_scores, "chosen_cutoff":chosen_cutoff,
    "confirmation":confirmation, "cache_model":model, "cachegrind":profile_rows,
    "source_exclusive_cachegrind":source_rows, "perf":perfs, "inline":inline, "allocations":allocations,
    "correctness":correctness, "stage_a_annotation_filter":audit})
write_csv("native-summary.csv", [{k:v for k,v in r.items() if k!="process_means_seconds"} for r in formal])
write_csv("native-trials.csv",trial_rows)
write_csv("cachegrind-summary.csv",profile_rows)
write_csv("cachegrind-source-exclusive.csv",source_rows)
write_csv("threshold-summary.csv",[{k:v for k,v in r.items() if k!="process_means_seconds"} for r in tuning])
write_csv("allocation-summary.csv",allocations)
changes = {"a":"原始归并", "i":"内联", "p":"指针", "c":"粗化 K=16", "m":"单缓冲", "f":"一次分配复用"}
tables = []
for n in (131072,1048576):
    tables += [f"N={n}，每类排序平均时间的五进程统计；单位 ms。", "",
               "| 版本与变化 | 输入 | 中位数［最小–最大］ | 相对本轮 a | 相对直接比较版本 |",
               "|---|---|---:|---:|---:|"]
    for v in "aipcmf":
        for row in (r for r in formal if r["N"]==n and r["variant"]==v):
            tables.append(f'| {v} {changes[v]} | {row["input"]} | {row["median_ms"]:.3f}［{row["min_ms"]:.3f}–{row["max_ms"]:.3f}］ | {row["speedup_vs_a"]:.3f} | {row["speedup_vs_previous"]:.3f}（{row["previous_variant"]}） |')
    tables.append("")
(DEST / "native-tables.md").write_text("\n".join(tables)+"\n",encoding="utf-8")
print(json.dumps({"formal_sort_calls":len(trial_rows),"chosen_base":chosen_base,"chosen_cutoff":chosen_cutoff,
      "stage_a_recompute_unchanged":True,"private_text_bytes":inline["private_text_bytes"],
      "final_f_speedups":{f'{r["N"]}-{r["input"]}':r["speedup_vs_a"] for r in formal if r["variant"]=="f"}},indent=2))
