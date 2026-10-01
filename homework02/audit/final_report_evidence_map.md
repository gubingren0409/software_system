# A2 最终报告证据映射

此表为 [主报告](../README.md)的重要可质疑断言标明**最短核验路径**。本机正式分数只来自 `SPECjvm2008.007`；`.008`–`.010` 为单项重复，`.015/.016` 为后做诊断。链接路径均相对 `homework02/`；原始文件不应为迎合文字而改写。`audit/evidence_manifest.csv`记录源文件当前 SHA-256/字节数，早期独立[哈希记录](../environment/artifact_sha256.txt)另可核对六份核心原件。

| 报告断言或数字 | 一手证据（精确字段/定位串） | 交叉核验与解释边界 |
|---|---|---|
| SPECjvm2008 测量 JRE、CPU/内存/OS；文件 I/O 较少、无远程网络 I/O | [SPEC User’s Guide §1.2](https://www.spec.org/jvm2008/docs/UserGuide.html) | 属官方设计定义，不是本机计数器实测 |
| Base 限制 JVM 手工调优；Peak 可调；有效单项≠合规完整 Base | [User’s Guide §1.4、§1.1](https://www.spec.org/jvm2008/docs/UserGuide.html)、[Run Rules](https://www.spec.org/jvm2008/docs/RunRules.html) | `.007.txt` 为 `Run is compliant`；单项 `.008-.010.txt` 为 `Run is valid, but not compliant` |
| 正式环境为 WSL2 Ubuntu 24.04、`6.18.33.2`、Ryzen 9 7940HX 16C/32T、7.4 GiB WSL RAM | [命令输出](../environment/environment_info.txt)的 `uname -a`、`lsb_release -a`、`lscpu`、`free -h`；[主机摘要](../analysis/environment_summary.md) | 6.0 GiB 可用是采集时快照；后来诊断内核不同，不能覆盖正式环境 |
| 测量 JDK OpenJDK 7u75 RI / HotSpot 24.75-b04；`JAVA_HOME`/`PATH`/空 `CLASSPATH` | [环境记录](../environment/environment_info.txt)的 `# Java`、`# Environment variables`；[正式日志](../logs/base_run.log)启动行 | Java 8u41 只用于早期失败尝试和后处理 reporter |
| 套件为 1.01、原版安装、未改 properties，安装包 SHA `4d3e...69cde` | [安装记录](../logs/install.log)的 `SPEC installer`/`Installation Complete`、[安装位置与完整 SHA](../specjvm2008/INSTALL_LOCATION.txt) | 安装包/JDK 压缩包不在 Git 中；路径为原 WSL 安装 |
| Java 8 编译器不兼容，遂选 Java 7 而非性能选优 | [Java 8 失败日志](../logs/base_run_java8_failed.log)的 `startup.compiler.sunflow`、[jstack](../logs/startup_sunflow_hang_jstack.txt)；[SPEC Known Issues §8](https://www.spec.org/jvm2008/docs/KnownIssues.html)；[Java 7 单项检查](../logs/java7_compiler_check.log) | 原 Java 8 轮没有完整成绩，不可跨版本比较性能 |
| 默认 32 线程 OOM/`NOT VALID`；改 16 可完成 | [OOM 原日志](../logs/base_run_oom_failed.log)的 `OutOfMemoryError`、`NOT VALID`、`START_TIME`/`END_TIME`；[16 线程 SciMark 短测](../logs/scimark_large_16t_check.log)；[Known Issues §1](https://www.spec.org/jvm2008/docs/KnownIssues.html) | 短测不是合规 Base；16 是可运行设置，不是最优证明；手写 `install.log` 终点有校注 |
| 更早 WSL 跳钟废弃轮；正式包装器做启动前校时 | [跳钟失败日志](../logs/base_run_clock_jump_failed.log)的 `11:18:49`→`15:02:30`、`compress 0.00`；[包装器](../scripts/run_base.ps1)时钟检查 | 包装器代码可见，但该次偏差打印未独立保存；不能声称正式全程无时钟风险 |
| 正式命令、时间 `.007` 16:10:03–18:25:15、`-bt 16` | [正式日志](../logs/base_run.log)的 `COMMAND`/`START_TIME`/`END_TIME`；[raw](../specjvm2008/results/SPECjvm2008.007/SPECjvm2008.007.raw)的 `workload`/`configs` | [文本报告](../specjvm2008/results/SPECjvm2008.007/SPECjvm2008.007.txt)显示 `specjvm.benchmark.threads=16` |
| 38 个计分 workload、另 1 个 `check`、39 个 `Valid run!`，无正式 OOM/`NOT VALID` | [正式日志](../logs/base_run.log)中的 `Score on`/`Valid run!`；[raw](../specjvm2008/results/SPECjvm2008.007/SPECjvm2008.007.raw)的 `benchmark-results` | [原始解析器](../scripts/analysis/build_core_data.py)要求 38 个互异项、39 个结果及正确的预热/测量配置 |
| **Base Composite 421.24 ops/min**、本地 reporter 标记 `Run is compliant` | [`.007.txt`](../specjvm2008/results/SPECjvm2008.007/SPECjvm2008.007.txt)的首部与 `Composite result`；[`.007.html`](../specjvm2008/results/SPECjvm2008.007/SPECjvm2008.007.html)、[`.summary`](../specjvm2008/results/SPECjvm2008.007/SPECjvm2008.007.summary)、[`.sub`](../specjvm2008/results/SPECjvm2008.007/SPECjvm2008.007.sub) | [原始 `.raw`](../specjvm2008/results/SPECjvm2008.007/SPECjvm2008.007.raw)的各 iteration 由脚本重算；这不等于 SPEC 官网已发表 |
| raw SHA-256 `4ae651e312061d09760743ab9908129b633e9ce1e5b5b296c13d4a30605e05ad` | [历史哈希](../environment/artifact_sha256.txt)的 `.007.raw` 项与现文件；[审计过程](core_evidence_audit.md) | 报告器操作前后没有独立双哈希；只表述当前与历史记录相符 |
| Java 7 测量后字体 NPE；Java 8 仅独立 reporter | [正式日志](../logs/base_run.log)末尾 `X11FontManager`；[reporter 日志](../logs/reporter_regeneration.log)的 `--reporter ...007.raw`/`EXIT_STATUS=0`；[User’s Guide §5.2](https://www.spec.org/jvm2008/docs/UserGuide.html) | 不写“全程无错误”，也不把后处理 Java 8 误称测量 JVM |
| SPEC 原图与 `.007/images/all.jpg` 相同；自制四图由 CSV 重生 | [原图](../specjvm2008/results/SPECjvm2008.007/images/all.jpg)、[报告拷贝](../images/base_scores.jpg)、[作图脚本](../scripts/analysis/plot_core.py)、[四图目录](../images/analysis/) | `verify_submission.ps1` 核对原图哈希；`plot_core.py --check` 核对生成图 |
| 11 组分及 Composite | [`.007.txt`](../specjvm2008/results/SPECjvm2008.007/SPECjvm2008.007.txt)首部；[组分 CSV](../analysis/base_result_table.csv) | [解析脚本](../scripts/analysis/build_core_data.py)用 raw 的 measured iterations 重算组几何平均 |
| 六项正式/预热/Δ：`compress 551.55`、`derby 820.63`、`sunflow 350.25`、`crypto.aes 206.89`、FFT small `709.00`/large `100.11` | [38 项 CSV](../analysis/workload_measurements.csv)按 `workload` 过滤；[`.007.raw`](../specjvm2008/results/SPECjvm2008.007/SPECjvm2008.007.raw)的各项 `warmup-result`/`iteration-result`；[六项分析](../analysis/workload_analysis.md) | 得分是不同 operation 定义，不宜跨项直比；设计机制见[SPEC workload 页面](https://www.spec.org/jvm2008/docs/benchmarks/) |
| `crypto.aes` 并非纯 AES；SciMark small/large 目标数据尺度不同 | [SPEC crypto](https://www.spec.org/jvm2008/docs/benchmarks/crypto.html)、[SPEC SciMark](https://www.spec.org/jvm2008/docs/benchmarks/scimark.html) | 是设计信息；未采集本次实际 Provider/AES-NI/cache miss |
| Huawei 主参考 335.78，Sugon 补充 853.15，均 1.01/Java 7 | [Huawei 官方报告](https://www.spec.org/jvm2008/results/res2012q1/jvm2008-20111230-00013.base/SPECjvm2008.base.html)、[Sugon 官方报告](https://www.spec.org/jvm2008/results/res2015q1/jvm2008-20150120-00018.base/SPECjvm2008.base.html)；[两份本地快照](../analysis/official_reference_huawei.html)、[Sugon 快照](../analysis/official_reference_base.html) | [候选清单](../analysis/official_reference_candidates.csv)说明六份 Base 中同代筛选；[官方分数 CSV](../analysis/official_group_scores.csv)及[校验脚本](../scripts/analysis/verify_official_data.py)核对七个指标各两份 |
| Huawei/Sugon CPU、核心/线程、内存、JVM、OS；跨机比值 0.797/2.025 | 两份官方 HTML 的 `hw-info`、`sw-info`、`jvm-info`；[官方比较表](../analysis/official_comparison.md)及[CSV](../analysis/official_group_scores.csv) | 本机环境另见本表上方；跨系统比较未控制变量，倍率仅为观察 |
| 三次主重复 `.008/.009/.010` 为 `557.34/545.48/522.15` | [主重复 CSV](../analysis/repeat_test_results.csv)、各 [`.008.raw`](../specjvm2008/results/SPECjvm2008.008/SPECjvm2008.008.raw)、[`.009.raw`](../specjvm2008/results/SPECjvm2008.009/SPECjvm2008.009.raw)、[`.010.raw`](../specjvm2008/results/SPECjvm2008.010/SPECjvm2008.010.raw)及同目录 TXT；[Run1](../logs/repeat_compress_run1.log)、[Run2](../logs/repeat_compress_run2.log)、[Run3](../logs/repeat_compress_run3.log) | 原始顺序保留；[解析脚本](../scripts/analysis/build_core_data.py)逐个对照 raw、TXT 与 CSV，三次均非完整合规 Base |
| `n=3`、均值 541.657、样本 SD 17.904、CV 3.305%、极差 35.19 | [统计 CSV](../analysis/repeat_statistics.csv)由三次原始分数重算；[重复分析](../analysis/repeat_test_analysis.md) | 无同步历史频率/温度/GC，连续下降不能唯一归因；不把极差称置信区间 |
| `.015/.016` 调度旁证，不能解释旧 `.007` 或旧重复 | [独立诊断 CSV](../analysis/diagnostics/profile_summary.csv)、[分析](../analysis/diagnostics/profile_analysis.md)、[原始诊断日志](../logs/diagnostics/) | 仅两次单项、整进程范围、不同 workload/时段，报告均 noncompliant；WSL perf 事件有限制 |
| 选做 `-Xmx` 对照不构成正式 Base 改进结论 | [参数记录](../analysis/jvm_parameter_experiment.md)、[`.013.txt`](../specjvm2008/results/SPECjvm2008.013/SPECjvm2008.013.txt)、[`.014.txt`](../specjvm2008/results/SPECjvm2008.014/SPECjvm2008.014.txt) | 两次顺序单项，差值在旧重复波动范围内；不与 `.007` 合并 |

## 可复核命令

在仓库根目录 `homework02` 分支执行：

```powershell
pwsh -NoProfile -File homework02/scripts/verify_goal1.ps1
pwsh -NoProfile -File homework02/scripts/verify_submission.ps1
python homework02/scripts/analysis/build_core_data.py --check
```

验证器的实际输出见[最终验收日志](../logs/final_submission_verification.log)；它还核对官方快照、图表、相对链接、旧哈希和本阶段证据清单。不能用一次验证器 PASS 代替 SPEC 官方投稿审查或历史环境遥测。
