# SPECjvm2008 官方资料整理

查阅日期：2026-09-30。主要依据为 SPEC 官方 [User’s Guide](https://www.spec.org/jvm2008/docs/UserGuide.html)、[Run and Reporting Rules](https://www.spec.org/jvm2008/docs/RunRules.html)、[Known Issues](https://www.spec.org/jvm2008/docs/KnownIssues.html) 和 [FAQ](https://www.spec.org/jvm2008/docs/FAQ.html)。具体 workload 以 [官方 benchmark 说明](https://www.spec.org/jvm2008/docs/benchmarks/) 为准。

## SPEC 与标准基准测试

SPEC（Standard Performance Evaluation Corporation）是制定和维护计算系统标准性能测试的非营利组织。统一的 workload、计分方法、有效性检查和披露规则，使不同机器或软件配置的成绩有可复查的共同基准；这比各自选择有利程序、只报告最好的运行片段更适合比较。标准成绩仍需要结合测试环境解读，不能代表所有真实业务。来源：[SPEC 组织介绍](https://www.spec.org/spec/spec.html)、[Run Rules](https://www.spec.org/jvm2008/docs/RunRules.html)。

## SPECjvm2008 测量什么

SPECjvm2008 主要测量 Java 运行环境（JVM 与类库）执行单个应用时的性能，同时受 CPU、内存系统与操作系统影响。它覆盖编译、压缩、密码学、嵌入式数据库、音频处理、科学计算、对象序列化、图形渲染、XML 处理以及启动性能。官方指出该套件对文件 I/O 的依赖较小，不包含远程网络 I/O，因此不能把它的成绩当作磁盘、网络或完整 Java EE 服务吞吐量。来源：[User’s Guide §1.2–1.3](https://www.spec.org/jvm2008/docs/UserGuide.html)、[FAQ Q1.1/Q1.6](https://www.spec.org/jvm2008/docs/FAQ.html)。

多数吞吐测试使用多个 benchmark 线程，默认数量由 JVM 看到的逻辑 CPU 数决定。一次 operation 是 workload 的一份固定工作；预热默认 120 秒、正式迭代默认 240 秒。预热不计入正式成绩。每项的 `ops/m` 是该项每分钟完成的 operation 数；不同 workload 的 operation 工作量不同，不能直接凭两个 `ops/m` 数字判断哪个算法“更快”。套件先对同类子项目求几何平均，再对各组求综合几何平均，减少某一组子项目过多而主导总分的情况。来源：[User’s Guide §1.5–1.8、§6](https://www.spec.org/jvm2008/docs/UserGuide.html)。

更精确地说，harness 在一次迭代中反复触发各 benchmark 的固定工作单元，结束后用 `operations × 60000 / 实际耗时毫秒` 算该项吞吐。官方规定的是迭代**至少**运行指定时间、等一个已开始的 operation 完成，所以不能假设每次真实耗时都恰好 240 秒；本机 `.007` raw 的 21 个吞吐项实际记录均为 120000 ms 预热、240000 ms 测量。[启动项](https://www.spec.org/jvm2008/docs/UserGuide.html)例外：它们为每个 workload 起一个新 JVM 完成一次 operation，不使用吞吐项的长时预热。几何平均是先在 `compiler`、`crypto`、`xml`、`startup`、SciMark 等组内计算，再以 11 组得分求综合分；`scimark.monte_carlo` 只运行一次，但在本机 raw 重算 `scimark.small` 和 `scimark.large` 组时都必须计入，否则无法复现官方 reporter 的两组分数。可复算的 [组分数 CSV](base_result_table.csv) 和 [解析脚本](../scripts/analysis/build_core_data.py) 是本实验的计算证据，而非另造的测试成绩。

## 主要 workload 与性能敏感点

下表中的“可能影响因素”是根据官方描述作出的机制推断，具体瓶颈需借助分析器或系统计数器验证。

| Workload | 官方描述的测试内容 | 主要计算特点与可能影响因素 |
|---|---|---|
| `compiler.compiler` / `compiler.sunflow` | 用套件内的旧版 OpenJDK `javac` 前端编译 javac 或 Sunflow 源码；自有 FileManager 使文件系统影响较小。 | 语法/类型分析、对象分配、缓存与 GC；多线程并发还受 CPU 核心和内存带宽影响。[来源](https://www.spec.org/jvm2008/docs/benchmarks/compiler.html) |
| `compress` | 对真实文件数据执行改进的 LZW 压缩。 | 字典查询、分支、整数运算和数据访问局部性；主要不是测磁盘吞吐。[来源](https://www.spec.org/jvm2008/docs/benchmarks/compress.html) |
| `crypto.aes` / `crypto.rsa` / `crypto.signverify` | 调用运行环境中的加密、解密、签名与验签实现，输入大小和协议各异；`crypto.aes` 名称下还包含 DES/CBC 路径，并非纯 AES 微基准。 | 算法与 JCE Provider 实现、整数/位运算、CPU 指令支持、JIT 优化；各子项 operation 不同。[来源](https://www.spec.org/jvm2008/docs/benchmarks/crypto.html) |
| `derby` | Java 嵌入式数据库业务逻辑，着重 `BigDecimal` 计算与锁行为。 | 对象分配、并发锁竞争、GC、数据库逻辑；真实数据库初始化会使用本地存储，但成绩不能简单解释为磁盘 I/O 速度。[来源](https://www.spec.org/jvm2008/docs/benchmarks/derby.html) |
| `mpegaudio` | 基于 JLayer 对 MP3 数据解码。 | 官方描述为浮点负载较重；解码循环、数组访问与 JIT/类库实现可能起作用，不能据此断言浮点单元已饱和。[来源](https://www.spec.org/jvm2008/docs/benchmarks/mpegaudio.html) |
| `serial` | 序列化/反序列化原语及对象，以同机 socket 传递生产者—消费者数据。 | 对象图遍历、`Object.equals()`、分配和同步/缓冲路径可能参与；同机 socket 不等于远程网络吞吐测试。[来源](https://www.spec.org/jvm2008/docs/benchmarks/serial.html) |
| `sunflow` | 多线程全局光照图像渲染。 | 浮点计算、渲染任务并发和内存访问；官方要求合规运行中每个 Sunflow 实例的内部线程数为 4。[来源](https://www.spec.org/jvm2008/docs/benchmarks/sunflow.html) |
| `mpegaudio` | 使用 JLayer 对 MP3 音频解码。 | 官方称其浮点运算较重；还可能涉及数据流处理、JIT 热循环与缓存，但瓶颈需测量。[来源](https://www.spec.org/jvm2008/docs/benchmarks/mpegaudio.html) |
| `scimark.*` | FFT、LU、SOR、稀疏矩阵及 Monte Carlo 浮点计算。 | small 数据集约 512 KiB，着重缓存内计算/JIT；large 约 32 MiB，更受内存层次与带宽影响。[来源](https://www.spec.org/jvm2008/docs/benchmarks/scimark.html) |
| `serial` | 将基本类型和对象序列化、通过本机 socket 传给消费者再反序列化，包含大量 `Object.equals()`。 | 对象图遍历、分配/GC、锁与本机通信可能参与；此处不是远程网络吞吐测试。[来源](https://www.spec.org/jvm2008/docs/benchmarks/serial.html) |
| `xml.transform` / `xml.validation` | 分别执行 XSLT 变换与 XML Schema 校验，调用 JRE XML API。 | 解析与对象构造、树/流式处理、类库实现和 GC；正式测量包含多种输入和访问方式。[来源](https://www.spec.org/jvm2008/docs/benchmarks/xml.html) |
| `startup.*` | 为各 workload 启动新的 JVM 并完成一次 operation。 | JVM 启动、类加载、解释/JIT 初始阶段与 OS 进程创建；与长时间吞吐测量的性能含义不同。[来源](https://www.spec.org/jvm2008/docs/UserGuide.html) |

## 为什么覆盖这些类别

此套件的目标不是模拟一套单一业务，而是给同一个 JRE 一组有共同运行与校验规则、但资源压力互补的 Java 工作：`compiler` 的语法/类型分析会动用对象图和类库；`compress` 的字典访问、`crypto` 的 Provider/位运算、`derby` 的十进制与并发逻辑、`mpegaudio` 的解码计算、`serial` 的对象重建与本机通信、`sunflow` 的并行浮点渲染、`xml` 的解析/变换、`scimark` 的数值数组，以及 `startup` 的冷启动路径，分别可能触及 JIT、GC、缓存、内存层次、同步、类加载和类库实现。它们不是互斥的“纯 CPU”或“纯内存”标签；一项往往同时受几个系统层影响。该设计使单一算法的偶然优势不至于代表整个 Java 环境，但也不能把综合分直接外推为真实应用 SLA。依据：[官方 workload 总览](https://www.spec.org/jvm2008/docs/UserGuide.html)、[各 benchmark 说明](https://www.spec.org/jvm2008/docs/benchmarks/)。

这些类别是覆盖面设计，不是“每项只测一个硬件部件”的隔离测试。例如 `derby` 同时经过 CPU、锁、内存与 Java 类库；`crypto` 受 Provider 和算法实现影响；`startup` 则把 JVM 初始化与 OS 创建进程的成本放进得分。对某个系统瓶颈的断言，必须另外有控制变量或计数器证据。

## 从 operation 到综合分：分母必须一致

一次 **operation** 是该子基准规定的一次固定任务，并非通用“指令”或相同字节量。吞吐项目通常在 120 秒 **warmup** 后执行一次 240 秒 **measured iteration**，记录完成 operation 数，再按实测毫秒数换算为 `operations × 60000 / duration_ms`，单位 **ops/min**；warmup 不计入最终成绩。`startup.*` 使用新进程完成一次工作，反映启动路径，与长时间、多线程的吞吐项不同。官方 [User's Guide §5–6](https://www.spec.org/jvm2008/docs/UserGuide.html) 给出记录与组合方法，[Run Rules §2.3](https://www.spec.org/jvm2008/docs/RunRules.html) 给出正式运行的时长、完整顺序及正确性条件。

`compiler.compiler`、`compiler.sunflow` 等先在组内求几何平均；完整 Base 再对 **11 个组** 求几何平均。几何平均让相对变化在乘法尺度上汇总，也避免组内子项多的 `startup` 仅凭数量占据大部分总分。这个权重设计不是“所有程序的总吞吐量”，也不能把 `derby 820.63` 与 `sunflow 350.25` 相除得到数据库相对渲染的速度。只有同名、同定义的 workload 在不同配置下，ops/min 才有直接解释性比较；即便如此，跨系统仍不是受控因果实验。

## Base 与 Peak

| 项目 | Base | Peak |
|---|---|---|
| 目标 | 反映 JVM 默认配置的开箱性能，便于公平复查 | 反映经过允许调优后的系统性能上限 |
| JVM 手工调优 | 不允许 | 允许，但须披露配置 |
| 预热与正式迭代 | 120 秒和 240 秒，1 次正式迭代 | 预热可调整；正式迭代至少 240 秒 |
| Benchmark 线程数 | 可配置，需披露 | 可配置，需披露 |
| 合规成绩 | 必须包含完整 Base 套件，正确性与校验通过 | 可选；需满足 Peak 规则 |

来源：[User’s Guide §1.4、§5.1](https://www.spec.org/jvm2008/docs/UserGuide.html)、[Run Rules §1.4、§2.3–2.4](https://www.spec.org/jvm2008/docs/RunRules.html)。本实验正式命令中的 `-bt 16` 只改变允许配置的 benchmark 线程数，仍使用完整 Base 顺序与默认时长；SPEC 生成的正式文本报告标明 `Run is compliant`。单项重复实验和 JVM 参数实验不构成另一份完整合规 Base 成绩。

Base/Peak 的区分使读者知道自己在比较什么：Base 偏向不手工调 JVM 的默认式配置，固定预热、测量及完整顺序并披露硬件/OS/软件；Peak 才允许在规则内调整并披露 JVM 选项、预热等，以考察调优后的能力。这不是说 Base 完全不允许控制实验条件：官方允许配置 benchmark 线程，也允许 OS/硬件调节；但不能悄悄改 properties、删掉不利 workload 或修改 measured iteration。课程只要求 Base，因此 `.007` 不与任何选做 JVM 参数结果混成一个“优化后 Base”，也没有运行 Peak。[User’s Guide §1.4](https://www.spec.org/jvm2008/docs/UserGuide.html)、[Run Rules](https://www.spec.org/jvm2008/docs/RunRules.html)。

Base/Peak 双轨并非宣称 Base 在各平台上必然公平到可直接归因硬件：Base 限制 JVM 手工调优，重视默认式部署、可复查与披露；Peak 允许记录过的针对性 JVM 设置和更长预热/测量，关注调优后表现。无论哪类，正确性、套件版本、完整顺序、计时和系统披露仍需遵循规则。这里选择 Base，是为了让课程主结果保留统一的完整套件与可解释配置；单项重复用于研究波动，不能改称另一份合规 Base。`-bt 16` 解决当时 WSL 内存不足造成的 OOM，并不是调优竞赛，也未证明比其他线程数快。[Run Rules §1.4、§2.3](https://www.spec.org/jvm2008/docs/RunRules.html)

## 官方已知问题与本实验对应

- **JDK 版本：** 套件内旧版 javac 不支持 Java SE 8+ 类库字节码，四个 compiler 项可能失败。课程 PDF 推荐先尝试 8u41 RI；本实验实测完整 Base 在其 compiler 阶段无法完成，因此改用独立的 Java 7u75 RI。来源：[Known Issues §8](https://www.spec.org/jvm2008/docs/KnownIssues.html)、[FAQ Q4.8](https://www.spec.org/jvm2008/docs/FAQ.html)。
- **堆内存：** workload 活数据量随 benchmark 线程数增加。默认 32 线程在本机 `scimark.fft.large` OOM；依官方建议减至 16 线程后完整 Base 通过。来源：[Known Issues §1](https://www.spec.org/jvm2008/docs/KnownIssues.html)。
- **结果判定：** 正确性、kit 校验和、完整顺序、时长等是合规条件；有效的单项成绩与完整套件的合规 Base 综合分须分别标注。来源：[Run Rules §2.3](https://www.spec.org/jvm2008/docs/RunRules.html)、[FAQ Q2.1](https://www.spec.org/jvm2008/docs/FAQ.html)。
