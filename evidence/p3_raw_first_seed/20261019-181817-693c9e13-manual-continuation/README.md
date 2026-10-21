# 首种子人工续跑：PARTIAL（2026-10-20交付）

本段唯一授权活动已经停止；不重试、不自动再次准入或领取窗口。停止原因为Greedy O3/s16组内Modern Standby，
不是资源门禁或RAW探针拒绝。Random完整结果不改，Greedy仍缺第12个完整配置及其前缀候选复测。

## 来源、授权与保护

基点d706a96ac8eea2a04c5f13c09420b89092c79546；实际测量/搜索内容
776b11171d796c8071e69824ffe463c4faf8ba57，继承科学3cc9e0d03ba682569fca0e91f28d364f2dab73fa；
session c1bd157c6c8d42439d0fb08f69156ff5不变。新增归档外助手706d239a5f1592dc17fb2ceefa46a2112727f966，
执行字节SHA256为79e99f7521824e3b2f531920a09c6f34487d96b01cf30a64dd7758d87c4b65db。
准确辅助归档C:/Users/28489/AppData/Local/Temp/matrix-raw-search-continuation-706d239a5f1592dc17fb2ceefa46a2112727f966，
冻结WSL运行归档/var/tmp/matrix-raw-comparison-content-776b11171d796c8071e69824ffe463c4faf8ba57。

- [采集前声明](../../../docs/P3_RAW_SEARCH_CONTINUATION.md)、[授权与16,831文件SHA清单](continuation/authorization.json)
- [起始快照](continuation/preserved/)、[旧v2只读审计](continuation/previous_independent_audit.json)
- [原冻结计划](../20261019-132400/content/search_plan.json)、[原session实时终态](../20261019-132400/content/search-c1bd157c/checkpoint.json)
- [执行源码/协议/二进制/reference身份](source_identity.json)、[运行前缓存核验](continuation/verified_cache_reuse.stdout.txt)

原98条2378346字节前缀SHA256 ceab94eb460bffe00592b51f5f7dbdd4cab36ce0a5d9d529dc3b7b1cb76aad3c不变；
16,831个不可变文件、旧claim/window/证书、关闭Grid/18条验证、Random全轨迹及旧Greedy2观测保持。
原session仅checkpoint/progress和samples追加允许变化。旧O3/s128两条失败尝试原样列入
[放弃账本](continuation/abandoned_attempt.json)，新attempt完整6fresh，不拼接旧组、不复用性能成绩。

## 测试与真实执行

14项新增相关受控回归在工作树及准确辅助归档通过。扩展审计夹具一度授权路径错误、首次准确导出遗漏
measurement_protocol测试依赖，失败日志都在[operations](operations/)；修正并通过后才启动真实活动。
只读prepare并行不启动探针/目标；无额外n17、历史大批测试、三配置验证或Grid。测试数据不作为成绩。

Formal预检→唯一fresh默认libc、不绑核短1e9/长1e10→来源/缓存核验通过；setup未调用，reference生成0。
本段新增9完整Greedy搜索组54fresh，加失败组4条共58次；session原始总数156，全部run_id唯一，
150条属于25完整组（Random12+Greedy11搜索，Random2复测），另旧放弃2条、新部分4条不计分。
新失败attempt42e0c68e880f4104a4041cc6a176b55d：预热、测量1/2成功，测量3 timeout/-9；不求成功子集中位数。
2026-10-19T12:27:28.5899707Z System506原始消息Reason:Lid，12:37:45.3273151Z System507及随后506报告
Austerity Battery Drain Budget Exceeded；原始XML/消息见[停止复核](stop_review.json)和
[失败组原始电源流](../20261019-132400/content/search-c1bd157c/group_checks/42e0c68e880f4104a4041cc6a176b55d/power_events/events_8.stdout.txt)。
初始AC检查通过不代表全程接电，不推断用户意图；不新增或修改系统设置。控制器实际returncode=2。

新准入2/2、9完整组前后18、失败组前1，共21个新区间；包含历史合计56区间/332响应原始复算通过。
失败组无组后/完整连续性，不能因其他探针通过而宣布整轮计时通过。全session含历史30资源快照均准入，
19次低2GiB警告，宿主最低711725056B、提交余量27615494144B、WSL可用4767371264B，采样WSL swap=0；
这些稀疏快照不证明组内无压力。本段11资源/11证据卷检查通过，合计29证据卷检查，RAW/MONO警告保留。

独立四项：evidence_integrity_pass=true；execution_complete=false；timing_checks_pass=false；comparison_ready=false。
范围仅first_seed，五种子仍false。GreedyB4/B8已形成，B12未完成，Greedy全部候选复测未执行；
Random不共享其复测样本。不能据此宣称两算法优劣或五种子完成。

- [独立审计](continuation/independent_continuation_audit.json)、[实际计数和状态](delivery_summary.json)
- [六行CSV](first_seed_six_rows.csv)、[含CV/MAD的JSON](first_seed_six_rows.json)
- [每次执行原始stdout/stderr/结果](../20261019-132400/content/search-c1bd157c/runs/)、[仅追加JSONL](../20261019-132400/content/search-c1bd157c/samples.jsonl)
- [资源/全部时钟派生复核](quality_report.json)、[电源与进程退出核验](stop_review.json)

## 成本与下一步

原15841.5879168s照计，本段7488.0732714s，累计23329.6611882s/43200s，账面余19870.3388118s，
不退款、重置或自动再授权。以[最终窗口整数QPC端点](continuation/window.json)为准，
后续progress的活读数多6.5691ms，原样保留但不覆盖窗口；跨epoch只相加各自已验证时长。
本段共享准备78.7235807s、全session已接纳Random评估12370.681806653s、Greedy7287.827451217s、
Random复测791.041269405s以及门禁/探针/核心都是嵌套范围，不全部相加。
新失败组评估RAW250.251100179s与进程QPC868.4670412s范围不同、无匹配FINISHED，不相减或校准分数。
[全部成本及来源](costs.json)；配置前缀仅自己的终态评估RAW，端到端前缀成本未知。
离线prepare43.6626891s、后处理32.9567671s、质量18.5004711s、停止复核41.2945405s各有操作记录，
后两汇总中有并行区间，不能盲目求和。离线审计暂停/模型/文档/Git不混入活动包络。

任务实验进程已退出，临时防睡眠已finally同线程释放；日志证明该请求无法保证阻止合盖。
未捕获可核验的真实终端截图；保留原始stdout/stderr，不制作伪截图。旧Grid待机/跨日限制仍在，不能以其QPC包络证明效率优势。

仅允许以下只读复算（预计退出2，表示真实PARTIAL；不调用run，不再次准入）：

```powershell
python -B -X utf8 C:/Users/28489/AppData/Local/Temp/matrix-raw-search-continuation-706d239a5f1592dc17fb2ceefa46a2112727f966/scripts/continue_raw_search.py audit --authorization evidence/p3_raw_first_seed/20261019-181817-693c9e13-manual-continuation/continuation/authorization.json
```

此命令依赖原准确归档和本机路径，跨机审计优先读取已提交原始证据/来源；临时目录被清理时须从准确SHA重新导出，不能假装通用可运行。
当前停止等待外审；再次正式运行需要新的明确授权及不重置预算/保留失败组的方案，本轮不自行开始。
