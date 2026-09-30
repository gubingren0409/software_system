# 正式 Base 的六项 workload 深度分析

下表只使用完整、合规的 `SPECjvm2008.007`，不掺入单项重复或诊断成绩。数值由 [`.007.raw`](../specjvm2008/results/SPECjvm2008.007/SPECjvm2008.007.raw) 自动解析，并逐项对照 [SPEC 文本报告](../specjvm2008/results/SPECjvm2008.007/SPECjvm2008.007.txt)；全部 38 项的工作表及计算字段见 [workload_measurements.csv](workload_measurements.csv)，复算方法见 [build_core_data.py](../scripts/analysis/build_core_data.py)。这六项都是 16 benchmark 线程的吞吐项，预热 120 s、正式迭代 240 s；`startup.*` 属另一种单 JVM 冷启动测量，不与此处混列。百分比是 `(正式 − 预热) / 预热 × 100`，不是跨机器加速比。

| Workload | 预热 ops/m | 正式 ops/m | Δ ops/m | Δ % | 固定工作与主要计算路径 |
|---|---:|---:|---:|---:|---|
| `compress` | 550.85 | 551.55 | +0.70 | +0.13% | LZW 类压缩的字典查询、编码、整数/分支与数据访问。[SPEC 说明](https://www.spec.org/jvm2008/docs/benchmarks/compress.html) |
| `derby` | 806.63 | 820.63 | +14.00 | +1.74% | 嵌入式数据库业务、`BigDecimal` 及并发锁路径。[SPEC 说明](https://www.spec.org/jvm2008/docs/benchmarks/derby.html) |
| `sunflow` | 345.02 | 350.25 | +5.23 | +1.52% | 多线程全局光照渲染；大量浮点几何/光照计算与任务协作。[SPEC 说明](https://www.spec.org/jvm2008/docs/benchmarks/sunflow.html) |
| `crypto.aes` | 205.42 | 206.89 | +1.47 | +0.72% | 名称虽为 aes，官方说明包含 AES **及 DES** 的 CBC 模式加/解密（100 B、713 kB 输入）；Provider 与实现路径进入工作负载。[SPEC 说明](https://www.spec.org/jvm2008/docs/benchmarks/crypto.html) |
| `scimark.fft.small` | 694.50 | 709.00 | +14.50 | +2.09% | 小数据集 FFT 浮点计算；套件 small 数据集标称约 512 KiB。[SPEC 说明](https://www.spec.org/jvm2008/docs/benchmarks/scimark.html) |
| `scimark.fft.large` | 108.52 | 100.11 | −8.41 | −7.75% | 大数据集 FFT 浮点计算；套件 large 数据集标称约 32 MiB。[SPEC 说明](https://www.spec.org/jvm2008/docs/benchmarks/scimark.html) |

## 逐项解释：观察与推断分开

`compress`：本次预热与正式值仅差 +0.13%，表明这一次的两个阶段吞吐接近。字典访问的局部性、分支预测、整数计算以及分配/GC 都可能参与；这不是“证明 JIT 已完全稳定”，也不能由接近 0 的阶段差推出无 GC。[原始三次重复](repeat_test_analysis.md)中同一项依然出现 557.34、545.48、522.15 ops/m，说明单次阶段稳定与跨进程稳定不是一回事。

`derby`：+1.74% 是观测到的阶段变化。数据库对象、十进制运算及同步可能使其对线程数、内存分配和锁竞争敏感；多线程负载下 JIT 热点编译也可改变性能。但没有锁等待、分配速率、GC 或数据库 I/O 计数器，不能把这 14.00 ops/m 具体归因于某一项。SPEC 设计对文件 I/O 依赖较小，不能把 `derby` 直接当磁盘基准。[User’s Guide §1.2](https://www.spec.org/jvm2008/docs/UserGuide.html)

`sunflow`：+1.52% 与浮点渲染热点在预热后继续优化、缓存/线程状态改变均相容。Sunflow 内部有任务并行，SPEC 对每个实例的线程有约束，因此外层 16 个 benchmark 线程不等于整个进程只有 16 条线程。正式 `.007` 没有每核利用率或调度/等待证据，不可声称 CPU 浮点单元是唯一瓶颈，也不可把该项 350.25 与 Derby 820.63 直接当程序速度比。

`crypto.aes`：+0.72% 很小。其工作含不同大小的分组密码输入，处理量随块数增长；可能涉及 JIT、Provider 类初始化、CPU 指令支持和缓冲区访问。本实验未记录 Java 7 的实际 JCE Provider 选择、AES 硬件指令调用或性能计数，因此不能宣称 AES-NI 已被使用，尤其不能把 AES/DES 混合 workload 当成单一 AES 核心。它只是 `crypto` 组的一个子项；正式组分 676.52 由 `crypto.aes`、`crypto.rsa`、`crypto.signverify` 共同取几何平均，不得用 206.89 冒充 crypto 组分。[组分表](base_result_table.csv)

`scimark.fft.small` 与 `scimark.fft.large`：SPEC 的设计意图是 small 更接近缓存内的 JVM/算术路径，large 超出通常 L2、增加内存层次压力。[SciMark 官方说明](https://www.spec.org/jvm2008/docs/benchmarks/scimark.html) 本机观察到小项 709.00、大项 100.11 ops/m，且大项从预热到正式下降 −7.75%，小项上升 +2.09%。FFT 的蝶形计算兼具浮点运算与跨位置数据访问；工作集变大可能降低局部性、增加缓存缺失/内存流量，进而改变有效吞吐，也可能受 GC、调度、频率和计时阶段状态影响。不过 small 与 large 的**一次 operation 工作量定义不同**，`709 / 100.11 ≈ 7.08` 绝非“内存慢 7.08 倍”或缓存 miss 惩罚。大项的阶段下降也只是一个样本，未能归因。

## 横向比较能回答什么，不能回答什么

算法层面也不能用一个 Big-O 标签解释实测得分：FFT 的标准蝶形运算随数据点数约为 `O(N log N)`，但 small/large 的工作单元规模不同；LZW 压缩需要逐步查找/更新字典，访问模式取决于输入数据；分组密码处理量随块数增长，但具体吞吐取决于 Provider；渲染取决于场景、光线与采样策略；Derby 的业务事务混合 `BigDecimal`、查询/更新及锁路径，没有一个能代表整个 operation 的单一复杂度。上述性质解释了为何它们会对 CPU、缓存、内存和同步产生不同压力，不是根据本机单次分数反推出的瓶颈。文件输入或本机通信的存在也不等于此套件可作磁盘/网络基准。[SPEC workload 说明](https://www.spec.org/jvm2008/docs/benchmarks/)

不同 benchmark 的 operation 并不等量，`derby > sunflow > crypto.aes` 这种数值排序首先是各自固定工作单元的计数尺度，不是算法或硬件的快慢排名。同名 workload 在**相同**定义下跨运行比较才更直接；跨系统还需披露 JDK、OS、硬件与 benchmark 线程的差异。正式 Base 的 11 个组分、综合几何平均和 SciMark Monte Carlo 双组归属在 [背景方法说明](specjvm_background.md) 与 [结果总表](base_result_table.csv)中解释。

本次正式运行没有采集 GC 事件、硬件 cycles/instructions/cache misses、锁争用或功耗/频率轨迹。[新编号的轻量 profiling](diagnostics/profile_analysis.md) 独立记录了 `compress`、`sunflow` 的整进程 RSS/上下文切换及 WSL2 计数器局限，不能倒推 `.007` 当时确切瓶颈。这里所有“可能”“相容”均是基于官方 workload 定义的机制假设，而非受控因果结论。
