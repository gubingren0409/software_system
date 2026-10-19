# P3_RAW_THREE_CONFIG_VALIDATION_COMPLETE（2026-10-19）

用户再次“重试”，仅补O3/s24；本轮已完成并停止，不运行Random/Greedy、其他种子、Grid或额外复测。
起点project01/aac44ef791454ff2263d9834f09c396f3a944733，原工作区干净，fetch及GitHub API核对成功。

## 固定身份

- 实际测量内容：35a60b090b728d2ec3b6a8ea014beac69fe3766d。
- 沿用科学内容：3cc9e0d03ba682569fca0e91f28d364f2dab73fa。
- 原验证session：9332ead2881a4c1e91b966e90a0d2057，原计划及初始证书不改。
- 新辅助内容：e8816554b3b9208b0ab4aa00d9adc96b0f692505；准确三文件归档
  `C:/Users/28489/AppData/Local/Temp/raw-validation-retry4-e881655`。
- 辅助仅扩展一次retry-v4授权链、原成本及独占claim；C、矩阵循环/输入/reference、资源v2、RAW、
  搜索算法和1预热+5fresh/中位数规则未改。科学模块仍从准确35a60b0归档运行。
- 17项相关受控回归在工作树及干净归档均通过，另3项合成AC拒绝核验通过；无额外n17或历史全套测试。
  [执行字节SHA/Git身份/行尾/协议/编译器](source_identity.json)，文档CRLF差异与执行字节分别记录。

## 实际执行

初步AC=1/52%，运行时AC=1/56%；临时防睡眠在同线程finally释放，不保证阻止用户合盖。
内核仍6.18.54.1-microsoft-standard-WSL2，源码/四候选/编译器/reference缓存逐SHA核验，跳过setup，
reference生成0、性能缓存复用0。新attempt `817ed02f95d74bbd8f03877b8e6a0a77` 只处理O3/s24。

Formal预检host最低4321181696B、WSL可用6236139520B、CPU平均8%/最高12%，通过且无警告。
组前Formal最低host648581120B（约619MiB）、WSL4907397120B、提交余量35466522624B、
CPU平均6.4%/最高10%，通过但保留host低2GiB警告。门槛未放宽，准入通过不证明环境无干扰。

唯一fresh短/长准入2/2 RAW通过；组前/后各1短区间通过，本轮共4区间/22响应，原始流完整保留。
17个历史及本轮区间独立复算均RAW通过，不能据此校准旧Grid或消除历史失败。
默认libc、不绑核；整数端点、QPC边界、20ms不确定性/读取跨度及5ms+1%U判据不变，无筛选/补采。

s24完整1预热+5fresh共6次新增目标执行，全部returncode0、全16777216元素正确、RAW契约通过。
本组五测量中位数63.240102045s，均值63.2280261924s，样本标准差0.318748303184s，
CV0.5041250255%，MAD0.273363999s。历史Grid66.249431562s原样保留，新旧变化−4.5424231515%，
不替换原分数、不挑较小值、不按待机退款。完整[三配置旁列表](three_configuration_comparison.csv)。

同范围组QPC387.9632797s、RAW387.957298023s，差0.005981677s，未达到30s连续性拒绝阈值；
System RecordID352983→352985的原始消息/XML经冻结检查，没有组内待机，uninterrupted_execution=true。
组评估器内部RAW387.918638421s是更小的嵌套范围，不能直接拿它替代外层同范围比较或累加。

后处理时一次[宿主快照](operations/after_host_occupancy.stdout.txt)可用6126317568B、
VmmemWSL工作集1658204160B，分页速率49787/s、page reads669/s；
[WSL完整meminfo](operations/after_wsl_meminfo.stdout.txt)MemAvailable6052056KiB，SwapTotal/Free均2097152KiB。
这些是较晚快照，不证明组内无分页/压力，不追认旧REJECT，更不证明WSL预占假说或唯一因果。
未结束用户应用、清系统缓存、重启WSL或改系统设置。

## 独立验收与保护

[独立审计](continuation/independent_continuation_audit.json)退出0：
evidence_integrity_pass=true、validation_complete=true、validation_timing_checks_pass=true。
3/3组、18/18fresh（3预热+15测量）、18个唯一run_id；部分/放弃目标样本0，reference生成0。
随机/贪心轨迹、搜索配置和前缀复测均0，因此P3 execution_complete/timing_checks_pass/comparison_ready仍false。

306个原session文件、13,711个其他证据、原两组/12条字节前缀/旧claim/证书/窗口与原件全部保护。
samples.jsonl只追加6条，checkpoint由原运行器更新为complete、active=null；没有手改分数/状态。
旧E满盘片段、REJECT、超时及关闭Grid/待机样本全保留。历史空stdout及0.0005393秒超额门禁继续拒绝。
两组在10月14日、s24在10月19日完成，**不是连续批次或严格同环境因果对照**；不宣称新20配置全局最优。

## 成本、证据与下一步

先前五段1469.0700994s全部计费；本段活动514.3688049s，六段合计1983.4389043s，原3600s余1616.5610957s。
本段进程包络527.3836979s包含活动和活动前身份/收尾，不与活动相加。原窗口saved qpc_end为权威，
不使用稍后progress快照替代。只对各自QPC整数端点相减后求和，不跨epoch相减。
累计已接受组评估RAW1038.754632961s、全部核心（含预热）1013.196641225s、门禁/探针均是嵌套分项，
不得再叠加到活动包络；准备、单测、Git、后处理、较晚资源快照属离线辅助成本，真实命令分别留档。
三配置验证到此关闭，余量不转移给搜索，也不再追加或重跑已完成组。

- [采集前范围/停止规则](stage_plan.md)、[授权/全部保护SHA/原快照](continuation/authorization.json)
- [停止窗口](continuation/window.json)、[防睡眠释放](continuation/sleep_request.json)、[原始命令/输出/退出码](operations/)
- [fresh准入原始流](continuation/admission/)、[独立准入](continuation/independent_continuation_admission.json)
- [全部RAW区间复算](all_clock_checks_independent.json)、[全部门禁/历史错误](all_resource_gates_independent.json)
- [18条严格结果契约](all_sample_contracts_independent.json)、[成本](costs.json)、[交付摘要](delivery_summary.json)
- [最终保护/链接/敏感信息/进程检查](final_checks.json)、[后续成本场景](search_budget_scenarios.json)

后续需外审本轮、低内存警告及跨日范围后，另行授权新search session/fresh准入和独立固定预算。
历史中位数×6的均匀无放回12配置成本先验约12279s/轨迹，两轨迹约6.82h纯核心；贪心不假设均匀。
保留43200s（12h）后续QPC活动总上限建议，包含24搜索组、至多6去重候选组、门禁/探针/收尾，
耗尽即PARTIAL，不承诺必完成、不重置。慢配置/候选场景可能超过该上限，详见JSON；这些不是搜索观测。
