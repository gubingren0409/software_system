# 首种子RAW比较：PARTIAL（2026-10-19）

本目录是efb7f9df后授权的一次真实首种子活动，**不是假执行器测试、不是五种子完成**。
Random搜索及其复测完成；Greedy第三搜索组发生合盖Modern Standby/超时，按冻结规则保留并停止。
不重跑、不校准、不筛样本、不退还待机时间、不重新领取活动窗口。

## 身份、范围和来源

- 分支project01，起点efb7f9df9c25dd509e207d67e08d4180c3e779ac。
- 实际运行内容：776b11171d796c8071e69824ffe463c4faf8ba57；科学测量内容继承3cc9e0d03ba682569fca0e91f28d364f2dab73fa。
- 新search session：c1bd157c6c8d42439d0fb08f69156ff5；没有复用旧空search或旧证书。
- Windows准确归档：C:/Users/28489/AppData/Local/Temp/matrix-raw-comparison-776b11171d796c8071e69824ffe463c4faf8ba57。
- WSL准确归档：/var/tmp/matrix-raw-comparison-content-776b11171d796c8071e69824ffe463c4faf8ba57。
- cache：/var/tmp/matrix-raw-comparison-cache-776b11171d796c8071e69824ffe463c4faf8ba57；只共享核验过的build/reference，不复用性能。
- n=4096，random输入，matrix_input_seed=20261008；search_seed=20261008另列。Random12及去重复测后，Greedy12及其复测。
- 每组1预热+5fresh、中位数、RAW整数端点及容差、20空间、科学C/输入/reference/编译参数/资源v2均不变。
- GCC13.3.0（Ubuntu13.3.0-6ubuntu2~24.04.1），WSL Python3.12.3；工具实际命令/路径/哈希见content/operations与身份文件。

[完整plan（双端Git内容/实际字节/行尾、编译器及缓存哈希）](content/search_plan.json)、
[源码身份汇总](source_identity.json)、[Git文件身份](content/git_identity.json)、
[新授权](search_authorization.json)、[采集前manifest](run_manifest.json)、[采集前方案](stage_plan.md)。
Python/C实际执行字节SHA与Git规范化SHA分别记录，不把CRLF/LF差异隐去；教师原件要求字节一致。
交付将本目录设为Git -text，原始JSON/stdout/stderr/哈希按采集字节保存；不改准确776b1117归档中的文件。
14个科学文件双端字节与3cc9e0d相同；教师SHA256为188d011109c4470e1f41829216e8677a5c2d8f2b7c8a44215652320dbdf6de15。
measurement/timing/resource/comparison协议的规范化哈希分别见plan；不是仅靠短Git SHA推断执行内容。

## 最小修复与验证（均在真实活动前冻结）

1. raw-comparison-audit-v2按mode选完成条件/CLI返回码；恰两算法、各12唯一、轨迹重放、4/8/12前缀、
   内部去重复测、跨算法不共享run_id、全样本/组/检查点、fresh、资源/RAW/连续性、正常窗口及预算全核验。
   搜索成功须24搜索组、R=2..6复测、144+6R执行；partial不能以成功子集变成comparison_ready。
2. 证据卷保护调用已有evidence_preflight：实际E:卷>=1GiB且write/fsync/read-back，活动开始和每组前保存原始结果。
   独立审计核对目录/上下文/字节/哈希；不是用WSL根盘冒充。未知/写失败/不足拒绝，受控拒绝目标0。
3. prepare仅建新search，准确导出/干净身份/编译器缓存验证；科学内容及协议没有修改。

工作树比较相关28项、准确Windows28项、准确WSL28项全部通过；续跑关联17项工作树/干净Windows通过。
覆盖search CLI成功0、空/缺算法/缺复测/多余样本拒绝、错误预算/完成状态、证据盘不足/写失败目标0；
原比较入口的隔离/恢复重放/待机拒绝/防睡眠释放回归保留。[准备结果](content/prepare_summary.json)。
没有重复历史110/160/834案例、额外n17或三配置验证。受控测试不计真实配置/目标。

## 真实执行和停止

13:36:02启动唯一43200s QPC活动；AC API=1、电量100%，临时防睡眠成功。
新fresh准入短1e9/长1e10固定更新2区间通过，绑定新内容/session/初始checkpoint；setup仅核验，reference生成0。
Random12搜索组及2个去重复测组完成，Greedy完成O1/s128、O1/s16两组。
第三组O3/s128：预热成功51.298125119s；第1次测量timeout、returncode=-9、无有效RAW分数。
两条原始样本均保留为不接纳的active部分组，剩余4次测量未执行，没有配置分数。

电源原始消息（UTC，+8为本地）来自失败组events_3，保留完整Message/XML：

- record353607，09:43:18.7512946Z，System506：entering Modern Standby，Reason:Lid。
- record353610，09:43:18.7530143Z，System506：再次进入待机。
- record353631，09:59:55.6677480Z，System507：exiting Modern Standby，Reason:Input Mouse。

原控制器首先因LastBootUpTime估计字符串01:49:39.5000000Z变成01:49:39.5048330Z，
抛出`Power event log reset or identity invalid`，没有将新事件加入成功观测列表；原始events_3仍完整保存。
cursor353603→353639，没有据此证明日志重置或真正重启；原始消息另直接证实待机。
监控45s sleep实际返回1035.169s，符合发生长暂停，但它本身不是精度/原因证明。
18:00:03控制器停止，真实returncode=2；没有改变冻结保护逻辑来绕过拒绝。
防睡眠请求同线程finally释放；它不能保证阻止合盖。[停止独立复核](stop_review.json)。

[控制器原始stdout](operations/search_activity.stdout.txt)、[stderr](operations/search_activity.stderr.txt)、
[实际argv/PID/QPC/退出码](operations/search_activity.operation.json)、
[原始样本JSONL](content/search-c1bd157c/samples.jsonl)、[检查点](content/search-c1bd157c/checkpoint.json)、
[窗口](content/search-c1bd157c/window.json)、[claim](content/search-c1bd157c/ACTIVITY.claim.json)、
[失败组原始电源消息/XML](content/search-c1bd157c/group_checks/aae9b1505c3c4a53aab33968a288876e/power_events/events_3.stdout.txt)、
[失败组及原始输出](content/search-c1bd157c/configurations/search_aae9b1505c3c4a53aab33968a288876e.json)。

## 首种子六行结果（没有填入未执行数据）

| 算法 | B | 已评估配置数 | 候选 | 搜索中位数/s | 独立复测中位数/s | 终态配置评估RAW成本/s |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| Random | 4 | 4 | O1/s64 | 77.616996424 | 77.570096137 | 6273.335551774 |
| Random | 8 | 8 | O3/s128 | 50.535368854 | 51.118067107 | 8340.945843372 |
| Random | 12 | 12 | O3/s128 | 50.535368854 | 51.118067107 | 12370.681806653 |
| Greedy | 4 | 2（前缀未完成） | 未形成 | 未完成 | 未执行 | 未形成 |
| Greedy | 8 | 2（前缀未完成） | 未形成 | 未完成 | 未执行 | 未形成 |
| Greedy | 12 | 2（前缀未完成） | 未形成 | 未完成 | 未执行 | 未形成 |

Random B4：搜索CV0.536393%、MAD0.246258124s；复测CV0.614031%、MAD0.208011120s；变化−0.060425%。
B8/B12同候选只复测一次：搜索CV2.555744%、MAD0.408699577s；复测CV0.742558%、MAD0.192439805s；变化+1.153050%。
原分数不替换，不选择两轮较小值。Greedy未达到任何预算前缀；不借另一算法的O3/s128复测。
[完整精度CSV](first_seed_six_rows.csv)、[JSON](first_seed_six_rows.json)。终态配置评估成本遵守P3_COST_SCOPE，
不含门禁/准入/setup/复测/失败；完整端到端前缀成本未知，不能直接解读为总调优成本。

## 验收、质量和保护

| 项目 | 实际状态 |
| --- | --- |
| evidence_integrity_pass | true |
| execution_complete（first_seed） | false |
| timing_checks_pass（整轮） | false |
| comparison_ready | false |
| five_seed_execution_complete / five_seed_comparison_ready | false / false |
| 完整搜索组 | Random12、Greedy2，共14/24 |
| 完整复测组 | Random2、Greedy0 |
| 原始执行/run_id | 98/98唯一；97 success、1 timeout |
| 已接纳/未接纳执行 | 96（16完整组）/2（部分组） |
| 完整搜索轨迹 | 1/2 |
| RAW检查实际采集 | 35区间/208响应：准入2＋完整组两侧32＋部分组前1，全部通过 |
| MONOTONIC辅助警告 | 7区间，不作RAW准入硬拒绝 |
| Formal/Recovery资源 | 19门禁全部通过，其中11快照低内存警告 |
| 证据卷检查 | 18次通过，最低62524596224B |

已采RAW检查通过不能替代失败组未完成的后检查/连续性，故整轮timing_checks_pass=false。
完整组的正确性/RAW契约/资源/连续性逐组独立核验；超时样本没有输出/正确性证明，不评分。
资源最低宿主1175203840B、提交余量30358896640B、WSL4822970368B；已采WSL swap used=0。
原始值均保留，不将Windows可用量加整个Vmmem；稀疏快照不证明无分页/性能干扰或占用根因。
[质量派生汇总及全部来源](quality_report.json)、[官方模式审计](official_first_seed_audit.json)、
[第二次独立后处理](independent_first_seed_audit.json)、[交付结构化摘要](delivery_summary.json)。
官方CLI及后处理实际returncode=2是未完成的正确拒绝，不是PASS。
PARTIAL审计中的expected_target_executions=156按当前2个已完成复测组计算，不是已确定最终R；
Greedy前缀尚未形成，完整活动的R仍须2..6、总执行144+6R（156..180）。
初次将审计文件直接作为脚本执行导致ModuleNotFoundError，原错误保留；改用准确归档cwd下`-m scripts.raw_comparison_contract`后正常得到PARTIAL。

14,221个历史文件逐SHA一致，包括关闭validation9332ead2全部18样本/分数、旧Grid待机/20组、
所有失败、旧checkpoint/controller/claim/证书/预算和d6811cad空session；没有追加或重标记。
[保护前映射](history_before.json)、[保护后核验](history_after.json)。
本任务Windows控制器/WSL测量器/候选进程已退出，[真实进程查询](stop_processes/owned_processes.stdout.txt)，
[防睡眠释放](content/search-c1bd157c/sleep_request.json)。所有大二进制/reference数据留WSL缓存，不提交。

## 成本范围（不可重复累加）

| 范围 | 秒 | 包含关系 |
| --- | ---: | --- |
| 独占活动宿主QPC | 15841.5879168 | 资源预检至停止收尾，含待机/失败/所有下列活动分项 |
| 控制器进程QPC | 15842.6557741 | 包含活动及其进程启动/退出，不另加活动 |
| 共享准备QPC | 84.7506965 | 活动开始至setup成功结束，含准入/门禁/setup |
| setup进程QPC / setup RAW | 1.8647197 / 0.542827549 | 后者嵌套前者，均在准备内 |
| Random12搜索评估RAW | 12370.681806653 | 1预热+5fresh/验证；不含门禁/复测 |
| Greedy已接纳2组评估RAW | 1041.151905033 | 不是完整预算4/8/12成本 |
| Random候选复测评估RAW | 791.041269405 | 2去重候选，各自完整6次，不占搜索预算 |
| 已接纳核心RAW合计 | 14018.663711764 | 嵌套上述各组评估，含预热 |
| 门禁QPC | 227.5545062 | 与准备范围有交集，嵌套活动 |
| 原生探针进程QPC | 152.1394165 | 35区间，嵌套活动 |
| 失败组评估RAW / 进程QPC | 93.559193609 / 1085.9140523 | 后者另含启动/停止，缺同范围宿主FINISHED端点，不相减/校准 |
| 离线准确导出/准备/测试进程QPC | 89.1660408 | 正式活动外；内部测试耗时不再叠加 |

固定43200s内账面剩余27358.4120832s，不代表再次启动授权，不按待机退款。
失败组只知道成功预热核心51.298125119s；超时测量核心时长未知。旧来宾MONOTONIC进程/lookup字段保留来源，
不用它们校准RAW或证明总调优成本。[全部成本清单](costs.json)。其他离线命令/保护/后处理/Git耗时在operations分别记录。
旧Grid含待机且跨日，不能用其QPC包络证明本轮效率优势；单种子/后台负载/资源警告仍是比较限制。

## 复核入口与下一步

只读审计（从对应内容的准确归档目录运行；输出选新路径，不覆盖历史）：

```powershell
python -B -X utf8 -m scripts.raw_comparison_contract --plan E:/software_system/project01/evidence/p3_raw_first_seed/20261019-132400/content/search_plan.json --output C:/Users/28489/AppData/Local/Temp/first-seed-readonly-audit.json
```

预期退出2：PARTIAL，不能据此启动目标。源码与manifest/缓存实际路径需按计划核验，不依赖原工作树PYTHONPATH或旧pycache。
新归档测试、CLI和20配置命令均已真实运行，日志在content/operations与operations；原始stdout/stderr未改排为图片。
没有可靠可见终端截图，明确不提供伪造终端截图。[最终交付检查](final_checks.json)。
本轮停止并交外审。若后续明确授权续跑，先审查是否允许在不重置已用15841.5879168s及原claim的前提下
使用剩余额度，如何封存两条失败样本、fresh资源/时钟准入及新完整attempt；当前入口是one-shot，不能直接重复。
不自动扩展其他种子/算法/完整Grid；本次不修改系统电源、NTP、内核、clocksource或结束用户应用。
