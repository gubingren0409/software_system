# SPECjvm2008 官方资料整理

查阅日期：2026-09-30。主要依据为 SPEC 官方 [User’s Guide](https://www.spec.org/jvm2008/docs/UserGuide.html)、[Run and Reporting Rules](https://www.spec.org/jvm2008/docs/RunRules.html)、[Known Issues](https://www.spec.org/jvm2008/docs/KnownIssues.html) 和 [FAQ](https://www.spec.org/jvm2008/docs/FAQ.html)。具体 workload 以 [官方 benchmark 说明](https://www.spec.org/jvm2008/docs/benchmarks/) 为准。

## SPEC 与标准基准测试

SPEC（Standard Performance Evaluation Corporation）是制定和维护计算系统标准性能测试的非营利组织。统一的 workload、计分方法、有效性检查和披露规则，使不同机器或软件配置的成绩有可复查的共同基准；这比各自选择有利程序、只报告最好的运行片段更适合比较。标准成绩仍需要结合测试环境解读，不能代表所有真实业务。来源：[SPEC 组织介绍](https://www.spec.org/spec/spec.html)、[Run Rules](https://www.spec.org/jvm2008/docs/RunRules.html)。

## SPECjvm2008 测量什么

SPECjvm2008 主要测量 Java 运行环境（JVM 与类库）执行单个应用时的性能，同时受 CPU、内存系统与操作系统影响。它覆盖编译、压缩、密码学、嵌入式数据库、音频处理、科学计算、对象序列化、图形渲染、XML 处理以及启动性能。官方指出该套件对文件 I/O 的依赖较小，不包含远程网络 I/O，因此不能把它的成绩当作磁盘、网络或完整 Java EE 服务吞吐量。来源：[User’s Guide §1.2–1.3](https://www.spec.org/jvm2008/docs/UserGuide.html)、[FAQ Q1.1/Q1.6](https://www.spec.org/jvm2008/docs/FAQ.html)。

多数吞吐测试使用多个 benchmark 线程，默认数量由 JVM 看到的逻辑 CPU 数决定。一次 operation 是 workload 的一份固定工作；预热默认 120 秒、正式迭代默认 240 秒。预热不计入正式成绩。每项的 `ops/m` 是该项每分钟完成的 operation 数；不同 workload 的 operation 工作量不同，不能直接凭两个 `ops/m` 数字判断哪个算法“更快”。套件先对同类子项目求几何平均，再对各组求综合几何平均，减少某一组子项目过多而主导总分的情况。来源：[User’s Guide §1.5–1.8、§6](https://www.spec.org/jvm2008/docs/UserGuide.html)。

## 主要 workload 与性能敏感点

下表中的“可能影响因素”是根据官方描述作出的机制推断，具体瓶颈需借助分析器或系统计数器验证。

| Workload | 官方描述的测试内容 | 主要计算特点与可能影响因素 |
|---|---|---|
| `compiler.compiler` / `compiler.sunflow` | 用套件内的旧版 OpenJDK `javac` 前端编译 javac 或 Sunflow 源码；自有 FileManager 使文件系统影响较小。 | 语法/类型分析、对象分配、缓存与 GC；多线程并发还受 CPU 核心和内存带宽影响。[来源](https://www.spec.org/jvm2008/docs/benchmarks/compiler.html) |
| `compress` | 对真实文件数据执行改进的 LZW 压缩。 | 字典查询、分支、整数运算和数据访问局部性；主要不是测磁盘吞吐。[来源](https://www.spec.org/jvm2008/docs/benchmarks/compress.html) |
| `crypto.aes` / `crypto.rsa` / `crypto.signverify` | 调用运行环境中的加密、解密、签名与验签实现，输入大小和协议各异。 | 算法与 JCE Provider 实现、整数/位运算、CPU 指令支持、JIT 优化；各子项 operation 不同。[来源](https://www.spec.org/jvm2008/docs/benchmarks/crypto.html) |
| `derby` | Java 嵌入式数据库业务逻辑，着重 `BigDecimal` 计算与锁行为。 | 对象分配、并发锁竞争、GC、数据库逻辑；真实数据库初始化会使用本地存储，但成绩不能简单解释为磁盘 I/O 速度。[来源](https://www.spec.org/jvm2008/docs/benchmarks/derby.html) |
| `sunflow` | 多线程全局光照图像渲染。 | 浮点计算、渲染任务并发和内存访问；官方要求合规运行中每个 Sunflow 实例的内部线程数为 4。[来源](https://www.spec.org/jvm2008/docs/benchmarks/sunflow.html) |
| `scimark.*` | FFT、LU、SOR、稀疏矩阵及 Monte Carlo 浮点计算。 | small 数据集约 512 KiB，着重缓存内计算/JIT；large 约 32 MiB，更受内存层次与带宽影响。[来源](https://www.spec.org/jvm2008/docs/benchmarks/scimark.html) |
| `xml.transform` / `xml.validation` | 分别执行 XSLT 变换与 XML Schema 校验，调用 JRE XML API。 | 解析与对象构造、树/流式处理、类库实现和 GC；正式测量包含多种输入和访问方式。[来源](https://www.spec.org/jvm2008/docs/benchmarks/xml.html) |
| `startup.*` | 为各 workload 启动新的 JVM 并完成一次 operation。 | JVM 启动、类加载、解释/JIT 初始阶段与 OS 进程创建；与长时间吞吐测量的性能含义不同。[来源](https://www.spec.org/jvm2008/docs/UserGuide.html) |

## Base 与 Peak

| 项目 | Base | Peak |
|---|---|---|
| 目标 | 反映 JVM 默认配置的开箱性能，便于公平复查 | 反映经过允许调优后的系统性能上限 |
| JVM 手工调优 | 不允许 | 允许，但须披露配置 |
| 预热与正式迭代 | 120 秒和 240 秒，1 次正式迭代 | 预热可调整；正式迭代至少 240 秒 |
| Benchmark 线程数 | 可配置，需披露 | 可配置，需披露 |
| 合规成绩 | 必须包含完整 Base 套件，正确性与校验通过 | 可选；需满足 Peak 规则 |

来源：[User’s Guide §1.4、§5.1](https://www.spec.org/jvm2008/docs/UserGuide.html)、[Run Rules §1.4、§2.3–2.4](https://www.spec.org/jvm2008/docs/RunRules.html)。本实验正式命令中的 `-bt 16` 只改变允许配置的 benchmark 线程数，仍使用完整 Base 顺序与默认时长；SPEC 生成的正式文本报告标明 `Run is compliant`。单项重复实验和 JVM 参数实验不构成另一份完整合规 Base 成绩。

## 官方已知问题与本实验对应

- **JDK 版本：** 套件内旧版 javac 不支持 Java SE 8+ 类库字节码，四个 compiler 项可能失败。课程 PDF 推荐先尝试 8u41 RI；本实验实测完整 Base 在其 compiler 阶段无法完成，因此改用独立的 Java 7u75 RI。来源：[Known Issues §8](https://www.spec.org/jvm2008/docs/KnownIssues.html)、[FAQ Q4.8](https://www.spec.org/jvm2008/docs/FAQ.html)。
- **堆内存：** workload 活数据量随 benchmark 线程数增加。默认 32 线程在本机 `scimark.fft.large` OOM；依官方建议减至 16 线程后完整 Base 通过。来源：[Known Issues §1](https://www.spec.org/jvm2008/docs/KnownIssues.html)。
- **结果判定：** 正确性、kit 校验和、完整顺序、时长等是合规条件；有效的单项成绩与完整套件的合规 Base 综合分须分别标注。来源：[Run Rules §2.3](https://www.spec.org/jvm2008/docs/RunRules.html)、[FAQ Q2.1](https://www.spec.org/jvm2008/docs/FAQ.html)。
