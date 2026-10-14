# 本轮交付：RAW比较入口已实现，三配置验证因未接AC停止

基点`e1b3a7ee26da346efa50da564199e53ec91cccda`；状态
**P3_RAW_COMPARISON_PARTIAL_AC_POWER_BLOCKED**，不是18次验证完成或P3搜索完成。

## 实际身份

- 执行内容：`35a60b090b728d2ec3b6a8ea014beac69fe3766d`；交付后文档/证据提交不替换它。
- 继承测量来源：`3cc9e0d03ba682569fca0e91f28d364f2dab73fa`，C、科学配置/输入/reference/
  容差、20空间、原搜索/测量、RAW计时和资源v2原字节不变。
- 新比较协议：`2026-10-14-raw-comparison-v1`，规范化JSON哈希
  `362668cb7857b69ccc528ecb58b5870d7d347dfa30149f615f228fd058593495`。
- validation session：`f9f3bb0d54724d2385a8b77be26a99b3`。
- search session：`d7a9ba9fc5384990b739ff51363a03e5`，完全空观测、没有活动claim/证书。
- WSL准确归档：`/var/tmp/matrix-raw-comparison-content-35a60b090b728d2ec3b6a8ea014beac69fe3766d`；
  Windows：`C:\Users\28489\AppData\Local\Temp\matrix-raw-comparison-35a60b090b728d2ec3b6a8ea014beac69fe3766d`。
- [validation plan](content/validation_plan.json)、[search plan](content/search_plan.json)绑定归档、Git blob、
  实际SHA256及CRLF/LF、编译器/二进制/reference、协议哈希。教师原C必须原字节相同。
  已核验build/reference缓存可复用，新performance目录独立，不读旧性能成绩。

## 真实停止与精确计数

[唯一验证调用stdout](operations/validation_activity.stdout.txt)、[stderr](operations/validation_activity.stderr.txt)、
[可靠退出2及外层QPC](operations/validation_activity.operation.json)。
GetSystemPowerStatus查询成功，[ACLineStatus=0、电量72%](content/validation-f9f3bb0d/ac_status.json)，
即当时未接交流电。按运行时接电/开盖条件停止，**没有重启重试**。
[临时防睡眠](content/validation-f9f3bb0d/sleep_request.json)核验申请及finally同线程释放均成功；
它不能阻止用户合盖，也没有修改全局电源设置。

| 项目 | 实际本轮 | 计划 |
| --- | ---: | ---: |
| Recovery / Formal资源门禁 | 未执行 / 未执行 | 按资源v2 |
| 新fresh短/长准入区间 | 0 | 2 |
| 分组两侧RAW探针 | 0 | 6 |
| 4096矩阵目标 | 0 | 18 |
| 三配置完整组 | 0 | 3 |
| 小矩阵、reference生成 | 0 / 0 | 不重复历史 |
| 部分/放弃矩阵组 | 0 / 0 | 失败保留 |
| Random/Greedy真实评估、轨迹、候选复测 | 0 / 0 / 0 | 本轮不执行 |

[window](content/validation-f9f3bb0d/window.json)的phase是计划进入的admission_resource_gate，
AC检查在实际采集之前拒绝；没有admission_resources目录或探针manifest，不能据phase写成门禁已执行。
排他[claim](content/validation-f9f3bb0d/ACTIVITY.claim.json)保留，不可通过重复启动重置预算。
3600秒预算实用QPC2.428145秒；外层验证进程3.1998347秒包含它，两者不相加。
门禁等待/原生探针/目标/评估RAW/复测/放弃目标成本均0；[costs](costs.json)另列辅助闭合捕获
去重108.9703983秒，仅为当时日志快照，不含后续收尾、编辑/模型/推送，不冒称整轮总耗时。

## 验收与测试

[独立原始复算](independent_validation_audit.json)从准确执行归档运行，退出2表示未完成：

| 字段 | 结果 |
| --- | --- |
| evidence_integrity_pass | true |
| validation_complete / validation_timing_checks_pass | false / false（未执行） |
| P3 execution_complete / timing_checks_pass / comparison_ready | false / false / false |

没有新恢复证书，也没有新时钟失败。不能将未执行写PASS，或称CPU/内存仍阻塞。
[完整摘要](delivery_summary.json)。

双干净归档各19项新回归通过：
[Windows](content/operations/clean_windows_focused_tests.stderr.txt)、[WSL](content/operations/clean_wsl_focused_tests.stderr.txt)。
覆盖12唯一/4-8-12前缀/内部候选去重映射、自身观测隔离/fresh/replay、身份/证书拒绝、独占预算、
两侧检查不能代替内部连续性、待机/包络差停止及异常释放。
均是假执行器结果，不能作为真实性能或18次4096结果。
[干净CLI](content/operations/clean_cli_help.stdout.txt)、[20唯一配置](content/operations/clean_list_configs.stdout.txt)、
[归档/空session初始化与工具日志](content/operations/)、[准备摘要](content/prepare_summary.json)。
一次辅助Windows list-configs因目标GCC仅在WSL而失败，[stderr](operations/list_configs_precommit.stderr.txt)保留；
最终实际WSL准确归档list-configs通过，无编译器替换。
[真实Windows防睡眠/API和事件smoke](operations/windows_api_smoke.stdout.txt)也成功，只是辅助检查。

## 历史保护与结果结构

关闭的Grid content3cc9e0d / sessionf705a488不再追加。
[准确旧归档只读审计](closed_grid_readonly_audit.json)仍为20配置、120唯一fresh、40两侧检查有效；
新输出仅写本目录，不覆盖旧审计。原[历史哈希清单](history_before.json)2089文件全部原字节未变，
[保护结果](history_after.json)包含closed Grid/controller/claim/证书/初始检查点/样本及相关失败历史；
其他旧证据没有Git diff，d681空session未写入观测。

[派生三种质量注释](closed_grid_quality_annotation.json)：correctness_pass与timing_contract_pass
依旧冻结契约；uninterrupted_execution对O3/s24为false（已证实待机），其他组为unknown而不是true。
不删除原待机样本、不替换中位数、不按休眠退款，不用新规则追认历史内部连续性。

[三配置旁列表](three_configuration_comparison.csv)只保留原Grid的50.996291138、52.469094035、
66.249431562秒及原CV/MAD；新值、变化百分比、正确性和连续性均未执行。
[六行预算结构](first_seed_six_row_template.csv)全部未执行，无假执行器成绩或旧Grid分数注入。
[后续提案](later_search_budget_proposal.json)约7–10小时、固定12小时QPC活动上限，需要另获外审授权；
实际组成、资源等待和复测可变化，不保证完成，超时不重置，不扩五种子/第四算法。

## 只读复核与下一步

从准确Windows归档执行（输出使用新文件）：

```powershell
Set-Location -LiteralPath 'C:\Users\28489\AppData\Local\Temp\matrix-raw-comparison-35a60b090b728d2ec3b6a8ea014beac69fe3766d'
$comparisonPlan = 'E:\software_system\project01\evidence\p3_raw_comparison\20261014-102833\content\validation_plan.json'
$comparisonReview = 'E:\software_system\project01\evidence\p3_raw_comparison\20261014-102833\readonly-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.json'
python -B -X utf8 -m scripts.raw_comparison_contract --plan $comparisonPlan --output $comparisonReview
```

预期退出2，必须同时读取errors为空/完整性true/未执行状态，不当作RAW判据失败。
**不得再次run当前one-shot plan**。先外审入口与失败证据，接AC/保持开盖后明确新有限验证授权；
保留本claim/成本，决定如何初始化新验证活动，不自行重置当前窗口或恢复旧Grid。
本轮停止，不自动搜索。[Windows原controller PID退出核验](operations/owned_windows_process_check.stdout.txt)、
[WSL无本任务测量器/探针进程](operations/owned_wsl_process_check.stdout.txt)均空。
真实终端stdout/stderr已保存，没有真实终端截图，不伪造或为截图补跑。
