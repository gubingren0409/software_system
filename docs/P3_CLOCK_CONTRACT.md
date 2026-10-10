# 辅助时钟与验收契约 v2.1（fdeed77 审计修复）

2026-10-10补充：本文件下述真实20区间及“本轮”指10-09历史。aedf028a后的集中
诊断未改变辅助源码/契约，因权限不足及资源拒绝没有进行新recovery或resume。
最新决策及前置处理要求见[P3_CLOCK_REPAIR](P3_CLOCK_REPAIR.md)；不能把历史命令
直接再次执行，下一轮须有处理证据、新唯一目录和新的有限验证授权。

这是辅助工具新版本，不是正式测量/搜索/campaign协议修订。正式内容仍为
`e308bfb873e6811c50ad685a979af345302fda8d`，session仍为
`dc1c292900654d44b36a72548b95a610`。C源码、循环、输入、容差、评分和原Grid不变。
本轮只授权seed=20261008的random/greedy两条12配置轨迹，不扩展五种子或第四算法。

## 单一判断实现与来源

主控和后处理均调用[`p3_clock_contract.py`](../scripts/p3_clock_contract.py)。原探针
`check_p2_clocks.py`仍从原e308bfb归档执行，SHA256为
`1cf4217497f674520ce22f015c61067287051d5644af66f4b27d2df2720706aa`。
判据文件未变，SHA256仍为
`720c91efdf26f6e435629d2638781cca1d79ebc49f49d203a7dcdaa398311b9f`：

- MONO/RAW：`abs(MONO-RAW) <= 0.005 + 0.01*RAW`。
- REALTIME/RAW及Windows整次调用UTC/QPC：`abs(a-b) <= 0.25 + 0.01*b`。
- 不用Windows启动全过程与WSL内部sleep之和直接比较；范围不同。
- 检查schema、必需字段/类型和准确数量；计时必须有限且正。纳秒端点必须为整数，
  先相减再除1e9，保存的delta必须与此结果相等。拒绝空、缺失、错误数量或来源。
- 每次操作绑定batch ID、manifest SHA、实际命令、输出路径、PID、退出码和stdout/
  stderr哈希。原始探针和stdout JSON须一致；保存的check必须与重新计算一致。
  不是信任check中的pass，也不是用旧批次通过证明新批次通过。

新辅助JSON明确写LF；源文件、流、检查点和JSONL仍同时保留运行时SHA与LF身份。
归档重定位时使用manifest记录的原执行路径，不能把新检出路径当成当时命令。
只接受可核验的CRLF/LF转换，不能接受内容变动；老师原件要求原始字节严格相等。

## 唯一一次有限复核

本轮证据根为`evidence/p3_clock_contract/20261009-180810-0491a4ec/`。
真实采集前落policy及manifest，再做A/B两个窗口，每个10×3秒，共20区间、60秒sleep预算。
每窗口WSL内部timeout为90秒，宿主等待上限120秒。A失败也采完B；没有自动重试路径。
全部20区间、整次调用UTC/QPC、冻结文件身份及正式资源门禁通过，才允许恢复。
任何失败保存全部可用数据并停止正式实验。Windows/WSL版本、启动、clocksource、
NTP及近期时间/休眠事件只读采集；缺失为unknown，不据同步状态推断物理时钟已校准。

测试使用合成端点，不占真实20区间预算。启动前先提交辅助实现，从同一内容提交
导出WSL和Windows独立副本。全套单测/CLI/20唯一配置及Windows实际模块/拒绝路径
从干净内容核验；不重复历史160案例或为辅助修复另跑4096。

## 统一入口和恢复

仅使用[`start_p3_first_seed.py`](../scripts/start_p3_first_seed.py)作为Windows入口：
明确启动Windows PowerShell，仅为子进程设置PSModulePath，调用前先验证Get-FileHash。
参数用数组传递，保留PID、stdout/stderr及可靠退出码；未知就是unknown。不改执行策略。

本轮唯一复核的实际命令如下，已执行并失败，**不得在本轮重复**：

```powershell
python scripts/start_p3_first_seed.py --mode recover --auxiliary-sha 0c6ee7e3726a01339d36e6ae7d19b0966dc043cd --output evidence/p3_clock_contract/20261009-180810-0491a4ec/recovery
```

恢复前重新正式门禁、冻结身份和当前检查点核验，实际调用批前/批后各3×3秒检查独立保存。
主控分别记录pre_clock_pass、campaign_invoked、campaign_returncode、post_clock_pass及
failure_reason；批后问题只追加，不能覆盖首个拒绝原因。原运行器自行归档暂停标记及
2条新部分样本，O0/s8新attempt重新1预热+5fresh，不拼部分组或性能缓存。

本轮没有实际resume批次。20/20 MONO/RAW失败，2/20 REALTIME/RAW失败，两个Windows
同调用UTC/QPC通过；另有宿主内存门禁拒绝。全部原始数据、端点复算及说明见
[复核分析](../evidence/p3_clock_contract/20261009-180810-0491a4ec/clock_review_analysis.json)。

### v2 → v2.1 辅助迁移（不改变正式身份）

真实复核使用已干净验证的辅助内容`0c6ee7e3726a01339d36e6ae7d19b0966dc043cd`。
复核另发现身份清单误把后增的`timing_audit_protocol.json`要求在原e308bfb归档中存在；
原归档没有此文件，sha256sum退出1。因此原summary的identity/integrity为false，保留不改。
原有31项存在的文件均匹配，实际执行判据一直来自辅助工作树且SHA正确；这是辅助
位置错误，不是正式源码改动。v2.1仅将该清单项指向辅助工作树，增加路径回归，
并区分时钟/身份/资源拒绝原因。共享时钟检查器字节、判据及正式协议全部不变。
[补充32项只读哈希](../evidence/p3_clock_contract/20261009-180810-0491a4ec/identity_location_correction.json)
全部匹配，但不修改旧manifest、不追认旧identity为PASS、不授权恢复，不重采时钟。
修订后的辅助内容须独立提交/干净验证；本轮就此阻塞交付。
v2.1最终验收另显式禁止“仅恢复探针通过”认证实际campaign：必须有实际调用及
该调用绑定的两个边界检查，恢复-only即使面对已完整检查点也不能comparison_ready。
此前bb17720是路径修复中间内容，最终辅助内容另提交后独立验证，未再采真实探针。

最终辅助内容为`fa597017c2317772a0f7f34faa75194ffecec8f2`。
[准确提交的双归档验证](../evidence/p3_clock_contract/20261009-180810-0491a4ec/clean-fa59701/summary.json)：
74项WSL单测（1项Windows专用跳过），Windows旧7/新21项、CLI帮助、20唯一配置、
历史证据和25文件身份通过。后续仅补文档/证据，执行源码与该提交一致。
干净验证的历史未完成模式审计退出2；当前真实复核的
[独立验收](../evidence/p3_clock_contract/20261009-180810-0491a4ec/final_recovery_acceptance.json)
因原始manifest缺失路径而退出1，不能把历史模式的integrity=true移用给本次复核。
本次原始窗口各自的raw integrity=true；整体原始身份拒绝、时钟失败与comparison=false
均据实保留，补充哈希不是覆盖旧判定。

## 验收与成本

验收分为evidence_integrity_pass、execution_complete、timing_checks_pass、comparison_ready。
两条轨迹须各12唯一配置、六个4/8/12前缀及候选独立复测齐备。证据和相关时钟都通过
才能comparison_ready。`audit_p3_first_seed.py --require-two`未完成退出2、满足全部条件退出0；
证据损坏退出1。record入口支持`--acceptance-mode incomplete|complete`，摘要使用实际结果。
旧v1阻塞核验继续可读，但不能作为新批次证书。

前后检查点、原始记录前缀/ID、完整观测和实际campaign操作绑定；过期批次拒绝。
原Grid、旧P3的时钟/资源限制继续披露，不校准旧数据，不把诊断反馈策略。
成本仍按[`P3_COST_SCOPE.md`](P3_COST_SCOPE.md)：终态评估、复测、活动campaign、门禁/
等待、放弃尝试及本轮辅助QPC成本分列；层级嵌套，不全部相加。完整端到端前缀未知。
