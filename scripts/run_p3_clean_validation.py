"""Committed-archive acceptance; all actual target executions here are diagnostic."""
from __future__ import annotations

import argparse
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autotuner.core import atomic_write_json, atomic_write_text, sha256_file, utc_now
from autotuner.session import source_identity


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--content-sha", required=True)
    parser.add_argument("--git-identity", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    identity = json.loads(args.git_identity.read_text())
    if identity["content_sha"] != args.content_sha or (ROOT / ".git").exists() or list(ROOT.rglob("__pycache__")):
        raise ValueError("expected clean committed archive without bytecode caches")
    files = source_identity(ROOT, identity["files"])
    parsed_files = []
    for directory in ("autotuner", "scripts", "tests"):
        for path in sorted((ROOT / directory).glob("*.py")):
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            parsed_files.append(str(path.relative_to(ROOT)))
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    commands = []

    def record(command, result, captured, expected=0):
        commands.append({"captured_at": captured, "command": command, "cwd": str(ROOT),
                         "stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode,
                         "expected_returncode": expected})
        atomic_write_json(args.output / "commands.json", commands)
        if result.returncode != expected:
            raise RuntimeError(f"clean P3 check failed: {command}")

    def run(command, expected=0):
        captured = utc_now()
        result = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True,
                                timeout=600, check=False)
        record(command, result, captured, expected)
        return result

    run([sys.executable, "--version"])
    run(["/usr/bin/gcc", "--version"])
    run([sys.executable, "-m", "autotuner", "--help"])
    listed = run([sys.executable, "-m", "autotuner", "list-configs"])
    configurations = json.loads(listed.stdout)
    if len(configurations) != 20 or len({tuple(sorted(item.items())) for item in configurations}) != 20:
        raise ValueError("CLI configuration space is not 20 unique configurations")
    run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
    run([sys.executable, "scripts/verify_p1.py"])
    with tempfile.TemporaryDirectory(prefix="matrix-p3-clean-tests-") as temporary:
        runtime = Path(temporary)
        target = json.loads((ROOT / "configs/target.json").read_text())
        target.update(candidate_source=str(ROOT / "code/working/matrix_multiplication.c"),
                      reference_source=str(ROOT / "code/working/reference_generator.c"),
                      shared_sources=[str(ROOT / "code/working/matrix_input.h")],
                      cache_root=str(runtime / "n17-cache"))
        target_path = runtime / "target.json"
        atomic_write_json(target_path, target)
        atomic_write_json(args.output / "diagnostic_target.json", target)
        evaluated = run([sys.executable, "-m", "autotuner", "--target", str(target_path),
                         "--evidence-root", str(args.output / "n17"), "evaluate", "--size", "17",
                         "--optimization", "O2", "--block-size", "8", "--seed", "20261008",
                         "--input", "random", "--timeout", "30", "--label", "clean_p3_n17"])
        n17 = json.loads(evaluated.stdout)
        if n17["source"] != "fresh_measurement" or n17["classification"] != "success":
            raise ValueError("n17 evaluation was not a correct fresh run")
        destination = args.output / "diagnostic_campaign"
        command = [sys.executable, "-m", "autotuner", "campaign", "--content-sha", args.content_sha,
                   "--git-identity", str(args.git_identity), "--campaign-directory", str(destination),
                   "--diagnostic-size", "130", "--diagnostic-cache", str(runtime / "n130-cache")]
        run([*command, "--trajectory-limit", "2"])

        def run_ids():
            return {json.loads(line)["run_id"] for path in (destination / "trajectories").glob("*/samples.jsonl")
                    for line in path.read_text().splitlines() if line}

        first_ids = run_ids()
        def expected_ids():
            states = [json.loads(path.read_text()) for path in (destination / "trajectories").glob("*/checkpoint.json")]
            return 6 * sum(len(state["observations"]) + len(state["independent_retests"]) for state in states)
        if len(first_ids) != expected_ids() or not 156 <= len(first_ids) <= 180:
            raise ValueError("two trajectories must have 144 search executions and independent prefix retests")
        run([*command, "--trajectory-limit", "2", "--resume"])
        if run_ids() != first_ids:
            raise ValueError("completed batch was remeasured on resume")
        run([*command, "--trajectory-limit", "10", "--resume"])
        final_execution_count = len(run_ids())
        if final_execution_count != expected_ids() or not 780 <= final_execution_count <= 900 or \
                not first_ids.issubset(run_ids()):
            raise ValueError("full diagnostic campaign does not preserve all unique fresh executions")
        run([sys.executable, "scripts/audit_p3_evidence.py", "--campaign", str(destination),
             "--output", str(args.output / "diagnostic_audit"), "--require-complete"])

        # Pause after a real saved sample; do not terminate an in-flight target.
        paused = args.output / "pause_resume_campaign"
        pause_command = [*command]
        pause_command[pause_command.index("--campaign-directory") + 1] = str(paused)
        pause_command.extend(["--trajectory-limit", "1"])
        captured = utc_now()
        process = subprocess.Popen(pause_command, cwd=ROOT, env=env, text=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        deadline = time.monotonic() + 30
        pause_sent = False
        while process.poll() is None and time.monotonic() < deadline:
            if list((paused / "trajectories").glob("*/runs/*/result.json")):
                atomic_write_text(paused / "PAUSE_REQUEST", "clean acceptance pause after a saved sample\n")
                pause_sent = True
                break
            time.sleep(0.01)
        stdout, stderr = process.communicate(timeout=600)
        record(pause_command, subprocess.CompletedProcess(pause_command, process.returncode, stdout, stderr),
               captured, expected=2)
        if not pause_sent:
            raise ValueError("actual partial-group pause did not occur")
        state_path = next((paused / "trajectories").glob("*/checkpoint.json"))
        prior = json.loads(state_path.read_text())
        prior_attempt = prior["active"]["attempt_id"]
        if prior["observations"] or prior["active"]["sample_count"] < 1:
            raise ValueError("pause did not retain an unscored partial first configuration")
        run([*pause_command, "--resume"])
        restored = json.loads(state_path.read_text())
        if restored["status"] != "complete" or len(restored["observations"]) != 12 or \
                restored["observations"][0]["attempt_id"] == prior_attempt or \
                not any(item["attempt_id"] == prior_attempt for item in restored["abandoned_attempts"]):
            raise ValueError("partial configuration was not abandoned and completely remeasured")
        run([sys.executable, "scripts/audit_p3_evidence.py", "--campaign", str(paused),
             "--output", str(args.output / "pause_resume_audit")])
    summary = {"status": "PASS", "content_commit": args.content_sha, "captured_at": utc_now(),
               "validator_sha256": sha256_file(Path(__file__)), "files": files,
               "python_ast_checked": parsed_files, "diagnostic_target_sha256": sha256_file(args.output / "diagnostic_target.json"),
               "diagnostic_only": True, "initial_pycache_count": 0, "pythonpath_removed": True,
               "config_count": 20, "n17_fresh_correct": True, "n130_trajectory_count": 10,
               "n130_unique_configuration_count": 120, "n130_fresh_execution_count": final_execution_count,
               "completed_batch_resume_remeasured": False, "partial_group_abandoned_and_remeasured": True}
    atomic_write_json(args.output / "summary.json", summary)
    print(json.dumps({key: summary[key] for key in
                     ("status", "content_commit", "n130_trajectory_count", "n130_fresh_execution_count")}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
