# Matrix Multiplication Autotuner (P1)

本仓库用于《软件系统优化》实践项目 P1。当前完成的是 **P0：环境与源码
核查、GitHub 准备和有限预实验**；P0 数据只用于建立可审计基线，不代表正式
调优结果或最优配置。

## 当前结论

- 老师源码已按字节保存在 [`code/original/`](code/original/)，SHA-256 为
  `188d011109c4470e1f41829216e8677a5c2d8f2b7c8a44215652320dbdf6de15`。
- 实际预实验环境为 WSL2 Ubuntu 24.04、GCC 13.3.0。
- O0/O1/O2/O3 编译成功；`n=65` 的 6 个有效诊断案例均通过独立 `long double`
  逐元素参考验证；大于矩阵尺寸的块按原接口被拒绝。
- 默认 `n=4096` 需要 384 MiB 三矩阵存储并执行约 687 亿次乘加，P0 未启动
  默认规模长测。

## 复现 P0

在 PowerShell 中运行：

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc `
  'cd /mnt/e/software_system/project01 && bash scripts/run_p0_preexperiment.sh'

powershell -ExecutionPolicy Bypass -File scripts/verify_p0.ps1
```

环境重新采集入口：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/collect_p0_host.ps1
wsl.exe -d Ubuntu-24.04 -- bash -lc `
  'cd /mnt/e/software_system/project01 && bash scripts/collect_p0_environment.sh'
```

环境脚本只向标准输出写结果；如需更新证据文件，应显式重定向并保留采集时间。

## 文档入口

- [`docs/P0_DISCOVERY.md`](docs/P0_DISCOVERY.md)：要求、环境、源码分析、预实验和 P1-P5 计划。
- [`docs/WORK_LOG.md`](docs/WORK_LOG.md)：命令、失败、定位与修复记录。
- [`docs/AUDIT_HANDOFF.md`](docs/AUDIT_HANDOFF.md)：P0 交接与证据索引。
- [`report.md`](report.md)：老师指定的唯一正式报告文件，目前为有证据的 P0 骨架。
