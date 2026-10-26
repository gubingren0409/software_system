"""Check report tables, links and preserved binaries; optionally check a Git ZIP."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--zip", type=Path)
args = parser.parse_args()
archive = zipfile.ZipFile(args.zip) if args.zip else None


def read(name):
    return archive.read("P2/" + name) if archive else (ROOT / name).read_bytes()


summary = json.loads(read("results/stage-a/summary/summary.json"))
report = read("README.md").decode("utf-8")
for value in summary["checkoff1"]["hardware_user_events"].values():
    assert f"{value:,}" in report
for row in summary["checkoff2"]["configs"]:
    expected = f'| {row["U"]:,} | {row["N"]:,} | {row["D_refs"]:,} | {row["D1_misses"]:,} | {row["D1_rate_percent"]:.4f}% | {row["LLd_misses"]:,} | {row["LLd_rate_percent"]:.4f}% |'
    assert expected in report, expected
for kind in ("random", "inverted"):
    native = summary["writeup1"]["native"]
    fields = []
    for mode in ("debug", "release"):
        data = native[mode][kind]
        fields.append(f'{1000*data["median_seconds"]:.3f}［{1000*data["min_seconds"]:.3f}–{1000*data["max_seconds"]:.3f}］')
    ratio = summary["writeup1"]["native_speedup_debug_over_release"][kind]
    assert f'| {kind} | {fields[0]} | {fields[1]} | {ratio:.2f} |' in report
for mode in ("debug", "release"):
    cg = summary["writeup1"]["cachegrind"][mode]
    totals = cg["whole_process"]
    for value in (totals["Ir"], cg["sort_a_c_exclusive"]["Ir"], totals["Dr"]+totals["Dw"],
                  totals["D1mr"]+totals["D1mw"], totals["DLmr"]+totals["DLmw"], totals["Bc"], totals["Bcm"]):
        assert f"{value:,}" in report
manifest = json.loads(read("results/stage-a/build-manifest.json"))
for name, expected in manifest.items():
    assert hashlib.sha256(read("results/stage-a/" + name)).hexdigest() == expected, name
for folder, copied_name in (("checkoff1", "perf-record"), ("preflight", "perf-record-nativefs")):
    copied = json.loads(read(f"results/stage-a/{folder}/{copied_name}/copied-artifact.json"))
    assert hashlib.sha256(read("results/stage-a/" + copied["delivered_at"])).hexdigest() == copied["sha256"]
for line in read("original/SHA256SUMS").decode().splitlines():
    expected, name = line.split()
    assert hashlib.sha256(read("original/" + name)).hexdigest() == expected, name
links = 0
for name in ("README.md", "REVIEW.md"):
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", read(name).decode("utf-8")):
        if "://" in target:
            continue
        target = target.split("#")[0]
        if archive:
            key = "P2/" + target
            assert key in archive.namelist() or any(p.startswith(key.rstrip("/")+"/") for p in archive.namelist()), key
        else:
            assert (ROOT / target).exists(), target
        links += 1
result = {"report_tables_match_derived_data": True, "valid_report_and_review_links": links,
          "source_and_binary_hashes_checked": len(manifest), "perf_copies_match": True,
          "original_download_hashes_match": True, "checked_zip": str(args.zip) if args.zip else None}
print(json.dumps(result, indent=2))
if archive:
    archive.close()
