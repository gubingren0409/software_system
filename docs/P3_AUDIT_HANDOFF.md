# P3 审计入口（首种子时钟阻塞，正式比较未完成）

## 最新：aedf028a后只读诊断（2026-10-10）

[集中诊断/处理决策/下一步](P3_CLOCK_REPAIR.md)；
[独立后处理](../evidence/p3_clock_repair/20261010-121004/diagnosis_analysis.json)。
W32Time仍未同步，source/configuration查询权限拒绝，未执行resync；宿主约403MiB
低于正式2GiB门禁。没有有效环境处理，按授权条件不重采recovery、不恢复campaign。
旧20区间原始端点复算仍20个MONO/RAW及2个REALTIME/RAW失败，根因尚未证实。
32/32冻结实际哈希匹配，10213个旧文件及PAUSE_REQUEST不变；21+7合成回归、CLI/20
唯一配置通过。正式仍3配置/23执行/0完整轨迹、0复测，五条部分执行不计分。
验收：诊断evidence_integrity=true，execution_complete/timing_checks/comparison_ready=false；
新计时检查未执行而非新采集失败。需要管理员配置核验和适当时的一次同步处理证据，
及恢复宿主资源后再交审计，不在本轮继续恢复。

## 历史：fdeed77辅助修复与唯一次20区间复核

辅助内容`0c6ee7e3726a01339d36e6ae7d19b0966dc043cd`先提交，再双干净归档验证。
71项WSL全套测试（Windows专用1项跳过）、Windows旧7/新18项、CLI/20配置及25文件
身份通过。[命令/来源](../evidence/p3_clock_contract/20261009-180810-0491a4ec/clean-0c6ee7e/)。
唯一真实复核20/20 MONO/RAW失败、2/20 REALTIME/RAW失败，Windows同调用UTC/QPC
2/2通过；宿主内存1.968GiB门禁拒绝。**没有实际resume调用，无新增正式执行**。
辅助判据路径错误已定位并修订v2.1；原失败manifest完整保留，补充32项正确位置
哈希匹配不追认旧结果、不授权恢复。[原始窗口/policy/启动记录](../evidence/p3_clock_contract/20261009-180810-0491a4ec/recovery/)、
[全部20条复算](../evidence/p3_clock_contract/20261009-180810-0491a4ec/clock_review_analysis.json)、
[路径补充](../evidence/p3_clock_contract/20261009-180810-0491a4ec/identity_location_correction.json)。
首种子仍3/24配置、0/2轨迹、23执行（18完整组+3已放弃+2待重启），复测0。
[当前状态/成本/后续约束](P3_FIRST_SEED_STATUS.md)、[辅助版本迁移](P3_CLOCK_CONTRACT.md)。
以下e46b96c及更早段落仅为历史，不作为本轮通过证明；等待外部复核，不再自动探测。

最终辅助内容为`fa597017c2317772a0f7f34faa75194ffecec8f2`，含恢复-only不能冒充
campaign边界证书的回归。其[双干净归档](../evidence/p3_clock_contract/20261009-180810-0491a4ec/clean-fa59701/summary.json)
74项全套（WSL跳过1项）、Windows7+21项、CLI/20配置及源码身份通过。
真实复核使用0c6ee7e内容，来源不替换；bb17720为中间路径修复，日志全部保留。
最终源码与fa59701一致，后续提交只含文档及证据。
[当前真实复核验收](../evidence/p3_clock_contract/20261009-180810-0491a4ec/final_recovery_acceptance.json)
整体integrity=false源于保留的旧错误路径，不是丢失20条端点；raw窗口完整性=true、
计时=false、比较=false。干净验证检查的旧未完成模式不能作为此次通过证明。
[最终进程与保护](../evidence/p3_clock_contract/20261009-180810-0491a4ec/final_state.json)、
[独立辅助成本](../evidence/p3_clock_contract/20261009-180810-0491a4ec/auxiliary_cost_index.json)。
下一步只读复算命令及需要外部裁决的时钟/环境处理见首种子状态；不自动再启动探针。

**最新授权与状态（e46b96c之后）**：用户要求沿用原e308bfb归档、固定身份及原
campaign，只恢复seed=20261008随机/贪心两条12配置轨迹及其前缀候选独立复测。
16:38用户要求继续后，原主控批前时钟检查失败，限定30秒复核也未通过，未启动目标。
当前3/24完整配置、23条原始执行、0/2完整轨迹；后四种子不自动启动。
[主控及独立边界时钟记录](../evidence/p3/first-seed-e46b96c-20261009/)、
[报告当前阶段](../report.md#72-e46b96c-后首种子正式恢复)。
原3完整配置和原始21条记录已复核不变；原O0/s8的3条部分样本已留存为放弃记录，
14:04恢复新增的2条部分样本在14:22暂停后仍未计分，下一次须重新1预热+5测量。
[最新阻塞说明、成本和命令](P3_FIRST_SEED_STATUS.md)、
[只读核验与全部命令输出](../evidence/p3/first-seed-review-20261009-1658/)。
交付内容`f64d41c1eab21c72e541f91ab7e2dbecf4adfe2b`的
[干净归档验证](../evidence/p3/first-seed-clean-f64d41c/summary.json)整体PASS：53项单测、
CLI/20配置、历史证据、两侧文件身份；正式比较仍false，`--require-two`按预期退出2。
正式实验内容仍是e308bfb，不将辅助核验内容提交当作新的实验session。
下文0023ceed审计与先前暂停/恢复段落均为历史记录，不代表最新运行状态。

授权：用户要求 P2 完成后开始 P3。P2 保留基线
`37b10327909d9d4134a2d4d68aae0e27b4fc483c` 已推送，尚未获得外部审计通过。

**此前审计阶段**：用户以0023ceed为审计基点要求先做独立诊断、复测和成本回归。
在55b776b后继续，3完整配置/21条原始执行保留，O0/s8的3条部分样本不计分，P3已
安全暂停。以下续跑/资源暂停段落是历史记录，不代表当前仍在运行。审计修订入口
[P3_TIMING_AUDIT](P3_TIMING_AUDIT.md)、[成本口径v1](P3_COST_SCOPE.md)。本轮不启动
完整P3；诊断不反馈策略，既有内容e308bfb/测量schema 2保持不变。

本轮诊断实际内容提交`0d57f8c53a14a8c1d02dfd91263b038fac710ee4`；主控v3通过
同提交Windows本地/WSL双干净归档执行，保留v1/v2启动失败，不改系统安全策略。
[干净46项回归/CLI/导入/配置检查](../evidence/p3_audit_0023ceed/clean_validation-0d57f8c.json)、
[旧P3停止后只读审计](../evidence/p3_audit_0023ceed/preserved_p3_audit.json)（3完整配置、
21条原始执行一致），以及[独立session及来源哈希](../evidence/p3_audit_0023ceed/session-0d57f8c/session.json)。
这些PASS仅证明契约/完整性，不证明正式P3算法比较完成。下文旧续跑命令**仅在
外部复核允许沿用协议后**执行；原`--resume`会留存并清除PAUSE_REQUEST，本轮不运行。

**本轮已完成**：六组各1预热+5fresh，共36条n4096/random/20261008/s128执行，
全部完整契约/正确性通过；[完整诊断分析](../evidence/p3_audit_0023ceed/session-0d57f8c/analysis.json)。
两轮中位数（秒）：O1 50.963140880→51.435436694，O2 52.042876327→52.626460105，
O3 51.308399075→52.122370106；漂移+0.9267%/+1.1214%/+1.5864%。观察排名相同
O1<O3<O2，但相邻差距全部<2%，宿主44/72运行中快照低于2GiB、一次21%CPU，
故robust判据未通过。时钟12个整组/探针+36个Evaluator区间对照通过，不能追认
旧时间已校准。PS主循环2369.4009297s，门禁采集/等待280.4425752s；五次拒绝
均留档并恢复成功。[成本范围/复算](../evidence/p3_audit_0023ceed/cost_and_clock_summary.json)。
之后干净归档重分析和46项回归PASS，[复验日志](../evidence/p3_audit_0023ceed/post_clean_validation.json)。
待裁决：是否需要更充裕/稳定环境下重新建匹配Grid及P3；若改计时协议必须新版本/
session并先重建Grid。完整P3长实验本轮未恢复，诊断没有进入策略或替换原Grid。

当前新增 P3 独立轨迹、私有观测恢复、预算前缀和各候选独立复测，C 核心与 P2 测量/
搜索 schema 2 不变。[冻结规则](P3_PROTOCOL.md)、[campaign 配置](../configs/p3_campaign_protocol.json)、
[运行器](../autotuner/campaign.py)、[只读后处理](../scripts/audit_p3_evidence.py)、
[受控回归](../tests/test_campaign.py)、[干净验收脚本](../scripts/run_p3_clean_validation.py)。

初始资源只读快照：[2026-10-09 开始快照](../evidence/p3/environment/start_20261009.json)。
正式/干净验收内容提交：`e308bfb873e6811c50ad685a979af345302fda8d`。
campaign schema 1 规范化哈希：
`bf7e5fd63656c6bb68714cffd8a060bac8e17db15138ef1b88e8b59b6d5c7461`。
独立归档 `/var/tmp/matrix-autotuner-p2-content-e308bfb873e6811c50ad685a979af345302fda8d`
没有 .git、初始 pycache 或 PYTHONPATH 依赖；旧 p2 名称来自复用导出器，不代表内容
仍是 P2。Git/实际执行身份分别记录，老师原件哈希再次确认一致。

## 已完成的验收（仅诊断）

- [干净验收摘要](../evidence/p3/validation-e308bfb/summary.json)：PASS，24 Python
  文件 AST、CLI帮助、20唯一配置、40项单元测试、verify_p1、空缓存 n17/O2/s8 fresh
  及正确性通过；[命令、stdout/stderr/退出码](../evidence/p3/validation-e308bfb/commands.json)。
- [n130全十轨迹审计](../evidence/p3/validation-e308bfb/diagnostic_audit/audit.json)：
  120次配置评估（每轨迹内去重，跨轨迹独立重测）、720次搜索执行+19组候选复测114次，
  共834次新执行；全局配置空间仍只有20种。所有轨迹
  仅使用自身观测；已完成批次续跑前后ID集合完全相同，没有新增目标执行。
- [真实暂停恢复审计](../evidence/p3/validation-e308bfb/pause_resume_audit/audit.json)：
  保存第一配置的1条部分样本，恢复后留作放弃记录并完整重测；12次配置及1组复测
  共78条有效完整执行、1条放弃记录。旧尝试没有被补成五次测量。

## 正式状态与证据

首批冻结为 seed=20261008 的随机/贪心各12配置（4/8前缀），各预算不同候选独立
复测。完整阶段仍是10条轨迹；本入口未宣称五种子稳定性完成。

- [固定Git身份](../evidence/p3/content-e308bfb/git_identity.json)，本地实际使用的CRLF字节
  SHA-256为`30ced7f0323364c604ebcc0983bb8ede0a2bc03a04521efa40f67ebe60d4ec67`；
  Git规范化LF内容SHA-256为`3fe4e5ef2d1bf2e62f1981a3469e7b764069605ba654ae05f4afe44176c5c10f`。
  两者解析内容相同。28行CRLF、Git blob为`398064667de4b8b0870824a61cb995dc421645d3`；
  [字节身份记录](../evidence/p3/content-e308bfb/identity_bytes.json)。
  不能把通用build/p2身份文件覆盖后直接用于旧实验续跑。
- [正式session与身份](../evidence/p3/campaign-e308bfb/session.json)、
  [检查点](../evidence/p3/campaign-e308bfb/checkpoint.json)、
  [启动命令及控制台记录](../evidence/p3/formal_controller.json)、
  [门禁](../evidence/p3/campaign-e308bfb/gates/)、
  [构建/reference manifests](../evidence/p3/campaign-e308bfb/manifests/)。
- setup与n4096 reference已经完成，data SHA-256与P2完全相同。01:18只读正式门禁
  PASS；setup后首配置门禁曾因宿主内存低于2GiB而拒绝。随后资源恢复，O1/s64启动。
  没有放宽门槛或停止其他应用。[初始门禁快照](../evidence/p3/environment/pre_formal_20261009.json)。
- [逐次原始证据](../evidence/p3/campaign-e308bfb/trajectories/)、
  [阶段完整性复核](../evidence/p3/postprocessing/audit.json)。audit PASS仅表示已保存
  记录一致，部分状态不得解释为正式阶段全部PASS。当前只读复核并未
  改变正在运行的策略数据；空预算表不构成搜索比较结论。

01:42进度快照：随机种子20261008完成1/12配置，首配置O1/s64五次中位数
54.993200129秒、均值54.7871725618秒、样本标准差0.6600945951秒、CV=1.2048%、
MAD=0.586264908秒；六次执行均fresh/force、退出0并验证16777216项、零错配。
O0/s24预热472.340622065秒已通过，计分五次尚未完整；贪心轨迹尚未开始。
这是首批1/24配置、全计划1/120次配置评估，不能宣称完成正式P3比较或候选复测。

**后续已保存的终止状态**：第二配置O0/s24六次全部fresh/force、退出0并全矩阵正确。
五次中位数467.876385448秒、均值467.706472674秒、样本标准差1.7528160454秒、
CV0.3748%、MAD1.201713070秒。当前首批2/24配置、全计划2/120次轨迹内配置评估，
共12条完整目标执行，没有正式复测或完整4/8/12预算前缀。贪心尚未开始。
第三配置开始前连续16次门禁失败，02:24:47根检查点保存`resource_paused`并退出，
没有活跃目标或部分测量组；子轨迹`running`字段表示未完成，不表示仍有进程存活。
执行工具记录的控制命令退出码为1；门禁文件与根检查点是暂停原因的原始证据，
不把该非零码当候选验证失败。控制台分块有工具截断；逐次stdout/stderr、资源、
样本与完整门禁JSON不依赖截断控制台，均保存在campaign目录。

[停止后只读一致性复核](../evidence/p3/resource-paused-audit/audit.json)为PASS，
只说明2个完整配置与12次执行可追溯，绝非阶段完成。
[10:12正式模式复查](../evidence/p3/environment/terminal_gate_20261009_101207.json)：
REJECT，宿主最低可用454094848字节（约433MiB），CPU平均4.4%/最大12%，
WSL可用4153413632字节、swap使用0；宿主内存是阻塞项。没有放宽协议或终止其他应用。
释放宿主资源后按下方固定身份命令续跑；2个完整组可以恢复，尚余首批22次配置评估
及各前缀候选复测，完整计划尚余118次配置评估。大型缓存留在WSL本地。
累计记录成本（未校准MONOTONIC）：active_total=4156.749711031秒，其中门禁/等待
945.379027386秒，初始setup=42.351758652秒；不包含停止至10:12的离线等待。

**本次恢复（2026-10-09）**：用户再次要求继续，10:40:20正式资源门禁PASS，宿主
最低可用6122872832字节（5.70GiB）、WSL4187226112字节（3.90GiB），CPU平均4.4%/
最高16%，磁盘通过、AC在线；既检查返回码，也解析正式schema/模式/判定与各数值。
[恢复前资源与12条旧run ID](../evidence/p3/resume-20261009-104020/preflight.json)、
[实际续跑命令与控制记录](../evidence/p3/resume-20261009-104020/controller.json)、
[恢复身份与状态](../evidence/p3/resume-20261009-104020/restoration.json)。
沿用内容e308bfb、session dc1c292900654d44b36a72548b95a610和固定身份；源码、编译器、
四个二进制/reference哈希及两完整组原始样本/自身观测顺序均通过恢复检查。
恢复setup查找0.657944117秒单独记账，未重建reference或用性能缓存凑重复。
10:42:55第三配置O3/s16启动预热，新的attempt ID不复用旧组；完整配置仍为2，
没有宣称新组分数或完整前缀。上述02:24/10:12暂停记录保留为历史，不标成当前阻塞。
当前只运行首种子的两条轨迹，最多24次唯一配置评估加前缀候选复测，五种子待续。
[恢复后的fresh样本](../evidence/p3/resume-20261009-104020/fresh_progress.json)确认
O3/s16预热84.614765330秒、第一条测量84.805230120秒，退出0、fresh/force、逐元素
16777216项零错配；12条旧run ID仍在、全部ID唯一。第三组未齐5条，不产生配置分数。

本阶段仅对一个自有reference文件做过一次POSIX_FADV_DONTNEED建议，数据仍在且
操作前哈希相同。[操作记录](../evidence/p3/environment/reference_page_advice_20261009.json)
表明建议成功返回，但不证明Windows回收；01:30:41门禁恢复早于01:31:01操作，
不能归因。操作发生于O0预热期间、非计分样本；不重复作为新测量策略。该诊断脚本
与绘图脚本是交付辅助文件，不替换e308bfb的正式归档/测量模块。后台I/O扰动未量化。

继续同一批次必须使用相同归档、身份和campaign根目录；`--resume`会核验全部原始
样本、内容、编译器、输入/reference、配置与协议。已有运行器存活时不要重复启动，
全局文件锁会拒绝第二个P3运行器。需要完成其余种子时将limit增至10。

```bash
cd /var/tmp/matrix-autotuner-p2-content-e308bfb873e6811c50ad685a979af345302fda8d
PYTHONDONTWRITEBYTECODE=1 env -u PYTHONPATH python3 -m autotuner campaign \
  --content-sha e308bfb873e6811c50ad685a979af345302fda8d \
  --git-identity /mnt/e/software_system/project01/evidence/p3/content-e308bfb/git_identity.json \
  --campaign-directory /mnt/e/software_system/project01/evidence/p3/campaign-e308bfb \
  --trajectory-limit 2 --resume
```

待审计：策略是否严格使用自身观测；每组是否完整 fresh/force；失败与部分样本是否
不计分；预算前缀与候选复测是否分离；资源 gate/暂停身份是否完整；P2 原表比较与
P3 跨 session 时间差是否明确区分；未校准时钟/环境压力是否要求另环境重新测量。

本入口为阶段状态，不替代 P2 完整性证据或外部审计意见。最终提交 SHA 只在提交和
推送后终端交接提供，不为把文档写进自身 SHA 而循环提交。

进度快照内容提交`ec68c6cf78807c023d3ed864d16b9bb45c4ed563`另从无.git/初始pycache
的归档复核：26个Python AST及核心模块导入、CLI帮助、20唯一配置、归档中正式
记录审计均PASS。[归档复核日志](../evidence/p3/progress_archive_smoke.json)、
[快照审计](../evidence/p3/progress-archive-audit/audit.json)。该固定快照含1个完整
配置与8条完整目标执行；后续实时进度写在原campaign目录，不能把快照当最终P3。
正式target/CLI/测量/搜索/配置对e308bfb无改动，复用其40项单测和空缓存实际小规模
验收；没有在正式目标运行期间再开诊断目标。辅助绘图仅AST检查，尚无足够正式
预算前缀数据生成图或完整算法比较。
