from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-directory", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args()
    args.output_directory.mkdir(parents=True, exist_ok=True)
    with (args.session_directory / "grid_summary.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 20 or any(row["valid"] != "True" for row in rows):
        raise ValueError("plots require the complete valid 20-configuration Grid")
    blocks, optimizations = [8, 16, 24, 64, 128], ["O0", "O1", "O2", "O3"]
    matrix = np.array([[float(next(row["median_seconds"] for row in rows
                                   if row["optimization"] == opt and int(row["block_size"]) == block))
                        for block in blocks] for opt in optimizations])
    fig, ax = plt.subplots(figsize=(8, 4))
    picture = ax.imshow(matrix, cmap="viridis_r", aspect="auto")
    for i in range(4):
        for j in range(5):
            ax.text(j, i, f"{matrix[i,j]:.2f}", ha="center", va="center",
                    color="white" if matrix[i,j] > matrix.mean() else "black")
    ax.set_xticks(range(5), labels=blocks)
    ax.set_yticks(range(4), labels=optimizations)
    ax.set_xlabel("Block size")
    ax.set_title("n=4096: measured median core time (seconds)")
    fig.colorbar(picture, ax=ax, label="seconds")
    fig.tight_layout()
    fig.savefig(args.output_directory / "p2_heatmap.png", dpi=160)
    plt.close(fig)

    checkpoint = json.loads((args.session_directory / "checkpoint.json").read_text())
    groups = checkpoint["completed"]
    fig, ax = plt.subplots(figsize=(11, 5))
    for index, group in enumerate(groups):
        values = group["measured_compute_seconds"]
        median = group["score_seconds"]
        ax.scatter([index] * len(values), [100 * (value / median - 1) for value in values],
                   color="#2579a4", alpha=0.75, s=18)
    ax.axhline(0, color="black", linewidth=0.7)
    ax.set_xticks(range(20), labels=[f"{group['config']['optimization']}/s{group['config']['block_size']}"
                                    for group in groups], rotation=60, ha="right")
    ax.set_ylabel("Deviation from configuration median (%)")
    ax.set_title("Five fresh measured runs per configuration (warmup excluded)")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(args.output_directory / "p2_variation.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    main()
