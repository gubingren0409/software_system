# 首种子正式比较尚未完成（2026-10-20交付）

## 当前：d706a96a后一次人工续跑，Greedy11/12，待机后停止

实际执行内容776b11171d796c8071e69824ffe463c4faf8ba57、session c1bd157c6c8d42439d0fb08f69156ff5不变。
仅新增归档外助手706d239a5f1592dc17fb2ceefa46a2112727f966及14项相关受控回归，干净归档通过；
教师原件、code/autotuner/configs和原搜索实现未改，不额外运行n17/Grid/关闭的三配置验证。
保留旧15841.5879168s，只领取一次剩余27358.4120832s，新claim不能重复使用。

Formal预检、唯一fresh默认libc不绑核短1e9/长1e10共2区间及源码/编译器/缓存核验通过；
无setup/reference生成或性能样本复用。旧O3/s128两条失败尝试按授权列为放弃，原文件不改；
新attempt重新1预热+5fresh完整通过，随后共新增9个完整Greedy配置。
第12个Greedy配置O3/s16仅预热+测量1/2成功、测量3超时（-9），共4条部分记录，不评分、不补齐。
2026-10-19T12:27:28.5899707Z System506原始消息Reason:Lid；12:37:45.3273151Z System507报告
Austerity Battery Drain Budget Exceeded，随后506再次进入待机。日志保留XML；不推断用户意图或时钟校准。
控制器真实退出2，防睡眠请求finally同线程释放；该请求不能阻止合盖。不是资源或RAW检查拒绝。

当前Random12搜索+2去重复测完整且全轨迹原样；Greedy11搜索/0复测。新增目标58，原始总数156且run_id唯一；
150条属25已接纳组（23搜索+2复测），旧放弃2、新部分4均不计分。GreedyB4/B8已形成，B12及所有自身候选复测未完成。
独立evidence_integrity_pass=true；execution_complete/timing_checks_pass/comparison_ready=false（first_seed）；五种子仍false。
本段21个真实RAW区间、与历史合计56区间/332响应全部原始复算通过；部分组缺组后检查及连续性，整轮计时仍false。
本段11资源门禁和11证据卷检查通过；全session含历史共30资源快照、19低内存警告、29证据卷检查。
门禁通过和WSL采样swap=0不证明组内无宿主压力，MONOTONIC差异仍只作警告，不校准成绩。

本段7488.0732714s，旧+本段23329.6611882s/43200s，账面余19870.3388118s；待机/失败不退款。
窗口最终整数QPC端点是成本依据，稍后的live progress多约6.5691ms，不拿该活读数覆盖已闭窗口。
后续离线暂停、复核、测试、Git不算正式活动；两段各自时长相加，不跨epoch相减。该余量不自动授权另一次运行。
Random搜索RAW12370.681806653s、Greedy已接受11组7287.827451217s、Random复测791.041269405s是嵌套分项；
本段共享准备78.7235807s，新失败组RAW250.251100179s与其进程QPC868.4670412s不是同范围，不相减/退款。

16,831旧文件、原98条2378346字节前缀、Random全轨迹及旧Greedy2组哈希/内容保护；
原claim/window/证书、Grid和已关闭18条验证样本不追加。原session只有checkpoint/progress和samples追加被授权变化。
任务实验进程已退出。下一步仅外审/只读复算；再次实验需新的明确授权和不重置累计预算的方案，本轮不启动。
[本段完整证据及只读入口](../evidence/p3_raw_first_seed/20261019-181817-693c9e13-manual-continuation/README.md)、
[六行CSV](../evidence/p3_raw_first_seed/20261019-181817-693c9e13-manual-continuation/first_seed_six_rows.csv)、
[独立验收](../evidence/p3_raw_first_seed/20261019-181817-693c9e13-manual-continuation/continuation/independent_continuation_audit.json)、
[历史/电源/退出核验](../evidence/p3_raw_first_seed/20261019-181817-693c9e13-manual-continuation/stop_review.json)。

## 历史：首次首种子真实搜索PARTIAL，因合盖待机停止

起点efb7f9df，实际执行内容`776b11171d796c8071e69824ffe463c4faf8ba57`，准确Windows/WSL归档，
新session `c1bd157c6c8d42439d0fb08f69156ff5`；matrix input/search seed分别固定20261008。
科学内容3cc9e0d不变；比较验收按mode/first_seed严格计数、重放、复测和退出码，新增证据卷门禁。
工作树/干净Windows/WSL各28项比较相关测试通过，续跑关联17项工作树/干净Windows通过；均为受控测试。
新空session绑定43200s独占claim，旧验证1616.5610957s余量不转移，构建/reference核验后复用，性能不复用。
唯一fresh准入短/长2/2通过；Random12组及去重复测2组完成，然后Greedy完成2组。
第三组O3/s128预热成功、测量1超时（returncode=-9），2条部分样本均不计分。
17:43:18 System506原始消息为Reason:Lid；17:59:55 System507退出Modern Standby。
原控制器先因Windows boot-time估计字符串变化报`Power event log reset or identity invalid`，真实退出2，
没有证据据此声称真正重启或事件日志清空；原始消息另证实待机。防睡眠请求finally同线程释放，进程退出。

计数：14/24搜索组、2个复测组，共16完整组/96已接纳执行；98个run_id唯一、另2条部分执行。
35个真实RAW/QPC区间（准入2＋完整组两侧32＋失败组前1）独立复算通过，208个响应；
失败组缺组后检查、连续性不成立，**整轮timing_checks_pass仍false**，不以其他区间通过冒充完成。
19资源门禁均通过、11次低内存警告；18次实际证据卷检查通过。不是资源或RAW探针拒绝。
evidence_integrity_pass=true；execution_complete/timing_checks_pass/comparison_ready=false（first_seed范围），
five_seed_execution_complete/five_seed_comparison_ready=false。Random三前缀完成不代表两个算法比较完成。
活动QPC15841.5879168s，余27358.4120832s只是账面余量，不自动续领、不退款或补跑。
全部14,221旧证据文件保持字节，包括关闭Grid、验证18条样本、旧失败/claim/证书/预算。
[全部结果/六行表/精确来源/成本](../evidence/p3_raw_first_seed/20261019-132400/README.md)、
[独立验收](../evidence/p3_raw_first_seed/20261019-132400/official_first_seed_audit.json)、
[历史保护](../evidence/p3_raw_first_seed/20261019-132400/history_after.json)。
此轮停止等待外审；下一步若授权续用余量，须先制定不重置claim/预算、保留失败组的新续跑方案，不能直接重跑入口。

## 历史：三配置独立验证已完成；当时真实搜索未执行

起点aac44ef7，用户仅授权一次重试。辅助e8816554b3b9208b0ab4aa00d9adc96b0f692505，
实际测量35a60b0/session9332ead2不变；准确干净辅助归档17项受控回归通过，另3项合成辅助核验通过。
retry-v4绑定已用1469.0700994s及全部旧claim，只用2130.9299006s余量，旧两组不重跑。
Formal预检、唯一短/长fresh RAW、组门禁、组前后RAW、六次正确性及连续性全部通过。
仅新增O3/s24六次fresh，3/3组、18/18目标（3预热+15计分），partial/abandoned目标0，reference生成0。
s24中位数63.240102045s、CV0.504125%、MAD0.273363999s；原两组/旧Grid（含待机）分数均不改。
组同范围QPC387.9632797s、RAW387.957298023s，差0.005981677s，无组内待机。
组门禁host最低648581120B（低2GiB警告），WSL/commit/CPU通过；门槛不改，不声称环境无干扰。
306原session文件、13,711其他证据、原12条字节前缀/旧组保护；原运行器写complete/active=null，只追加6条。
本段514.3688049s，累计1983.4389043s，余1616.5610957s，三配置验证关闭、不转移余量或自动搜索。
独立evidence_integrity_pass/validation_complete/validation_timing_checks_pass均true；
P3 execution_complete/timing_checks_pass/comparison_ready仍false，轨迹/预算前缀复测0。
10月14日两组及19日s24为跨日分段，不是连续同环境实验；旧Grid限制/所有失败仍披露。
[完整证据/源身份/成本/下一步](../evidence/p3_raw_comparison/20261019-122200-user-retry4/README.md)。
当前停止等待外审。下一阶段需另行授权新search session与fresh准入，不复用旧Grid或本session证书。

## 历史：再次人工重试，接电/时钟通过，s24组前资源门禁停止

起点9d271433，辅助02907787f09ee94922d159e6b6bb9a0203c6bde5准确归档；16项关联受控测试
工作树及干净归档通过，3项合成AC拒绝检查通过。原测量35a60b0/session9332ead2不变。
retry-v3独占claim绑定四段旧活动1261.0861871s，起始余2338.9138129s，无退款或新窗口。
AC=1/电量100%，Formal预检通过，唯一fresh短/长RAW2/2及真实缓存/编译器/来源核验通过；不重做setup。
s24组前四个有效快照host最低281374720/325533696/429780992/474804224B，只因host_memory拒绝，
CPU/WSL/提交余量/根盘通过。门禁118.9061907s后停止，控制器退出2，finally同线程释放防睡眠。
新组两侧探针/READY/矩阵0，仍2/3组、12/18fresh，partial/abandoned目标样本0，搜索/前缀复测0。
289原session文件、13,618其他证据、原两组/12条前缀/claim/初始证书保护通过，checkpoint原字节ready。
本段207.9839123s，累计1469.0700994s，余2130.9299006s，不自动继续。本段进程218.5935365s包含活动。
独立evidence_integrity_pass=true；validation_complete/validation_timing_checks_pass与P3三项仍false。
本次2区间通过不证明未执行s24或校准旧Grid。历史失败和待机样本不变，不修改系统/结束用户应用。
[本轮全部证据与边界](../evidence/p3_raw_comparison/20261018-201600-user-retry3/README.md)。
下一步需宿主512MiB以上稳定余量、接电开盖，并明确一次仅用原剩余额度的s24补齐；本轮在此停止。

## 历史：下午第二次明确重试，AC未连接而停止

起点6b1860a，辅助103387cfae82523d9ad42bf4567af42cc2239337，测量35a60b0/session9332ead2不变。
原三段1257.8308447s照计，本次仅2342.1691553s，新retry-v2 claim绑定完整旧链，不删原claim或退款。
15项相关回归在工作树和准确干净归档通过。接电API成功，但ac=0、电量75%，控制器真实退出2。
防睡眠finally同线程释放；资源门禁、RAW短/长、组边界和新目标全部未执行，不是新的内存/时钟失败。
仍2/3组、12/18fresh，active=null、checkpoint原字节ready；287+13,545旧文件与12条前缀保护通过。
本段3.2553424s，累计1261.0861871s，账面余2338.9138129s，不自动继续。
原辅助审计对早期拒绝缺资源文件而integrity=false，原结果保留；单独拒绝审计复算授权/保护/预算、
操作SHA/整数QPC/AC状态及未启动阶段，证据完整性true，3项拒绝合成回归通过，不冒充恢复证明。
validation_complete/validation_timing_checks_pass及P3三项仍false，资源/本轮时钟状态not_executed。
旧两组分数、Grid/待机限制及搜索空观测不变。未结束应用、改系统或清缓存。
[完整说明和核验入口](../evidence/p3_raw_comparison/20261015-152400-user-retry2/README.md)。
下一步先接电、保持开盖，再明确一次原余量补齐；本轮停止，不调用run或启动搜索。

## 历史：用户明确一次重试，组前内存不足/末次采集超时

起点742cac14，外层内容3eaeadd28245664f4ea27bd8e4f79082fcf0124e准确归档，14项相关受控测试通过。
测量35a60b0/session9332ead2881a4c1e91b966e90a0d2057不变。新retry claim只用2553.8794551s，
旧846.073676s和200.0468689s照计，不删除原claim/证书/失败或重跑两组。
证据盘余62714880000B可写；Formal预检host最低1016856576B通过并警告低2GiB，CPU18.8%/31%。
一次默认libc短/长fresh RAW2/2通过，无MONOTONIC辅助警告，不补采。s24组前前三个有效快照
host最低247074816/379310080/341209088B，均仅host_memory拒绝，CPU/commit/WSL不是拒绝原因；
第四次timed_out=true、退出1、stdout空，判unknown而非PASS。门禁119.5028273s，在原120s内停止。
新组前/后探针、READY和矩阵执行均0，checkpoint仍原字节ready/active=null/两组；防睡眠finally释放。
原270个session文件、13,458其他证据和12条字节前缀保持，科学代码/资源策略v2不变。
本段211.7102998s，累计1257.8308447s，余2342.1691553s不是自动再次启动许可。
来源/证据完整性true；validation_complete/validation_timing_checks_pass及P3三项仍false。
仍2/3组、12/18fresh，partial/abandoned矩阵样本0，算法轨迹/前缀复测0。旧成绩不变。
停止后快照显示游戏VALORANT约1.71GiB，不证明其唯一因果；未终止应用或改系统设置。
[完整结果/原始日志/下步](../evidence/p3_raw_comparison/20261015-130000-user-retry/README.md)。
本轮停止并推送。先由用户释放高占用，后续仍只补s24六次、使用原剩余额度，不自动启动搜索。

## 历史：E空间恢复，单次补齐在组前host_memory门禁停止

用户授权补齐磁盘失败，外层助手22fe97c02e2bf1cd56662413e10fc5311113a246准确干净归档，
原测量35a60b0/session9332ead2881a4c1e91b966e90a0d2057不变。没有再创建3600秒预算，
保留原846.073676秒，只用2753.926324秒剩余额度，独占新claim防止重复领取。
新增证据盘1GiB余量+write/fsync/read-back前检通过（62715604992B），不修改资源v2或冻结归档。
正式预检通过：host最低3317710848B、commit余量31561756672B、WSL可用6248665088B、CPU均3.6%/峰6%。
一次fresh短/长默认RAW准入2/2通过，无MONOTONIC辅助警告；旧证书保持，附件绑定当前checkpoint及授权。

O3/s24新资源attempt 91ca8e9806b246f6a1b2d9e2938ec072四个快照都仅host_memory拒绝：
239452160、302333952、394579968、300908544B。CPU均2.2/3.6/10.4/14%、峰4/5/15/27%，
WSL约4.58–5.81GiB、commit余量约25.75–26.01GiB，不是CPU、commit、WSL、磁盘或时钟阻塞。
等待包络120.0005393秒，原严格审计记录超额0.0005393秒而拒绝，不放宽判据、不伪写PASS。
组前/后探针及新目标均0，不是新增部分矩阵组；有效checkpoint仍原字节ready/active=null/两组。
新的外层window stopped，真实退出2；原故障claim/window和片段不动，新防睡眠申请/释放成功。

本段200.0468689s，累计1046.1205449s；账面余2553.8794551s不是新的启动许可。
两次活动QPC包络分别验证后求和，离线排查、用户释放空间、代码/快照/提交单列；嵌套RAW/门禁不叠加。
独立核验253个原session文件、13,354个其他证据和12条样本字节前缀不变，科学源码不改。
evidence_integrity_pass=true（来源/既有测量数据）；validation_complete/validation_timing_checks_pass=false；
P3 execution_complete/timing_checks_pass/comparison_ready=false。累计时钟9区间全部RAW通过，但不能证明未执行的s24。
停止后只读host快照回升4068204544B不等于组前门禁通过，不据此再次尝试；内存变化原因尚未证实。
旧独立结果仍s128 51.602724641s、s64 52.784908609s，s24未执行。没有Random/Greedy轨迹或前缀复测。

[本轮证据和下一步](../evidence/p3_raw_comparison/20261014-204900-disk-continuation/README.md)、
[独立验收](../evidence/p3_raw_comparison/20261014-204900-disk-continuation/continuation/independent_continuation_audit.json)。
当前任务实验进程已退出；下一轮先复核失败门禁及内存稳定性，再明确授权使用原剩余额度的一次补齐，不重置预算。

## 历史：新AC授权验证完成两组，E证据盘耗尽后停止

基于c08184e的新授权，不重用旧claim：执行35a60b090b728d2ec3b6a8ea014beac69fe3766d，
新session `9332ead2881a4c1e91b966e90a0d2057`，科学/搜索/计时/资源协议均未修改。
新归档/编译器/缓存身份核验通过，复用已通过的双端19项测试，不重复110项或n17。
ACLineStatus=1；临时防睡眠申请及finally同线程释放成功，两个完整组无待机事件。

一次短/长准入2/2通过、10响应完整，新证书绑定新session。组前后已采5区间全部通过：
s128两侧、s64两侧、s24仅组前，合计7区间，无RAW失败/MONOTONIC准入警告。
按顺序完成s128、s64各1预热+5fresh：12/18次、2/3组，全部全矩阵/RAW整数契约通过。
s128中位数51.602724641s、CV1.7022%、MAD0.449608174s（比原Grid+1.1892%）；
s64中位数52.784908609s、CV1.7756%、MAD0.242572761s（+0.6019%）。不替换旧Grid或取两轮较小值。

s24组前门禁/时钟通过，但WSL写活动检查点EIO，Windows失败保存又报ENOSPC。
E:只剩16384B，WSL根盘仍有223129370624B；原门禁仅检查根盘，不能证明E证据盘可写。
第三组没有READY/目标process.json，没有任何矩阵样本；剩6次未执行，部分矩阵样本0，失败启动attempt1。
有效checkpoint保留ready/active=null/两组，这是最后持久化状态；window stopped且控制器真实退出1。
没有手工改checkpoint、删临时片段或重启。预算窗口QPC846.073676s，原claim保持。

独立验收完整性true；validation_complete/validation_timing_checks_pass=false，P3三项仍false。
Random/Greedy、预算前缀与候选复测均未执行；旧空search session及旧Grid未改。
13,231个历史证据文件全部字节一致。290个本轮文件先复制到C并逐SHA核验，保留两段失败临时片段。
E空间不足无法提交，使用同历史C应急副本提交推送；原E HEAD仍c08184e且原文件不动，不强制同步。

下一步：先外审磁盘故障及两组证据；恢复E空间后安全同步原工作树，并审定证据盘空间准入与
ENOSPC保存失败回归/续跑方案。当前one-shot不能直接重启，剩余额度不是自动重试授权；本轮停止。
[完整新批次](../evidence/p3_raw_comparison/20261014-182807-ac-validation/README.md)、
[独立验收](../evidence/p3_raw_comparison/20261014-182807-ac-validation/independent_validation_audit.json)、
[结果和波动](../evidence/p3_raw_comparison/20261014-182807-ac-validation/three_configuration_comparison.csv)。

## 历史：独立RAW入口已冻结，验证因未接电停止

基于e1b3a7ee，本轮没有真实Random/Greedy搜索。新增比较协议v1，新运行内容
`35a60b090b728d2ec3b6a8ea014beac69fe3766d`，继承科学测量内容3cc9e0d及原协议/资源v2。
validation session `f9f3bb0d54724d2385a8b77be26a99b3`；search session
`d7a9ba9fc5384990b739ff51363a03e5`完全空观测。原f705a488 Grid已关闭，不再修改/追加。

双干净归档各19项新受控回归、CLI、20唯一配置及科学源码/缓存哈希通过，没有额外n17或110项重复。
新主控临时防睡眠成功申请/释放，按System RecordID跟踪待机；组内待机或同范围QPC/RAW
差超过max(30s,5%RAW)将保留受扰组并停止。策略只能获得自身观测，候选复测不反馈。

唯一3600秒验证窗口在准入资源检查之前因Windows ACLineStatus=0（查询成功、电量72%）停止。
实用QPC2.428145s，外层进程3.1998347s，范围嵌套。claim保留，不重置、不自动再次启动。
Recovery/Formal门禁均**未执行**；短/长准入0/2、组边界探针0、4096目标0/18、组0/3、
部分/放弃矩阵组0、候选复测0、两算法观测/轨迹0。没有新时钟失败，不应描述为CPU或内存阻塞。

独立验收evidence_integrity_pass=true；validation_complete/validation_timing_checks_pass=false；
P3 execution_complete/timing_checks_pass/comparison_ready全部false。
三个原Grid分数旁列，新分数/CV/MAD/变化均“未执行”，六行预算表仅结构，不含假执行器成绩。
已闭合历史2089文件全部字节相同；原Grid准确归档只读审计仍20/120有效。
O3/s24受扰事实及原样本不删、不退款，其他组连续性未认证，不能倒推为连续执行。

后续先外审本轮入口，连接AC/保持开盖，再明确授权新的有限验证活动；当前plan再次调用会拒绝，
不能删除claim或借旧Grid证书。长搜索建议约7–10小时，独立固定12小时预算需另获审核授权；
不承诺全部完成，不扩种子/算法。任务进程已退出。
[全部交接](../evidence/p3_raw_comparison/20261014-102833/README.md)、
[独立验收](../evidence/p3_raw_comparison/20261014-102833/independent_validation_audit.json)、
[代码与冻结协议](P3_RAW_COMPARISON.md)。

## 历史：RAW Grid完整，首种子搜索比较仍未运行

9f714a72后用户明确允许一次人工续用原剩余额度，旧133.3351975秒继续计费，不重置或开启第三窗口。
辅助内容957576ca、测量内容3cc9e0d/session f705a488；原资源v2/计时/输入/核心/评分/搜索均不变。
干净归档20项受控测试通过；原Formal预检在120秒内先REJECT后PASS，全部原样保存。
唯一两区间fresh准入RAW2/2通过，MONOTONIC差异仅辅助警告。index5–19串行完成新增15组/90fresh，
完整Grid20/20、120唯一fresh（20预热/100测量）、40/40分组RAW检查，active=null、partial=0、abandoned=[]。
原12区间恢复证书不改，本次2区间为续跑附件，不是第二套恢复证书。

测得最低中位数O3/s12850.996291138秒，CV0.4313%、MAD0.229528039秒；没有独立复测或算法轨迹。
独立验收evidence_integrity_pass=true、grid_complete=true、grid_timing_checks_pass=true；
**P3 execution_complete/timing_checks_pass/comparison_ready仍false**。
本次O3/s24测量5期间有Kernel-Power506/507明确的合盖Modern Standby，约36分钟（UTC事件标签差）。
冻结RAW契约和两侧检查通过不证明整次矩阵执行未暂停；该样本/统计原样保留，不剔除、不重跑、不校准。
排名为实际观测，不能表述成稳定性保证或物理时钟绝对精度认证。

本次QPC10313.8951424s，第二段含旧失败尝试10447.2303399s；含首段累计24330.2994407s。
该包络含休眠；审核/人工离线等待单列，只加各epoch时长，不跨epoch减绝对端点。
原329文件、五组、30条前缀、上轮101文件、11017更早文件及教师原件保持；原controller只描述首段。
进程均已退出，不调用剩余预算、不启动Random/Greedy或最优复测，等待外部审计。
[完整交接](../evidence/p3_raw_grid/20261012-181149-manual-remaining/README.md)、
[独立审计](../evidence/p3_raw_grid/20261012-181149-manual-remaining/window/independent_segment_audit.json)、
[休眠定位](../evidence/p3_raw_grid/20261012-181149-manual-remaining/standby_analysis.json)。

## 历史：一次新分段窗口在资源预检停止

基点f19f9f84，辅助内容`7a8dc17f7e268edcea7ff011b56540725ce65af4`；正式测量内容仍3cc9e0d，
session仍f705a488。15项受控测试及其干净导出通过；没有重复110项或n17。
只领取一个新窗口。Formal预检三个完整快照仅host_memory拒绝（最低457887744、397090816、
316342272B），第四次超时无输出；原策略v2、CPU与WSL等规则不变。
本轮fresh续跑准入**未执行**，不是RAW失败；新配置/探针/目标/放弃组/复测均0。
原checkpoint、五行CSV、controller、30条JSONL、五完整组、初始检查点及第一段证书均原字节不变。
继续为5/20配置、30/120执行，余15仍从index5/O1/s8开始，Random/Greedy和前缀复测未运行。
证据完整性true；Grid complete、全Grid timing、P3 execution_complete/timing_checks_pass/comparison_ready均false。
当前没有实验进程。一次性claim保留；本轮不再调用run或重置窗口，下一步等待外审明确剩余额度的
后续授权，并先解决实际宿主余量。收尾内存快照不是新Formal门禁，不追认拒绝通过。
[当前分段入口和成本](P3_RAW_GRID_SEGMENT.md)、
[独立验收](../evidence/p3_raw_grid/20261012-144553-segment/window/independent_segment_audit.json)。

## 首段历史：正式RAW Grid部分完成，资源门禁停止

状态 **RAW_GRID_RESOURCE_BLOCKED / PARTIAL**。运行内容
`3cc9e0d03ba682569fca0e91f28d364f2dab73fa`，新Grid session
`f705a488d7b442789973381e2190c944`，正式RAW协议`2026-10-11-raw-formal-v1`。
唯一fresh恢复12/12通过，5配置两侧10/10 RAW检查通过，所有22区间连未加容差边界也通过。
O0/s8、16、24、64、128完成：5/20有效配置、30条唯一fresh执行（5预热+25测量）。
无部分执行、放弃组、独立复测或搜索轨迹；O1/O2/O3的15配置未执行。
已测最低中位数O0/s128为416.593961898秒、CV0.254%、MAD0.557350426秒；不是全Grid最优。

O1/s8前Formal v2门禁三次因host_memory拒绝，最低可用分别521515008、437022720、
189259776 bytes；CPU、commit余量和WSL容量不是这三次拒绝原因。第四次采集超时无JSON。
120秒预算耗尽后停止，实测门禁QPC120.5548004秒（轮询/终止收尾约0.555秒超出预算边界），
不重采recovery、不自动再启门禁、未结束用户应用或改系统设置。
检查点`ready`表示五组已接纳、无活动组，不表示Grid完成；控制器为`blocked_or_partial`。
总预算从恢复开始计，停止时QPC13883.0691008秒，未用完的预算不重置或转作新恢复。

验收：证据完整性true；唯一恢复eligible及已采RAW检查true；Grid完成/全Grid计时验收false。
P3的execution_complete、timing_checks_pass、comparison_ready仍全false（未运行两算法）。
旧d6811cad与7405fcc3仍空、旧e308bfb的3完整/23执行/5部分执行和暂停标记均不变。
双干净归档110项相关测试分别2/3平台跳过、一次n17 fresh校验通过，不能代替未执行的15配置。

[完整结果、成本、来源及只读入口](P3_RAW_GRID.md)、
[独立审计](../evidence/p3_raw_grid/20261011-021601/final-content/grid_audit_archive.json)、
[20槽状态表](../evidence/p3_raw_grid/20261011-021601/final-content/grid_status_20.csv)、
[历史保护](../evidence/p3_raw_grid/20261011-021601/history_protection_after.json)。
本阶段停止等待外审；不自动运行Random/Greedy或重置8小时预算。

## 历史：P3_RAW_CLOCK_CANDIDATE_READY，未恢复正式实验

审计基点da0afd87。预提交a498263后一次固定工作量诊断22/22完整、90响应一致；
RAW22/22通过且保守范围均在未加容差宿主[L,U]内，MONOTONIC失败0/2/7/11/21保留。
通过后冻结RAW候选 `3c7a4ab11f7e753936ab8735e03364b44b4dd1ef`，协议
`2026-10-10-raw-candidate-v1`；工作副本主时钟及严格整数端点契约改为RAW。
原始C、核心循环、输入/容差/reference、20空间/搜索、资源v2未改。
双干净归档80项相关测试（各跳过2项）、CLI、20配置、n17 fresh/289元素和独立审计通过。
原件目录非运行元数据CRLF/LF造成首次身份拒绝，原失败保留；修正身份选择后仅重新审计，
不重跑小矩阵，不改变执行源码或教师C字节规则。

正式content d6811cad/session `2c270825458a4857a5ac9df5aadf597b`仍为空；不创建新正式session，
不生成恢复证书。本轮recovery区间0、Formal门禁未执行、4096目标0、搜索配置/轨迹/复测均0。
evidence_integrity_pass=true；候选参考/验证通过；正式execution_complete、timing_checks_pass、
comparison_ready均false（未执行，不是将RAW诊断标为失败）。
10760项旧文件字节、51项原正式归档、三个campaign检查点及旧23条执行/部分组/暂停标记保护通过。
未自动调整系统或重启WSL；本任务拥有的实验进程0。

[本轮完整说明](P3_RAW_CLOCK_CANDIDATE.md)、
[独立诊断](../evidence/p3_raw_candidate/20261010-234702-fixed-work/final_independent_diagnostic.json)、
[交付/成本/历史保护入口](../evidence/p3_raw_candidate/20261010-234702-fixed-work/delivery_summary.json)。
当前入口显式禁止candidate-only协议启动recovery/Grid/campaign，避免套用旧MONO/RAW相等门槛。
下一轮先外审候选，再授权版本化RAW准入、fresh宿主/来宾恢复证据、新session及匹配fresh Grid。
旧Grid继续只是有限历史参照，不自动重新搜索或扩展种子。

## 历史：50cd24e后唯一30区间有界诊断

先提交方案/源码7950a8a533f5c60dd8fb7a0d26cb90a3e3d2b32d，再冻结编译/二进制/manifest，
一个持续原生PID收集A10空闲、B10忙工作、C5系统调用空闲、D5临时绑核空闲。
默认MONOTONIC A10/10、B8/10匹配宿主有界QPC，C/D各5/5；RAW30/30匹配宿主。
零起点B1/B2分别超U+a至少46.355/132.330ms；全部边界不确定性≤1.2861ms，没有宽边界
或回退。执行预声明第3项：不认证默认C计时路径，不修改时钟准入、不恢复正式实验。
具体读数、环境、未知根因和下一步见[P3_CLOCK_REFERENCE](P3_CLOCK_REFERENCE.md)。

本轮新recovery0、Formal门禁未执行、正式目标0、配置0/24、轨迹0/2、前缀0/6、复测0。
四验收evidence_integrity_pass=true、execution_complete=false、timing_checks_pass=false、
comparison_ready=false，另reference_match_pass=false。正式content d6811cad/session
2c270825458a4857a5ac9df5aadf597b仍initialized/空观测，没有新session或成绩迁移。
内存/CPUv2、矩阵C/输入/容差/计时/搜索/1+5fresh/中位数均不变；旧6/20仍失败。
10623项历史字节及51项原正式归档身份、各session检查点和旧23条执行保护通过，无实验进程。
11项相关回归及准确内容干净复验通过，测试通过与正式比较完成严格分开。

[交付摘要](../evidence/p3_clock_reference/20261010-190645-1375f246/delivery_summary.json)、
[独立复算](../evidence/p3_clock_reference/20261010-190645-1375f246/independent_diagnostic.json)、
[成本](../evidence/p3_clock_reference/20261010-190645-1375f246/costs.json)。
本轮停止等待外审，不追加诊断、不循环recovery、不启动原命令绕过失配；
旧Grid只保留有限历史参照，不校准或声称同协议全局最优。

## 历史：ac33d9d后内存准入v2及唯一新恢复

用户授权将宿主物理可用与提交额度余量独立设置为512MiB底线，宿主低于2GiB仅警告；
Recovery WSL至少256MiB，Formal仍2GiB。CPU/磁盘/120秒等待及测量、C、搜索均不变。
新策略、真实读数、缺失项和成本见[P3_MEMORY_POLICY](P3_MEMORY_POLICY.md)。

实际内容 `d6811cadda8ecd7b46225ebe65c51831278694a0`，干净归档
`/var/tmp/matrix-autotuner-p3-memory-content-d6811cadda8ecd7b46225ebe65c51831278694a0`，
新空session `2c270825458a4857a5ac9df5aadf597b`，
campaign位于`evidence/p3_memory_policy/20261010-174802-11f7775c/campaign-d6811cad/`。
51项运行来源通过；干净归档28项相关单测（1跳过）、CLI/20唯一配置、n17 fresh/289元素通过。
没有导入旧完整组或部分样本，原7405fcc3和e308bfb封存。

17:55初始真实采集host最低434728960 bytes不足新512MiB，仍REJECT；18:06唯一recovery
自己的资源采集host最低3927523328、提交余量26103156736、WSL6210179072 bytes，PASS。
CPU24.2%/31%只警告，分页计数原样保留。两次不同窗口不能用于确认内存回收原因。
A/B原始20区间全部保存，MONOTONIC/RAW有6项失败（零起点A3/6/8、B1/8/9），
REALTIME/RAW20项及Windows同调用UTC/QPC两项均通过。原容差未放宽、无筛选或校准。
入口和独立审计真实退出均2，`recovery_eligible=false`；不调用resume、不重复探测。

| 独立验收 | 结果 |
|---|---|
| evidence_integrity_pass | true：实际新批次来源、整数端点及完整20区间 |
| execution_complete | false：0/2完整轨迹 |
| timing_checks_pass | false：6个MONOTONIC/RAW区间失败 |
| comparison_ready | false |

Formal门禁**未执行**，不是失败或PASS；4096目标0、配置0/24、前缀结果0/6、独立复测0，
新部分组/放弃组均0。新检查点仍initialized。n17是独立诊断数据，不是正式配置分数。
本轮到此停止，等待外审及有依据的时钟处理方案；不结束用户进程、不调整系统设置。
下一轮若源码不变，可保留此空session，但须新授权和新唯一recovery目录，不得复用失败证书。
历史Grid仍是带时钟/资源限制的旁列参考，不是新条件下全局最优证明。

独立验收：[independent_recovery.json](../evidence/p3_memory_policy/20261010-174802-11f7775c/independent_recovery.json)；
完整摘要：[delivery_summary.json](../evidence/p3_memory_policy/20261010-174802-11f7775c/delivery_summary.json)。

## 历史：b19e6cd 后7405fcc3的唯一新恢复调用

用户本轮新授权一次recovery，并在全部条件通过后直接恢复首种子。实际内容仍为
7405fcc37074ab815294ba401d5cf5e8280f3d5f、既有session3768a29ade69408da4c5d0c4404ba44e，
没有重建或迁入旧观测。50项归档SHA及工作区内容身份通过，原检查点保持initialized。
Recovery入口真实退出2：CPU采样17/5/13/27/11%只警告；宿主可用内存最低775036928
bytes（0.722GiB）不足2GiB，具体拒绝host_memory。WSL内存/根盘通过。

A/B区间0，时钟与Formal门禁均未执行，未调用resume或矩阵，不自动第二次recovery。
新session完整配置0/24、轨迹0/2、原始目标执行0、部分/放弃组0、独立复测0。
独立验收四项均false：第一项因没有两窗口原始证据，不是冻结源码哈希失败。
已保存操作流哈希通过，10357项历史保护核验通过；无正式进程/runner锁可获取。
16:18收尾单快照显示内存升为7.768GiB，但不同时/不同API，不能冒充新门禁或翻写REJECT。
本轮详细证据、成本和下一轮入口见[7405fcc3首种子恢复](P3_FIRST_SEED_7405FCC3.md)。

## 历史：aae4147 后资源策略迁移与e0353bf失败批次

用户授权将 CPU 准入调整为 Recovery 仅警告、Formal 均值≤30%/最高≤60%。
集中策略与来源、全新 session 的身份、一次有限 recovery 计划及实际结果见
[P3_RESOURCE_POLICY](P3_RESOURCE_POLICY.md)。原 session 的3配置/23执行及部分组全部封存，
新版从空观测开始，不能迁入旧分数。新源码已修改，不能继续声称执行身份为 fa59701。
本轮唯一recovery全部20区间/两个宿主检查通过，来源50/50匹配；新的Formal门禁及
实际失败调用的批前/批后各3区间也通过。执行内容e0353bf、session920aee4663ff44b084cd11d35eeeadbb
的campaign调用退出1，内部UNC资源采集解码异常，未启动矩阵，配置0/24、轨迹0/2、复测0。
修复后的内容7405fcc37074ab815294ba401d5cf5e8280f3d5f经双干净归档验证通过；
新空session3768a29ade69408da4c5d0c4404ba44e仅初始化。唯一recovery额度已用，旧通过
证明不移用到修复后身份，不再自动恢复。下一轮新有限复核授权及入口见策略文档。

| 验收范围 | evidence_integrity_pass | execution_complete | timing_checks_pass | comparison_ready |
|---|---|---|---|---|
| 实际e0353bf恢复/失败调用 | true | false | true | false |
| 当前修复后7405fcc空session | true（身份/无观测） | false | false（未执行） | false |

本次不是时钟失败或CPU仍阻塞。旧Grid/P3计时与资源限制保留，不校准历史成绩。

## 历史：e4f93333后管理员处理核验，未同步/CPU门禁阻塞

实际管理员日志为
[`admin-20261010-135245/admin-session.txt`](../evidence/p3_clock_repair/admin-20261010-135245/admin-session.txt)。
W32Time Running，配置/源/peers有完整输出，仍是既有time.windows.com,0x9；这些查询
没有各自的可靠原生退出码记录。resync有执行输出但报告无可用时间数据，记录的0与
语义冲突，脚本来源未提供，不能确认该0是可靠原生退出码。操作后Leap=3/层次0，
本轮13:56只读查询仍如此，最后同步错误为1。未再次resync，未修改配置或系统设置。

新唯一目录为`evidence/p3_clock_repair/20261010-135557/`。原Formal门禁只执行一次：
宿主最低2724028416字节（2.537GiB）、WSL6215512064字节（5.789GiB）、swap使用0，
内存恢复并通过阈值；CPU五次13/9/16/18/15%，平均14.2%>10%，最大18%通过20%。
因此门禁REJECT/退出2，未启动recovery或矩阵。新时钟区间0；状态是**未执行**，
不是20项通过或新20项失败。也没有把旧检查的PASS移用给此批。

正式content=e308bfb、session=dc1c292900654d44b36a72548b95a610和辅助fa59701不变。
仍random 3/12、greedy 0/12，0/2轨迹、23执行（18完整组、3已放弃、2待重启），
六行预算结果与候选复测均0。原检查点/JSONL/run_id/完整观测及PAUSE_REQUEST未改，
32项冻结哈希匹配；本轮只做必要后处理，不重跑28项回归、4096或历史正确性案例。

[本批独立验收](../evidence/p3_clock_repair/20261010-135557/independent_acceptance.json)：
evidence_integrity_pass=true（管理员日志/门禁/来源/历史保护范围），execution_complete=false，
timing_checks_pass=false（not_performed），comparison_ready=false；要求两轨迹完成的退出码2。
没有正式实验进程，原runner锁可用。各项正式成本增量0；辅助命令及历史嵌套成本另列，
见[P3_CLOCK_REPAIR](P3_CLOCK_REPAIR.md)。本阶段到此停止，等待审计；未消耗本轮一次
recovery额度，也不在交付后自行重试。后续须明确同步处理结果并通过新Formal门禁，
再获下一轮指令以新唯一目录执行有限验证；原运行器才可归档那2条未完成样本。

## 历史：aedf028a 后集中诊断，权限/资源阻塞

本轮完成只读环境诊断、旧20区间独立复算和28项针对性回归；没有有效环境处理，
因此新 recovery/resume/矩阵执行均为0。W32Time Running但Leap=3未同步，当前token
非管理员，source/configuration查询0x80070005；未越权或执行resync。原正式资源
门禁也拒绝：宿主最低422170624字节，WSL4913426432字节，CPU均值2.8%/最高13%。
辅助七文件与fa59701一致；正式e308bfb/session dc1c292900654d44b36a72548b95a610不变。

当前验收为 evidence_integrity_pass=true（诊断及历史保护）、execution_complete=false、
timing_checks_pass=false（新复核未执行）、comparison_ready=false。仍随机3/12、
贪心0/12，23条原始执行，旧3条abandoned和新2条pending_restart均不计分，复测0。
32项实际冻结哈希匹配，10213个历史/实现文件字节不变，PAUSE_REQUEST未动。
旧20条仍20个MONO/RAW、2个REALTIME/RAW失败，根因未确认，不校准旧数据。

详细结论、权限所需准确命令和下一阶段条件见[P3_CLOCK_REPAIR](P3_CLOCK_REPAIR.md)；
[本批独立后处理](../evidence/p3_clock_repair/20261010-121004/diagnosis_analysis.json)。
请先完成管理员只读配置核验及适当时的一次resync并返回证据；恢复资源后交外部
复核，再在新批次进行限定验证。本轮到此停止，不直接再次recover/resume。

## 历史：fdeed77 修复与 10-09 有限复核

依据`fdeed77c43dcbbf74de46968055677f97fed8faf`继续，初始工作区干净；Windows fetch
遇失效本机代理，WSL fetch origin成功，未改TLS/代理。正式3配置、23条记录及全部
历史证据保持。新辅助契约v2和唯一20区间计划见[P3_CLOCK_CONTRACT](P3_CLOCK_CONTRACT.md)。
初始检查点、ID/哈希及测试记录位于`evidence/p3_clock_contract/20261009-180810-0491a4ec/`。
辅助内容`0c6ee7e3726a01339d36e6ae7d19b0966dc043cd`已从WSL/Windows干净归档验证：
WSL全套71项单测（1项Windows专用跳过），Windows旧7项与新18项均通过，CLI、
20唯一配置、历史证据及25文件Git/实际身份通过。只有PS脚本存在预期LF/CRLF差异；
老师原件字节完全一致。[15条命令](../evidence/p3_clock_contract/20261009-180810-0491a4ec/clean-0c6ee7e/commands.json)。
这些测试不代表正式比较完成；更早precommit日志是中间版本，不能替代该干净验证。

18:39–18:41按先落policy的唯一次方案完成A/B各10×3秒，**没有恢复campaign**：

| 窗口 | MONO/RAW失败 | REALTIME/RAW失败 | Windows UTC/QPC秒 | 宿主同调用检查 |
|---|---:|---:|---|---|
| A | 10/10 | 1/10（第4区间） | 29.5880455 / 29.5913338 | PASS |
| B | 10/10 | 1/10（第4区间） | 29.4256449 / 29.4254076 | PASS |

MONO/RAW绝对差96.361–157.728ms，冻结允许差33.442–34.140ms，20个区间全部不通过。
原始schema/端点/delta/操作来源逐项复算通过；不筛失败区间，不用比例校准历史数据。
[全部20条分析](../evidence/p3_clock_contract/20261009-180810-0491a4ec/clock_review_analysis.json)、
[policy/manifest及原始读数](../evidence/p3_clock_contract/20261009-180810-0491a4ec/recovery/)。
原探针两次均退出0，Windows入口可靠记录退出2；工具外层PowerShell以1表示非零子进程。
没有实际campaign调用，批前/批后字段为未执行，campaign_returncode为unknown（非成功）。

本次正式资源门禁同时拒绝：宿主最低2113110016字节（1.968GiB），WSL5035520000
字节（4.690GiB），CPU均值7.4%/最高12%，swap使用0。根盘空闲224183226368字节。
之前干净验证时门禁PASS不能代替此快照。Windows10.0.26200，宿主启动17:20:44；
WSL Ubuntu24.04/6.18.40.1，启动18:36:44，clocksource=tsc，NTP报告已同步。
只读事件查询保留最近24小时最多30条ID/时间；它们及NTP状态不证明时钟准确或根因。
两个REALTIME异常区间也保留，原因仍unknown，未调整任何系统设置。

复核暴露辅助身份清单的判据路径错误；原e308bfb不含后来新增的判据文件，原身份
检查据实失败。v2.1已修正辅助路径并增加回归；[补充32项哈希](../evidence/p3_clock_contract/20261009-180810-0491a4ec/identity_location_correction.json)
一致。原失败manifest/check/summary完整保留，补充核验不追认PASS、不授权resume。
详见[迁移说明](P3_CLOCK_CONTRACT.md)。

当前仍随机3/12、贪心0/12，0/2完整轨迹、23条原始执行；18条属于完整组，旧3条
abandoned、新2条pending_restart，均不计分。原campaign检查点、run_id、JSONL字节
与完整观测未变，新增正式配置/执行/复测均为0。剩余21配置和各前缀候选复测。
原活动成本7120.754915s、门禁/等待1165.348475s、终态调用3668.358619s、部分组
进程2236.427057s、复测0；本轮增量0，各范围嵌套不相加。唯一次复核整个Windows
入口QPC93.366197s（内含两探针、门禁、哈希与元数据），辅助命令另列，不混入campaign。

下一步仅外部审计和只读复算。不得直接再次recover/resume；需要先确定环境/时钟
问题处理方案及新的有限验证授权。如果改变正式计时协议，必须另起匹配Grid基线。

最终辅助内容`fa597017c2317772a0f7f34faa75194ffecec8f2`已经双干净归档复验：
WSL74项（1项Windows专用跳过）、Windows旧7/新21项通过；CLI/20唯一配置、导入、
历史证据及Git/执行字节身份均通过。[最终15条命令/摘要](../evidence/p3_clock_contract/20261009-180810-0491a4ec/clean-fa59701/)。
该摘要只认证代码及历史未完成验收模式，不认证此次真实时钟通过。实际复核
[最终后处理](../evidence/p3_clock_contract/20261009-180810-0491a4ec/final_recovery_acceptance.json)
保留原身份拒绝，退出1；原始窗口完整性通过、计时失败，不伪装为仅未完成退出2。
恢复-only不能认证完整campaign的回归也通过；没有固定false掩盖真正完成的batch验收。

19:01验证阶段新资源快照另拒绝CPU均值12.8%（门槛10%），最高18%；宿主
2241531904字节、WSL5041565696字节。这不替代18:40的内存拒绝，也不解除时钟阻塞。
18:58只读补充WSL包3.0.1.0/Windows完整版本10.0.26200.9457及Windows w32tm状态：
Leap=3未同步、源Local CMOS Clock；WSL先前报告已同步。它们是不同来源/时间，
不能据此断言异常因果。[原始与解码说明](../evidence/p3_clock_contract/20261009-180810-0491a4ec/extra_metadata_readable_v2.json)。

[最终保护/进程核验](../evidence/p3_clock_contract/20261009-180810-0491a4ec/final_state.json)：
初始10个受保护文件的运行时字节哈希全相同，PAUSE_REQUEST仍在，原件SHA正确，
正式进程清单为空、原runner锁可获取，未终止用户应用。辅助操作已记录的非重叠
QPC合计627.847147s；[逐项成本与排除项](../evidence/p3_clock_contract/20261009-180810-0491a4ec/auxiliary_cost_index.json)
排除嵌套子操作，且不包含后续推送、未记录编辑/模型开销，不能称完整轮次总时间。

可执行的下一步仅只读复算（output使用新文件，非正式恢复命令）：

```powershell
python scripts/audit_p3_first_seed.py --batch evidence/p3_clock_contract/20261009-180810-0491a4ec/recovery --clock-recovery evidence/p3_clock_contract/20261009-180810-0491a4ec/recovery --output build/p3_clock_contract_recheck.json --require-two
```

预期退出1（保留的原始身份清单错误）；必须同时查看20条raw复算与补充位置核验，
不能据单一退出码判断算法完成。本轮不再执行recover/resume，等待外部审计。

## fdeed77 交付时的历史状态

当前状态为 **P3_CLOCK_BLOCKED**，不是READY。审计基点为
`e46b96cff35e7ea3b23c0b1eaef5fc66b03399ec`；保留其后68392db内容及已有工作。
只授权seed=20261008的随机、贪心各12配置和前缀候选复测，未扩展五种子。

## 身份和进度

正式执行仍用原内容`e308bfb873e6811c50ad685a979af345302fda8d`、原归档、固定
[Git身份](../evidence/p3/content-e308bfb/git_identity.json)、原cache与
[campaign检查点](../evidence/p3/campaign-e308bfb/checkpoint.json)。session仍为
`dc1c292900654d44b36a72548b95a610`，测量/搜索/campaign协议及输入、循环、容差不变。

- 随机3/12，贪心0/12：首批3/24个完整配置，0/2条完整轨迹，尚余21配置及候选复测。
- 23条原始执行：18条属于3个完整组，旧O0/s8的3条已abandoned，新attempt的2条
  于14:22按暂停请求中断组，留存为pending_restart；这5条都不产生配置分数。
- 原3个完整观测及原21条记录未改动；下一次真正恢复会放弃新2条部分组，完整重做
  一次预热和五次新测量。不能从性能缓存或旧部分组凑齐重复。
- 还没有完整4/8/12前缀、候选独立复测或两算法质量比较。原Grid表只作后续事后
  参照，诊断读数没有反馈策略，历史pilot没有改标为正式数据。

## 实际恢复尝试和边界时钟

[14:04批次](../evidence/p3/first-seed-e46b96c-20261009/controller.json)的前后检查都PASS；
新增2条样本后因用户暂停请求安全停止，主控退出2。16:38用户再次明确要求继续。
首次后台启动因Windows PS模块路径缺少Get-FileHash失败，尚未启动目标；
[原始stderr](../evidence/p3/first-seed-e46b96c-resume-20261009-1639/controller.stderr.txt)
保留，未获得该已结束后台进程的可靠退出码，明确为未知。
仅为新子进程指定Windows PS系统模块路径后修复，不改脚本字节或系统设置。

[16:42恢复主控](../evidence/p3/first-seed-e46b96c-resume-20261009-1643/controller.json)
使用相同脚本SHA、e308bfb归档和参数。其批前检查失败，**没有调用正式campaign**；
退出前检查也失败，原检查点/活动成本不变。短检查scope是WSL同区间时钟，以及
Windows完整调用的UTC/QPC一致性；不把宿主整次调用与三个sleep之和直接比较。

| 检查 | MONOTONIC s | RAW s | 绝对差 ms | 允许差 ms | 判定 |
|---|---:|---:|---:|---:|---|
| 批前第3区间 | 3.001954764 | 2.966602491 | 35.352273 | 34.666025 | FAIL |
| 退出前第1区间 | 3.000338465 | 2.963099324 | 37.239141 | 34.630993 | FAIL |

之后先声明[限定复核规则](../evidence/p3/clock-recovery-20261009-1646/policy.json)，
唯一一次10×3秒探针保留所有[原始纳秒端点/读数](../evidence/p3/clock-recovery-20261009-1646/probe.json)：
5/10个MONO/RAW区间失败，最大绝对差39.919ms；REALTIME/RAW十条均通过。
判据仍为`abs(MONO-RAW)<=5ms+1%*RAW`，不改限值、不筛值、不继续探测到偶然通过。
[判据复算](../evidence/p3/clock-recovery-20261009-1646/check.json)。tsc与NTP同步状态
不证明独立物理时间精度，根因未确认。没改频率/内核/WSL配额/安全策略/计时源。

16:56[正式资源复查](../evidence/p3/first-seed-review-20261009-1658/resource_gate.json)
通过：宿主最低2.76GiB、WSL3.93GiB、CPU平均5%/最大7%，swap使用0、根空闲约209GiB。
这是新快照，不冒充16:42条件；资源PASS不解除时钟阻塞，也不保证运行期间平稳。
旧诊断Windows确为运行中约30秒采样（中位33.111s），72条中的44条低内存及一次
CPU21%的警告保留，不追认旧结果稳定。

## 成本与核验

原campaign未校准MONOTONIC累计活动7120.754915秒，其中门禁/等待1165.348475秒；
3个终态搜索评估调用3668.358619秒；5条不计分执行进程累计2236.427057秒。
独立复测为0。各层级嵌套，不相加。活动成本不含离线暂停，新恢复前的时钟检查/
独立复核/只读验证也不混入此成本；辅助操作耗时各自见command/controller记录。
不存在完整端到端预算前缀成本，继续遵守[成本口径v1](P3_COST_SCOPE.md)。

[首次只读核验](../evidence/p3/first-seed-review-20261009-1658/summary.json)记录资源、
3项当时回归、原观测/原始前缀及CLI `--require-two`应退出2。随后新增两项行尾
回归：支持Git外层CRLF/LF转换但不接受内容篡改；保留原运行时SHA及独立规范化
旁证，不能把两者混称字节完全一致。已用源码另存collector_sources且哈希对应。
[30项原归档/编译器/缓存实际SHA核验](../evidence/p3/first-seed-review-20261009-1658/cache_and_archive_identity.json)
全部一致，原C/运行器/冻结配置对审计基点差异为0。交付内容随后另从干净归档检查，
记录其准确内容SHA，不替换正式实验身份。

内容45f990de42341d61d93a9f5b7023784584969d53的首次干净验证中，CLI、20配置、
51项单测及历史证据核验通过，但收集器整体退出1：错误要求PS工作区LF与归档CRLF的
实际SHA相等。[失败记录](../evidence/p3/first-seed-clean-45f990d/failure.json)保留；
修复只读身份检查，使用既有严格Git blob核验，另存两侧实际SHA和行尾数量。
不能将Git内容相等写成执行字节完全相同，也不能借行尾转换接受任何内容改动。

修复后的内容`f64d41c1eab21c72e541f91ab7e2dbecf4adfe2b`独立归档，初始无.git、
pycache且移除PYTHONPATH。12个[实测命令](../evidence/p3/first-seed-clean-f64d41c/commands.json)
均按预期退出：Windows7项针对性回归、干净WSL53项全套单测、CLI/20唯一配置、
verify_p1历史证据核验及22个文件身份核对通过。verify_p1核验已有160等历史案例，
不是本轮重跑这些实验。两侧实际字节只在PS脚本行尾不同，
[身份判定](../evidence/p3/first-seed-clean-f64d41c/archive_identity_check.json)明确记录。
[整体只读验证PASS](../evidence/p3/first-seed-clean-f64d41c/summary.json)不代表正式比较PASS；
`--require-two`正确返回2。该核验没有调用正式目标，正式实验内容仍为e308bfb。

## 后续入口（本轮不再启动）

先复核时钟异常及是否能恢复原协议；不能仅因资源PASS或某一次探针PASS就宣称稳定。
更换核心计时源/测量协议必须新版本、新session并先建立匹配完整Grid。
确认条件满足后，用**新的**批次证据目录调用既有主控；它先检查时钟、再由原
运行器检查门禁/固定身份，并自动归档清除暂停标记，禁止手动删标记或改旧分数：

```powershell
powershell.exe -NoProfile -File scripts/resume_p3_first_seed.ps1 `
  -EvidenceDirectory E:/software_system/project01/evidence/p3/first-seed-NEW-BATCH
```

仍只运行limit=2。完成两轨迹及其4/8/12候选复测、审计后，才讨论五种子扩展。
