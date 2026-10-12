# RAW Grid：一次明确授权的分段续跑 v1

本轮审计基点 `f19f9f84b19a5a7c2b71ba38ffab206499ffff54`。用户于2026-10-12授权
一个新的外层续跑窗口，不改变测量规则，不增加Random/Greedy、种子、最优独立复测。
正式内容仍为 `3cc9e0d03ba682569fca0e91f28d364f2dab73fa`，session仍为
`f705a488d7b442789973381e2190c944`。不是重新初始化，也不复用性能缓存。

## 冻结范围及原数据

新增 [`raw_grid_segment.py`](../scripts/raw_grid_segment.py) 只做Windows外层调度及独立复核，
从原Windows准确归档导入原门禁/采集/审计模块，从原WSL归档调用 `autotuner.raw_grid measure/accept`。
不能调用过期旧 `run_grid` 入口或要求空session的recover；旧controller、initial checkpoint、
第一段恢复证书保持原字节。原328项session只读文件、五组JSON身份、30条原始字节前缀、
所有第一段恢复文件及6个cache manifests均在授权中锁定。

准备阶段原测量独立审计通过：恰为O0/s8、16、24、64、128，active为空、abandoned为空、
30个run_id唯一。四级候选、编译器、reference、协议及执行源码身份由原审计重验。
原setup和reference_generation_calls=1保持；完整artifacts时跳过setup，不覆盖历史成本。
起点必须为index5/O1/s8，终点index19/O3/s128。原O1/s8资源拒绝attempt保留；新attempt不覆盖它。

辅助实现单独提交/干净导出后运行，提交SHA与实际辅助字节匹配；归档模块ROOT须匹配原计划，
防止工作区导入影子。Git blob身份与执行字节身份分别记录，不假设CRLF/LF字节相等。

## 单次窗口与当前准入

授权文件：[`authorization.json`](../evidence/p3_raw_grid/20261012-144553-segment/window/authorization.json)。
运行前用session内排他创建的 `RAW_SEGMENT_WINDOW_V1.claim.json` 领取一次窗口。
重复启动不能覆盖该文件或获得新的四小时，失败后也不自动第二次调用。

第一段已审核QPC活动包络13883.0691008秒；本段最多14400秒；两段非重叠包络合计≤28800秒。
本段含当前环境查询、首次Formal资源预检、fresh续跑准入、所有组、门禁等待、收尾。
保留25秒停止收尾余量，不缩短每组重复数。审核暂停以UTC起止标签单列，精确可信暂停秒数unknown；
不把它当计算/资源等待。同频率不证明同epoch；只相加分别验证的时长，不跨epoch相减绝对QPC。

先保存Windows启动/主要内存进程/Vmmem、WSL boot_id/uptime/完整meminfo/vmstat，再运行一次现有
Formal v2预检（采集与重试总预算120秒）。不结束用户应用、不重启WSL、不清全局缓存或改策略。
内存/CPU阈值完整沿用原协议。失败则停止，探针/矩阵新增均0。

预检通过后，仅一次2区间fresh续跑附件：原libc、不绑核、同一持久原生进程，先10亿次短区间，
再100亿次长区间；120秒含采集与收尾，保留原始端点/消息并逐条flush。
沿用整数检查：通信不确定性/RAW读取跨度≤20ms，a=5ms+1%×U，RAW整个保守范围在[L-a,U+a]内。
MONOTONIC仅记录。独立复算来源、序号、PID、原始流、端点及全部区间；不信任保存的PASS。
此附件绑定当前原检查点/授权，不替换或改写第一段证书，也不是新增整套12区间恢复。

只有身份、当前Formal门禁及2区间准入均通过才执行余15组。每组仍1预热+5fresh，组前门禁及
两侧fresh RAW检查全部通过才accept。任何失败立即停止，保留部分记录，不拼组/筛子集/自动重测。
每60秒保存并报告阶段、配置、样本、已完成数、本段/累计活动、剩余预算及进程运行时间。

## 验证与验收

新增15项受控测试不执行矩阵/探针，覆盖五组保护及index5开始、跳过setup、排他预算、epoch分离、
旧窗口不能自动续期、资源/时钟/身份失败不启动目标、原始端点复算、部分或缺少哈希不能准入。
首轮测试夹具遗漏group_checks父目录，1项失败；补齐与真实session一致的夹具后15/15通过，失败日志保留。
不重复110项历史回归或额外n17。

独立验收同时运行原测量审计及外层分段审计。原controller累计值只代表第一段，不能当整个Grid成本。
完整目标20配置/120fresh/40分组检查；原恢复12区间及本段准入2区间另计。
成本使用两段非重叠QPC包络，不再叠加内含组、核心、验证、等待时间。
Grid完成与P3 Random/Greedy比较分开，后者execution_complete/timing_checks_pass/comparison_ready仍false。

只读复核（辅助准确提交的干净导出入口；不产生新窗口）：

```powershell
python -X utf8 <auxiliary-archive>/scripts/raw_grid_segment.py audit --authorization E:/software_system/project01/evidence/p3_raw_grid/20261012-144553-segment/window/authorization.json
```

实际新窗口结果待本轮运行后填写；准备/受控测试通过不表示正式Grid完成。
