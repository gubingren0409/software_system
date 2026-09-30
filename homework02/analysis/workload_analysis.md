# SPECjvm2008 Workload 结果分析

数据来源：正式完整 Base 运行 `SPECjvm2008.007` 的 [原始结果](../specjvm2008/results/SPECjvm2008.007/SPECjvm2008.007.raw)、[文本报告](../specjvm2008/results/SPECjvm2008.007/SPECjvm2008.007.txt) 与 [完整日志](../logs/base_run.log)。测量环境为 OpenJDK 7u75 RI、16 benchmark 线程、120 秒预热、240 秒正式迭代。下面的性能因素是结合官方 workload 设计与观测结果的解释，未用性能计数器单独证明瓶颈。

| 项目 | 本次得分 (ops/m) | 正式迭代观察 | 主要资源与 JVM 因素 |
|---|---:|---|---|
| `compress` | 551.55 | 预热 550.85；正式 551.55，接近 | LZW 字典查询、数据局部性、分支和分配；JIT 稳定后吞吐接近预热值。[官方说明](https://www.spec.org/jvm2008/docs/benchmarks/compress.html) |
| `derby` | 820.63 | 预热 806.63；正式 820.63 | `BigDecimal`、数据库逻辑、对象分配和锁竞争；多线程下 CPU 与内存子系统共同作用。[官方说明](https://www.spec.org/jvm2008/docs/benchmarks/derby.html) |
| `sunflow` | 350.25 | 预热 345.02；正式 350.25 | 多线程全局光照渲染，浮点计算和任务协作较重；受核心并行度、缓存/内存及 JIT 编译影响。[官方说明](https://www.spec.org/jvm2008/docs/benchmarks/sunflow.html) |
| `crypto.aes` | 206.89 | 预热 205.42；正式 206.89 | 调用 JRE 密码学实现执行不同大小输入的对称加密；Provider、CPU 指令和内存访问均可能影响吞吐。[官方说明](https://www.spec.org/jvm2008/docs/benchmarks/crypto.html) |

不能把表中 `derby` 的 820.63 与 `sunflow` 的 350.25 解释为“数据库比渲染快 2.34 倍”。每个 benchmark 的一次 operation 定义和工作量不同；`ops/m` 在同一项目跨配置或重复运行时才有直接比较意义。SPEC 综合分使用分组几何平均，避免仅凭一个数值大的项目得出整体结论。[User’s Guide §6](https://www.spec.org/jvm2008/docs/UserGuide.html)

## 为什么特征不同

**CPU 计算与算法。** `sunflow` 的渲染涉及光照计算与并发任务；`crypto.aes` 执行密码学流程；`compress` 的 LZW 侧重查找和编码；`derby` 则混合数据库业务与十进制算术。各自一次 operation 的算法路径不同，原始得分大小首先反映了 SPEC 定义的工作单位，并非单一 CPU 快慢。

**内存访问与 JVM。** `compress` 的字典结构、`derby` 的数据库对象和 `BigDecimal`、`sunflow` 的渲染数据、`crypto.aes` 的输入缓冲区对缓存与分配/GC 有不同压力。JIT 对热点循环和虚调用的优化也不同。四项预热与正式值分别相差约 +0.13%、+1.74%、+1.52%、+0.72%；这是观测到的阶段差异，可以与 JIT/缓存稳定化相符，但单次运行不足以证明具体机制。

**I/O 边界。** SPEC 官方说明套件整体尽量降低文件 I/O 依赖、没有远程网络 I/O；因此 `derby` 项虽会有本地数据库准备，不能直接把 `derby` 成绩差异归因于磁盘速度。正式迭代的准确瓶颈仍需额外的 GC 日志、CPU 性能计数器或剖析器；本作业没有采集这些数据。[User’s Guide §1.2](https://www.spec.org/jvm2008/docs/UserGuide.html)

**大小数据集的旁证。** 同类 `scimark.fft.small` 为 709.00 ops/m，`scimark.fft.large` 为 100.11 ops/m；大小数据集的 operation 规模也不同，不能仅用 7.08 倍数字推算纯内存惩罚。官方设计说明 small 更接近缓存内计算，large 更强调内存系统，是两者性能特征的合理解释。[官方 SciMark 说明](https://www.spec.org/jvm2008/docs/benchmarks/scimark.html)

三次同项重复运行后的波动统计见 [重复实验分析](repeat_test_analysis.md) 和 [数据 CSV](repeat_test_results.csv)；本文件的主表只使用完整 Base 的正式数据。
