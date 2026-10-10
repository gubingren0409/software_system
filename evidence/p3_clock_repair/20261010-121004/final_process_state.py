"""WSL read-only process and nonblocking original runner-lock check."""
import fcntl
import json
from pathlib import Path

matches, inaccessible = [], 0
for path in Path("/proc").glob("[0-9]*/cmdline"):
    try:
        argv = [part.decode("utf-8", "replace") for part in path.read_bytes().split(b"\0") if part]
    except (OSError, PermissionError):
        inaccessible += 1
        continue
    if not argv:
        continue
    candidate = Path(argv[0]).name == "candidate"
    campaign = "autotuner" in argv and "campaign" in argv and "-m" in argv
    controller = any(Path(arg).name == "start_p3_first_seed.py" for arg in argv[:3])
    if candidate or campaign or controller:
        matches.append({"pid": int(path.parent.name), "argv": argv})

lock = Path("/var/tmp/matrix-autotuner-p3-10245102457.runner.lock")
state = "unknown"
if lock.exists():
    try:
        with lock.open("rb") as stream:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                state = "available"
                fcntl.flock(stream, fcntl.LOCK_UN)
            except BlockingIOError:
                state = "held"
    except OSError as error:
        state = "unknown: " + str(error)
else:
    state = "absent (not created)"
print(json.dumps({"formal_processes": matches, "inaccessible_cmdline_count": inaccessible,
                  "runner_lock": str(lock), "runner_lock_state": state,
                  "pause_marker_action": "none", "system_settings_modified": False}))
