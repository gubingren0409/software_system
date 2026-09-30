# A2 必做部分证据审计（2026-10-01）

审计对象是仓库中保留的真实文件，而不是 README 的二次描述。正式结果唯一指向 `SPECjvm2008.007`；失败尝试、单项重复和本 Goal 新增诊断均不得替代它。路径均相对于 `homework02/`。[逐文件清单](evidence_manifest.csv)记录了原有及新增的一手证据文件的字节数、UTC 修改时间和 SHA-256，可运行 `python scripts/analysis/build_evidence_manifest.py --check` 复核。已有的 `environment/artifact_sha256.txt` 是历史哈希记录；新增清单不改写它。

## `.007` 正式 Base 的逐项判定

| 核验点 | 直接证据与交叉核验 | 判定 |
|---|---|---|
| 1. 完整 Base | `.007.raw` 的 `workload=SPECjvm2008 Base`，版本 `1.01 (20090519)`；38 个互异的计分 workload，另有 `check`；`base_run.log` 有 38 条 `Score on` | 是完整套件，不是单项选测 |
| 2. Composite | 原始各 iteration 重算组分，再与 `.txt`、`.html`、`.summary`、`.sub` 和 `base_run.log` 的 `421.24` 对照 | 一致，单位 SPECjvm2008 Base ops/m |
| 3. 合规标签 | `.txt`/`.html` 显示 `Run is compliant`；`.sub` 的 status 相同 | SPEC 报告标记合规；这不是声称已提交 SPEC 官方发表 |
| 4. 线程数 | `.raw` 配置 `specjvm.benchmark.threads=16`；`.txt` 和命令一致；startup 子项固定单线程，Sunflow 有其特殊线程安排 | 吞吐项配置为 `-bt 16` |
| 5. 测量 JVM | `base_run.log` 和 `scripts/run_base.sh` 显示 OpenJDK 7u75 RI、HotSpot 24.75-b04；`.raw` 的运行时信息与之吻合 | 正式测量由 Java 7 完成，Java 8 仅用于后处理 |
| 6–7. reporter | `reporter_regeneration.log` 是 `java -jar ... --reporter ...007.raw`，Java 8u41，退出码 0；脚本 `regenerate_report.sh` 也只调用 reporter。SPEC [User's Guide §5.2](https://www.spec.org/jvm2008/docs/UserGuide.html)明示此模式读取既有 raw、不会运行 benchmark | 支持“只重生报告、不重跑”；见下方证据边界 |
| 8. 各 workload | [自动解析器](../scripts/analysis/build_core_data.py)逐项解析 `.raw` 的一次 measured iteration，核对 `.txt` 的逐项得分，生成 [38 项测量表](../analysis/workload_measurements.csv)和 [11 组得分表](../analysis/base_result_table.csv) | 38/38 均有成绩；`check` 通过 |
| 9–10. 无效标志/OOM | `base_run.log` 内 `Valid run!` 共 39 次，无 `NOT VALID` 或 `OutOfMemoryError`；`.007.txt` 合规 | 正式测量未发现这两类失败；失败的 OOM 另在旧日志 |
| 11. 其他错误 | `base_run.log` 测量结束后的 Java 7 图表生成阶段有 `X11FontManager` `NullPointerException`；随后 Java 8 reporter 成功生成图表与报告。不得把异常写成“全程无错误”，也不能误判为 workload 失败 | 报告渲染错误确实存在，但未见它改变已完成的 `.007` 测量；仍保留该风险说明 |
| 12. raw 哈希 | `.007.raw` SHA-256 `4ae651e312061d09760743ab9908129b633e9ce1e5b5b296c13d4a30605e05ad`，与历史 `artifact_sha256.txt` 一致 | 当前文件完整性可复核 |
| 13. 报告一致性 | `.txt`/`.html`/`.summary`/`.sub` 的 Base 421.24 一致，前两者及 `.sub` 合规标志一致；原始 workload 数据与 `.txt` 逐项一致 | 未发现关键分数不一致 |
| 14. 图来源 | `images/base_scores.jpg` 与 `.007/images/all.jpg` SHA-256 完全相同 | 报告图是正式 `.007` 图的拷贝 |

`logs/base_run.log` 的 `EXIT_STATUS=0` 不是单独的有效性证明：失败 OOM 日志也以 0 退出。有效性必须联合套件/校验、逐项 `Valid run!`、无 `NOT VALID`、raw 完整性和生成报告状态判断。基于这些交叉证据，本仓库的 `.007` 可作为课程实验的完整合规 Base 结果；原始文档未包含向 SPEC 投稿及独立复审的证明。Java 7 报告器异常发生在全部工作负载测完后；另用 Java 8 reporter 后处理符合官方单独 reporter 用法。由于没有 reporter 操作前后连续采集的 raw 双哈希，不能把“raw 从未发生任何字节级写入”当作已独立证明的事实；能够证明的是当前 raw 与历史记录一致、其数据与全部报告互相吻合。

## 版本/线程数决策链及失败样本隔离

1. 课程建议的 Java 8u41 已实际安装并尝试。`logs/base_run_java8_failed.log` 在 `startup.compiler.sunflow` 停住；`logs/startup_sunflow_hang_jstack.txt` 显示编译器诊断输出中的线程阻塞。SPEC [Known Issues §8](https://www.spec.org/jvm2008/docs/KnownIssues.html)与 [FAQ](https://www.spec.org/jvm2008/docs/FAQ.html)指出套件内旧版 javac 对 Java 8+ 类库不兼容。不能删除 compiler 子项后冒充完整 Base，因此另选 Java 7u75 RI；`logs/java7_compiler_check.log` 是单项验证而非完整结果。
2. 机器有 32 逻辑 CPU，WSL 当时只分配约 7.4 GiB RAM。无 `-bt` 的 Base 尝试在 `scimark.fft.large` 预热阶段出现 `OutOfMemoryError`，并明确 `NOT VALID`。SPEC [Known Issues §1](https://www.spec.org/jvm2008/docs/KnownIssues.html)允许 Base 通过减少 benchmark 线程数降低活数据量，故候选设为 `-bt 16`。它恰与 16 个物理核心数相同，但只是资源约束下验证过可完成的设置，不是证明的最优线程数。
3. `logs/scimark_large_16t_check.log` 为短时单项诊断，因时长/范围不合规，不当作分数。其后才运行完整 `.007`；`.007` 的命令、默认 Base 时长和合规标签独立核实。历史 `scripts/run_base.*` 中的 `/mnt/e/software_system/A2/homework02` 是原实验路径；本仓库检出路径不同，直接照搬脚本会写到旧目录，故保留历史脚本不作静默改写。

## `install.log` 时间线矛盾

| 证据 | 记录的时间与含义 |
|---|---|
| `logs/install.log` 描述 | OOM 尝试标为 `15:05–16:48`，与正式 Base `16:10–18:25` 字面重叠 |
| `logs/base_run_oom_failed.log` 机器内嵌时间 | `2026-09-30T15:06:31+08:00` 至 `16:00:50+08:00`，在 `scimark.fft.large` 暖机 OOM；`Composite result: not valid` |
| `logs/scimark_large_16t_check.log` | `16:07:35–16:09:12`，位于失败尝试与成功尝试之间 |
| `logs/base_run.log` 机器内嵌时间 | `16:10:03–18:25:15`；正式 `.007.raw` 末次修改 `18:25:08`，早于 reporter `18:26:42–18:26:56` |
| `logs/base_run_clock_jump_failed.log` | 更早的另一轮从 `11:00:28` 开始，测量中墙钟由 `11:18:49` 跳至 `15:02:30`，出现不可信负吞吐；已废弃 |
| `scripts/run_base.ps1` | 正式包装器先用 Windows UTC epoch 同步 WSL，检查偏差不超过 3 秒，再启动 benchmark；但本仓库没有单独保存当时包装器打印的偏差值 |
| Windows 文件元数据 | 仓库副本 `.007.raw` 创建时间晚于其嵌入测量时间，显示复制带来的元数据效应；只能辅助，不能代替日志内时间 |

**结论：** 对被问及的 OOM 与正式 `.007` 两次运行，最有力的原始日志支持不重叠。`install.log` 的 `16:48` 是人工描述的错误或近似记录错误，可能包含其他工作时间；无法从现有证据确定其具体笔误来源。早先确有 WSL 跳钟，但发生在另一份失败日志，不能据此把 OOM 的 `16:00:50` 擅改成 `16:48`。该判断置信度高；不影响正式 `.007` 的工作负载成绩和合规标志。报告应写为：“一次默认线程 Base 在约 15:06–16:01 因 OOM 失效，16:07–16:09 完成 16 线程短测，16:10–18:25 完成正式 Base；原 `install.log` 将失败段终点写成 16:48，与机器日志不符。”`install.log` 的旧行未删除，文件末尾附有校注；原始 benchmark 日志及结果文件未为消除矛盾而修改。

## 可重跑的核查

- `pwsh -NoProfile -File scripts/verify_goal1.ps1`：关键 `.007` 文件、分数、合规、线程、版本、Git 仓库/分支、raw 哈希。
- `pwsh -NoProfile -File scripts/verify_submission.ps1`：必做研究文件、可解析的 CSV、来源清单、相对链接、图表重生校验；不把选做题或指定 PDF 形式强行当提交规则。
- `python scripts/analysis/build_core_data.py --check`：raw、文本报告与派生表交叉校验。完整输出保存在 [最终核查日志](../logs/final_core_verification.log)。

限制和后续测试在 [remaining_risks.md](remaining_risks.md)。
