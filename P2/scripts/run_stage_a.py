"""Reproduce Stage A; each command preserves its raw output without overwriting.

Run build, preflight, checkoff1, writeup1, checkoff2 in that order, or use all.
Use --out /new/empty/directory for an independent reproduction.
"""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import statistics
import tempfile
import zipfile

from capture import capture

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("phase", choices=["build", "preflight", "checkoff1", "writeup1", "checkoff2", "all"])
parser.add_argument("--out", type=Path, default=ROOT / "results" / "stage-a")
parser.add_argument("--perf", default=os.environ.get("P2_PERF", "perf"), help="perf executable with libelf/DWARF support")
parser.add_argument("--resume", action="store_true", help="legacy option; disabled because its provenance check was insufficient")
args = parser.parse_args()
if args.resume:
    parser.error("Legacy resume is disabled: use a fresh --out directory and the preserved Stage A source snapshot.")
OUT = args.out.resolve()
SRC, BIN = OUT / "source", OUT / "binaries"
CPU = min(os.sched_getaffinity(0))
PERF = args.perf
CONFIGS = [(4096, 1000000), (262144, 1000000), (10000000, 1000000), (33554432, 1000000),
           (10000000, 10000000), (10000000, 100000000)]


def run(name, argv, cwd=None, expected=0):
    directory = OUT / name
    return capture(directory, argv, cwd or ROOT, expected)


def binary(mode):
    return BIN / f"sort-{mode}.elf"


def sum_binary(u, n):
    return BIN / f"sum-u{u}-n{n}.elf"


def record_perf(name, destination, program, frequency, affinity=False):
    # perf's direct write from its ring buffer fails with EFAULT on this DrvFS.
    # Record on Linux ext4, then copy the completed regular file into the result.
    with tempfile.TemporaryDirectory(prefix="p2-perf-") as temporary:
        temporary_data = Path(temporary) / "perf.data"
        prefix = ["taskset", "-c", CPU] if affinity else []
        run(name, prefix + [PERF, "record", "-e", "cycles:u", "-F", frequency,
                           "-o", temporary_data, "--"] + list(program))
        shutil.copy2(temporary_data, destination)
        (OUT / name / "copied-artifact.json").write_text(json.dumps({
            "recorded_at": str(temporary_data), "delivered_at": str(destination.relative_to(OUT)),
            "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}, indent=2) + "\n")


def check_sort_output(name, trials):
    directory = OUT / name
    output = (directory / "stdout.txt").read_text()
    errors = (directory / "stderr.txt").read_text()
    timings = re.findall(r"TIMING input=(\w+) trial=(\d+) function=(\w+) seconds=([\d.]+)", output)
    assert len(timings) == 2 * trials, (name, len(timings))
    averages = [float(v) for v in re.findall(r"Elapsed execution time: ([\d.]+)", output)]
    assert len(averages) == 2 and output.count("Arrays are sorted: yes") == 2
    assert "FAIL" not in errors
    for kind, reported in zip(("random", "inverted"), averages):
        subset = [(int(t), float(sec)) for k, t, func, sec in timings if k == kind and func == "sort_a"]
        assert [t for t, sec in subset] == list(range(1, trials + 1))
        assert all(sec > 0 for t, sec in subset)
        assert abs(statistics.mean(sec for t, sec in subset) - reported) < 1.1e-9
    return timings


def build():
    SRC.mkdir(parents=True, exist_ok=False)
    BIN.mkdir(exist_ok=False)
    for section in ("homework", "recitation"):
        (SRC / section).mkdir()
        for path in (ROOT / "results/stage-a/source" / section).iterdir():
            if path.suffix in (".c", ".h") or path.name == "Makefile":
                shutil.copy2(path, SRC / section / path.name)
    with zipfile.ZipFile(ROOT / "original" / "MIT6_172F18_hw2.zip") as archive:
        for name in ("homework/sort_a.c", "recitation/isort.c"):
            assert archive.read(name) == (SRC / name).read_bytes(), name
    for mode, debug in (("debug", "1"), ("release", "0")):
        run(f"build/homework-{mode}", ["make", "--always-make", f"DEBUG={debug}"], SRC / "homework")
        shutil.copy2(SRC / "homework" / "sort", binary(mode))
    (SRC / "homework" / "sort").unlink()
    run("build/isort-debug", ["make", "--always-make", "isort", "DEBUG=1"], SRC / "recitation")
    shutil.copy2(SRC / "recitation" / "isort", BIN / "isort-debug.elf")
    (SRC / "recitation" / "isort").unlink()
    run("build/sum-default", ["make", "--always-make", "sum", "DEBUG=0"], SRC / "recitation")
    shutil.copy2(SRC / "recitation" / "sum", sum_binary(10000000, 100000000))
    (SRC / "recitation" / "sum").unlink()
    for u, n in [(257, 2000)] + CONFIGS[:-1]:
        run(f"build/sum-u{u}-n{n}", ["clang", "-Wall", "-O1", "-DNDEBUG", "-g",
            f"-DSUM_U={u}", f"-DSUM_N={n}", "sum.c", "-o", sum_binary(u, n), "-lrt"], SRC / "recitation")
    manifest = {str(path.relative_to(OUT)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(OUT.rglob("*")) if path.is_file() and
                (path.parent == BIN or (SRC in path.parents and path.suffix != ".o"))}
    (OUT / "build-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def preflight():
    checks = []
    for mode in ("debug", "release"):
        for size, seed in ((1, 1), (2, 42), (31, 1), (32, 42), (33, 42), (1000, 42)):
            name = f"preflight/correct-{mode}-n{size}-s{seed}"
            run(name, [binary(mode), "-s", seed, size, 1])
            check_sort_output(name, 1)
            checks.append(name)
    random_arrays = []
    for label, seed in (("a", 42), ("b", 42), ("c", 43)):
        name = f"preflight/seed-{label}"
        run(name, [binary("debug"), "-b", "-p", "-s", seed, 16, 1])
        text = (OUT / name / "stdout.txt").read_text()
        random_arrays.append(re.findall(r"Data before sort\n([^\n]+)", text)[0])
    assert random_arrays[0] == random_arrays[1] and random_arrays[0] != random_arrays[2]
    fault = OUT / "preflight" / "fault-sort.c"
    fault.write_text("#include <stdint.h>\nvoid sort_a(uint32_t* a,int p,int r) { for(int i=p;i<=r;i++) a[i]=0; }\n")
    run("preflight/build-fault", ["clang", "-O0", "-g", SRC / "homework/main.c",
        SRC / "homework/tests.c", SRC / "homework/util.c", fault,
        "-o", OUT / "preflight/fault.elf", "-lrt", "-lm"])
    run("preflight/reject-corrupted-elements", [OUT / "preflight/fault.elf", "-b", "-s", 42, 32, 1], expected=1)
    assert "Reference mismatch" in (OUT / "preflight/reject-corrupted-elements/stderr.txt").read_text()
    run("preflight/reject-invalid-size", [binary("release"), 0, 1], expected=1)
    subarray = OUT / "preflight" / "subarray.c"
    subarray.write_text('#include "tests.h"\nextern void sort_a(data_t*,int,int);\n'
        'extern void test_subarray(int,int,int,struct testFunc_t*,int);\n'
        'int main(void) { struct testFunc_t f={sort_a,"sort_a"}; set_random_seed(42); '
        'test_subarray(1,33,1,&f,1); return 0; }\n')
    run("preflight/build-subarray", ["clang", "-O0", "-g", "-I", SRC / "homework",
        subarray, SRC / "homework/tests.c", SRC / "homework/util.c", SRC / "homework/sort_a.c",
        "-o", OUT / "preflight/subarray.elf", "-lrt", "-lm"])
    run("preflight/subarray", [OUT / "preflight/subarray.elf"])
    run("preflight/pilot-debug", [binary("debug"), "-b", "-s", 42, 131072, 5])
    run("preflight/pilot-release", [binary("release"), "-b", "-s", 42, 131072, 5])
    check_sort_output("preflight/pilot-debug", 5)
    check_sort_output("preflight/pilot-release", 5)
    libc = ctypes.CDLL(None)
    libc.rand_r.argtypes = [ctypes.POINTER(ctypes.c_uint)]
    seed, value = ctypes.c_uint(42), 0
    for _ in range(2000):
        value = (value + libc.rand_r(ctypes.byref(seed)) % 257) & 0xffffffff
    run("preflight/sum-native", [sum_binary(257, 2000)])
    assert f"Value = {value}" in (OUT / "preflight/sum-native/stdout.txt").read_text()
    data = OUT / "preflight" / "cachegrind.out"
    run("preflight/cachegrind", ["valgrind", "--tool=cachegrind", "--cache-sim=yes", "--branch-sim=yes",
        f"--cachegrind-out-file={data}", sum_binary(257, 2000)])
    assert "summary:" in data.read_text() and "Bcm" in data.read_text()
    run("preflight/perf-stat", [PERF, "stat", "-e", "cycles:u,instructions:u,branches:u,branch-misses:u",
        "--", BIN / "isort-debug.elf", 5000, 2])
    finish_perf_preflight()
    (OUT / "preflight/verification.json").write_text(json.dumps({
        "correctness_cases": checks, "seed_repeatable_and_effective": True,
        "sorted_but_corrupted_rejected_with_exit_1": True, "subarray_checked": True,
        "timing_averages_match_separate_trial_records": True,
        "sum_uint32_reference": value, "cachegrind_cache_and_branch_events": True,
        "perf_real_samples_readable_by_report_and_annotate": True}, indent=2) + "\n")


def finish_perf_preflight(reuse=None):
    perf_data = reuse or OUT / "preflight" / "perf-nativefs.data"
    if reuse is None:
        record_perf("preflight/perf-record-nativefs", perf_data, [BIN / "isort-debug.elf", 5000, 2], 499)
    run("preflight/perf-report-symbols", [PERF, "report", "-i", perf_data, "--stdio", "--no-children", "--sort=symbol"])
    run("preflight/perf-annotate-symbols", [PERF, "annotate", "-i", perf_data, "--stdio", "--stdio-color=never", "-l", "-s", "isort"])
    assert "isort" in (OUT / "preflight/perf-report-symbols/stdout.txt").read_text()
    assert re.search(r"[1-9]\d*\.\d+\s*:", (OUT / "preflight/perf-annotate-symbols/stdout.txt").read_text())


def checkoff1():
    folder = OUT / "checkoff1"
    folder.mkdir(exist_ok=args.resume)
    data = folder / "perf.data"
    run("checkoff1/perf-stat", ["taskset", "-c", CPU, PERF, "stat", "-x", ",",
        "-e", "cycles:u,instructions:u,branches:u,branch-misses:u", "--", BIN / "isort-debug.elf", 10000, 10])
    record_perf("checkoff1/perf-record", data, [BIN / "isort-debug.elf", 10000, 10], 999, affinity=True)
    run("checkoff1/perf-report", [PERF, "report", "-i", data, "--stdio", "--header", "--no-children", "--sort=symbol"])
    run("checkoff1/perf-annotate", [PERF, "annotate", "-i", data, "--stdio", "--stdio-color=never",
        "--percent-type=local-period", "-l", "-s", "isort"])
    run("checkoff1/perf-script", [PERF, "script", "-i", data, "-F", "event,ip,sym,symoff,srcline,period"])
    run("checkoff1/disassembly", ["objdump", "-dSl", BIN / "isort-debug.elf"])
    run("checkoff1/build-id", ["readelf", "-n", BIN / "isort-debug.elf"])


def writeup1():
    folder = OUT / "writeup1"
    folder.mkdir(exist_ok=args.resume)
    (folder / "parameters.json").write_text(json.dumps({"N": 131072, "R": 5, "initial_rand_r_seed": 42,
        "native_independent_runs_per_mode": 5, "cpu_affinity": CPU,
        "timed_sort_calls_per_process": 10, "input_types": ["random", "inverted"],
        "timing_boundary": "CLOCK_MONOTONIC immediately around sort_a(data,0,N-1)",
        "cachegrind_scope": "whole process, including generation, allocation, qsort reference and IO"}, indent=2) + "\n")
    for iteration in range(1, 6):
        modes = ("debug", "release") if iteration % 2 else ("release", "debug")
        for mode in modes:
            name = f"writeup1/native-{mode}-{iteration}"
            run(name, ["taskset", "-c", CPU, binary(mode), "-b", "-s", 42, 131072, 5])
            check_sort_output(name, 5)
    for mode in ("debug", "release"):
        data = folder / f"cachegrind-{mode}.out"
        run(f"writeup1/cachegrind-{mode}", ["taskset", "-c", CPU, "valgrind", "--tool=cachegrind",
            "--cache-sim=yes", "--branch-sim=yes", f"--cachegrind-out-file={data}", binary(mode), "-b", "-s", 42, 131072, 5])
        check_sort_output(f"writeup1/cachegrind-{mode}", 5)
        run(f"writeup1/annotate-{mode}", ["cg_annotate", "--auto=yes", "--threshold=0.1", "--show-percs=no", data])


def checkoff2():
    folder = OUT / "checkoff2"
    folder.mkdir(exist_ok=args.resume)
    (folder / "parameters.json").write_text(json.dumps({"seed": 42, "accumulator": "original uint32_t, modulo 2^32",
        "configs": [{"U": u, "N": n, "array_bytes": 4*u} for u, n in CONFIGS],
        "scope": "whole process, including initialization, rand_r, modulo and output"}, indent=2) + "\n")
    for u, n in CONFIGS:
        label = f"u{u}-n{n}"
        run(f"checkoff2/native-{label}", [sum_binary(u, n)])
        data = folder / f"cachegrind-{label}.out"
        run(f"checkoff2/cachegrind-{label}", ["valgrind", "--tool=cachegrind", "--cache-sim=yes", "--branch-sim=yes",
            f"--cachegrind-out-file={data}", sum_binary(u, n)])
        native = (folder / f"native-{label}/stdout.txt").read_text()
        simulated = (folder / f"cachegrind-{label}/stdout.txt").read_text()
        assert native == simulated, label
        run(f"checkoff2/annotate-{label}", ["cg_annotate", "--auto=yes", "--threshold=0.1", "--show-percs=no", data])


phases = {"build": build, "preflight": preflight, "checkoff1": checkoff1,
          "writeup1": writeup1, "checkoff2": checkoff2}
if __name__ == "__main__":
    for phase in phases if args.phase == "all" else [args.phase]:
        phases[phase]()
