# Matrix Multiplication Autotuner (P1)

《软件系统优化》实践项目 P1。**P2 历史Grid已保存；P3首种子正式比较尚未完成（P3_CLOCK_BLOCKED）。**

当前50cd24e后唯一原生C/宿主QPC参照诊断已完成30区间：默认A空闲10/10、B忙工作8/10，
syscall空闲及临时绑核空闲各5/5；RAW全部30匹配宿主。B1/B2（零起点）MONOTONIC
真实失配，通信不确定性均≤1.2861ms，不启用新时钟准入，不启动recovery/4096/搜索。
诊断执行内容`7950a8a533f5c60dd8fb7a0d26cb90a3e3d2b32d`；正式d6811cad及空session
2c270825458a4857a5ac9df5aadf597b不变。11项相关回归/干净归档、20配置、二进制复编
身份和10623项历史保护通过，但不代表时钟或正式比较通过。
[方案、全部读数、决定及只读复算入口](docs/P3_CLOCK_REFERENCE.md)、
[本轮独立复算](evidence/p3_clock_reference/20261010-190645-1375f246/independent_diagnostic.json)、
[交付摘要](evidence/p3_clock_reference/20261010-190645-1375f246/delivery_summary.json)。

以下为历史ac33d9d后用户授权内存准入v2，策略本轮原样保留：宿主可用与提交余量各512MiB，宿主低于2GiB警告，
Recovery WSL至少256MiB，Formal仍2GiB；CPU与测量/搜索不变。针对性验证、实际采集及
新内容/新session有限恢复见[P3_MEMORY_POLICY](docs/P3_MEMORY_POLICY.md)。不迁入旧分数或重跑Grid。

本轮实际运行内容为 `d6811cadda8ecd7b46225ebe65c51831278694a0`，新空session
`2c270825458a4857a5ac9df5aadf597b`。干净归档28项相关单测（1跳过）、CLI/20配置及
n17/O2/s8 fresh逐元素校验通过。唯一recovery资源PASS，但MONOTONIC/RAW **6/20区间失败**，
两个宿主同调用检查通过；来源完整性通过，不具备恢复资格。**Formal未执行、4096执行0、
配置0/24、完整轨迹0/2、候选复测0**。没有第二次recovery，旧成绩不迁移或校准。
[实际独立验收](evidence/p3_memory_policy/20261010-174802-11f7775c/independent_recovery.json)、
[交付摘要](evidence/p3_memory_policy/20261010-174802-11f7775c/delivery_summary.json)。

历史（2026-10-10 16:19，b19e6cd后）：运行内容7405fcc3、既有session3768a29a不变。
唯一一次新recovery调用退出2，宿主内存最低0.722GiB<2GiB，CPU14.6%/27%仅警告。
50项身份通过；时钟区间、Formal门禁、矩阵执行均未开始，新配置0/24、轨迹0/2、复测0。
四项独立验收均false（完整性字段因未生成两个时钟窗口，不是源码哈希损坏）。
停止而不循环重采；历史数据、检查点及暂停标记不变。详见
[当前恢复结论/成本/续跑条件](docs/P3_FIRST_SEED_7405FCC3.md)及
[本批独立验收](evidence/p3_resource_policy/20261010-161312-30f9a2a1-first-seed-7405fcc3/independent_recover.json)。

## 历史：资源策略迁移和e0353bf失败批次

2026-10-10：用户明确授权新 CPU 准入策略：Recovery 超过旧 CPU 阈值只警告，Formal
均值≤30%/单次≤60%；内存/磁盘不放宽，配置启动前门禁等待总预算120秒。
新内容、新归档、新 session/campaign，不拼接旧成绩；C、搜索、输入、容差、计时和评分不变。
策略、迁移、唯一一次20区间验证计划及当前结果见 [P3_RESOURCE_POLICY](docs/P3_RESOURCE_POLICY.md)。
旧 Grid/P3 与以下管理员核验均保留为历史，不能用新门槛追认历史 REJECT。

本轮唯一 recovery 的20区间、两个宿主检查以及随后批前/批后6区间全部通过，来源50/50
匹配，实际新Formal门禁也通过（CPU均值11%）。但e0353bf的campaign内部UNC资源采集
异常退出1，**4096执行0、搜索配置0、轨迹0/2、复测0**，不是CPU或时钟再次拒绝。
已定位并修复进程启动及非UTF8错误处理；最终运行内容为
`7405fcc37074ab815294ba401d5cf5e8280f3d5f`，
[双干净归档验证](evidence/p3_resource_policy/20261010-143415/clean-7405fcc3/summary.json)通过。
修复后的空session `3768a29ade69408da4c5d0c4404ba44e` 不继承旧恢复证明；本轮不再采第二次
recovery。下一轮须外部复核及新的有限验证授权，命令见上述策略文档和
[新session计划](evidence/p3_resource_policy/20261010-143415/corrected_session_plan.json)。

历史 2026-10-10 13:56 管理员处理核验：已保留13:52管理员原始日志，resync有执行
输出，但明确报告“没有可用的时间数据”，操作后及本轮查询仍Leap=3/层次0。
日志中的退出码0及更新的“上次成功同步”字段不构成同步成功证据。内存已恢复：
宿主最低2.537GiB、WSL可用5.789GiB；Formal门禁因CPU平均14.2%>10%拒绝。
因此本轮recovery/resume/新增矩阵执行均0，仍3/24配置、23条原始执行、0/2完整轨迹。
32项冻结SHA及fa59701辅助七文件匹配；只复用既有验证，不重跑28项回归或时钟探针。
[管理员核验/阻塞原因](docs/P3_CLOCK_REPAIR.md)、
[本批独立验收](evidence/p3_clock_repair/20261010-135557/independent_acceptance.json)。
下述12:12集中诊断及10-09记录均保留为历史，不校准旧Grid/P3。

20/20 配置有效，120 次正式执行与 6 次独立复测均通过全矩阵检查。
保留的P2 Grid session测得最低中位数为 **O1/s=128：53.444627760 s**；独立复测为
**54.779446389 s**（+2.50%）。P3 将按五种子、4/8/12预算比较随机与贪心；
当前尚无 P3 完整五种子比较结论。P2 未被标记为外部审计通过。
时钟未独立校准及运行中背景资源扰动限制见
[`docs/P2_TIMING_NOTE.md`](docs/P2_TIMING_NOTE.md) 和 [`report.md`](report.md)。
0023ceed审计修订的独立诊断判据、双归档主控迁移与下一阶段条件见
[`docs/P3_TIMING_AUDIT.md`](docs/P3_TIMING_AUDIT.md)；预算前缀的明确排除项及
失败门禁暂停—成功恢复回归见[`docs/P3_COST_SCOPE.md`](docs/P3_COST_SCOPE.md)。
历史P3曾沿用原e308bfb归档、固定身份和campaign；封存3个完整配置、23条原始执行，
其中旧O0/s8部分组3条已放弃，新部分组2条待重启，均不计配置分数。14:22按暂停
请求安全停止；16:38用户要求继续，批前检查及限定复核发现时钟异常，没有恢复目标。
当时资源门禁PASS不解除时钟阻塞。只限seed=20261008两条轨迹，不扩展五种子。
当前状态、成本及续跑条件见[首种子状态](docs/P3_FIRST_SEED_STATUS.md)。
fdeed77后统一辅助检查和验收，唯一次20区间复核中MONO/RAW全部失败，REALTIME/RAW
另有2项失败；本次宿主内存门禁也拒绝。未启动4096或恢复campaign，状态仍为
**P3_CLOCK_BLOCKED**。[辅助契约v2.1/路径修复](docs/P3_CLOCK_CONTRACT.md)、
[完整复核分析](evidence/p3_clock_contract/20261009-180810-0491a4ec/clock_review_analysis.json)。
最终辅助内容`fa597017c2317772a0f7f34faa75194ffecec8f2`双干净归档74项全套测试
（WSL跳过1项）及Windows旧7/新21项回归通过；
[最终验证](evidence/p3_clock_contract/20261009-180810-0491a4ec/clean-fa59701/summary.json)。
测试通过不代表算法比较完成，也不授权继续尝试探针。原始20区间使用0c6ee7e辅助内容，
后续仅修辅助路径/验收，不替换该来源身份。
此前交付代码从内容`f64d41c1eab21c72e541f91ab7e2dbecf4adfe2b`独立归档验证：
CLI、20唯一配置、53项单测、历史证据核验及Git/实际文件身份检查通过，
[全部命令及结果](evidence/p3/first-seed-clean-f64d41c/summary.json)。不是正式比较PASS。
此前独立审计六组/36次n4096执行全部通过；两轮观察排名O1→O3→O2，但相邻差距
不足2%且有资源警告，**不满足先验稳定排名判据**。该次时钟对照通过不校准旧数据。
诊断主循环39分29秒，正式P3比较仍未完成，下一阶段命令和裁决条件见上述审计说明。

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

- [`docs/P3_PROTOCOL.md`](docs/P3_PROTOCOL.md)：P3 批次、私有观测、复测和比较指标。
- [`docs/P3_AUDIT_HANDOFF.md`](docs/P3_AUDIT_HANDOFF.md)：P3 执行状态与审计入口。
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

## P3 批次入口

`python3 -m autotuner campaign --help` 展示 P3 正式/诊断运行参数。正式运行必须先
提交内容并通过 `scripts/prepare_p2_content.ps1 -ContentSha <完整内容SHA>` 导出，
沿用导出器的历史 `p2-content-<SHA>` 名称但实际内容绑定 P3 SHA。在该干净归档目录
中运行，Git 身份文件是导出器生成的 `build/p2/git_identity.json`：

```bash
PYTHONDONTWRITEBYTECODE=1 env -u PYTHONPATH python3 scripts/run_p3_clean_validation.py \
  --content-sha <完整内容SHA> --git-identity <导出器身份JSON绝对路径> \
  --output <新的小规模验收证据目录>
PYTHONDONTWRITEBYTECODE=1 env -u PYTHONPATH python3 -m autotuner campaign \
  --content-sha <相同内容SHA> --git-identity <相同身份JSON路径> \
  --campaign-directory <P3正式证据绝对目录> --trajectory-limit 2
```

默认先做首种子的两条完整轨迹；将 limit 增大至 10 并加 `--resume` 可继续冻结顺序。
当前这些占位命令是接口说明，不是已经执行的正式命令；实际内容 SHA、参数和输出
由验收/实验日志记录。安全暂停和完整恢复规则见 P3_PROTOCOL。

P3实际内容提交为 `e308bfb873e6811c50ad685a979af345302fda8d`。40项单测、n17 fresh、
n130十条诊断轨迹（834次目标新执行）和部分组暂停重测通过，
见[干净验收摘要](evidence/p3/validation-e308bfb/summary.json)。正式批次使用独立固定
Git身份，不依赖将来会被导出器覆盖的通用身份文件；当前范围与实际续跑命令见
[P3审计入口](docs/P3_AUDIT_HANDOFF.md)。所有P0/P1/P2历史证据保持原身份。

2026-10-09 02:24自动暂停时已保存2/24首批配置（完整计划2/120次轨迹内配置评估）、
12条完整目标执行；当前没有仍在运行的P3目标。10:12只读复查宿主最低可用内存
454094848字节（约433MiB），仍未达到2GiB门槛，WSL/CPU/磁盘条件通过。
先恢复宿主可用内存，再使用审计入口中固定身份的`--resume`命令；不要重建session或
用单次缓存拼重复。P3尚非完整交付，不能据此比较算法或五种子稳定性。

10:40正式门禁恢复PASS：宿主最低可用约5.70GiB、WSL约3.90GiB、CPU平均4.4%/
最大16%、AC电源在线。用户要求继续后，使用原e308bfb归档、固定身份和同一session
执行`--trajectory-limit 2 --resume`；两完整组核验后保留，10:42:55第三配置O3/s16
已开始预热。见[恢复证据](evidence/p3/resume-20261009-104020/restoration.json)。
上述02:24/10:12段落是历史暂停快照，不冒充本次状态；完整P3比较尚未完成。

此前审计基点`0023ceed`，在已推送的55b776b历史上继续。P3安全暂停后保留3个完整
配置及O0/s8的3条部分样本（合计21次执行）。[本轮诊断判据与入口](docs/P3_TIMING_AUDIT.md)、
[前缀成本范围](docs/P3_COST_SCOPE.md)。这是历史暂停状态；本次用户以e46b96c授权
沿用协议恢复，显式`--resume`已留存并清除原PAUSE_REQUEST。两轮s128复测仍是独立
诊断，不是Grid扩展或搜索观测。
