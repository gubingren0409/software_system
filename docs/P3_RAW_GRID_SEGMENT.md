# RAW Grid：一次明确授权的分段续跑 v1

## 9f714a72 后的人工剩余额度授权

用户再次明确授权一次人工续跑：旧尝试的133.3351975秒保持计费，
仅使用原14400秒中的14266.6648025秒余量，不重置额度、不启动第三个窗口。
新增外层授权schema `raw-grid-manual-remaining-v1`，锁定9f714a72中旧授权、旧窗口和旧claim的原始Git字节，
并锁定上次交付目录全部文件。原 `RAW_SEGMENT_WINDOW_V1.claim.json` 不改；另用排他创建的
`RAW_SEGMENT_MANUAL_REMAINING_V1.claim.json` 防止人工授权被重复领取。

实际测量内容3cc9e0d/session f705a488、资源/计时协议和原五组保持。
本次包络从环境预检开始计，前次133.3351975秒＋本次QPC包络≤14400秒，
再加第一段13883.0691008秒≤28800秒。分别在各自epoch内求差，只累加时长；
两次尝试间审核/人工等待单列，不当计算或资源等待。
原Formal失败则停止；通过后才做一次两区间fresh时钟准入（短10亿/长100亿次更新），
全部通过才从index5完成余15组。任何失败停止，无自动重试或额外窗口。

本轮证据入口：[人工续跑声明](../evidence/p3_raw_grid/20261012-181149-manual-remaining/README.md)。
针对外层适配新增5项受控测试，连同既有15项共20项；不额外运行n17、4096或110项历史回归。
下方“历史实际结果”保留上一轮已封存的失败；本次结果如下，不追认旧REJECT为PASS。

### 人工剩余额度的实际结果

辅助冻结957576ca39689e9b8a723006aeb8177562e1620b，SHA256
bd22b200f08a2bb9242434e6baa1ff10a96e314f99c36269968b8d11b8418a21，Git/归档/执行字节一致，LF532/CRLF0。
20项受控测试在工作区及准确干净导出通过；无额外小矩阵或110项历史回归。
Formal预检第一次仅host_memory拒绝（500543488B），第二次通过（1919221760B），总QPC71.505736s。
通过快照CPU均值8.4%/峰24%、WSL6203023360B、commit余量24678649856B、根盘223111458816B；
低于2GiB警告及初次REJECT保留。全部新组Formal用同一v2独立复算，未新增硬门槛。
唯一两区间fresh附件10响应，RAW2/2完整且在未加容差边界内，QPC35.9889743s；MONO警告不作为拒绝。
由原归档从index5完成余15组，新增90fresh；合计20组/120唯一/40组检查，无部分或放弃组。
缓存身份核验后跳过setup；reference生成计数仍1，本次build/reference新增0，性能缓存0。

Windows明确记录20:23:27.022合盖进入Modern Standby、20:59:36.239退出，UTC标签差2169.217s。
定位O3/s24测量5/run_id6948e9aca2aa4b8eaf4b2085ef068731：核心RAW65.122054088s，
该组测量调用宿主QPC2593.8447413s、来宾RAW评估417.886870885s。
这不是同一范围可直接作比例校准的数据；冻结两侧RAW检查通过，未触发原失败分类，原运行器继续最后两组。
保留全部原始样本及后处理警告；不把边界通过宣称为计算全程连续，也不自动剔除/重测。

本次QPC10313.8951424s，旧133.3351975s继续计费；第二段10447.2303399s，
累计24330.2994407s（约6h45m30s），余3952.7696601s，不开启额外窗口。
包络含休眠，不等于纯执行成本；事件UTC差不从QPC预算扣除。
新增15组评估RAW7524.601799888s（内含核心7359.824058116s、验证40.335517487s），
新增组门禁QPC173.2838986s、预检71.505736s、准入35.9889743s均是包络内含项，不全加。
原controller13883.0691008s只代表首段，不能当整个Grid总成本。
只读审计退出0：evidence完整、Grid完整/RAW检查true；P3执行/时钟/比较false，无搜索/独立复测。
原329项session保护、上轮101文件、五组和30条字节前缀、11017更早文件均保持；live checkpoint/CSV合法追加。
Windows/WSL任务进程已退出。新摘要、20行CSV、图、资源与休眠证据均在本次入口。

只读复核，不领取预算或运行目标：

```powershell
python -X utf8 C:/Users/28489/AppData/Local/Temp/raw-grid-remaining-957576ca-9f3uvul3/content/scripts/raw_grid_segment.py audit --authorization E:/software_system/project01/evidence/p3_raw_grid/20261012-181149-manual-remaining/window/authorization.json
```

从干净检出复核时，导出准确957576ca辅助提交，并按原plan核验/还原两侧3cc9e0d归档及缓存路径；
不要直接从后续工作区导入冻结执行模块。不再执行run；剩余额度不是新的调用许可。

## 历史：f19f9f84之后的分段授权

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

## 历史实际结果：资源预检拒绝，未进行fresh时钟准入

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
