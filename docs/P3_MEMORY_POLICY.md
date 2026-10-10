# 内存准入修订 v2（ac33d9d之后）

本轮依据用户明确授权，区分宿主物理余量、宿主提交额度余量和WSL内部容量。
这是项目质量策略，不是教师要求，也不意味着通过门禁的性能数据必然可靠。
原始证据根：[20261010-174802-11f7775c](../evidence/p3_memory_policy/20261010-174802-11f7775c/)。
原7405fcc3/e308bfb session、旧Grid、所有REJECT/部分组封存，不迁入新分数，不校准旧数据。

## 集中策略与兼容性

配置：[resource_policy.json](../configs/resource_policy.json)，版本
`2026-10-10-memory-admission-v2`，schema `p3-resource-policy-v2`，输出gate schema v4。
规范化JSON SHA-256：`38e073716eafc5356d775509414018415bba05ac6e87e4e29be93663b90da9d9`；
文件字节SHA-256：`38a18cc4eef60473fbfa3316f7e9f6d0b72a8e9f582bdb6d14fc452ea59609e3`。
测量协议升为schema4，规范化SHA `03783dfa48ba277d693631b8c8cac11941fac19b45d5137205d7ce9b7cb0beb6`；
campaign升为schema3并绑定该哈希。搜索协议、C、输入、容差、计时、1预热+5fresh中位数不变。

| 条件 | Recovery | Formal |
|---|---|---|
| 五次Windows可用内存的最低值 | <512MiB拒绝；<2GiB警告 | 相同 |
| 五次CommitLimit−CommittedBytes的最低值 | <512MiB拒绝 | 相同 |
| WSL MemAvailable | ≥256MiB | ≥2GiB |
| WSL根盘空闲 | ≥1GiB | ≥1GiB |
| CPU五次、原1秒sleep间隔 | 只警告（旧10%/20%警告线） | 均值≤30%、最高≤60% |
| 门禁等待总预算 | 不循环recovery | 含采集/重试共120秒 |

提交计数必须为非bool的正整数，≤INT64_MAX，CommittedBytes≤CommitLimit。
零提交余量是可表示的拒绝，不可将缺失/零计数当作正常容量。所有原始样本保留；
分页只作质量证据，不因单个非零计数新增拒绝。Vmmem/交叉接口/完整meminfo是诊断字段，
缺失标unknown，不加入容量或额外门槛。不得计算“Windows可用+整个Vmmem工作集”。

PowerShell只采集，判定委托[autotuner.resources](../autotuner/resources.py)；主控、campaign、
measurement的WSL阈值及独立审计沿统一协议读取。重复阈值必须与集中策略一致。
旧CPU策略保存于[resource_policy_cpu_v1.json](../configs/resource_policy_cpu_v1.json)，
字节和规范化哈希与旧版相同；旧v3按原2GiB/CPU策略及原collector来源验收，旧v2按保存协议验收。
新旧record schema不互相冒用，不把新门槛用于翻写历史REJECT。

## 有界诊断与本轮真实读数

初始HEAD=ac33d9d897b4f3802251430956ae79fb4e4a49a8，project01，工作区干净。
复核旧host最低775036928 bytes、WSL6208774144 bytes、仅host_memory拒绝；旧A/B区间0、目标0。

独立诊断脚本声明一组并设置120秒超时，实际120.148205秒后被终止，stdout/stderr均空，
没有可恢复的完整组或已保存部分组，具体停留步骤unknown。失败PID/命令/退出1/超时标志保留，
**没有重跑该诊断**。另一次任务要求的真实资源入口在17:55完成，附同窗口诊断字段：

- 窗口17:55:30.2085913—17:55:41.8076159（Asia/Shanghai），五次宿主采样与WSL读数
  有各自先后，不声称完全同时；未捕获冷启动前状态，未关闭WSL制造冷启动。
- Windows AvailableBytes最低 **434728960 bytes（414.59MiB）**，新512MiB底线仍拒绝。
  同窗口较早的Win32_OperatingSystem交叉读数604827648 bytes；不能以它替换五次最低值。
- 最低提交余量 **29736370176 bytes（27.69GiB）**；CPU平均18%、最高51%，Recovery只警告。
- WSL MemAvailable **4742434816 bytes**；MemFree2750656512、Cached2208256000、
  SReclaimable57577472、AnonPages1788116992、Shmem5038080、Dirty618496 bytes；
  SwapTotal/Free均2147483648，使用0。完整meminfo保存在原始资源输出。
- VmmemWSL PID82464、WorkingSet5335613440 bytes，是工作集观测，不是可直接借用的额外容量。
- WSL3.0.1.0、内核报告6.18.40.1-1、Windows10.0.26200.9457；现有.wslconfig只读保留
  与memory/reclaim相关的匹配行和文件哈希，没有匹配到显式memory/autoMemoryReclaim值。

上述字段、全部CPU/提交/分页计数、时间边界、工具原始版本输出和退出码见
[discovery_analysis.json](../evidence/p3_memory_policy/20261010-174802-11f7775c/discovery_analysis.json)及
[actual_resource_capture.stdout.txt](../evidence/p3_memory_policy/20261010-174802-11f7775c/actual_resource_capture.stdout.txt)。
观测只能确认同窗口内余量与工作集，不能证实“WSL预占”或具体回收机制的因果解释。
没有修改系统配置、drop_caches、wsl --shutdown、NTP或终止用户应用。

## 源码需求估算与验证范围

候选A/B/C为三块静态double矩阵（matrix_multiplication.c:32—34），每块n²×8：
n4096每块128MiB、合计384MiB；验证另分配一行32768 bytes（:188）。
reference有两块静态矩阵（reference_generator.c:30—31）及calloc输出（:154），
同样约384MiB主要数据；输出文件128MiB。campaign先构建、生成/核验reference，再串行候选；
reference子进程与候选不并行，但Python父进程仍驻留（campaign.py:343—365）。
这些是主要数组估算，不包含Python/编译器/加载器/页表/stdio/Windows/WSL服务和文件缓存，
**不是整机精确峰值，也不是实测RSS**。本轮新默认规模RSS尚未测；n17实测及以后目标
GNU time/RSS、执行前后MemAvailable/swap/vmstat和运行中宿主分页应分别保存，不混用口径。

Windows18项资源回归通过；WSL18项（1个Windows专用跳过）通过。覆盖512MiB边界/提交
缺失或非法/两种WSL限值/CPU/用途/集中阈值一致/120秒/旧协议；实际PowerShell受控入口
与Python一致。历史原读数回放明确为合成诊断：新Recovery/Formal均通过且保留内存警告，
旧策略复算仍原REJECT，见[回放结果](../evidence/p3_memory_policy/20261010-174802-11f7775c/historical_replay_results.json)。
回放不是新资源门禁或正式性能证据，未修改历史文件。

## 冻结和有限恢复计划

运行代码先提交，然后导出该准确内容的干净归档，核验Git/实际字节、相关回归、CLI/20配置
及独立空缓存n17/O2/s8 fresh逐元素正确性；只初始化新空session，不导入任何旧分数。
新SHA、归档和session由本目录生成的session_plan.json及最终交付记录给出，避免自引用SHA。
不运行历史160/834验收或新Grid。

仅调用一次新recovery，入口重新采集自己的Recovery资源，不复用预提交快照。
A/B各10×3秒，原时钟容差/整数端点/同调用宿主检查不变，先落policy/manifest；资源拒绝
则不采区间，不再次recovery。独立复算eligible/来源/完整20区间全部通过后才条件resume，
Formal新门禁及批前/批后检查不可由Recovery代替。
只跑seed20261008的random/greedy12配置及4/8/12前缀去重复测，串行，约60秒报告进度。
O0按自身超时与进程/日志判断，不因慢而判卡死；OOM/退出/校验失败保留整组且无分数。
正式运行前后内存/交换及内存警告入报告；门禁通过仍不能证明稳定性，不删慢样本。
任何资源/时钟拒绝后停止并提交，不扩展种子/算法/Grid。费用按P3_COST_SCOPE分列，嵌套不相加。
