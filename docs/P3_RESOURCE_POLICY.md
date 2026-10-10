# P3 资源准入迁移 v1（2026-10-10）

本轮以 `aae4147f1e246c5fb115060ef484df625b611e3d` 为审计基点。用户明确授权
替换原 CPU 10%/20% 硬门槛；这是项目测量质量策略，不是老师规定。未修改系统设置。
当前执行证据根为 [`20261010-143415`](../evidence/p3_resource_policy/20261010-143415/)。
最终执行状态以该目录中的原始操作、独立验收及本文后续结果为准，不把预提交测试当作正式实验。

## 集中策略与适用范围

唯一配置为 [`resource_policy.json`](../configs/resource_policy.json)，版本
`2026-10-10-cpu-admission-v1`；规范化 JSON SHA-256：
`e191aee4348fa5501bb923dbf1be35741a188c738ebf6fdb4863bc91b0be5671`，
文件字节 SHA-256：`0b423aab2e40b4bc65df5d3d3a3969d54d819eaf36ecaf7ad22bf95f0297ab5d`。

| 用途 | CPU 五次原始采样（间隔仍为 1 秒） | 其他硬条件 |
|---|---|---|
| Recovery | 超过旧均值 10% / 单次 20% 仅警告，不拒绝时钟诊断 | Windows/WSL 可用内存各 ≥2GiB，WSL 根盘空闲 ≥1GiB，来源/数据/超时有效 |
| Formal | 均值 ≤30%，单次最高 ≤60%，同时满足 | 同上 |

这是**每个配置启动前**的背景负载准入，不限制矩阵程序运行时自身 CPU。
保留所有读数、均值、最高值、内存最低值、用途、版本、配置哈希、逐项判定及拒绝原因。
PowerShell 只采集，通过 [`autotuner.resources`](../autotuner/resources.py) 的同一判定实现
输出严格 JSON；主控、session/campaign 运行器和后处理重新核验原始数据与来源，而非信任 PASS。
未知用途、空/缺失/非有限或不可能的数据拒绝；Recovery 记录不能冒充 Formal。
运行中 Snapshot 仅为资源披露，仍不用于事后删除慢样本。

Formal 门禁每次配置等待预算 **120 秒**，包含采集、重试间隔及保存开销；单次采集上限
60 秒且不超过剩余预算，重查间隔 10 秒。拒绝时记录具体原因与耗时，超预算安全保存暂停。
旧 v2 记录用其各自保存的原协议读取，历史 REJECT 保留，不以新规则追认。

## 身份迁移与不变部分

新 measurement schema 为 3，规范化哈希
`df08b97fc86f8940ec046d797826df2ea94f98031a0bc34f8e02c81685698238`；
campaign schema 为 2，辅助批次/恢复证据 schema 为 3。真实新内容提交先于执行，
新归档路径、Git blob、执行字节/LF SHA、session ID、campaign 与资源用途通过参数及 manifest 绑定。
支持 `campaign --initialize-only --session-id ...`：核验源码/编译器并建立空检查点，不运行矩阵。

旧 `e308bfb873e6811c50ad685a979af345302fda8d` 归档、session
`dc1c292900654d44b36a72548b95a610`、原 campaign、3 个完整配置、23 条执行及 3/2 条部分组
封存保留。旧 PAUSE_REQUEST 不手动删除；本轮不再恢复旧 session，不拼入任何旧分数。
新版只有 fresh 正式样本；可复用身份验证后的构建/reference，不用性能缓存凑重复。

教师 C 原件、工作 C/头文件、core/measurement/search、20 配置空间及搜索协议保持不变。
输入仍 n=4096、random、种子 20261008，1 次成功预热 +5 次 fresh 测量，中位数计分，
任意失败不对成功子集计分；容差、超时、MONOTONIC 核心计时及搜索自身观测限制均不变。
旧 Grid 仅为带计时/资源限制的历史参考，不自动重跑 Grid、不按比例校准。
若后来比较其推荐 O1/s128 的同条件表现，必须单独 fresh 复测，不能声称新条件下全局最优。

## 本轮执行前声明

从准确的新提交导出干净归档：无 .git、初始无 pycache、移除 PYTHONPATH；单独空缓存
完成 CLI/20 唯一配置、针对性回归和 n=17/O2/s8 实际 fresh 正确性验证。
不重复历史 160 正确性案例、834 次诊断或长 Grid。

本轮仅授权一次 recovery：A/B 各 10×3 秒，共 20 区间；先保存 policy/manifest 再采集。
探针及判据文件不变，MONO/RAW 仍 `abs(MONO-RAW) <= 0.005 + 0.01*RAW`，
REALTIME/RAW 和 Windows **同一次完整调用** UTC/QPC 仍为原容差；整数纳秒先相减再换秒。
Windows 全程与 WSL 内部区间范围不同，不做相等比较。NTP 同步状态只读保存，不再为硬前提；
不再 resync、不更换服务器/clocksource/内核/机器。A 失败仍保留 B，结束后不重复探测直到通过。

仅全部时钟、来源、新 Formal 门禁通过才恢复**新** session 首种子 random/greedy 各 12 个唯一配置，
4/8 是同一轨迹前缀，候选按既有规则去重独立复测，不反馈搜索。串行、每 60 秒进度报告；
任意恢复失败即停止正式目标。首种子完成后交审，不扩展其他四种子或第四算法。

四项验收分开生成：evidence_integrity_pass、execution_complete、timing_checks_pass、comparison_ready。
未执行不写成通过或实测失败。成本遵循 [P3_COST_SCOPE](P3_COST_SCOPE.md)，终态调用、复测、
campaign 活动、门禁等待、放弃尝试、辅助诊断分列，嵌套范围不相加，完整端到端前缀仍未知。

## 当前交付结果

待一次有限 recovery 与独立验收后据原始证据填写；此内容提交尚不声明时钟或正式比较通过。
