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
