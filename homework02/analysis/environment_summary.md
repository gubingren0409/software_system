# 正式 Base 实验环境总表

以下是 2026-09-30 正式 `.007` 的**运行时记录**，不把 2026-10-01 的复核机器状态倒填为当时的动态状态。原始证据：[环境采集](../environment/environment_info.txt)、[Windows 宿主采样](../environment/host_cpu_comparison.txt)、[正式日志](../logs/base_run.log)、[raw](../specjvm2008/results/SPECjvm2008.007/SPECjvm2008.007.raw)、[启动脚本](../scripts/run_base.sh)。

| 项目 | 实际记录 | 证据/解释 |
|---|---|---|
| 宿主 OS | Microsoft Windows 11 家庭版中文版，build 26200 | Windows CIM 采样；不是 SPEC 所在进程看到的 OS。 |
| 客体 OS/虚拟化 | Ubuntu 24.04 LTS（noble），WSL2 | `/etc/os-release`、`lsb_release -a`、`uname -a` 与 PowerShell wrapper 的 `Ubuntu-24.04`。 |
| 客体 kernel | `6.18.33.2-microsoft-standard-WSL2`，x86_64 | 运行时 `uname -a`，属于微软 WSL2 内核。 |
| CPU | AMD Ryzen 9 7940HX with Radeon Graphics，x86-64；1 socket × 16 cores × 2 threads = 32 logical CPUs | WSL `lscpu` 和 Windows CIM 一致。`-bt 16` 是 benchmark 并行线程数，不是把机器变成 16 核。 |
| WSL 报告的缓存 | L1d 512 KiB/16 实例，L1i 512 KiB/16 实例，L2 16 MiB/16 实例，L3 32 MiB/1 实例 | `lscpu` 的虚拟机可见拓扑；不能据此断言运行期间命中率。 |
| WSL 内存/交换 | 7.4 GiB 总内存、采集时 6.0 GiB available；2.0 GiB swap | `free -h` 的一次时点快照，不是每项运行时峰值。宿主物理内存不能由此反推。 |
| SPEC kit | SPECjvm2008 1.01 `(20090519)` | `.007.raw` 和报告。独立安装目录 `/home/gubingren/benchmarks/SPECjvm2008`。 |
| 正式测量 Java/JVM | OpenJDK 7u75 RI；`javac 1.7.0_75`；HotSpot 64-Bit Server VM `24.75-b04` | 正式日志、环境采集。Java 8u41 只用于结束后的独立 reporter，不能写成测量 JVM。 |
| `JAVA_HOME` | `/home/gubingren/java/java-se-7u75-ri` | `run_base.sh` 内显式导出，独立于系统 Java。 |
| `PATH` 策略 | `${JAVA_HOME}/bin` 置于原有 `PATH` 最前 | `run_base.sh`，环境记录中的 `which java/javac` 均指向 Java 7 RI。保留原始完整 `PATH` 于环境文件，不在此重复冗长快照。 |
| `CLASSPATH` | 空字符串 | `run_base.sh` 与环境记录；SPEC 由 `-jar` 启动。 |
| Base 命令 | `java -jar SPECjvm2008.jar --base -bt 16` | 无额外 JVM 调优选项、无 properties 改动；正式日志逐字记录。 |
| 工作目录 | `/home/gubingren/benchmarks/SPECjvm2008` | 正式日志 `WORKING_DIRECTORY`。 |
| 结果 | `SPECjvm2008.007`；421.24 SPECjvm2008 Base ops/m，`Run is compliant` | 结果被原样复制到本仓库 `specjvm2008/results/`；报告生成见 reporter 日志。 |

Windows CIM 的 `CurrentClockSpeed=1984 MHz` 和 `MaxClockSpeed=2401 MHz` 只是一份 **22:35 的宿主采样**；`lscpu` 未给出运行时 MHz。既不能作为正式测试各 workload 的实际主频，也不能与官方机器标称主频直接相除。宿主 CPU 温度、功耗与运行期间频率时间序列没有保存。实验初期 Git 不可识别是因为当时位于 `E:\software_system\A2`，不是后来建立的课程仓库；[最终仓库状态](../environment/final_repository_state.txt) 单独记录，原始环境文件不回写。

## 决策链：Java 8 → Java 7

**Problem。** 课程 PDF 建议先用 OpenJDK 1.8.0_41 RI，故独立安装并在完整 Base 中实际尝试。[安装过程](../logs/install.log) 记录下载哈希和路径。

**Evidence。** [Java 8 失败日志](../logs/base_run_java8_failed.log) 在 `startup.compiler.sunflow` 停滞；[当时的线程栈](../logs/startup_sunflow_hang_jstack.txt) 指向 javac 诊断输出相关调用。此运行没有完整结果，不能通过删去 compiler 项“补成 Base”。

**Official documentation。** SPEC [Known Issues §8](https://www.spec.org/jvm2008/docs/KnownIssues.html) 和 [FAQ Q4.8](https://www.spec.org/jvm2008/docs/FAQ.html) 指出随套件提供的 compiler workload 与 Java 8+ 不兼容；这与实际故障位置一致，但日志本身不足以证明所有底层细节。

**Decision。** 保留 Java 8 RI，不替换系统 Java；另装 Java 7u75 RI，通过 `JAVA_HOME`/`PATH` 只为本次测量选择它，保持 kit 和 properties 原状。

**Verification。** [Java 7 compiler 单项检查](../logs/java7_compiler_check.log) 通过；之后 `.007` 的完整 Base 也完成全部 compiler/startup 项。测量后的图形 reporter 异常通过独立 reporter 处理，不改变测量 JVM 或 raw。

## 决策链：32 → 16 benchmark 线程

**Problem。** WSL 可见 32 逻辑 CPU，但内存配额仅约 7.4 GiB；默认高并行度并不保证堆中活对象能装下。

**Evidence。** [32 线程尝试](../logs/base_run_oom_failed.log) 在 `scimark.fft.large` 预热阶段报 `java.lang.OutOfMemoryError: Java heap space`，SPEC 标 `NOT VALID`、综合分 `not valid`。退出码 0 不可覆盖此判定。

**Official documentation。** SPEC [Known Issues §1](https://www.spec.org/jvm2008/docs/KnownIssues.html) 指出活数据量随线程数增加，Base 可降低 benchmark 线程数；[Run Rules](https://www.spec.org/jvm2008/docs/RunRules.html) 要求披露配置并保持完整测量规则。

**Decision。** 选 `-bt 16` 作为有限内存下可行的候选，恰与物理核心数相同，但此巧合**不是**其理论最优性的证据。没有运行线程数扫参，因此不宣称它提供最高分。

**Verification。** [16 线程 `scimark.fft.large` 短诊断](../logs/scimark_large_16t_check.log) 首先通过，随后完整 `.007` 39 项有效、报告合规。短诊断得分不是正式 Base 成绩；最终结论仅是“16 线程能完成合规 Base”，不是“16 线程性能最优”。
