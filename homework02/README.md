# A2 SPECjvm2008 基准评测

学号：10245102457<br>
姓名：谷秉仁

- 操作系统：Windows 11 宿主上的 WSL2 Ubuntu 24.04 LTS
- CPU：AMD Ryzen 9 7940HX，16 核 32 线程
- 内存：WSL2 中 7.4 GiB，采集时可用 6.0 GiB
- 测量用 JDK：OpenJDK 1.7.0_75 RI，HotSpot 24.75-b04

## 1. SPECjvm2008 与 Base、Peak

SPEC（Standard Performance Evaluation Corporation）制定标准化的性能测试和结果披露规则。统一的程序、计分与校验方法使不同配置的结果可以复查，但分数仍须结合测试环境解释。SPECjvm2008 测量 Java 运行环境执行单个应用的吞吐和启动性能，也反映 CPU、内存系统及操作系统的影响；它不是磁盘、网络或所有 Java 应用性能的通用分数。依据：[SPEC 介绍](https://www.spec.org/spec/spec.html)、[User’s Guide](https://www.spec.org/jvm2008/docs/UserGuide.html)。

主要 workload 包括 `compress`（LZW 压缩，字典查找和数据访问）、`crypto`（加解密及签名，受 JCE 实现和计算指令影响）、`derby`（嵌入式数据库和 `BigDecimal`，涉及对象分配、锁与内存）、`sunflow`（并行光照渲染，涉及浮点计算和任务协作）、`compiler`（Java 源码编译，涉及类加载、对象分配和 GC）、`xml`（XSLT 与 Schema 校验，涉及解析和类库实现）。套件还包含音频、科学计算、序列化和 JVM 启动测试。具体说明及官方来源见[资料整理](analysis/specjvm_background.md)。

Base 限制手工 JVM 调优，采用规定的默认预热和正式迭代，强调可复现与公平比较；Peak 允许披露后的针对性优化，侧重调优后的性能。完整 Base 成绩必须运行全套测试并通过正确性与规则校验。本作业只进行了完整 Base 套件，没有进行完整 Peak 套件。[Run and Reporting Rules](https://www.spec.org/jvm2008/docs/RunRules.html)

## 2. 安装、配置与完整 Base 测试

先检查了系统与现有 Java：WSL 中原有 Java 17，但没有可用的 SPECjvm2008 安装。按照作业建议，将 OpenJDK 8u41 RI 单独解压到 `/home/gubingren/java/java-se-8u41-ri`，通过 `JAVA_HOME` 和 `PATH` 选择，不替换系统 Java。SPECjvm2008 1.01 从[官方安装包](https://www.spec.org/downloads/osg/java/SPECjvm2008_1_01_setup.jar)安装到 `/home/gubingren/benchmarks/SPECjvm2008`，未修改 properties。Java 8 运行完整 Base 时在旧版 `compiler` 项遇到兼容问题；依据[官方 Known Issues](https://www.spec.org/jvm2008/docs/KnownIssues.html)和[FAQ](https://www.spec.org/jvm2008/docs/FAQ.html)，另行安装 OpenJDK 7u75 RI 并用于测量。32 benchmark 线程时 `scimark.fft.large` 内存不足，改用规则允许并在报告披露的 16 线程。安装、失败输出与处理过程保留在[安装日志](logs/install.log)。

测量时 `JAVA_HOME=/home/gubingren/java/java-se-7u75-ri`，其 `bin` 位于 `PATH` 首位，`CLASSPATH` 为空。`uname -a`、`lsb_release -a`、`/etc/os-release`、`lscpu`、`free -h`、`java -version`、`javac -version` 和变量实测输出见[环境记录](environment/environment_info.txt)。

在安装目录执行：

```bash
java -jar SPECjvm2008.jar --base -bt 16
```

2026-09-30 16:10:03 至 18:25:15（北京时间）的完整运行得到 `SPECjvm2008.007`，综合得分 **421.24 SPECjvm2008 Base ops/m**。38 项得分均产生，SPEC 文本报告写明 `Run is compliant`；原始输出见[完整日志](logs/base_run.log)、[raw 数据](specjvm2008/results/SPECjvm2008.007/SPECjvm2008.007.raw)和[文本报告](specjvm2008/results/SPECjvm2008.007/SPECjvm2008.007.txt)。测量后 Java 7 在图表绘制阶段出现字体管理器异常，已使用安装的 Java 8 RI 对原 `.raw` 单独生成报告；它不重新测量或修改得分，过程见[报告生成日志](logs/reporter_regeneration.log)。

![SPECjvm2008 Base 各组得分图](images/base_scores.jpg)

| 分组 | ops/m | 分组 | ops/m |
|---|---:|---|---:|
| `compiler` | 865.65 | `compress` | 551.55 |
| `crypto` | 676.52 | `derby` | 820.63 |
| `sunflow` | 350.25 | `xml` | 1462.69 |
| `startup` | 26.74 | `scimark.large` | 90.84 |

图表和表格均来自 `SPECjvm2008.007`，不是其他试运行的成绩。完整的 `specjvm2008/results/` 同时保留先前诊断结果及后续单项实验；只有 `.007` 是完整合规 Base 成绩。

## 3. Workload 结果分析

以下均取完整 Base 运行 `.007` 的正式迭代分数，单位为 ops/m。

| 测试项 | 得分 | 主要特征与可能影响因素 |
|---|---:|---|
| `compress` | 551.55 | LZW 字典查找与编码，受整数计算、分支、局部性和 JIT 热点优化影响。 |
| `derby` | 820.63 | 数据库业务与 `BigDecimal` 计算，可能受对象分配、锁竞争、缓存与 GC 影响。 |
| `sunflow` | 350.25 | 并行渲染的浮点运算与任务协作，可能受核心并行度和内存访问影响。 |
| `crypto.aes` | 206.89 | 通过 JRE 密码学实现处理输入；Provider、CPU 指令、缓冲区访问可能影响吞吐。 |

这些项目的一次 operation 工作量不同，不能把 `derby` 数字较大直接解释为“数据库算法比渲染快”。SPEC 的文件 I/O 依赖较低，不能仅因 `derby` 名称就把分数归因于磁盘；上述瓶颈均是基于 workload 设计的可能解释，未用剖析器证明。逐项预热/正式值、计算与内存差异见[详细分析](analysis/workload_analysis.md)。

## 4. 与官方发布的 Base 结果比较

选择 SPEC 发布的 [Sugon I620-G20 Base Report](https://www.spec.org/jvm2008/results/res2015q1/jvm2008-20150120-00018.base/SPECjvm2008.base.html)。该机为双路 Intel Xeon E5-2660 v3、20 核 40 线程、256 GiB 内存、RHEL 6.5 和 Red Hat OpenJDK 7 HotSpot 24.45-b08，合规 Base 得分 853.15 ops/m；本机得分为 421.24 ops/m。

| 指标 | 本机 | 官方机器 |
|---|---:|---:|
| 综合 Base (ops/m) | 421.24 | 853.15 |
| `compress` (ops/m) | 551.55 | 1225.96 |
| `derby` (ops/m) | 820.63 | 1705.74 |
| `sunflow` (ops/m) | 350.25 | 491.28 |
| 多数吞吐项 benchmark 线程 | 16 | 40 |

官方综合分约为本机的 2.03 倍。官方机器物理核心和 benchmark 线程更多，内存也大得多，可能提高并行吞吐；两个环境的 CPU 架构/频率、JDK 构建与类库、Linux 发行版及 WSL2 虚拟化层也不同。官方报告中 Xeon 标称 2.60 GHz；本机 WSL 未给出稳定频率，Windows WMI 的[单次采样](environment/host_cpu_comparison.txt)不能当作基准运行时的频率。因此不能把差距直接归因于某一个部件。其他分组与环境对照见[完整比较](analysis/official_comparison.md)。

## 5. `compress` 三次重复运行

同一环境与 `-bt 16` 下，依次执行三次 `java -jar SPECjvm2008.jar --base -bt 16 compress`，均保留默认 120 秒预热、240 秒正式迭代。只运行单项，因此三份 SPEC 报告均为 `Run is valid, but not compliant`，不用作全套 Base 分数。

| Run | 正式分数 (ops/m) | 原始结果 |
|---|---:|---|
| 1 | 557.34 | `SPECjvm2008.008` |
| 2 | 545.48 | `SPECjvm2008.009` |
| 3 | 522.15 | `SPECjvm2008.010` |

均值 541.657 ops/m，样本标准差 17.904 ops/m，变异系数 3.305%；最大与最小相差 35.19 ops/m。每次新 JVM 的类加载、JIT、堆扩张与 GC 过程未必一致，宿主调度、后台任务以及 CPU 动态频率也可能造成波动。没有采集 GC 和频率时间序列，不能确定单一原因。逐次时间、命令及数据见[CSV](analysis/repeat_test_results.csv)与[分析](analysis/repeat_test_analysis.md)，原始输出保留在 `logs/repeat_compress_run1.log` 至 `run3.log`。

## 6. 问题与体会

这次最明显的困难是旧 benchmark 与新环境的兼容性：Java 8 能安装套件，却无法顺利完成旧 `compiler` 项；Java 7 完成测量后又在图表生成阶段遇到字体异常。分离“测量 JVM”和“根据 raw 绘图的 JVM”，保留原始数据，才完成了可复查的 Base 报告。另一次完整试跑在 32 线程下遇到 `OutOfMemoryError`，改为 16 线程后完成，说明 benchmark 线程、可用内存和合规条件必须一起考虑。所有失败现象、输出及解决过程都保留在[安装日志](logs/install.log)与 `logs/`，没有把失败试跑当作成绩。

标准基准测试的价值不只是得出一个总分：还要固定配置、检验有效性、保留 raw 和完整输出。即使同项同配置，三次 `compress` 仍有 3.305% 的变异系数；比较不同机器时更应先看线程数、JVM 与系统条件，而不是只比较数字。

## 7. JVM 参数实验（选做）

为观察 `-Xmx`，先后以 `--base -bt 16 compress` 运行同一单项：默认堆上限 546.46 ops/m（`.013`），设置 `-Xmx2560m` 后 536.04 ops/m（`.014`），观察差值为 **−1.907%**。两次都不是完整套件，且修改 JVM 堆上限不符合正式 Base 调优限制；SPEC 报告均标记为“有效但不合规”，不能替代第 2 节的合规 Base 成绩。前述三次默认参数重复运行的分数范围为 522.15–557.34 ops/m，本次差值落在该波动范围内，不能证明变化由 `-Xmx` 单独造成。较大的最大堆可能改变扩张与 GC 行为，也可能因工作集本来适配默认堆而无益；本次未采集 GC 时间与实际堆占用。准确命令、原始结果与机制分析见[参数实验记录](analysis/jvm_parameter_experiment.md)。

在确定这一对照方式前，曾做过两次 `--peak` 单项探索（`.011`、`.012`），均不是完整或合规 Peak 测试；其 raw 和日志仍保留在 results、logs 中，但不用于本题结论。完整 Peak 套件未运行。
