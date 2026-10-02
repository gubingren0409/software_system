# `-Xmx` 选做实验增强前审计

审计基线为 Git commit `b7fcd1f0ac03cb013439644e81c3e78875fdb396`。本审计先检查现有 48 个计划单元、49 份元数据（含计划外中断 `.026`）、48 份计划内 GC 日志、SPEC raw/TXT、控制台日志与解析/绘图/验证脚本，再决定是否需要新 benchmark。审计期间未修改 `SPECjvm2008.007`，其 raw SHA-256 仍为 `4ae651e312061d09760743ab9908129b633e9ce1e5b5b296c13d4a30605e05ad`。

## 1. 已有证据强支持的结论

1. **实验矩阵完整且有效性分类可复算。** 四个 workload × 四档堆 × 三次独立 JVM 共 48 次均有唯一 Result ID、命令、时间、raw/TXT、控制台、GC 和元数据。现有 verifier 从源文件确认 39 个有效正式分数、9 个 invalid；`.026` 是额外中断证据，不计入矩阵。
2. **`-Xmx` 实际改变了最大堆。** 各轮运行前日志中的 `PrintFlagsFinal` 给出一致的 `MaxHeapSize`：默认 1,977,614,336 B，512 MiB 为 536,870,912 B，1024 MiB 为 1,073,741,824 B，2560 MiB 为 2,684,354,560 B。它不是根据参数名推测的。
3. **效果依 workload 而异，不是单调“越大越快”。** compress 的 2560 MiB 均值比默认低 6.065%；sunflow 的 512 MiB 低 9.113%，但 2560 MiB 仍未超过默认；derby 的 512 MiB 三次失败、1024 MiB 严重降速、2560 MiB 与默认接近；FFT large 的 512/1024 MiB 三次均失败，而默认和 2560 MiB 接近。
4. **存在可重复的容量失效区。** derby/512 MiB 三次均出现 OOM 和持续 Full GC；FFT large 的 512/1024 MiB 各三次都在 warmup 内 OOM。失败分数为空而非零，且外层退出码为零的 SciMark 失败仍被 raw/TXT/OOM 联合判为 invalid。
5. **whole-process GC 压力与部分吞吐差异同步变化。** derby/1024 MiB 的有效进程平均 GC 暂停 260.711 s、吞吐比默认低 68.547%；sunflow/512 MiB 的 GC 事件和暂停显著高于默认且吞吐低 9.113%。反例同样有证据：compress/2560 MiB 暂停更少但吞吐更低，说明 GC 不是唯一决定因素。
6. **小幅正差不能声称优化成功。** derby/2560 MiB 相对默认 +2.900%，而两组 CV 约 4%；FFT/2560 MiB +1.481%，两组 CV 约 5%。这些差异处在已观察的运行波动量级。

## 2. 目前只能作为假说的结论

1. **compress/2560 MiB 下降的原因。** 更大的自适应堆布局、缓存/局部性、JIT 时序、调度或频率变化都可能参与，但现有日志没有硬件计数器、JIT 编译时间线、频率/温度或宿主负载序列，不能选定单一原因。
2. **GC 对 sunflow 全部分差的因果贡献。** 512 MiB 同时有更多 GC 和较低吞吐，与 GC 压力机制一致；但 whole-process GC 混合了 check、warmup、measurement 和报告阶段，尚不能把全部 9.113% 分差归因于 measured-phase GC。
3. **derby/1024 MiB 的对象存活机制。** 大量 Full GC 与低吞吐表明高堆压力，但没有对象年龄、live-set 分类、heap dump 或分配剖析，不能断言是哪类 Derby 对象造成保留。
4. **2560 MiB 的“饱和点”。** 当前四档只能说明在已测点上收益不单调；没有足够密集的中间容量点建立精确阈值或响应曲线，也没有必要为本增强任务盲目增加配置。
5. **跨机器/JDK 的普遍性。** 结果只适用于这台 WSL2 机器、Java 7u75 RI、Parallel GC、16 benchmark 线程与当时宿主状态。

## 3. 缺失证据与可由现有材料补足的部分

| 缺口 | 现有材料 | 增强方法 | 是否需要新 benchmark |
|---|---|---|---|
| GC 前后堆压力 | `gc_events.csv` 已有每事件 `heap_before_kib`、`heap_after_kib`、`heap_capacity_kib`，运行表有实际 `MaxHeapSize` | 派生 MiB 与相对实际最大堆的前/后占比；因 Full GC 可调整 committed capacity，只计算事件后的 `after/logged_capacity`，保留事件级平表 | 否 |
| measurement 阶段 GC | raw 对有效轮提供 warmup/measurement 的 epoch 毫秒边界；GC 日志提供 JVM uptime | 用 run start 秒估算事件 wall time并分阶段；边界附近标记不确定，不伪称精确同步 | 否 |
| 四档完整 JVM flags | 轮次日志只有 `MaxHeapSize`；环境日志只有默认档部分 flags | 用同一 Java 7 RI 对四档执行非 benchmark 的 `-XX:+PrintFlagsFinal -version`，保存命令输出与结构化 CSV | 否 |
| GC frequency 图 | 最终 summary 已有有效轮平均 GC count | 由 CSV 生成第四张图并标注 `n=0` | 否 |
| Derby 深入案例 | 现有三档有效分数、GC/Full GC、暂停和 512 MiB 失败日志 | 合并分数、measurement 估算与利用率分布，明确观察/解释/限制 | 否 |
| allocation rate | 现有 Java 7 GC 日志没有 TLAB/分配 profiler 数据 | 只能用 GC 间占用变化作压力观察，不能称为真实 allocation rate | 否；新增运行也需改变采集协议，不能与正式 optional 矩阵混合 |

## 审计决定

不重跑 48 次，也不新增 benchmark 配置。现有证据足以完成 heap occupancy、measurement-window 估算、GC frequency 和 Derby case study；新增运行不会解决主要缺口，反而会把不同采集协议的数据混入正式 optional 矩阵。唯一新增执行是同一 Java 7 RI 的四档 `PrintFlagsFinal -version` 配置快照，它不运行 SPEC、不产生分数，并单独标记为诊断证据。
