# 审计交接入口

当前入口为0023ceed独立审计修订：[`P3_TIMING_AUDIT.md`](P3_TIMING_AUDIT.md)、
[`P3_AUDIT_HANDOFF.md`](P3_AUDIT_HANDOFF.md)；P3正式比较尚未完成，长实验仍暂停。
P2历史入口保留在[`P2_AUDIT_HANDOFF.md`](P2_AUDIT_HANDOFF.md)，P1/P1-R1在
[`P1_AUDIT_HANDOFF.md`](P1_AUDIT_HANDOFF.md)。以下仍是原P0历史交接。

## P0 交接（历史）

## 阶段判定

P0 的环境核查、要求核对、原始源码保存、静态分析与有限预实验已经完成。本文件
不宣称项目整体完成，也不宣称 P1-P5 已通过。

固定提交 SHA 与 GitHub 固定链接在提交、推送及远程核验后由终端交接消息提供，
避免为把提交 SHA 写进自身提交而制造循环提交。

## 审查入口

1. [`P0_DISCOVERY.md`](P0_DISCOVERY.md)：完整事实、风险、假设、P1-P5 计划。
2. [`../code/original/matrix_multiplication.c`](../code/original/matrix_multiplication.c)：
   老师源码的逐字节副本。
3. [`../code/original/SHA256SUMS`](../code/original/SHA256SUMS)：原件校验。
4. [`../experiments/p0/matrix_multiplication_probe.c`](../experiments/p0/matrix_multiplication_probe.c)：
   单独的 P0 诊断副本，不冒充原件。
5. [`../evidence/p0/preexperiment/summary.csv`](../evidence/p0/preexperiment/summary.csv)：
   结构化有限实验结果；同目录含每案 stdout/stderr/命令/退出码。
6. [`../evidence/p0/environment_host.txt`](../evidence/p0/environment_host.txt) 与
   [`../evidence/p0/environment_wsl.txt`](../evidence/p0/environment_wsl.txt)：原始环境输出。
7. [`WORK_LOG.md`](WORK_LOG.md)：失败、定位和修复过程。

## 已验证事项

- 原始源码仓库副本 SHA-256 与外部提供文件一致。
- GCC 13.3 O0/O1/O2/O3 均能无警告编译，仓库保留四级原始日志。
- n=65 的 6 个有效诊断案例逐元素验证全部 PASS；s=8/24/64 都不能整除 65。
- n=65、s=24 的 O1 调试构建通过 Valgrind，错误数为 0。
- s=128>65 被原程序的范围规则拒绝，没有伪造成“超大块计算成功”。
- 当前 GCC O3 反汇编仍含乘法和写回；同时保留“源码缺乏可观察结果”的跨工具链
  风险结论。
- P0 没有运行默认规模或完整搜索，性能数字被明确标为诊断数据。

## 建议审查者重点裁决

1. 是否认可 P1 采用“可覆盖的 MATRIX_SIZE + 严格 CLI + 单调计时 + checksum +
   correctness 模式”作为老师源码的最小工作副本改动。
2. 是否接受无放回随机搜索与带随机重启贪心作为 P3 两种算法候选。
3. 候选公平预算 B=8、5 个种子是否足够；还是要求不同预算/种子数。
4. P2 的候选测量规则（每配置 1 次预热 + 5 次正式测量、中位数排名）是否应在
   P1 pilot 后冻结。
5. `docs/AUDIT_HANDOFF.md` 等过程材料是当前工程审查证据，但公用约定要求最终
   正式报告不含内部审查用语；请裁决最终提交前是否保留这些辅助文件。无论裁决
   如何，`report.md` 都保持为唯一正式报告。
6. `perf` 在当前 WSL 内核不可用。P4 是否允许仅用汇编、硬件规格与稳定时序解释，
   或要求在不改变 P0 基线的前提下另行准备可用计数器环境。

## 复核命令

```powershell
git status --short --branch
powershell -ExecutionPolicy Bypass -File scripts/verify_p0.ps1
wsl.exe -d Ubuntu-24.04 -- bash -lc `
  'cd /mnt/e/software_system/project01 && bash scripts/run_p0_preexperiment.sh'
```
