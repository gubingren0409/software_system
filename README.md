# Matrix Multiplication Autotuner (P1)

《软件系统优化》实践项目 P1。**P2：运行契约修复与正式完整 Grid 已完成，等待外部审计。**
20/20 配置有效，120 次正式执行与 6 次独立复测均通过全矩阵检查。
本会话测得最低中位数为 **O1/s=128：53.444627760 s**；独立复测为
**54.779446389 s**（+2.50%）。随机与贪心只做了诊断验证，尚未进行 P3 正式比较。
时钟未独立校准及运行中背景资源扰动限制见
[`docs/P2_TIMING_NOTE.md`](docs/P2_TIMING_NOTE.md) 和 [`report.md`](report.md)。

## 当前状态

- 老师原件保持不变：SHA-256
  `188d011109c4470e1f41829216e8677a5c2d8f2b7c8a44215652320dbdf6de15`。
- 正式工作副本默认 `n=4096`，固定输入规则和种子，单调时钟只计核心计算，计时区外
  逐元素验证并输出严格 JSON。
- `ConfigSpace`、`TargetAdapter`、`Evaluator` 已实现；构建、reference 和性能缓存分离。
- `ConfigurationEvaluator` 是三种搜索的统一配置测量接口：一次成功预热和五次
  强制新执行，取核心时间中位数；任意失败不计分。Grid、无放回随机、随机重启贪心
  均已实现，贪心每点七个单参数邻居，预算单位是唯一配置。
- P2 修复了非零退出搭配成功 JSON 仍可能计分的问题，并核对请求身份、n² 全量检查
  和冻结容差。从内容提交 `0d3dd5242c728d8001dd02a4e332185459d04721` 的无 Git/
  字节码缓存归档完成 31 项单元测试、160 个小规模正确性案例、7 类故障、6 类非法
  输入及 n=130 三策略实际链路（20/8/8 个配置）。证据见
  [`evidence/p2/validation-final/`](evidence/p2/validation-final/)。
- 最终交付内容提交`c2a964162915b8cf0019df4e73bcd7cd634d1902`另从干净归档复验，
  独立空缓存完成同样的全部检查，n=17为fresh且正确性通过、n=130三策略20/8/8通过；
  全部Python源码AST及归档内完整Grid证据审计通过。见
  [`evidence/p2/validation-delivery/summary.json`](evidence/p2/validation-delivery/summary.json)。
- P1 初次提交的 `.gitignore` 中 `core.*` 误忽略了本地实际使用的
  `autotuner/core.py`。R1 已恢复该文件、收窄规则，并从内容提交
  `bd9b7d264c42f7c65cd22b16a64a4a0f9c119c5f` 的无 `.git` 归档完整验证。
- `n=129/130` 的 160 个配置/输入案例全部通过；7 类故障注入和 6 类非法参数全部
  被正确拒绝。
- 默认规模四级代表配置成功；O3 代表配置五次核心时间中位数 `78.789159 s`，CV
  `1.10%`。这些 pilot 对应 R1 前本地实现且资源受限，仅保留为历史诊断数据，不是
  正式 Grid 数据；R1 没有重跑 `n=4096`。

## 复现与检查

主要命令在 WSL Ubuntu-24.04、GCC 13.3.0 下运行：

```bash
cd /mnt/e/software_system/project01
python3 -m unittest discover -s tests -v
python3 scripts/verify_p1.py
python3 -m autotuner list-configs
```

R1 的干净归档验收结果、逐命令 stdout/stderr/退出码和源码哈希位于
[`evidence/p1_revision1/`](evidence/p1_revision1/)。其中还实际确认移除 `core.py` 后
`verify_p1.py` 非零退出、`n=17/O2/s=8` 为 `fresh_measurement`，以及 `n=1/2`
reference 的 ASan+UBSan 边界检查。

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

- [`docs/P2_PROTOCOL.md`](docs/P2_PROTOCOL.md)：P2 冻结协议、资源条件与续跑规则。
- [`docs/P2_AUDIT_HANDOFF.md`](docs/P2_AUDIT_HANDOFF.md)：本轮审计及正式证据入口。
- [`docs/P1_FOUNDATION.md`](docs/P1_FOUNDATION.md)：设计、验证、试跑、协议和成本。
- [`docs/P1_AUDIT_HANDOFF.md`](docs/P1_AUDIT_HANDOFF.md)：审计索引与待裁决事项。
- [`docs/WORK_LOG.md`](docs/WORK_LOG.md)：实际操作、失败和修复。
- [`report.md`](report.md)：仅纳入已有证据的课程报告正文。
- [`docs/P0_DISCOVERY.md`](docs/P0_DISCOVERY.md)：保留并纠正后的 P0 基线。

## P2 正式证据与复现

正式内容提交固定为 `0d3dd5242c728d8001dd02a4e332185459d04721`，后续提交仅整合
证据、辅助复核与文档，不替换实验身份。原始样本、20 行统计、独立复测和完整性审计：

- [`evidence/p2/grid-session-0d3dd52/summary.json`](evidence/p2/grid-session-0d3dd52/summary.json)
- [`evidence/p2/grid-session-0d3dd52/grid_summary.csv`](evidence/p2/grid-session-0d3dd52/grid_summary.csv)
- [`evidence/p2/grid-session-0d3dd52/independent_retest.json`](evidence/p2/grid-session-0d3dd52/independent_retest.json)
- [`evidence/p2/grid-session-0d3dd52/evidence_audit.json`](evidence/p2/grid-session-0d3dd52/evidence_audit.json)
- [`evidence/p2/postprocessing/`](evidence/p2/postprocessing/)：绘图命令、版本、哈希和成本核算。

记录的活动会话耗时 6 h 38 min 28 s，其中资源门禁/等待约 35 min 54 s；关机前未完成
执行只有 325 s 最后观测下界，精确成本未知。该耗时来自单调时钟，不等于已校准物理时间。

正式协议为 n=4096、random、seed=20261008；宿主与 WSL 都至少 2 GiB 可用，
根目录至少 1 GiB，宿主 CPU 五次采样平均不超过 10%、单次不超过 20%。
资源不满足时不启动下一个配置；不修改系统设置或终止其他应用。

先在 PowerShell 导出指定内容提交（不要用最终证据提交代替内容提交）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/prepare_p2_content.ps1 `
  -ContentSha 0d3dd5242c728d8001dd02a4e332185459d04721
```

以下是已经实际使用的暂停续跑入口；当前 session 完整，不需要新增正式运行。
若复核续跑，必须保留 WSL 本地 cache，并由运行器核对内容、
编译器、二进制、输入、reference 及协议身份；已完成配置只从该 session 的全部
原始样本恢复。中断配置重新预热和五次测量，不使用性能缓存凑样本。

```bash
cd /var/tmp/matrix-autotuner-p2-content-0d3dd5242c728d8001dd02a4e332185459d04721
PYTHONDONTWRITEBYTECODE=1 env -u PYTHONPATH python3 -m autotuner grid \
  --content-sha 0d3dd5242c728d8001dd02a4e332185459d04721 \
  --git-identity /mnt/e/software_system/project01/build/p2/git_identity.json \
  --session-directory /mnt/e/software_system/project01/evidence/p2/grid-session-0d3dd52 \
  --resume
```

完整性复核（不启动目标性能实验；省略 `--output` 不写审计结果文件）：

```bash
cd /mnt/e/software_system/project01
PYTHONDONTWRITEBYTECODE=1 env -u PYTHONPATH python3 scripts/audit_p2_evidence.py \
  --session evidence/p2/grid-session-0d3dd52 --require-complete
```

使用上述内容归档重新进行小规模干净检查时，须另用空证据目录；脚本自行建立临时空缓存：

```bash
cd /var/tmp/matrix-autotuner-p2-content-0d3dd5242c728d8001dd02a4e332185459d04721
PYTHONDONTWRITEBYTECODE=1 env -u PYTHONPATH python3 scripts/run_p2_clean_validation.py \
  --content-sha 0d3dd5242c728d8001dd02a4e332185459d04721 \
  --git-identity /mnt/e/software_system/project01/build/p2/git_identity.json \
  --output /var/tmp/matrix-p2-clean-check-new
```

图表可在 Windows 已安装的 Python 3.12.6、matplotlib 3.10.6、numpy 2.3.3 下重建：

```powershell
python scripts/plot_p2_results.py --session-directory evidence/p2/grid-session-0d3dd52 --output-directory assets
```

CPU 平均≤10%/单次≤20%是**配置开始前的后台负载门槛**，不是限制矩阵程序使用 CPU。
它减少调度、缓存、带宽和频率/温度变化的干扰；不是老师要求或通用标准，运行中快照也
不保证资源一直稳定。本轮不因结果改变冻结门槛或事后筛除样本。
