# RAW 主计时器候选：预声明与边界

本轮以 `da0afd87bbfe594fa69ca98ddfdcc048c2de4770` 为审计基点。
目标是验证并准备 RAW 候选，不执行 recovery、Formal、4096、Grid、搜索或 resume。
原 `d6811cadda8ecd7b46225ebe65c51831278694a0` / session
`2c270825458a4857a5ac9df5aadf597b` 保持空，不写观测。

## 采集前固定方案

独立探针 `code/diagnostics/clock_fixed_work_probe.c` 与矩阵程序分开。
忙工作沿用 volatile uint64 更新式，每个短区间固定十亿次，长区间固定一百亿次；
循环结束不依赖任何时钟或 sleep。CPU17 已在采集前确认属于允许的 0–31。

五轮短区间，每轮 LU（libc/unbound）、SU（syscall/unbound）、LP（libc/CPU17）、
SP（syscall/CPU17）各一次；奇数轮正序，偶数轮反序。
第2、5轮后各加一个 LU 长区间，总22区间、400亿次更新、90响应（含 HELLO/QUIT）。
每区间 MODE / READ / WORK / READ；一个持续存活进程、递增序号、逐条 flush。
每端点同时记录 RAW1→MONOTONIC→RAW2，以及外层 MONOTONIC 双读、REALTIME、BOOTTIME、
CPU编号、只读 adjtimex（modes=0）、boot_id、uptime、clocksource。
缺失元数据写 unknown，不新增无关门槛。

Windows 真实 QPC 包围两个 READ，各自 send/recv 范围：
`L=(He_send-Hs_recv)/Frequency`，`U=(He_recv-Hs_send)/Frequency`。
RAW 保守范围是 `[RAW1_end-RAW2_start, RAW2_end-RAW1_start]`。
通信不确定性和 RAW 读取跨度均至多20ms；
整个 RAW 范围必须落在 `[L-a,U+a]`，`a=5ms+1%*U`。
另报是否整个落在未增加容差的 `[L,U]`。整数端点先相减，判据用整数交叉乘法。
其他时钟单独判定；MONOTONIC 失配仅保留诊断，不替换 RAW 证明。
这是项目拟议的跨域一致性标准，不是官方物理精度保证。

实际采集总预算480秒（Windows QPC/perf_counter），包括元数据。
每次通信仅可等待剩余总预算，不使用旧15秒上限误杀长工作。
内层进程另有470秒生存上限；错误/超时保存全部部分记录并停止。
不删样本、不替换、不补采、不启动第二轮、不调整系统设置。

## 决策（在采集前声明）

22区间完整、可判定且 RAW 全部通过，才允许准备候选。
默认路径失败/回退/无法判定，或任何区间不完整、RAW失败，均阻塞，
不能用 syscall/绑核通过替代。不生成正式恢复证书。
通过也只说明本轮条件下跨域一致性，不解释全部 MONOTONIC 根因。

本轮证据入口：
[唯一固定工作量批次](../evidence/p3_raw_candidate/20261010-234702-fixed-work/)。
先提交源码，再编译、保存源码/编译器/二进制身份和 manifest，最后才采集。
审计入口：`python -m scripts.p3_fixed_work_clock --directory <批次> --output <新文件>`。

## 待采集后的状态

诊断尚未执行；候选实现和 n=17 验证待诊断决策。
本轮正式 execution_complete / timing_checks_pass / comparison_ready 均为 false。
未来正式比较需要相同新计时协议的 fresh Grid，本轮不会启动。
