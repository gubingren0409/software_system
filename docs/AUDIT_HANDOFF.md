# 审计交接入口

## 当前：d706a96a后人工续跑已停止，FIRST_SEED_RAW_COMPARISON_PARTIAL

执行776b11171d796c8071e69824ffe463c4faf8ba57、session c1bd157c6c8d42439d0fb08f69156ff5保持；
辅助706d239a5f1592dc17fb2ceefa46a2112727f966准确归档，科学3cc9e0d/RAW/资源v2/搜索不改。
14项新增相关受控回归工作树及准确归档通过。先保存旧checkpoint/window/98条记录与16,831历史文件SHA。
唯一fresh准入2/2、Formal和缓存核验通过后，旧O3/s128两条明确放弃，新完整组重做且不复用性能缓存。
Random12+2复测全保留，新增Greedy9完整组；当前23/24搜索组（12+11）、2复测组（2+0）、25完整组。
原始156唯一记录=150已接纳+2旧放弃+4新部分，新增目标58。GreedyO3/s16测量3超时，缺组后RAW、连续性不成立。
2026-10-19T12:27:28.5899707Z System506明确Reason:Lid，12:37:45退出/再次待机的完整消息/XML保留；
控制器退出2，安全停止不重试，不把原始部分组的成功样本挑出计分，防睡眠finally释放，任务进程退出。

四项为evidence_integrity_pass=true；execution_complete/timing_checks_pass/comparison_ready=false，first_seed范围，五种子仍false。
本段21个RAW区间通过（合计历史56/332响应），资源11次通过、证据卷11次通过；并不证明受干扰组连续执行。
预算保留旧15841.5879168s，本段7488.0732714s，累计23329.6611882s/43200s，余19870.3388118s不自动续领。
旧window/claim/证书/旧98条字节前缀/Random完整轨迹和所有历史不可变文件均保护。
prefix成本仅终态配置评估RAW，完整端到端未知；分段宿主包络、共享准备/测量/复测/失败/门禁为嵌套范围，不全部相加。

- [本段说明/实际命令/来源/只读复算入口](../evidence/p3_raw_first_seed/20261019-181817-693c9e13-manual-continuation/README.md)
- [新授权/16,831文件SHA](../evidence/p3_raw_first_seed/20261019-181817-693c9e13-manual-continuation/continuation/authorization.json)、[闭合QPC窗口](../evidence/p3_raw_first_seed/20261019-181817-693c9e13-manual-continuation/continuation/window.json)
- [独立续跑审计](../evidence/p3_raw_first_seed/20261019-181817-693c9e13-manual-continuation/continuation/independent_continuation_audit.json)、[停止/电源/历史/进程核验](../evidence/p3_raw_first_seed/20261019-181817-693c9e13-manual-continuation/stop_review.json)
- [六行真实前缀表](../evidence/p3_raw_first_seed/20261019-181817-693c9e13-manual-continuation/first_seed_six_rows.csv)、[成本及范围](../evidence/p3_raw_first_seed/20261019-181817-693c9e13-manual-continuation/costs.json)

未解决：Greedy第12配置及其去重候选复测；本段待机造成的连续性拒绝；跨段/历史低内存和单种子比较限制。
仅交外审，不直接重复run/准入或另开窗口。旧审计v2不支持人工续跑放弃账本，原结论保留；新版本审计复用冻结组判据并严格核对账本。

## 历史：efb7f9df后RAW首种子搜索PARTIAL

实际执行SHA `776b11171d796c8071e69824ffe463c4faf8ba57`，继承科学内容3cc9e0d；
新search session `c1bd157c6c8d42439d0fb08f69156ff5`，一次43200s独占QPC窗口，双seed分别20261008。
最小运行修复仅mode验收/完整性及实际证据卷门禁、prepare search-only适配与受控测试，科学C/协议不改。
三环境28项比较回归、两环境17项续跑关联回归、CLI与20唯一配置通过；没有额外n17、三配置或Grid。

Random12完整搜索组＋2个去重复测完整，Greedy2/12完整；第三组O3/s128受合盖待机/测量超时影响。
98个唯一run_id，96条属16个完整组；另成功预热/超时两条保留为active不可比较，不拼接、不评分、不自动重试。
17:43:18原始System506消息Reason:Lid，17:59:55 System507退出；boot-time估计字符串发生微小变化，
原控制器先报身份拒绝，不据此伪称日志重置/真正重启。防睡眠请求无法阻止合盖，已finally释放。
官方模块CLI及独立后处理均真实退出2，四项为true/false/false/false：证据完整、执行未完成、整轮计时未验收、比较未就绪。
35个已采RAW区间/208响应独立复算通过，但失败组无组后/连续性，不能据此将整轮timing_checks_pass置true。
19资源门禁通过、11次低内存警告；18证据卷检查均通过；本次不是CPU/内存/磁盘准入阻塞。
历史14,221文件全SHA不变，关闭验证9332ead2的18样本/分数、Grid待机/旧失败/claim/证书/预算均不改。

- [原始证据总入口、六行真实前缀表及成本范围](../evidence/p3_raw_first_seed/20261019-132400/README.md)
- [执行计划/双端源码与协议身份](../evidence/p3_raw_first_seed/20261019-132400/content/search_plan.json)、[来源清单](../evidence/p3_raw_first_seed/20261019-132400/source_identity.json)
- [官方独立审计](../evidence/p3_raw_first_seed/20261019-132400/official_first_seed_audit.json)、[独立后处理](../evidence/p3_raw_first_seed/20261019-132400/independent_first_seed_audit.json)
- [停止原始消息与部分样本复核](../evidence/p3_raw_first_seed/20261019-132400/stop_review.json)、[成本](../evidence/p3_raw_first_seed/20261019-132400/costs.json)
- [历史保护](../evidence/p3_raw_first_seed/20261019-132400/history_after.json)、[资源/时钟质量派生说明](../evidence/p3_raw_first_seed/20261019-132400/quality_report.json)

活动包络15841.5879168s（43200内），待机不退款；Random配置评估RAW12370.681806653s、
Greedy已接纳两组1041.151905033s、Random复测791.041269405s及准备84.7506965s是嵌套分项，不全部相加。
现有prefix终态配置评估口径不含门禁/准入/复测/失败，完整端到端prefix成本仍未知。
五种子未完成，不能以Random三个前缀的完成声称整个P3已完成；旧Grid跨日/待机限制不消失。
当前实验进程全部退出，保留claim/window/失败组；后续仅外审和新的明确续跑授权，禁止直接重启一次性入口。

## 历史：aac44ef7后仅补s24，三配置验证完整通过

状态P3_RAW_THREE_CONFIG_VALIDATION_COMPLETE，**不表示P3搜索比较完成**。
辅助e8816554b3b9208b0ab4aa00d9adc96b0f692505准确归档；实际执行35a60b090b728d2ec3b6a8ea014beac69fe3766d、
验证session9332ead2881a4c1e91b966e90a0d2057不变，继承科学3cc9e0d。17项相关回归/干净归档与3项合成辅助测试通过。
本次唯一fresh准入2区间、组两侧2区间全部独立RAW通过，来源/缓存/编译器核验，无setup/reference生成。
只新增s24的1预热+5fresh，3/3组、18/18执行，全16777216元素正确，18个run_id唯一，无部分/放弃目标。
s24中位数63.240102045s、CV0.504125%、MAD0.273363999s；相对原Grid−4.542423%，原Grid/待机/旧分数不改。
System原始消息无组内待机；同范围QPC387.9632797s/RAW387.957298023s，差0.005981677s。防睡眠finally释放。
组门禁host最低648581120B、低2GiB警告保留；后续资源快照不能证明组内无压力或WSL预占原因。
两组10月14日、s24在19日，跨日分段，不是连续批次或严格同环境因果比较。

独立evidence_integrity_pass/validation_complete/validation_timing_checks_pass=true；
P3 execution_complete/timing_checks_pass/comparison_ready=false，搜索轨迹/配置/前缀复测仍0。
306原session文件、13,711其他证据、原两组/12条字节前缀/旧claim/证书保护；samples只追加6条，原运行器写complete。
旧空stdout、超额门禁、E满盘片段及全部旧失败仍保存为原结论。本轮在此关闭验证，不追加或自动搜索。
本段514.3688049s，六段累计1983.4389043s，3600s账面余1616.5610957s，不转移搜索预算。
进程527.3836979s包含活动；门禁/核心/组评估/探针嵌套成本不再相加，离线辅助成本另列。

- [全部证据/来源/限制/下一阶段](../evidence/p3_raw_comparison/20261019-122200-user-retry4/README.md)
- [独立完整验收](../evidence/p3_raw_comparison/20261019-122200-user-retry4/continuation/independent_continuation_audit.json)、[授权/保护SHA](../evidence/p3_raw_comparison/20261019-122200-user-retry4/continuation/authorization.json)
- [三配置CSV](../evidence/p3_raw_comparison/20261019-122200-user-retry4/three_configuration_comparison.csv)、[18条结果契约复算](../evidence/p3_raw_comparison/20261019-122200-user-retry4/all_sample_contracts_independent.json)
- [本轮及历史RAW复算](../evidence/p3_raw_comparison/20261019-122200-user-retry4/all_clock_checks_independent.json)、[资源与旧拒绝](../evidence/p3_raw_comparison/20261019-122200-user-retry4/all_resource_gates_independent.json)
- [源码/协议/二进制身份](../evidence/p3_raw_comparison/20261019-122200-user-retry4/source_identity.json)、[成本](../evidence/p3_raw_comparison/20261019-122200-user-retry4/costs.json)

待外审：验证完整性、跨日与低内存边界、12h搜索预算场景；之后才另行授权新search session及fresh准入。
不把独立验证/旧Grid馈入搜索，不借原证书或未用验证余量启动搜索。

## 历史：9d271433后人工重试，组前host_memory拒绝

状态P3_RAW_VALIDATION_RESOURCE_BLOCKED。新外层02907787f09ee94922d159e6b6bb9a0203c6bde5，
原实际测量35a60b090b728d2ec3b6a8ea014beac69fe3766d/session9332ead2881a4c1e91b966e90a0d2057不变。
16项针对性回归及干净归档、3项合成AC拒绝测试通过。未重跑历史大批测试或额外n17/搜索。
AC已接100%，Formal预检通过、唯一fresh RAW2/2及源码/编译器/缓存核验通过；没有setup/reference生成。
s24组前四有效快照仅host_memory拒绝，最低281374720/325533696/429780992/474804224B；
门禁118.9061907s内停止，控制器退出2，临时防睡眠释放。没有组边界新探针或矩阵执行。
仍2组/12fresh，部分/放弃目标0，搜索/前缀复测0。独立完整性true，验证完成/全计时及P3三项false。
289个session文件、13,618其他证据和原12条字节前缀/两组成绩/初始证书/旧claim均保护。
本段207.9839123s，累计1469.0700994s，余2130.9299006s；不跨epoch相减，不叠加嵌套成本。

- [本轮完整说明/测试/真实资源/下一步](../evidence/p3_raw_comparison/20261018-201600-user-retry3/README.md)
- [新授权与历史保护SHA](../evidence/p3_raw_comparison/20261018-201600-user-retry3/continuation/authorization.json)、[停止窗口](../evidence/p3_raw_comparison/20261018-201600-user-retry3/continuation/window.json)
- [独立验收](../evidence/p3_raw_comparison/20261018-201600-user-retry3/continuation/independent_continuation_audit.json)、[所有门禁与历史错误](../evidence/p3_raw_comparison/20261018-201600-user-retry3/all_resource_gates_independent.json)
- [源码/协议身份及行尾](../evidence/p3_raw_comparison/20261018-201600-user-retry3/source_identity.json)、[成本](../evidence/p3_raw_comparison/20261018-201600-user-retry3/costs.json)

本轮已停止；余量不代表自动重新授权。先稳定宿主余量/接电开盖，后续只补s24、不重复旧两组或搜索。
占用快照仅说明当前内存压力，不能证明WSL预占或单个进程的唯一因果；不改旧失败结论。

## 历史：6b1860a后再次明确重试，接电前检停止

状态P3_RAW_VALIDATION_AC_POWER_BLOCKED。辅助103387cfae82523d9ad42bf4567af42cc2239337，
原测量35a60b0/session9332ead2不变；15项关联测试/干净归档通过，只允许s24及原2342.1691553s。
Windows API ac=0、电量75%，父控退出2；finally释放防睡眠。资源/新RAW/新组边界/矩阵全部0次。
仍2/3组、12/18fresh，287个原session文件和13,545其他证据、原12条字节前缀不变。
本段3.2553424s，累计1261.0861871s，账面余2338.9138129s；不重置、不再次探测或自动搜索。
原辅助审计早期文件缺席的integrity=false结果保留；另以原数据/捕获/授权检查器核验接电拒绝及阶段缺席，
证据完整性true。资源/时钟not_executed不是PASS，验证全完成/全计时及P3三项false。

- [全部新说明/原始命令/成本/下一步](../evidence/p3_raw_comparison/20261015-152400-user-retry2/README.md)
- [采集前授权/保护哈希](../evidence/p3_raw_comparison/20261015-152400-user-retry2/continuation/authorization.json)、[AC原始操作](../evidence/p3_raw_comparison/20261015-152400-user-retry2/continuation/ac_status.operation.json)
- [原辅助拒绝](../evidence/p3_raw_comparison/20261015-152400-user-retry2/continuation/independent_continuation_audit.json)、[单独阶段核验](../evidence/p3_raw_comparison/20261015-152400-user-retry2/continuation/independent_preflight_stop_audit.json)
- [阶段/成本摘要](../evidence/p3_raw_comparison/20261015-152400-user-retry2/delivery_summary.json)、[辅助源码/协议身份](../evidence/p3_raw_comparison/20261015-152400-user-retry2/source_identity.json)

待审：阶段缺席与检查失败/通过分开；组级timing标志与全验证完成分开。所有旧记录不改。
先由用户接电/保持开盖，再一次原余量授权，当前已关闭claim不可直接再run。

## 历史：742cac14后授权一次重试，仍在组前资源门禁停止

外层3eaeadd28245664f4ea27bd8e4f79082fcf0124e，测量35a60b0/session9332ead2不变；14项针对性测试
工作树及干净归档通过，未执行n17/历史大批测试、搜索或新Grid。新retry claim绑定前次授权/窗口/旧claim，
原1046.1205449s全部保留，只获2553.8794551s，非新3600秒预算。门禁保留1秒收尾、不改120秒上限。
Formal预检与唯一2区间fresh RAW通过；s24组前3有效快照低于512MiB仅host_memory拒绝，第四次采集超时。
119.5028273s安全停止，新目标/边界检查0；仍2/3组、12/18fresh，旧270+13,458文件/原前缀不变。
本段211.7102998s，累计1257.8308447s，账面余2342.1691553s，不再自动试。
evidence_integrity_pass=true；验证完成/验证全计时及P3 execution_complete/timing_checks_pass/comparison_ready=false。
停止后快照有VALORANT约1.71GiB；不是已证实的唯一根因，也不以较晚内存恢复追认门禁PASS。

- [本轮完整说明和原始证据](../evidence/p3_raw_comparison/20261015-130000-user-retry/README.md)
- [授权/保护哈希](../evidence/p3_raw_comparison/20261015-130000-user-retry/continuation/authorization.json)、[独立验收](../evidence/p3_raw_comparison/20261015-130000-user-retry/continuation/independent_continuation_audit.json)
- [全部资源门禁/超时/历史REJECT](../evidence/p3_raw_comparison/20261015-130000-user-retry/all_resource_gates_independent.json)、[RAW区间复算](../evidence/p3_raw_comparison/20261015-130000-user-retry/all_clock_checks_independent.json)
- [成本口径](../evidence/p3_raw_comparison/20261015-130000-user-retry/costs.json)、[源码/协议/行尾](../evidence/p3_raw_comparison/20261015-130000-user-retry/source_identity.json)

下一步先释放游戏等高内存占用，再明确一次原剩余额度补齐；不直接重复run、不删除claim或运行搜索。

## 历史：释放E空间后单次续用原额度，组前内存门禁停止

状态`P3_RAW_VALIDATION_RESOURCE_BLOCKED`。辅助内容22fe97c02e2bf1cd56662413e10fc5311113a246；
实际35a60b090b728d2ec3b6a8ea014beac69fe3766d/session9332ead2881a4c1e91b966e90a0d2057不变。
新增外层调度，不绕过原空session入口或改旧claim/证书，保留两组，仅授权s24及原剩余额度2753.926324s。
10项针对性测试工作树/准确干净辅助归档均通过，没有n17/额外历史测试或新Grid/搜索。
E证据盘可写/约58.4GiB通过，Formal预检通过，一次fresh短/长RAW2/2通过（累计9区间全部通过）。
第三组资源门禁四个快照仅host_memory拒绝，最低239452160/302333952/394579968/300908544B，
等待120.0005393s后停止；严格独立审计也保留0.0005393s超额拒绝。组前后新探针0、目标0。
仍2/3组、12/18fresh、部分矩阵样本0；253原session文件、13,354其他证据、旧原始前缀均保持。
累计活动1046.1205449s=原846.073676s+本段200.0468689s，不退款、不重置；离线辅助成本另列。
原始/来源完整性true；validation_complete/validation_timing_checks_pass和P3三项全部false。
Formal预检通过不证明组门禁通过；停止后的host恢复快照也不能取代失败快照。
旧Grid仍关闭，原待机样本/分数不变，旧空search session和所有搜索协议均不动。

审计入口：

- [完整说明、调用和停止边界](../evidence/p3_raw_comparison/20261014-204900-disk-continuation/README.md)
- [真实授权及保护哈希](../evidence/p3_raw_comparison/20261014-204900-disk-continuation/continuation/authorization.json)
- [独立核验与预算](../evidence/p3_raw_comparison/20261014-204900-disk-continuation/continuation/independent_continuation_audit.json)
- [完整门禁复算/旧REJECT与超额](../evidence/p3_raw_comparison/20261014-204900-disk-continuation/all_resource_gates_independent.json)
- [9区间复算](../evidence/p3_raw_comparison/20261014-204900-disk-continuation/all_clock_checks_independent.json)、[12条严格结果契约](../evidence/p3_raw_comparison/20261014-204900-disk-continuation/all_sample_contracts_independent.json)
- [来源/行尾/缓存](../evidence/p3_raw_comparison/20261014-204900-disk-continuation/source_identity.json)、[成本](../evidence/p3_raw_comparison/20261014-204900-disk-continuation/costs.json)
- [原工作树备份和ff-only同步](../evidence/p3_raw_comparison/20261014-204900-disk-continuation/sync.transcript.txt)、[范围/准入/预算规则](P3_RAW_VALIDATION_CONTINUATION.md)

本轮已停止。剩s24六次，下一轮须核验资源稳定并明确一次剩余额度补齐，不能再run本次claim或借新3600s。

## 历史：c08184e后新AC授权，2/3验证组完成后证据盘满

状态`P3_RAW_VALIDATION_PARTIAL / EVIDENCE_DISK_FULL`。原执行内容
`35a60b090b728d2ec3b6a8ea014beac69fe3766d`不改，新验证session
`9332ead2881a4c1e91b966e90a0d2057`，唯一新3600s活动，不覆盖旧claim或失败证据。
一次fresh短/长准入2/2通过，已采5组边界RAW检查通过；12fresh（2预热/10测量）、2完整组有效。
新分数s128=51.602724641s、s64=52.784908609s，正确性/RAW/连续性三项各自通过。
第三组s24在写检查点时EIO，Windows故障保存ENOSPC；实际目标0次，剩6次未执行。
E:仅16384B，WSL根盘约208GiB；不是时钟失败/AC失败，也未放宽内存/CPU/计时规则。
控制器真实退出1，窗口stopped，最后有效checkpoint仍ready/两组/active=null，不手工修成stopped或complete。
临时防睡眠finally释放成功；没有重跑、补采、删除样本或退款。QPC846.073676s。

evidence_integrity_pass=true；validation_complete/validation_timing_checks_pass=false；
P3 execution_complete/timing_checks_pass/comparison_ready=false。正式搜索仍未运行。
13,231项旧证据字节保护通过；旧AC claim/失败、关闭Grid和旧成绩都不改。
本轮290文件复制并逐SHA核验到C，E原始文件不动；两份失败checkpoint临时片段也随证据保留。
提交/推送工作树为C盘同历史project01副本，原E工作树仍在c08184e，需释放空间后安全同步，禁止reset覆盖。

优先审计：

- [完整新批次、原因及只读命令](../evidence/p3_raw_comparison/20261014-182807-ac-validation/README.md)
- [新授权](../evidence/p3_raw_comparison/20261014-182807-ac-validation/authorization.json)、[plan/准确归档](../evidence/p3_raw_comparison/20261014-182807-ac-validation/validation_plan.json)
- [独立验收](../evidence/p3_raw_comparison/20261014-182807-ac-validation/independent_validation_audit.json)、[12条逐样本契约](../evidence/p3_raw_comparison/20261014-182807-ac-validation/all_sample_contracts_independent.json)
- [7区间原始独立复算](../evidence/p3_raw_comparison/20261014-182807-ac-validation/all_clock_checks_independent.json)、[门禁含旧REJECT](../evidence/p3_raw_comparison/20261014-182807-ac-validation/all_resource_gates_independent.json)
- [三配置表/波动/变化](../evidence/p3_raw_comparison/20261014-182807-ac-validation/three_configuration_comparison.csv)、[成本包含关系](../evidence/p3_raw_comparison/20261014-182807-ac-validation/costs.json)
- [真实退出1及ENOSPC stderr](../evidence/p3_raw_comparison/20261014-182807-ac-validation/operations/validation_activity.stderr.txt)、[E和WSL磁盘原读数](../evidence/p3_raw_comparison/20261014-182807-ac-validation/operations/wsl_root_and_evidence_disk.stdout.txt)
- [13231项历史保护](../evidence/p3_raw_comparison/20261014-182807-ac-validation/history_after.json)、[救援复制逐字节证明](../evidence/p3_raw_comparison/20261014-182807-ac-validation/disk_full_rescue/rescue_manifest.json)

未解决：证据盘未被现有根盘门禁覆盖，失败保存可再次ENOSPC，s24未验证。下一轮审定最小入口修复及
补充磁盘/写失败回归、新内容或有界续跑授权；不要拿剩余2753.926324s自动重试，也不直接开始搜索。

## 历史：e1b3a7ee之后独立RAW比较入口，验证未接电停止

状态`P3_RAW_COMPARISON_PARTIAL_AC_POWER_BLOCKED`，不是完成18次验证或P3比较。
实际内容`35a60b090b728d2ec3b6a8ea014beac69fe3766d`准确双归档，各19项新受控测试通过；
测量来源3cc9e0d独立绑定，科学源码、20空间/搜索、测量/RAW及资源v2未改。
validation session `f9f3bb0d54724d2385a8b77be26a99b3`，search session
`d7a9ba9fc5384990b739ff51363a03e5`；两者未导入旧成绩，旧Grid完全关闭。

唯一调用真实退出2：GetSystemPowerStatus成功、ACLineStatus=0、电量72%，按接电/开盖要求停止。
防睡眠请求核验非零、finally同线程释放。QPC窗口2.428145秒（3600预算），外层3.1998347秒含该窗口；
claim和真实stdout/stderr/退出码保留，不重启/退款。资源/时钟均未执行，不能写成时钟失败或门禁通过。
0/18矩阵、0/3验证组、0/2准入区间、0搜索/复测/部分组；没有恢复证书。
证据完整性true；验证完成/验证计时及P3 execution_complete/timing_checks_pass/comparison_ready均false。

优先审计：

- [本轮完整证据与只读命令](../evidence/p3_raw_comparison/20261014-102833/README.md)
- [最终摘要](../evidence/p3_raw_comparison/20261014-102833/delivery_summary.json)、[独立验收](../evidence/p3_raw_comparison/20261014-102833/independent_validation_audit.json)
- [新协议/连续性/信息隔离/固定预算](P3_RAW_COMPARISON.md)、[受控回归](../tests/test_raw_comparison.py)
- [双干净归档及实际来源](../evidence/p3_raw_comparison/20261014-102833/content/prepare_summary.json)、[validation plan](../evidence/p3_raw_comparison/20261014-102833/content/validation_plan.json)、[空search plan](../evidence/p3_raw_comparison/20261014-102833/content/search_plan.json)
- [接电API原始返回](../evidence/p3_raw_comparison/20261014-102833/content/validation-f9f3bb0d/ac_status.json)、[申请/释放](../evidence/p3_raw_comparison/20261014-102833/content/validation-f9f3bb0d/sleep_request.json)、[窗口/原因](../evidence/p3_raw_comparison/20261014-102833/content/validation-f9f3bb0d/window.json)
- [三配置原Grid/新未执行表](../evidence/p3_raw_comparison/20261014-102833/three_configuration_comparison.csv)、[六行比较空表](../evidence/p3_raw_comparison/20261014-102833/first_seed_six_row_template.csv)
- [历史保护](../evidence/p3_raw_comparison/20261014-102833/history_after.json)、[旧Grid只读审计](../evidence/p3_raw_comparison/20261014-102833/closed_grid_readonly_audit.json)、[三种质量结论](../evidence/p3_raw_comparison/20261014-102833/closed_grid_quality_annotation.json)
- [本轮成本和包含关系](../evidence/p3_raw_comparison/20261014-102833/costs.json)、[后续搜索预算提案](../evidence/p3_raw_comparison/20261014-102833/later_search_budget_proposal.json)

待审：独立RAW授权而非删除旧拒绝、source/session/协议拒绝、同范围QPC/RAW及RecordID受扰判定、
one-shot预算防重置、三配置验证尚未进行。下一步应接电开盖、外审后明确新的有限验证授权；
不直接复用当前claim，不自动启动搜索。新准入通过也不能追认旧Grid内部连续性。

## 历史：9f714a72之后，人工续用剩余额度完成RAW Grid

**RAW_GRID_COMPLETE / P3_SEARCH_COMPARISON_INCOMPLETE**，不是整个作业完成。
测量内容`3cc9e0d03ba682569fca0e91f28d364f2dab73fa`、session `f705a488d7b442789973381e2190c944`不变；
外层内容`957576ca39689e9b8a723006aeb8177562e1620b`，准确归档运行，20项关联受控测试通过。
人工授权仅续用14266.6648025s，旧133.3351975s保持计费。新claim排他，旧claim/预算/controller不改。
一次原Formal预检、一次两区间fresh附件通过，余15配置/90fresh完成，合计20/120/40组检查。
原12区间证书不变，附件2区间另计；120个run_id唯一，1+5fresh完整，无部分/放弃组。
evidence_integrity_pass=true；grid_complete/grid_timing_checks_pass=true；
P3 execution_complete/timing_checks_pass/comparison_ready=false，Random/Greedy及独立最优复测均未运行。

**必须审计的质量限制：O3/s24第5测量内发生合盖Modern Standby。**
事件506/507及消息已保存，UTC标签间隔2169.217s；原RAW契约和组边界检查通过，但不证明矩阵内部连续。
样本/排名不修改、不筛掉、不校准或重跑；整段QPC计费，不退款。
独立审计的Grid timing=true仅表示冻结规定的RAW端点/准入/分组边界成立，不是全天候准确性或稳定性认证。
测得最低中位数O3/s12850.996291138s，CV0.4313%、MAD0.229528039s；未独立复测。

优先审计：

- [本次完整入口与只读命令](../evidence/p3_raw_grid/20261012-181149-manual-remaining/README.md)
- [授权及旧133.3351975s绑定](../evidence/p3_raw_grid/20261012-181149-manual-remaining/window/authorization.json)、[真实预算/退出状态](../evidence/p3_raw_grid/20261012-181149-manual-remaining/window/window.json)
- [辅助内容/实际字节/归档](../evidence/p3_raw_grid/20261012-181149-manual-remaining/auxiliary_freeze.json)、[20项干净测试](../evidence/p3_raw_grid/20261012-181149-manual-remaining/operations/clean_controlled_tests.stderr.txt)
- [两区间全部原始流](../evidence/p3_raw_grid/20261012-181149-manual-remaining/window/admission/)、[独立端点复算](../evidence/p3_raw_grid/20261012-181149-manual-remaining/window/recomputed_admission.json)
- [原测量＋分段独立审计](../evidence/p3_raw_grid/20261012-181149-manual-remaining/window/independent_segment_audit.json)、[20配置汇总](../evidence/p3_raw_grid/20261012-181149-manual-remaining/grid_summary_20.csv)
- [全部120样本](../evidence/p3_raw_grid/20261011-021601/final-content/grid-f705a488/samples.jsonl)、[40个组检查](../evidence/p3_raw_grid/20261011-021601/final-content/grid-f705a488/group_checks/)
- [休眠/受影响样本和来源](../evidence/p3_raw_grid/20261012-181149-manual-remaining/standby_analysis.json)、[Windows原消息](../evidence/p3_raw_grid/20261012-181149-manual-remaining/operations/monitor_gap_power_events.stdout.txt)
- [原件/旧5组/前缀/11017历史/进程退出保护](../evidence/p3_raw_grid/20261012-181149-manual-remaining/delivery_verification.json)、[资源独立复算](../evidence/p3_raw_grid/20261012-181149-manual-remaining/resource_quality.json)
- [真实终端stdout/可靠退出0](../evidence/p3_raw_grid/20261012-181149-manual-remaining/operations/manual_run.stdout.txt)、[stderr](../evidence/p3_raw_grid/20261012-181149-manual-remaining/operations/manual_run.stderr.txt)
- [分段与嵌套成本](../evidence/p3_raw_grid/20261012-181149-manual-remaining/costs.json)、[辅助成本去重索引](../evidence/p3_raw_grid/20261012-181149-manual-remaining/final_cost_index.json)

本次QPC10313.8951424s，第二段10447.2303399s，累计包络24330.2994407s，余3952.7696601s。
包络含系统休眠而不是纯计算，离线审核暂停另列；嵌套RAW/门禁/外层包装不相加。
冻结源码/四二进制/reference身份一致，新增setup/reference0；所有本任务实验进程已退出。
只追加新组与原JSONL，旧controller/initial/证书/五组/前缀及上轮101文件不变。
本轮到此停止。请外审裁决本次休眠质量限制和分段结果适用范围；不自动再领窗口、复测或进入算法比较。

## 历史：f19f9f84之后的一次分段续跑交付

**RAW_GRID_RESOURCE_BLOCKED / PARTIAL**。辅助内容`7a8dc17f7e268edcea7ff011b56540725ce65af4`；
实际测量仍准确`3cc9e0d03ba682569fca0e91f28d364f2dab73fa`归档，session
`f705a488d7b442789973381e2190c944`。没有修改冻结测量/时钟/资源协议。
一次性窗口已领取且在资源预检停止；三次完整快照独立复算均只有host_memory拒绝，第四次超时。
本轮新增准入区间/分组检查/4096/小矩阵/reference/配置/轨迹/复测/放弃组均0。
仍5/20有效配置、30/120fresh、10个分组检查，原恢复12区间另计。

优先审计本轮新增内容：

- [外层分段设计与结果、下一步限制](P3_RAW_GRID_SEGMENT.md)
- [授权、328文件/30样本/五组/缓存哈希锁定](../evidence/p3_raw_grid/20261012-144553-segment/window/authorization.json)
- [辅助准确内容、干净导出及字节SHA](../evidence/p3_raw_grid/20261012-144553-segment/auxiliary_freeze.json)
- [15项干净受控测试](../evidence/p3_raw_grid/20261012-144553-segment/tests/clean_auxiliary_tests.stderr.txt)
- [唯一窗口/真实QPC、停止原因](../evidence/p3_raw_grid/20261012-144553-segment/window/window.json)
- [资源原始流](../evidence/p3_raw_grid/20261012-144553-segment/window/preflight_gate/)、[独立判定](../evidence/p3_raw_grid/20261012-144553-segment/resource_rejection_recomputed.json)
- [分段+原测量独立验收](../evidence/p3_raw_grid/20261012-144553-segment/window/independent_segment_audit.json)
- [历史及原六文件字节保护、进程退出](../evidence/p3_raw_grid/20261012-144553-segment/delivery_verification.json)
- [成本包含关系](../evidence/p3_raw_grid/20261012-144553-segment/costs.json)、[窗口原始stdout](../evidence/p3_raw_grid/20261012-144553-segment/operations/segment_run.stdout.txt)
- [闭合22项流/退出码/QPC与链接/误提交检查](../evidence/p3_raw_grid/20261012-144553-segment/closed_packaging_verification.json)、[非重叠辅助成本](../evidence/p3_raw_grid/20261012-144553-segment/final_cost_index.json)

完整性true，正式执行未新增；当前续跑时钟not_performed，Grid/P3完整及比较false。
两段活动包络14016.4042983秒，不跨epoch相减、不叠加内含门禁/组时间。
120秒门禁实测120.1520997秒，约0.152秒停止返回越界如实披露，不接受为PASS。
11017个更早文件原字节不变，原首段controller/checkpoint/CSV/progress/JSONL/initial全不变，
首段证书和原失败记录保留。一次性claim不删除，不自动再跑或开启第三窗口。

## 首段历史交付（3755c4a外审后，f19f9f84已接受）

状态：**RAW_GRID_RESOURCE_BLOCKED / PARTIAL**。
修复协议路径重定位、schema严格binding和QPC发送戳顺序，新增正式RAW协议与独立恢复证书。
运行内容`3cc9e0d03ba682569fca0e91f28d364f2dab73fa`，新Grid session
`f705a488d7b442789973381e2190c944`；候选协议、资源v2、教师C/核心/输入/reference/容差/搜索不改。
唯一恢复12/12、五组前后10/10 RAW均通过，22区间均在未加容差宿主边界内；MONO9项警告保留。
完成5/20配置（仅O0全部块大小）、30/120目标执行，均fresh/全矩阵/RAW契约通过。
O1/s8之前三次host_memory拒绝、第四次采集超时，120秒门禁预算耗尽后停止；余15配置未执行。
已测五配置最低中位数O0/s128为416.593961898秒，不能称20配置最优。

优先核验：

- [完整说明/停止原因/成本/复核入口](P3_RAW_GRID.md)
- [精确内容、协议和双归档Git/执行字节/换行身份](../evidence/p3_raw_grid/20261011-021601/final-content/plan.json)
- [110项双干净回归、一次n17 fresh、20唯一配置及空初始化](../evidence/p3_raw_grid/20261011-021601/final-content/clean_validation.json)
- [原恢复证书](../evidence/p3_raw_grid/20261011-021601/final-content/recovery/certificate.json)、[从原端点独立复算](../evidence/p3_raw_grid/20261011-021601/final-content/recovery_recomputed_archive.json)
- [Grid独立审计](../evidence/p3_raw_grid/20261011-021601/final-content/grid_audit_archive.json)、[原始30条样本](../evidence/p3_raw_grid/20261011-021601/final-content/grid-f705a488/samples.jsonl)
- [检查点](../evidence/p3_raw_grid/20261011-021601/final-content/grid-f705a488/checkpoint.json)、[停止控制器](../evidence/p3_raw_grid/20261011-021601/final-content/grid-f705a488/controller.json)
- [五行有效表](../evidence/p3_raw_grid/20261011-021601/final-content/grid-f705a488/grid_summary.csv)、[20槽完整/未执行状态](../evidence/p3_raw_grid/20261011-021601/final-content/grid_status_20.csv)
- [拒绝门禁及全部原始输出](../evidence/p3_raw_grid/20261011-021601/final-content/grid-f705a488/group_checks/4361ea9b921f4f668e6eaa6952757169/resources/)、[资源质量/RSS/交换](../evidence/p3_raw_grid/20261011-021601/final-content/resource_quality.json)
- [实际Formal终端stdout](../evidence/p3_raw_grid/20261011-021601/final-content/formal_grid.stdout.txt)、[stderr](../evidence/p3_raw_grid/20261011-021601/final-content/formal_grid.stderr.txt)
- [闭合调用命令/退出码/流哈希](../evidence/p3_raw_grid/20261011-021601/closed_operation_verification.json)、[成本包含关系](../evidence/p3_raw_grid/20261011-021601/final-content/costs.json)
- [辅助调用失败与精确归档cwd修正](../evidence/p3_raw_grid/20261011-021601/final-content/auxiliary_invocation_correction.json)、[历史保护](../evidence/p3_raw_grid/20261011-021601/history_protection_after.json)
- [交付计数/独立状态](../evidence/p3_raw_grid/20261011-021601/final-content/delivery_summary.json)
- [提交前运行源码/原件/流哈希/相对链接/凭据模式/进程退出检查](../evidence/p3_raw_grid/20261011-021601/delivery_verification.json)

完整性true；恢复eligible=true、已采RAW检查通过；Grid complete及Grid timing false（15配置未执行）。
P3 execution_complete/timing_checks_pass/comparison_ready均false；Random/Greedy/独立复测本轮均0。
Windows/WSL各110项相关测试分别2/3平台跳过、适用项通过。小矩阵1/reference1，正式reference1；
初始化矩阵/reference为0，恢复与分组探针另计22区间/110响应/11原生进程，不混入目标计数。
11017个旧文件字节、53个原d681归档文件、三campaign及原23条执行/暂停标记保护通过。
原两次辅助CLI/cwd失败及一次收尾自调用记录缺陷完整保留；仅后处理修正，没有重采或冻结源码改动。
本轮停止等待外审。资源通过不是性能稳定性证明；旧Grid不混表、不校准，8小时预算不能静默重置。
提交前85条已闭合operation的流哈希、QPC差和退出码均合法；收尾自身父调用在子退出后另行闭合。
585个本轮证据文件当时约14.4MB，单文件均小于10MiB，无高置信凭据模式或新证据坏链；
准确归档/缓存下的WSL实验进程与Windows主控/启动助手均已退出。无真实终端截图，保留真实终端流。

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
