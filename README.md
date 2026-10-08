# Matrix Multiplication Autotuner (P1)

《软件系统优化》实践项目 P1。当前完成 **P1：正确性与统一测量基础**；完整 20 配置
Grid 和两种随机搜索尚未运行，有限试跑不代表最终最优配置。

## 当前状态

- 老师原件保持不变：SHA-256
  `188d011109c4470e1f41829216e8677a5c2d8f2b7c8a44215652320dbdf6de15`。
- 正式工作副本默认 `n=4096`，固定输入规则和种子，单调时钟只计核心计算，计时区外
  逐元素验证并输出严格 JSON。
- `ConfigSpace`、`TargetAdapter`、`Evaluator` 已实现；构建、reference 和性能缓存分离。
- `n=129/130` 的 160 个配置/输入案例全部通过；7 类故障注入和 6 类非法参数全部
  被正确拒绝。
- 默认规模四级代表配置成功；O3 代表配置五次核心时间中位数 `78.789159 s`，CV
  `1.10%`。这些是资源条件受限的 P1 pilot，不是正式 Grid 数据。

## 复现与检查

主要命令在 WSL Ubuntu-24.04、GCC 13.3.0 下运行：

```bash
cd /mnt/e/software_system/project01
python3 -m unittest discover -s tests -v
python3 scripts/verify_p1.py
python3 -m autotuner list-configs
```

完整小规模正确性会运行 160 个案例：

```bash
python3 scripts/run_p1_correctness.py
```

默认规模 pilot 很慢，且脚本会先检查资源；仅在需要复现实验、确认时间预算后运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/check_p1_resources.ps1 `
  -OutputPath evidence/p1/environment/pre_default_gate_new.json
wsl.exe -d Ubuntu-24.04 -- bash -lc `
  'cd /mnt/e/software_system/project01 && python3 scripts/run_p1_pilots.py --resource-gate evidence/p1/environment/pre_default_gate_new.json'
```

## 文档入口

- [`docs/P1_FOUNDATION.md`](docs/P1_FOUNDATION.md)：设计、验证、试跑、协议和成本。
- [`docs/P1_AUDIT_HANDOFF.md`](docs/P1_AUDIT_HANDOFF.md)：审计索引与待裁决事项。
- [`docs/WORK_LOG.md`](docs/WORK_LOG.md)：实际操作、失败和修复。
- [`report.md`](report.md)：仅纳入已有证据的课程报告正文。
- [`docs/P0_DISCOVERY.md`](docs/P0_DISCOVERY.md)：保留并纠正后的 P0 基线。
