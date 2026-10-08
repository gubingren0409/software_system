# P2 审计交接

## 范围与版本

基线 `7e8ab2e0ccb28cff25f9d3146c6a38d284bfd4de`。正式执行与最终干净回归使用内容提交
`0d3dd5242c728d8001dd02a4e332185459d04721`，而非后续的证据/报告提交。
固定最终交接 SHA 在推送并远程核验后的终端回复给出。

测量协议 schema 2 的规范 JSON SHA-256 为
`2b1a75e9c5f88b80d83a47be4e34c2c5577d82d1468f37fd976e0d6d6ce5b828`，
文件本身 SHA-256 为
`c02cbf718cda049dc621c807df9b68acc539a8e06aa5918f7cb0376456515ab4`。
两者计算方式不同；session 用前者比较协议身份。

## 实现与回归

- [`../autotuner/core.py`](../autotuner/core.py)：只有退出 0 且严格 JSON、正确性、请求
  身份及容差全部通过才能计分；64/65 核对错误 schema/status，不接受成功 JSON。
- [`../autotuner/measurement.py`](../autotuner/measurement.py)：统一配置评估、预热和
  五个强制新测量，保存全部样本、均值、标准差、CV、MAD 与墙钟；不筛选成功子集。
- [`../autotuner/search.py`](../autotuner/search.py)：ask/tell 的三种可替换策略，每个
  实例仅有自身观测；唯一预算、随机种子、七邻居贪心遵循搜索 schema 2。
- [`../autotuner/session.py`](../autotuner/session.py)：正式 JSON 门禁、固定顺序全 Grid、
  身份检查、完整样本恢复、中断配置重测、独立复测。
- [`../tests/test_runner.py`](../tests/test_runner.py) 与
  [`../tests/test_search_measurement.py`](../tests/test_search_measurement.py)：退出码冲突、
  身份错配、checked_entries=0、放宽/非法容差、崩溃/超时/编译错误、配置预算与
  重复测量、检查点篡改/性能缓存拒绝和 setup 前资源暂停续跑回归。
- [`../evidence/p2/validation-final/commands.json`](../evidence/p2/validation-final/commands.json)：
  干净归档的帮助、20 配置 CLI、31 项单元测试、verify_p1、实际 n=17/O2/s=8
  fresh evaluation 和全部小规模正确性，逐命令 stdout/stderr/退出码。
- [`../evidence/p2/validation-final/diagnostic_trajectories.json`](../evidence/p2/validation-final/diagnostic_trajectories.json)：
  n=130 实际 Grid20、随机8、贪心8，均通过统一接口的每配置六次执行；仅为诊断。

## 正式实验状态与原始证据

正式数据仅在 [`../evidence/p2/grid-session-0d3dd52/`](../evidence/p2/grid-session-0d3dd52/)。
完成数量及暂停状态以 `checkpoint.json` 为准，不把历史 pilot 或诊断拼进该 session。

- `session.json` / `protocol.json` / `checkpoint.json`：内容、协议、输入、源码、编译器、
  二进制与 reference 身份；原始 Git blob、Git 内容 SHA-256、实际执行 SHA-256 和
  LF/CRLF 数量分开记录。老师原件始终按原字节保存。
- `samples.jsonl`、`configurations/`、`runs/`：全部执行、唯一 ID、命令、原始输出、
  退出码、/usr/bin/time 峰值 RSS、计算/验证/墙钟和连续资源样本。
- `manifests/`、`references/`：实际构建和完整 reference 生成 JSON。大矩阵与二进制
  留在 `/var/tmp/matrix-autotuner-p2-10245102457/cache`，不提交。
- `gates/`：每次正式资源检查的完整命令、stdout、stderr、退出码和解析字段。
- `grid_summary.csv`：已完成配置行；完成全部 20 行后才能认为是完整 Grid 表。
- `evidence_audit.json`：逐条原始记录与检查点交叉核验、成本与资源统计。

`evidence/p2/grid-main/` 是旧内容提交的废弃 session。它生成了 reference 并启动过
O0/s8，但运行器中断后候选写输出时收到 SIGPIPE；仅有 /usr/bin/time 记录，没有
可计分的完整结果。该进程于15:16:31结束，当前 session 首次执行于15:26:17开始，
两者没有重叠；旧数据不并入当前 Grid。`evidence/p2/validation/` 是修复前内容版本的干净回归；
最终归档验证在 `validation-final/`。P0、P1、P1-R1 证据不覆盖、不追认为正式数据。

## 资源与续跑

资源门槛及理由见 [`P2_PROTOCOL.md`](P2_PROTOCOL.md)。用户提供高内存占用截图后，
另采集 [`../evidence/p2/environment/memory_followup_20261008.json`](../evidence/p2/environment/memory_followup_20261008.json)。
WSL 内部可用内存与 Windows 可用物理内存不能互相替代。未更改 WSL 配额、频率或
内核设置，也未终止其他用户程序。续跑完整命令见 [`../README.md`](../README.md)。

## 待后续完成/裁决

本轮只运行正式 Grid；正式随机/贪心的预算4/8/12和五种子实验留给 P3。
若资源导致 Grid 尚未完成，剩余配置、独立复测及完整图表仍是必需工作，不宣称
P2_READY。运行期间宿主内存压力、CPU 温度/boost/计数器未知等限制必须在报告保留，
不能把无 swap 的 WSL 样本解读为宿主无压力。

时钟域核查见[`P2_TIMING_NOTE.md`](P2_TIMING_NOTE.md)：确认REALTIME调整及
MONOTONIC/RAW差异，跨宿主精度尚未独立校准。继续按冻结计时源保留原样分数，
不事后换算；证据审计PASS仅说明原始记录、计分契约与完整性一致，不证明时钟或
背景资源完全稳定。该限制是否需另建更稳定环境session复测，交外部审计者裁决。

用户因电量不足暂停后，于19:08要求续跑。暂停提交为
`76d37b50d47a27fd798f958f8303fbf2faaa87a3`；当前session的一行完整结果和三条部分
样本均已保存。恢复时确认电源Online、正在充电。中断执行的精确成本无法恢复，
另以 `interruption_record.json` 保留最后一次进程观测及成本下界。
