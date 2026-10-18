# 2026-10-18人工单次重试：P3_RAW_VALIDATION_RESOURCE_BLOCKED

起点project01/9d27143362f7e9cdb7bc1295c3724df160c13b46，工作区原本干净；fetch github成功，
API核对同基点。只补旧验证的O3/s24，不启动Random/Greedy、Grid、其他种子或额外n17。
用户本轮“重试”仅授权一次尝试，失败即停。本次已停止，不能重复调用本次claim。

## 身份与验证

- 实际测量内容：35a60b090b728d2ec3b6a8ea014beac69fe3766d。
- 原科学测量内容：3cc9e0d03ba682569fca0e91f28d364f2dab73fa。
- 原验证session：9332ead2881a4c1e91b966e90a0d2057；计划未改，见[授权](continuation/authorization.json)。
- 新外层辅助内容：02907787f09ee94922d159e6b6bb9a0203c6bde5；准确三文件归档位于
  `C:/Users/28489/AppData/Local/Temp/raw-validation-retry3-0290778`。
- 外层仅增加已关闭AC拒绝的授权/成本链接及独占retry-v3 claim；未修改原归档、C源码、协议或阈值。
  16项相关受控回归在工作树及干净归档各通过，另3项合成AC拒绝核验通过；无C测试目标调用。
- 本轮WSL内核仍为6.18.54.1-microsoft-standard-WSL2；归档模块、源码、编译器、构建和reference缓存
  核验成功，未执行setup或生成reference。性能分数没有复用。
- [执行字节SHA、Git内容身份及行尾](source_identity.json)；源码/测试要求字节一致，非执行文档单列CRLF差异。

## 实际执行与停止

运行前和运行时API均确认AC=1、电量100%。临时防睡眠同线程finally释放；未修改系统电源配置，
此请求不保证阻止用户合盖。Formal预检首个快照通过：宿主最低4071182336B、提交余量36704141312B、
WSL可用6228447232B，CPU平均3.6%、最高6%；无资源警告。

唯一fresh准入为默认libc、不绑核的10亿次、100亿次固定更新，2/2 RAW通过，10条响应。
两区间RAW保守范围均在未加容差的宿主QPC范围内，端点和来源独立复算通过；未补采、筛选或校准。
这不能追认历史Grid的内部连续性或修复历史MONOTONIC问题。

随后s24组前资源attempt `4ac0ce3795a14103b1f041a051e2ec5f` 的四个有效快照均只因host_memory拒绝：

| 快照 | 宿主最低可用bytes | WSL可用bytes | CPU平均/最高% |
|---|---:|---:|---:|
| 0 | 281374720 | 4903395328 | 4.8 / 10 |
| 1 | 325533696 | 6224891904 | 1.8 / 4 |
| 2 | 429780992 | 6229106688 | 11.2 / 16 |
| 3 | 474804224 | 6166638592 | 14.4 / 23 |

均低于冻结512MiB门槛，提交余量/WSL/CPU/根盘通过；四个采集退出2、均非超时。
门禁118.9061907秒，在原120秒上限内拒绝。控制器真实退出2；没有组前/后新探针、READY或新矩阵执行。
本轮目标0次、reference生成0次；session仍2/3组、12/18fresh（2预热+10计分），部分/放弃矩阵样本0。
原持久化checkpoint仍ready/active=null且字节一致；外层stopped才是本次停止状态，不伪写完成。

一次同等待窗口的[只读占用快照](operations/host_occupancy.stdout.txt)显示宿主可用334102528B、
VmmemWSL工作集5230096384B；分页速率5611/s、page reads1059/s。它是质量证据，不证明唯一根因，
不能把整个Vmmem工作集加到可用容量，也不能声称WSL预占已证实。部分非ASCII进程名由旧PowerShell
编码输出，原字节保留，名称不可可靠解读；未据此归因、结束应用或重采。

## 独立验收与历史保护

[独立辅助审计](continuation/independent_continuation_audit.json)：evidence_integrity_pass=true，
validation_complete=false、validation_timing_checks_pass=false；其退出2表示未完成，不是整体PASS。
Formal预检及fresh准入通过，组Formal明确拒绝。P3 execution_complete/timing_checks_pass/comparison_ready
全部false，真实搜索轨迹/预算前缀复测仍0。

289个原session文件、13,618个其他证据、原两组分数、12条run_id/字节前缀、初始证书/窗口/claim、
关闭Grid及待机样本全部保护。两组旧中位数51.602724641s、52.784908609s不变；s24仍未执行。
本轮只生成新的派生[三配置旁列表](three_configuration_comparison.csv)，不覆盖旧表或挑选较小值。
历史门禁超出0.0005393秒及旧空stdout错误继续保留为拒绝，不用新结果改标PASS。

## 成本及入口

先前四段1261.0861871s全计费；本段活动QPC207.9839123s，累计1469.0700994s，原3600s余2130.9299006s。
每段整数端点相减后求和，不跨epoch。外层本段进程包络218.5935365s包含活动及身份/收尾；
门禁/探针/组评估RAW/核心为嵌套分项，不与活动包络再相加。离线准备、单测、Git、审计独立列在operations。
账面余量不是自动再次运行许可，不删除旧claim或重置预算。本轮不再恢复或启动搜索。

- [采集前范围/停止规则](stage_plan.md)、[保护快照/来源/预算授权](continuation/authorization.json)
- [真实停止窗口](continuation/window.json)、[防睡眠释放](continuation/sleep_request.json)
- [本次fresh准入原始流](continuation/admission/)、[独立准入复算](continuation/independent_continuation_admission.json)
- [全部资源门禁复算及历史错误](all_resource_gates_independent.json)、[13区间RAW复算](all_clock_checks_independent.json)
- [12条样本严格结果契约复算](all_sample_contracts_independent.json)、[成本](costs.json)、[交付摘要](delivery_summary.json)
- [真实命令/输出/退出码](operations/)、[最终保护/链接/进程检查](final_checks.json)

首次最终链接检查在写出自身结果前发现该自引用文件尚不存在，退出1；
[首次原结果](final_checks.initial.json)保留。结果文件生成后再做只读交付检查，不重复实验。

下一步先由用户释放宿主内存并保持接电开盖，再明确一次仅使用2130.9299006s原余量的补s24授权。
需重新验证资源和fresh准入；当前已关闭claim不可重复run。旧两组/旧Grid/所有失败仍不得改写。
