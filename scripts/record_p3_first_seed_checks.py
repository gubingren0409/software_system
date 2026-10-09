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
from autotuner.core import sha256_file, utc_now
from autotuner.session import source_identity, valid_formal_gate
from scripts.p3_clock_contract import atomic_write_json


def review_result(status, mode, command_checks_pass):
    fields = {key: status[key] for key in ("evidence_integrity_pass", "execution_complete",
                                          "timing_checks_pass", "comparison_ready")}
    if any(type(value) is not bool for value in fields.values()):
        raise ValueError("Audit acceptance fields must be booleans")
    checks_pass = command_checks_pass and fields["evidence_integrity_pass"]
    requested = fields["comparison_ready"] if mode == "complete" else not fields["execution_complete"]
    return {**fields, "review_checks_pass": checks_pass, "requested_acceptance_satisfied": requested and checks_pass,
            "returncode": 0 if requested and checks_pass else (2 if checks_pass else 1)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--batch", type=Path, required=True)
    parser.add_argument("--clock-recovery", type=Path, required=True)
    parser.add_argument("--archive-root")
    parser.add_argument("--archive-commit")
    parser.add_argument("--windows-archive-root", type=Path)
    parser.add_argument("--acceptance-mode", choices=("incomplete", "complete"), default="incomplete")
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

    def run(command, expected=(0,), timeout=180, cwd=ROOT):
        started = utc_now()
        timer = time.perf_counter()
        result = subprocess.run(command, cwd=cwd, env=env, capture_output=True,
                                encoding="utf-8", errors="backslashreplace", timeout=timeout)
        commands.append({"command": command, "cwd": str(cwd), "started_at": started,
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
    run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_p3_clock_contract.py", "-v"])
    run([sys.executable, "scripts/audit_p3_first_seed.py", "--batch", str(args.batch),
         "--clock-recovery", str(args.clock_recovery), "--output", str(args.output / "first_seed_status.json"),
         "--acceptance-mode", args.acceptance_mode, "--require-two"],
        (0, 1, 2))
    status = json.loads((args.output / "first_seed_status.json").read_text())
    required = ("evidence_integrity_pass", "execution_complete", "timing_checks_pass", "comparison_ready")
    if any(type(status.get(field)) is not bool for field in required):
        raise ValueError("Audit acceptance contract differs")
    files = [*sorted((ROOT / "autotuner").glob("*.py")), *sorted((ROOT / "configs").glob("*.json")),
             *sorted((ROOT / "code/working").glob("*.[ch]")), ROOT / "code/original/matrix_multiplication.c",
             ROOT / "scripts/resume_p3_first_seed.ps1", Path(__file__),
             ROOT / "scripts/audit_p3_first_seed.py", ROOT / "tests/test_first_seed_audit.py",
             ROOT / "scripts/p3_clock_contract.py", ROOT / "scripts/start_p3_first_seed.py",
             ROOT / "tests/test_p3_clock_contract.py"]
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
        if args.windows_archive_root:
            windows_root = args.windows_archive_root.resolve()
            if (windows_root / ".git").exists() or list(windows_root.rglob("__pycache__")):
                raise ValueError("Windows archive is not initially clean")
            actual_windows = source_identity(windows_root, git_blobs)
            atomic_write_json(args.output / "windows_archive_sources.json", actual_windows)
            run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_first_seed_audit.py", "-v"], cwd=windows_root)
            run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_p3_clock_contract.py", "-v"], cwd=windows_root)
    review_pass = all(row["returncode"] in row["expected_returncodes"] for row in commands)
    reviewed = review_result(status, args.acceptance_mode, review_pass)
    atomic_write_json(args.output / "summary.json", {**reviewed, "acceptance_mode": args.acceptance_mode,
        "formal_first_seed_complete": status["execution_complete"], "formal_resource_gate_pass": gate_pass,
        "formal_blocker": None if status["comparison_ready"] else "See recomputed first_seed_status.json; not comparison-ready",
        "archive_root": args.archive_root, "archive_commit": args.archive_commit,
        "windows_archive_root": str(args.windows_archive_root) if args.windows_archive_root else None,
        "command_count": len(commands), "recorder_sha256": sha256_file(Path(__file__)),
        "process_only_module_path_override": env["PSModulePath"],
        "performance_protocol_modified": False, "formal_4096_runs_started_by_recorder": 0,
        "small_target_tests": "Full unit suite may execute isolated small C targets; see command logs"})
    print(json.dumps({**reviewed, "formal_resource_gate_pass": gate_pass, "commands": len(commands)}))
    return reviewed["returncode"]


if __name__ == "__main__":
    raise SystemExit(main())
