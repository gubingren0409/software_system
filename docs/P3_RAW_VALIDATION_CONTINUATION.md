# 磁盘故障后的单次补齐授权（2026-10-14）

用户释放E盘并明确要求补齐本次失败内容。本次不创建新的3600秒预算，
只续用原846.073676秒后的2753.926324秒。离线排查/代码准备单列，两个活动包络按各自QPC
整数端点相减后求和；不跨epoch相减，不删除旧claim、不改写原window或初始证书。

执行测量内容仍为35a60b090b728d2ec3b6a8ea014beac69fe3766d、验证session仍为
9332ead2881a4c1e91b966e90a0d2057。只允许index2/O3/s24，前两组和12条JSONL字节前缀必须保持。
新外层助手单独提交、准确归档；所有科学模块从原35a60b0归档导入，无setup重做、无性能缓存复用。
原失败attempt和两份临时检查点片段继续保留。旧派生摘要描述首次停止，不能冒充最终状态。

外层新增证据盘保障：至少1GiB自由空间并实际write/fsync/read-back；这是因E盘故障新增的
调度前检，不修改科学资源策略v2的CPU、内存或WSL根盘规则，不追认历史REJECT。
原子写可保留最后有效检查点，但磁盘完全耗尽时无法保证再次写出失败状态；旧失败证据如实保留。

本次只允许一次fresh短/长默认libc、不绑核准入附件，绑定原计划、当前检查点及本次授权哈希，
原RAW/QPC判据不变。正式资源门禁先于长探针，组前再次门禁、组前后各一次fresh短探针。
原初始恢复证书仍由原运行器验证；本次附件独立审计，不能用旧证书单独证明当前准入。

O3/s24重新以新attempt完成1预热+5fresh，RAW中位数计分。任何失败停止，不从旧失败attempt
补样、不挑成功子集、不自动重试。临时防睡眠、接电检查、System事件及同范围QPC/RAW连续性沿用。
每60秒保存并报告进度，finally释放防睡眠。补齐后独立验证完整18次/三组及所有原始端点，
原始测量审计外另核验本次附件、活动预算、前缀和历史保护。

仅验证完成可以标validation_complete / validation_timing_checks_pass；Random/Greedy未运行，
P3 execution_complete / timing_checks_pass / comparison_ready仍为false。不自动搜索或额外复测。

```powershell
# 从新辅助内容SHA的准确归档执行，--plan仍指向原validation_plan.json
python -B -X utf8 scripts/resume_raw_validation.py prepare --plan <原计划> --output <全新续跑目录> --auxiliary-sha <辅助内容SHA>
python -B -X utf8 scripts/resume_raw_validation.py run --authorization <续跑目录/authorization.json>
python -B -X utf8 scripts/resume_raw_validation.py audit --authorization <续跑目录/authorization.json>
```

重复调用run因session独占DISK_CONTINUATION_V1.claim.json拒绝，不再次获得额度；prepare不执行矩阵。
真实命令/退出码、当前环境、资源、来源和结果见本轮独立证据目录。

## 2026-10-15：用户明确授权再尝试一次，仍用原余量

用户“重试一下吧”授权本次人工重试，不授权循环重试或新的3600秒窗口。
原846.073676秒和上次200.0468689秒全部计费，起始累计1046.1205449秒，
本次只用2553.8794551秒。通过`--prior-authorization`绑定上次授权、窗口、原claim及SHA，
使用新schema raw-validation-user-retry-v1和独占DISK_CONTINUATION_RETRY_V1.claim.json。
旧claim/故障/REJECT/原十二条均不改；原22fe97c助手归档和记录仍按原身份保留。
新助手单独冻结，测量仍用35a60b0及原验证session，只补s24一个组。

保持原Formal策略及120秒总上限；外层将一次门禁采集/等待的deadline设为至多119秒，
预留1秒收尾，原冻结manifest预算及严格审计仍为120秒。这是提前停止，不放宽上限，
不修改CPU/内存/计时判据。上次120.0005393秒失败仍失败。
先门禁再一次fresh短/长附件，组前重做门禁与fresh检查；任何失败立即保存停止，
不因旧准入通过跳过当前验证，不启动搜索。

## 2026-10-15下午：第二次明确人工重试

用户再次“重试”，仅授权一次新尝试。通过版本raw-validation-user-retry-v2绑定此前两次拒绝的完整
授权/claim/窗口链；新独占DISK_CONTINUATION_RETRY_V2.claim.json，不能覆盖或重复领取旧claim。
先前846.073676+200.0468689+211.7102998=1257.8308447秒照计，本次只用2342.1691553秒。
新外层内容单独提交/准确归档，实际35a60b0测量及原session不变；前两组不重跑，只差s24六次。
本次仍只允许一次新的short/long准入及原组两侧检查；资源/计时规则和119秒采集等待+1秒收尾不变。
任意失败停止，不借当前授权无限循环或打开新3600秒预算，不启动搜索。
