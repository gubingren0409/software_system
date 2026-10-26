"""Inventory the actual environment and reproduce the unmodified build failure."""
import json
from pathlib import Path
import subprocess
import zipfile

from capture import capture

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "stage-a"
ENV = OUT / "environment"
ENV.mkdir(parents=True, exist_ok=True)
for name, argv in [
    ("os", ["cat", "/etc/os-release"]), ("kernel", ["uname", "-a"]),
    ("cpu", ["lscpu"]), ("clang", ["clang", "--version"]),
    ("perf", ["perf", "--version"]), ("valgrind", ["valgrind", "--version"]),
    ("memory", ["free", "-h"]), ("disk", ["df", "-h", str(ROOT)]),
    ("perf-paranoid", ["cat", "/proc/sys/kernel/perf_event_paranoid"]),
    ("perf-kptr", ["cat", "/proc/sys/kernel/kptr_restrict"]),
    ("identity", ["id"]), ("sudo-check", ["sudo", "-n", "true"]),
    ("pmu-events", ["perf", "stat", "-e", "cycles:u,instructions:u,branches:u,branch-misses:u", "--", "true"]),
    ("cpu-topology", ["lscpu", "-e=CPU,CORE,SOCKET,NODE,ONLINE"]),
    ("cache-sysfs", ["sh", "-c", "for d in /sys/devices/system/cpu/cpu0/cache/index*; do echo $d; cat $d/level $d/type $d/size $d/coherency_line_size $d/ways_of_associativity; done"]),
]:
    capture(ENV / name, argv, expected=None)
(ROOT / "lscpu.txt").write_bytes((ENV / "cpu" / "stdout.txt").read_bytes())
with zipfile.ZipFile(ROOT / "original" / "MIT6_172F18_hw2.zip") as archive:
    names = [n for n in archive.namelist() if n.startswith(("homework/", "recitation/")) and not n.endswith("/")]
    mismatches = [n for n in names if archive.read(n) != (ROOT / n).read_bytes()]
    (ENV / "original-inventory.json").write_text(json.dumps({"files": names, "mismatches_before_edits": mismatches}, indent=2) + "\n")
    if mismatches:
        raise RuntimeError(f"Unexpected edits before original build: {mismatches}")
capture(OUT / "original-build" / "homework-debug", ["make", "DEBUG=1"], ROOT / "homework", expected=None)
capture(OUT / "original-build" / "recitation-debug", ["make", "isort", "DEBUG=1"], ROOT / "recitation")
