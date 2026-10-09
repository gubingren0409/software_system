# 预算前缀成本口径 v1（0023ceed 审计修订）

这是对 schema 1 既有字段的范围说明，不改运行器、冻结搜索/测量协议或旧数值。
P3 正式算法比较尚未完成。不能用以下任意一个前缀之和宣称完整端到端搜索成本。

| 既有字段 | 包含 | 不包含 |
|---|---|---|
| `configuration_evaluation_seconds` | 前k个终态配置的ConfigurationEvaluator调用；预热、测量、验证、每次cache查找、失败时已有样本 | 配置启动前门禁、setup、跨暂停等待、放弃的非终态尝试、候选独立复测、离线间隔 |
| `configuration_start_gate_seconds` | 产生该终态组的那次运行器调用内、配置开始前的门禁/重试等待 | 更早调用中失败并退出的门禁；setup门禁、非终态组、离线间隔 |
| `configuration_total_wall_seconds` | 上述同一次配置循环调用从门禁到终态保存的墙钟（不是前两字段再加一份） | 跨暂停前失败门禁/旧部分组、setup、其他配置、复测、离线间隔 |
| `core_compute_seconds` | 前k个终态组全部目标样本的核心计算含预热，失败缺失值不推算 | 编译/reference/验证/墙钟；不等于k个中位数之和 |

前k以终态配置观测（包括失败配置）定义，预算仍为唯一配置评估。失败不产生分数，
不能从成功子集拼重复。`process_wall_seconds`、核心秒、评估秒和门禁秒有包含关系，
不能全部相加。既有fallback到evaluation_wall的旧组字段并非门禁已知为0的证明。

session 的 `wait_seconds` 累计每次门禁调用，包括失败退出前等待；`active_total_seconds`
累计各运行器调用到最后检查点的MONOTONIC成本，含门禁/setup/部分尝试，但不含进程
未运行的人工暂停区间或未落检查点的中断尾段。UTC跨时钟跳变/偏移不能反推精确
离线成本。失败门禁原始JSON和放弃记录另保留；旧session不存在可靠的完整按前缀
分摊账本，完整端到端前缀成本标为未知，不能把后来整个session的wait分配给早期前缀。

后续图表只能将现有 `configuration_evaluation_seconds` 标为“终态配置评估调用累计秒
（排除门禁/setup/放弃/复测/离线等待）”；如比较实际端到端预算耗时，需要新版本
事件账本和新session，不能在现有冻结session中改写来源。复测成本始终另列。

新增受控回归：[test_campaign_costs.py](../tests/test_campaign_costs.py)。使用受控时钟/
目标（不是性能数据）：setup门禁1秒、配置门禁连续16次各1秒+15次30秒等待，
暂停时session.wait=467；恢复setup1秒+4次配置门禁，wait=472，session身份不变。
四配置前缀只有恢复调用中的4秒门禁；session活动成本与该前缀total差468秒。
这明确保留此前失败等待，且证明前缀字段不能代表完整端到端。未修订计时或计分代码。

同步收窄只读后处理`plot_p3_results.py`的坐标/标题及排除项，改称终态配置评估
成本，不再笼统称Search cost。本轮未生成P3比较图（尚无完整正式预算前缀），
该辅助文件不被正式运行器或新诊断程序导入，不改变任何冻结session或搜索观测。
