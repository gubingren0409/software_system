# JVM `-Xmx` 参数对照实验（选做）

选择 `compress` 单项测试。两次都使用同一 OpenJDK 7u75 RI、同一 SPECjvm2008 1.01 安装、`--base -bt 16 compress`、120 秒预热和 240 秒正式迭代；唯一有意改变的 JVM 启动参数是第二次加入 `-Xmx2560m`。测量期间未修改 properties。单项选择本身及手工堆参数使测试不能成为完整合规 Base 成绩；两次 SPEC 报告均写明 `Run is valid, but not compliant`。正式全套 Base 成绩仍以 `SPECjvm2008.007` 为准。

| 配置 | 运行前 JVM 报告的 `MaxHeapSize` | `compress` 正式得分 (ops/m) | 结果编号 |
|---|---:|---:|---|
| 默认堆上限，无 JVM 命令行参数 | 1,977,614,336 字节 | 546.46 | `SPECjvm2008.013` |
| `-Xmx2560m` | 2,684,354,560 字节 | 536.04 | `SPECjvm2008.014` |

修改后减少 10.42 ops/m，相对默认配置为 **−1.907%**。默认轮时间为 2026-09-30 22:12:29–22:19:32，修改轮为 22:19:32–22:26:33（北京时间）。逐次原始命令和时间见[数据 CSV](jvm_parameter_base_results.csv)，测量输出见[默认日志](../logs/parameter_base_baseline.log)与[`-Xmx2560m` 日志](../logs/parameter_base_xmx2560m.log)，对应[默认文本报告](../specjvm2008/results/SPECjvm2008.013/SPECjvm2008.013.txt)和[修改后文本报告](../specjvm2008/results/SPECjvm2008.014/SPECjvm2008.014.txt)。Java 8 RI 根据原 raw 单独生成两份报告的过程见[reporter 日志](../logs/parameter_base_reporter.log)。

`-Xmx` 只规定最大 Java 堆容量，不代表 JVM 一开始就占用这么多。上限变化可能影响自适应堆扩张、垃圾收集触发频率及工作集的内存压力；如果原堆已经足够，增大上限未必提升 `compress` 吞吐。依据：[Oracle Java 7 `java` 文档](https://docs.oracle.com/javase/7/docs/technotes/tools/solaris/java.html)、[HotSpot GC ergonomics](https://docs.oracle.com/javase/8/docs/technotes/guides/vm/gc-ergonomics.html)。

这是一组顺序 A/B 运行，没有 ABBA 交错、GC 日志或 CPU 温度/频率时间序列。此前三次相同默认参数的 `compress` 单项已在 522.15–557.34 ops/m 之间波动，本次 10.42 ops/m 的差值落在这个范围内，因此不能把下降归因于 `-Xmx`，也不能据此推荐该参数。若要验证因果关系，需要多轮交错重复并测量 GC 与实际内存占用。

过程记录：最初曾用 `--peak` 做两次单项探索，结果编号 `.011`、`.012`，分别为 507.62 和 472.99 ops/m；两者均非完整合规 Peak，不能与 Base 分类混用。其[原 CSV](jvm_parameter_results.csv)、日志和 raw 仍保留，以便复查；本报告的参数结论只采用 `.013`、`.014` 的 Base 模式单项数据。完整 Peak 套件未运行。
