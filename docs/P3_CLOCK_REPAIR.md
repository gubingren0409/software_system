# aedf028a 后集中时钟诊断（2026-10-10）

## 结论：P3_CLOCK_BLOCKED，仅交付诊断

基点为 `aedf028a9b8893166317338eb7aaba4f19ab3a9c`，project01 初始工作区干净，
该提交为 HEAD/祖先。`origin` 仍是课程 Gitea：WSL fetch 超时，Windows fetch
因失效的 127.0.0.1:7897 代理失败；没有改代理/TLS。`github` fetch 成功，取得的
project01 同为该基点。本轮正常向 GitHub project01 推送，最终 SHA 在终端交接。

新证据独立保存在
[`evidence/p3_clock_repair/20261010-121004/`](../evidence/p3_clock_repair/20261010-121004/)。
没有权限实施同步，且资源门禁拒绝，因此 **resync=0、recovery=0、resume=0、
新增矩阵执行=0**。不重复探测到通过，不以旧通过文件替代新批次。已审核的辅助
七文件未改，仍对应 `fa597017c2317772a0f7f34faa75194ffecec8f2`；没有扩张运行框架。
目录内 Python/C 只是本批只读采集、复算与进程核验脚本，不是新搜索/计时协议。

| 验收字段 | 结果 | 精确范围 |
|---|---|---|
| evidence_integrity_pass | true | 新诊断流/来源核验及历史保护；不是恢复证书 |
| execution_complete | false | random 3/12，greedy 0/12；0/2 完整轨迹 |
| timing_checks_pass | false | 新 recovery **未执行**，没有新的 20 区间或宿主调用时钟证书 |
| comparison_ready | false | 没有六行预算结果或候选独立复测 |

[独立后处理](../evidence/p3_clock_repair/20261010-121004/diagnosis_analysis.json)
退出 0 只表示所声明的诊断完整性成立，不能读成时钟或正式比较 PASS。

## 集中只读诊断与权限限制

实际命令、超时、PID、UTC/QPC 端点、stdout/stderr、退出码和字节/LF SHA 均见
[`operations/`](../evidence/p3_clock_repair/20261010-121004/operations/)。先保存
[命令计划/来源](../evidence/p3_clock_repair/20261010-121004/diagnostic_commands.json)，
再采集；没有安装诊断依赖。Windows 子进程使用明确的 Windows PowerShell 路径、
仅子进程 PSModulePath，且先确认 Get-FileHash 可用。
本批局部`.gitattributes`仅禁用此新目录的行尾转换，保存raw流/副本的字节SHA；
不改根属性或旧文件。Git规范化身份与原运行时字节身份仍分别保留。

- 12:12 宿主 W32Time 为 Running / Automatic，当前 token 非管理员。
  `w32tm /query /status /verbose` 退出 0，但 Leap=3（未同步）、stratum=0，
  源显示 `time.windows.com,0x9`，最后成功同步为 10-09 21:20:23，最后错误为
  “没有可用的时间数据”。成功查询不等于成功同步。
- `/query /source` 和 `/query /configuration` 均明确返回 **2147942405 /
  0x80070005（拒绝访问）**；当前完整配置记 unknown，不用历史事件冒充当前配置。
  `/query /peers` 成功：一个既有客户端 peer `time.windows.com,0x9`。
- 因权限不足且当前配置无法完整核验，**没有执行** `w32tm /resync /rediscover`，
  未启动服务、提权、更换服务器或改组织策略。[处理决策](../evidence/p3_clock_repair/20261010-121004/treatment_decision.json)。
- 查询 10-09 16:00 至 10-10 12:12 的 System（70 条）及已启用的 Time-Service/
  Operational（42 条）事件，保留 **完整消息**、时间、provider、record ID；每类
  上限 300 条，日志为环形，不能证明保留范围外不存在事件。
  [按 GB18030 严格解码的消息](../evidence/p3_clock_repair/20261010-121004/windows_events_readable.json)。
- 21:20 有事件 37/35 记录接收数据/同步；次日 06:35、07:35、08:34、09:36、11:02
  有事件 134 明确记录 time.windows.com DNS 失败（0x80072AF9）。12:17 的只读 DNS
  查询成功解析到 52.231.114.183，这是另一时间的事实，不能证明 NTP/UDP 可达，
  也不能将这些次日错误认作前一天 18:40 异常的已证实原因。
- 系统时间变更、休眠/唤醒及 Time-Service 配置消息全部保存；18:34 的
  VMICTimeProvider 消息自述非 Hyper-V 来宾环境下停止可能正常，不能据此断言 WSL
  虚拟时钟故障。没有发现能直接归因那 20 区间的宿主事件证据。

## WSL、频率与旧区间复算

Windows 仍报告 10.0.26200.9457，WSL 包 3.0.1.0、Ubuntu 24.04、内核
6.18.40.1-microsoft-standard-WSL2、GCC 13.3.0；编译器实际 SHA 匹配原 session。
只读 CPU 查询仍为 AMD Ryzen 9 7940HX、16 核/32 线程；未发现机器/版本更换证据。
报告的宿主启动为 10-09 21:17:49，WSL `uptime -s` 为 10-10 12:10:48，后续内核
日志也显示新的 WSL 启动记录；版本未变但启动状态与旧批不同。没有主动执行
shutdown、切 clocksource、升级内核或改变配额。启动/日志时间也不是独立物理时钟。

WSL 当前 clocksource=tsc；可用项为 tsc、hyperv_clocksource_tsc_page、
hyperv_clocksource_msr、acpi_pm。实际同步服务为 enabled/active 的 systemd-timesyncd；
chrony/chronyd/ntp/ntpsec 单元为 not-found。timedatectl status/show 报告已同步；
timesync-status 却同时记录约 -1.259 秒 offset、475.772ms jitter、packet count=2。
已保存服务状态、show-timesync、跨异常时段的同步日志及可取得的内核时钟日志；
“已同步”状态不证明通过本项目的一致性判据。

本批 [`read_adjtimex.c`](../evidence/p3_clock_repair/20261010-121004/read_adjtimex.c)
仅用 `struct timex state={0}; state.modes=0; adjtimex(&state)`，没有设置调用。
GCC `-std=c11 -O2 -Wall -Wextra -Werror` 编译及运行均退出 0，二进制在独立
`/var/tmp/matrix-autotuner-clock-repair-20261010-121004-read-adjtimex`，不提交。
源与二进制 SHA、实际命令见原始日志；字段单位以本机 timex 头文件旁证：

| 字段 | 本次读数 | 单位/意义 |
|---|---:|---|
| requested / returned modes | 0 / 0 | 只读 |
| return_state | 0 | 内核返回值，不是本项目时钟 PASS |
| freq | -1816586 | scaled ppm |
| freq / 65536 | -27.718902587891 | ppm；不使用未经缩放的原数 |
| tick | 10020 | 微秒 |
| status | 8192 = 0x2000 | STA_NANO |
| offset | 0 | 纳秒（由 STA_NANO 决定） |
| maxerror / esterror | 0 / 0 | 微秒；不代表已证明物理误差为零 |

旧 20 区间用未改的共享检查器从原始整数端点重算，包含 stdout/manifest/操作来源
及保存 delta 的一致性核验。两窗口 raw integrity=true，MONO/RAW **20/20 失败**，
REALTIME/RAW **2/20 失败**；Windows 各自完整调用 UTC/QPC 均通过。旧 manifest
的判据定位错误及失败 summary 保留，补充正确位置哈希不追认旧整体 PASS。
[20 条完整复算](../evidence/p3_clock_repair/20261010-121004/old_twenty_recomputed.json)。

观察到 `(MONO-RAW)/RAW` 为 33161.663–55051.737 ppm（3.316%–5.505%），**只作
差异描述，不是校准因子**。A/B 第 4 区间的 REALTIME-MONO 分别约 -1.401036、
-1.326827 秒；旧同步日志也有多次初始同步/服务启动。频率纪律、同步调整和虚拟化
时钟都是待检验解释，但旧区间没有同期 adjtimex/tick 或逐次调整来源记录；当前
freq 分量仅 -27.719ppm，不能解释或排除旧时段的其他调整，也不能确认根因。
不同调用范围的 Windows 全程和 WSL 内部区间不做相等比较，不校准旧 Grid/P3。

## 资源、验证与历史保护

12:12:47–53 的原正式 JSON 门禁退出 2 / REJECT，重新解析字段结果亦为 false：
宿主最低 **422170624 字节（约 403MiB）**，WSL 可用 4913426432 字节，根盘空闲
223848574976 字节；CPU 均值 2.8%、最高 13%，WSL swap 使用 0。仅宿主内存未达到
2GiB。保留宿主提交量/分页及另外时刻的 top 工作集、WSL memory PSI/swaps；
后一个快照不替代门禁，不把各进程共享工作集简单相加。没有清全局缓存或结束应用。

- 初始封存 root/子检查点、JSONL 副本、run_id 集合、字节及 LF SHA、Git index blob。
  10213 个已有 evidence/code/config/autotuner/scripts/tests 文件运行时 SHA 全相同。
  [保护清单](../evidence/p3_clock_repair/20261010-121004/protected_files_before.json)。
- 原归档、运行器、协议、GCC、四档候选及 reference 数据等 **32/32 实际 SHA**
  匹配；原教师 C 字节 SHA 为
  `188d011109c4470e1f41829216e8677a5c2d8f2b7c8a44215652320dbdf6de15`。
- 七个辅助文件对 fa59701 的 Git 内容一致，工作树/干净 Windows 归档实际字节另列，
  PS 行尾差异不冒充字节相同。[来源核验](../evidence/p3_clock_repair/20261010-121004/reviewed_auxiliary_identity.json)。
- 从既有干净 fa59701 副本实际重跑 **21+7 个针对性回归**，含 Windows 模块启动及
  合成异常拒绝，全部通过；WSL CLI help 退出 0，配置列表确认 20 个唯一项。
  合成测试不调用真实时钟探针；没有重复历史 160 案例或默认规模实验。
- 当前诊断的独立后处理从原始流复算，不信任 collection 中的 pass；原 campaign
  另做只读结构/原始执行核验，PASS 仅认证证据，0/2 轨迹未完成。新/旧部分组均不计分。

## 成本与后续入口

原 campaign 不变：3 完整配置、23 条执行（18 完整组、3 已 abandoned、2 待重启），
原 `PAUSE_REQUEST` 保留，独立复测 0。余 21 配置及去重候选复测，尚无六行预算表。
活动 7120.754915s，其中门禁/等待 1165.348475s；终态调用 3668.358619s；
部分执行进程 2236.427057s（已放弃 1336.598866s、待重启 899.828191s），复测 0。
这些范围嵌套，不全部相加；本轮正式增量均为 0。端到端前缀成本仍 unknown，见
[P3_COST_SCOPE](P3_COST_SCOPE.md)。

独立分析截止时记录的辅助命令 QPC 区间**并集**为 200.514293s；逐操作时长之和
209.126912s 含 8.612619s 并行 fetch/元数据重叠，不能当作墙钟总时间。分析本身
10.968886s、后续保护/进程/提交验证另列日志；不加入嵌套 WSL 子命令，不宣称含
编辑/模型/离线/推送的完整本轮成本。诊断不混入 campaign 或搜索观测。
随后包含独立分析、保护/进程及交付检查的已记录区间并集为 **250.155887s**；
[逐项成本索引](../evidence/p3_clock_repair/20261010-121004/auxiliary_cost_index.json)
说明截止范围和排除项，不再与前述200.514293s重复相加。
[最终保护/部分组/进程核验](../evidence/p3_clock_repair/20261010-121004/final_state.json)
确认两个部分组的3/2条样本均未进入分数、无正式进程、原runner锁可获取。

需要用户在 **管理员 Windows PowerShell** 保存以下只读输出；只有确认既有配置
适合同步时才执行一次 resync，并保存结果和之后状态（不保证会成功）：

```powershell
Get-Service W32Time
C:/Windows/System32/w32tm.exe /query /status /verbose
C:/Windows/System32/w32tm.exe /query /source
C:/Windows/System32/w32tm.exe /query /configuration
C:/Windows/System32/w32tm.exe /query /peers
# 仅配置适当时一次；不反复同步，不换服务器或修改策略
C:/Windows/System32/w32tm.exe /resync /rediscover
C:/Windows/System32/w32tm.exe /query /status /verbose
```

先把操作证据交外部复核，并恢复宿主至少 2GiB 可用内存；本阶段结束，不自动等待
或重试。获得新一轮指令后，用新的唯一目录，沿用 fa59701 入口执行 **一次**
A/B 各 10×3 秒 recovery。全部时钟/身份/正式门禁和当前检查点绑定通过，才使用
该批 recovery 的目录执行 resume。以下是下一轮条件满足后的入口，**本轮未执行**：

```powershell
$futureClockBatch = Get-Date -Format 'yyyyMMdd-HHmmss'
$futureRecovery = "evidence/p3_clock_repair/$futureClockBatch/recovery"
$futureResume = "evidence/p3_clock_repair/$futureClockBatch/resume"
python scripts/start_p3_first_seed.py --mode recover --auxiliary-sha fa597017c2317772a0f7f34faa75194ffecec8f2 --output $futureRecovery
# 仅 recovery 的20区间、同调用宿主检查、身份、资源及当前检查点绑定全部通过后
python scripts/start_p3_first_seed.py --mode resume --auxiliary-sha fa597017c2317772a0f7f34faa75194ffecec8f2 --recovery-directory $futureRecovery --output $futureResume
```

不能直接运行旧 legacy PS 入口或复用旧通过文件。
若需更换机器、编译器、WSL/内核版本或正式计时协议，应新 session 及匹配完整 Grid，
由审计裁决；本轮未实施这些变更。即使未来复核通过，也不追认旧数据已校准。
