# 2026-10-15：用户授权一次重试，仍在组前资源门禁停止

状态：**P3_RAW_VALIDATION_RESOURCE_BLOCKED**。这不是补齐三配置或P3比较完成。
用户“重试一下吧”授权一次新的人工尝试，不授权循环准入、新3600秒预算或搜索。
原测量内容35a60b090b728d2ec3b6a8ea014beac69fe3766d/session9332ead2881a4c1e91b966e90a0d2057不变，
只准备补O3/s24一个组。旧s128/s64两组、12次执行、旧claim/失败/检查点/证书/分数均保留。

## 执行身份及预算

外层辅助内容`3eaeadd28245664f4ea27bd8e4f79082fcf0124e`，准确三文件归档
`C:/Users/28489/AppData/Local/Temp/raw-validation-retry-3eaeadd`。
所有科学运行模块从原35a60b0归档导入；矩阵、输入/reference、容差、RAW评分、20配置/搜索及资源v2未改。
原22fe97c助手及记录保留，新的schema raw-validation-user-retry-v1独立绑定它的授权、窗口、claim及SHA。
[采集前授权和所有保护哈希](continuation/authorization.json)、[前置计划](stage_plan.md)、
[外层规则](../../../docs/P3_RAW_VALIDATION_CONTINUATION.md)。旧claim不删除，新retry claim独占，不能重复调用购买额度。

原846.073676s＋上次200.0468689s＝1046.1205449s继续计费，只允许原剩余2553.8794551s。
本轮实际211.7102998s，累计1257.8308447s，账面余2342.1691553s，不自动再次运行。
当前QPC端点属于新的epoch，只各自先相减再加时长，不跨epoch相减，不退还旧失败成本。

## 实际门禁、时钟及停止

E盘62714880000B可用，至少1GiB及write/fsync/read-back通过；[原始写验证](continuation/evidence_volume_preflight.json)。
Formal预检通过：host最低1016856576B、commit余量28973170688B、WSL可用6315413504B、CPU均18.8%/峰31%。
host低2GiB只警告，原512MiB硬下限不改。随后一次默认libc/不绑核短1e9＋长1e10更新的RAW准入
2/2通过，10响应全部保留，无MONOTONIC辅助警告：[manifest](continuation/admission/manifest.json)、
[整数端点/原始通信](continuation/admission/messages.jsonl)、[独立复算](continuation/independent_continuation_admission.json)。
没有重采、筛选或校准，没有借旧证书冒充当前附件。

新s24资源attempt `06413e1e6af34cbf90ddf856126d8276`：

| 采集 | Windows最低可用/B | WSL可用/B | CPU均/峰% | 结果 |
| --- | ---: | ---: | ---: | --- |
| 0 | 247074816 | 4874485760 | 26.6 / 49 | REJECT，仅host_memory |
| 1 | 379310080 | 6249627648 | 12.4 / 18 | REJECT，仅host_memory |
| 2 | 341209088 | 6215036928 | 17 / 35 | REJECT，仅host_memory |
| 3 | unknown | unknown | unknown | timed_out=true，退出1，stdout空，不是PASS或第四个有效内存读数 |

完整前三个窗口的最小值低于512MiB，CPU符合30%/60%，commit/WSL容量不是这些快照的拒绝原因。
[原始四次操作/退出码](../20261014-182807-ac-validation/validation-9332ead2/group_checks/06413e1e6af34cbf90ddf856126d8276/resources/gate_outcome.json)。
本次外层至多119秒采集/等待，留1秒收尾；门禁实际119.5028273s，保持原120秒硬上限。
未改变冻结collector、manifest预算或严格审计。第四次超时无JSON，独立审计明确拒绝；
上次120.0005393s超额失败也仍保留，见[全部门禁独立复算](all_resource_gates_independent.json)。

资源拒绝后没有启动新组前/后探针、READY、矩阵或accept；控制器真实退出2、stderr空。
新防睡眠申请/同线程finally释放通过，未改电源/系统设置、结束用户应用、清缓存或主动重启WSL。
[停止后的只读宿主快照](operations/final_host_memory_and_processes.stdout.txt)可用2669293568B，
VALORANT WorkingSet1836716032B（约1.71GiB）、VmmemWSL998596608B。
这是不同窗口的占用证据，不证明游戏或WSL是唯一根因，也不能追认失败门禁通过。
[WSL完整meminfo/启动身份/无args进程快照](operations/final_wsl_state.stdout.txt)只读保存。

## 验收、成绩和成本

14项相关受控测试在工作树与准确辅助归档均通过，未重复整套历史验收或n17。
[真实命令、stdout/stderr、退出码及QPC](operations/)；假执行器测试不计为目标运行。
[独立验收](continuation/independent_continuation_audit.json)退出2（未完成），确认270个原session文件、
13,458个其他历史文件、原12条样本前缀/两组/旧Grid和空搜索session不变。

evidence_integrity_pass=true；formal_preflight_pass=true；group_formal_resource_pass=false；新RAW准入通过。
validation_complete/validation_timing_checks_pass=false，P3 execution_complete/timing_checks_pass/comparison_ready均false。
source/原始数据完整性不能替代失败的资源门禁；累计11个RAW区间通过不能证明未执行的s24。
目标仍12/18fresh（2预热+10测量），本次新增0；组2/3，矩阵部分/放弃样本0，search/前缀复测/reference生成0。
[逐样本严格契约](all_sample_contracts_independent.json)、[时钟复算](all_clock_checks_independent.json)、
[三配置旁列表](three_configuration_comparison.csv)：s128仍51.602724641s、s64仍52.784908609s，s24未执行。
旧Grid的待机样本/分数/连续性限制不变，不反馈给任何搜索。

[来源及行尾身份](source_identity.json)：实际原92文件、编译器/四候选/reference哈希；辅助Python字节与Git一致。
非执行Markdown归档CRLF与Git LF分别记录，规范化内容一致，不伪称字节一致，不修改原件。
最终只读文件/链接/源码/进程检查见final_checks.json。

[成本](costs.json)：三段活动846.073676＋200.0468689＋211.7102998＝1257.8308447s。
本段外层进程226.3787934s包含身份检查、活动及末尾记录；门禁累计414.1561236s、
探针125.3838414s、已接受组评估RAW650.83599454s和核心含预热633.229610487s都是嵌套项，不能全部相加。
原setup0.553232607s未覆盖；reference/search/前缀复测0。离线准备/人工等待/审计/Git单列，
不虚构完整人工总耗时，不从不同范围或时钟校准性能分数。

只读复核，不运行矩阵：

```powershell
python -B -X utf8 C:/Users/28489/AppData/Local/Temp/raw-validation-retry-3eaeadd/scripts/resume_raw_validation.py audit --authorization E:/software_system/project01/evidence/p3_raw_comparison/20261015-130000-user-retry/continuation/authorization.json
```

本轮停止，不再调用run。下一步先由用户释放游戏等高占用内存、复核资源稳定性，
再明确一次原剩余额度补齐的授权；仍只差s24六次，不新开3600秒或启动搜索。
