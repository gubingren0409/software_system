#!/usr/bin/env python3
"""Build the independent nine-attempt OOM reverification table and report."""

import argparse
import csv
import io
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / "analysis" / "jvm_parameter"
LOGS = ROOT / "logs" / "jvm_parameter" / "oom_reverification"
RESULTS = ROOT / "specjvm2008" / "verification_results"
OUTPUT_CSV = ANALYSIS / "oom_reverification_results.csv"
OUTPUT_MD = ANALYSIS / "oom_reverification_report.md"
FORMAL_HASH = "4ae651e312061d09760743ab9908129b633e9ce1e5b5b296c13d4a30605e05ad"
ATTEMPTS = (
    ("derby", "xmx512m", 1), ("derby", "xmx512m", 2), ("derby", "xmx512m", 3),
    ("scimark.fft.large", "xmx512m", 1), ("scimark.fft.large", "xmx1024m", 1),
    ("scimark.fft.large", "xmx512m", 2), ("scimark.fft.large", "xmx1024m", 2),
    ("scimark.fft.large", "xmx512m", 3), ("scimark.fft.large", "xmx1024m", 3),
)
FIELDS = (
    "source_run_key", "verification_run_key", "workload", "heap_config", "run_id",
    "original_result_id", "verification_result_id", "original_invalid_reason",
    "original_java_exit_status", "verification_java_exit_status",
    "original_wall_s", "verification_wall_s", "original_oom_occurrences",
    "verification_oom_occurrences", "original_gc_count", "verification_gc_count",
    "original_full_gc_count", "verification_full_gc_count", "original_gc_pause_s",
    "verification_gc_pause_s", "verification_reporter_exit_status",
    "verification_start_time", "verification_end_time",
    "verification_not_valid", "verification_measured_score_present",
    "verification_young_gc_count", "failure_reproduced", "run_log_path", "gc_log_path",
    "raw_path", "txt_path", "command",
)
GC_EVENT = re.compile(r"^\s*\d+(?:\.\d+)?:\s+\[(Full GC|GC)\b")
GC_PAUSE = re.compile(r",\s*(\d+(?:\.\d+)?) secs\]")


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_meta(path):
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.partition("=")
        if sep:
            values[key] = value
    return values


def relative(path):
    return path.relative_to(ROOT).as_posix()


def parse_gc(path):
    young = full = 0
    pause = 0.0
    for line in path.read_text(encoding="latin-1", errors="replace").splitlines():
        event = GC_EVENT.match(line)
        if not event:
            continue
        pauses = GC_PAUSE.findall(line)
        if not pauses:
            raise ValueError(f"GC event has no pause: {path}: {line[:100]}")
        pause += float(pauses[-1])
        if event.group(1) == "Full GC":
            full += 1
        else:
            young += 1
    return young, full, pause


def build_rows():
    originals = {row["run_key"]: row for row in read_csv(ANALYSIS / "heap_parameter_results.csv")}
    rows = []
    for workload, heap, repetition in ATTEMPTS:
        slug = workload.replace(".", "_")
        source_key = f"{slug}__{heap}__r{repetition}"
        verify_key = f"oomverify__{source_key}"
        meta_path = LOGS / f"{verify_key}.meta"
        if not meta_path.is_file():
            raise FileNotFoundError(f"Missing completed reverification: {meta_path}")
        meta = read_meta(meta_path)
        run_log = LOGS / meta["run_log"]
        gc_log = LOGS / "gc" / meta["gc_log"]
        run_text = run_log.read_text(encoding="latin-1", errors="replace")
        young, full, pause = parse_gc(gc_log)
        result_id = meta["result_id"]
        result_dir = RESULTS / result_id
        raw = result_dir / f"{result_id}.raw"
        txt = result_dir / f"{result_id}.txt"
        original = originals[source_key]
        original_run_text = (ROOT / original["run_log_path"]).read_text(
            encoding="latin-1", errors="replace"
        )
        start = datetime.fromisoformat(meta["start_time"])
        end = datetime.fromisoformat(meta["end_time"])
        oom_count = run_text.count("OutOfMemoryError")
        not_valid = "NOT VALID" in run_text
        score_present = bool(re.search(
            rf"Score on\s+{re.escape(workload)}\s*:\s*[0-9]+(?:\.[0-9]+)?\s+ops/m",
            run_text,
        ))
        reproduced = oom_count > 0 and not_valid and not score_present
        rows.append({
            "source_run_key": source_key,
            "verification_run_key": verify_key,
            "workload": workload,
            "heap_config": heap,
            "run_id": f"Run{repetition}",
            "original_result_id": original["result_id"],
            "verification_result_id": result_id,
            "original_invalid_reason": original["invalid_reason"],
            "original_java_exit_status": original["java_exit_status"],
            "verification_java_exit_status": meta["java_exit_status"],
            "original_wall_s": original["attempt_wall_s"],
            "verification_wall_s": f"{(end - start).total_seconds():.3f}",
            "original_oom_occurrences": original_run_text.count("OutOfMemoryError"),
            "verification_oom_occurrences": oom_count,
            "original_gc_count": original["gc_count"],
            "verification_gc_count": young + full,
            "original_full_gc_count": original["gc_full_count"],
            "verification_full_gc_count": full,
            "original_gc_pause_s": original["gc_time_s"],
            "verification_gc_pause_s": f"{pause:.7f}",
            "verification_reporter_exit_status": meta["reporter_exit_status"],
            "verification_start_time": meta["start_time"],
            "verification_end_time": meta["end_time"],
            "verification_not_valid": str(not_valid).lower(),
            "verification_measured_score_present": str(score_present).lower(),
            "verification_young_gc_count": young,
            "failure_reproduced": str(reproduced).lower(),
            "run_log_path": relative(run_log),
            "gc_log_path": relative(gc_log),
            "raw_path": relative(raw) if raw.is_file() else "",
            "txt_path": relative(txt) if txt.is_file() else "",
            "command": meta["command"],
        })
    return rows


def csv_content(rows):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def report_content(rows):
    reproduced = sum(row["failure_reproduced"] == "true" for row in rows)
    first_log = (ROOT / rows[0]["run_log_path"]).read_text(encoding="latin-1", errors="replace")
    uname = re.search(r"^UNAME=(.+)$", first_log, re.M).group(1)
    java_home = re.search(r"^JAVA_HOME=(.+)$", first_log, re.M).group(1)
    java_version = re.search(r'^openjdk version "([^"]+)"$', first_log, re.M).group(1)
    vm_build = re.search(r"^OpenJDK 64-Bit Server VM \(build ([^,]+),", first_log, re.M).group(1)
    start = min(row["verification_start_time"] for row in rows)
    end = max(row["verification_end_time"] for row in rows)
    lines = [
        "# 9 个 OOM/invalid 尝试的独立复核",
        "",
        "## 目的与隔离措施",
        "",
        "本复核重新执行原实验中 9 个 OOM/invalid 单元，检查失败是否可重复。它不属于原 48 次实验矩阵，"
        "不替换原 Result ID 或分数。新日志位于 `logs/jvm_parameter/oom_reverification/`，新 SPEC 输出位于 "
        "`specjvm2008/verification_results/`；原 `specjvm2008/results/` 未作为写入目标。正式 `.007` raw 的 "
        f"SHA-256 仍为 `{FORMAL_HASH}`。",
        "",
        "JVM、SPEC 套件、`--base -bt 16`、workload、`-Xmx` 和 GC 选项与原实验相同；仅日志路径和结果保存命名空间改变。"
        "所有复核统一使用 900 秒 watchdog。原 Derby Run2/Run3 本来即使用该边界；原 Run1 是约 956 秒人工终止，"
        "因此 Run1 的外层终止方式不是字节级相同，这一差异不影响是否再次观察到 OOM/NOT VALID，但限制退出码的直接比较。",
        "",
        "## 实际复核环境",
        "",
        f"- 执行时段：`{start}` 至 `{end}`。",
        f"- OS/内核：`{uname}`。",
        f"- 测量 JVM：OpenJDK `{java_version}`，HotSpot `{vm_build}`；`JAVA_HOME={java_home}`；`CLASSPATH` 为空。",
        "- 实际最大堆：512 MiB 单元为 `536870912` bytes，1024 MiB 单元为 `1073741824` bytes；每轮运行日志均保存 `PrintFlagsFinal` 输出。",
        "- 每轮开始前均记录 `free -h`；WSL 可见内存为 7.4 GiB、swap 为 2.0 GiB，可用内存在各轮间变化。",
        "",
        "## 逐次结果",
        "",
        "| 原单元 | 新 Result ID | 原→新 Java / 新 Reporter 退出 | 原→新 OOM | 原→新 GC / Full GC | 原→新 GC 暂停（s） | 正式分数 | 复现 |",
        "|---|---|---:|---:|---:|---:|---|---|",
    ]
    for row in rows:
        score = "有" if row["verification_measured_score_present"] == "true" else "无"
        verdict = "是" if row["failure_reproduced"] == "true" else "否"
        lines.append(
            f"| `{row['source_run_key']}` | `{row['verification_result_id']}` | "
            f"{row['original_java_exit_status']}→{row['verification_java_exit_status']} / "
            f"{row['verification_reporter_exit_status']} | "
            f"{row['original_oom_occurrences']}→{row['verification_oom_occurrences']} | "
            f"{row['original_gc_count']}/{row['original_full_gc_count']}→"
            f"{row['verification_gc_count']}/{row['verification_full_gc_count']} | "
            f"{float(row['original_gc_pause_s']):.3f}→{float(row['verification_gc_pause_s']):.3f} | "
            f"{score} | {verdict} |"
        )
    lines += [
        "",
        "## 判定",
        "",
        f"按预先采用的联合判据（控制台含 `OutOfMemoryError`、workload 标为 `NOT VALID`、没有正式测量分数），"
        f"**{reproduced}/9** 个失败得到复现。退出码不单独决定有效性：FFT large 可能由 SPEC 外层正常返回，"
        "而 Derby 达到 watchdog 返回 124；两者都必须结合 OOM、NOT VALID、raw/日志完整性判断。",
        "",
        "原实验与复核的 GC 次数、Full GC 次数和暂停不要求完全相等，因为宿主后台负载、时钟、JIT/GC 时序会变化；"
        "本复核回答的是失败类别能否在相同 JVM/SPEC/堆配置下再次出现，而不是要求逐事件轨迹相同。逐行数值、路径和命令"
        "见 [`oom_reverification_results.csv`](oom_reverification_results.csv)。",
        "",
        "## 限制",
        "",
        "复核发生在原实验之后，宿主后台状态不可能完全还原。每轮日志保存内存快照，但没有同步 CPU 频率、温度或宿主负载"
        "时间序列。900 秒 watchdog 会截断 Derby 的长期 Full GC thrash，"
        "因此 GC 总数和总暂停只描述该观察窗口。复核结果不能回填原矩阵，也不能作为新的性能分数。",
        "",
        "## 复现与验证",
        "",
        "```powershell",
        "pwsh -NoProfile -File homework02/scripts/jvm_parameter/run_oom_reverification.ps1",
        "python homework02/scripts/jvm_parameter/build_oom_reverification.py",
        "python homework02/scripts/jvm_parameter/build_oom_reverification.py --check",
        "```",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rows = build_rows()
    csv_data = csv_content(rows)
    md_data = report_content(rows)
    if args.check:
        if OUTPUT_CSV.read_text(encoding="utf-8") != csv_data:
            raise ValueError("Reverification CSV differs from raw evidence")
        if OUTPUT_MD.read_text(encoding="utf-8") != md_data:
            raise ValueError("Reverification report differs from CSV/raw evidence")
    else:
        OUTPUT_CSV.write_text(csv_data, encoding="utf-8", newline="")
        OUTPUT_MD.write_text(md_data, encoding="utf-8", newline="")
    print(f"PASS: {sum(r['failure_reproduced'] == 'true' for r in rows)}/9 OOM/invalid failures reproduced")


if __name__ == "__main__":
    main()
