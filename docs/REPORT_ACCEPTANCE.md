# P1课程报告验收（报告整理，不是新实验）

依据本地一页《P1 Matrix Multiplication Autotuner》任务书及用户本轮明确范围，
从已审`0050066fd748c0fa5c06475eaa3b8a12e5e07ece`继续；开始时工作区干净、
HEAD与GitHub project01相同。已正常fetch，无reset/clean/强制推送。

## 要求与证据对应

| 老师明确要求 | 现有实现/证据 | 正式报告位置 | 本轮补齐 |
|---|---|---|---|
| 三个明确输入接口 | TargetAdapter、ConfigSpace、SearchStrategy；[core.py](../autotuner/core.py)、[search.py](../autotuner/search.py) | 2.1接口表及实际片段 | 将三个输入和统一评估关系写清，不宣称任意目标零适配 |
| 框架图及框架/实现优劣 | 三输入、统一评估及自身观测反馈 | 2.1图1、2.2取舍 | 新PNG/SVG图；复测结果不进入策略 |
| 使用附件矩阵程序 | [教师原件](../code/original/matrix_multiplication.c)、[工作C](../code/working/matrix_multiplication.c) | 2.2 | 区分原件未改与工作副本外围改动；保留核心循环摘录 |
| 五种s与四种O，共20组合 | [配置文件](../configs/config_space.json)、完整RAW Grid | 1、2.1、4.1 | 明确固定顺序，列出全部20个中位数 |
| 完整Grid并分析性能差异 | 120执行、20完整组、[20行CSV](../evidence/p3_raw_grid/20261012-181149-manual-remaining/grid_summary_20.csv) | 4.1–4.3 | 当前RAW表/热力图/全部测量波动；按行按列分析、证据与机制假设分开 |
| 自行实现另外两算法、比较三算法 | 无放回Random、七邻居随机重启Greedy；各12搜索组及2/1复测 | 5、6 | 轨迹、六行前缀、三算法主表及各自优缺点 |
| 源码及重点说明 | 原件、工作副本、Python接口/策略/评估实现均已入Git | 2、3 | 片段与当前源码核对，保留测量身份 |
| Markdown、可显示图片、软硬件版本 | report.md、三张PNG/框架SVG、已有环境输出 | 1、图1–3、7 | 新图另存，不覆盖历史；链接/显示检查 |
| project01分支、源码及report.md | 已有分支和实现 | 7、README | 普通提交/推送并核对远端 |

上表无已知老师硬性缺项；“无缺项”指要求均在报告中回答，不消除以下实验局限，也不代替老师评分。
五种子、第四算法、perf计数器、终端截图不是任务书硬性要求。
五种子是已有自定计划，只完成首种子，原整体完成/比较false不改。

## 自审范围与结果入口

- [离线统计和输入SHA](../evidence/report_release/20261021/derived-release/summary.json)：
  从原JSONL及终态组重算Grid20、验证3、搜索24、复测3；中位数、CV、MAD、前缀及成本与既有CSV一致。
- [本轮命令、退出码及验收入口](../evidence/report_release/20261021/README.md)：
  只读帮助、20配置列表、离线复算、Markdown数值/片段/链接和保护检查。
- 三张报告图逐张实看，首次图表文字对比度和框架反馈线已修正；正式图排除预热，
  100测量点全部保留，O3/s24测量5单独标识，图并非终端截图。
- 正文完整通读；旧MONOTONIC结果与流水账不再占主结果。旧叙述仍可从基线Git和原交接中读取。
- 不重跑历史110测试、160正确性例、n17或任何矩阵/探针/门禁；新真实性能执行0。

报告局限原样披露：单种子、跨日期/运行段及内核快照差异、Grid s24待机、
低宿主内存警告、端到端前缀成本未知、没有计数器/向量化证据。
新图/复算不签发证书，不修复或覆盖历史连续性结论。

## 原始材料身份

任务书：`E:/software_system/P1/P1 Matrix Multiplication Autotuner.pdf`，1页，SHA-256：
`ffe21db96ab0af28ff2f329f6d0a03b61fac577e530e8649c375ce13bf74eafe`。
已提取文字并查看原PDF渲染，要求以该页为准，未用网上程序替换附件。
本地附件C与Git原件字节一致，SHA-256：
`188d011109c4470e1f41829216e8677a5c2d8f2b7c8a44215652320dbdf6de15`。

沿用科学测量3cc9e0d、搜索执行776b1117、收尾辅助0539309和原session；
本轮只改报告、入口说明和派生脚本/图，不产生新实验身份或迁移旧成绩。
完整SHA在[交接](AUDIT_HANDOFF.md)保留。
