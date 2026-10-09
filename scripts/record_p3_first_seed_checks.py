"""Windows-side read-only review; never resumes the formal campaign."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autotuner.core import atomic_write_json, sha256_file, utc_now
from autotuner.session import source_identity, valid_formal_gate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--batch", type=Path, required=True)
    parser.add_argument("--clock-recovery", type=Path, required=True)
    parser.add_argument("--archive-root")
    parser.add_argument("--archive-commit")
    args = parser.parse_args()
    if os.name != "nt" or args.output.exists():
        raise ValueError("Run on Windows with a new output directory")
    args.output.mkdir(parents=True)
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # Start-Process/Python do not apply pwsh's native Windows PowerShell path fixup.
    env["PSModulePath"] = "C:/Windows/System32/WindowsPowerShell/v1.0/Modules"
    commands = []

    def run(command, expected=(0,), timeout=180):
        started = utc_now()
        timer = time.perf_counter()
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True,
                                encoding="utf-8", errors="backslashreplace", timeout=timeout)
        commands.append({"command": command, "cwd": str(ROOT), "started_at": started,
            "ended_at": utc_now(), "host_perf_counter_seconds": time.perf_counter() - timer,
            "stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode,
            "expected_returncodes": list(expected)})
        atomic_write_json(args.output / "commands.json", commands)
        if result.returncode not in expected:
            raise RuntimeError("Review command failed: " + repr(command))
        return result

    run([sys.executable, "--version"])
    resource = run(["C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe", "-NoProfile",
                    "-File", str(ROOT / "scripts/check_p2_resources.ps1"), "-Mode", "Formal"], (0, 2))
    parsed = json.loads(resource.stdout)
    protocol = json.loads((ROOT / "configs/measurement_protocol.json").read_text())
    gate_pass = resource.returncode == 0 and valid_formal_gate(parsed, protocol)
    atomic_write_json(args.output / "resource_gate.json", {"parsed": parsed,
        "returncode": resource.returncode, "formal_fields_pass": gate_pass})
    run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_first_seed_audit.py", "-v"])
    run([sys.executable, "scripts/audit_p3_first_seed.py", "--batch", str(args.batch),
         "--clock-recovery", str(args.clock_recovery), "--output", str(args.output / "first_seed_status.json"),
         "--require-two"], (2,))  # Deliberately must not declare this partial campaign complete.
    files = [*sorted((ROOT / "autotuner").glob("*.py")), *sorted((ROOT / "configs").glob("*.json")),
             *sorted((ROOT / "code/working").glob("*.[ch]")), ROOT / "code/original/matrix_multiplication.c",
             ROOT / "scripts/resume_p3_first_seed.ps1", Path(__file__),
             ROOT / "scripts/audit_p3_first_seed.py", ROOT / "tests/test_first_seed_audit.py"]
    git_blobs = {}
    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        git_hash = subprocess.check_output(["git", "hash-object", "--path=" + relative, str(path)],
                                           cwd=ROOT, env=env, text=True).strip()
        git_blobs[relative] = git_hash
    if args.archive_root:
        if not args.archive_commit:
            raise ValueError("Archive commit identity is required")
        tree = subprocess.check_output(["git", "ls-tree", "-r", "--format=%(objectname)%x09%(path)",
                                       args.archive_commit, "--", *git_blobs], cwd=ROOT, env=env, text=True)
        committed_blobs = dict((path, blob) for blob, path in
                               (line.split("\t", 1) for line in tree.splitlines()))
        if committed_blobs != git_blobs:
            raise ValueError("Working sources differ from the requested content commit")
    sources = source_identity(ROOT, git_blobs)
    atomic_write_json(args.output / "sources.json", sources)
    if args.archive_root:
        prefix = ["wsl.exe", "-d", "Ubuntu-24.04", "--cd", args.archive_root, "--", "env",
                  "-u", "PYTHONPATH", "PYTHONDONTWRITEBYTECODE=1"]
        clean = run([*prefix, "python3", "-c", "import json,pathlib; p=pathlib.Path('.'); "
            "print(json.dumps({'has_git':(p/'.git').exists(),'pycache':list(map(str,p.rglob('__pycache__')))}))"])
        if json.loads(clean.stdout) != {"has_git": False, "pycache": []}:
            raise ValueError("Archive is not initially clean")
        run([*prefix, "python3", "--version"])
        run([*prefix, "/usr/bin/gcc", "--version"])
        run([*prefix, "python3", "-m", "autotuner", "--help"])
        listed = json.loads(run([*prefix, "python3", "-m", "autotuner", "list-configs"]).stdout)
        if len(listed) != 20 or len({tuple(sorted(row.items())) for row in listed}) != 20:
            raise ValueError("Configuration space differs")
        run([*prefix, "python3", "-m", "unittest", "discover", "-s", "tests", "-v"])
        run([*prefix, "python3", "scripts/verify_p1.py"])
        archived = run([*prefix, "python3", "-c",
            "import json,sys; from pathlib import Path; from autotuner.session import source_identity; "
            "print(json.dumps(source_identity(Path('.'),json.loads(sys.argv[1]))))", json.dumps(git_blobs)])
        actual = json.loads(archived.stdout)
        atomic_write_json(args.output / "archive_sources.json", actual)
        if set(actual) != set(sources) or any(
                actual[path]["git_content_sha256"] != record["git_content_sha256"]
                for path, record in sources.items()):
            raise ValueError("Archive/working Git content differs")
        atomic_write_json(args.output / "archive_identity_check.json", {
            "content_commit": args.archive_commit, "git_content_match": True,
            "actual_byte_differences": [path for path, record in sources.items()
                if actual[path]["executed_sha256"] != record["executed_sha256"]],
            "rule": "Each actual file must match its committed Git blob, either byte-for-byte "
                "or solely after CRLF-to-LF conversion; code/original must be byte-for-byte."})
    atomic_write_json(args.output / "summary.json", {"review_checks_pass": True,
        "formal_first_seed_complete": False, "formal_resource_gate_pass": gate_pass,
        "formal_blocker": "Failed unchanged MONOTONIC/RAW clock criteria; no formal resume",
        "archive_root": args.archive_root, "archive_commit": args.archive_commit,
        "command_count": len(commands), "recorder_sha256": sha256_file(Path(__file__)),
        "process_only_module_path_override": env["PSModulePath"],
        "performance_protocol_modified": False, "new_formal_target_executions": 0})
    print(json.dumps({"review_checks_pass": True, "formal_resource_gate_pass": gate_pass,
                      "formal_first_seed_complete": False, "commands": len(commands)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
