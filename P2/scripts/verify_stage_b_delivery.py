"""Verify Stage B report, evidence manifests and optionally a fixed-commit ZIP."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--zip", type=Path)
parser.add_argument("--commit", help="also compare every ZIP file with this local Git commit")
args = parser.parse_args()
if args.commit and not args.zip:
    parser.error("--commit requires --zip")
archive = zipfile.ZipFile(args.zip) if args.zip else None
names = set(archive.namelist()) if archive else None


def raw(path):
    return archive.read("P2/" + path) if archive else (ROOT / path).read_bytes()


def text(path): return raw(path).decode("utf-8").replace("\r\n", "\n")
def read(path): return json.loads(raw(path))
def digest(path): return hashlib.sha256(raw(path)).hexdigest()


def files_under(prefix):
    if archive:
        return {name[3:] for name in names if name.startswith("P2/" + prefix + "/") and not name.endswith("/")}
    return {p.relative_to(ROOT).as_posix() for p in (ROOT / prefix).rglob("*") if p.is_file()}


BASE = "results/stage-b/"
summary = read(BASE + "summary/summary.json")
report, review = text("README.md"), text("REVIEW.md")
for item in ("Checkoff Item 1", "Checkoff Item 2", *(f"Write-up {i}" for i in range(1, 8))):
    assert f"## {item}\n" in report, item
native_tables = text(BASE + "summary/native-tables.md").strip()
assert native_tables in report
rows = summary["formal_native"]
assert len(rows) == 24 and summary["formal_sort_calls"] == 600
trial_rows = list(csv.DictReader(io.StringIO(text(BASE + "summary/native-trials.csv"))))
assert len(trial_rows) == 600
for row in rows:
    values = f'{row["median_ms"]:.3f}［{row["min_ms"]:.3f}–{row["max_ms"]:.3f}］ | {row["speedup_vs_a"]:.3f} | {row["speedup_vs_previous"]:.3f}（{row["previous_variant"]}）'
    assert values in report, row
for row in summary["cachegrind"]:
    cells = [f'{row[k]:,}' for k in ("Ir", "D_refs", "D1_misses", "LLd_misses")]
    cells += [f'{row["I1mr"]:,} / {row["ILmr"]:,}', f'{row["Bc"]:,} / {row["Bcm"]:,}']
    assert f'| {row["variant"]} | ' + " | ".join(cells) + " |" in report
    assert f'| {row["variant"]} | {row["sort_file_Ir"]:,} | {row["allocator_file_Ir"]:,} | {summary["inline"]["private_text_bytes"][row["variant"]]} |' in report
for row in summary["allocations"]:
    values = [f'{row[k]:,}' for k in ("malloc_calls", "free_calls", "requested_bytes", "peak_live_bytes")]
    assert f'| {row["variant"]} | ' + " | ".join(values) + " |" in report
for k in (8, 16, 32, 64, 128):
    times = {row["input"]: row["median_ms"] for row in summary["tuning"] if row["variant"] == f"k{k}"}
    assert f'| {k} | {times["random"]:.3f} | {times["inverted"]:.3f} | {summary["tuning_scores"][f"k{k}"]:.5f} |' in report
for event, title in (("cycles:u", "cycles"), ("instructions:u", "instructions"), ("branches:u", "branches"), ("branch-misses:u", "branch-misses")):
    values = [f'{summary["perf"][v]["user_hardware_counts_whole_process"][event]:,}' for v in "if"]
    assert f"| {title} | " + " | ".join(values) + " |" in report
assert summary["chosen_base"] == "a" and summary["chosen_cutoff"] == 16
assert summary["stage_a_offline_recompute_unchanged"]

hashes = 0
for phase in ("selection", "tuning", "final"):
    prefix = BASE + phase + "/"
    manifest = read(prefix + "build-manifest.json")
    assert manifest["sources"] == read(prefix + "source-manifest.json")
    actual_sources = {p[len(prefix):] for p in files_under(prefix + "source")}
    actual_binaries = {p[len(prefix):] for p in files_under(prefix + "binaries")}
    assert set(manifest["sources"]) == actual_sources
    assert set(manifest["binaries"]) == actual_binaries
    for path, expected in {**manifest["sources"], **manifest["binaries"]}.items():
        assert digest(prefix + path) == expected, prefix + path
        hashes += 1
    if phase == "final":
        for path, expected in manifest["sources"].items():
            assert digest(path.removeprefix("source/")) == expected, path
for path in ("sort_a.c", "util.c", "util.h"):
    assert raw("homework/" + path) == raw("results/stage-a/source/homework/" + path)

for variant in "if":
    prefix = BASE + f"profile/perf-record-{variant}/"
    copied = read(prefix + "copied-artifact.json")
    assert digest(BASE + copied["delivered_at"]) == copied["sha256"]
    assert copied["binary_sha256"] == digest(BASE + "final/binaries/release.elf")
    samples = int(re.search(r"\((\d+) samples\)", text(prefix + "stderr.txt"))[1])
    assert samples == summary["perf"][variant]["samples"]
    assert f"**{samples} 个样本、丢失 0 个**" in report
    assert summary["perf"][variant]["lost_samples"] == 0

links = 0
for document in (report, review):
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", document):
        if "://" in target:
            continue
        path = PurePosixPath(target.split("#")[0])
        assert not path.is_absolute() and ".." not in path.parts, target
        if archive:
            key = "P2/" + str(path)
            assert key in names or any(p.startswith(key.rstrip("/") + "/") for p in names), target
        else:
            assert (ROOT / str(path)).exists(), target
        links += 1

commit_files = None
if archive:
    assert archive.testzip() is None
    for name in names:
        assert not PurePosixPath(name).is_absolute() and ".." not in PurePosixPath(name).parts
        assert ".git" not in PurePosixPath(name).parts and "__pycache__" not in PurePosixPath(name).parts
        assert not re.search(r"P2-Stage[AB]-.*\.zip$", name, re.I), name
if args.commit:
    assert re.fullmatch(r"[0-9a-f]{40}", args.commit), "Use the full commit SHA"
    assert archive.comment.decode("ascii") == args.commit, "Git archive ZIP commit comment mismatch"
    tree = subprocess.check_output(["git", "ls-tree", "-rz", "--full-tree", args.commit], cwd=ROOT.parent)
    expected_blobs = {}
    for entry in tree.split(b"\0"):
        if entry:
            metadata, name = entry.split(b"\t", 1)
            mode, kind, object_id = metadata.split()
            assert kind == b"blob", "Unexpected submodule in delivery"
            expected_blobs[name.decode("utf-8")] = object_id.decode("ascii")
    assert {n for n in names if not n.endswith("/")} == set(expected_blobs), "ZIP file set differs from commit"
    for name, expected in expected_blobs.items():
        content = archive.read(name)
        actual = hashlib.sha1(f"blob {len(content)}\0".encode("ascii") + content).hexdigest()
        assert actual == expected, name
    commit_files = len(expected_blobs)

print(json.dumps({"all_nine_answers_present": True, "stage_b_report_tables_match": True,
    "native_trials": len(trial_rows), "manifest_hashes_checked": hashes, "links_checked": links,
    "working_sources_equal_final_snapshot": True, "perf_samples": {v:summary["perf"][v]["samples"] for v in "if"},
    "checked_zip": str(args.zip) if args.zip else None, "commit": args.commit,
    "zip_files_equal_commit": commit_files}, indent=2))
if archive:
    archive.close()
