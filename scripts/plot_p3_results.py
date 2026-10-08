"""Post-hoc plots only; no target execution or search observations are changed."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--grid", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit = json.loads(args.audit.read_text())
    checkpoint = json.loads((args.grid / "checkpoint.json").read_text())
    if audit["status"] != "PASS" or audit["diagnostic_only"] or not audit["p2_comparison_reference"]:
        raise ValueError("requires audited formal trajectories and explicit P2 comparison reference")
    groups = checkpoint["completed"]
    if len(groups) != 20 or any(group["classification"] != "success" for group in groups):
        raise ValueError("requires complete P2 Grid")
    budgets = [4, 8, 12]
    grid_lowest = min(group["score_seconds"] for group in groups)
    figure, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    styles = {"random": ("#2579a4", "o"), "greedy": ("#d48228", "s")}
    seed_counts = {}
    for algorithm, (color, marker) in styles.items():
        rows = [row for row in audit["prefix_rows"] if row["algorithm"] == algorithm]
        seeds = sorted({row["search_seed"] for row in rows})
        seed_counts[algorithm] = len(seeds)
        for index, seed in enumerate(seeds):
            selected = sorted((row for row in rows if row["search_seed"] == seed), key=lambda row: row["budget"])
            valid = [row for row in selected if row["p2_selected_configuration_median_seconds"] is not None]
            label = f"{algorithm} (n={len(seeds)} seeds)" if index == 0 else None
            axes[0].plot([row["budget"] for row in valid],
                         [row["p2_selected_configuration_median_seconds"] / grid_lowest for row in valid],
                         color=color, marker=marker, alpha=0.75, label=label)
            axes[1].plot([row["budget"] for row in selected],
                         [row["configuration_evaluation_seconds"] / 3600 for row in selected],
                         color=color, marker=marker, alpha=0.75, label=label)
    if not any(seed_counts.values()):
        raise ValueError("no formal budget prefixes to plot")
    axes[0].plot(budgets, [min(group["score_seconds"] for group in groups[:budget]) / grid_lowest
                           for budget in budgets], "D--", color="#666666", label="Grid canonical prefix")
    axes[1].plot(budgets, [sum(group["evaluation_wall_seconds"] for group in groups[:budget]) / 3600
                           for budget in budgets], "D--", color="#666666", label="Grid canonical prefix")
    axes[0].axhline(1, color="#888888", linestyle=":", linewidth=1, label="Full Grid lowest median")
    axes[0].set_yscale("log")
    axes[0].set_ylabel("Selected / full Grid time in P2 table (log scale)")
    axes[0].set_title("Configuration selection quality (post-hoc)")
    axes[1].set_ylabel("Configuration evaluator wall time (hours)")
    axes[1].set_title("Search cost (gates, setup and retests excluded)")
    for axis in axes:
        axis.set_xlabel("Unique configuration evaluations")
        axis.set_xticks(budgets)
        axis.grid(axis="y", alpha=0.2)
        axis.legend(fontsize=8, loc="best")
    partial = audit["completed_trajectory_count"] != 10
    figure.suptitle("P3 partial batch" if partial else "P3 five-seed comparison", fontsize=12)
    figure.text(0.5, 0.015,
        "P2 table is not a strategy oracle. Grid prefixes have order bias. Uncalibrated clock; cross-session cost."
        + (" Seed stability remains incomplete." if partial else ""), ha="center", fontsize=8)
    figure.tight_layout(rect=(0, 0.055, 1, 0.96))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=160)
    plt.close(figure)


if __name__ == "__main__":
    main()
