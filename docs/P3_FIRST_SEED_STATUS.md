# 首种子正式比较：时钟阻塞（2026-10-09）

当前状态为 **P3_CLOCK_BLOCKED**，不是READY。审计基点为
`e46b96cff35e7ea3b23c0b1eaef5fc66b03399ec`；保留其后68392db内容及已有工作。
只授权seed=20261008的随机、贪心各12配置和前缀候选复测，未扩展五种子。

## 身份和进度

正式执行仍用原内容`e308bfb873e6811c50ad685a979af345302fda8d`、原归档、固定
[Git身份](../evidence/p3/content-e308bfb/git_identity.json)、原cache与
[campaign检查点](../evidence/p3/campaign-e308bfb/checkpoint.json)。session仍为
`dc1c292900654d44b36a72548b95a610`，测量/搜索/campaign协议及输入、循环、容差不变。

- 随机3/12，贪心0/12：首批3/24个完整配置，0/2条完整轨迹，尚余21配置及候选复测。
- 23条原始执行：18条属于3个完整组，旧O0/s8的3条已abandoned，新attempt的2条
  于14:22按暂停请求中断组，留存为pending_restart；这5条都不产生配置分数。
- 原3个完整观测及原21条记录未改动；下一次真正恢复会放弃新2条部分组，完整重做
  一次预热和五次新测量。不能从性能缓存或旧部分组凑齐重复。
- 还没有完整4/8/12前缀、候选独立复测或两算法质量比较。原Grid表只作后续事后
  参照，诊断读数没有反馈策略，历史pilot没有改标为正式数据。

## 实际恢复尝试和边界时钟

[14:04批次](../evidence/p3/first-seed-e46b96c-20261009/controller.json)的前后检查都PASS；
新增2条样本后因用户暂停请求安全停止，主控退出2。16:38用户再次明确要求继续。
首次后台启动因Windows PS模块路径缺少Get-FileHash失败，尚未启动目标；
[原始stderr](../evidence/p3/first-seed-e46b96c-resume-20261009-1639/controller.stderr.txt)
保留，未获得该已结束后台进程的可靠退出码，明确为未知。
仅为新子进程指定Windows PS系统模块路径后修复，不改脚本字节或系统设置。

[16:42恢复主控](../evidence/p3/first-seed-e46b96c-resume-20261009-1643/controller.json)
使用相同脚本SHA、e308bfb归档和参数。其批前检查失败，**没有调用正式campaign**；
退出前检查也失败，原检查点/活动成本不变。短检查scope是WSL同区间时钟，以及
Windows完整调用的UTC/QPC一致性；不把宿主整次调用与三个sleep之和直接比较。

| 检查 | MONOTONIC s | RAW s | 绝对差 ms | 允许差 ms | 判定 |
|---|---:|---:|---:|---:|---|
| 批前第3区间 | 3.001954764 | 2.966602491 | 35.352273 | 34.666025 | FAIL |
| 退出前第1区间 | 3.000338465 | 2.963099324 | 37.239141 | 34.630993 | FAIL |

之后先声明[限定复核规则](../evidence/p3/clock-recovery-20261009-1646/policy.json)，
唯一一次10×3秒探针保留所有[原始纳秒端点/读数](../evidence/p3/clock-recovery-20261009-1646/probe.json)：
5/10个MONO/RAW区间失败，最大绝对差39.919ms；REALTIME/RAW十条均通过。
判据仍为`abs(MONO-RAW)<=5ms+1%*RAW`，不改限值、不筛值、不继续探测到偶然通过。
[判据复算](../evidence/p3/clock-recovery-20261009-1646/check.json)。tsc与NTP同步状态
不证明独立物理时间精度，根因未确认。没改频率/内核/WSL配额/安全策略/计时源。

16:56[正式资源复查](../evidence/p3/first-seed-review-20261009-1658/resource_gate.json)
通过：宿主最低2.76GiB、WSL3.93GiB、CPU平均5%/最大7%，swap使用0、根空闲约209GiB。
这是新快照，不冒充16:42条件；资源PASS不解除时钟阻塞，也不保证运行期间平稳。
旧诊断Windows确为运行中约30秒采样（中位33.111s），72条中的44条低内存及一次
CPU21%的警告保留，不追认旧结果稳定。

## 成本与核验

原campaign未校准MONOTONIC累计活动7120.754915秒，其中门禁/等待1165.348475秒；
3个终态搜索评估调用3668.358619秒；5条不计分执行进程累计2236.427057秒。
独立复测为0。各层级嵌套，不相加。活动成本不含离线暂停，新恢复前的时钟检查/
独立复核/只读验证也不混入此成本；辅助操作耗时各自见command/controller记录。
不存在完整端到端预算前缀成本，继续遵守[成本口径v1](P3_COST_SCOPE.md)。

[首次只读核验](../evidence/p3/first-seed-review-20261009-1658/summary.json)记录资源、
3项当时回归、原观测/原始前缀及CLI `--require-two`应退出2。随后新增两项行尾
回归：支持Git外层CRLF/LF转换但不接受内容篡改；保留原运行时SHA及独立规范化
旁证，不能把两者混称字节完全一致。已用源码另存collector_sources且哈希对应。
[30项原归档/编译器/缓存实际SHA核验](../evidence/p3/first-seed-review-20261009-1658/cache_and_archive_identity.json)
全部一致，原C/运行器/冻结配置对审计基点差异为0。交付内容随后另从干净归档检查，
记录其准确内容SHA，不替换正式实验身份。

## 后续入口（本轮不再启动）

先复核时钟异常及是否能恢复原协议；不能仅因资源PASS或某一次探针PASS就宣称稳定。
更换核心计时源/测量协议必须新版本、新session并先建立匹配完整Grid。
确认条件满足后，用**新的**批次证据目录调用既有主控；它先检查时钟、再由原
运行器检查门禁/固定身份，并自动归档清除暂停标记，禁止手动删标记或改旧分数：

```powershell
powershell.exe -NoProfile -File scripts/resume_p3_first_seed.ps1 `
  -EvidenceDirectory E:/software_system/project01/evidence/p3/first-seed-NEW-BATCH
```

仍只运行limit=2。完成两轨迹及其4/8/12候选复测、审计后，才讨论五种子扩展。
