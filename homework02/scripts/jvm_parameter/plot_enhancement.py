#!/usr/bin/env python3
"""Generate enhancement figures strictly from committed derived CSV files."""

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


def read_summary():
    path = ANALYSIS / "gc_measurement_summary.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return {(row["workload"], row["heap_config"]): row for row in rows}


def setup():
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 9, "axes.titlesize": 11,
        "figure.facecolor": "white", "axes.spines.top": False,
        "axes.spines.right": False, "savefig.dpi": 170,
    })


def save(fig, path):
    fig.savefig(path, bbox_inches="tight", facecolor="white",
                metadata={"Software": "A2 plot_enhancement.py"})
    plt.close(fig)


def gc_frequency_plot(summary, path):
    fig, axes = plt.subplots(2, 2, figsize=(10.8, 7.1))
    fig.suptitle("Heap size vs estimated measurement-window GC frequency", fontsize=14)
    for ax, workload in zip(axes.flat, WORKLOADS):
        ax.set_title(workload, loc="left", fontweight="bold")
        for x, heap in enumerate(HEAPS):
            row = summary[workload, heap]
            value = row["mean_measurement_gc_count"]
            if not value:
                ax.text(x, .5, "n=0", transform=ax.get_xaxis_transform(),
                        ha="center", va="center", color="#9b4a43", fontsize=8)
                continue
            count = float(value)
            ax.bar(x, count, color=COLORS[x], alpha=.8, width=.68)
            ax.annotate(f"{count:.0f}", (x, count), xytext=(0, 3),
                        textcoords="offset points", ha="center", fontsize=8)
        ax.set_xticks(range(4), LABELS, rotation=15)
        ax.set_ylabel("mean GC events per valid run")
        ax.set_ylim(bottom=0)
        ax.grid(axis="y", alpha=.2)
        ax.set_axisbelow(True)
    fig.text(.5, .01, "Valid runs only; events within ±1 s of a phase boundary are excluded. "
             "Each nonempty bar has n=3 runs.", ha="center", fontsize=8)
    fig.tight_layout(rect=(0, .04, 1, .94))
    save(fig, path)


def derby_case_plot(summary, path):
    rows = [summary["derby", heap] for heap in HEAPS]
    metrics = (
        ("mean_score_ops_per_min", "Throughput", "ops/min"),
        ("mean_measurement_full_gc_count", "Full GC frequency", "events/run"),
        ("mean_measurement_gc_pause_s", "Summed GC pauses", "seconds/run"),
        ("mean_measurement_pre_gc_max_heap_percent", "Pre-GC heap pressure", "% of max heap"),
    )
    fig, axes = plt.subplots(2, 2, figsize=(10.8, 7.1))
    fig.suptitle("Derby case study: throughput and estimated measurement-window GC", fontsize=14)
    for ax, (field, title, ylabel) in zip(axes.flat, metrics):
        ax.set_title(title, loc="left", fontweight="bold")
        for x, row in enumerate(rows):
            value = row[field]
            if not value:
                ax.text(x, .5, "n=0\n(OOM)", transform=ax.get_xaxis_transform(),
                        ha="center", va="center", color="#9b4a43", fontsize=8)
                continue
            number = float(value)
            ax.bar(x, number, color=COLORS[x], alpha=.8, width=.68)
            label = f"{number:.1f}" if abs(number) >= 10 else f"{number:.2f}"
            ax.annotate(label, (x, number), xytext=(0, 3), textcoords="offset points",
                        ha="center", fontsize=8)
        ax.set_xticks(range(4), LABELS, rotation=15)
        ax.set_ylabel(ylabel)
        ax.set_ylim(bottom=0)
        ax.grid(axis="y", alpha=.2)
        ax.set_axisbelow(True)
    fig.text(.5, .01, "Bars are means of n=3 valid runs; 512 MiB had 0/3 valid Derby runs. "
             "Phase assignment is an estimate with ±1 s boundary exclusion.", ha="center", fontsize=8)
    fig.tight_layout(rect=(0, .04, 1, .94))
    save(fig, path)


def generate(folder):
    setup()
    folder.mkdir(parents=True, exist_ok=True)
    summary = read_summary()
    outputs = (
        ("heap_vs_gc_frequency.png", gc_frequency_plot),
        ("derby_case_study.png", derby_case_plot),
    )
    for name, draw in outputs:
        draw(summary, folder / name)
    return [name for name, _ in outputs]


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
    print("PASS: two enhancement CSV-driven plots")


if __name__ == "__main__":
    main()
