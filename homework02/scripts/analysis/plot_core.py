#!/usr/bin/env python3
"""Reproducible core figures; only CSVs verified against raw evidence are inputs."""

import argparse
import csv
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / "analysis"
OUT = ROOT / "images" / "analysis"
BLUE = "#285e91"
ORANGE = "#cf7839"
GREEN = "#4b8870"
METRICS = ("Composite", "compress", "derby", "sunflow", "crypto", "startup", "scimark.large")
FOCUS = ("compress", "derby", "sunflow", "crypto.aes", "scimark.fft.small", "scimark.fft.large")


def read(name):
    with (ANALYSIS / name).open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def configure():
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10, "axes.titlesize": 13,
        "figure.facecolor": "white", "axes.spines.top": False,
        "axes.spines.right": False, "savefig.dpi": 170,
    })


def save(fig, output):
    fig.savefig(output, bbox_inches="tight", facecolor="white", metadata={"Software": "A2 plot_core.py"})
    plt.close(fig)


def plot_groups(path):
    rows = {row["group"]: float(row["score_ops_per_min"]) for row in read("base_result_table.csv")}
    names = [name for name in rows if name not in ("Composite", "startup")]
    fig, (ax, startup_ax) = plt.subplots(2, 1, figsize=(9.5, 6.8),
                                         gridspec_kw={"height_ratios": [5, 1]})
    y = np.arange(len(names))
    ax.barh(y, [rows[name] for name in names], color=BLUE, height=.7)
    ax.set_yticks(y, names)
    ax.invert_yaxis()
    ax.set_xlim(0, max(rows[name] for name in names) * 1.16)
    ax.set_xlabel("Throughput group score (ops/min; different operations)")
    ax.grid(axis="x", alpha=.22)
    ax.set_axisbelow(True)
    for i, name in enumerate(names):
        ax.text(rows[name] + 12, i, f"{rows[name]:.2f}", va="center", fontsize=8)
    startup_ax.barh([0], [rows["startup"]], color=ORANGE, height=.48)
    startup_ax.set_yticks([0], ["startup"])
    startup_ax.set_xlim(0, 40)
    startup_ax.set_xlabel("Startup group score (ops/min; separate scale)")
    startup_ax.text(rows["startup"] + .4, 0, f"{rows['startup']:.2f}", va="center")
    fig.suptitle(f"Local compliant Base .007: 11 group scores (Composite {rows['Composite']:.2f})")
    fig.subplots_adjust(hspace=.55)
    save(fig, path)


def plot_warmup(path):
    rows = {row["workload"]: row for row in read("workload_measurements.csv")}
    values = [float(rows[name]["percent_change"]) for name in FOCUS]
    fig, (ax, labels_ax) = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True,
                                       gridspec_kw={"width_ratios": [3, 1.8]})
    y = np.arange(len(FOCUS))
    ax.barh(y, values, color=[ORANGE if v < 0 else BLUE for v in values], height=.62)
    ax.axvline(0, color="#444444", linewidth=.8)
    ax.set_yticks(y, FOCUS)
    ax.invert_yaxis()
    ax.set_xlim(min(-9.2, min(values) * 1.2), max(4.2, max(values) * 1.5))
    ax.set_xlabel("Measured vs warmup change within each workload (%)")
    ax.set_title("Change from warmup to measured iteration")
    ax.grid(axis="x", alpha=.2)
    ax.set_axisbelow(True)
    for i, name in enumerate(FOCUS):
        row = rows[name]
        label = f"{row['warmup_ops_per_min']} → {row['measured_ops_per_min']} ops/min"
        labels_ax.text(0, i, label, va="center", fontsize=9, color="#333333")
    labels_ax.set_xlim(0, 1)
    labels_ax.set_xticks([])
    labels_ax.set_title("Warmup → measured")
    for spine in labels_ax.spines.values():
        spine.set_visible(False)
    labels_ax.tick_params(left=False, labelleft=False)
    save(fig, path)


def plot_repeats(path):
    rows = read("repeat_statistics.csv")
    x = np.arange(1, len(rows) + 1)
    scores = [float(row["score_ops_per_min"]) for row in rows]
    mean = float(rows[0]["mean_ops_per_min"])
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(x, scores, color=BLUE, marker="o", linewidth=2, markersize=8)
    ax.axhline(mean, color=ORANGE, linestyle="--", label=f"mean {mean:.3f} ops/min")
    ax.set_xticks(x, [row["run"] for row in rows])
    ax.set_ylabel("compress measured score (ops/min)")
    ax.set_ylim(min(scores) - 22, max(scores) + 18)
    ax.set_title(f"Original three compress runs; sample CV {rows[0]['cv_percent']}% (zoomed y-axis)")
    ax.grid(axis="y", alpha=.22)
    ax.legend(loc="lower left", frameon=False)
    for xi, score in zip(x, scores):
        ax.annotate(f"{score:.2f}", (xi, score), xytext=(0, 9),
                    textcoords="offset points", ha="center")
    fig.text(.5, -.02, "Order is chronological; n=3 cannot identify a cause for the decline.",
             ha="center", fontsize=9, color="#555555")
    save(fig, path)


def plot_official(path):
    local = {row["group"]: float(row["score_ops_per_min"]) for row in read("base_result_table.csv")}
    official = {}
    for row in read("official_group_scores.csv"):
        official.setdefault(row["reference"], {})[row["metric"]] = float(row["score_ops_per_min"])
    if set(official) != {"Huawei RH 2285", "Sugon I620-G20"}:
        raise ValueError("Unexpected official reference set")
    if any(set(scores) != set(METRICS) for scores in official.values()):
        raise ValueError("Official metric set incomplete")
    fig, ax = plt.subplots(figsize=(9.8, 5.0))
    y = np.arange(len(METRICS))
    height = .36
    for offset, (reference, color) in zip((-.18, .18),
                                          (("Huawei RH 2285", GREEN), ("Sugon I620-G20", ORANGE))):
        ratios = [official[reference][metric] / local[metric] for metric in METRICS]
        ax.barh(y + offset, ratios, height, label=reference, color=color)
    ax.axvline(1, color="#333333", linestyle="--", linewidth=1)
    ax.set_yticks(y, METRICS)
    ax.invert_yaxis()
    ax.set_xlabel("Official / local score (dimensionless; same-named metric only)")
    ax.set_title("Published reference ratios are observations, not causal effects")
    ax.legend(loc="lower right", frameon=False)
    ax.grid(axis="x", alpha=.2)
    ax.set_axisbelow(True)
    save(fig, path)


def generate(folder):
    configure()
    folder.mkdir(parents=True, exist_ok=True)
    functions = (
        ("base_group_scores.png", plot_groups),
        ("warmup_measured.png", plot_warmup),
        ("repeat_compress.png", plot_repeats),
        ("official_comparison.png", plot_official),
    )
    for name, function in functions:
        function(folder / name)
    return [name for name, _ in functions]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        with tempfile.TemporaryDirectory() as temp:
            for name in generate(Path(temp)):
                existing = OUT / name
                if not existing.is_file() or existing.read_bytes() != (Path(temp) / name).read_bytes():
                    raise ValueError(f"Figure differs from source CSV or is missing: {existing}")
    else:
        generate(OUT)
    print("PASS: four CSV-driven core figures")


if __name__ == "__main__":
    main()
