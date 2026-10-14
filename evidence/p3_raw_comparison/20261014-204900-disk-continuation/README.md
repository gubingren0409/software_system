# E盘空间恢复后的单次补齐：资源阻塞，未新增目标执行

状态：**P3_RAW_VALIDATION_RESOURCE_BLOCKED**，不是三配置验证完成或正式搜索完成。
用户明确要求补齐磁盘失败。本次只准备O3/s24一个组，未重跑s128/s64，未启动Random/Greedy。
磁盘故障确已解除，但本次组前Windows可用内存门禁失败，按原规则保存停止。

## 身份、范围与保护

- 实际测量内容：`35a60b090b728d2ec3b6a8ea014beac69fe3766d`，科学来源3cc9e0d；
  validation session `9332ead2881a4c1e91b966e90a0d2057`不变。
- 外层补齐助手内容：`22fe97c02e2bf1cd56662413e10fc5311113a246`，准确三文件归档
  `C:/Users/28489/AppData/Local/Temp/raw-validation-continuation-22fe97c`。
  原冻结35a归档和协议完全不改，不删除原入口的空session保护，单独新增一次性外层授权。
- [授权/所有保护哈希](continuation/authorization.json)绑定原plan、当前checkpoint、12个run_id及字节前缀、
  原253个session文件、13,354个其他历史证据、helper SHA和仅s24的范围。
  [原检查点快照](continuation/preserved/checkpoint.json)、[原12条快照](continuation/preserved/samples.jsonl)
  及原claim/window/initial checkpoint均保存。新的claim只追加，不修改旧claim。
- [执行/归档字节、Git blob及行尾身份](source_identity.json)包括92个原执行文件、辅助三文件、
  协议/编译器/四二进制/reference身份。验证缓存复用，不调用setup/reference生成，不复用性能缓存。
  两个辅助Python执行/测试文件与Git字节一致；非执行Markdown归档为CRLF、Git为LF，规范化内容一致，
  单独记录两个SHA及计数，不把规范化相等伪称字节相等，也不改写原件或执行归档。
- [同步日志](sync.transcript.txt)、[原E文件哈希](pre_sync_original_files.json)：
  原E未跟踪activity移至`C:/Users/28489/AppData/Local/Temp/matrix-validation-rescue-20261014-184709/original-e-pre-sync-20261014-204900`，
  移前移后均SHA一致，再正常ff-only同步0a74241。只有既存后处理脚本版本与救援提交不同，原版本也保留。
  未reset/clean/强推，无用户文件丢失，原Gitea origin与GitHub github远端都保留。

## 预声明与实际执行

原3600秒中846.073676秒继续计费，本次只获余2753.926324秒；不新开3600秒，不退款，不自动再试。
[调度规则](../../../docs/P3_RAW_VALIDATION_CONTINUATION.md)和授权在采集前保存。
新增外层证据卷保障：至少1GiB空闲+实际写/fsync/read-back，不改变冻结资源策略v2。
E实测62715604992B可用（约58.4GiB），[写验证](continuation/evidence_volume_preflight.json)通过。

Formal预检通过：host最低3317710848B，commit余量31561756672B，WSL可用6248665088B，CPU均3.6%/峰6%。
随后仅一次默认libc/不绑核、固定10亿更新+100亿更新，2区间/10响应，RAW全部通过，无MONOTONIC辅助警告。
[新准入manifest](continuation/admission/manifest.json)、[整数端点/全部通信](continuation/admission/messages.jsonl)、
[独立复算](continuation/independent_continuation_admission.json)。旧初始证书不改，新附件绑定当前checkpoint/授权。
继承原20ms通信/读取跨度、5ms+1%U容差，没有删除、比例校准或补采。

O3/s24的新资源attempt `91ca8e9806b246f6a1b2d9e2938ec072`四次均仅host_memory拒绝：

| 快照 | Windows最低可用/B | WSL可用/B | CPU均/峰% | 原始判定 |
| --- | ---: | ---: | ---: | --- |
| 0 | 239452160 | 4913885184 | 2.2 / 4 | REJECT host_memory |
| 1 | 302333952 | 6240878592 | 3.6 / 5 | REJECT host_memory |
| 2 | 394579968 | 6209232896 | 10.4 / 15 | REJECT host_memory |
| 3 | 300908544 | 6168997888 | 14 / 27 | REJECT host_memory |

[全部原始快照及QPC包络](../20261014-182807-ac-validation/validation-9332ead2/group_checks/91ca8e9806b246f6a1b2d9e2938ec072/resources/gate_outcome.json)。
五个原始样本的最小值必须≥512MiB，不能挑选第4快照末尾较高值通过。
commit/CPU/WSL/磁盘不是本次拒绝原因。门禁耗时120.0005393秒，严格冻结审计还拒绝其0.0005393秒超额；
该失败及原始错误明确留在[独立门禁汇总](all_resource_gates_independent.json)，未放宽120秒。
原主控返回false并停止，新组前/后探针、READY、目标执行都未开始。真实退出码2，stderr空。
临时防睡眠申请非零、finally同线程释放成功；不改全局电源、不结束用户应用、不清缓存或主动重启WSL。

停止后的[宿主进程快照](operations/final_host_memory_and_processes.stdout.txt)显示可用4068204544B、
VmmemWSL约0.935GiB、ChatGPT单进程约0.844GiB、多个Chrome进程约0.57GiB/0.56GiB。
它与失败窗口不同，不能追认门禁通过，也不能证明某个应用或WSL预占是已证实根因。
[WSL完整meminfo/vmstat及进程快照](operations/final_wsl_memory_boot_and_processes.stdout.txt)仅作只读环境证据，
没有把Vmmem工作集加到宿主可用内存，没有再次发起正式门禁或时钟恢复。

## 验收、计数、成绩和成本

[独立补齐审计](continuation/independent_continuation_audit.json)真实退出2（未完成）；
[原冻结测量审计](continuation/base_independent_audit.json)继续确认两组/12条有效。
`evidence_integrity_pass=true`指原数据、来源、预算及保护；不表示失败资源门禁合法通过。
`formal_preflight_pass=true`、`group_formal_resource_pass=false`分别列出。
新准入2/2通过，累计9个RAW区间通过；只有128/64两组的四个边界检查完整，旧s24组前失败启动检查保留。
`validation_complete=false`、`validation_timing_checks_pass=false`；
P3 `execution_complete/timing_checks_pass/comparison_ready`仍全部false。

累计目标仍12/18fresh（2预热+10测量），本次新增0；完整2/3组，矩阵部分/放弃样本0，
旧磁盘失败启动1次，新门禁拒绝attempt1次；搜索配置/轨迹/前缀复测/reference生成均0。
原s128中位数51.602724641s、s64 52.784908609s不变，s24未执行。
[三配置表、CV/MAD及历史Grid旁列](three_configuration_comparison.csv)、[12条契约复算](all_sample_contracts_independent.json)。
旧Grid包括s24待机样本的所有原记录/分数保持，不能据新准入认证历史连续性。

[成本](costs.json)：原846.073676s＋本段200.0468689s＝1046.1205449s活动QPC，
原3600s内账面余2553.8794551s。只相加分别验证的时长，不跨epoch相减；claim不允许再领取。
本段外层进程211.1955594s包含本段活动及启动核验；两组评估RAW650.83599454s，
核心含预热633.229610487s、全部门禁258.9473047s、原生探针89.4850927s都是嵌套项，不能全部相加。
setup仍原0.553232607s，reference/search/前缀复测0。离线排查/用户释放空间/代码/快照/审计/Git不入活动，
各辅助命令实测包络见operations，存在并行/包含关系，未虚构完整人工操作成本。

10项相关受控测试在工作树和准确辅助归档均通过，无新增n17/真实目标。初次夹具及后处理失败修复
保留在[开发记录](development_notes.md)及operations，不隐藏失败。所有操作都有实际argv/stdout/stderr/退出码。

只读复核（不会运行矩阵）：

```powershell
python -B -X utf8 C:/Users/28489/AppData/Local/Temp/raw-validation-continuation-22fe97c/scripts/resume_raw_validation.py audit --authorization E:/software_system/project01/evidence/p3_raw_comparison/20261014-204900-disk-continuation/continuation/authorization.json
```

**本轮已停止，不再调用run。** 后续先审查资源变化和失败门禁，再明确一次使用2553.8794551秒剩余额度的授权；
不能删除原claim、直接重启本次run或自动开始搜索。任务进程退出状态见final_checks.json。
