"""One-off read-only collection for this batch. Does not resync or probe clocks.

Run from the Windows project root. Uses the already-reviewed capture helper;
every child has a timeout, raw streams, PID, exit code, and QPC/UTC endpoints.
No installation, time/clocksource setters, service starts, or matrix execution.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
from scripts.p3_clock_contract import POWERSHELL, atomic_write_json, capture, load, wsl_path
from scripts.start_p3_first_seed import auxiliary_identity
from autotuner.core import utc_now
from autotuner.session import valid_formal_gate

OUT = Path(__file__).resolve().parent
AUX = "fa597017c2317772a0f7f34faa75194ffecec8f2"
OPS = OUT / "operations"
BATCH = OUT.name


def main():
    if (OUT / "diagnostic_commands.json").exists():
        raise ValueError("This one-off collection has already started; do not overwrite")
    windows = lambda code: [POWERSHELL, "-NoProfile", "-Command", code]
    wsl = lambda *command: ["wsl.exe", "-d", "Ubuntu-24.04", "--cd", "/tmp", "--", "env", "LC_ALL=C", *command]
    service = (
        "$ErrorActionPreference='Stop'; Get-Command Get-FileHash -ErrorAction Stop | Out-Null; "
        "$s=Get-Service W32Time; $o=Get-CimInstance Win32_OperatingSystem; "
        "$cs=Get-CimInstance Win32_Service -Filter \"Name='W32Time'\"; "
        "$admin=([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator); "
        "[pscustomobject]@{captured_at=[DateTimeOffset]::Now.ToString('o');service_name=$s.Name;"
        "status=$s.Status.ToString();start_type=$s.StartType.ToString();start_mode=$cs.StartMode;"
        "exit_code=$cs.ExitCode;process_id=$cs.ProcessId;current_token_administrator=$admin;"
        "windows_version=$o.Version;windows_build=$o.BuildNumber;"
        "windows_boot=$o.LastBootUpTime.ToString('o');"
        "full_build=(Get-Item 'C:/Windows/System32/ntoskrnl.exe').VersionInfo.FileVersion;"
        "system_settings_modified=$false} | ConvertTo-Json -Depth 5"
    )
    event_scope = (
        "$ErrorActionPreference='Stop'; $from=[datetime]'2026-10-09T16:00:00'; $to=Get-Date; "
        "$systemError=$null; $operationalError=$null; $logState=$null; $system=@(); $operational=@(); "
        "try {$system=@(Get-WinEvent -FilterHashtable @{LogName='System';StartTime=$from;EndTime=$to;"
        "ProviderName=@('Microsoft-Windows-Time-Service','Microsoft-Windows-Kernel-General',"
        "'Microsoft-Windows-Kernel-Power','Microsoft-Windows-Power-Troubleshooter')} -MaxEvents 300 -ErrorAction Stop | "
        "ForEach-Object {[pscustomobject]@{time=$_.TimeCreated.ToString('o');id=$_.Id;"
        "provider=$_.ProviderName;record_id=$_.RecordId;message=$_.Message}})} catch {$systemError=$_.Exception.Message}; "
        "try {$l=Get-WinEvent -ListLog 'Microsoft-Windows-Time-Service/Operational' -ErrorAction Stop; "
        "$logState=[pscustomobject]@{is_enabled=$l.IsEnabled;record_count=$l.RecordCount;log_mode=$l.LogMode.ToString()}; "
        "$operational=@(Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-Time-Service/Operational';"
        "StartTime=$from;EndTime=$to} -MaxEvents 300 -ErrorAction Stop | ForEach-Object {"
        "[pscustomobject]@{time=$_.TimeCreated.ToString('o');id=$_.Id;provider=$_.ProviderName;"
        "record_id=$_.RecordId;message=$_.Message}})} catch {$operationalError=$_.Exception.Message}; "
        "[pscustomobject]@{start_local=$from.ToString('o');end_local=$to.ToString('o');"
        "scope='Each log limited to latest 300 matching records; no records does not prove absence';"
        "system_events=$system;system_query_error=$systemError;time_service_log=$logState;"
        "time_service_events=$operational;time_service_query_error=$operationalError;"
        "system_settings_modified=$false} | ConvertTo-Json -Depth 8"
    )
    frozen = load(ROOT / "evidence/p3_clock_contract/20261009-180810-0491a4ec/identity_location_correction.json")["corrected_expected"]
    executable = "/var/tmp/matrix-autotuner-clock-repair-20261010-121004-read-adjtimex"
    commands = [
        ("windows_service_privileges", windows(service), 35),
        ("windows_time_status_before", ["w32tm.exe", "/query", "/status", "/verbose"], 20),
        ("windows_time_source_before", ["w32tm.exe", "/query", "/source"], 20),
        ("windows_time_configuration", ["w32tm.exe", "/query", "/configuration"], 20),
        ("windows_time_peers", ["w32tm.exe", "/query", "/peers"], 20),
        ("windows_events", windows(event_scope), 60),
        ("wsl_version", ["wsl.exe", "--version"], 20),
        ("wsl_kernel", wsl("uname", "-a"), 20),
        ("wsl_os_release", wsl("cat", "/etc/os-release"), 20),
        ("wsl_boot", wsl("uptime", "-s"), 20),
        ("wsl_timedatectl_status", wsl("timedatectl", "status"), 20),
        ("wsl_timedatectl_show", wsl("timedatectl", "show"), 20),
        ("wsl_clocksource", wsl("sh", "-c", "for p in /sys/devices/system/clocksource/clocksource0/current_clocksource /sys/devices/system/clocksource/clocksource0/available_clocksource; do printf '%s\\n' \"$p\"; cat \"$p\"; done"), 20),
        ("wsl_sync_services", wsl("systemctl", "show", "systemd-timesyncd.service", "chrony.service", "chronyd.service", "ntp.service", "ntpsec.service", "--property=Id,LoadState,ActiveState,SubState,UnitFileState,ExecMainStatus,ExecMainStartTimestamp"), 25),
        ("wsl_timesyncd_status", wsl("systemctl", "status", "systemd-timesyncd.service", "--no-pager", "--full"), 20),
        ("wsl_timesync_status", wsl("timedatectl", "timesync-status", "--all"), 20),
        ("wsl_timesync_show", wsl("timedatectl", "show-timesync", "--all"), 20),
        ("wsl_timesync_journal", wsl("journalctl", "--utc", "--since", "2026-10-09 08:00:00 UTC", "-u", "systemd-timesyncd.service", "-u", "chrony.service", "-u", "chronyd.service", "-u", "ntp.service", "-u", "ntpsec.service", "-n", "400", "--no-pager", "-o", "short-iso-precise"), 30),
        ("wsl_clock_kernel_journal", wsl("journalctl", "-k", "--utc", "--since", "2026-10-09 08:00:00 UTC", "--grep", "clocksource|tsc|Timekeeping|timekeeping|suspend|resume", "-n", "120", "--no-pager", "-o", "short-iso-precise"), 30),
        ("wsl_timex_headers", wsl("sh", "-c", "sed -n '1,170p' /usr/include/x86_64-linux-gnu/bits/timex.h; sed -n '1,190p' /usr/include/linux/timex.h"), 20),
        ("compiler_version", wsl("gcc", "--version"), 20),
        ("compile_readonly_adjtimex", wsl("gcc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", wsl_path(OUT / "read_adjtimex.c"), "-o", executable), 30),
        ("readonly_adjtimex", wsl(executable), 20),
        ("readonly_adjtimex_binary_sha", wsl("sha256sum", executable), 20),
        ("formal_frozen_sha", ["wsl.exe", "-d", "Ubuntu-24.04", "--", "sha256sum", *frozen], 45),
        ("resource_gate", [POWERSHELL, "-NoProfile", "-File", str(ROOT / "scripts/check_p2_resources.ps1"), "-Mode", "Formal"], 90),
    ]
    atomic_write_json(OUT / "diagnostic_commands.json", {"declared_at": utc_now(), "batch": BATCH,
        "command_scope": "Read-only diagnosis; only compile output in unique /var/tmp path is created",
        "new_clock_probes": 0, "resync_attempts": 0, "formal_matrix_calls": 0,
        "auxiliary_content_commit": AUX, "auxiliary_identity": auxiliary_identity(AUX),
        "collector_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "adjtimex_source_sha256": hashlib.sha256((OUT / "read_adjtimex.c").read_bytes()).hexdigest(),
        "commands": [{"name": name, "command": cmd, "timeout_seconds": timeout} for name, cmd, timeout in commands]})
    records = []
    for name, cmd, timeout in commands:
        operation = capture(cmd, OPS, name, BATCH, timeout=timeout)
        records.append(operation)
        print(json.dumps({"name": name, "returncode": operation["returncode"], "qpc_seconds": operation["qpc_seconds"], "timed_out": operation["timed_out"]}), flush=True)
    actual = {}
    for line in (OPS / "formal_frozen_sha.stdout.txt").read_text().splitlines():
        digest, path = line.split(maxsplit=1)
        actual[path.strip()] = digest
    resource = load(OPS / "resource_gate.stdout.txt")
    atomic_write_json(OUT / "diagnostic_collection.json", {
        "completed_at": utc_now(), "operations": records,
        "frozen_files_expected": frozen, "frozen_files_actual": actual,
        "frozen_files_pass": frozen == actual and records[-2]["returncode"] == 0,
        "resource_gate": resource, "formal_resource_gate_pass": records[-1]["returncode"] == 0 and valid_formal_gate(resource, load(ROOT / "configs/measurement_protocol.json")),
        "new_clock_probes": 0, "resync_attempts": 0, "formal_matrix_calls": 0,
        "missing_metrics": "See operation exit codes and raw stderr; do not treat missing logs/services as healthy."})


if __name__ == "__main__":
    main()
