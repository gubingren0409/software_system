# 四项单项 workload 的选择理由

选择目标是让 `-Xmx` 在不同 Java 工作路径上可能产生可区分的响应；以下资源压力是**待检验的设计预期**，并非运行前已测出的瓶颈。全部在同一套件/JVM、`--base -bt 16`、默认 120/240 秒时长下分别运行，单项结果均不能称完整合规 Base。[SPEC benchmark 总览](https://www.spec.org/jvm2008/docs/benchmarks/)

| Workload | SPEC 官方描述与观察目标 | 与堆/GC 的待验证关系 | 特别边界 |
|---|---|---|---|
| `compress` | 改进 LZW 数据压缩；作为与旧 `.013/.014` 同名的基线项。[官方说明](https://www.spec.org/jvm2008/docs/benchmarks/compress.html) | 字典/缓冲区访问可能比大量短命对象更显著；检验 GC 事件是否确实相对少，而非直接预设“低分配”。 | 与旧样本跨时段、GC 记录选项不同；绝不合并均值。 |
| `derby` | 嵌入式数据库操作、`BigDecimal` 与锁行为。[官方说明](https://www.spec.org/jvm2008/docs/benchmarks/derby.html) | 对象分配/存活与并发同步可能让 GC 频次或暂停改变。 | 套件对磁盘 I/O 依赖较小；不能把分数称磁盘性能。 |
| `sunflow` | 多线程全局光照渲染，包含浮点几何计算与内部并行。[官方说明](https://www.spec.org/jvm2008/docs/benchmarks/sunflow.html) | 渲染对象/场景结构可能改变 live set 与收集行为，同时 CPU/调度也可能主导。 | 外层 `-bt 16` 不等于 Java 进程仅 16 条线程；GC 与分数的相关性不是单因果。 |
| `scimark.fft.large` | 大数据集 FFT，官方设计用于观察超出典型 L2 的内存层次影响。[官方说明](https://www.spec.org/jvm2008/docs/benchmarks/scimark.html) | 数组工作集可能使过小堆 OOM 或频繁 GC；较大堆也可能增加 RSS/系统压力。 | large 与 small 的一次 operation 不等量；无硬件 cache miss 时不能从分数推断内存惩罚。 |

四项覆盖压缩、数据库、并行渲染与数值数组，不意味着每项只测一个硬件部件。正式 `.007` 中对应分数只提供历史背景；本选做实验的新 48 次尝试将另编号并单独统计。若某堆配置失效，保留该单元的失败记录与失败比例，而不是换掉该 workload。
