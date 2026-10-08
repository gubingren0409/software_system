# P1 外部审计交接

本文件是 P1 审计入口；固定提交 SHA 以推送后的终端交接消息为准。

## 范围与结论

- 基线：`174789158813b5446d2ab6ed754ae89662cc1c78`，分支 `project01`。
- 原件未变，SHA-256：`188d011109c4470e1f41829216e8677a5c2d8f2b7c8a44215652320dbdf6de15`。
- P0 宿主历史数据已按原始日志纠正，新旧快照明确分开。
- 小规模 160/160、故障注入 7/7、严格 CLI 6/6 通过预期。
- 中等规模四级链路和默认 `n=4096` 四级有限试跑均成功；代表配置五次重复成功。
- 没有执行完整 Grid 或搜索，不宣称最优配置。默认规模试跑时功能门禁通过，但
  4 GiB 宿主正式稳定性门禁未通过，因此数据不能作为后续正式计分基线。

## 建议审计顺序

1. `docs/P1_FOUNDATION.md`：完整事实、协议、成本和限制。
2. `code/working/` 与 `autotuner/core.py`：工作副本和三个统一接口。
3. `evidence/p1/correctness/summary.json`、`faults.json`、`strict_cli.json`。
4. `evidence/p1/pilots/summary.json` 与 `reference_manifest.json`。
5. `configs/measurement_protocol.json` 与 `configs/search_protocol.json`。
6. `evidence/p1/tests/unit_tests.txt`、`sanitizers.txt` 和 `p1_verification.txt`。
7. `evidence/p1/remote_verification.txt`：内容提交的推送与 fetch 一致性记录。

原始逐次运行记录位于 `small_cases.jsonl`、`medium_runs.jsonl` 与 `runs.jsonl`；每项
包含命令、stdout、stderr、退出码、计算/进程时间、资源和来源哈希。128 MiB reference
与编译二进制只在 WSL `/var/tmp/matrix-autotuner-p1-10245102457/`，未提交。

## 重点裁决

- 有限性检查、错误分类和严格 JSON 是否足以关闭 P0 的 NaN/任意非零退出缺陷。
- 独立 `double i-k-j` 全量 reference 加 16 点 `long double` 复核是否满足正式规模要求。
- 1 预热 + 5 测量、中位数计分以及 O0/O1/O2/O3 的 `1271/244/151/243 s` 超时。
- 冻结的随机与随机重启贪心规则、公平预算和约 37 小时全套代表性成本是否可接受。
