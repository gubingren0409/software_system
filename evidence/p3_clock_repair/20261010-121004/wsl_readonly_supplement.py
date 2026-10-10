"""Repeat only two failed read-only metadata commands without shell quoting.

The first collection's sh -c variable and journal --grep pipe were interpreted
by the WSL launcher. Preserve those failures; direct subprocess argument lists
inside WSL remove the extra shell. No clock probes or parameter setters.
"""
import json
import subprocess
import time

commands = [
    ["cat", "/sys/devices/system/clocksource/clocksource0/current_clocksource"],
    ["cat", "/sys/devices/system/clocksource/clocksource0/available_clocksource"],
    ["journalctl", "-k", "--utc", "--since", "2026-10-09 08:00:00 UTC",
     "--grep", "clocksource|tsc|Timekeeping|timekeeping|suspend|resume",
     "-n", "120", "--no-pager", "-o", "short-iso-precise"],
]
rows = []
for command in commands:
    started = time.perf_counter()
    completed = subprocess.run(command, text=True, capture_output=True, timeout=20)
    rows.append({"command": command, "stdout": completed.stdout,
                 "stderr": completed.stderr, "returncode": completed.returncode,
                 "process_seconds": time.perf_counter() - started})
print(json.dumps({"schema": "one-off-readonly-wsl-supplement-v1",
                  "system_settings_modified": False, "commands": rows}))
