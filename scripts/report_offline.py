"""Read archived results and write NEW report derivatives; never run an experiment.

No autotuner imports, subprocesses, resource sampling, claims, or cache writes.
Only the explicit --output and optional --figures directories are writable; both
must be new. Python's standard library suffices unless figures are requested.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
GRID = "evidence/p3_raw_grid/20261011-021601/final-content/grid-f705a488"
GRID_END = "evidence/p3_raw_grid/20261012-181149-manual-remaining"
VALIDATION = "evidence/p3_raw_comparison/20261014-182807-ac-validation/validation-9332ead2"
VALIDATION_END = "evidence/p3_raw_comparison/20261019-122200-user-retry4"
SEARCH = "evidence/p3_raw_first_seed/20261019-132400/content/search-c1bd157c"
SEARCH_END = "evidence/p3_raw_first_seed/20261020-214028-09795d71-first-seed-finish"
INPUT_HASHES: dict[str, str] = {}


def read(name: str) -> str:
    data = (ROOT / name).read_bytes()
    INPUT_HASHES[name] = hashlib.sha256(data).hexdigest()
    return data.decode("utf-8-sig")


def load(name: str):
    return json.loads(read(name))


def close(actual, expected):
    if not math.isclose(float(actual), float(expected), rel_tol=1e-12, abs_tol=1e-9):
        raise ValueError(f"Archived/derived values differ: {actual} != {expected}")


def label(config):
    return f"{config['optimization']}/s{config['block_size']}"


def rows(name):
    return list(csv.DictReader(io.StringIO(read(name))))


def samples(directory):
    result = [json.loads(line) for line in read(directory + "/samples.jsonl").splitlines()]
    mapping = {s["run_id"]: s for s in result}
    assert len(result) == len(mapping), "Duplicate raw run_id"
    return mapping


def group(group, raw):
    """Recompute published statistics from six exact archived raw records."""
    saved = group["samples"]
    assert group["classification"] == "success" and len(saved) == 6
    ids = [s["run_id"] for s in saved]
    assert len(set(ids)) == 6
    current = [raw[identifier] for identifier in ids]
    assert saved == current, "Checkpoint group differs from JSONL"
    for index, item in enumerate(current):
        assert item["sample_index"] == index
        assert item["role"] == ("warmup" if index == 0 else "measurement")
        assert item["source"] == "fresh_measurement" and item["context"]["force_remeasure"] is True
        assert item["classification"] == "success" and item["returncode"] == 0
        target = item["target_result"]
        assert target["n"] == 4096 and target["checked_entries"] == 4096 ** 2
        assert target["seed"] == 20261008 and target["input"] == "random"
        assert target["validation"] is True and target["mismatch_count"] == 0
        assert target["primary_clock"] == "CLOCK_MONOTONIC_RAW"
        assert type(target["raw_start_ns"]) is int and type(target["raw_end_ns"]) is int
        elapsed = (target["raw_end_ns"] - target["raw_start_ns"]) / 1e9
        assert elapsed > 0 and math.isfinite(elapsed)
        close(elapsed, target["elapsed_seconds"])
        close(elapsed, item["score_seconds"])
    values = [s["score_seconds"] for s in current[1:]]
    median = statistics.median(values)
    mean = statistics.mean(values)
    cv = statistics.stdev(values) / mean
    mad = statistics.median(abs(v - median) for v in values)
    close(median, group["score_seconds"])
    for field, value in (("median_seconds", median), ("coefficient_of_variation", cv),
                         ("median_absolute_deviation_seconds", mad)):
        close(value, group["statistics"][field])
    assert group["evaluation_wall_clock"] == "CLOCK_MONOTONIC_RAW"
    return dict(config=label(group["config"]), median=median, cv_percent=100 * cv, mad=mad,
                values=values, run_ids=ids, attempt_id=group["attempt_id"],
                evaluation_raw_seconds=group["evaluation_wall_seconds"])


def derive():
    grid_state, search_state, validation_state = [load(p + "/checkpoint.json")
                                                for p in (GRID, SEARCH, VALIDATION)]
    grid_raw, search_raw, validation_raw = [samples(p) for p in (GRID, SEARCH, VALIDATION)]
    grid = [group(g, grid_raw) for g in grid_state["completed"]]
    expected_order = [f"{o}/s{s}" for o in ("O0", "O1", "O2", "O3") for s in (8, 16, 24, 64, 128)]
    assert [g["config"] for g in grid] == expected_order and len(grid_raw) == 120
    for g, row in zip(grid, rows(GRID_END + "/grid_summary_20.csv")):
        assert g["config"] == label({"optimization": row["optimization"], "block_size": row["block_size"]})
        close(g["median"], row["median_seconds"])
        close(g["cv_percent"] / 100, row["coefficient_of_variation"])
        close(g["mad"], row["median_absolute_deviation_seconds"])
    validation = [group(g, validation_raw) for g in validation_state["validation_groups"]]
    assert len(validation_raw) == 18
    for g, row in zip(validation, rows(VALIDATION_END + "/three_configuration_comparison.csv")):
        close(g["median"], row["independent_median_raw_seconds"])
        close(g["cv_percent"], row["independent_cv_percent"])
        close(g["mad"], row["independent_mad_seconds"])

    trajectories, prefixes, retests, accepted = {}, [], {}, []
    for algorithm in ("random", "greedy"):
        own = search_state["trajectories"][algorithm]
        trajectory = [group(g, search_raw) for g in own["observations"]]
        retest = [group(g, search_raw) for g in own["retests"]]
        assert len(trajectory) == 12 and len({g["config"] for g in trajectory}) == 12
        assert len(retest) == (2 if algorithm == "random" else 1)
        trajectories[algorithm], retests[algorithm] = trajectory, retest
        accepted.extend(trajectory + retest)
        for budget, published, mapping in zip((4, 8, 12), own["prefixes"], own["prefix_retest_mapping"]):
            best = min(trajectory[:budget], key=lambda g: (g["median"], expected_order.index(g["config"])))
            repeat = next(g for g in retest if g["attempt_id"] == mapping["retest_attempt"])
            cost = sum(g["evaluation_raw_seconds"] for g in trajectory[:budget])
            assert best["config"] == label(published["best_config"]) == repeat["config"]
            assert published["budget"] == budget
            close(best["median"], published["median_seconds"])
            close(cost, published["terminal_evaluation_raw_seconds"])
            prefixes.append(dict(algorithm=algorithm, budget=budget, selected_config=best["config"],
                search_median=best["median"], independent_median=repeat["median"],
                search_cv_percent=best["cv_percent"], independent_cv_percent=repeat["cv_percent"],
                search_mad=best["mad"], independent_mad=repeat["mad"],
                change_percent=100 * (repeat["median"] / best["median"] - 1),
                configuration_evaluation_raw_seconds=cost))
    for actual, row in zip(prefixes, rows(SEARCH_END + "/first_seed_six_rows.csv")):
        assert actual["algorithm"] == row["algorithm"] and actual["budget"] == int(row["budget"])
        assert actual["selected_config"] == row["selected_config"]
        for key, column in (("search_median", "search_median_raw_seconds"),
                ("independent_median", "independent_median_raw_seconds"),
                ("configuration_evaluation_raw_seconds", "terminal_configuration_evaluation_raw_seconds"),
                ("search_cv_percent", "search_cv_percent"), ("independent_cv_percent", "independent_cv_percent"),
                ("search_mad", "search_mad_seconds"), ("independent_mad", "independent_mad_seconds")):
            close(actual[key], row[column])
    ids = [identifier for g in accepted for identifier in g["run_ids"]]
    assert len(ids) == len(set(ids)) == 162 and len(search_raw) == 168
    ledger = load(SEARCH_END + "/continuation/abandoned_attempt.json")
    abandoned = {i for v in ledger["exact_combined_abandonments"].values() for i in v}
    assert set(search_raw) - set(ids) == abandoned and len(abandoned) == 6
    assert not search_state["active"] and search_state["status"] == "complete"

    windows = [load(p) for p in (SEARCH + "/window.json",
        "evidence/p3_raw_first_seed/20261019-181817-693c9e13-manual-continuation/continuation/window.json",
        SEARCH_END + "/continuation/window.json")]
    durations = [(w["qpc_end"] - w["qpc_start"]) / w["qpc_frequency"] for w in windows]
    for w, duration in zip(windows, durations):
        close(duration, w["activity_qpc_seconds"])
    costs = dict(grid=sum(g["evaluation_raw_seconds"] for g in grid),
        search={a: sum(g["evaluation_raw_seconds"] for g in v) for a, v in trajectories.items()},
        retest={a: sum(g["evaluation_raw_seconds"] for g in v) for a, v in retests.items()},
        activity_windows_qpc_seconds=durations, activity_qpc_seconds=sum(durations))
    historical_costs = load(SEARCH_END + "/costs.json")
    for a in ("random", "greedy"):
        close(costs["search"][a], historical_costs["search_terminal_configuration_evaluation_raw_seconds"][a])
        close(costs["retest"][a], historical_costs["candidate_retest_evaluation_raw_seconds"][a])
    close(costs["grid"], load(GRID_END + "/costs.json")["all_grid_nested_raw_costs"]["grid_group_evaluation_raw_seconds"])
    close(costs["activity_qpc_seconds"], historical_costs["cumulative_activity_qpc_seconds"])
    summary = load(SEARCH_END + "/delivery_summary.json")
    assert all(summary[k] is True for k in ("evidence_integrity_pass", "execution_complete", "timing_checks_pass", "comparison_ready"))
    assert summary["five_seed_execution_complete"] is False and summary["five_seed_comparison_ready"] is False
    return dict(scope="Offline derivatives of archived accepted data; not new performance or a new recovery audit",
        new_target_executions=0, grid=grid, validation=validation, trajectories=trajectories,
        prefixes=prefixes, retests=retests, costs=costs, first_seed_accepted=162,
        first_seed_abandoned=6, first_seed_total=168, five_seed_execution_complete=False)


def figures(data, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm
    from matplotlib.patches import FancyBboxPatch
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "svg.fonttype": "none"})
    output.mkdir(parents=True, exist_ok=False)
    grid = data["grid"]
    fig, ax = plt.subplots(figsize=(9, 4.5), layout="constrained")
    values = [[g["median"] for g in grid[i:i+5]] for i in range(0,20,5)]
    im = ax.imshow(values, cmap="viridis_r", norm=LogNorm(vmin=50, vmax=470), aspect="auto")
    for i in range(4):
        for j in range(5):
            ax.text(j,i,f"{values[i][j]:.3f}" + ("*" if (i,j)==(3,2) else ""),ha="center",va="center",color="white" if values[i][j] > 180 else "#161616")
    ax.set(xticks=range(5),xticklabels=[8,16,24,64,128],yticks=range(4),yticklabels=["O0","O1","O2","O3"],xlabel="Block size s",ylabel="Optimization",title="RAW Grid: median core time (seconds)")
    fig.colorbar(im,ax=ax,label="Seconds (log color scale)",ticks=[50,80,120,200,300,450])
    fig.text(.10,-.03,"Five fresh measurements; warmup excluded. * O3/s24 includes a standby-affected call.",fontsize=9)
    fig.savefig(output/"raw_grid_heatmap.png",dpi=180,bbox_inches="tight"); plt.close(fig)

    fig, axes = plt.subplots(2,2,figsize=(10,6.2),sharey=True,layout="constrained")
    for i,ax in enumerate(axes.flat):
        subset=grid[5*i:5*i+5]
        for j,g in enumerate(subset):
            y=[100*(v/g["median"]-1) for v in g["values"]]
            ax.scatter([j+(k-2)*.055 for k in range(5)],y,s=32,color="#24658c")
            if g["config"]=="O3/s24":
                ax.scatter(j+.11,y[4],s=100,facecolors="none",edgecolors="#b03b32",linewidths=1.5)
        ax.axhline(0,color="#555",lw=.8)
        ax.set(xticks=range(5),xticklabels=[8,16,24,64,128],title=f"O{i}",xlabel="Block size s",ylim=(-6,6))
        ax.grid(axis="y",alpha=.20)
    for ax in axes[:,0]: ax.set_ylabel("Deviation from own median (%)")
    fig.suptitle("All 100 Grid measurements: relative within-configuration variation")
    fig.text(.05,-.025,"Five dots/configuration; warmups excluded. Red ring: standby-affected O3/s24 measurement 5; retained.",fontsize=9)
    fig.savefig(output/"raw_grid_sample_variation.png",dpi=180,bbox_inches="tight"); plt.close(fig)

    fig,ax=plt.subplots(figsize=(12,5.8)); ax.set(xlim=(0,12),ylim=(0,6));ax.axis("off")
    def box(x,y,w,h,title,body,color="#eaf1f5"):
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.10",facecolor=color,edgecolor="#496175"))
        ax.text(x+w/2,y+h*.72,title,ha="center",va="center",weight="bold",fontsize=12)
        ax.text(x+w/2,y+h*.33,body,ha="center",va="center",fontsize=10.5)
    def arrow(a,b,label=""):
        ax.annotate("",xy=b,xytext=a,arrowprops=dict(arrowstyle="->",color="#34495e",lw=1.5))
        if label: ax.text((a[0]+b[0])/2+.08,(a[1]+b[1])/2+.1,label,fontsize=10)
    box(.3,4.55,3.3,1.05,"Target program input","target.json + teacher working C")
    box(4.35,4.55,3.3,1.05,"Configuration input","config_space.json: 4 levels x 5 sizes")
    box(8.4,4.55,3.3,1.05,"Algorithm input","Grid / Random / restart Greedy")
    box(.3,2.65,3.3,1.1,"TargetAdapter","Build by n/O; s at runtime\nVerified build/reference caches")
    box(4.35,2.65,3.3,1.1,"ConfigSpace","20 legal unique configurations")
    box(8.4,2.65,3.3,1.1,"SearchStrategy","ask / tell / best\nOwn observations only")
    box(3.7,.55,4.6,1.25,"Unified configuration evaluator","1 warmup + 5 fresh; full correctness\nMedian core RAW; any failure: no score")
    box(9.1,.55,2.5,1.25,"Saved result","Raw evidence + best\nRetest separate",color="#f6f0df")
    for x in (1.95,6,10.05): arrow((x,4.55),(x,3.85))
    arrow((3.6,3.0),(3.8,1.8));arrow((6,2.65),(6,1.8));arrow((9,2.65),(7.5,1.8),"ask(): config")
    arrow((8.3,1.12),(9.0,1.12))
    ax.annotate("",xy=(10.2,2.55),xytext=(7.9,1.8),
        arrowprops=dict(arrowstyle="->",color="#34495e",lw=1.5))
    ax.text(9.2,1.95,"tell(own score)",fontsize=10)
    fig.tight_layout();fig.savefig(output/"autotuner_framework.svg",bbox_inches="tight")
    fig.savefig(output/"autotuner_framework.png",dpi=180,bbox_inches="tight");plt.close(fig)
    return {"matplotlib":matplotlib.__version__,"warmup_excluded":True,"grid_points":100,
            "standby_sample_retained":True,"figure_source":"RAW Grid session f705a488; see summary.json input hashes"}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True,help="NEW derived directory, never an old session")
    parser.add_argument("--figures",type=Path,help="Optional NEW image directory (requires matplotlib)")
    args=parser.parse_args()
    data=derive()
    args.output.mkdir(parents=True,exist_ok=False)
    if args.figures: data["figures"]=figures(data,args.figures)
    data["input_sha256"]=INPUT_HASHES
    data["script_sha256"]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (args.output/"summary.json").write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"offline_recomputation_pass":True,"grid_configurations":len(data["grid"]),
        "first_seed_groups":27,"first_seed_raw_records":168,"prefix_rows":len(data["prefixes"]),
        "costs":data["costs"],"new_target_executions":0},indent=2))


if __name__=="__main__": main()
