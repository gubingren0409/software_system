# 原生C与宿主有界QPC参照诊断（50cd24e之后）

本轮先诊断参照，不修改正式矩阵C、核心计时源、输入、容差、搜索或评分。
内存/CPU资源策略v2已审核，原样保留。现有d6811cad/session
2c270825458a4857a5ac9df5aadf597b仍为空；旧6/20失败不改写、不校准旧Grid/P3。
证据根：[20261010-190645-1375f246](../evidence/p3_clock_reference/20261010-190645-1375f246/)。

## 采集前固定方案

独立[原生C探针](../code/diagnostics/clock_reference_probe.c)按端点顺序读取CPU编号、
M1=MONOTONIC、RAW、M2=MONOTONIC、REALTIME、BOOTTIME、CPU编号。整数纳秒直接输出。
默认路径调用libc clock_gettime，与正式C使用相同API；不预设libc一定选择vDSO。
系统调用路径仅C组使用SYS_clock_gettime；D组仅对该临时子进程绑首个允许CPU。
所有模式使用同一持续存活的WSL原生进程、递增序号和逐行fflush。

| 固定顺序 | 读取路径/亲和性 | 工作条件 | 区间数 |
|---|---|---|---:|
| A | 默认libc，不绑核 | nanosleep约3秒 | 10 |
| B | 默认libc，不绑核 | 单线程volatile整数忙工作约3秒 | 10 |
| C | 直接syscall，不绑核 | 空闲等待约3秒 | 5 |
| D | 默认libc，绑首个允许CPU | 空闲等待约3秒 | 5 |

sleep/忙循环的3秒只是工作安排，不作准确性证据。宿主参照为Windows真实QPC时长边界。
[宿主采集器](../scripts/run_clock_reference.py)在起点/终点READ发送前和响应读取后记录
Hs_send/Hs_recv、He_send/He_recv及Frequency。所有通信、模式、PID、序号与读取边界留存。
原生进程只启动一次，不能减去猜测的启动开销，也不比较不同域的绝对时间戳。

L=(He_send−Hs_recv)/Frequency，U=(He_recv−Hs_send)/Frequency。
U−L必须≤20ms，容许误差a=5ms+1%×U。来宾时长必须落入[L−a,U+a]。
MONOTONIC采用保守读取范围[(M1_end−M2_start),(M2_end−M1_start)]，整个范围须落在
宿主允许范围内；M2−M1读取跨度≤20ms，出现回退或无效整数不认证。
[统一判定](../scripts/p3_clock_reference.py)先做整数相减，并用整数交叉乘法判断边界。
这是项目拟议诊断标准，**不是官方精度保证或物理时钟绝对准确认证**。

先保存manifest的方案、完整源码SHA、编译命令、编译器/二进制哈希，再执行这一轮。
采集总预算480秒，元数据子操作有超时；每完成区间立即flush JSONL，原始通信流同样flush。
宽边界标无法判定，整组不认证；失败样本仍保留，无补采、筛选、比例修正或第二轮。
固定四组均收集，除非进程/通信/超时使之无法继续；不因A组失败更改后续条件。

只读元数据含当前/可用clocksource、uptime/boot_id、CPU型号/允许CPU、同步服务及日志、
与tsc/clocksource/timekeeping相关内核日志。C探针adjtimex modes明确为0，只读，
freq/65536换算ppm，单位随STA_NANO保存；权限/工具缺失标unknown，不新增门槛。
不调整NTP/clocksource/内核/电源，不重启WSL或终止用户应用；不并行正式实验。

## 冻结的决策表

1. 默认A/B全部20区间MONOTONIC匹配宿主、RAW仍失配时，可提出新版有界宿主准入，
   RAW保留诊断警告；只认证当前条件的跨域一致性。须另提交运行内容、干净归档、
   新空session、新协议与一次独立recovery，诊断包不能冒充恢复证书。
2. 若发现探针/解析错误，做最小修复并保存修复前后差异，旧失败仍保留。
3. 默认MONOTONIC失配、回退、宽边界或数据不完整，保持阻塞并交付原始证据。
   不能以C/D单独通过替代A/B，也不能以MONOTONIC/REALTIME或UTC/QPC互相一致替代宿主边界。

只有新协议确有证据支撑、最终冻结内容的一次recovery及独立来源/计时/eligible全通过，
才条件恢复首种子random/greedy各12配置及4/8/12去重复测；串行，1预热+5fresh中位数，
Formal等待含采集最多120秒。旧分数不迁移，不扩展种子/算法或自动新Grid。
本页先保存方案，实际数据、独立复算、决策与成本在采集后追加。

## 实际结果与决定：P3_CLOCK_BLOCKED

方案/源码先提交为`7950a8a533f5c60dd8fb7a0d26cb90a3e3d2b32d`，之后才编译、落
[manifest](../evidence/p3_clock_reference/20261010-190645-1375f246/manifest.json)和采集。
manifest SHA256为`acc421f4055f3b1e73fc095ab038055d37c97161f945245bbb73914e62887a6b`；
执行二进制SHA256为`6665366ddabad468f3e6c86be6ab5fb263619a405033cab46619943501b0cde6`。
GCC13.3.0以`-std=c11 -O2 -Wall -Wextra -Werror`编译；命令、版本、动态符号和哈希
各有operation/stdout/stderr。矩阵C及正式计时源没有改动。
正式工作C在matrix_multiplication.c第146/162行调用CLOCK_MONOTONIC；本轮只运行独立
同API探针，未执行矩阵程序，也不把独立探针当作整个正式程序已认证。

一次固定顺序采完30/30，持续原生PID2189，Windows wsl.exe PID120724，QPC频率
10000000；96条响应（HELLO、4个MODE、90个READ/WAIT/READ、QUIT）与原始流一致。
探针和外层采集均真实退出0，表示采集完成，**不表示时钟认证通过**。
[独立复算](../evidence/p3_clock_reference/20261010-190645-1375f246/independent_diagnostic.json)
不信任保存的PASS，重新核对Git/运行来源、消息/PID/序号、整数端点、读取跨度、原始流哈希
及固定样本数量，退出2（不认证）。所有30条证据完整、可判定，无回退。

| 条件 | MONOTONIC匹配宿主 | RAW匹配宿主 | REALTIME/BOOTTIME匹配宿主 |
|---|---:|---:|---:|
| A 默认/不绑核/空闲 | 10/10 | 10/10 | 各10/10 |
| B 默认/不绑核/忙工作 | 8/10 | 10/10 | 各8/10 |
| C syscall/不绑核/空闲 | 5/5 | 5/5 | 各5/5 |
| D 默认/CPU0/空闲 | 5/5 | 5/5 | 各5/5 |

全部通信不确定性0.8019–1.2861ms，均低于20ms；最大M2−M1为2326ns。
两个失败区间如下（**序号为零起点**，秒）：

| 区间 | 宿主[L,U] | MONOTONIC保守范围 | RAW | a | 最小MONO超过U+a |
|---|---|---|---:|---:|---:|
| B1（第2条） | [2.920034100,2.920943400] | [3.001507735,3.001508090] | 2.920459798 | 0.034209434 | 0.046354901 |
| B2（第3条） | [2.834922100,2.835973300] | [3.001663284,3.001663628] | 2.835416878 | 0.033359733 | 0.132330251 |

B1端点CPU16→17，B2端点CPU17→17；每个端点内部CPU未变。后者说明记录到的跨端点
CPU迁移不是发生失配的必要条件，但没有记录整个区间的调度轨迹，不能据此排除迁移或
虚拟化的影响。两条的REALTIME和BOOTTIME也偏离QPC，彼此一致不能代替宿主参照。
原始整数端点见[intervals.jsonl](../evidence/p3_clock_reference/20261010-190645-1375f246/intervals.jsonl)，
全30行秒单位旁表见[interval_summary.csv](../evidence/p3_clock_reference/20261010-190645-1375f246/interval_summary.csv)。

执行预声明决策表第3项：**默认C的MONOTONIC在B组失配，阻塞，不启用新版准入**。
RAW本轮30/30与宿主匹配，但这不证明RAW物理绝对准确，也不能追认旧RAW参照或校准旧成绩。
C/D是空闲且时序较晚的条件，不足以区分忙工作、阶段漂移、读取路径、CPU迁移等因素，
不能称为“syscall/绑核修复有效”。未发现可以据此实施的解析或读取错误，根因仍unknown。
本轮没有调整系统、改正式协议、建立新正式session、采第二轮或运行4096。

## 只读环境、来源与缺失项

[环境逐命令原始输出](../evidence/p3_clock_reference/20261010-190645-1375f246/wsl_environment.stdout.txt)
保留命令、退出码、stderr和子耗时；Windows外层operation另保存UTC/QPC范围。
当前tsc，可用tsc/hyperv_clocksource_tsc_page/hyperv_clocksource_msr/acpi_pm；
WSL3.0.1.0、内核6.18.40.1-microsoft-standard-WSL2、Windows10.0.26200.9457，
AMD Ryzen9 7940HX，允许CPU0–31。wsl.exe版本原始流为UTF-16LE，读取时需按此解码，
不是修改原始日志。Python3.12.6、Git2.50.1.windows.1。

采集前uptime37.29秒，boot_id=`21f7ee99-f877-4ff3-a129-736c2b40c74c`；
timesyncd running，timedatectl报告已同步，日志含19:16:18.933507的初始同步。
组合systemctl查询退出4是因为chrony/ntp unit不存在；timesyncd本身有有效状态输出，
缺失服务记unknown而不新增门槛。dmesg保留声明过滤器匹配的tsc/clocksource/timekeeping消息。
未捕获WSL启动前状态，未主动shutdown/restart；日志中的多个boot不用于断言异常因果。

原生HELLO的adjtimex modes=0、returncode0；freq=0（0ppm）、tick=10000微秒、
status=8193、offset=4462008纳秒、maxerror=2500微秒、esterror=0微秒。
这是一次只读状态，不是区间内连续调频记录；无法据此证明或排除同步/虚拟化根因。
物理准确度、忙工作是否因果、底层vDSO实际选择及异常时的连续频率状态仍unknown。

[clean_export](../evidence/p3_clock_reference/20261010-190645-1375f246/clean_export.json)分别
记录12个诊断/协议/C/Python文件的Git blob、实际字节SHA、归档字节SHA和LF/CRLF数量，
这些文件三方字节一致；教师C另严格复核`188d011109c4470e1f41829216e8677a5c2d8f2b7c8a44215652320dbdf6de15`。
继承的qpc/capture与正式运行依赖另由
[retained_identity](../evidence/p3_clock_reference/20261010-190645-1375f246/retained_identity.json)
核对d6811cad的51项归档和工作区Git内容；不把可允许的行尾转换称为执行字节一致。
内存/CPU、measurement、campaign及原时钟判据四个配置对d6811cad字节不变。

## 回归、失败与最小修复

11项针对性回归通过，包括2^60以上整数的1ns差值、通信顺序/缺失/PID、宽边界、
回退、非法/非有限整数、真实失配、RAW警告不能证明MONO、C/D不能替代默认路径、
保存PASS不能覆盖原端点，以及旧20区间仍6失败。未重跑160/834历史案例或矩阵目标。
从准确7950a8a导出的独立空目录（无.git、初始pycache0，去除PYTHONPATH，禁写字节码）
再次通过11项、CLI帮助、WSL20唯一配置；归档C重编译哈希等于实际执行二进制。

第一次收尾辅助验证把Linux GCC配置交给Windows CLI，实际输出compiler not found；
错误使用os.execv的Windows包装器未转交可靠子退出码，外层后续解析空stdout退出1。
原`clean_entry`/`clean_configs`日志保留，不能把其0当作CLI通过。
收尾助手改为subprocess.run并转交returncode，退出7负控确实捕获7；配置列表移到
WSL干净目录，`clean_entry_v2`退出0。初始助手SHA为
`86d352d77796845fdee14ac61adb0454139726811d44c3a075adc2a485ea5043`，
最后流哈希核验进一步确认：首轮4个execv辅助包装器的stdout/stderr可在包装器退出后
继续写入，使部分原operation的流哈希与最终文件不一致。它们全部明确列为拒绝的辅助
记录，不用于验收、不覆盖哈希或日志。最终11项/帮助/20配置以可靠等待的v2记录为准。
首次发现该问题的`delivery_verification_entry`退出1保留；明确报告拒绝记录的v2退出0。
这不是删除诊断异常样本：30个真实区间和B1/B2失败仍全部参与判定。
此修复仅涉及证据收尾，不修改已提交/已执行的原生探针、采集器、判据或正式运行器。
最终助手源码见[finish.py](../evidence/p3_clock_reference/20261010-190645-1375f246/finish.py)，
通过摘要见[clean_validation](../evidence/p3_clock_reference/20261010-190645-1375f246/clean_validation.json)。
最终流哈希、拒绝辅助记录及链接核验见
[delivery_verification](../evidence/p3_clock_reference/20261010-190645-1375f246/delivery_verification.json)。
下述完整性true的范围是实际诊断、冻结身份、历史保护与最终v2干净验证，不认证那4条
首次失败的辅助包装器记录；所有旧记录保留可审计。

## 验收、历史保护及成本范围

| 字段 | 当前结果/范围 |
|---|---|
| evidence_integrity_pass | true：30区间/96响应/来源/旧文件保护 |
| reference_match_pass | false：默认B1/B2失配 |
| timing_checks_pass | false：不认证默认C路径 |
| execution_complete | false：首种子两轨迹未运行 |
| comparison_ready | false |

新recovery调用/区间0，Formal门禁**未执行**，正式目标0、配置0/24、轨迹0/2、
前缀0/6、独立复测0、部分/放弃组新增0。原d6811cad session保持initialized且无观测；
7405fcc3/e308bfb和全部REJECT、旧Grid、旧23条原始执行/ID、完整组、部分组及PAUSE_REQUEST
均不变。[历史保护](../evidence/p3_clock_reference/20261010-190645-1375f246/history_protection_after.json)
逐域原字节摘要核对10623个文件，通过；前后session快照完整保存。进程清单为空。

[成本](../evidence/p3_clock_reference/20261010-190645-1375f246/costs.json)：真实诊断入口
QPC91.6706073秒，内含采集90.9342755秒，其中原生进程90.1953194秒；范围嵌套不相加，
全部低于480秒。声明范围的非嵌套捕获操作合计234.2932793秒，包括fetch、构建、
独立审计、失败/修复干净验证和保护父调用；其子命令不再加一遍。
生成摘要父调用另2.6291969秒，编辑、后续文档/核验/推送未包含，完整端到端成本unknown。
正式执行、候选复测、Formal门禁等待、放弃尝试本轮增量均0。
原session初始化活动0.100855773秒、旧e308bfb活动7120.754915秒等仅历史范围，不相加
或归到本轮诊断；继续遵守[P3_COST_SCOPE](P3_COST_SCOPE.md)。

## 下一步（本轮停止）

下一轮先外审本轮默认C/宿主真实失配。若需进一步定位，可另行预声明忙工作下的
libc/syscall与绑核对照、连续只读频率/事件观测；这是待审核方案，不是已证实修复，
本轮不追加采样。任何内核/clocksource/电源/机器调整需单独授权与环境记录；若改变
正式计时源/准入，须真实新内容、新协议/干净归档/新session及独立有限恢复证明，
不能复用本包作证书，也不能用旧Grid声称同条件全局最优。

仅重算保存数据的入口（不会采样/恢复；预期退出2）：

```powershell
python -B -X utf8 -c "import json,sys; from pathlib import Path; from scripts.p3_clock_reference import audit_diagnostic; r=audit_diagnostic(Path('evidence/p3_clock_reference/20261010-190645-1375f246')); print(json.dumps(r,indent=2)); sys.exit(0 if r['diagnostic_certifiable'] else 2)"
```

当前不提供可直接跳过失败的resume入口；待外审决定后才推进新一轮有界处理。
