# P2 审计交接

## 范围与版本

基线 `7e8ab2e0ccb28cff25f9d3146c6a38d284bfd4de`。正式执行及启动前干净回归使用内容提交
`0d3dd5242c728d8001dd02a4e332185459d04721`，而非后续的证据/报告提交。
状态：20/20完整配置有效、120次正式执行全部通过；独立一预热五测量也已完成。
代码/协议未在会话中改变。最终交付归档的小规模复验另存`validation-delivery/`，
其内容SHA与正式内容SHA分开记录。固定最终交接SHA在推送并远程核验后的终端回复给出。

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
- [`validation-delivery/summary.json`](../evidence/p2/validation-delivery/summary.json)：内容提交
  `c2a964162915b8cf0019df4e73bcd7cd634d1902`从独立归档复验PASS：6个CLI/测试命令
  退出0，31项单测、160正确性、7故障、6参数拒绝、n17 fresh及n130三策略20/8/8
  均通过。独立空缓存，不依赖原工作目录未跟踪文件、旧pycache或PYTHONPATH。
  20个Python源码AST通过，归档内已提交的完整正式证据审计也通过；不重跑n4096。
  初次验证因归档导出尚未结束而找不到目录，未启动任何目标；等待导出退出0后重新
  执行通过。原失败保留startup_diagnostic.json，不伪造整体第一次即PASS。

## 正式实验状态与原始证据

正式数据仅在 [`../evidence/p2/grid-session-0d3dd52/`](../evidence/p2/grid-session-0d3dd52/)。
`checkpoint.json`最终status=complete；残留paused_at仅为历史暂停时间，不是当前状态。
不把历史pilot或诊断拼进该session。

- `session.json` / `protocol.json` / `checkpoint.json`：内容、协议、输入、源码、编译器、
  二进制与 reference 身份；原始 Git blob、Git 内容 SHA-256、实际执行 SHA-256 和
  LF/CRLF 数量分开记录。老师原件始终按原字节保存。
- `samples.jsonl`、`configurations/`、`runs/`：全部执行、唯一 ID、命令、原始输出、
  退出码、/usr/bin/time 峰值 RSS、计算/验证/墙钟和连续资源样本。
- `manifests/`、`references/`：实际构建和完整 reference 生成 JSON。大矩阵与二进制
  留在 `/var/tmp/matrix-autotuner-p2-10245102457/cache`，不提交。
- `gates/`：每次正式资源检查的完整命令、stdout、stderr、退出码和解析字段。
- `grid_summary.csv`：20行有效配置，全部100个计分样本及20个预热可追溯。
- `evidence_audit.json`：逐条原始记录与检查点交叉核验、成本与资源统计。
- `independent_retest.json`：O1/s128另组预热与五测量，Grid表保持不变。
- [`../evidence/p2/postprocessing/`](../evidence/p2/postprocessing/)：工具版本、实际命令与
  stdout/stderr/退出码、辅助源码及图片哈希、运行后重查执行源码/编译器/四级二进制/
  reference数据SHA-256、Grid前缀及后续成本估计；全部核对通过。
- [`../assets/p2_heatmap.png`](../assets/p2_heatmap.png) 与
  [`../assets/p2_variation.png`](../assets/p2_variation.png)：图表均已实际生成并查看。

`evidence/p2/grid-main/` 是旧内容提交的废弃 session。它生成了 reference 并启动过
O0/s8，但运行器中断后候选写输出时收到 SIGPIPE；仅有 /usr/bin/time 记录，没有
可计分的完整结果。该进程于15:16:31结束，当前 session 首次执行于15:26:17开始，
两者没有重叠；旧数据不并入当前 Grid。`evidence/p2/validation/` 是修复前内容版本的干净回归；
启动前最终归档验证在`validation-final/`。P0、P1、P1-R1证据不覆盖、不追认为正式数据。

## 结果与成本

测得最低中位数：O1/s=128，Grid 53.444627760 s；独立复测54.779446389 s，
较Grid高2.4976%。两组CV为1.9264%/1.4518%；20配置CV为0.1441%--4.7865%。
完整表、原始五次样本和限制见[`../report.md`](../report.md)，不是稳定环境全局最优声明。

活动会话记录23908.150 s（6 h 38 min 28 s），其中门禁/等待2153.500 s（35 min 54 s）；
完整Grid配置评估20088.175 s，四级候选构建2.988 s、reference setup35.092 s，
独立复测配置评估338.596 s。以上为存在包含关系的MONOTONIC成本项，不可全相加。
UTC起止时间戳跨度31719.227 s，含关机暂停且UTC曾调整，不与单调时钟相减作精确成本。

完整性审计`--require-complete`通过：120条正式Grid、6条复测、3条放弃完整记录，
另1条无完整结果的中断执行。129条完整记录均fresh且force=true、唯一ID、退出0、
全矩阵零错配；3条放弃成本1273.673 s不计分，中断成本只有最后观测325 s下界。
不能把这个下界伪造为最终耗时或退出码。原始stdout/stderr/time-v与JSONL逐一一致。

## 资源与续跑

资源门槛及理由见 [`P2_PROTOCOL.md`](P2_PROTOCOL.md)。用户提供高内存占用截图后，
另采集 [`../evidence/p2/environment/memory_followup_20261008.json`](../evidence/p2/environment/memory_followup_20261008.json)。
WSL内部可用内存与Windows可用物理内存不能互相替代。运行中718个宿主样本有197个
低于2GiB、41个CPU超过20%，宿主最低约99.5MiB、最高CPU62%。候选峰值RSS
385.60MiB且逐进程major fault全部0，WSL无swap，仍不证明宿主或CPU资源一直稳定。
23:49只读快照[`recurrent_memory_pressure_20261008.json`](../evidence/p2/environment/recurrent_memory_pressure_20261008.json)
包含游戏进程约2.76GiB工作集；用户表示自行关闭高负载应用并继续。未更改WSL配额、
频率或内核设置，也未终止用户程序。原暂停及续跑命令见[`../README.md`](../README.md)。

辅助inspect_p2曾因新增选项列表缺闭括号而SyntaxError退出1，命令未开始采集。
错误、源码哈希及补括号后实际12命令成功的记录均保留；修复前后字节快照见
`environment/collector_sources/`。该采集器不在正式归档的运行依赖中，未改变session。

## 待后续完成/裁决

本轮只运行正式 Grid；正式随机/贪心的预算4/8/12和五种子实验留给 P3。
没有剩余Grid配置、候选复测或图表工作。尚未完成的是正式三算法比较、机制实证和
最终课程作业验收，不代表外部审计已通过。审计重点：

1. 是否接受当前时钟精度及运行中背景扰动限制，或要求更稳定环境另建session复测。
2. 独立复测+2.50%大于相邻优化档的原表差距，是否需要增加候选之间的独立复测；
   不回写当前Grid、不事后改容差或删慢样本。
3. P3五种子×12唯一配置每算法约16.74h（不含等待/失败/复测），建议先一种子核查
   成本再分批完成；保持4/8前缀、七邻居、自身观测限制及同一测量协议。

时钟域核查见[`P2_TIMING_NOTE.md`](P2_TIMING_NOTE.md)：确认REALTIME调整及
MONOTONIC/RAW差异，跨宿主精度尚未独立校准。继续按冻结计时源保留原样分数，
不事后换算；证据审计PASS仅说明原始记录、计分契约与完整性一致，不证明时钟或
背景资源完全稳定。该限制是否需另建更稳定环境session复测，交外部审计者裁决。

历史暂停：用户因电量不足暂停后，于19:08要求续跑。暂停提交为
`76d37b50d47a27fd798f958f8303fbf2faaa87a3`；当时保存了一行完整结果和三条部分样本。
恢复时确认电源Online、正在充电；整组重测后已完整完成。中断执行的精确成本无法恢复，
`interruption_record.json`保留最后观测及成本下界。
