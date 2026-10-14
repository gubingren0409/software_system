# 新AC授权验证：两组完整通过，E证据盘满后停止

状态 **P3_RAW_VALIDATION_PARTIAL / EVIDENCE_DISK_FULL**。本轮不执行Random/Greedy。

## 身份和新授权

基于`c08184e2cd6ac90af9d22aafdd3cd6b2ab09dd06`，用户已接AC、保持开盖，明确授权
一次新3600秒活动，不覆盖旧claim/AC失败证据。

- 运行内容：`35a60b090b728d2ec3b6a8ea014beac69fe3766d`，归档/源码/协议完全沿用。
- 科学测量来源：`3cc9e0d03ba682569fca0e91f28d364f2dab73fa`。
- 新session：`9332ead2881a4c1e91b966e90a0d2057`，初始化目标/reference/观测均0。
- 新比较协议哈希：`362668cb7857b69ccc528ecb58b5870d7d347dfa30149f615f228fd058593495`。
- [新授权](authorization.json)、[冻结plan](validation_plan.json)、[初始化及来源核验](preparation_summary.json)。
  92个双端执行文件、科学来源、编译器、12个build/reference缓存文件及探针二进制身份通过。
  Git blob/执行字节/CRLF/LF分别记录；教师原C保持188d0111…字节身份。

复用上轮双干净归档各19项测试，不重复110项、历史案例或n17；没有修改正式代码/协议或搜索规则。
只调用原准确归档，目标n4096/random/输入种子20261008、1预热+5fresh/中位数不变。

## 实际结果

| 配置/执行顺序 | 原Grid中位数/秒 | 本轮中位数/秒 | 变化/% | 本轮CV/% | MAD/秒 | 状态 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| O3/s128 | 50.996291138 | 51.602724641 | +1.1892 | 1.7022 | 0.449608174 | 完整通过 |
| O3/s64 | 52.469094035 | 52.784908609 | +0.6019 | 1.7756 | 0.242572761 | 完整通过 |
| O3/s24 | 66.249431562 | 未执行 | 未执行 | 未执行 | 未执行 | READY前写checkpoint失败 |

[三配置CSV](three_configuration_comparison.csv)、[JSON含同范围连续性数据](three_configuration_comparison.json)。
旧Grid只旁列、不覆盖或取两轮较小值；旧s24待机样本/原中位数保持。
两组共12唯一fresh（2预热+10测量），全部16777216元素校验，绝对/相对误差0，结果/参考/
误差/checksum/时间有限，RAW整数端点和elapsed契约通过。[逐样本复算](all_sample_contracts_independent.json)、
[数值摘要](numeric_result_summary.json)、[原始samples](validation-9332ead2/samples.jsonl)。
结果没有传给任何策略；search/prefix candidate retest均0，旧空search session不变。

一次准入2/2完整、10响应、新证书绑定新session；原生libc/不绑核、先10亿后100亿固定更新。
组边界已采5个区间（128前后、64前后、24仅前），合计7区间全部RAW通过，无替换/补采/校准，
MONOTONIC辅助警告0。[全部独立端点复算](all_clock_checks_independent.json)、
[准入原始消息/端点/证书](validation-9332ead2/admission/)、
[各组检查/连续性及电源原消息](validation-9332ead2/group_checks/)。

ACLineStatus=1；临时防睡眠请求成功，finally同线程释放。两个完整组无待机事件；
同范围QPC/RAW分别320.8052023/320.798597304秒、330.1134924/330.107951371秒，
差6.605/5.541ms，预声明连续性规则通过。防睡眠仍不能保证阻止用户合盖。
正确性、RAW契约和内部连续性三项分别成立，不推广到未执行s24或旧Grid。

## 精确计数与停止原因

| 项目 | 本轮实际 |
| --- | ---: |
| 新完整验证组 | 2/3 |
| 4096目标启动/保存/fresh | 12/12/12（计划18） |
| 已保存预热/测量 | 2/10 |
| s24目标/样本 | 0/0，剩6次未执行 |
| 部分矩阵样本/放弃矩阵组 | 0/0 |
| 失败组启动控制attempt | 1（s24，READY前） |
| fresh准入/组边界区间 | 2/5，共7，全部通过 |
| 新reference生成/小矩阵/Grid/搜索/前缀复测 | 全部0 |

s24组前Formal及RAW通过，但WSL写活动checkpoint时EIO，尚未发READY或启动目标。
Windows主控保存失败状态又报`Errno28 No space left on device`；真实[stdout](operations/validation_activity.stdout.txt)、
[stderr](operations/validation_activity.stderr.txt)、[退出1](operations/validation_activity.operation.json)。
只读[Windows磁盘](operations/evidence_and_system_disks.stdout.txt)和[WSL根盘/证据盘](operations/wsl_root_and_evidence_disk.stdout.txt)
同时确认E:仅16384B，WSL根盘223129370624B可用。原门禁只查WSL根盘，不能代表E证据盘。
启动前E余量/致满过程unknown，不归因到某应用、Vmmem预占或时钟异常。

[window](validation-9332ead2/window.json)为stopped；[最后有效checkpoint](validation-9332ead2/checkpoint.json)
仍ready、active=null、两组，**是最后持久化状态，不是控制器成功或可以直接resume**。
保留两份失败临时片段：

- [.checkpoint…33fb…tmp（0B）](validation-9332ead2/.checkpoint.json.33fb0a2d949b40ebb62312d0290adc43.tmp)
- [.checkpoint…d9e1…tmp（65512B）](validation-9332ead2/.checkpoint.json.d9e18db1111948aaac9d63a7af07ec1f.tmp)

它们不是有效成绩/检查点，不拼接、不手工修复原状态。当前claim保留，未补跑、重启或退款。

## 资源与成本

Recovery最终PASS，setup和三组前Formal最终PASS；s128前原host_memory REJECT297893888B
仍保留，原120秒窗口内下一次PASS821194752B。所有五样本/CPU/提交额度/分页原值保留，
宿主低2GiB警告不抹去，也不误用于限制目标自身CPU。[独立门禁复算](all_resource_gates_independent.json)。
根盘门禁通过不保证证据盘可写或性能可靠，新CV高于原值但不事后删慢样本。
最大单进程RSS394852KiB约385.6MiB，不是整机精确峰值。

- 活动窗口QPC：846.073676s，预算3600s；外层进程846.9903539s包含它。
- 两个完成组ConfigurationEvaluator评估RAW：650.83599454s，内含全部核心633.229610487s。
- 门禁采集/等待QPC113.3422585s，原生时钟过程53.8220326s，setup缓存核验RAW0.553232607s。
- 新reference生成、搜索和前缀候选复测0；s24没有核心计算成本，失败启动包装仍计活动包络。

上述范围嵌套，不能全相加。准备、C救援/克隆、后处理、Git/推送为活动外辅助，不填入核心成绩。
[costs.json](costs.json)保留范围；旧Grid/旧AC成本不修改、不退款。

## C盘救援与历史保护

复制本轮290文件/4867951B到C，应急[逐文件SHA证明](disk_full_rescue/rescue_manifest.json)，
原E没有移动、删除或改写。[复制核验](raw_evidence_copy_verification.json)证明全部原始运行数据字节一致；
仅本轮辅助后处理脚本有已记录修改，初始版本另存救援目录。
[13231项历史保护](history_after.json)包含旧AC claim/失败、关闭Grid/待机样本/检查点/证书/预算及旧空search。

提交工作树：
`C:\Users\28489\AppData\Local\Temp\matrix-validation-rescue-20261014-184709\repository`。
它保留c08184e历史、project01分支及原GitHub目标；原E工作树仍基点且保留本轮未提交数据，
不reset/强制同步。首次克隆checkout因长路径失败，后续仅此新repo启用core.longpaths，
checkout-index只填7465个缺失文件，不覆盖原E或已存在文件；[原始操作](disk_full_rescue/operations/)。

后处理Windows路径解析首次失败，只改辅助脚本使用既有local_path；原执行源码/日志另存，
再将第三配置明确为not_executed（不是RAW失败），未修改冻结35a归档或重跑目标。

## 验收与下一步

[准确35a归档独立审计](independent_validation_audit.json)退出2表示未完成，errors=[]：
evidence_integrity_pass=true，validation_complete/validation_timing_checks_pass=false；
P3 execution_complete/timing_checks_pass/comparison_ready全部false。不是已经采集的时钟失败。
[最终摘要](delivery_summary.json)。

只读复核需保留原E原始证据和本机准确归档，输出写C盘新文件：

```powershell
Set-Location -LiteralPath 'C:\Users\28489\AppData\Local\Temp\matrix-raw-comparison-35a60b090b728d2ec3b6a8ea014beac69fe3766d'
$validationPlan = 'E:\software_system\project01\evidence\p3_raw_comparison\20261014-182807-ac-validation\validation_plan.json'
$reviewFile = 'C:\Users\28489\AppData\Local\Temp\raw-validation-review-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.json'
python -B -X utf8 -m scripts.raw_comparison_contract --plan $validationPlan --output $reviewFile
```

**不要直接再次run当前plan**。先外审两组及磁盘故障，释放E空间后审定安全同步原工作树、
证据盘写入余量/ENOSPC回归和有界续跑方案。剩2753.926324s不构成自动重试授权。
本轮不自动开始搜索、不扩种子/算法，不伪造终端截图；真实终端日志已保留。
[Windows进程退出](operations/owned_windows_processes.stdout.txt)、[WSL测量/探针/候选进程为空](operations/owned_wsl_processes.stdout.txt)。

默认Git whitespace检查仅提示原克隆失败stderr末尾空行；原始SHA不改，单一路径排除后严格检查通过。
[例外/退出码](whitespace_exception.json)、[失败临时片段哈希及非成绩声明](failed_checkpoint_fragments.json)。
