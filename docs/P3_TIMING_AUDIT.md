# 0023ceed 时钟、资源与交错复测审计

本文保留0023ceed独立诊断的历史结论；e46b96c之后实际恢复、再次暂停以及16:42
时钟检查阻塞的最新状态见[首种子状态](P3_FIRST_SEED_STATUS.md)，不混入本诊断session。

审计基点`0023ceedcbbb416e6ee8b6e2db44c41a10e90983`，在其后已推送的55b776b历史上
继续，保留用户/本轮续跑的全部证据，不回退分支。P2的20配置表保留；P3正式算法
比较未完成，该轮审计不继续完整P3长实验。本文以下“本轮”指0023ceed独立审计；
e46b96c后的首种子恢复按用户新授权进行，最新状态见[P3审计入口](P3_AUDIT_HANDOFF.md)。

## 运行前判据（诊断schema 1）

[protocol](../configs/timing_audit_protocol.json)在本次诊断读数出现前声明并提交。
独立诊断session，C/core/measurement/search/campaign以及测量schema 2不变。
不能用诊断文件取代Grid或给搜索策略提供观测。

- 每个对照区间保留MONOTONIC、RAW、REALTIME、BOOTTIME端点纳秒原值（十进制串）
  和差值。Windows保留QPC/Stopwatch端点、频率、UTC ticks、完整WSL调用耗时。
- WSL同一区间：`abs(MONO-RAW) <= 0.005s + 1%*RAW`。宿主完整调用含启动/采集/输出，
  与WSL完整操作对照：`abs(host-RAW) <= 1s + 1%*RAW`。REALTIME对RAW允许
  `0.25s + 1%*RAW`，超过即标注间隔不一致，不能据此单独确认根因。
- 3个20秒sleep探针在复测前、3个在后；目标执行期间每次Evaluator完整调用也同时
  读MONO/RAW。这不是RAW核心时间，不能把比例直接乘到历史核心秒数。
- 每组开始前使用正式JSON门禁：Windows/WSL均≥2GiB、WSL根空闲≥1GiB、宿主CPU
  五样本平均≤10%/最高≤20%。不能仅凭退出0；失败门禁留档并按16次重查上限暂停。
  运行中保留宿主提交/分页、WSL swap/vmstat/PSI和目标GNU time峰值RSS；缺失为未知。
- n=4096/random/20261008/s=128，原输入/循环/1e-12容差、原超时。顺序固定
  `r1: O1,O2,O3; r2: O3,O2,O1`，平衡线性位置漂移，但中央O3相邻与仅两轮是局限。
  每组独立一次预热+五次force测量，五次核心MONOTONIC中位数；任何失败整组无分数。
- 预声明：组CV>2%标为波动，跨轮同配置中位数变化绝对值>2%标为漂移；相邻优化
  差距<2%标为小幅差距。稳定排序判据要求两轮排序相同、相邻差距均≥2%、漂移≤2%、
  无CV警告、全部时钟检查通过且无运行中资源警告，否则只写“本次观察排名”。

这些是本项目审计质量判据，不是老师要求，也不是物理校准标准。没有引入单一校准
系数、不删慢值、不将“读数一致”写成独立物理时间认证。若后续更换计时源/测量
协议，必须新版本/内容提交/session并先取得匹配的完整新Grid，不能沿用旧Grid作
新协议的正式比较基线。

## 已保留与修订范围

用户要求后写PAUSE_REQUEST，旧P3在当前目标完成后安全退出：3个完整配置、
21次完整目标执行，含O0/s8部分组3条，未计分。它们全部留在原campaign，恢复该
部分组须重新预热及五次测量。[暂停证据](../evidence/p3_audit_0023ceed/p3_pause.json)。
P3原内容仍e308bfb；新诊断session单独绑定新内容SHA，不迁移/改写旧样本。

成本不是改计分：限定原前缀字段的排除项，新增失败门禁暂停—成功恢复的受控回归，
见[成本口径](P3_COST_SCOPE.md)。report修正O3差距：O1复测漂移2.4976%大于O2差距
1.9850%，但小于O3差距2.9017%；原笼统“大于O2/O3”错误，修正不证明稳定最优。
[只读原CSV/检查点复算](../evidence/p3_audit_0023ceed/report_gap_correction.json)。

## 执行与后续

脚本：[Windows主控](../scripts/run_timing_audit.ps1)、[WSL诊断](../scripts/timing_audit.py)。
从内容提交的干净归档执行，移除PYTHONPATH/不写pycache；工具/源码/Git字节、实际
字节、编译器、二进制/reference哈希和manifests都记录。每个步骤取得同一P3独占锁，
防止并发目标；PAUSE_REQUEST保持，完整P3必须等外部复核后才显式恢复。
原缓存不清理，新增大数据/二进制仅在WSL本地独立audit缓存，不提交Git。

## 实际诊断结果（2026-10-09，audit-only）

[完整分析](../evidence/p3_audit_0023ceed/session-0d57f8c/analysis.json)与
[终止检查点](../evidence/p3_audit_0023ceed/session-0d57f8c/checkpoint.json)：6/6组success，
36/36条执行fresh/force、run ID全唯一、退出0、16777216项逐元素验证与冻结契约通过；
没有失败子集计分或性能缓存重复。六组样本/命令/独立stdout/stderr/峰值RSS/资源
在`session-0d57f8c/groups/<id>/`，组内`runs/`原始文件和`clocks/`纳秒端点留存。

| 组 | 核心中位数 s | 均值 s | 样本标准差 s | CV | MAD s |
|---|---:|---:|---:|---:|---:|
| r1_O1 | 50.963140880 | 51.346668034 | 0.656165478 | 1.2779% | 0.176966341 |
| r1_O2 | 52.042876327 | 51.889700547 | 0.495585593 | 0.9551% | 0.420997592 |
| r1_O3 | 51.308399075 | 51.325586134 | 0.358692970 | 0.6989% | 0.266120639 |
| r2_O3 | 52.122370106 | 52.022998779 | 0.741401509 | 1.4251% | 0.504769459 |
| r2_O2 | 52.626460105 | 52.647590853 | 0.584501766 | 1.1102% | 0.031252171 |
| r2_O1 | 51.435436694 | 51.539353973 | 0.454933242 | 0.8827% | 0.359252603 |

两轮观察排序都是**O1 < O3 < O2**（越低越好）。跨轮中位数变化：O1 **+0.9267%**、
O2 **+1.1214%**、O3 **+1.5864%**，均未超过先验2%漂移警告；组CV也均≤2%。
但第一轮相邻差距0.6775%/1.4315%，第二轮1.3355%/0.9671%，全部不足2%。
加上资源警告，`robust_ranking_criteria_pass=false`；只报告本次观察排名，不能称
稳定最优。P2本来的O2/O3顺序与本次不同，是跨session观察，不替换原Grid表。

### 时钟一致性

| 探针 | MONOTONIC s | RAW s | 宿主整次调用 s |
|---|---:|---:|---:|
| before0 | 20.000710163 | 20.008712049 | 20.6539246 |
| before1 | 20.000229627 | 19.970415609 | 20.6149494 |
| before2 | 20.000167466 | 19.932767006 | 20.5757147 |
| after0 | 20.000203785 | 20.000831105 | 20.6366738 |
| after1 | 20.000571795 | 19.970145269 | 20.5927583 |
| after2 | 20.000117981 | 19.921000160 | 20.5541894 |

12个整组/探针对照与36个Evaluator区间均满足各自先验对照判据：
`all_clock_checks_pass=true`。20s探针MONO/RAW相对差最大约0.3972%；整组/探针
MONO/RAW绝对差最大0.521036448s（在约321s区间），host/RAW差最大0.845274831s。
宿主区间包括WSL启动、来源核验和输出，不能对比单次C核心或称RAW核心时间。
NTP/tsc状态与[运行后采集](../evidence/p3_audit_0023ceed/post_environment.json)只表明
当时状态；未确认P2历史异常根因，也没有独立物理时钟校准。此次一致性不能追认
旧样本精度，不作单比例校准、不筛改历史数据、不反馈搜索。

### 资源、暂停与成本

六组正式开始门禁都解析为PASS；此前共5次低内存拒绝（r2_O3一次、r2_O2一次、
r2_O1三次），按30s重查后恢复，原始门禁及其returncode=2全部保留。
宿主72个去重运行中快照中44个低于2GiB，最低**1.8264GiB**；一条CPU=21%，
因此有运行期资源警告。原始执行记录的`resource_samples[].host.host_samples`表明，
Windows在目标运行期间按约30秒节奏采样，实际相邻时间戳间隔28–34秒；不是仅在
目标执行前后采集，也不是连续监控。该说明修正不改变原始样本或资源警告。
WSL执行期间有资源样本，最低可用**3.4757GiB**，swap使用0、pswpin/pswpout均
0→0；PSI读数全为avg10/60/300=0、total=0。全WSL pgmajfault40359→40583，
不是目标独占计数。目标GNU time峰值RSS**394856KiB（385.60MiB）**。
宿主最大提交占比58%，PagesPersec最大5191、PageReadsPersec最大2421，不能
归因本程序；压缩内存、温度、节流/真实频率状态未知。
[去重资源明细](../evidence/p3_audit_0023ceed/resource_detail.json)。

主控主循环Stopwatch **2369.4009297s（39分29秒）**，包含setup/门禁/探针/六组/
分析，不含最初路径/哈希检查、导出、单测、文档或Git。门禁采集与等待累计
**280.4425752s**（其中5×30s重试睡眠）；六组Evaluator调用累计1918.089173439s，
目标进程MONO累计1899.847689186s；36条核心MONO累计1866.508659992s（含预热），
30条计分核心合计1553.859491604s。这些层级有包含关系，不能全相加。
新reference生成核心35.876636807s、进程36.726809061s；整个WSL setup40.728946107s。
各编译耗时未逐次单独计时，setup余额不能全部称编译成本，明确未知。
[成本/对照复算](../evidence/p3_audit_0023ceed/cost_and_clock_summary.json)。
门禁等待使实际间隔不均匀；反序不能保证温度/频率/后台负载漂移完全抵消。

### 完整性与验证

干净归档的CLI帮助、20配置、verify_p1及46项单测通过；目标结束后从同一归档
重跑完整分析和46项回归也通过：[日志](../evidence/p3_audit_0023ceed/post_clean_validation.json)。
verify_p1中的历史数量是旧证据核验，不是本轮重新执行全部历史实验。
[完整性复核](../evidence/p3_audit_0023ceed/post_integrity_cost.json)确认新旧三个候选
二进制/reference SHA完全相同，正式C/运行器/冻结协议Git差异为0，P2表/检查点
SHA与运行前相同，老师原件188d0111…未动。PS的实际CRLF与Git规范化LF分别
列在session.source_identity；Windows/WSL实际脚本逐项SHA相同。
文本日志检出时可受Git的CRLF/LF转换；JSON内保留stdout/stderr字符串及原始时钟
整数读数。源码“实际执行SHA”和Git规范化身份不能混用，文本一致性复核采用
Python读文本的换行归一化，不宣称所有.txt在任意检出中保持字节完全相同。
原P3保持user_paused、3完整配置/21次执行（含3条部分组），正式比较未完成。
辅助绘图仅收窄成本标签；无完整P3前缀，本轮不生成比较图。
证据内容提交`4ec89ed51f35cea19e41082afa7d10e8fe3ff13d`随后另导出干净归档，CLI/
配置20/verify_p1/46项回归及对**归档内**六组原始数据的重分析通过。
[归档复验](../evidence/p3_audit_0023ceed/delivery_archive-4ec89ed.json)、
[重分析SHA一致](../evidence/p3_audit_0023ceed/archive_analysis_identity.json)。
验证没有新增n4096执行，实验身份仍0d57f8c；随后仅补复验日志/说明和派生成本
字段的预热范围标签（数值未变），不更改运行器或冻结协议。

### 主控v2迁移（读数出现前）

首次从WSL UNC路径启动dbf43e6副本，Windows返回未签名脚本拒绝（退出1），
没有建立诊断session或执行目标。原失败stdout/stderr保留在
[controller](../evidence/p3_audit_0023ceed/diagnostic_controller.json)。
不修改执行策略：改用同一新内容提交的Windows本地`git archive`副本执行PS，
WSL仍用该提交的独立干净归档执行Python/C。主控schema升为`timing-audit-host-v2`，
逐项核对本地PS/协议与WSL归档的SHA-256；Snapshot子进程也使用校验过的本地
资源脚本。新的内容SHA、诊断session与迁移记录绑定，原测量/搜索协议与C计时源
不变，无任何旧/新样本拼接。

v2的正式门禁PASS后，setup发现`wsl.exe`边界把反斜线路径去转义为无分隔符路径，
在构建/reference/目标前失败。保留session-46bcbd7全部原始输出。v3仅将传给WSL
的Windows脚本路径规范化为正斜线；本地执行及SHA校验不变，另建内容提交/session。

本轮实际内容提交为`0d57f8c53a14a8c1d02dfd91263b038fac710ee4`，不是最终证据提交。
诊断协议规范化SHA-256为
`de969257d62202be0a6470af033eaf4e8f14118c51d78de88d87e5372b5409ae`；
实际JSON文件SHA-256为`720c91efdf26f6e435629d2638781cca1d79ebc49f49d203a7dcdaa398311b9f`。
新[session](../evidence/p3_audit_0023ceed/session-0d57f8c/session.json)绑定两个协议、
全部实际源码/Git字节与换行、编译器/候选/reference身份；
[主控命令及退出记录](../evidence/p3_audit_0023ceed/diagnostic_controller_v3.json)。
Windows PS 5.1.26100.9444与WSL Python3.12.3/GCC13.3.0，主控v3双归档一致；
没有改变CLOCK_MONOTONIC核心计时或测量schema 2。

## 后续命令（仅供复核后执行，本轮不启动）

只读正式资源复查：`powershell.exe -NoProfile -File scripts/check_p2_resources.ps1 -Mode Formal`。
应解析schema/mode/PASS与全部冻结数值门槛，不仅看退出码。下阶段先由审计者裁决
是否原计时协议/环境足以继续；若换计时源或测量协议，另建版本/session并先重跑
匹配的20配置Grid，不得接着用旧Grid作正式对照。

仅当裁决允许沿用原协议，才执行下述命令；原运行器的显式`--resume`会把
`PAUSE_REQUEST`内容留存到`pause_requests/*.json`再清除请求，不需要手动删除：

```bash
cd /var/tmp/matrix-autotuner-p2-content-e308bfb873e6811c50ad685a979af345302fda8d
PYTHONDONTWRITEBYTECODE=1 env -u PYTHONPATH python3 -m autotuner campaign \
  --content-sha e308bfb873e6811c50ad685a979af345302fda8d \
  --git-identity /mnt/e/software_system/project01/evidence/p3/content-e308bfb/git_identity.json \
  --campaign-directory /mnt/e/software_system/project01/evidence/p3/campaign-e308bfb \
  --trajectory-limit 2 --resume
```

原3完整配置从全部原始记录恢复；O0/s8旧3条部分样本保留为放弃记录，必须重新
预热+完整五次测量。不要把诊断session/通用build身份文件当作原P3续跑身份。
首批完成并复核资源/成本后，扩大到`--trajectory-limit 10`才是全五种子计划。
若需要**端到端预算前缀成本**而不只是终态配置调用累计，必须新版本事件账本和
新session；旧前缀字段不具备完整等待/放弃成本，见成本口径v1。
