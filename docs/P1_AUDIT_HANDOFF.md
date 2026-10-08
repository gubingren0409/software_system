# P1-R1 外部审计交接

本文件是 P1-R1 审计入口；最终固定提交 SHA 以推送后的终端交接消息为准。R1 基线为
`bd57fd5cae021b6f503b96646488e0ce88ad7792`，干净验证的内容提交为
`bd9b7d264c42f7c65cd22b16a64a4a0f9c119c5f`。

## 范围与结论

- 分支：`project01`。
- 原件未变，SHA-256：`188d011109c4470e1f41829216e8677a5c2d8f2b7c8a44215652320dbdf6de15`。
- 过宽的 `core.*` 曾使 `autotuner/core.py` 未提交；恢复文件的修订前本地 SHA-256
  为 `1675f682e45103b5fb4d1be2bb8fe08fb6c8f8ba7f206c02a04f4c3549c84ccd`。
  R1 内容提交归档中的最终文件 SHA-256 为
  `4e5a7a884a0a5b1c09055f4499b53e8aeb67d4c3ec4bbbf2f211f6c1aa760f12`。
- `git ls-files` 与内容提交的 `git ls-tree` 均包含 `autotuner/core.py`。
- `reference_generator.c` 过滤越界采样坐标；n=1/2 在 ASan+UBSan 下通过，n=4096
  仍为原来的 16 个采样点。候选和 reference 只接受非空十进制种子数字串。
- P0 宿主历史数据已按原始日志纠正，新旧快照明确分开。
- 从无 `.git`、无 `__pycache__`、清除 `PYTHONPATH` 的归档运行：18/18 单元测试、
  小规模 160/160、故障注入 7/7、严格 CLI 6/6 均通过。
- `n=17/O2/s=8` 使用独立空缓存和证据目录，结果为 `fresh_measurement`、正确性通过。
- 临时副本删除 `core.py` 后验证入口按预期非零退出。
- 中等规模四级链路和默认 `n=4096` 四级有限试跑均成功；代表配置五次重复成功。
- 上述 pilot 对应 R1 前实现；R1 没有重跑默认规模。没有执行完整 Grid 或搜索，
  不宣称最优配置。

## 建议审计顺序

1. `evidence/p1_revision1/summary.json`：R1 干净验收总览与内容提交 SHA。
2. `evidence/p1_revision1/commands/`：实际命令、stdout、stderr、退出码和墙钟时间。
3. `evidence/p1_revision1/source_hashes.json`：Python、C、配置和验证文件哈希。
4. `evidence/p1_revision1/boundary_regressions.json`：种子与 n=1/2/4096 采样回归。
5. `evidence/p1_revision1/correctness/`：R1 后 160 次小规模与 7 次故障注入原始记录。
6. `docs/P1_FOUNDATION.md`、`code/working/` 与 `autotuner/core.py`。
7. `configs/measurement_protocol.json` 与 schema version 2 的 `search_protocol.json`。
8. `evidence/p1/pilots/`：只读保留的 R1 前历史 pilot。

原始逐次运行记录位于 `small_cases.jsonl`、`medium_runs.jsonl` 与 `runs.jsonl`；每项
包含命令、stdout、stderr、退出码、计算/进程时间、资源和来源哈希。128 MiB reference
与编译二进制只在 WSL `/var/tmp/matrix-autotuner-p1-10245102457/`，未提交。

## 重点裁决

- 干净归档验证是否充分关闭“工作树有文件但提交缺失”的问题。
- 独立 `double i-k-j` 全量 reference 加 16 点 `long double` 复核是否满足正式规模要求。
- 1 预热 + 5 测量、中位数计分以及 O0/O1/O2/O3 的 `1271/244/151/243 s` 超时。
- schema version 2 的贪心邻域（单参数改到任意其他值、每点 7 邻居）与 Grid 前缀
  顺序偏置说明是否可接受。
