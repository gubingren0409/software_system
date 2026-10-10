# 7405fcc3 首种子恢复：P3_RESOURCE_BLOCKED

## 本轮范围与身份（2026-10-10 16:13起）

审计/交付基点为 `b19e6cde1004c00d641f4459d1530c89ed56a383`，初始工作区干净，
分支 `project01`，目录 `E:\software_system\project01`。本轮获准一次新的有限 recovery，
全部条件通过后才执行首种子 random/greedy 各12个唯一配置及去重前缀复测。

- 实际运行内容：`7405fcc37074ab815294ba401d5cf5e8280f3d5f`。
- 既有 session：`3768a29ade69408da4c5d0c4404ba44e`，没有重新创建。
- 参数来源：[corrected_session_plan.json](../evidence/p3_resource_policy/20261010-143415/corrected_session_plan.json)。
- 归档：`/var/tmp/matrix-autotuner-p3-policy-content-7405fcc37074ab815294ba401d5cf5e8280f3d5f`。
- campaign：[campaign-7405fcc3](../evidence/p3_resource_policy/20261010-143415/campaign-7405fcc3/)。
- 本轮[执行计划与命令](../evidence/p3_resource_policy/20261010-161312-30f9a2a1-first-seed-7405fcc3/execution_plan.json)、
  [工作区实际字节/Git身份](../evidence/p3_resource_policy/20261010-161312-30f9a2a1-first-seed-7405fcc3/worktree_source_identity.json)。

50个实际归档文件的SHA-256全部匹配冻结身份；工作区运行文件与内容提交一致，
Git文本身份和实际字节/换行身份分开记录，教师C仍严格字节一致。本轮没有修改正式
Python/C/配置/测试，也没有改变协议、计时源或搜索；复用既有干净验证，不重跑历史测试或Grid。
仅新增批次专用编排/只读后处理，源码与执行哈希独立保存，不冒充7405fcc3的一部分。

## 实际 recovery 与拒绝原因

新目录：[20261010-161312-30f9a2a1-recovery-7405fcc3](../evidence/p3_resource_policy/20261010-161312-30f9a2a1-recovery-7405fcc3/)。
先保存policy/manifest再采集。入口真实退出 **2**，用时60.0090101秒；
内含Recovery门禁34.4752770秒。没有第二次调用，没有进入A/B时钟探针。

版本 `2026-10-10-cpu-admission-v1`，规范化策略SHA-256
`e191aee4348fa5501bb923dbf1be35741a188c738ebf6fdb4863bc91b0be5671`。
独立按全部原始读数复算，与保存判定完全相同：

| 项目 | 实际读数 | 判定 |
|---|---|---|
| CPU五次 | 17、5、13、27、11%；均值14.6%、最大27% | Recovery仅警告，不拒绝 |
| Windows可用内存五次 | 851079168、864403456、849502208、798076928、775036928 bytes | 最低0.722GiB，低于2GiB，REJECT |
| WSL可用内存 | 6208774144 bytes（5.782GiB） | PASS |
| WSL根盘空闲 | 223673192448 bytes（208.312GiB） | PASS |
| WSL swap | 2GiB总量/2GiB空闲 | 使用0；不能据此推断宿主无内存压力 |

原始[资源输出](../evidence/p3_resource_policy/20261010-161312-30f9a2a1-recovery-7405fcc3/resources.stdout.txt)
与[操作/PID/退出码/时间/流哈希](../evidence/p3_resource_policy/20261010-161312-30f9a2a1-recovery-7405fcc3/resources.operation.json)保留。
具体拒绝原因只有 `host_memory`，不是CPU、NTP或已执行的时钟检查失败。
16:15原始宿主读数还记录分页最高84 pages/s、page reads最高34/s，不能删掉这些压力证据。

16:18:47收尾的[只读内存/进程快照](../evidence/p3_resource_policy/20261010-161312-30f9a2a1-first-seed-7405fcc3/host_memory_explanation_corrected.stdout.txt)
另显示OS可用内存8340865024 bytes（7.768GiB）。它与门禁不同时、采集API不同，
只说明后续快照不同，原因未知；不是五次新门禁，不能替换旧REJECT或证明Formal通过。
未结束用户进程、回收系统缓存、修改WSL配额/系统设置或执行resync。
本轮只读NTP输出仍Leap=3/未同步，按协议仅保存元数据，不作为本次拒绝原因。

## 独立验收与保护

使用已有审计入口对**本轮新目录**复算，未传 `--grid`：

```powershell
python -B -X utf8 evidence/p3_resource_policy/20261010-161312-30f9a2a1-first-seed-7405fcc3/execute.py audit-recover
```

[独立验收](../evidence/p3_resource_policy/20261010-161312-30f9a2a1-first-seed-7405fcc3/independent_recover.json)
真实退出1，不仅凭退出码判断启动。结果：

| evidence_integrity_pass | execution_complete | timing_checks_pass | comparison_ready |
|---|---|---|---|
| false | false | false | false |

`recovery_eligible=false`。现有审计器的完整性要求包含两窗口原始操作；门禁拒绝后
两个窗口均**未执行**，因此第一项false，不是源码/现有输出哈希损坏。
已采集操作stdout/stderr哈希核验通过，冻结身份50/50通过；A/B区间0、宿主同调用
时钟检查未执行、Formal门禁未执行、resume未启动。没有把历史通过证明移用于本批。

新campaign仍 `initialized`：完整配置0/24、轨迹0/2、目标执行0、部分/放弃组0、
候选复测0，六行预算比较尚未产生，CV/MAD也没有可计算的新样本。检查点字节不变。
旧e308bfb的3配置/23执行（18条完整组、3条已放弃、2条待重启）及PAUSE_REQUEST
原样封存；e0353bf失败批次及旧Grid也未改。
10357个已跟踪历史/原件文件的实际字节摘要前后一致，范围与摘要见
[保护核验](../evidence/p3_resource_policy/20261010-161312-30f9a2a1-first-seed-7405fcc3/protection_after.json)。
独立检查没有正式campaign/目标进程，runner锁可获取。

本轮仅批次收尾字符串误带两个`+`，导致只读Windows/Python查询退出1、随后解析空stdout失败；
[原始辅助源码](../evidence/p3_resource_policy/20261010-161312-30f9a2a1-first-seed-7405fcc3/finalize_initial.py)
及实际失败流保留。移除两个字符，使用新输出文件名重做只读查询均退出0；
这不是第二次recovery或正式运行器修改。详见[辅助失败记录](../evidence/p3_resource_policy/20261010-161312-30f9a2a1-first-seed-7405fcc3/finalize_initial_failure.txt)。

## 成本与下一步

[交付结构化摘要](../evidence/p3_resource_policy/20261010-161312-30f9a2a1-first-seed-7405fcc3/delivery_summary.json)
列出所有已捕获命令、真实退出码和QPC范围。已记录辅助操作区间并集 **118.069225秒**，
包含Recovery入口60.009010秒、其内门禁34.475277秒及独立审计0.751948秒等，不能再相加。
该并集不含哈希/汇总自身、编辑、模型等待、推送等未计量开销，不冒充整个阶段端到端耗时。
新campaign活动累计仍0.080059216秒（既有初始化成本）、wait=0；本轮正式执行、终态
配置评估、放弃、复测、campaign门禁/等待增量均0。辅助前置门禁不记入campaign.wait。
旧campaign成本不变；[P3_COST_SCOPE](P3_COST_SCOPE.md)的包含/排除范围仍适用。

停止本轮，不扩展种子/算法，也不自动重采。本次20区间授权入口已调用一次；即使后来
单快照内存恢复，也不循环recovery到通过。下一轮外审确认后，宿主可用内存达到2GiB，
使用相同计划/归档/session与**新的唯一目录**重新授权有限验证；随后才可有条件resume。
具体参数仍取corrected_session_plan.json，不改检查点或PAUSE_REQUEST。
不可直接使用本批失败目录作为 `--recovery-directory`，也不可再次运行本批execute.py recover。

下一轮入口仍为Windows项目根目录的 `python -X utf8 scripts/start_p3_first_seed.py`，
先 `--mode recover`，必须显式传计划的content/auxiliary/archive/campaign/git-identity/session及新output；
独立复算eligible、来源和全部20区间通过后才 `--mode resume --recovery-directory <新通过目录>`。
运行内容和session可继续保留（前提是身份未变），无须重新初始化、复跑全套历史验收或Grid。
旧Grid仅作带时钟/资源限制的历史参考，不按比例校准，不宣称新策略下20配置全局最优。
