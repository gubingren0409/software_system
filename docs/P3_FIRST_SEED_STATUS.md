# 首种子正式比较：P3_CLOCK_BLOCKED（2026-10-10，原生C/宿主参照诊断）

## 当前：50cd24e后唯一30区间有界诊断

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
