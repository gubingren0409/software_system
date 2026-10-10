# 正式 RAW Grid v1：采集前冻结

本轮基点 `3755c4a9d1c387e891fdcc89151250020895370a`，用户已接受22区间候选诊断，
授权修复衔接、一次新恢复和通过后新的20配置Grid。不是P3算法比较完成。
候选协议 `configs/raw_timing_protocol.json`、教师原件、历史成绩/失败/暂停标记保持原样；
`d6811cad` / `2c270825458a4857a5ac9df5aadf597b` 仍空，不写观测。

## 协议与身份

新增 [`raw_formal_timing_protocol.json`](../configs/raw_formal_timing_protocol.json)，
版本 `2026-10-11-raw-formal-v1`，measurement schema6、target schema2绑定同一规范化哈希。
RAW结果schema2、整数先相减和double精确round-trip校验不变；工作C仅改协议版本常量，
核心循环、输入、独立reference和误差容限不变。辅助MONOTONIC保留但不准入、不校准。
新版缺失/null/错误binding启动前拒绝；旧schema1–4只能使用明确历史MONOTONIC契约。
旧契约测试读真实历史协议，不从新版删除binding。候选schema5继续禁止正式准入。

effective target在原配置目录解析所有源码及timing协议路径，之后写入绝对路径；
独立输出目录不需要偶然存在同名协议。旧P3入口不能运行新RAW；新入口
[`start_raw_grid.py`](../scripts/start_raw_grid.py)只实现本轮Grid，campaign继续禁止。

先提交最终运行内容，再从准确SHA导出Windows及WSL干净归档。
Git blob身份、执行字节SHA256及换行分别保存；教师C必须原字节相等。
新session初始化只查询身份/编译器，不编译或执行矩阵/生成reference。
初始化检查点另存不可变 `initial_checkpoint.json`。无旧观测/性能缓存导入。

## 一次恢复（必须先于4096）

原生探针保持已接受的volatile uint64固定工作量；libc、不绑核。
十个短区间各10亿次，第5、10个后各加100亿次长区间：共12区间、300亿次更新、
50条响应（HELLO + 每区间MODE/READ/WORK/READ + QUIT），同一持续存活PID。
不靠sleep或来宾时钟结束工作。每条原始流和JSONL立即flush。
发送前先写进度，然后紧贴write/flush记录send QPC；读取响应立即记recv QPC，
再解析、写文件。原始记录不删除、不补采。

`L=(He_send-Hs_recv)/Frequency`，`U=(He_recv-Hs_send)/Frequency`；
RAW保守范围 `[RAW1_end-RAW2_start, RAW2_end-RAW1_start]`。
通信不确定性、RAW端点读取跨度各≤20ms，`a=5ms+1%*U`，
整个RAW范围须在 `[L-a,U+a]` 内，另报未加容差 `[L,U]`。
整数端点决策复用已审checker，所有区间完整、可判定、RAW通过才签发。
来源/content/session/初始检查点/协议/资源及原始证据都绑定到新证书；独立重算而非读PASS。
候选22区间、旧恢复证书绝不能代用。
Recovery资源v2原规则，CPU只警告；资源与采集整体QPC预算240秒。
资源拒绝、任何时钟失败/过宽/超时都保存并停止，不再次recovery。

## Grid及停止规则

恢复开始起Windows QPC总预算8小时。n4096/random/seed20261008，原20配置；
固定优化外层O0/O1/O2/O3，块内层8/16/24/64/128。每配置1预热+5fresh，中位数。
无失败时120次矩阵调用，reference生成/探针/测试另计。本轮不额外做Grid最优复测，
重复波动来自每组5个样本；后续同协议算法比较/独立复测另授权。

setup和每组前Formal v2：五样本CPU平均≤30%、峰值≤60%；宿主物理及commit余量≥512MiB，
宿主物理<2GiB警告；WSL可用≥2GiB，根盘≥1GiB。每次等待包含采集/重试最多120秒。
不以NTP、MONOTONIC差异等新增门槛；运行中目标自身CPU不受准入门槛限制。

每组前后各1个fresh默认libc/不绑核、固定10亿次的QPC/RAW有界检查（各60秒预算），
位于矩阵计时之外、与矩阵串行。before绑定组index/attempt，after另绑定实测组文件SHA。
六次成功原始测量只有同时通过两侧检查才进入completed和Grid表。
组后检查失败保留六样本及临时聚合，不记完成/最佳；任何执行失败不筛成功子集。
不自动重试失败组，不拼部分组；完整组恢复须重验六原始样本、来源/协议/证书和组检查。
资源/时钟/测量/预算失败立即保存检查点停止。每60秒保存及报告进度。

## 成本和验收口径

核心/验证/进程/配置组/新setup可信来宾成本用RAW；外层调用、资源等待、时钟采集及8小时
预算用Windows真实QPC。reference C自己的generation_seconds及历史MONOTONIC字段仅原始
未校准元数据，不能当可信总调优成本或用于校准RAW。
核心/验证在进程内，进程和lookup/I/O在组内，setup/组/门禁/探针在外层QPC内，不能全部相加。
测试、干净导出、身份核查等辅助操作单列，不混进120个矩阵样本。

独立审计 [`audit_raw_grid.py`](../scripts/audit_raw_grid.py)重验实际源码/编译器/二进制/reference、
恢复证书、20唯一配置及原始JSONL/流、fresh属性、正确性/RAW端点、组两侧、统计和成本。
`grid_complete` / `grid_timing_checks_pass`与P3的 `execution_complete` /
`timing_checks_pass` / `comparison_ready`分开：本轮没有Random/Greedy，P3三项仍false。
旧Grid继续仅历史参考，不混表、不按比例校准。

本轮证据根：[20261011-021601](../evidence/p3_raw_grid/20261011-021601/)。
正式SHA、空session、真实计数和最终结果在冻结/实际执行后补充，不预写成功。
