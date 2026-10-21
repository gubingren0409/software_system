# 第一种子有界收尾完成（2026-10-20）

状态FIRST_SEED_RAW_COMPARISON_COMPLETE，仅search seed=20261008；五种子整体未完成。
本轮正常完成即停止，无新真实失败、自动重试或其他种子/算法/Grid/三配置/n17目标执行。
首种子四项evidence_integrity_pass/execution_complete/timing_checks_pass/comparison_ready均true，
five_seed_execution_complete/five_seed_comparison_ready均false。

## 执行身份与历史保护

- 基线60c103711fc935b52b614f32aff2ed8101c7b9cc，科学/测量/搜索执行776b11171d796c8071e69824ffe463c4faf8ba57，
  session c1bd157c6c8d42439d0fb08f69156ff5，继承科学3cc9e0d03ba682569fca0e91f28d364f2dab73fa。
- 新归档外助手053930946d73b142d6eb39a1bb297b52cdd446fd；
  实际脚本SHA256 fb18a53e5a5ae11b2353686f1e6ca2a345c88dec0220066c7577a90e02faee42。
  Windows准确辅助归档C:/Users/28489/AppData/Local/Temp/matrix-first-seed-finish-053930946d73b142d6eb39a1bb297b52cdd446fd；
  真正Linux测量仍从/var/tmp/matrix-raw-comparison-content-776b11171d796c8071e69824ffe463c4faf8ba57执行。
- 不改原C、计时/输入/reference/编译选项/资源v2/正确性/评分/搜索。经实际哈希核验复用编译/reference缓存，
  setup未调用，新增reference_generation_calls=0，禁止复用性能样本。
- [采集前声明](../../../docs/P3_RAW_SEARCH_FINISH.md)、[原冻结计划](../20261019-132400/content/search_plan.json)、
  [源码/协议/编译器/四候选/reference身份](source_identity.json)、[实际缓存核验](continuation/verified_cache_reuse.stdout.txt)。
- [新授权/保护清单/旧窗口链](continuation/authorization.json)、[开始前快照](continuation/preserved/)、
  [25组独立起始核验](continuation/initial_integrity.json)、[新独占claim](../20261019-132400/content/search-c1bd157c/MANUAL_FIRST_SEED_FINISH_V2.claim.json)。
- 18,178旧证据文件哈希不变，Random12+2复测整轨迹、Greedy原11完整组、旧claim/window/证书/审计及失败都保留；
  原156条3556374字节前缀SHA256 e004ed1d9530aae73c05358c52536576b8436dd56e108dec627bfe6991147927不变。
  [历史/旧账本/进程核验](stop_review.json)。

原manual_resume的aae9b1505c3c4a53aab33968a288876e两条保持，准入成功后追加finish_resume，
精确登记42e0c68e880f4104a4041cc6a176b55d四条为放弃。
[第二次放弃与旧账本哈希链](continuation/abandoned_attempt.json)固定六个run_id，不泛化忽略任意不完整记录。
原session只有checkpoint/progress与samples追加发生有授权变化；旧成绩、原始结果和旧失败结论不改。

## 测试与真实执行

18项本次相关受控回归在工作树/准确归档通过，CLI帮助通过，不重跑历史大批测试或n17。
[全部命令、stdout、stderr、真实退出码](operations/)保留初始JSONL夹具换行错误与首次未暂存提交的失败。
夹具修正/正常暂存后才冻结准确辅助提交并开始唯一真实活动。受控数据不是性能成绩。

Formal预检→唯一fresh默认libc不绑核短1e9/长1e10共2区间→冻结来源/缓存核验→明确放弃旧四条→完整重做O3/s16。
新搜索attempt948266703a364a7098efe114d2a84fda完成1预热+5fresh；仅重放Greedy自己11观测，下一项确为O3/s16。
完成后Greedy自己的B4/B8/B12均选O3/s128，内部去重G=1，新retest attempt27ccb0d66b844db8bcb960d45f13990c完整6fresh。
不共享Random复测，不把Random/Grid/三配置验证或复测分数反馈策略。

实际新增12目标，总168个run_id唯一，24搜索+Random2复测+Greedy1复测=27完整组/162已接纳执行，
另6条精确放弃；未知额外/active/新部分均0。每次新执行全矩阵16777216元素正确，RAW整数端点契约/计时身份通过。
组前资源/证据卷、前后RAW、完整FINISHED握手及同范围QPC/RAW/电源连续性均通过。
[新独立验收](continuation/independent_continuation_audit.json)、[精确计数](delivery_summary.json)、
[全部只追加JSONL](../20261019-132400/content/search-c1bd157c/samples.jsonl)、
[每次原始流/退出码/资源](../20261019-132400/content/search-c1bd157c/runs/)。

本轮6个RAW区间通过；连同历史62区间/366响应全部复算，11个MONOTONIC辅助警告保留。
新3次Formal门禁/3次实际E证据卷write/fsync/read-back均通过，O3/s16组宿主最低1557786624B有低2GiB警告；
O3/s128复测组最低3923279872B。全范围33快照、20低内存警告、32证据卷检查，
历史最低host711725056B/commit27615494144B/WSL4767371264B，采样WSL swap used=0。
[质量原始索引与复算](quality_report.json)。不因门禁通过断言全程无压力，不把Vmmem加回可用容量或宣称时钟绝对准确。
新通过不追认历史失败/旧Grid已连续或已校准，六条失败原样保留且不退款。

## 六行真实第一种子比较

矩阵input seed与search seed分别固定20261008。CV仅五次测量的样本标准差/均值，MAD为五次绝对偏差中位数，
不代表跨搜索种子稳定性。成本仅自己的终态配置评估RAW，含1预热+5fresh/验证，排除门禁/准入/失败/复测/离线。

| 算法 | B | 候选 | 搜索中位数/s | 独立复测/s | 搜索CV% / MADs | 复测CV% / MADs | 配置评估RAW/s |
| --- | ---: | --- | ---: | ---: | --- | --- | ---: |
| Random | 4 | O1/s64 | 77.616996424 | 77.570096137 | 0.536393 / 0.246258124 | 0.614031 / 0.208011120 | 6273.335551774 |
| Random | 8 | O3/s128 | 50.535368854 | 51.118067107 | 2.555744 / 0.408699577 | 0.742558 / 0.192439805 | 8340.945843372 |
| Random | 12 | O3/s128 | 50.535368854 | 51.118067107 | 2.555744 / 0.408699577 | 0.742558 / 0.192439805 | 12370.681806653 |
| Greedy | 4 | O3/s128 | 51.760896392 | 50.118510833 | 0.472854 / 0.176828183 | 0.538161 / 0.127395643 | 1839.423685402 |
| Greedy | 8 | O3/s128 | 51.760896392 | 50.118510833 | 0.472854 / 0.176828183 | 0.538161 / 0.127395643 | 5960.500095546 |
| Greedy | 12 | O3/s128 | 51.760896392 | 50.118510833 | 0.472854 / 0.176828183 | 0.538161 / 0.127395643 | 7753.893434528 |

[完整精度CSV](first_seed_six_rows.csv)、[JSON与复测映射](first_seed_six_rows.json)。
Greedy三行只映射自己的同一次复测，Random B8/B12映射Random自己的一次复测；两算法没有共享样本。
Greedy复测相对自身搜索−3.173024%，Random B4−0.060425%、B8/B12+1.153050%；原分数不替换、不择小。
本种子Greedy到B4、Random到B8选中O3/s128，B12候选相同；跨段/跨日观测不能证明算法使同一配置本身更快，
不外推五种子稳定性或20配置全局最优，不用含待机的旧Grid QPC包络证明速度优势。

## 活动预算和嵌套成本

三段各自验证QPC整数端点/频率后相加：15841.5879168+7488.0732714+962.6504186=24292.3116068s。
总43200s，账面剩余18907.6883932s不转给其他种子/阶段；不跨不同epoch相减绝对QPC、不退待机成本。
[最终新窗口](continuation/window.json)保留原始浮点尾数，文档按QPC精度显示；旧两窗口不改。
外层进程976.5080898s包含本段窗口；claim前身份/保护验证属辅助，不能再把进程包络加到活动。

- 搜索前缀：上表终态配置评估RAW，Random12累计12370.681806653s、Greedy12累计7753.893434528s；端到端前缀未知。
- 独立候选复测RAW：Random791.041269405s、Greedy311.761200991s，不占唯一配置搜索预算。
- 本段共享准备QPC88.3884232s、门禁QPC65.6198174s、时钟进程QPC49.3091376s均嵌套于本段。
- 已接纳核心RAW20910.455161873s又嵌套在组评估内；六条旧放弃已知核心287.855589786s，两个超时核心未知，
  其进程/待机/失败已经在各段宿主包络里，不再加一次或退款，不用不同范围相减校准。
- 只读prepare46.0984768s、测试/导出、离线报告、审核暂停和Git单列；辅助操作有并行，不盲目相加。
  [全部逐项成本/来源/嵌套](costs.json)。

离线汇总初次残留manual_search_activity操作名，两个脚本FileNotFoundError退出1；
修正为真实finish_activity后，stop_review重复采集同名快照被不可覆盖保护拒绝，未写坏原证据。
最终改为checked_operation验证复用原成功进程快照，退出0；[失败前源码/原始快照](reporting_failures/)和失败操作日志保留。
这些是离线辅助修复，没有重跑准入/目标或修改冻结05393094辅助主控、776科学内容与任何分数。
最终打包检查的通用5MiB提醒命中必须保留的起始checkpoint；只对白名单中的精确路径及授权SHA接受必要大文件，
不截断或删除证据，不修改性能/资源门槛；初次拒绝源码/日志仍保存。

临时防睡眠已finally同线程释放，不能保证阻止用户合盖；[原始释放记录](continuation/sleep_request.json)。
控制器退出0，原始进程快照无本任务Windows/WSL目标；没有伪造终端截图，原始stdout/stderr保留。
本轮完成即停止，等待外审，不自动启动其他种子、算法或新完整实验。

仅供只读复算（应退出0，不调用run或再次准入）：

```powershell
python -B -X utf8 C:/Users/28489/AppData/Local/Temp/matrix-first-seed-finish-053930946d73b142d6eb39a1bb297b52cdd446fd/scripts/finish_raw_search.py audit --authorization evidence/p3_raw_first_seed/20261020-214028-09795d71-first-seed-finish/continuation/authorization.json
```

该命令依赖本机准确临时归档；临时目录丢失须按精确SHA重新导出，不能声称任意机器上的绝对路径直接可用。
外审可从已提交原始整数端点、通信流、每次JSON/组文件和授权哈希独立复算；不修改旧审计文件。
