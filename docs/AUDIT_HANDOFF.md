# 审计交接入口

当前（3755c4a外审后）：正式RAW Grid v1衔接修复和采集前冻结；尚未执行recovery/4096。
本轮只授权一次fresh恢复及新20配置Grid，不运行Random/Greedy。
[新阶段方案](P3_RAW_GRID.md)、[本轮原始操作入口](../evidence/p3_raw_grid/20261011-021601/)。
最终结果、内容SHA、新空session和独立验收在实际执行后更新。

已冻结运行内容 `3cc9e0d03ba682569fca0e91f28d364f2dab73fa`，
空Grid session `f705a488d7b442789973381e2190c944`；
[精确身份/归档](../evidence/p3_raw_grid/20261011-021601/final-content/plan.json)、
[110项双干净回归/一次n17/20配置/空初始化](../evidence/p3_raw_grid/20261011-021601/final-content/clean_validation.json)。
110测试各适用项通过，Windows/WSL分别2/3平台跳过。n17实际矩阵1/reference1，初始化二者0；
目前恢复/4096/正式搜索仍0，下一步唯一一次fresh恢复。

## 历史RAW候选交付（已获本轮外审接受）

历史：**P3_RAW_CLOCK_CANDIDATE_READY**，基于da0afd87，完成唯一22区间固定工作量诊断及
最小RAW候选，不执行恢复或正式实验。预声明内容a4982632ae9640001876c45dcba1cee581e07754；
候选执行内容 `3c7a4ab11f7e753936ab8735e03364b44b4dd1ef`，最终交付提交只补证据、文档
及收尾验证辅助脚本，不替换候选归档或写入旧session。
RAW22/22匹配（连未加容差边界也全部通过），MONOTONIC失败索引0/2/7/11/21保留。
双干净归档80项关联回归（各2项跳过）、CLI/20配置、一次n17 fresh及289元素/整数契约通过。

优先审计：

- [方案、候选协议、超时/成本时钟清单与范围](P3_RAW_CLOCK_CANDIDATE.md)
- [采集前manifest/源码/编译/二进制身份](../evidence/p3_raw_candidate/20261010-234702-fixed-work/manifest.json)
- [全部22区间](../evidence/p3_raw_candidate/20261010-234702-fixed-work/intervals.jsonl)、[90响应/宿主整数QPC](../evidence/p3_raw_candidate/20261010-234702-fixed-work/messages.jsonl)
- [独立复算](../evidence/p3_raw_candidate/20261010-234702-fixed-work/final_independent_diagnostic.json)、[分条件分析/未知原因](../evidence/p3_raw_candidate/20261010-234702-fixed-work/diagnostic_analysis.json)
- [干净内容计划](../evidence/p3_raw_candidate/20261010-234702-fixed-work/clean_plan.json)、[源码Git/执行字节与小矩阵独立审计](../evidence/p3_raw_candidate/20261010-234702-fixed-work/candidate_validation.json)
- [首次拒绝及身份清单修正（未改源码或重跑）](../evidence/p3_raw_candidate/20261010-234702-fixed-work/identity_selection_correction.json)
- [10760项历史保护](../evidence/p3_raw_candidate/20261010-234702-fixed-work/history_protection_after.json)、[三个campaign保护](../evidence/p3_raw_candidate/20261010-234702-fixed-work/campaign_protection.json)
- [实际操作退出码和流哈希](../evidence/p3_raw_candidate/20261010-234702-fixed-work/operation_verification.json)、[成本包含关系](../evidence/p3_raw_candidate/20261010-234702-fixed-work/costs.json)、[交付计数/状态](../evidence/p3_raw_candidate/20261010-234702-fixed-work/delivery_summary.json)

证据完整性true、候选参考匹配true、候选验证true；正式执行/时钟检查/比较就绪均false。
recovery/Formal/4096/Grid/搜索0；d6811cad/session2c270825458a4857a5ac9df5aadf597b保持空，
旧e308bfb的3完整/23原始及5部分执行状态不动，无任务拥有的实验进程。
待裁决：仅认证本轮RAW跨域一致性，尚非物理精度保证/正式准入；candidate-only恢复入口
当前明确拒绝。未来新准入需独立授权、fresh宿主/RAW证据、新session及同协议fresh Grid。
根因未知不应虚构解释；旧失败仍失败，不筛选、不比例校准，不移用旧证书。

## 历史交接（原结论及失败完整保留）

历史入口为50cd24e后的**唯一原生C/宿主QPC有界参照诊断**：
[P3_CLOCK_REFERENCE](P3_CLOCK_REFERENCE.md)、[首种子状态](P3_FIRST_SEED_STATUS.md)。
执行源码先提交为7950a8a533f5c60dd8fb7a0d26cb90a3e3d2b32d，30区间/96响应完整；
A默认空闲10/10、B默认忙工作8/10、C/D各5/5匹配宿主，RAW30/30匹配。
B1/B2（零起点）MONOTONIC失配且边界清晰，按第3决策阻塞，不启用新准入。
Formal门禁/recovery/4096/搜索均未执行，不新增session或成绩。正式d6811cad/session
2c270825458a4857a5ac9df5aadf597b仍为空；内存/CPUv2及正式C/测量/搜索协议不变。

验收为evidence_integrity_pass=true、reference_match_pass=false、execution_complete=false、
timing_checks_pass=false、comparison_ready=false。11项相关回归、准确提交干净复验/CLI/
20唯一配置/探针二进制哈希通过；10623项旧文件、51项正式归档、旧23条执行/ID及暂停标记保护通过。
测试通过不是正式比较完成，旧6失败保持，当前无实验进程。

优先审查：

- [先声明manifest/协议/来源](../evidence/p3_clock_reference/20261010-190645-1375f246/manifest.json)
- [全部30原始区间](../evidence/p3_clock_reference/20261010-190645-1375f246/intervals.jsonl)、[96条原始通信](../evidence/p3_clock_reference/20261010-190645-1375f246/messages.jsonl)
- [独立重算](../evidence/p3_clock_reference/20261010-190645-1375f246/independent_diagnostic.json)、[30行秒单位表](../evidence/p3_clock_reference/20261010-190645-1375f246/interval_summary.csv)
- [交付计数/状态](../evidence/p3_clock_reference/20261010-190645-1375f246/delivery_summary.json)、[干净验证](../evidence/p3_clock_reference/20261010-190645-1375f246/clean_validation.json)
- [最终流哈希/链接核验及4条被拒绝的初次辅助记录](../evidence/p3_clock_reference/20261010-190645-1375f246/delivery_verification.json)
- [旧文件保护](../evidence/p3_clock_reference/20261010-190645-1375f246/history_protection_after.json)、[保留正式身份](../evidence/p3_clock_reference/20261010-190645-1375f246/retained_identity.json)、[成本与包含关系](../evidence/p3_clock_reference/20261010-190645-1375f246/costs.json)

待裁决：默认C忙工作异常的下一轮受控定位/环境方案；当前不能以C/D空闲通过归因
于vDSO或迁移，也不能将MONO/REALTIME一致当作证明。诊断参照仅跨域一致性，不保证
物理准确。只读复算命令见上述文档；本轮不再采样或resume，等待外审。
完整性true限实际诊断/来源/保护及可靠v2验证；首轮Windows execv辅助包装器发生
退出/流哈希竞态，4条原记录明确拒绝且不改写，首次最终核验退出1保留，不作为通过证据。
该问题不影响已独立复算的全部30条诊断区间，也没有筛掉B1/B2。

历史入口为ac33d9d后内存准入v2及一次有限恢复：
[`P3_MEMORY_POLICY.md`](P3_MEMORY_POLICY.md)、[`P3_FIRST_SEED_STATUS.md`](P3_FIRST_SEED_STATUS.md)。
运行内容`d6811cadda8ecd7b46225ebe65c51831278694a0`，新空session
`2c270825458a4857a5ac9df5aadf597b`，未继承7405fcc3/e308bfb的任何成绩。
Windows物理可用/提交余量各512MiB底线、<2GiB物理余量警告；Recovery WSL256MiB/
Formal2GiB。旧协议与REJECT保留原判定，CPU/测量/搜索不变。

本轮唯一Recovery资源PASS，但时钟20区间中6个MONOTONIC/RAW失败，停止而未调用Formal
或4096目标。当前P3_CLOCK_BLOCKED，配置0/24、轨迹0/2、前缀0/6、复测0；
独立四项验收为true/false/false/false。Windows18项资源回归（实际PS入口）、干净归档
28项相关单测（1跳过）、CLI/20配置/n17 fresh正确性通过，不代表正式比较完成。

证据根：[`20261010-174802-11f7775c`](../evidence/p3_memory_policy/20261010-174802-11f7775c/)；
优先查看[`session_plan.json`](../evidence/p3_memory_policy/20261010-174802-11f7775c/session_plan.json)、
[`独立验收`](../evidence/p3_memory_policy/20261010-174802-11f7775c/independent_recovery.json)、
[`时钟全部读数与失败索引`](../evidence/p3_memory_policy/20261010-174802-11f7775c/clock_analysis.json)、
[`结构化交付`](../evidence/p3_memory_policy/20261010-174802-11f7775c/delivery_summary.json)、
[`历史保护`](../evidence/p3_memory_policy/20261010-174802-11f7775c/history_protection_after.json)、
[`成本范围`](../evidence/p3_memory_policy/20261010-174802-11f7775c/costs.json)。
独立诊断120秒超时/空输出也保留，没有重复该诊断；真实资源入口记录同窗口跨接口、
Vmmem/full meminfo，不推断未经证实的WSL预占原因。旧时钟与资源限制不因新策略消失。

历史入口为b19e6cd后7405fcc3首种子恢复：
[`P3_FIRST_SEED_7405FCC3.md`](P3_FIRST_SEED_7405FCC3.md)、[`P3_FIRST_SEED_STATUS.md`](P3_FIRST_SEED_STATUS.md)。
50项来源匹配，既有session3768a29a保持；唯一新recovery入口退出2，宿主内存最低0.722GiB
不足2GiB，CPU14.6%/27%只警告。A/B时钟、Formal门禁与正式目标均未开始，0/24配置、
0/2轨迹/0复测，P3_RESOURCE_BLOCKED。四项独立验收均false，原因说明及原始证据在
[`独立验收`](../evidence/p3_resource_policy/20261010-161312-30f9a2a1-first-seed-7405fcc3/independent_recover.json)
和[`结构化交付摘要`](../evidence/p3_resource_policy/20261010-161312-30f9a2a1-first-seed-7405fcc3/delivery_summary.json)。
不再自动recovery，不借旧证书恢复；10357项历史和新检查点保护通过，无正式实验进程。

历史入口为aae4147后资源准入迁移及运行器修复：
[`P3_RESOURCE_POLICY.md`](P3_RESOURCE_POLICY.md)、[`P3_FIRST_SEED_STATUS.md`](P3_FIRST_SEED_STATUS.md)。
Recovery CPU仅警告、Formal30%/60%，内存/磁盘不放宽，等待含采集最多120秒。
唯一20区间及随后实际失败调用的6个边界区间全通过；新Formal门禁通过，campaign内部
资源UNC签名/非UTF8错误导致退出1、目标执行0。最小修复和准确7405fcc双归档验证通过，
新空session不移用原恢复证书；P3_PARTIAL，首种子比较尚未完成，待下一轮有限验证授权。
证据根为[`本轮目录`](../evidence/p3_resource_policy/20261010-143415/)，
原始失败、所有时钟、身份与成本均保留；不是CPU或新时钟失败。

历史入口为e4f93333后管理员处理/资源核验：[`P3_CLOCK_REPAIR.md`](P3_CLOCK_REPAIR.md)、
[`P3_FIRST_SEED_STATUS.md`](P3_FIRST_SEED_STATUS.md)。管理员resync报告无可用时间数据，
当前仍未同步；内存恢复但原Formal门禁因CPU均值14.2%拒绝，没有新recovery或正式执行。
新证据位于`evidence/p3_clock_repair/20261010-135557/`，管理员原件在
`evidence/p3_clock_repair/admin-20261010-135245/`；P3比较仍未完成。
旧Grid、观测、部分组和失败记录均保留，辅助执行身份仍为fa59701。

0023ceed历史独立审计修订：[`P3_TIMING_AUDIT.md`](P3_TIMING_AUDIT.md)、
[`P3_AUDIT_HANDOFF.md`](P3_AUDIT_HANDOFF.md)；P3正式比较尚未完成，长实验仍暂停。
P2历史入口保留在[`P2_AUDIT_HANDOFF.md`](P2_AUDIT_HANDOFF.md)，P1/P1-R1在
[`P1_AUDIT_HANDOFF.md`](P1_AUDIT_HANDOFF.md)。以下仍是原P0历史交接。

## P0 交接（历史）

## 阶段判定

P0 的环境核查、要求核对、原始源码保存、静态分析与有限预实验已经完成。本文件
不宣称项目整体完成，也不宣称 P1-P5 已通过。

固定提交 SHA 与 GitHub 固定链接在提交、推送及远程核验后由终端交接消息提供，
避免为把提交 SHA 写进自身提交而制造循环提交。

## 审查入口

1. [`P0_DISCOVERY.md`](P0_DISCOVERY.md)：完整事实、风险、假设、P1-P5 计划。
2. [`../code/original/matrix_multiplication.c`](../code/original/matrix_multiplication.c)：
   老师源码的逐字节副本。
3. [`../code/original/SHA256SUMS`](../code/original/SHA256SUMS)：原件校验。
4. [`../experiments/p0/matrix_multiplication_probe.c`](../experiments/p0/matrix_multiplication_probe.c)：
   单独的 P0 诊断副本，不冒充原件。
5. [`../evidence/p0/preexperiment/summary.csv`](../evidence/p0/preexperiment/summary.csv)：
   结构化有限实验结果；同目录含每案 stdout/stderr/命令/退出码。
6. [`../evidence/p0/environment_host.txt`](../evidence/p0/environment_host.txt) 与
   [`../evidence/p0/environment_wsl.txt`](../evidence/p0/environment_wsl.txt)：原始环境输出。
7. [`WORK_LOG.md`](WORK_LOG.md)：失败、定位和修复过程。

## 已验证事项

- 原始源码仓库副本 SHA-256 与外部提供文件一致。
- GCC 13.3 O0/O1/O2/O3 均能无警告编译，仓库保留四级原始日志。
- n=65 的 6 个有效诊断案例逐元素验证全部 PASS；s=8/24/64 都不能整除 65。
- n=65、s=24 的 O1 调试构建通过 Valgrind，错误数为 0。
- s=128>65 被原程序的范围规则拒绝，没有伪造成“超大块计算成功”。
- 当前 GCC O3 反汇编仍含乘法和写回；同时保留“源码缺乏可观察结果”的跨工具链
  风险结论。
- P0 没有运行默认规模或完整搜索，性能数字被明确标为诊断数据。

## 建议审查者重点裁决

1. 是否认可 P1 采用“可覆盖的 MATRIX_SIZE + 严格 CLI + 单调计时 + checksum +
   correctness 模式”作为老师源码的最小工作副本改动。
2. 是否接受无放回随机搜索与带随机重启贪心作为 P3 两种算法候选。
3. 候选公平预算 B=8、5 个种子是否足够；还是要求不同预算/种子数。
4. P2 的候选测量规则（每配置 1 次预热 + 5 次正式测量、中位数排名）是否应在
   P1 pilot 后冻结。
5. `docs/AUDIT_HANDOFF.md` 等过程材料是当前工程审查证据，但公用约定要求最终
   正式报告不含内部审查用语；请裁决最终提交前是否保留这些辅助文件。无论裁决
   如何，`report.md` 都保持为唯一正式报告。
6. `perf` 在当前 WSL 内核不可用。P4 是否允许仅用汇编、硬件规格与稳定时序解释，
   或要求在不改变 P0 基线的前提下另行准备可用计数器环境。

## 复核命令

```powershell
git status --short --branch
powershell -ExecutionPolicy Bypass -File scripts/verify_p0.ps1
wsl.exe -d Ubuntu-24.04 -- bash -lc `
  'cd /mnt/e/software_system/project01 && bash scripts/run_p0_preexperiment.sh'
```
