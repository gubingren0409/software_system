"""Retain diagnostics for the perf writer/symbolization failures."""
import json
import os
from pathlib import Path
import shutil
import subprocess

from capture import capture

root = Path(__file__).resolve().parents[1]
out = root / "results/stage-a/perf-diagnostics"
out.mkdir(exist_ok=False)
perf = shutil.which("perf")
(out / "paths.json").write_text(json.dumps({"perf": perf, "realpath": os.path.realpath(perf)}, indent=2) + "\n")
for name, command in [
    ("build-options", ["perf", "version", "--build-options"]),
    ("file", ["file", os.path.realpath(perf)]),
    ("ldd", ["ldd", os.path.realpath(perf)]),
    ("packages", ["dpkg-query", "-W", "libelf-dev", "libdw-dev", "linux-tools-common", "linux-tools-generic"]),
    ("usr-lib-tools", ["find", "/usr/lib", "-path", "*/linux-tools*/*perf", "-type", "f"]),
    ("local-tools", ["find", "/home/gubingren", "-maxdepth", "5", "-type", "f", "-name", "perf"]),
    ("buildid", ["readelf", "-n", root / "results/stage-a/binaries/isort-debug.elf"]),
    ("header", ["perf", "report", "--header-only", "-i", root / "results/stage-a/preflight/perf-nativefs.data"]),
]:
    capture(out / name, command, expected=None)
