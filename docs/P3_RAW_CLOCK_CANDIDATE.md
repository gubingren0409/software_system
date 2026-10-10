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

## 唯一采集的独立复算结果

探针/判据预提交 `a4982632ae9640001876c45dcba1cee581e07754`，
实际C源码 SHA256 `1fc6777c1bf613c1afd9eb4c9a21b5d14574abadc60a1b9e88b8a69c19654e50`，
GCC13.3.0编译二进制 `51170d65035e84f6a3345f6b2189f48c8b08e54e9f9195b0cd35a9baa93aa3bd`。
先有 manifest，再采集；22区间/90响应完整，RAW22/22通过，且全部保守范围落在未加容差的宿主边界内。
无宽边界/回退/补采；MONOTONIC零起点失败索引 `0,2,7,11,21`，原始数据全部保留。
独立复算 [independent_diagnostic.json](../evidence/p3_raw_candidate/20261010-234702-fixed-work/independent_diagnostic.json)。
原生进程QPC范围128.7020971秒；外层采集151.5732249秒包含只读元数据和启动，二者不能相加。

## RAW 候选实现 v1（仅候选，不是恢复许可）

主时钟为 `CLOCK_MONOTONIC_RAW`，结果schema升级v2，协议版本
`2026-10-10-raw-candidate-v1`。协议独立保存在
[`raw_timing_protocol.json`](../configs/raw_timing_protocol.json)，规范化SHA256
`3de408af7fc27a03c3169597fa50af4d7d42efc8f9946d2f1a434e65a0e39f49`。
target v2、measurement v5和campaign v4绑定同一协议。旧schema/旧协议仍原判据，不追认历史失败。

所有配置统一 RAW 起止整数ns，先整数相减，按同一 double 除法得到 elapsed_seconds，
解析后要求精确round-trip一致。拒绝错误时钟/版本、非整数/非正/溢出端点、非正时长、
不一致delta或非有限辅助数值。MONOTONIC辅助读取在RAW核心范围外，保留整数端点、
duration及差异，不把与RAW相等作为硬门槛，也不逐样本选择计时器。
初始化、reference、逐元素正确性和输出在核心计时范围外；乘法核心循环字节不变。
原始C、输入头、reference、搜索空间、随机/贪心源码及资源v2均不变。

构建键和性能键新增时钟协议哈希；执行记录包含同一哈希和实际主时钟。
正确性reference缓存身份独立、无需更换计时器；不得导入旧性能分数。
`autotuner/timing.py`是运行器/恢复入口/独立小尺寸审计共同读取的绑定与契约实现。
本候选协议 `formal_recovery_enabled=false`；恢复、正式Grid/campaign在启动前明确拒绝，
独立恢复审计也不能把候选诊断包当恢复证书。旧记录缺少新绑定时走明确的旧契约。
未来要启用正式运行，必须经外审授权、版本化准入实现、fresh宿主/RAW证据和新session；
正式比较需要同一新协议下 fresh Grid，不在本轮自动启动。

| 范围 | 时钟来源与限制 |
| --- | --- |
| 核心分数 | C RAW整数端点，统一计分，不校准 |
| 工作副本验证耗时 | RAW，仍在核心计时范围外 |
| 候选进程墙钟/看门狗 | Python CLOCK_MONOTONIC_RAW；排空管道线程，不用communicate的MONOTONIC deadline |
| Windows采集/验证总预算与操作成本 | 真实QPC/perf_counter，包含子进程启动和等待 |
| reference/setup/configuration/campaign旧成本字段 | 原Python MONOTONIC，未校准元数据；不能拿它校准RAW或当物理准确成本 |
| /usr/bin/time资源报告 | GNU time单独原样保存，非核心评分来源 |

## 有限验证范围与当前边界

仅关联回归和干净归档的n=17/O2/s8 fresh正确性/契约验证，20唯一配置检查。
历史受控v1夹具显式绑定旧协议，不用新版RAW记录冒充旧计时。
最终运行内容 `3c7a4ab11f7e753936ab8735e03364b44b4dd1ef`，干净归档
`/var/tmp/matrix-raw-candidate-3c7a4ab11f7e753936ab8735e03364b44b4dd1ef`。
Windows/WSL各80项相关回归（各2项平台跳过）、CLI帮助/20配置/隔离条件通过。
一次n17/O2/s8 random seed20261008 fresh运行，289元素通过、最大绝对误差1.7764e-15；
RAW差5991ns与输出5.991e-6s精确一致。这是契约/正确性诊断，不是性能比较。
[clean_validation.json](../evidence/p3_raw_candidate/20261010-234702-fixed-work/clean_validation.json)
与[candidate_validation.json](../evidence/p3_raw_candidate/20261010-234702-fixed-work/candidate_validation.json)
记录实际内容、Git/执行字节、二进制/reference及协议身份。
首次独立审计因原件目录非运行元数据行尾拒绝，原退出1/清单保留；另建运行身份清单只排除
SHA256SUMS和SOURCE_PROVENANCE.md（仍在10760项历史原字节保护中），教师C绝不排除或
允许行尾变换。仅重新审计同一结果通过，没有再跑矩阵或修改3c7a4ab运行内容。
收尾辅助脚本的实际来源SHA单列，不冒充候选归档中的执行源码。
本轮正式 execution_complete / timing_checks_pass / comparison_ready 均为 false；
recovery、Formal门禁、4096、Grid、搜索执行均为0，不生成新session或恢复证书。
