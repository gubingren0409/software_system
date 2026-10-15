# 2026-10-15下午：一次明确重试在接电前检停止

状态 **P3_RAW_VALIDATION_AC_POWER_BLOCKED**。当前不是内存/CPU/时钟失败，也没有补齐第三组。
基点6b1860aae12daba654c6ed313f43928811da09db，用户再次“重试”，仅授权一次原余量尝试。
新外层内容103387cfae82523d9ad42bf4567af42cc2239337，准确归档
`C:/Users/28489/AppData/Local/Temp/raw-validation-retry2-103387c`；工作树与干净归档各15项相关回归通过。
实际测量保持35a60b090b728d2ec3b6a8ea014beac69fe3766d、session9332ead2881a4c1e91b966e90a0d2057。
矩阵/输入/reference/容差/20配置/RAW计时/资源v2与搜索均未改，原两组不重跑。

[采集前授权](continuation/authorization.json)绑定两次旧拒绝的授权/claim/窗口链，新的独占retry-v2 claim
不覆盖旧claim。原846.073676+200.0468689+211.7102998=1257.8308447s照计，本次仅2342.1691553s。
保护287个原session文件、13,545个其他历史证据及两组/12条字节前缀，旧Grid和空搜索session保持。
[预声明](stage_plan.md)、[当前规则及迁移](../../../docs/P3_RAW_VALIDATION_CONTINUATION.md)。

## 实际停止证据

E盘写/fsync/read-back通过。临时防睡眠申请成功，随后Windows GetSystemPowerStatus报告
`ok=true, ac=0, battery_percent=75`，接电子检查退出2，外层同样退出2。
[AC原始stdout](continuation/ac_status.stdout.txt)、[完整命令/时间/QPC/退出码/哈希](continuation/ac_status.operation.json)、
[停止窗口](continuation/window.json)、[同线程finally释放](continuation/sleep_request.json)。
窗口stopped/preflight，未绕过接电要求，未修改电源、NTP/内核/WSL或终止用户应用。

本轮Recovery/Formal资源门禁、short/long准入、组前后检查全部**未执行**，新探针0、新矩阵0，
不填PASS/REJECT或编造当前内存读数；没有准入证书。旧11区间仍只是历史证据，不冒充本轮通过。
仍2/3组、12/18fresh（2预热/10测量），active=null，checkpoint原字节ready，矩阵部分/放弃样本0。
s24六次未执行，搜索/前缀复测/reference生成0。s128仍51.602724641s、s64仍52.784908609s。
原教师C/既有分数/失败片段/暂停状态和全部旧claim保留，不重置预算、不重试到通过。

## 独立验收与辅助修复

[原冻结辅助审计](continuation/independent_continuation_audit.json)真实退出2，因尚未进入资源阶段而缺
admission_resources/gate_manifest.json，给出integrity=false。原结果/命令/日志原样保留，不改写为PASS。
这暴露了辅助审计器对早期接电拒绝的阶段适用限制，不是新时钟或正式测量失败。

[单独接电拒绝核验](continuation/independent_preflight_stop_audit.json)由
[只读后处理](summarize_continuation.py)生成：复用冻结helper的授权/保护/预算验证、原运行器数据审计、
checked_operation的原始流SHA与整数QPC，核对真实AC退出/类型/范围、操作与窗口绑定、未启动阶段目录缺席
以及防睡眠释放；不调用资源/时钟/目标，不生成恢复证书，不替换原辅助审计结果。
源码SHA与原始命令在结果及operations中。3项新增合成回归覆盖合法拒绝、无效/非有限值、
错误退出/超时/阶段/QPC绑定，未产生任何实验执行。

来源/原始数据/保护的evidence_integrity_pass=true；resource_status/clock_status=not_executed。
validation_complete/validation_timing_checks_pass=false；P3 execution_complete/timing_checks_pass/comparison_ready均false。
Formal/准入字段为null而非PASS；[最终摘要](delivery_summary.json)、[来源/行尾](source_identity.json)、
[样本契约](all_sample_contracts_independent.json)、[三配置派生表](three_configuration_comparison.csv)。
本轮派生表纠正组级timing_contract_pass不应套用“全三组完成”标志：两已接受组依其原始证据通过，
全验证仍未完成。历史派生表不覆盖，分数/样本均不改。

## 成本和下一步

[成本](costs.json)：本段3.2553424s，加原1257.8308447s＝1261.0861871s，账面余2338.9138129s。
四个包络分别以QPC整数相减后求和，不跨epoch、不退款、不再获得3600秒。
本段进程12.8550992s包含启动身份核查、活动及最终记录，不与活动相加。
本轮资源/探针/测量成本0；旧414.1561236s门禁、125.3838414s探针、650.83599454s配置RAW及
633.229610487s核心均为历史活动内含项，不重复累加。离线准备/审计/Git另外记录，不虚构人工总耗时。

所有真实命令/stdout/stderr/退出码见[operations](operations/)。fetch一次TLS握手失败退出128，已保留，
GitHub API已确认基点，未降低TLS校验；普通推送及远端SHA在终端交接中核实。
最终文件/链接/原件/执行源码/进程检查见final_checks.json。

本轮停止，不再调用run。下一步需要用户先接通电源、保持开盖，再明确一次剩余额度尝试；
仍只补s24六次，按原资源门禁及一次fresh准入，不启动搜索或新Grid。
