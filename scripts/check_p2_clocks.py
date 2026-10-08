"""Read-only clock-domain probe; no target runs and no system clock changes."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autotuner.core import atomic_write_json, sha256_file, utc_now


def clocks() -> dict[str, int]:
    return {"realtime_ns": time.time_ns(), "monotonic_ns": time.monotonic_ns(),
            "raw_ns": time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW),
            "boottime_ns": time.clock_gettime_ns(time.CLOCK_BOOTTIME)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--intervals", type=int, default=5)
    parser.add_argument("--seconds", type=float, default=1.0)
    parser.add_argument("--skip-host", action="store_true")
    args = parser.parse_args()
    if args.intervals < 1 or args.seconds <= 0 or args.intervals * args.seconds > 30:
        parser.error("probe sleep budget must be in (0, 30] seconds")
    intervals = []
    for _ in range(args.intervals):
        before = clocks()
        time.sleep(args.seconds)
        after = clocks()
        delta = {key.removesuffix("_ns") + "_seconds": (after[key] - before[key]) / 1e9
                 for key in before}
        intervals.append({"before": before, "after": after, "delta": delta})
    host_probe = "$a=[DateTimeOffset]::UtcNow; $s=[Diagnostics.Stopwatch]::StartNew(); " \
                 "Start-Sleep -Seconds 10; $s.Stop(); $b=[DateTimeOffset]::UtcNow; " \
                 "[pscustomobject]@{before=$a.ToString('o'); after=$b.ToString('o'); " \
                 "utc_seconds=($b-$a).TotalSeconds; stopwatch_seconds=$s.Elapsed.TotalSeconds; " \
                 "stopwatch_frequency=[Diagnostics.Stopwatch]::Frequency} | ConvertTo-Json -Compress"
    commands = [["cat", "/sys/devices/system/clocksource/clocksource0/current_clocksource",
                 "/sys/devices/system/clocksource/clocksource0/available_clocksource"],
                ["timedatectl", "show", "-p", "NTPSynchronized", "-p", "CanNTP", "-p", "NTP"],
                ]
    if not args.skip_host:
        commands.append(["/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe",
                         "-NoProfile", "-Command", host_probe])
    recorded = []
    for command in commands:
        result = subprocess.run(command, capture_output=True, text=True, timeout=25, check=False)
        recorded.append({"command": command, "stdout": result.stdout, "stderr": result.stderr,
                         "returncode": result.returncode, "captured_at": utc_now()})
    result = {"schema": "p2-clock-probe-v1", "captured_at": utc_now(),
              "script_sha256": sha256_file(Path(__file__)),
              "command": [sys.executable, *sys.argv], "wsl_intervals": intervals,
              "clock_info": {name: str(time.get_clock_info(name)) for name in ("time", "monotonic")},
              "commands": recorded, "system_settings_modified": False}
    atomic_write_json(args.output, result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
