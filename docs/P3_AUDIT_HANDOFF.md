# P3 审计入口（执行中）

授权：用户要求 P2 完成后开始 P3。P2 保留基线
`37b10327909d9d4134a2d4d68aae0e27b4fc483c` 已推送，尚未获得外部审计通过。

当前新增 P3 独立轨迹、私有观测恢复、预算前缀和各候选独立复测，C 核心与 P2 测量/
搜索 schema 2 不变。[冻结规则](P3_PROTOCOL.md)、[campaign 配置](../configs/p3_campaign_protocol.json)、
[运行器](../autotuner/campaign.py)、[只读后处理](../scripts/audit_p3_evidence.py)、
[受控回归](../tests/test_campaign.py)、[干净验收脚本](../scripts/run_p3_clean_validation.py)。

初始资源只读快照：[2026-10-09 开始快照](../evidence/p3/environment/start_20261009.json)。
正式内容 SHA、干净归档验收路径、正式批次范围、逐样本证据和最终结果在实际完成后
填写，当前没有宣称完成 P3 正式实验或五种子比较。

待审计：策略是否严格使用自身观测；每组是否完整 fresh/force；失败与部分样本是否
不计分；预算前缀与候选复测是否分离；资源 gate/暂停身份是否完整；P2 原表比较与
P3 跨 session 时间差是否明确区分；未校准时钟/环境压力是否要求另环境重新测量。

本入口为阶段状态，不替代 P2 完整性证据或外部审计意见。最终提交 SHA 只在提交和
推送后终端交接提供，不为把文档写进自身 SHA 而循环提交。
