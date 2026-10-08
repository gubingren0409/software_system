from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from autotuner.core import ConfigSpace, Evaluator, TargetAdapter, atomic_write_json, sha256_json
from autotuner.measurement import ConfigurationEvaluator
from autotuner.search import GridSearch, RandomSearch, RestartGreedySearch
from autotuner.session import source_identity


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--content-sha", required=True)
    parser.add_argument("--git-identity", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    identity = json.loads(args.git_identity.read_text())
    if identity["content_sha"] != args.content_sha or (ROOT / ".git").exists() or list(ROOT.rglob("__pycache__")):
        raise ValueError("expected committed clean archive without bytecode caches")
    files = source_identity(ROOT, identity["files"])
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    commands = []
    with tempfile.TemporaryDirectory(prefix="matrix-p2-clean-tests-") as temporary:
        runtime = Path(temporary)
        target_data = json.loads((ROOT / "configs/target.json").read_text())
        target_data.update(candidate_source=str(ROOT / "code/working/matrix_multiplication.c"),
                           reference_source=str(ROOT / "code/working/reference_generator.c"),
                           shared_sources=[str(ROOT / "code/working/matrix_input.h")],
                           cache_root=str(runtime / "cache"))
        target_path = runtime / "target.json"
        atomic_write_json(target_path, target_data)
        checks = [
            [sys.executable, "-m", "autotuner", "--help"],
            [sys.executable, "-m", "autotuner", "list-configs"],
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
            [sys.executable, "scripts/verify_p1.py"],
            [sys.executable, "-m", "autotuner", "--target", str(target_path),
             "--evidence-root", str(args.output / "cli_n17"), "evaluate", "--size", "17",
             "--optimization", "O2", "--block-size", "8", "--seed", "20261008",
             "--input", "random", "--timeout", "30", "--label", "clean_cli_n17"],
            [sys.executable, "scripts/run_p1_correctness.py", "--target", str(target_path),
             "--output-directory", str(args.output / "correctness"),
             "--runtime-evidence-root", str(args.output / "runtime")],
        ]
        for command in checks:
            completed = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True, check=False)
            record = {"command": command, "returncode": completed.returncode,
                      "stdout": completed.stdout, "stderr": completed.stderr, "cwd": str(ROOT)}
            commands.append(record)
            atomic_write_json(args.output / "commands.json", commands)
            if completed.returncode != 0:
                raise RuntimeError(f"clean regression failed: {command}")

        protocol = json.loads((ROOT / "configs/measurement_protocol.json").read_text())
        protocol["target_matrix_n"] = 130
        protocol["resource_gate"]["formal_wsl_minimum_available_bytes"] = 0
        space = ConfigSpace.load(ROOT / "configs/config_space.json")
        trajectories = []
        for name, strategy in (("grid", GridSearch(space)), ("random", RandomSearch(space, 8, 20261008)),
                               ("greedy", RestartGreedySearch(space, 8, 20261008))):
            output = args.output / f"n130_{name}"
            target = TargetAdapter.load(target_path, evidence_root=output)
            evaluator = ConfigurationEvaluator(Evaluator(target), protocol, sha256_json(protocol), output)
            observations = []
            while (config := strategy.ask()) is not None:
                result = evaluator.evaluate(config)
                if result["classification"] != "success":
                    raise RuntimeError(f"real n=130 pipeline failed: {config}")
                strategy.tell(config, result)
                observations.append({"config": result["config"], "score_seconds": result["score_seconds"]})
            trajectories.append({"algorithm": name, "observations": observations,
                                 "unique_count": len(strategy.observations)})
        atomic_write_json(args.output / "diagnostic_trajectories.json", trajectories)
    summary = {"status": "PASS", "content_commit": args.content_sha, "files": files,
               "controlled_tests": "PASS", "real_n130_counts": [20, 8, 8],
               "diagnostic_only": True, "pythonpath_removed": True, "initial_pycache_count": 0}
    atomic_write_json(args.output / "summary.json", summary)
    print(json.dumps({key: summary[key] for key in ("status", "content_commit", "real_n130_counts")}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
