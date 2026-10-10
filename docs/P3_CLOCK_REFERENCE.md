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
