"""Save the exact argv, output, exit code and UTC interval of a command."""
import datetime as dt
import json
import os
from pathlib import Path
import shlex
import subprocess
import time


def capture(directory, argv, cwd=None, expected=0, env=None):
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    argv = [str(arg) for arg in argv]
    cwd = Path(cwd or Path.cwd()).resolve()
    metadata = {"argv": argv, "cwd": str(cwd),
                "started_utc": dt.datetime.now(dt.timezone.utc).isoformat()}
    (directory / "command.txt").write_text(shlex.join(argv) + "\n", encoding="utf-8")
    print(f"RUN {directory.name}: {shlex.join(argv)}", flush=True)
    started = time.monotonic()
    with (directory / "stdout.txt").open("w") as stdout, (directory / "stderr.txt").open("w") as stderr:
        result = subprocess.run(argv, cwd=cwd, stdout=stdout, stderr=stderr,
                                env=None if env is None else {**os.environ, **env})
    metadata.update(returncode=result.returncode, wall_seconds=time.monotonic() - started,
                    ended_utc=dt.datetime.now(dt.timezone.utc).isoformat())
    (directory / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"END {directory.name}: exit={result.returncode}, {metadata['wall_seconds']:.3f}s", flush=True)
    if expected is not None and result.returncode != expected:
        raise RuntimeError(f"{directory}: exit {result.returncode}; inspect stderr.txt")
    return result.returncode
