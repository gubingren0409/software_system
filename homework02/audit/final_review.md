# A2 最终报告四轮自审

审稿范围：[主报告](../README.md)、[逐条证据映射](final_report_evidence_map.md)、既有分析/原始 SPEC 结果、教师 A2 任务清单（工作区外原 PDF）。以下是**本次报告集成后的自审**，不是 SPEC 官方认证。自动验收的实际输出单独保存在[最终验证日志](../logs/final_submission_verification.log)。

## REVIEW A — TA Requirement Review

| 教师必做要求 | 主报告位置 | 核验结果与处理 |
|---|---|---|
| 官方四份资料、SPEC/用途/workload/Base–Peak | §2，另有[背景整理](../analysis/specjvm_background.md) | 四份 SPEC 官方链接明确；`compiler/compress/crypto/derby/sunflow/xml` 等类别及计分机制均在正文，不只给外链 |
| 安装并完成一次完整 Base、保留配置/输出/results | §3–5、§9；[results](../specjvm2008/results/) | 正式 `.007` 38 项+功能 check，421.24、报告 compliant；安装过程、Java/变量、命令、时间、日志均可定位；未以单项代替完整套件 |
| 至少三项 workload 的得分及原因分析 | §6 | 六项预热/正式/变化及设计、可能机制、证据边界；修正 `crypto.aes` 不等于纯 AES 的潜在误述 |
| SPEC 已发表 Base 结果对照 | §7 | 主 Huawei、补充 Sugon；CPU/JDK/OS/线程/内存与七个同名指标、倍率及非受控边界均披露 |
| 相同环境三次单项重复 | §8 | 仅原 `.008–.010`；显示原分数、均值、样本 SD、CV、极差及 `n=3` 限制 |
| 遇到的问题、解决方案、反思 | §4、§9–11 | 网络、Java 8、跳钟、OOM、reporter 均有“现象—证据—处理—正式结果影响”；保留失败日志 |

课程 PDF 允许 Markdown 或 PDF；主报告使用 README Markdown，没有无必要的重复 `report.md`。选做 JVM 参数实验只保留独立链接，不污染正式 Base 主线。

## REVIEW B — Performance Engineering Review

1. **错误分母/排名风险：**不同 workload 的 operation 定义不同；报告第 5–6 节和组图 caption 明确不能把 `derby 820.63` 与 `sunflow 350.25` 当通用“快慢”比。SciMark `709/100.11≈7.08` 明确不称内存惩罚倍率；`crypto.aes` 与 `crypto` 组分分开。
2. **跨机因果风险：**官方对照只算同名指标、保持原环境列；Huawei 与 Sugon 分别服务于拓扑/Java 家族的不同参考目的。报告没有把官方倍率归因于单一核心数、容量、频率或 JVM 参数；Huawei 部分软件披露占位符已注明。
3. **稳定性统计风险：**三次 `compress` 是新 JVM、单项且 noncompliant；样本 SD 使用 `n−1`，CV、极差、均值均有生成 CSV。图的纵轴放大标注清楚，正文不把单调下降写成长期趋势或热降频证据。
4. **诊断混用风险：**后做 `.015/.016` 是不同 workload 的整进程计数、跨日且 WSL 内核版本不同；只提供调度旁证，不解释 `.007` 迭代瓶颈或旧三次下降。正式图/CSV仍唯一来自 `.007`；选做 `-Xmx` 不在主结论里宣称优化。

## REVIEW C — Evidence Review

- 用[原始解析器](../scripts/analysis/build_core_data.py)复核 `.007.raw`、TXT、38 项/11 组/Composite 和 `.008–.010` raw/TXT/索引；正式 raw 旧 SHA 与[历史清单](../environment/artifact_sha256.txt)一致。`EXIT_STATUS=0` 并非唯一判据，失败 OOM 也曾以 0 退出。
- [官方快照核验脚本](../scripts/analysis/verify_official_data.py)核对 Huawei/Sugon 共 14 个分数；[文档表核验脚本](../scripts/analysis/verify_document_tables.py)还检查 README 的 Base/六项/官方/重复表与 CSV 一致，避免“CSV 对而报告抄错”。
- [证据映射](final_report_evidence_map.md)为主要数字、版本/线程决策、时间线、reporter 异常和限制分别指向 exact raw、日志字段、保存的网页或官方文档；不同级别的“直接测得/官方定义/可能机制”在正文分开。发现旧 `install.log` 的 OOM 终点写成 `16:48`，沿用前一阶段[审计校注](core_evidence_audit.md)而未改原始 benchmark 日志。
- 剩余证据边界未因行文优化而消失：reporter 前后缺独立双哈希，正式期间缺同步频率/温度/GC，跨机无控制变量，历史脚本固化旧路径。[风险清单](remaining_risks.md)

## REVIEW D — Report Quality / Markdown Review

- **逻辑修复：**旧 README 以 Sugon 为唯一官方参照，且安装、结果、失败与选做参数比例失衡。现用 11 节依“目标→定义→环境→配置→正式结果→workload→官方→重复→问题→反思→结论”组织；失败样本只讲决定性路径，细节留链接。
- **去重修复：**[背景资料](../analysis/specjvm_background.md)的 `mpegaudio`/`serial` 表格重复行已删；[诊断分析](../analysis/diagnostics/profile_analysis.md)重复遥测说明已合并。Markdown 预览曾将摘要首句的粗体标记原样显示，已加入空格修复；预览元数据引入的第二个标题只属于临时渲染命令，重新渲染时不再添加元数据标题。
- **图表审查：**保留原 SPEC 图，四张自制图分别说明组分（`startup` 独立尺度）、预热变化、无量纲官方比值、三次重复（非零纵轴与均值）。四图由[作图脚本](../scripts/analysis/plot_core.py)和已核对 CSV 生成，视觉检查字号、图例/单位及 caption；不为凑图数继续作图。
- **渲染与链接：**使用 Pandoc GFM 渲染独立 HTML，实际解析出 **1 个一级标题、11 个二级节、5 张嵌入图、9 张表、0 个残留字面 `**`**；headless Chrome 顶部预览亦已检查，无重复标题或粗体渲染错误。`verify_submission.ps1` 递归核对本提交内 **204 个** Markdown 相对链接、5 个图像引用及四张分析图的 README 嵌入。最终结果以[实际日志](../logs/final_submission_verification.log)为准。

## 审稿结论

四轮审阅没有发现需要重跑完整 Base 的有效性问题；已修复报告中的渲染、重复和主参考选择问题。2026-10-01 的 `verify_submission.ps1` 对要求的 **15 项条件均 PASS**，输出见[最终日志](../logs/final_submission_verification.log)。这只说明课程提交材料当前自洽，不是 SPEC 官方独立审查或因果归因证明。
