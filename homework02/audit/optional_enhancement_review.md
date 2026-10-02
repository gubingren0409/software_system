# JVM 参数增强实验四项复审

复审范围：在既有 48 次 `-Xmx` 计划尝试上新增的堆占用、measurement 阶段估计、JVM flag 快照、Derby 个案、图表和 README 整合。正式 Base `.007` 只做哈希核验，不属于增强数据。

## Review A：Experimental validity

- `SPECjvm2008.007.raw` 仍为 SHA-256 `4ae651e312061d09760743ab9908129b633e9ce1e5b5b296c13d4a30605e05ad`；增强脚本不写 `results/`。
- 没有新增 SPEC benchmark 运行；四次新执行仅为同一 Java 7 的 `-XX:+PrintFlagsFinal -version`，日志没有 `SPECjvm2008.jar`。
- 48 个 optional 尝试仍为 39 个有效、9 个失败；失败分数为空，未把单项分数或诊断快照混成 Base Composite。
- measurement 阶段对齐只用于完整有效 raw；9 个不完整失败明确标为阶段不可用。±1 秒边界不确定事件被排除而不是强行分类。

结论：增强没有修改 `.007`、没有改变既有分数，也没有把诊断执行混入 optional 结果。

## Review B：JVM correctness

- 每轮 GC 前后数值来自总堆日志元组，实际最大堆来自旧运行日志保存的 `MaxHeapSize`；新增 flag 快照独立复核四档值。
- HotSpot 7 Full GC 可能调整 committed capacity，因此未把同一行的容量错误地当作 GC 前容量；GC 前压力按实际最大堆计算，事件后另保留 logged-capacity 比例。
- `PrintFlagsFinal` 证实 Parallel GC、Parallel Old GC、AdaptiveSizePolicy 以及 `NewRatio=2`、`SurvivorRatio=8`。快照采集晚于 benchmark，文档没有把它写成历史同步遥测。
- “allocation behavior”只通过 GC 前后用量与回收量间接讨论；没有伪称得到对象分配率、对象年龄或 live-set 身份。

结论：堆、GC 与分配压力的术语和计算口径符合现有证据，没有从日志推导不存在的遥测。

## Review C：Scientific writing

- 所有 workload 区分“观察”“与机制一致的解释”“未经验证的假设”。Compress 的 locality、JIT、调度等明确标为未验证。
- Derby/FFT 的失败用于容量门槛证据，不生成 0 分；有效运行才计算正式均值。
- 效应量与 CV 并列。Derby 2560 MiB 的 +2.900% 小于约 4% CV；FFT 的 +1.481% 小于约 5% CV，均未宣称显著提升。
- `n=3` 不计算置信区间或显著性检验；阶段对齐精度、GC 日志范围及缺失遥测均明确披露。

结论：观察不等同因果，小样本没有被包装成强统计证明。

## Review D：Report usefulness

- 证据链从原来的 `-Xmx → GC → score` 扩展为 `实际 MaxHeapSize → GC 前后堆压力 → measurement GC 类型/频率/暂停 → throughput`。
- Derby 个案将 512 MiB 的 OOM、1024 MiB 的 Full GC thrash、2560 MiB 的恢复放在同一表和 CSV 驱动图中，解释力明显强于只列分数。
- README optional 章节按 Motivation、Design、Results、Behavior、Case Study、Limitations、Conclusion 导航；必做 Base 结论保持不变。
- 两张新增图均由最终 CSV 生成，并有 `--check` 确认图像与源数据一致。

结论：增强直接回答“为什么同一 `-Xmx` 对 workload 影响不同”，已达到最终报告可用状态；剩余不足需要新的同步遥测实验，而不是继续解释现有数据。
