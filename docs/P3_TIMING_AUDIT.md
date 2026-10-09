# 0023ceed 时钟、资源与交错复测审计

审计基点`0023ceedcbbb416e6ee8b6e2db44c41a10e90983`，在其后已推送的55b776b历史上
继续，保留用户/本轮续跑的全部证据，不回退分支。P2的20配置表保留；P3正式算法
比较未完成，本轮不继续完整P3长实验。

## 运行前判据（诊断schema 1）

[protocol](../configs/timing_audit_protocol.json)在本次诊断读数出现前声明并提交。
独立诊断session，C/core/measurement/search/campaign以及测量schema 2不变。
不能用诊断文件取代Grid或给搜索策略提供观测。

- 每个对照区间保留MONOTONIC、RAW、REALTIME、BOOTTIME端点纳秒原值（十进制串）
  和差值。Windows保留QPC/Stopwatch端点、频率、UTC ticks、完整WSL调用耗时。
- WSL同一区间：`abs(MONO-RAW) <= 0.005s + 1%*RAW`。宿主完整调用含启动/采集/输出，
  与WSL完整操作对照：`abs(host-RAW) <= 1s + 1%*RAW`。REALTIME对RAW允许
  `0.25s + 1%*RAW`，超过即标注间隔不一致，不能据此单独确认根因。
- 3个20秒sleep探针在复测前、3个在后；目标执行期间每次Evaluator完整调用也同时
  读MONO/RAW。这不是RAW核心时间，不能把比例直接乘到历史核心秒数。
- 每组开始前使用正式JSON门禁：Windows/WSL均≥2GiB、WSL根空闲≥1GiB、宿主CPU
  五样本平均≤10%/最高≤20%。不能仅凭退出0；失败门禁留档并按16次重查上限暂停。
  运行中保留宿主提交/分页、WSL swap/vmstat/PSI和目标GNU time峰值RSS；缺失为未知。
- n=4096/random/20261008/s=128，原输入/循环/1e-12容差、原超时。顺序固定
  `r1: O1,O2,O3; r2: O3,O2,O1`，平衡线性位置漂移，但中央O3相邻与仅两轮是局限。
  每组独立一次预热+五次force测量，五次核心MONOTONIC中位数；任何失败整组无分数。
- 预声明：组CV>2%标为波动，跨轮同配置中位数变化绝对值>2%标为漂移；相邻优化
  差距<2%标为小幅差距。稳定排序判据要求两轮排序相同、相邻差距均≥2%、漂移≤2%、
  无CV警告、全部时钟检查通过且无运行中资源警告，否则只写“本次观察排名”。

这些是本项目审计质量判据，不是老师要求，也不是物理校准标准。没有引入单一校准
系数、不删慢值、不将“读数一致”写成独立物理时间认证。若后续更换计时源/测量
协议，必须新版本/内容提交/session并先取得匹配的完整新Grid，不能沿用旧Grid作
新协议的正式比较基线。

## 已保留与修订范围

用户要求后写PAUSE_REQUEST，旧P3在当前目标完成后安全退出：3个完整配置、
21次完整目标执行，含O0/s8部分组3条，未计分。它们全部留在原campaign，恢复该
部分组须重新预热及五次测量。[暂停证据](../evidence/p3_audit_0023ceed/p3_pause.json)。
P3原内容仍e308bfb；新诊断session单独绑定新内容SHA，不迁移/改写旧样本。

成本不是改计分：限定原前缀字段的排除项，新增失败门禁暂停—成功恢复的受控回归，
见[成本口径](P3_COST_SCOPE.md)。report修正O3差距：O1复测漂移2.4976%大于O2差距
1.9850%，但小于O3差距2.9017%；原笼统“大于O2/O3”错误，修正不证明稳定最优。
[只读原CSV/检查点复算](../evidence/p3_audit_0023ceed/report_gap_correction.json)。

## 执行与后续

脚本：[Windows主控](../scripts/run_timing_audit.ps1)、[WSL诊断](../scripts/timing_audit.py)。
从内容提交的干净归档执行，移除PYTHONPATH/不写pycache；工具/源码/Git字节、实际
字节、编译器、二进制/reference哈希和manifests都记录。每个步骤取得同一P3独占锁，
防止并发目标；PAUSE_REQUEST保持，完整P3必须等外部复核后才显式恢复。
原缓存不清理，新增大数据/二进制仅在WSL本地独立audit缓存，不提交Git。

诊断结果与实际新SHA在本轮执行后补充；当前不预填任何性能或时钟结论。

### 主控v2迁移（读数出现前）

首次从WSL UNC路径启动dbf43e6副本，Windows返回未签名脚本拒绝（退出1），
没有建立诊断session或执行目标。原失败stdout/stderr保留在
[controller](../evidence/p3_audit_0023ceed/diagnostic_controller.json)。
不修改执行策略：改用同一新内容提交的Windows本地`git archive`副本执行PS，
WSL仍用该提交的独立干净归档执行Python/C。主控schema升为`timing-audit-host-v2`，
逐项核对本地PS/协议与WSL归档的SHA-256；Snapshot子进程也使用校验过的本地
资源脚本。新的内容SHA、诊断session与迁移记录绑定，原测量/搜索协议与C计时源
不变，无任何旧/新样本拼接。

v2的正式门禁PASS后，setup发现`wsl.exe`边界把反斜线路径去转义为无分隔符路径，
在构建/reference/目标前失败。保留session-46bcbd7全部原始输出。v3仅将传给WSL
的Windows脚本路径规范化为正斜线；本地执行及SHA校验不变，另建内容提交/session。
