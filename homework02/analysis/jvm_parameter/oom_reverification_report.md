# 9 个 OOM/invalid 尝试的独立复核

## 目的与隔离措施

本复核重新执行原实验中 9 个 OOM/invalid 单元，检查失败是否可重复。它不属于原 48 次实验矩阵，不替换原 Result ID 或分数。新日志位于 `logs/jvm_parameter/oom_reverification/`，新 SPEC 输出位于 `specjvm2008/verification_results/`；原 `specjvm2008/results/` 未作为写入目标。正式 `.007` raw 的 SHA-256 仍为 `4ae651e312061d09760743ab9908129b633e9ce1e5b5b296c13d4a30605e05ad`。

JVM、SPEC 套件、`--base -bt 16`、workload、`-Xmx` 和 GC 选项与原实验相同；仅日志路径和结果保存命名空间改变。所有复核统一使用 900 秒 watchdog。原 Derby Run2/Run3 本来即使用该边界；原 Run1 是约 956 秒人工终止，因此 Run1 的外层终止方式不是字节级相同，这一差异不影响是否再次观察到 OOM/NOT VALID，但限制退出码的直接比较。

## 实际复核环境

- 执行时段：`2026-10-02T15:28:23+08:00` 至 `2026-10-02T16:19:49+08:00`。
- OS/内核：`Linux localhost 6.18.40.1-microsoft-standard-WSL2 #1 SMP PREEMPT_DYNAMIC Fri Jul 31 22:12:15 UTC 2026 x86_64 x86_64 x86_64 GNU/Linux`。
- 测量 JVM：OpenJDK `1.7.0_75`，HotSpot `24.75-b04`；`JAVA_HOME=/home/gubingren/java/java-se-7u75-ri`；`CLASSPATH` 为空。
- 实际最大堆：512 MiB 单元为 `536870912` bytes，1024 MiB 单元为 `1073741824` bytes；每轮运行日志均保存 `PrintFlagsFinal` 输出。
- 每轮开始前均记录 `free -h`；WSL 可见内存为 7.4 GiB、swap 为 2.0 GiB，可用内存在各轮间变化。

## 逐次结果

| 原单元 | 新 Result ID | 原→新 Java / 新 Reporter 退出 | 原→新 OOM | 原→新 GC / Full GC | 原→新 GC 暂停（s） | 正式分数 | 复现 |
|---|---|---:|---:|---:|---:|---|---|
| `derby__xmx512m__r1` | `SPECjvm2008.066` | 143→124 / 255 | 1→5 | 13167/13111→13609/13554 | 842.018→801.145 | 无 | 是 |
| `derby__xmx512m__r2` | `SPECjvm2008.067` | 124→255 / 255 | 4→17 | 12666/12616→11239/11188 | 810.015→687.947 | 无 | 是 |
| `derby__xmx512m__r3` | `SPECjvm2008.068` | 124→124 / 255 | 14→9 | 12191/12133→13186/13138 | 789.865→789.670 | 无 | 是 |
| `scimark_fft_large__xmx512m__r1` | `SPECjvm2008.069` | 0→0 / 0 | 16→16 | 121/60→121/60 | 1.533→1.551 | 无 | 是 |
| `scimark_fft_large__xmx1024m__r1` | `SPECjvm2008.070` | 0→0 / 0 | 10→10 | 75/36→71/34 | 1.424→1.516 | 无 | 是 |
| `scimark_fft_large__xmx512m__r2` | `SPECjvm2008.071` | 0→0 / 0 | 16→16 | 121/60→121/60 | 1.572→1.577 | 无 | 是 |
| `scimark_fft_large__xmx1024m__r2` | `SPECjvm2008.072` | 0→0 / 0 | 10→10 | 68/33→75/37 | 1.224→1.666 | 无 | 是 |
| `scimark_fft_large__xmx512m__r3` | `SPECjvm2008.073` | 0→0 / 0 | 16→16 | 121/60→121/60 | 1.502→1.508 | 无 | 是 |
| `scimark_fft_large__xmx1024m__r3` | `SPECjvm2008.074` | 0→0 / 0 | 10→10 | 75/36→71/35 | 1.566→1.899 | 无 | 是 |

## 判定

按预先采用的联合判据（控制台含 `OutOfMemoryError`、workload 标为 `NOT VALID`、没有正式测量分数），**9/9** 个失败得到复现。退出码不单独决定有效性：FFT large 可能由 SPEC 外层正常返回，而 Derby 达到 watchdog 返回 124；两者都必须结合 OOM、NOT VALID、raw/日志完整性判断。

原实验与复核的 GC 次数、Full GC 次数和暂停不要求完全相等，因为宿主后台负载、时钟、JIT/GC 时序会变化；本复核回答的是失败类别能否在相同 JVM/SPEC/堆配置下再次出现，而不是要求逐事件轨迹相同。逐行数值、路径和命令见 [`oom_reverification_results.csv`](oom_reverification_results.csv)。

## 限制

复核发生在原实验之后，宿主后台状态不可能完全还原。每轮日志保存内存快照，但没有同步 CPU 频率、温度或宿主负载时间序列。900 秒 watchdog 会截断 Derby 的长期 Full GC thrash，因此 GC 总数和总暂停只描述该观察窗口。复核结果不能回填原矩阵，也不能作为新的性能分数。

## 复现与验证

```powershell
pwsh -NoProfile -File homework02/scripts/jvm_parameter/run_oom_reverification.ps1
python homework02/scripts/jvm_parameter/build_oom_reverification.py
python homework02/scripts/jvm_parameter/build_oom_reverification.py --check
```
