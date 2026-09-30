# 独立单项 profiling：有调度旁证，无正式瓶颈判决

2026-10-01 在与原基准相同的 WSL2 安装、Java 7u75 RI、`-bt 16` 下，使用 [独立脚本](../../scripts/analysis/run_diagnostic_profiles.sh)各运行一次 `compress` 和 `sunflow`。新 ID 为 `.015`、`.016`，既有 `.007` 和 `.008`–`.010` 未重跑、未覆盖。每次以 `/usr/bin/time -v` 和 `perf stat` 包裹**整个 Java 进程**（含 kit 校验、功能 check、预热、测量、报告器）；新 raw/txt 与完整日志分别在 `specjvm2008/results/` 和 `logs/diagnostics/`。两份 SPEC 文本报告都明确 `Run is valid, but not compliant`，因为只选择一个 workload；其分数只作诊断背景，**不能与正式 Base Composite 混用**。Java 7 在测量后的图表渲染阶段仍有已知字体管理器异常，故图表不作为诊断证据。

[解析脚本](../../scripts/analysis/build_profile_summary.py)将新 raw、txt、日志交叉核对，生成 [可复核 CSV](profile_summary.csv)，包含各源文件 SHA-256。表中 CPU 百分比是 `/usr/bin/time` 的“相当于单逻辑 CPU 的百分比”，可超过 100%；RSS 为整个进程的最大常驻内存，非 JVM 堆精确峰值。

| 指标（整个诊断进程） | `compress` `.015` | `sunflow` `.016` |
|---|---:|---:|
| 单项测量得分，ops/min（不合规为完整 Base） | 522.75 | 322.25 |
| 墙钟时间 | 7:00.50 | 6:55.90 |
| CPU 使用量 | 1382% | 2499% |
| 最大 RSS | 669080 KiB | 1128580 KiB |
| 自愿上下文切换 | 27537 | 495345 |
| 非自愿上下文切换 | 9505 | 1331534 |
| 主缺页 | 28 | 0 |

**可支持的有限观察：** 在这两次不同 workload 的新诊断里，`sunflow` 进程用了更多并行 CPU 时间、RSS 和尤其多的上下文切换。SPEC [Sunflow 官方说明](https://www.spec.org/jvm2008/docs/benchmarks/sunflow.html)指出内部每实例 4 线程、外层通常按硬件线程数的一半启动实例；本机此项 raw 为 16 个 benchmark 实例，这与“比 `compress` 有更密集的调度活动”相容。这比只读 workload 名称更具体，但**不能**得出“上下文切换造成 sunflow 得分低”或“sunflow 比 compress 慢”的结论：两者 operation 不同，没有控制只改变线程数的实验，计数也包含整个套件进程。

**没有采纳的弱证据：** `perf stat` 确实给出 `cycles:u`、`instructions:u`、`cache-misses:u`（原始值保存在 CSV），但 WSL2 的虚拟化事件映射和全过程计数使其不适合作为正式迭代的 IPC/cache 瓶颈判断。`perf` 的 `context-switches:u` 在两个新进程都报告 0，而 `/usr/bin/time -v` 报告了非零值，故该 perf 事件被排除，以上上下文切换值只来自 `time -v`。本机 Windows ACPI/WSL thermal 接口未给出可靠温度；本 Goal 没有伪造温度、热降频或频率曲线。

[同日遥测可行性快照](../../logs/diagnostics/telemetry_feasibility.log)是在 `sunflow` 运行期间 04:50 取得的**单一时点**，显示当时 Windows WMI CPU load 100%、WSL `/proc/loadavg` 较高，ACPI 温度读取被拒绝、WSL thermal/cpufreq sysfs 不可用。它帮助判断可用指标，但本身也是诊断时的额外系统活动，既不能代表整个测量阶段，更不能作为旧三次 compress 的历史温度/负载证据。

新的 `compress` 522.75 与正式 `.007` 的 551.55、旧重复的 557.34/545.48/522.15 **不可作受控前后差**：跨日、工具包裹、背景负载和完整/单项顺序均不同。新资料不能回溯解释原三次连续下降，也不足以证明某个工作负载的 CPU/cache/GC 瓶颈；因此只保留为方法和调度旁证，不把它升格为报告的核心因果结论。

[遥测可用性命令记录](../../logs/diagnostics/telemetry_feasibility.log)在 **sunflow 正在运行的 04:50** 采得 Windows `LoadPercentage=100`、WSL 可用内存约 3.5 GiB；这绝非原三次或正式 `.007` 的历史负载。该次 Windows ACPI 温度访问被拒，WSL 无 thermal zone 与 `cpu0/cpufreq` 接口，故无可靠温度/频率序列。当前 WSL 内核 `6.18.40.1-microsoft-standard-WSL2` 与正式环境采集的 `6.18.33.2-microsoft-standard-WSL2` 也不同，进一步排除把新旧分数视为仅 profiling 一因素变化的 A/B 实验。额外三次 compress 即便现在执行也无法重现旧时段缺失的温度/GC/背景活动；此处选择仅两项互补 workload 作最小探测，而不把新样本混入旧重复统计。
