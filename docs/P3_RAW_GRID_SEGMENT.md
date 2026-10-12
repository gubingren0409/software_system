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
python -X utf8 C:/Users/28489/AppData/Local/Temp/raw-grid-segment-7a8dc17f-us7jy1r9/content/scripts/raw_grid_segment.py audit --authorization E:/software_system/project01/evidence/p3_raw_grid/20261012-144553-segment/window/authorization.json
```

## 实际结果：资源预检拒绝，未进行fresh时钟准入

辅助冻结内容 `7a8dc17f7e268edcea7ff011b56540725ce65af4`，源码/执行/Git blob SHA256
均 `a49b9b2217256eef6bd77e0a3e342e6d9b79b0eed212c32ac4cce0583fbdd6a1`，LF458/CRLF0。
干净归档的15项测试通过；没有矩阵或真实探针。正式依赖完整使用原3cc归档，执行字节清单仍为原计划。

唯一窗口实际在2026-10-12 14:52开始，14:54:48停止；入口可靠退出2、stderr为空。
Formal预检三个完整快照各5个原始样本，宿主最低457887744/397090816/316342272B，
均低于512MiB，只有host_memory拒绝。WSL5771509760/6198054912/6201458688B、
CPU均值8.8/7.2/12.2%、最高19/15/23%、commit余量及磁盘均通过。
第四个采集用剩余3.973811秒，超时退出1、stdout为空；不补造读数。
预检实测120.1520997秒，0.1520997秒停止返回越界如实保留，门禁未通过。
[`resource_rejection_recomputed.json`](../evidence/p3_raw_grid/20261012-144553-segment/resource_rejection_recomputed.json)
用原策略从全部完整原始读数重新计算，结论一致，未放宽/筛选。

新2区间准入、分组探针、矩阵、reference、部分/放弃组、复测全部0。
仍O0五完整/30fresh，起点index5/O1/s8未动；没有新attempt覆盖旧拒绝记录。
原controller/checkpoint/五行CSV/initial/progress/samples六文件字节均相同，第一段证书及
328项原文件、缓存manifests、11017更早历史文件原字节保持。新claim是唯一追加到原session的文件。
准确归档/缓存/探针范围WSL实验进程与Windows主控均已退出，未终止用户应用。

| 验收范围 | 结果 |
| --- | --- |
| evidence_integrity_pass（测量/分段/保护） | true |
| 本段Formal资源 | failed：host_memory；末次采集timeout |
| 本段fresh时钟准入 | not_performed，eligible=false |
| grid_complete / grid_timing_checks_pass | false / false |
| P3 execution_complete / timing_checks_pass / comparison_ready | false / false / false |

本段QPC133.3351975秒；两段活动包络累计14016.4042983秒，低于28800秒。
门禁120.1520997秒是本段内含项，外层启动捕获142.7036262秒也包含本段，不重复相加。
审核暂停UTC标签差116394.010757秒，精确可信时长unknown，不计活动/计算/资源等待。
辅助成本见[`costs.json`](../evidence/p3_raw_grid/20261012-144553-segment/costs.json)；
闭合到收尾/远端fetch的非重叠辅助包络合计87.4688323秒，
见[`final_cost_index.json`](../evidence/p3_raw_grid/20261012-144553-segment/final_cost_index.json)，不是完整轮次成本。
全部22个已闭合operation的退出码、QPC差及流哈希通过，含先前自身收尾父调用；
新文件链接/敏感模式/大文件检查通过，见
[`closed_packaging_verification.json`](../evidence/p3_raw_grid/20261012-144553-segment/closed_packaging_verification.json)。
新主控自身窗口已关闭；剩余预算不自动变成再启动授权，不删除claim或重开四小时。

只读收尾快照宿主可用3949428736B，与门禁不是同一时间，不能追认拒绝或直接开始矩阵。
收尾WSL boot_id从ec5e9efe…变为bc99880b…，Vmmem PID从150060变为151944，
变化为观测、原因unknown；本任务没有执行WSL重启或系统修改。未跨boot减vmstat计数器。
后续先由外审裁决分段额度和续跑入口，再核实资源稳定、做授权范围内的fresh准入。
本轮到此停止；不再次运行Formal、时钟采集、Grid、Random/Greedy或最优复测。
