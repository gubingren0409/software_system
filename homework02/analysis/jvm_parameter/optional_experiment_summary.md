# SPECjvm2008 选做：`-Xmx` 参数优化实验总结

## 研究问题与固定条件

问题是：在 AMD Ryzen 9 7940HX、WSL2 Ubuntu 24.04、OpenJDK 7u75 RI、SPECjvm2008 1.01、`--base -bt 16` 不变时，最大堆上限 `-Xmx` 如何与不同 workload 的吞吐和 GC 行为关联？只改变 `-Xmx`：默认、512 MiB、1024 MiB、2560 MiB；不修改 properties、benchmark、JDK、collector 或 `-Xms`。

选择 compress、derby、sunflow、scimark.fft.large，分别覆盖较低分配压力的压缩、对象/数据库操作、并行渲染对象结构和大数组 FFT。每个 workload × 配置以独立 JVM 重复 3 次，配置顺序在三轮中交叉，共 **48 个计划尝试**。命令保留默认 120 秒 warmup、240 秒 measurement，并固定启用 Java 7 GC 详细日志。完整设计见[`jvm_parameter_design.md`](jvm_parameter_design.md)，选择依据见[`workload_selection.md`](workload_selection.md)。

这 48 次中 **39 次产生有效正式分数，9 次因 OOM/不完整 warmup 无有效分数**。另有一次会话中断造成的 compress partial `.026`，单独保留但不冒充计划内 Run3。所有单项报告都不是完整套件 Composite；正式 Base 仍是独立的 `SPECjvm2008.007`、421.24 SPECjvm2008 Base ops/min。

## 结果总表

数值为三次有效运行的均值；括号内为样本 SD、CV。`0/3` 表示三次都真实运行但无有效正式分数，不能写为 0 ops/min。

| workload | 默认 | 512 MiB | 1024 MiB | 2560 MiB |
|---|---:|---:|---:|---:|
| compress | 517.567 (6.051, 1.169%) | 508.677 (0.855, 0.168%) | 516.047 (10.128, 1.963%) | 486.177 (8.405, 1.729%) |
| derby | 717.743 (32.816, 4.572%) | 0/3 有效，warmup OOM/Full GC thrash | 225.753 (9.225, 4.086%) | 738.560 (29.297, 3.967%) |
| sunflow | 312.263 (5.611, 1.797%) | 283.807 (4.700, 1.656%) | 304.783 (12.594, 4.132%) | 304.820 (4.067, 1.334%) |
| scimark.fft.large | 112.123 (5.712, 5.094%) | 0/3 有效，warmup OOM | 0/3 有效，warmup OOM | 113.783 (5.391, 4.738%) |

完整逐轮数据、GC 字段、命令、时间、有效性和路径见[`heap_parameter_results.csv`](heap_parameter_results.csv)，聚合值见[`heap_parameter_summary.csv`](heap_parameter_summary.csv)。

## 观察、机制与边界

- compress：512/1024 MiB 与默认较接近，2560 MiB 反而低 6.065%；四档整进程 GC 暂停均小于 2 秒。说明该 workload 在本条件下不是简单的堆容量受限，扩大堆没有普遍收益。
- derby：512 MiB 三次均失效；1024 MiB 能完成但平均 GC 暂停 260.711 秒、吞吐比默认低 68.547%；2560 MiB 比默认高 2.900%且暂停较少，但该差值小于两组约 4% 的 CV，不能声称稳定提升。
- sunflow：512 MiB 比默认低 9.113%，同时 GC 事件均值从 2437 增到 8128.667、暂停从 23.886 增到 49.434 秒；这与小堆下更高回收压力一致。2560 MiB GC 更少，却仍比默认低 2.384%，显示超过容量压力区后没有单调收益。
- FFT large：512/1024 MiB 都无法容纳 16 线程 warmup 工作集；默认实际 `MaxHeapSize` 约 1.84 GiB、2560 MiB 均可运行。两者吞吐仅差 +1.481%，低于约 5% CV，不能确认扩大后的性能收益。

参数到机制的证据链是：`-Xmx` 限制堆可扩展容量 → 影响自适应分代/GC 触发或能否容纳 live set → 对分配密集 workload 产生不同 GC/可运行性 → 吞吐变化。但 GC 日志覆盖整个 Java 进程而非只覆盖 240 秒 measurement；没有 live-set、分配剖析、硬件计数器、频率/温度和宿主负载时序，所以只报告关联和与机制一致的解释，不宣称单因果。

## 历史 `-Xmx2560m` 对照

2026-09-30 的历史 compress 单次结果是默认 `.013` 546.46、2560 MiB `.014` 536.04 ops/min（−1.907%）。本轮三次均值方向同样下降（517.567→486.177，−6.065%），因此**方向得到重复观察，幅度没有复现**。历史轮没有本轮统一的 GC 日志且是相邻顺序单次，不能并入 `n=3`、不能替代本轮 baseline，也不能证明长期稳定退化。

## 复现、图表与结论

从仓库根目录依次运行：

```powershell
pwsh -NoProfile -File homework02/scripts/jvm_parameter/run_optional.ps1
python homework02/scripts/jvm_parameter/build_optional_data.py
python homework02/scripts/jvm_parameter/plot_optional.py
python homework02/scripts/jvm_parameter/build_optional_data.py --check
python homework02/scripts/jvm_parameter/plot_optional.py --check
python homework02/scripts/jvm_parameter/verify_optional.py
```

三张图分别是[分数](../../images/jvm_parameter/heap_vs_score.png)、[GC 暂停](../../images/jvm_parameter/heap_vs_gc_time.png)、[相对默认变化](../../images/jvm_parameter/heap_vs_score_change.png)。实验的主要结论不是“越大越快”，而是：`-Xmx` 在低于 workload 容量门槛时会导致严重 GC 或无法运行；越过门槛后，继续扩大堆的收益依 workload 而异，并可能饱和、落入自然波动，甚至伴随较低吞吐。
