"""Windows-side, post-experiment plots and read-only provenance/cost checks."""
from __future__ import annotations

import argparse
import ast
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autotuner.core import atomic_write_json, sha256_file, utc_now


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.session = args.session.resolve()
    args.output = args.output.resolve()
    checkpoint = json.loads((args.session / "checkpoint.json").read_text())
    session = json.loads((args.session / "session.json").read_text())
    audit = json.loads((args.session / "evidence_audit.json").read_text())
    groups = checkpoint["completed"]
    if not audit["grid_complete"] or len(groups) != 20:
        raise ValueError("postprocessing requires complete audited Grid and retest")
    args.output.mkdir(parents=True, exist_ok=True)
    commands = []

    def run(command: list[str]) -> str:
        captured = utc_now()
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                timeout=60, check=False)
        commands.append({"captured_at": captured, "command": command, "cwd": str(ROOT),
                         "stdout": result.stdout, "stderr": result.stderr,
                         "returncode": result.returncode})
        atomic_write_json(args.output / "commands.json", commands)
        if result.returncode != 0:
            raise RuntimeError(f"postprocessing command failed: {command}")
        return result.stdout

    run([sys.executable, "--version"])
    run([sys.executable, "-c", "import matplotlib,numpy; "
         "print('matplotlib',matplotlib.__version__); print('numpy',numpy.__version__)"])
    run([sys.executable, "scripts/plot_p2_results.py", "--session-directory", str(args.session),
         "--output-directory", "assets"])
    expected = {checkpoint["fingerprint"]["compiler_path"]:
                checkpoint["fingerprint"]["compiler_sha256"]}
    for path in sorted((args.session / "manifests").glob("*.json")):
        manifest = json.loads(path.read_text())
        if "command" in manifest:
            command = manifest["command"]
            expected[command[command.index("-o") + 1]] = manifest["binary_sha256"]
            expected.update(manifest["source_hashes"])
    sample = groups[0]["samples"][0]
    command = sample["command"]
    expected[command[command.index("--reference") + 1]] = sample["reference_sha256"]
    actual_text = run(["wsl.exe", "-d", "Ubuntu-24.04", "--", "sha256sum", *sorted(expected)])
    actual = {line.split(maxsplit=1)[1].lstrip(" *"): line.split(maxsplit=1)[0]
              for line in actual_text.splitlines()}
    if actual != expected:
        raise ValueError("post-run source/compiler/binary/reference hashes changed")
    parsed_files = []
    for directory in ("autotuner", "scripts", "tests"):
        for path in sorted((ROOT / directory).glob("*.py")):
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            parsed_files.append(str(path.relative_to(ROOT)).replace("\\", "/"))
    best = min(groups, key=lambda group: group["score_seconds"])
    retest = checkpoint["independent_retest"]
    grid_eval = sum(group["evaluation_wall_seconds"] for group in groups)
    grid_process = sum(group["process_wall_seconds"] for group in groups)
    prefixes = []
    for budget in (4, 8, 12):
        winner = min(groups[:budget], key=lambda group: group["score_seconds"])
        prefixes.append({"budget": budget, "config": winner["config"],
                         "median_seconds": winner["score_seconds"],
                         "regret_percent": 100 * (winner["score_seconds"] / best["score_seconds"] - 1),
                         "order_dependent": True})
    source_files = [Path(__file__), ROOT / "scripts/plot_p2_results.py",
                    ROOT / "scripts/audit_p2_evidence.py", ROOT / "scripts/inspect_p2.py"]
    artifacts = [ROOT / "assets/p2_heatmap.png", ROOT / "assets/p2_variation.png",
                 args.session / "grid_summary.csv", args.session / "summary.json",
                 args.session / "independent_retest.json", args.session / "evidence_audit.json"]
    result = {
        "schema": "p2-postprocessing-v1", "status": "PASS", "captured_at": utc_now(),
        "command_argv": [sys.executable, *sys.argv],
        "formal_content_commit": checkpoint["fingerprint"]["content_commit"],
        "helper_scope": "post-experiment only; does not alter formal code/protocol or samples",
        "source_hashes": {str(path.relative_to(ROOT)).replace("\\", "/"): sha256_file(path)
                          for path in source_files},
        "artifact_hashes": {str(path.relative_to(ROOT)).replace("\\", "/"): sha256_file(path)
                            for path in artifacts},
        "postrun_executed_file_hashes": actual, "python_ast_checked": parsed_files,
        "utc_span_seconds_including_shutdown_pause":
            (datetime.fromisoformat(checkpoint["updated_at"]) -
             datetime.fromisoformat(session["created_at"])).total_seconds(),
        "utc_span_caveat": "UTC was adjusted; distinct from monotonic costs, not calibrated physical time",
        "grid_complete_configuration_evaluation_seconds": grid_eval,
        "grid_complete_configuration_process_seconds": grid_process,
        "canonical_grid_prefixes": prefixes,
        "retest_change_percent": 100 * (retest["score_seconds"] / best["score_seconds"] - 1),
        "future_cost_estimate_seconds_per_algorithm_60_unique": grid_eval / 20 * 60,
        "future_cost_caveat": "Conditional empirical average, not a guarantee; excludes new setup, "
                              "resource waiting, failed/interrupted work and candidate retests. "
                              "No formal random/greedy run is performed here.",
    }
    atomic_write_json(args.output / "summary.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
