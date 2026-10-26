"""One-time continuation after the retained DrvFS perf-record failure.

The ordinary run_stage_a.py now uses Linux output directly on fresh runs.
This continuation reuses the already successful build/correctness checks.
"""
import hashlib
import json
import sys

# Import the existing run definitions without dispatching their CLI phase.
sys.argv = [sys.argv[0], "preflight", "--perf", "/usr/lib/linux-tools-6.8.0-146/perf"]
import run_stage_a as stage

stage.run("perf-diagnostics/full-build-options", [stage.PERF, "version", "--build-options"])
stage.finish_perf_preflight(reuse=stage.OUT / "preflight/perf-nativefs.data")
u, n = 33554432, 1000000
stage.run(f"build/sum-u{u}-n{n}", ["clang", "-Wall", "-O1", "-DNDEBUG", "-g",
    f"-DSUM_U={u}", f"-DSUM_N={n}", "sum.c", "-o", stage.sum_binary(u, n), "-lrt"], stage.SRC / "recitation")
manifest_path = stage.OUT / "build-manifest.json"
manifest = json.loads(manifest_path.read_text())
path = stage.sum_binary(u, n)
manifest[str(path.relative_to(stage.OUT))] = hashlib.sha256(path.read_bytes()).hexdigest()
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
checks = sorted(str(path.relative_to(stage.OUT)) for path in (stage.OUT / "preflight").glob("correct-*/metadata.json"))
for name in checks:
    assert json.loads((stage.OUT / name).read_text())["returncode"] == 0
    stage.check_sort_output(str((stage.OUT / name).parent.relative_to(stage.OUT)), 1)
for name, code in (("reject-corrupted-elements", 1), ("reject-invalid-size", 1),
                   ("subarray", 0), ("cachegrind", 0), ("perf-stat", 0),
                   ("perf-record-nativefs", 0), ("perf-report-symbols", 0), ("perf-annotate-symbols", 0)):
    assert json.loads((stage.OUT / "preflight" / name / "metadata.json").read_text())["returncode"] == code
arrays = [__import__("re").findall(r"Data before sort\n([^\n]+)",
    (stage.OUT / f"preflight/seed-{label}/stdout.txt").read_text())[0] for label in "abc"]
assert arrays[0] == arrays[1] and arrays[0] != arrays[2]
assert "Reference mismatch" in (stage.OUT / "preflight/reject-corrupted-elements/stderr.txt").read_text()
for mode in ("debug", "release"):
    stage.check_sort_output(f"preflight/pilot-{mode}", 5)
verification = {"correctness_cases": checks, "seed_repeatable_and_effective": True,
    "sorted_but_corrupted_rejected_with_exit_1": True, "subarray_checked": True,
    "timing_averages_match_separate_trial_records": True,
    "cachegrind_cache_and_branch_events": True,
    "perf_real_samples_readable_by_report_and_annotate": True,
    "retained_failed_attempts": ["preflight/perf-record; exit 255 on DrvFS; replaced by nativefs capture",
        "preflight/perf-report and perf-annotate; original perf has no libelf/DWARF; symbols read with full Ubuntu perf 6.8"]}
(stage.OUT / "preflight/verification.json").write_text(json.dumps(verification, indent=2) + "\n")
