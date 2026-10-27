"""Stage B commands use fresh directories and bind data to frozen source/ELF hashes."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import tempfile

from capture import capture

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("phase", choices=["audit", "select", "tune", "confirm", "final-build", "verify", "native", "profile"])
parser.add_argument("--out", type=Path, default=ROOT / "results/stage-b")
parser.add_argument("--perf", default="/usr/lib/linux-tools-6.8.0-146/perf")
args = parser.parse_args()
OUT = args.out.resolve()
CPU = 0 if 0 in os.sched_getaffinity(0) else min(os.sched_getaffinity(0))
CFLAGS = ["-O3", "-DNDEBUG", "-g", "-Wall", "-std=gnu99", "-gdwarf-3"]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + "\n")


def run(name, argv, phase=None, executable=None, expected=0, cwd=None, env=None):
    identity = {"parameters_in_argv": [str(a) for a in argv], "environment_overrides": env or {}}
    if executable:
        identity["executable"] = str(executable)
        identity["binary_sha256"] = digest(executable)
    if phase:
        identity["source_manifest_sha256"] = digest(OUT / phase / "source-manifest.json")
        manifest = OUT / phase / "build-manifest.json"
        if manifest.exists(): identity["build_manifest_sha256"] = digest(manifest)
    code = capture(OUT / name, argv, cwd or ROOT, expected=None, env=env)
    dump(OUT / name / "identity.json", identity)
    if code != expected:
        raise RuntimeError(f"{name}: expected {expected}, got {code}; inspect saved output")


def freeze(phase):
    destination = OUT / phase / "source/homework"
    destination.mkdir(parents=True, exist_ok=False)
    for path in (ROOT / "homework").rglob("*"):
        if path.suffix in (".c", ".h") or path.name == "Makefile":
            target = destination / path.relative_to(ROOT / "homework")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
    for name in ("sort_a.c", "util.c", "util.h"):
        assert (destination / name).read_bytes() == (ROOT / "results/stage-a/source/homework" / name).read_bytes(), name
    dump(OUT / phase / "source-manifest.json", {p.relative_to(OUT / phase).as_posix(): digest(p)
         for p in sorted(destination.rglob("*")) if p.is_file()})
    (OUT / phase / "binaries").mkdir()
    return destination


def build(phase, name="release", defines=(), flags=None):
    source = OUT / phase / "source/homework"
    options = list(flags or CFLAGS) + list(defines)
    run(f"{phase}/build-{name}", ["make", "--always-make", "DEBUG=0", "CFLAGS=" + " ".join(options)], phase, cwd=source)
    binary = OUT / phase / "binaries" / (name + ".elf")
    shutil.copy2(source / "sort", binary)
    (source / "sort").unlink()
    return binary


def seal(phase):
    sources = json.loads((OUT / phase / "source-manifest.json").read_text())
    binaries = {p.relative_to(OUT / phase).as_posix(): digest(p)
                for p in sorted((OUT / phase / "binaries").glob("*.elf"))}
    dump(OUT / phase / "build-manifest.json", {"sources": sources, "binaries": binaries})


def parse_timing(directory, variant, n, repeats, seed):
    text = (directory / "stdout.txt").read_text()
    records = re.findall(r"TIMING input=(\w+) trial=(\d+) function=sort_(\w) seconds=([\d.]+) N=(\d+) R=(\d+) seed=(\d+) fingerprint=([0-9a-f]+)", text)
    assert len(records) == 2*repeats and all(v == variant for _, _, v, *_ in records), directory
    result = {}
    for kind in ("random", "inverted"):
        subset = [r for r in records if r[0] == kind]
        assert [int(r[1]) for r in subset] == list(range(1, repeats+1))
        assert all((int(r[4]), int(r[5]), int(r[6])) == (n, repeats, seed) for r in subset)
        seconds = [float(r[3]) for r in subset]
        assert all(math.isfinite(value) and value > 0 for value in seconds)
        summary = re.search(rf"SUMMARY variant=sort_{variant} input={kind} N={n} R={repeats} seed={seed} calls={repeats} mean_seconds=([\d.]+)", text)
        assert summary and abs(float(summary[1])-statistics.mean(seconds)) < 1.1e-9
        result[kind] = {"mean_seconds": statistics.mean(seconds), "trials": seconds,
                        "fingerprints": [r[7] for r in subset]}
    assert f"TOTAL variant=sort_{variant} N={n} R={repeats} seed={seed} actual_sort_calls={2*repeats}" in text
    assert "FAIL" not in (directory / "stderr.txt").read_text()
    return result


def native_batch(phase, variants, sizes, processes, repeats, seed, binary_map=None, folder="native"):
    order = []
    fingerprints = {}
    rows = []
    for process in range(1, processes+1):
        for size_index, n in enumerate(sizes):
            offset = (process-1+size_index) % len(variants)
            rotated = list(variants[offset:]) + list(variants[:offset])
            if process % 2 == 0: rotated.reverse()
            for variant in rotated:
                binary = binary_map[variant] if binary_map else OUT / phase / "binaries/release.elf"
                algorithm = "c" if variant.startswith("k") else variant
                name = f"{phase}/{folder}/n{n}-{variant}-run{process}"
                argv = ["taskset", "-c", CPU, binary, "--variant", algorithm, "-b", "-s", seed, n, repeats]
                run(name, argv, phase, binary)
                parsed = parse_timing(OUT / name, algorithm, n, repeats, seed)
                for kind, data in parsed.items():
                    key = (n, kind)
                    if key in fingerprints: assert fingerprints[key] == data["fingerprints"], name
                    else: fingerprints[key] = data["fingerprints"]
                    rows.append({"variant": variant, "N": n, "input": kind, "process": process,
                                 "R": repeats, "seed": seed, "mean_seconds": data["mean_seconds"], "capture": name})
                order.append(name)
    dump(OUT / phase / f"{folder}-order.json", order)
    dump(OUT / phase / f"{folder}-process-means.json", rows)
    return rows


def score(rows, reference_variant=None):
    grouped = {}
    for row in rows:
        grouped.setdefault((row["variant"], row["N"], row["input"]), []).append(row["mean_seconds"])
    variants = sorted({row["variant"] for row in rows})
    medians = {v: {(n, kind): statistics.median(grouped[v, n, kind])
                   for n, kind in sorted({(r["N"], r["input"]) for r in rows})} for v in variants}
    reference = medians[reference_variant or variants[0]]
    scores = {v: math.exp(statistics.mean(math.log(value/reference[key]) for key, value in medians[v].items())) for v in variants}
    return scores, medians


def audit():
    run("audit/annotate-filter", ["python3", ROOT / "scripts/check_stage_a_audit.py"])
    run("audit/stage-a-recompute", ["python3", ROOT / "scripts/summarize_stage_a.py", "--destination", OUT / "audit/stage-a-derived"])
    for name, argv in [("os", ["cat", "/etc/os-release"]), ("kernel", ["uname", "-a"]),
                       ("lscpu", ["lscpu"]), ("clang", ["clang", "--version"]),
                       ("perf", [args.perf, "version", "--build-options"]),
                       ("valgrind", ["valgrind", "--version"]), ("cg-annotate", ["cg_annotate", "--version"]),
                       ("memory", ["free", "-h"]), ("affinity", ["taskset", "-pc", str(os.getpid())])]:
        run("environment/"+name, argv)


def select_base():
    freeze("selection")
    binary = build("selection")
    seal("selection")
    for variant in "aip":
        run(f"selection/correct-{variant}", [binary, "--variant", variant, "-s", 42, 33, 1], "selection", binary)
    # Rule fixed before measurements: four cells have equal log weight; <=3% is a tie.
    policy = {"sizes": [131072, 1048576], "inputs": ["random", "inverted"], "processes": 5,
              "R": 5, "seed": 42, "cpu": CPU, "score": "geometric mean median time / a median across four cells",
              "tie": "within 3% of best score; choose earliest in a,i,p simplicity order"}
    dump(OUT / "selection/policy.json", policy)
    rows = native_batch("selection", "aip", policy["sizes"], 5, 5, 42)
    scores, medians = score(rows)
    best = min(scores.values())
    tied = [v for v in "aip" if scores[v] <= best*1.03]
    chosen = tied[0]
    decision = {"chosen_base": chosen, "scores_lower_is_better": scores, "within_3_percent": tied,
                "medians_seconds": {v: {f"{n}-{kind}": value for (n, kind), value in cells.items()} for v, cells in medians.items()}}
    dump(OUT / "selection/decision.json", decision)
    print(json.dumps(decision, indent=2), flush=True)


def tune():
    assert json.loads((OUT / "selection/decision.json").read_text())["chosen_base"] == "a"
    freeze("tuning")
    thresholds = [8, 16, 32, 64, 128]
    binaries = {f"k{k}": build("tuning", f"k{k}", [f"-DSORT_CUTOFF={k}"]) for k in thresholds}
    seal("tuning")
    policy = {"base": "a", "thresholds": thresholds, "N": 131072, "R": 3,
              "processes_per_threshold": 3, "seed": 42, "cpu": CPU,
              "score": "equal-weight geometric mean of random/inverted median times, normalized to K=8",
              "tie": "choose smallest threshold within 3% of best score",
              "confirmation": "chosen and next-best score; seed=43,N=1048576,R=5,one process each",
              "formal_seed": 20261026}
    dump(OUT / "tuning/policy.json", policy)
    for key, binary in binaries.items():
        run(f"tuning/correct-{key}", [binary, "--variant", "c", "-s", 42, 33, 1], "tuning", binary)
    rows = native_batch("tuning", list(binaries), [131072], 3, 3, 42, binaries)
    scores, medians = score(rows, "k8")
    best = min(scores.values())
    tied = [k for k in thresholds if scores[f"k{k}"] <= best*1.03]
    chosen = min(tied)
    runner_up = min((key for key in scores if key != f"k{chosen}"), key=scores.get)
    decision = {"chosen_threshold": chosen, "runner_up": runner_up, "scores_lower_is_better": scores,
                "within_3_percent": tied, "medians_seconds": {v: {f"{n}-{kind}": value for (n, kind), value in cells.items()} for v, cells in medians.items()}}
    dump(OUT / "tuning/decision.json", decision)
    print(json.dumps(decision, indent=2), flush=True)


def confirm():
    decision = json.loads((OUT / "tuning/decision.json").read_text())
    selected = f'k{decision["chosen_threshold"]}'
    candidates = [selected, decision["runner_up"]]
    binaries = {key: OUT / "tuning/binaries" / (key + ".elf") for key in candidates}
    rows = native_batch("tuning", candidates, [1048576], 1, 5, 43, binaries, "confirmation")
    scores, medians = score(rows, selected)
    dump(OUT / "tuning/confirmation.json", {"chosen": selected, "scores_relative_to_chosen": scores,
         "selection_not_retuned_on_confirmation": True, "seed": 43,
         "process_means": rows})
    print(json.dumps(scores), flush=True)


def final_build():
    chosen = json.loads((OUT / "tuning/decision.json").read_text())["chosen_threshold"]
    assert int(re.search(r"#define SORT_CUTOFF (\d+)", (ROOT / "homework/sort_config.h").read_text())[1]) == chosen
    source = freeze("final")
    remarks = ["-Rpass=inline", "-Rpass-missed=inline"]
    build("final", flags=CFLAGS+remarks)
    build("final", "debug", flags=["-O0", "-DDEBUG", "-g", "-Wall", "-std=gnu99", "-gdwarf-3"])
    build("final", "i-no-inline-keyword", ["-DI_RECURSIVE_INLINE=0"], flags=CFLAGS+remarks)
    sort_sources = [source / f"sort_{v}.c" for v in "aipcmf"]
    run("final/build-allocation-probe", ["clang"]+CFLAGS+[source / "diagnostics/allocation_probe.c", source / "util.c"]+
        sort_sources+["-Wl,--wrap=malloc,--wrap=free", "-o", OUT / "final/binaries/allocation-probe.elf"], "final")
    run("final/build-fault", ["clang"]+CFLAGS+[source / name for name in ("main.c", "tests.c", "util.c", "isort.c")]+
        [p for p in sort_sources if p.name != "sort_a.c"]+[source / "diagnostics/fault_a.c", "-lrt", "-lm",
        "-o", OUT / "final/binaries/fault.elf"], "final")
    seal("final")
    dump(OUT / "final/configuration.json", {"cutoff": chosen, "coarsening_base": "a", "formal_flags": CFLAGS+remarks,
         "formal_binary": "binaries/release.elf", "cpu": CPU, "N": [131072, 1048576],
         "seed": 20261026, "R": 5, "processes_per_variant_and_size": 5,
         "CG_N": 131072, "CG_R": 5, "perf_N": 1048576, "perf_R": 5,
         "input_domain": "0..2147483647; CLI 1<=N<=INT_MAX/2; empty ranges are correctness cases"})
    for label in ("release", "i-no-inline-keyword"):
        binary = OUT / "final/binaries" / (label + ".elf")
        run(f"final/nm-{label}", ["nm", "-S", "--defined-only", "--radix=d", binary], "final", binary)
        run(f"final/disassembly-{label}", ["objdump", "-dSl", "--no-show-raw-insn", binary], "final", binary)


def verify():
    release = OUT / "final/binaries/release.elf"
    debug = OUT / "final/binaries/debug.elf"
    pattern_cases = None
    for name, binary in (("release", release), ("debug", debug)):
        run(f"correctness/all-{name}", [binary, "--variant", "all", "-s", 42, 33, 1], "final", binary)
        text = (OUT / f"correctness/all-{name}/stdout.txt").read_text()
        assert text.count("PATTERNS variant=") == 6 and "domain=0..2147483647" in text
        counts = [int(value) for value in re.findall(r"PATTERNS variant=sort_\w cases=(\d+)", text)]
        assert len(set(counts)) == 1
        if pattern_cases is None: pattern_cases = counts[0]
        else: assert pattern_cases == counts[0]
        for v in "aipcmf":
            assert f"TOTAL variant=sort_{v} N=33 R=1 seed=42 actual_sort_calls={pattern_cases+4}" in text
        assert "FAIL" not in (OUT / f"correctness/all-{name}/stderr.txt").read_text()
    run("correctness/memcheck", ["valgrind", "--tool=memcheck", "--leak-check=full", "--errors-for-leak-kinds=all",
        "--error-exitcode=99", release, "--variant", "all", "-s", 42, 33, 1], "final", release)
    errors = (OUT / "correctness/memcheck/stderr.txt").read_text()
    assert "ERROR SUMMARY: 0 errors" in errors and "All heap blocks were freed" in errors
    invalid = [["--variant", "bad", 32, 1], ["--variant", "a", "0", 1], ["--variant", "a", 32, "0"],
               ["--variant", "a", "32junk", 1], ["--variant", "a", "1073741824", 1],
               ["--variant", "a", "-2", 1], ["--variant", "a", "-s", "4294967296", 32, 1],
               ["--unknown", 32, 1]]
    for index, tail in enumerate(invalid):
        run(f"correctness/reject-{index}", [release]+tail, "final", release, expected=1)
    fault = OUT / "final/binaries/fault.elf"
    run("correctness/reject-corrupted-elements", [fault, "--variant", "a", "-b", "-s", 42, 32, 1], "final", fault, expected=1)
    assert "Reference mismatch" in (OUT / "correctness/reject-corrupted-elements/stderr.txt").read_text()
    fingerprints = None
    for v in "aipcmf":
        name = f"correctness/seed-{v}"
        run(name, [release, "--variant", v, "-b", "-s", 42, 33, 2], "final", release)
        parsed = parse_timing(OUT / name, v, 33, 2, 42)
        values = {kind: data["fingerprints"] for kind, data in parsed.items()}
        if fingerprints is None: fingerprints = values
        else: assert fingerprints == values
    run("correctness/seed-all", [release, "--variant", "all", "-b", "-s", 42, 33, 2], "final", release)
    all_text = (OUT / "correctness/seed-all/stdout.txt").read_text()
    for v in "aipcmf":
        for kind, expected in fingerprints.items():
            actual = re.findall(rf"TIMING input={kind} trial=\d+ function=sort_{v} [^\n]*fingerprint=([0-9a-f]+)", all_text)
            assert actual == expected
        assert f"TOTAL variant=sort_{v} N=33 R=2 seed=42 actual_sort_calls=4" in all_text
    run("correctness/seed-different", [release, "--variant", "a", "-b", "-s", 43, 33, 2], "final", release)
    other = parse_timing(OUT / "correctness/seed-different", "a", 33, 2, 43)
    assert other["random"]["fingerprints"] != fingerprints["random"]
    probe = OUT / "final/binaries/allocation-probe.elf"
    run("correctness/allocation-probe", [probe], "final", probe)
    allocations = [json.loads(line) for line in (OUT / "correctness/allocation-probe/stdout.txt").read_text().splitlines()]
    assert len(allocations) == 6 and allocations[-1]["malloc_calls"] == 1
    assert all(row["remaining_live_bytes"] == 0 and row["malloc_calls"] == row["free_calls"] for row in allocations)
    dump(OUT / "correctness/verification.json", {"all_six_variants_release_and_debug": True,
         "patterns_per_variant": pattern_cases,
         "memcheck_errors": 0, "all_heap_blocks_freed": True, "invalid_commands_rejected": len(invalid),
         "sorted_but_corrupted_rejected": True, "all_vs_single_seed_fingerprints_match": True,
         "different_seed_changes_random_input": True, "allocations": allocations})


def native():
    assert json.loads((OUT / "correctness/verification.json").read_text())["memcheck_errors"] == 0
    native_batch("final", "aipcmf", [131072, 1048576], 5, 5, 20261026)


def profile():
    binary = OUT / "final/binaries/release.elf"
    (OUT / "profile").mkdir(exist_ok=False)
    for v in "aipcmf":
        data = OUT / f"profile/cachegrind-{v}.out"
        run(f"profile/cachegrind-{v}", ["taskset", "-c", CPU, "valgrind", "--tool=cachegrind", "--cache-sim=yes",
            "--branch-sim=yes", f"--cachegrind-out-file={data}", binary, "--variant", v, "-b", "-s", 20261026, 131072, 5], "final", binary)
        parse_timing(OUT / f"profile/cachegrind-{v}", v, 131072, 5, 20261026)
        run(f"profile/cg-annotate-{v}", ["cg_annotate", "--auto=yes", "--threshold=0.1", "--show-percs=no", data], "final", binary)
    nm = (OUT / "final/nm-release/stdout.txt").read_text()
    for v in "if":
        program = [binary, "--variant", v, "-b", "-s", 20261026, 1048576, 5]
        run(f"profile/perf-stat-{v}", ["taskset", "-c", CPU, args.perf, "stat", "-x", ",",
            "-e", "cycles:u,instructions:u,branches:u,branch-misses:u", "--"]+program, "final", binary)
        data = OUT / f"profile/perf-{v}.data"
        with tempfile.TemporaryDirectory(prefix="p2-stage-b-perf-") as folder:
            temporary = Path(folder) / "perf.data"
            run(f"profile/perf-record-{v}", ["taskset", "-c", CPU, args.perf, "record", "-e", "cycles:u", "-F", "999",
                "-o", temporary, "--"]+program, "final", binary)
            shutil.copy2(temporary, data)
            dump(OUT / f"profile/perf-record-{v}/copied-artifact.json", {"recorded_at": str(temporary),
                 "delivered_at": data.relative_to(OUT).as_posix(), "sha256": digest(data), "binary_sha256": digest(binary)})
        run(f"profile/perf-report-{v}", [args.perf, "report", "-i", data, "--stdio", "--header", "--no-children", "--sort=symbol"], "final", binary)
        candidates = [(int(size), name) for size, name in re.findall(r"^\d+\s+(\d+)\s+[Tt]\s+(\S+)$", nm, re.M)
                      if re.fullmatch(rf"(?:sort|recursive|merge|copy|alloc|free|insertion)_{v}(?:[.$].*)?", name)]
        target = max(candidates)[1]
        run(f"profile/perf-annotate-{v}", [args.perf, "annotate", "-i", data, "--stdio", "--stdio-color=never",
            "--percent-type=local-period", "-l", "-s", target], "final", binary)
        text = (OUT / f"profile/perf-annotate-{v}/stdout.txt").read_text()
        assert target in text and re.search(r"[1-9]\d*\.\d+\s*:", text)


if __name__ == "__main__":
    if args.phase == "audit": audit()
    elif args.phase == "select": select_base()
    elif args.phase == "tune": tune()
    elif args.phase == "confirm": confirm()
    elif args.phase == "final-build": final_build()
    elif args.phase == "verify": verify()
    elif args.phase == "native": native()
    elif args.phase == "profile": profile()
    else: raise SystemExit("Phase will be added after base and threshold decisions are recorded")
