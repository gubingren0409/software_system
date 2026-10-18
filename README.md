# Matrix Multiplication Autotuner (P1)

《软件系统优化》实践项目 P1。**P2 历史Grid已保存；P3首种子正式比较尚未完成。**

当前（2026-10-18，用户再次重试）：**P3_RAW_VALIDATION_RESOURCE_BLOCKED**。
已接AC、电量100%，16项相关回归及准确干净归档通过；新辅助02907787，测量35a60b0/session9332ead2不变。
Formal预检、唯一fresh RAW短/长2/2及源码/缓存核验通过，但s24组前四快照宿主最低268–453MiB，
均仅host_memory拒绝；118.9061907s内停止，新增目标0。仍2/3组、12/18fresh，未启动搜索。
289原session文件、13,618其他证据、旧两组/原12条前缀不变；防睡眠finally释放，任务进程退出。
本段207.9839123s，累计1469.0700994s，余2130.9299006s，不重置或自动再次尝试。
证据完整性true；验证全完成/全计时及P3三项false。资源预检通过不等于后续组门禁通过。
[本轮完整证据/具体拒绝/下一步](evidence/p3_raw_comparison/20261018-201600-user-retry3/README.md)。

历史（2026-10-15下午，用户再次重试）：**P3_RAW_VALIDATION_AC_POWER_BLOCKED**。
辅助103387c、测量35a60b0/session9332ead2不变，15项关联回归及干净归档通过。
Windows接电检查报告AC未连接、电量75%，安全停止；资源门禁/RAW准入/新目标全部未执行。
仍2/3组、12/18fresh，287个原session文件、13,545其他证据及原样本前缀不变；未启动搜索。
原1257.8308447s照计，本段3.2553424s，累计1261.0861871s，余2338.9138129s，不重置或再次尝试。
单独拒绝核验和3项合成测试通过；原辅助审计因早期阶段文件缺席而拒绝的结果也原样保存，不伪写PASS。
[本轮完整证据/停止边界](evidence/p3_raw_comparison/20261015-152400-user-retry2/README.md)。
请先接电并保持开盖；本轮进程退出，下一步仍仅使用原余量补s24，不直接重复已关闭claim。

历史（2026-10-15，用户授权一次重试）：**P3_RAW_VALIDATION_RESOURCE_BLOCKED**。
辅助内容3eaeadd、测量内容35a60b0/session9332ead2；14项关联测试及干净归档验证通过。
Formal预检和唯一short/long RAW2/2通过，但s24组前3个有效快照仅host_memory拒绝，第四次采集超时。
门禁119.5028273s内安全停止，新增目标0；仍2/3组、12/18fresh，原270个session文件与13,458其他证据不变。
原两段1046.1205449s照计，新211.7102998s，累计1257.8308447s；余2342.1691553s不自动再run。
停止后快照显示VALORANT约1.71GiB占用；不终止用户应用、不放宽门槛、不追认旧REJECT。
来源/原数据完整性true，验证完成/全验证计时及P3三项false。任务进程已退出，没有搜索。
[本轮完整证据及下一步](evidence/p3_raw_comparison/20261015-130000-user-retry/README.md)、
[独立验收](evidence/p3_raw_comparison/20261015-130000-user-retry/continuation/independent_continuation_audit.json)。

历史（2026-10-14，释放E空间后）：**P3_RAW_VALIDATION_RESOURCE_BLOCKED**。
E盘可写性/约58.4GiB自由空间通过；一次新的短/长RAW准入2/2通过。
只准备补齐原session的O3/s24，不重跑两组，不重置3600秒预算。组前Formal门禁四个快照
均仅host_memory拒绝（最低约228/288/376/287MiB），120秒耗尽后安全停止，新增目标0次。
仍为2/3组、12/18fresh，余s24六次；原253个session文件、13,354个其他证据及12条样本字节前缀不变。
外层助手准确内容`22fe97c02e2bf1cd56662413e10fc5311113a246`双端10项受控测试通过；
实际测量内容35a60b0、session9332ead2不变。原846.073676s仍计费，新增200.0468689s，累计1046.1205449s。
证据完整性true；验证完成/全验证计时及P3三项仍false，真实搜索未运行。
E工作树已安全快进同步0a74241，原未跟踪目录有逐SHA备份，未reset或覆盖用户修改。
[本轮完整入口/阻塞及预算](evidence/p3_raw_comparison/20261014-204900-disk-continuation/README.md)、
[最终独立核验](evidence/p3_raw_comparison/20261014-204900-disk-continuation/continuation/independent_continuation_audit.json)、
[单次补齐规则](docs/P3_RAW_VALIDATION_CONTINUATION.md)。本次claim已关闭，不自动重试或启动搜索。

历史（2026-10-14，c08184e后新授权）：**P3_RAW_VALIDATION_PARTIAL / EVIDENCE_DISK_FULL**。
沿用执行内容`35a60b090b728d2ec3b6a8ea014beac69fe3766d`，新validation session
`9332ead2881a4c1e91b966e90a0d2057`，未改运行代码/协议，未重跑历史测试。
已接AC；唯一fresh准入2/2与已采5个组边界区间全部通过。O3/s128、s64完成2组/12fresh，
全16777216元素正确；新中位数51.602724641s、52.784908609s，无待机或连续性拒绝。
O3/s24在启动目标前写检查点失败：E:证据盘仅剩16384B；WSL EIO、Windows ENOSPC，
保存并停止，余6次未执行，不补跑、不重置claim。活动QPC846.073676s（3600预算内）。
有效检查点仍为最后持久化的ready/两组，不代表控制器成功；真实退出1，失败临时片段保留。
证据完整性true，验证完成/全验证计时以及P3 execution_complete/timing_checks_pass/comparison_ready均false。
13,231个历史文件字节不变，旧AC拒绝/claim及关闭Grid完全保留，真实搜索仍为0。
E:无法继续写入，使用C:应急同历史project01副本提交；原E:工作树停在c08184e，未reset或回写。
[本轮完整交接及恢复限制](evidence/p3_raw_comparison/20261014-182807-ac-validation/README.md)、
[新独立验收](evidence/p3_raw_comparison/20261014-182807-ac-validation/independent_validation_audit.json)、
[三配置旁列表](evidence/p3_raw_comparison/20261014-182807-ac-validation/three_configuration_comparison.csv)。

历史（2026-10-14，e1b3a7ee后）：**P3_RAW_COMPARISON_PARTIAL_AC_POWER_BLOCKED**。
已新增独立RAW比较协议/入口及连续性保护；没有解除原campaign的Grid-only限制。
执行内容`35a60b090b728d2ec3b6a8ea014beac69fe3766d`双干净归档各19项假执行器测试通过，
20配置及科学文件字节身份通过；新validation session `f9f3bb0d54724d2385a8b77be26a99b3`，
新search session `d7a9ba9fc5384990b739ff51363a03e5`为空。本轮**没有真实搜索**。
唯一验证调用在接电检查停止：API成功、ACLineStatus=0、电量72%。防睡眠请求同线程释放。
资源门禁及时钟准入均未执行（不是失败/PASS）；矩阵0/18、组0/3、部分样本0。
证据完整性true；validation完成/时钟和P3 execution_complete/timing_checks_pass/comparison_ready均false。
原Grid已关闭，20组/120次及O3/s24待机样本、检查点/证书/预算原字节保留，不追加或退款。
[本轮交接与下一步](evidence/p3_raw_comparison/20261014-102833/README.md)、
[入口及预声明协议](docs/P3_RAW_COMPARISON.md)、
[独立验收](evidence/p3_raw_comparison/20261014-102833/independent_validation_audit.json)。
本轮停止并等待外审；接电、开盖后仍需明确新的有限验证授权，不能重复运行已领取的one-shot plan。

历史（2026-10-12，9f714a72后的人工剩余额度授权）：**RAW_GRID_COMPLETE / P3比较未完成**。
正式内容`3cc9e0d03ba682569fca0e91f28d364f2dab73fa`、session `f705a488d7b442789973381e2190c944`不变；
外层助手内容`957576ca39689e9b8a723006aeb8177562e1620b`干净导出20项受控测试通过。
一次两区间fresh准入及原Formal门禁通过后，从index5完成余15组，合计20配置/120fresh/40组检查。
旧五组和30条字节前缀不变。测得最低中位数O3/s128为50.996291138秒，CV0.431%、MAD0.229528039秒；
未独立最优复测，未运行Random/Greedy。**O3/s24第5次测量中发生合盖Modern Standby，不能宣称全程连续或稳定。**
本次QPC10313.8951424秒＋旧133.3351975秒＝第二段10447.2303399秒；加首段共24330.2994407秒，
整段休眠计入、不退款、不重置，余3952.7696601秒不构成新的调用授权。所有实验进程已退出。
[本次证据/质量限制/只读入口](evidence/p3_raw_grid/20261012-181149-manual-remaining/README.md)、
[独立验收](evidence/p3_raw_grid/20261012-181149-manual-remaining/window/independent_segment_audit.json)、
[20配置与波动](report.md#811-人工续用剩余额度完成raw-grid9f714a72之后)。

上一轮历史（f19f9f84外审之后）：**RAW_GRID_RESOURCE_BLOCKED / PARTIAL**。
已按授权实现一次性分段续跑助手，辅助内容`7a8dc17f7e268edcea7ff011b56540725ce65af4`，
干净导出15项受控测试通过。原五组和30条样本完整封存，不重跑、不修改冻结归档。
唯一新窗口在Formal预检停止：三次完整采样宿主最低约437/379/302MiB均低于512MiB，
第四次采集被剩余预算中止；新探针/矩阵/配置均0。累计活动包络14016.4042983秒，
不含审核暂停，不用旧controller值冒充整个Grid成本。窗口不可重复领取。
[分段授权、停止原因及只读复核入口](docs/P3_RAW_GRID_SEGMENT.md)、
[分段独立审计](evidence/p3_raw_grid/20261012-144553-segment/window/independent_segment_audit.json)、
[原数据与进程保护核验](evidence/p3_raw_grid/20261012-144553-segment/delivery_verification.json)。

首段已接受结果（历史，不被本次拒绝改写）：
正式RAW内容`3cc9e0d03ba682569fca0e91f28d364f2dab73fa`、新Grid session
`f705a488d7b442789973381e2190c944`。唯一恢复12/12与5组前后10/10 RAW检查通过；
O0五配置完成、30/120次fresh执行有效。O1/s8前宿主内存门禁等待耗尽，停止；余15配置未执行。
已测五项中最低中位数为O0/s128的416.593961898秒，**不是20配置最优**。
未运行Random/Greedy或独立候选复测，P3比较仍未完成；旧成绩不迁移、不校准。
[协议、实际结果、停止原因和只读复核入口](docs/P3_RAW_GRID.md)、
[独立审计](evidence/p3_raw_grid/20261011-021601/final-content/grid_audit_archive.json)、
[交付计数](evidence/p3_raw_grid/20261011-021601/final-content/delivery_summary.json)。

上一轮：**P3_RAW_CLOCK_CANDIDATE_READY**（da0afd87后，2026-10-10/11）。
唯一固定工作量诊断22区间/90响应完整，RAW22/22通过且均落在未加容差的宿主QPC边界内。
MONOTONIC失败索引0/2/7/11/21原样保留。RAW候选运行内容
`3c7a4ab11f7e753936ab8735e03364b44b4dd1ef`，双干净归档80项关联测试（各2项平台跳过）、
CLI/20唯一配置、一次n=17 fresh/289元素及严格整数计时契约通过。
候选协议明确禁止恢复/正式运行；本轮recovery/Formal/4096/Grid/搜索均0，旧session保持空。
这不是正式计时认证或算法比较完成；以后正式比较须同一新协议的fresh Grid。
[候选、身份与成本边界](docs/P3_RAW_CLOCK_CANDIDATE.md)、
[交付摘要](evidence/p3_raw_candidate/20261010-234702-fixed-work/delivery_summary.json)、
[干净验证](evidence/p3_raw_candidate/20261010-234702-fixed-work/clean_validation.json)。

## 历史状态（不以新候选追认旧成绩或失败）

历史50cd24e后唯一原生C/宿主QPC参照诊断已完成30区间：默认A空闲10/10、B忙工作8/10，
syscall空闲及临时绑核空闲各5/5；RAW全部30匹配宿主。B1/B2（零起点）MONOTONIC
真实失配，通信不确定性均≤1.2861ms，不启用新时钟准入，不启动recovery/4096/搜索。
诊断执行内容`7950a8a533f5c60dd8fb7a0d26cb90a3e3d2b32d`；正式d6811cad及空session
2c270825458a4857a5ac9df5aadf597b不变。11项相关回归/干净归档、20配置、二进制复编
身份和10623项历史保护通过，但不代表时钟或正式比较通过。
[方案、全部读数、决定及只读复算入口](docs/P3_CLOCK_REFERENCE.md)、
[本轮独立复算](evidence/p3_clock_reference/20261010-190645-1375f246/independent_diagnostic.json)、
[交付摘要](evidence/p3_clock_reference/20261010-190645-1375f246/delivery_summary.json)。

以下为历史ac33d9d后用户授权内存准入v2，策略本轮原样保留：宿主可用与提交余量各512MiB，宿主低于2GiB警告，
Recovery WSL至少256MiB，Formal仍2GiB；CPU与测量/搜索不变。针对性验证、实际采集及
新内容/新session有限恢复见[P3_MEMORY_POLICY](docs/P3_MEMORY_POLICY.md)。不迁入旧分数或重跑Grid。

该历史轮实际运行内容为 `d6811cadda8ecd7b46225ebe65c51831278694a0`，当时新空session
`2c270825458a4857a5ac9df5aadf597b`。干净归档28项相关单测（1跳过）、CLI/20配置及
n17/O2/s8 fresh逐元素校验通过。唯一recovery资源PASS，但MONOTONIC/RAW **6/20区间失败**，
两个宿主同调用检查通过；来源完整性通过，不具备恢复资格。**Formal未执行、4096执行0、
配置0/24、完整轨迹0/2、候选复测0**。没有第二次recovery，旧成绩不迁移或校准。
[实际独立验收](evidence/p3_memory_policy/20261010-174802-11f7775c/independent_recovery.json)、
[交付摘要](evidence/p3_memory_policy/20261010-174802-11f7775c/delivery_summary.json)。

历史（2026-10-10 16:19，b19e6cd后）：运行内容7405fcc3、既有session3768a29a不变。
唯一一次新recovery调用退出2，宿主内存最低0.722GiB<2GiB，CPU14.6%/27%仅警告。
50项身份通过；时钟区间、Formal门禁、矩阵执行均未开始，新配置0/24、轨迹0/2、复测0。
四项独立验收均false（完整性字段因未生成两个时钟窗口，不是源码哈希损坏）。
停止而不循环重采；历史数据、检查点及暂停标记不变。详见
[当前恢复结论/成本/续跑条件](docs/P3_FIRST_SEED_7405FCC3.md)及
[本批独立验收](evidence/p3_resource_policy/20261010-161312-30f9a2a1-first-seed-7405fcc3/independent_recover.json)。

## 历史：资源策略迁移和e0353bf失败批次

2026-10-10：用户明确授权新 CPU 准入策略：Recovery 超过旧 CPU 阈值只警告，Formal
均值≤30%/单次≤60%；内存/磁盘不放宽，配置启动前门禁等待总预算120秒。
新内容、新归档、新 session/campaign，不拼接旧成绩；C、搜索、输入、容差、计时和评分不变。
策略、迁移、唯一一次20区间验证计划及当前结果见 [P3_RESOURCE_POLICY](docs/P3_RESOURCE_POLICY.md)。
旧 Grid/P3 与以下管理员核验均保留为历史，不能用新门槛追认历史 REJECT。

本轮唯一 recovery 的20区间、两个宿主检查以及随后批前/批后6区间全部通过，来源50/50
匹配，实际新Formal门禁也通过（CPU均值11%）。但e0353bf的campaign内部UNC资源采集
异常退出1，**4096执行0、搜索配置0、轨迹0/2、复测0**，不是CPU或时钟再次拒绝。
已定位并修复进程启动及非UTF8错误处理；最终运行内容为
`7405fcc37074ab815294ba401d5cf5e8280f3d5f`，
[双干净归档验证](evidence/p3_resource_policy/20261010-143415/clean-7405fcc3/summary.json)通过。
修复后的空session `3768a29ade69408da4c5d0c4404ba44e` 不继承旧恢复证明；本轮不再采第二次
recovery。下一轮须外部复核及新的有限验证授权，命令见上述策略文档和
[新session计划](evidence/p3_resource_policy/20261010-143415/corrected_session_plan.json)。

历史 2026-10-10 13:56 管理员处理核验：已保留13:52管理员原始日志，resync有执行
输出，但明确报告“没有可用的时间数据”，操作后及本轮查询仍Leap=3/层次0。
日志中的退出码0及更新的“上次成功同步”字段不构成同步成功证据。内存已恢复：
宿主最低2.537GiB、WSL可用5.789GiB；Formal门禁因CPU平均14.2%>10%拒绝。
因此本轮recovery/resume/新增矩阵执行均0，仍3/24配置、23条原始执行、0/2完整轨迹。
32项冻结SHA及fa59701辅助七文件匹配；只复用既有验证，不重跑28项回归或时钟探针。
[管理员核验/阻塞原因](docs/P3_CLOCK_REPAIR.md)、
[本批独立验收](evidence/p3_clock_repair/20261010-135557/independent_acceptance.json)。
下述12:12集中诊断及10-09记录均保留为历史，不校准旧Grid/P3。

20/20 配置有效，120 次正式执行与 6 次独立复测均通过全矩阵检查。
保留的P2 Grid session测得最低中位数为 **O1/s=128：53.444627760 s**；独立复测为
**54.779446389 s**（+2.50%）。P3 将按五种子、4/8/12预算比较随机与贪心；
当前尚无 P3 完整五种子比较结论。P2 未被标记为外部审计通过。
时钟未独立校准及运行中背景资源扰动限制见
[`docs/P2_TIMING_NOTE.md`](docs/P2_TIMING_NOTE.md) 和 [`report.md`](report.md)。
0023ceed审计修订的独立诊断判据、双归档主控迁移与下一阶段条件见
[`docs/P3_TIMING_AUDIT.md`](docs/P3_TIMING_AUDIT.md)；预算前缀的明确排除项及
失败门禁暂停—成功恢复回归见[`docs/P3_COST_SCOPE.md`](docs/P3_COST_SCOPE.md)。
历史P3曾沿用原e308bfb归档、固定身份和campaign；封存3个完整配置、23条原始执行，
其中旧O0/s8部分组3条已放弃，新部分组2条待重启，均不计配置分数。14:22按暂停
请求安全停止；16:38用户要求继续，批前检查及限定复核发现时钟异常，没有恢复目标。
当时资源门禁PASS不解除时钟阻塞。只限seed=20261008两条轨迹，不扩展五种子。
当前状态、成本及续跑条件见[首种子状态](docs/P3_FIRST_SEED_STATUS.md)。
fdeed77后统一辅助检查和验收，唯一次20区间复核中MONO/RAW全部失败，REALTIME/RAW
另有2项失败；本次宿主内存门禁也拒绝。未启动4096或恢复campaign，状态仍为
**P3_CLOCK_BLOCKED**。[辅助契约v2.1/路径修复](docs/P3_CLOCK_CONTRACT.md)、
[完整复核分析](evidence/p3_clock_contract/20261009-180810-0491a4ec/clock_review_analysis.json)。
最终辅助内容`fa597017c2317772a0f7f34faa75194ffecec8f2`双干净归档74项全套测试
（WSL跳过1项）及Windows旧7/新21项回归通过；
[最终验证](evidence/p3_clock_contract/20261009-180810-0491a4ec/clean-fa59701/summary.json)。
测试通过不代表算法比较完成，也不授权继续尝试探针。原始20区间使用0c6ee7e辅助内容，
后续仅修辅助路径/验收，不替换该来源身份。
此前交付代码从内容`f64d41c1eab21c72e541f91ab7e2dbecf4adfe2b`独立归档验证：
CLI、20唯一配置、53项单测、历史证据核验及Git/实际文件身份检查通过，
[全部命令及结果](evidence/p3/first-seed-clean-f64d41c/summary.json)。不是正式比较PASS。
此前独立审计六组/36次n4096执行全部通过；两轮观察排名O1→O3→O2，但相邻差距
不足2%且有资源警告，**不满足先验稳定排名判据**。该次时钟对照通过不校准旧数据。
诊断主循环39分29秒，正式P3比较仍未完成，下一阶段命令和裁决条件见上述审计说明。

## 当前状态

- 老师原件保持不变：SHA-256
  `188d011109c4470e1f41829216e8677a5c2d8f2b7c8a44215652320dbdf6de15`。
- 正式工作副本默认 `n=4096`，固定输入规则和种子，单调时钟只计核心计算，计时区外
  逐元素验证并输出严格 JSON。
- `ConfigSpace`、`TargetAdapter`、`Evaluator` 已实现；构建、reference 和性能缓存分离。
- `ConfigurationEvaluator` 是三种搜索的统一配置测量接口：一次成功预热和五次
  强制新执行，取核心时间中位数；任意失败不计分。Grid、无放回随机、随机重启贪心
  均已实现，贪心每点七个单参数邻居，预算单位是唯一配置。
- P2 修复了非零退出搭配成功 JSON 仍可能计分的问题，并核对请求身份、n² 全量检查
  和冻结容差。从内容提交 `0d3dd5242c728d8001dd02a4e332185459d04721` 的无 Git/
  字节码缓存归档完成 31 项单元测试、160 个小规模正确性案例、7 类故障、6 类非法
  输入及 n=130 三策略实际链路（20/8/8 个配置）。证据见
  [`evidence/p2/validation-final/`](evidence/p2/validation-final/)。
- 最终交付内容提交`c2a964162915b8cf0019df4e73bcd7cd634d1902`另从干净归档复验，
  独立空缓存完成同样的全部检查，n=17为fresh且正确性通过、n=130三策略20/8/8通过；
  全部Python源码AST及归档内完整Grid证据审计通过。见
  [`evidence/p2/validation-delivery/summary.json`](evidence/p2/validation-delivery/summary.json)。
- P1 初次提交的 `.gitignore` 中 `core.*` 误忽略了本地实际使用的
  `autotuner/core.py`。R1 已恢复该文件、收窄规则，并从内容提交
  `bd9b7d264c42f7c65cd22b16a64a4a0f9c119c5f` 的无 `.git` 归档完整验证。
- `n=129/130` 的 160 个配置/输入案例全部通过；7 类故障注入和 6 类非法参数全部
  被正确拒绝。
- 默认规模四级代表配置成功；O3 代表配置五次核心时间中位数 `78.789159 s`，CV
  `1.10%`。这些 pilot 对应 R1 前本地实现且资源受限，仅保留为历史诊断数据，不是
  正式 Grid 数据；R1 没有重跑 `n=4096`。

## 复现与检查

主要命令在 WSL Ubuntu-24.04、GCC 13.3.0 下运行：

```bash
cd /mnt/e/software_system/project01
python3 -m unittest discover -s tests -v
python3 scripts/verify_p1.py
python3 -m autotuner list-configs
```

R1 的干净归档验收结果、逐命令 stdout/stderr/退出码和源码哈希位于
[`evidence/p1_revision1/`](evidence/p1_revision1/)。其中还实际确认移除 `core.py` 后
`verify_p1.py` 非零退出、`n=17/O2/s=8` 为 `fresh_measurement`，以及 `n=1/2`
reference 的 ASan+UBSan 边界检查。

完整小规模正确性会运行 160 个案例：

```bash
python3 scripts/run_p1_correctness.py
```

默认规模 pilot 很慢，且脚本会先检查资源；仅在需要复现实验、确认时间预算后运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/check_p1_resources.ps1 `
  -OutputPath evidence/p1/environment/pre_default_gate_new.json
wsl.exe -d Ubuntu-24.04 -- bash -lc `
  'cd /mnt/e/software_system/project01 && python3 scripts/run_p1_pilots.py --resource-gate evidence/p1/environment/pre_default_gate_new.json'
```

## 文档入口

- [`docs/P3_PROTOCOL.md`](docs/P3_PROTOCOL.md)：P3 批次、私有观测、复测和比较指标。
- [`docs/P3_AUDIT_HANDOFF.md`](docs/P3_AUDIT_HANDOFF.md)：P3 执行状态与审计入口。
- [`docs/P2_PROTOCOL.md`](docs/P2_PROTOCOL.md)：P2 冻结协议、资源条件与续跑规则。
- [`docs/P2_AUDIT_HANDOFF.md`](docs/P2_AUDIT_HANDOFF.md)：本轮审计及正式证据入口。
- [`docs/P1_FOUNDATION.md`](docs/P1_FOUNDATION.md)：设计、验证、试跑、协议和成本。
- [`docs/P1_AUDIT_HANDOFF.md`](docs/P1_AUDIT_HANDOFF.md)：审计索引与待裁决事项。
- [`docs/WORK_LOG.md`](docs/WORK_LOG.md)：实际操作、失败和修复。
- [`report.md`](report.md)：仅纳入已有证据的课程报告正文。
- [`docs/P0_DISCOVERY.md`](docs/P0_DISCOVERY.md)：保留并纠正后的 P0 基线。

## P2 正式证据与复现

正式内容提交固定为 `0d3dd5242c728d8001dd02a4e332185459d04721`，后续提交仅整合
证据、辅助复核与文档，不替换实验身份。原始样本、20 行统计、独立复测和完整性审计：

- [`evidence/p2/grid-session-0d3dd52/summary.json`](evidence/p2/grid-session-0d3dd52/summary.json)
- [`evidence/p2/grid-session-0d3dd52/grid_summary.csv`](evidence/p2/grid-session-0d3dd52/grid_summary.csv)
- [`evidence/p2/grid-session-0d3dd52/independent_retest.json`](evidence/p2/grid-session-0d3dd52/independent_retest.json)
- [`evidence/p2/grid-session-0d3dd52/evidence_audit.json`](evidence/p2/grid-session-0d3dd52/evidence_audit.json)
- [`evidence/p2/postprocessing/`](evidence/p2/postprocessing/)：绘图命令、版本、哈希和成本核算。

记录的活动会话耗时 6 h 38 min 28 s，其中资源门禁/等待约 35 min 54 s；关机前未完成
执行只有 325 s 最后观测下界，精确成本未知。该耗时来自单调时钟，不等于已校准物理时间。

正式协议为 n=4096、random、seed=20261008；宿主与 WSL 都至少 2 GiB 可用，
根目录至少 1 GiB，宿主 CPU 五次采样平均不超过 10%、单次不超过 20%。
资源不满足时不启动下一个配置；不修改系统设置或终止其他应用。

先在 PowerShell 导出指定内容提交（不要用最终证据提交代替内容提交）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/prepare_p2_content.ps1 `
  -ContentSha 0d3dd5242c728d8001dd02a4e332185459d04721
```

以下是已经实际使用的暂停续跑入口；当前 session 完整，不需要新增正式运行。
若复核续跑，必须保留 WSL 本地 cache，并由运行器核对内容、
编译器、二进制、输入、reference 及协议身份；已完成配置只从该 session 的全部
原始样本恢复。中断配置重新预热和五次测量，不使用性能缓存凑样本。

```bash
cd /var/tmp/matrix-autotuner-p2-content-0d3dd5242c728d8001dd02a4e332185459d04721
PYTHONDONTWRITEBYTECODE=1 env -u PYTHONPATH python3 -m autotuner grid \
  --content-sha 0d3dd5242c728d8001dd02a4e332185459d04721 \
  --git-identity /mnt/e/software_system/project01/build/p2/git_identity.json \
  --session-directory /mnt/e/software_system/project01/evidence/p2/grid-session-0d3dd52 \
  --resume
```

完整性复核（不启动目标性能实验；省略 `--output` 不写审计结果文件）：

```bash
cd /mnt/e/software_system/project01
PYTHONDONTWRITEBYTECODE=1 env -u PYTHONPATH python3 scripts/audit_p2_evidence.py \
  --session evidence/p2/grid-session-0d3dd52 --require-complete
```

使用上述内容归档重新进行小规模干净检查时，须另用空证据目录；脚本自行建立临时空缓存：

```bash
cd /var/tmp/matrix-autotuner-p2-content-0d3dd5242c728d8001dd02a4e332185459d04721
PYTHONDONTWRITEBYTECODE=1 env -u PYTHONPATH python3 scripts/run_p2_clean_validation.py \
  --content-sha 0d3dd5242c728d8001dd02a4e332185459d04721 \
  --git-identity /mnt/e/software_system/project01/build/p2/git_identity.json \
  --output /var/tmp/matrix-p2-clean-check-new
```

图表可在 Windows 已安装的 Python 3.12.6、matplotlib 3.10.6、numpy 2.3.3 下重建：

```powershell
python scripts/plot_p2_results.py --session-directory evidence/p2/grid-session-0d3dd52 --output-directory assets
```

CPU 平均≤10%/单次≤20%是**配置开始前的后台负载门槛**，不是限制矩阵程序使用 CPU。
它减少调度、缓存、带宽和频率/温度变化的干扰；不是老师要求或通用标准，运行中快照也
不保证资源一直稳定。本轮不因结果改变冻结门槛或事后筛除样本。

## P3 批次入口

`python3 -m autotuner campaign --help` 展示 P3 正式/诊断运行参数。正式运行必须先
提交内容并通过 `scripts/prepare_p2_content.ps1 -ContentSha <完整内容SHA>` 导出，
沿用导出器的历史 `p2-content-<SHA>` 名称但实际内容绑定 P3 SHA。在该干净归档目录
中运行，Git 身份文件是导出器生成的 `build/p2/git_identity.json`：

```bash
PYTHONDONTWRITEBYTECODE=1 env -u PYTHONPATH python3 scripts/run_p3_clean_validation.py \
  --content-sha <完整内容SHA> --git-identity <导出器身份JSON绝对路径> \
  --output <新的小规模验收证据目录>
PYTHONDONTWRITEBYTECODE=1 env -u PYTHONPATH python3 -m autotuner campaign \
  --content-sha <相同内容SHA> --git-identity <相同身份JSON路径> \
  --campaign-directory <P3正式证据绝对目录> --trajectory-limit 2
```

默认先做首种子的两条完整轨迹；将 limit 增大至 10 并加 `--resume` 可继续冻结顺序。
当前这些占位命令是接口说明，不是已经执行的正式命令；实际内容 SHA、参数和输出
由验收/实验日志记录。安全暂停和完整恢复规则见 P3_PROTOCOL。

P3实际内容提交为 `e308bfb873e6811c50ad685a979af345302fda8d`。40项单测、n17 fresh、
n130十条诊断轨迹（834次目标新执行）和部分组暂停重测通过，
见[干净验收摘要](evidence/p3/validation-e308bfb/summary.json)。正式批次使用独立固定
Git身份，不依赖将来会被导出器覆盖的通用身份文件；当前范围与实际续跑命令见
[P3审计入口](docs/P3_AUDIT_HANDOFF.md)。所有P0/P1/P2历史证据保持原身份。

2026-10-09 02:24自动暂停时已保存2/24首批配置（完整计划2/120次轨迹内配置评估）、
12条完整目标执行；当前没有仍在运行的P3目标。10:12只读复查宿主最低可用内存
454094848字节（约433MiB），仍未达到2GiB门槛，WSL/CPU/磁盘条件通过。
先恢复宿主可用内存，再使用审计入口中固定身份的`--resume`命令；不要重建session或
用单次缓存拼重复。P3尚非完整交付，不能据此比较算法或五种子稳定性。

10:40正式门禁恢复PASS：宿主最低可用约5.70GiB、WSL约3.90GiB、CPU平均4.4%/
最大16%、AC电源在线。用户要求继续后，使用原e308bfb归档、固定身份和同一session
执行`--trajectory-limit 2 --resume`；两完整组核验后保留，10:42:55第三配置O3/s16
已开始预热。见[恢复证据](evidence/p3/resume-20261009-104020/restoration.json)。
上述02:24/10:12段落是历史暂停快照，不冒充本次状态；完整P3比较尚未完成。

此前审计基点`0023ceed`，在已推送的55b776b历史上继续。P3安全暂停后保留3个完整
配置及O0/s8的3条部分样本（合计21次执行）。[本轮诊断判据与入口](docs/P3_TIMING_AUDIT.md)、
[前缀成本范围](docs/P3_COST_SCOPE.md)。这是历史暂停状态；本次用户以e46b96c授权
沿用协议恢复，显式`--resume`已留存并清除原PAUSE_REQUEST。两轮s128复测仍是独立
诊断，不是Grid扩展或搜索观测。
