from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import Config, ConfigSpace, EvaluationContext, Evaluator, TargetAdapter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Matrix multiplication P1 runner")
    parser.add_argument("--target", type=Path, default=Path("configs/target.json"))
    parser.add_argument("--space", type=Path, default=Path("configs/config_space.json"))
    parser.add_argument("--evidence-root", type=Path, default=Path("evidence/p1"))
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list-configs")
    list_parser.set_defaults(action=command_list_configs)

    build = subparsers.add_parser("build")
    build.add_argument("--size", type=int, required=True)
    build.add_argument("--optimization", choices=("O0", "O1", "O2", "O3"), required=True)
    build.set_defaults(action=command_build)

    reference = subparsers.add_parser("reference")
    reference.add_argument("--size", type=int, required=True)
    reference.add_argument("--seed", type=int, required=True)
    reference.add_argument("--input", choices=("random", "zero", "identity"), required=True)
    reference.add_argument("--timeout", type=float, default=600.0)
    reference.set_defaults(action=command_reference)

    evaluate = subparsers.add_parser("evaluate")
    evaluate.add_argument("--size", type=int, required=True)
    evaluate.add_argument("--optimization", choices=("O0", "O1", "O2", "O3"), required=True)
    evaluate.add_argument("--block-size", type=int, required=True)
    evaluate.add_argument("--seed", type=int, required=True)
    evaluate.add_argument("--input", choices=("random", "zero", "identity"), required=True)
    evaluate.add_argument("--timeout", type=float, default=600.0)
    evaluate.add_argument("--label", required=True)
    evaluate.add_argument("--min-wsl-available-bytes", type=int, default=0)
    evaluate.add_argument("--fault-injection", type=int, choices=range(0, 8), default=0)
    evaluate.set_defaults(action=command_evaluate)
    grid = subparsers.add_parser("grid", help="Run or resume the formal 20-configuration Grid session")
    grid.add_argument("--content-sha", required=True)
    grid.add_argument("--git-identity", type=Path, required=True)
    grid.add_argument("--session-directory", type=Path, required=True)
    grid.add_argument("--resume", action="store_true")
    grid.set_defaults(action=command_grid)
    return parser


def command_grid(args: argparse.Namespace) -> int:
    from .session import run_grid
    return run_grid(Path(__file__).resolve().parents[1], args.session_directory.resolve(),
                    args.content_sha, args.git_identity, resume=args.resume)


def load_runtime(args: argparse.Namespace) -> tuple[TargetAdapter, ConfigSpace]:
    target = TargetAdapter.load(args.target, evidence_root=args.evidence_root)
    space = ConfigSpace.load(args.space)
    return target, space


def command_list_configs(args: argparse.Namespace) -> int:
    _, space = load_runtime(args)
    print(json.dumps([config.__dict__ for config in space.all()], indent=2))
    return 0


def command_build(args: argparse.Namespace) -> int:
    target, _ = load_runtime(args)
    artifact = target.build_candidate(args.size, args.optimization)
    print(
        json.dumps(
            {
                "build_key": artifact.build_key,
                "binary_sha256": artifact.binary_sha256,
                "matrix_n": artifact.matrix_n,
                "optimization": artifact.optimization,
            },
            sort_keys=True,
        )
    )
    return 0


def command_reference(args: argparse.Namespace) -> int:
    target, _ = load_runtime(args)
    artifact = target.get_reference(args.size, args.seed, args.input, args.timeout)
    print(json.dumps(artifact.metadata, sort_keys=True))
    return 0


def command_evaluate(args: argparse.Namespace) -> int:
    target, _ = load_runtime(args)
    evaluator = Evaluator(target)
    record = evaluator.evaluate(
        Config(args.optimization, args.block_size),
        EvaluationContext(
            matrix_n=args.size,
            seed=args.seed,
            input_pattern=args.input,
            timeout_seconds=args.timeout,
            evidence_label=args.label,
            min_wsl_available_bytes=args.min_wsl_available_bytes,
            fault_injection=args.fault_injection,
        ),
    )
    print(json.dumps(record, sort_keys=True))
    return 0 if record["classification"] == "success" else 1


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.action(args)


if __name__ == "__main__":
    raise SystemExit(main())
