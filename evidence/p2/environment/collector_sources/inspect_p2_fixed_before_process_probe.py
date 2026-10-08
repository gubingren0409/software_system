"""Collect narrowly scoped, read-only tool and memory diagnostics."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autotuner.core import atomic_write_json, resource_snapshot, sha256_file, utc_now


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--compiler-optimizers", action="store_true")
    args = parser.parse_args()
    powershell = "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
    host = "Add-Type -AssemblyName System.Windows.Forms; " \
           "$power=[System.Windows.Forms.SystemInformation]::PowerStatus; " \
           "$os=Get-CimInstance Win32_OperatingSystem; $vm=Get-Process VmmemWSL -ErrorAction SilentlyContinue; " \
           "[pscustomobject]@{Timestamp=[DateTimeOffset]::Now.ToString('o'); " \
           "TotalBytes=[int64]$os.TotalVisibleMemorySize*1KB; FreeBytes=[int64]$os.FreePhysicalMemory*1KB; " \
           "WslWorkingSetBytes=$vm.WorkingSet64; WslPrivateBytes=$vm.PrivateMemorySize64; " \
           "PowerShellVersion=$PSVersionTable.PSVersion.ToString(); " \
           "PowerLineStatus=$power.PowerLineStatus.ToString(); " \
           "BatteryChargeStatus=$power.BatteryChargeStatus.ToString(); " \
           "BatteryLifePercent=$power.BatteryLifePercent} | ConvertTo-Json -Compress"
    commands = [[sys.executable, "--version"], ["/usr/bin/gcc", "--version"], ["git", "--version"],
                ["uname", "-a"], ["cat", "/etc/os-release"], ["cat", "/proc/meminfo"],
                ["ps", "-eo", "pid,etimes,rss,comm", "--sort=-rss"],
                [powershell, "-NoProfile", "-Command", host]]
    if args.compiler_optimizers:
        commands.extend([["/usr/bin/gcc", "-Q", f"-O{level}", "--help=optimizers"] for level in range(4)])
    records = []
    for command in commands:
        captured = utc_now()
        result = subprocess.run(command, text=True, capture_output=True, timeout=30, check=False)
        records.append({"captured_at": captured, "command": command, "stdout": result.stdout,
                        "stderr": result.stderr, "returncode": result.returncode})
    record = {"captured_at": utc_now(), "collector_sha256": sha256_file(Path(__file__)),
              "command_argv": [sys.executable, *sys.argv], "compiler_sha256": sha256_file(Path("/usr/bin/gcc")),
              "commands": records, "wsl_resource_snapshot": resource_snapshot(),
              "system_settings_modified": False, "other_applications_terminated": False}
    atomic_write_json(args.output, record)
    print(json.dumps({"output": str(args.output), "commands": len(records),
                      "nonzero_commands": sum(item["returncode"] != 0 for item in records)}))


if __name__ == "__main__":
    main()
