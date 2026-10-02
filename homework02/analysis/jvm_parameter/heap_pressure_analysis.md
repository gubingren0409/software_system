# `-Xmx`、堆压力、GC 与吞吐

## 数据口径

本分析只使用已保存的 48 个计划尝试，不新增 benchmark 运行。逐事件数据来自 Java 7 `PrintGCDetails` 日志，经[`build_enhancement_data.py`](../../scripts/jvm_parameter/build_enhancement_data.py)生成[`gc_memory_behavior.csv`](gc_memory_behavior.csv)。`before_used_mib`/`after_used_mib` 是总堆 GC 前后用量；`logged_capacity_mib` 是该事件日志元组中的容量。HotSpot 7 可在 Full GC 时调整 committed capacity，因此 GC 前用量不能一律除以同一行的、可能已调整后的容量；本文改用每轮实际 `MaxHeapSize` 计算 `before_max_heap_percent`，只把 `after_logged_capacity_percent` 当事件结束后的占用参考。

正式阶段的 GC 是估计值：SPEC raw 给出毫秒级 warmup/measurement 边界，GC 日志给出 JVM uptime，而 raw 的 run date 只有秒级。解析器以 raw run date 加 uptime 对齐，保守设置 ±1 秒不确定区；落在边界附近的事件标为 `boundary_uncertain` 并排除。完整边界见[`gc_phase_boundaries.csv`](gc_phase_boundaries.csv)，聚合见[`gc_measurement_summary.csv`](gc_measurement_summary.csv)。这比整进程统计更接近 measurement，但不是同步时钟跟踪。

## Derby：从失败、GC thrash 到恢复

**观察。** 512 MiB 三轮均在不完整 warmup 中 OOM，持续 901–956 秒；每轮有 12,191–13,167 次 GC，其中 12,133–13,111 次为 Full GC，累计暂停 789.865–842.018 秒。因为没有进入完整正式阶段，不能计算正式分数或 measurement 指标。

1024 MiB 三轮都完成，但正式均值只有 **225.753 ops/min**，相对默认 **−68.547%**。估计 measurement 内每轮平均 **1,861.667 次 GC，全部为 Full GC**，暂停 **164.417 秒**；GC 前用量平均为最大堆的 **94.030%**，GC 后仍为 **71.388%**。这条链支持更具体的表述：在本执行条件下，1 GiB 虽足以避免 OOM，却使 Derby 长时间停留在高占用、几乎连续 Full GC 的区域，回收后仍保留很大的存活集合，与吞吐严重下降一致。

默认实际 `MaxHeapSize=1,977,614,336` bytes（约 1.842 GiB），正式均值 **717.743 ops/min**；估计 measurement 中 **2,202 次 GC、0 次 Full GC、13.580 秒暂停**，GC 前/后最大堆占比分别为 **73.960%/40.882%**。2560 MiB 为 **738.560 ops/min**，估计 measurement 中 **1,667 次 GC、0 次 Full GC、10.484 秒暂停**，GC 前/后占比 **63.518%/30.389%**。因此 2560 MiB 相比 1024 MiB 的恢复同时有吞吐、Full GC 和占用证据；但相比默认仅 **+2.900%**，小于两组各约 4% 的 CV，不能称为稳定性能提升。

## SciMark FFT large：容量门槛而非渐进变慢

**观察。** 512 MiB 三轮均在 63–64 秒 OOM，每轮 121 次 GC、60 次 Full GC；1024 MiB 三轮在 69–71 秒 OOM，记录 68–75 次 GC、33–36 次 Full GC。它们发生在 warmup 未完成之前，不能生成 measurement 统计。外层退出码仍可能为 0，因此 OOM/raw 完整性检查比退出码更重要。

默认实际最大堆约 1.842 GiB 与 2560 MiB 均可完成：正式均值分别 **112.123** 和 **113.783 ops/min**。估计 measurement 中，两组 GC 暂停分别为 **2.838** 与 **2.529 秒**；分数差 **+1.481%**，而 CV 分别为 **5.094%** 与 **4.738%**。证据说明 16 线程 FFT large 在本环境存在高于 1 GiB、低于约 1.84 GiB 的可运行容量门槛；越过门槛后，当前 `n=3` 没有证明 2560 MiB 更快。

## Sunflow：GC 压力下降，吞吐收益饱和

512 MiB 的正式均值 **283.807 ops/min**，相对默认 **−9.113%**。估计 measurement GC 从默认每轮 **1,567.667** 增至 **5,251.667** 次，暂停从 **15.159** 增至 **31.935 秒**，GC 前最大堆占比从 **40.940%** 增至 **57.599%**。这与小堆增加回收压力并损害吞吐一致。

增加到 2560 MiB 后，估计 measurement GC 降到 **1,132.667** 次、暂停 **12.163 秒**，但分数 **304.820 ops/min** 仍比默认低 **2.384%**。该差异与默认/2560 MiB 的 CV（1.797%/1.334%）同一量级，且没有同步 JIT、硬件计数器和调度数据；可得结论是“GC 压力继续下降但吞吐没有单调上升”，而不是“较大堆导致下降”。

## Compress：低 GC 开销下的非单调结果

四档都有效。估计 measurement 暂停依次为 **0.544/0.925/0.644/0.558 秒**；2560 MiB 的 GC 次数约 **107.333**，与默认 **107.000** 接近，暂停也接近，但分数从 **517.567** 降到 **486.177 ops/min（−6.065%）**。因此 GC 次数或暂停不足以解释该差异。

可能但未经验证的解释包括：自适应分代尺寸改变对象布局与缓存局部性、JIT 编译时序差异、OS/WSL 调度、动态频率与后台负载。实验没有同步分配剖析、JIT 日志、cache miss、频率或负载序列，不能从现有证据选择其中任何一个原因。观察只支持：在本样本中，扩大最大堆没有给 compress 带来单调收益；−6.065% 高于各组约 0.17%–1.96% 的组内 CV，值得后续受控复验，但 `n=3` 仍不足以给出普遍因果结论。

## 综合结论

证据链现在是：实际 `MaxHeapSize` → GC 前后堆用量/最大堆压力 → measurement 估计内的 GC 类型、频率和暂停 → 同 workload 吞吐。它清楚区分了三种区域：容量不足时 OOM 或 Full GC thrash；越过容量门槛后性能恢复；继续增大堆时收益依 workload 饱和或消失。结论仍是 **`-Xmx` 的效果取决于 workload**，不是“更大的堆一定更快”。
