#!/usr/bin/env python3
"""Generate the three requested optional-study plots strictly from derived CSVs."""

import argparse
import csv
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / "analysis" / "jvm_parameter"
OUT = ROOT / "images" / "jvm_parameter"
WORKLOADS = ("compress", "derby", "sunflow", "scimark.fft.large")
HEAPS = ("default", "xmx512m", "xmx1024m", "xmx2560m")
LABELS = ("Default", "512 MiB", "1024 MiB", "2560 MiB")
COLORS = ("#345f8a", "#bf7545", "#5a866d", "#8b6a9a")


def read(name):
    with (ANALYSIS / name).open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def setup():
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 9, "axes.titlesize": 11,
        "figure.facecolor": "white", "axes.spines.top": False,
        "axes.spines.right": False, "savefig.dpi": 170,
    })


def save(fig, path):
    fig.savefig(path, bbox_inches="tight", facecolor="white",
                metadata={"Software": "A2 plot_optional.py"})
    plt.close(fig)


def panel_grid(title, ylabel):
    fig, axes = plt.subplots(2, 2, figsize=(10.8, 7.1))
    fig.suptitle(title, fontsize=14)
    for ax, workload in zip(axes.flat, WORKLOADS):
        ax.set_title(workload, loc="left", fontweight="bold")
        ax.set_xticks(range(4), LABELS, rotation=15)
        ax.set_xlim(-.6, 3.6)
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", alpha=.2)
        ax.set_axisbelow(True)
    fig.tight_layout(rect=(0, .04, 1, .94))
    return fig, axes


def score_plot(summary, attempts, path):
    fig, axes = panel_grid("Heap size vs measured SPECjvm2008 score", "ops/min within this workload")
    for ax, workload in zip(axes.flat, WORKLOADS):
        for x, heap in enumerate(HEAPS):
            row = summary[workload, heap]
            samples = [float(r["score_ops_per_min"]) for r in attempts
                       if r["workload"] == workload and r["heap_config"] == heap and r["status"] == "valid"]
            if not samples:
                ax.text(x, .5, "n=0", transform=ax.get_xaxis_transform(),
                        ha="center", va="center", color="#9b4a43", fontsize=8)
                continue
            mean = float(row["mean_score_ops_per_min"])
            sd = float(row["sample_std_score_ops_per_min"]) if row["sample_std_score_ops_per_min"] else 0
            ax.bar(x, mean, color=COLORS[x], alpha=.77, width=.68)
            if sd:
                ax.errorbar(x, mean, yerr=sd, color="#232323", capsize=4, fmt="none")
            offsets = (-.13, 0, .13)
            for i, score in enumerate(samples):
                ax.plot(x + offsets[i], score, "o", color="#202020", markersize=3.8)
            ax.text(x, .02, f"n={len(samples)}", transform=ax.get_xaxis_transform(),
                    ha="center", va="bottom", fontsize=8, color="white" if mean else "black")
        ax.set_ylim(bottom=0)
    fig.text(.5, .01, "Bars: valid-run mean; whiskers: sample SD; dots: individual valid runs. "
             "Do not compare absolute ops/min across unlike workloads.", ha="center", fontsize=8)
    save(fig, path)


def gc_plot(summary, attempts, path):
    fig, axes = panel_grid("Heap size vs observed whole-process GC pause time", "summed GC pauses (s)")
    for ax, workload in zip(axes.flat, WORKLOADS):
        for x, heap in enumerate(HEAPS):
            row = summary[workload, heap]
            samples = [float(r["gc_time_s"]) for r in attempts
                       if r["workload"] == workload and r["heap_config"] == heap
                       and r["status"] == "valid" and r["gc_time_s"]]
            if not samples:
                ax.text(x, .5, "n=0", transform=ax.get_xaxis_transform(),
                        ha="center", va="center", color="#9b4a43", fontsize=8)
                continue
            mean = float(row["mean_gc_time_s"])
            sd = float(row["sample_std_gc_time_s"]) if row["sample_std_gc_time_s"] else 0
            ax.bar(x, mean, color=COLORS[x], alpha=.77, width=.68)
            if sd:
                ax.errorbar(x, mean, yerr=sd, color="#232323", capsize=4, fmt="none")
            for i, gc_time in enumerate(samples):
                ax.plot(x + (-.13, 0, .13)[i], gc_time, "o", color="#202020", markersize=3.8)
            ax.text(x, .02, f"n={len(samples)}", transform=ax.get_xaxis_transform(),
                    ha="center", va="bottom", fontsize=8, color="white" if mean else "black")
        ax.set_ylim(bottom=0)
    fig.text(.5, .01, "GC logs cover the full Java process, not only the 240 s measured interval. "
             "Bars/whiskers/dots use valid runs only.", ha="center", fontsize=8)
    save(fig, path)


def change_plot(summary, path):
    fig, axes = panel_grid("Measured score change vs same-workload default", "change in mean score (%)")
    for ax, workload in zip(axes.flat, WORKLOADS):
        ax.axhline(0, color="#343434", linewidth=.8)
        for x, heap in enumerate(HEAPS):
            row = summary[workload, heap]
            value = row["score_change_vs_default_percent"]
            if not value:
                ax.text(x, .5, "n=0", transform=ax.get_xaxis_transform(),
                        ha="center", va="center", color="#9b4a43", fontsize=8)
                continue
            percent = float(value)
            ax.bar(x, percent, color=COLORS[x], width=.68)
            ax.annotate(f"{percent:+.1f}%", (x, percent), xytext=(0, 3 if percent >= 0 else -12),
                        textcoords="offset points", ha="center", fontsize=8)
        ax.margins(y=.2)
    fig.text(.5, .01, "Percentage uses the mean of valid repetitions in each configuration; "
             "not a paired or causal estimate.", ha="center", fontsize=8)
    save(fig, path)


def generate(folder):
    setup()
    folder.mkdir(parents=True, exist_ok=True)
    attempts = read("heap_parameter_results.csv")
    summary = {(r["workload"], r["heap_config"]): r for r in read("heap_parameter_summary.csv")}
    figures = (
        ("heap_vs_score.png", lambda p: score_plot(summary, attempts, p)),
        ("heap_vs_gc_time.png", lambda p: gc_plot(summary, attempts, p)),
        ("heap_vs_score_change.png", lambda p: change_plot(summary, p)),
    )
    for name, draw in figures:
        draw(folder / name)
    return [name for name, _ in figures]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        with tempfile.TemporaryDirectory() as temp:
            for name in generate(Path(temp)):
                if not (OUT / name).is_file() or (OUT / name).read_bytes() != (Path(temp) / name).read_bytes():
                    raise ValueError(f"Plot differs from CSV source: {name}")
    else:
        generate(OUT)
    print("PASS: three optional-study CSV-driven plots")


if __name__ == "__main__":
    main()
