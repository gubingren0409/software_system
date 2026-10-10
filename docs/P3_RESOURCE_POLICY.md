# P3 资源准入迁移 v1（2026-10-10）

最新b19e6cd后7405fcc3有限恢复结果另见[P3_FIRST_SEED_7405FCC3](P3_FIRST_SEED_7405FCC3.md)：
Recovery因宿主内存不足拒绝、未采集时钟或启动矩阵。下述“本轮”及e0353bf结果为迁移阶段历史，
不作为7405fcc3/session3768a29a的通过证明；新旧原始证据均保留，策略本身未再修改。

本轮以 `aae4147f1e246c5fb115060ef484df625b611e3d` 为审计基点。用户明确授权
替换原 CPU 10%/20% 硬门槛；这是项目测量质量策略，不是老师规定。未修改系统设置。
当前执行证据根为 [`20261010-143415`](../evidence/p3_resource_policy/20261010-143415/)。
最终执行状态以该目录中的原始操作、独立验收及本文后续结果为准，不把预提交测试当作正式实验。

## 集中策略与适用范围

唯一配置为 [`resource_policy.json`](../configs/resource_policy.json)，版本
`2026-10-10-cpu-admission-v1`；规范化 JSON SHA-256：
`e191aee4348fa5501bb923dbf1be35741a188c738ebf6fdb4863bc91b0be5671`，
文件字节 SHA-256：`0b423aab2e40b4bc65df5d3d3a3969d54d819eaf36ecaf7ad22bf95f0297ab5d`。

| 用途 | CPU 五次原始采样（间隔仍为 1 秒） | 其他硬条件 |
|---|---|---|
| Recovery | 超过旧均值 10% / 单次 20% 仅警告，不拒绝时钟诊断 | Windows/WSL 可用内存各 ≥2GiB，WSL 根盘空闲 ≥1GiB，来源/数据/超时有效 |
| Formal | 均值 ≤30%，单次最高 ≤60%，同时满足 | 同上 |

这是**每个配置启动前**的背景负载准入，不限制矩阵程序运行时自身 CPU。
保留所有读数、均值、最高值、内存最低值、用途、版本、配置哈希、逐项判定及拒绝原因。
PowerShell 只采集，通过 [`autotuner.resources`](../autotuner/resources.py) 的同一判定实现
输出严格 JSON；主控、session/campaign 运行器和后处理重新核验原始数据与来源，而非信任 PASS。
未知用途、空/缺失/非有限或不可能的数据拒绝；Recovery 记录不能冒充 Formal。
运行中 Snapshot 仅为资源披露，仍不用于事后删除慢样本。

Formal 门禁每次配置等待预算 **120 秒**，包含采集、重试间隔及保存开销；单次采集上限
60 秒且不超过剩余预算，重查间隔 10 秒。拒绝时记录具体原因与耗时，超预算安全保存暂停。
旧 v2 记录用其各自保存的原协议读取，历史 REJECT 保留，不以新规则追认。

## 身份迁移与不变部分

新 measurement schema 为 3，规范化哈希
`df08b97fc86f8940ec046d797826df2ea94f98031a0bc34f8e02c81685698238`；
campaign schema 为 2，辅助批次/恢复证据 schema 为 3。真实新内容提交先于执行，
新归档路径、Git blob、执行字节/LF SHA、session ID、campaign 与资源用途通过参数及 manifest 绑定。
支持 `campaign --initialize-only --session-id ...`：核验源码/编译器并建立空检查点，不运行矩阵。

旧 `e308bfb873e6811c50ad685a979af345302fda8d` 归档、session
`dc1c292900654d44b36a72548b95a610`、原 campaign、3 个完整配置、23 条执行及 3/2 条部分组
封存保留。旧 PAUSE_REQUEST 不手动删除；本轮不再恢复旧 session，不拼入任何旧分数。
新版只有 fresh 正式样本；可复用身份验证后的构建/reference，不用性能缓存凑重复。

教师 C 原件、工作 C/头文件、core/measurement/search、20 配置空间及搜索协议保持不变。
输入仍 n=4096、random、种子 20261008，1 次成功预热 +5 次 fresh 测量，中位数计分，
任意失败不对成功子集计分；容差、超时、MONOTONIC 核心计时及搜索自身观测限制均不变。
旧 Grid 仅为带计时/资源限制的历史参考，不自动重跑 Grid、不按比例校准。
若后来比较其推荐 O1/s128 的同条件表现，必须单独 fresh 复测，不能声称新条件下全局最优。

## 本轮执行前声明

从准确的新提交导出干净归档：无 .git、初始无 pycache、移除 PYTHONPATH；单独空缓存
完成 CLI/20 唯一配置、针对性回归和 n=17/O2/s8 实际 fresh 正确性验证。
不重复历史 160 正确性案例、834 次诊断或长 Grid。

本轮仅授权一次 recovery：A/B 各 10×3 秒，共 20 区间；先保存 policy/manifest 再采集。
探针及判据文件不变，MONO/RAW 仍 `abs(MONO-RAW) <= 0.005 + 0.01*RAW`，
REALTIME/RAW 和 Windows **同一次完整调用** UTC/QPC 仍为原容差；整数纳秒先相减再换秒。
Windows 全程与 WSL 内部区间范围不同，不做相等比较。NTP 同步状态只读保存，不再为硬前提；
不再 resync、不更换服务器/clocksource/内核/机器。A 失败仍保留 B，结束后不重复探测直到通过。

仅全部时钟、来源、新 Formal 门禁通过才恢复**新** session 首种子 random/greedy 各 12 个唯一配置，
4/8 是同一轨迹前缀，候选按既有规则去重独立复测，不反馈搜索。串行、每 60 秒进度报告；
任意恢复失败即停止正式目标。首种子完成后交审，不扩展其他四种子或第四算法。

四项验收分开生成：evidence_integrity_pass、execution_complete、timing_checks_pass、comparison_ready。
未执行不写成通过或实测失败。成本遵循 [P3_COST_SCOPE](P3_COST_SCOPE.md)，终态调用、复测、
campaign 活动、门禁等待、放弃尝试、辅助诊断分列，嵌套范围不相加，完整端到端前缀仍未知。

## 当前交付结果

实际执行内容 `e0353bfdd20abb3bf9b33790b0d3558268621cea`，空 session
`920aee4663ff44b084cd11d35eeeadbb`。唯一一次 recovery：20/20 MONO/RAW、
20/20 REALTIME/RAW、2/2 Windows 同调用检查全部通过，冻结源码50/50匹配。
Recovery 门禁宿主CPU均值6%/最高11%，内存/磁盘通过；没有因NTP未同步拒绝诊断。
原始记录见 [recovery](../evidence/p3_resource_policy/20261010-143415/recovery/)，
[独立复算](../evidence/p3_resource_policy/20261010-143415/independent_recovery.json)。

随后新的 Formal 门禁和批前3区间通过，campaign确实被调用，**退出1、没有矩阵执行**。
WSL归档的资源PS脚本为UNC路径；本轮错误移除了基线已有的子进程 `-ExecutionPolicy Bypass`，
Windows因签名拒绝该脚本。中文GB18030 stderr触发UTF-8解码异常，资源函数又在异常
分支访问未初始化的result，导致UnboundLocalError。原始失败和只读复现（含原字节hex）保留在
[resume](../evidence/p3_resource_policy/20261010-143415/resume/)和
[diagnosis](../evidence/p3_resource_policy/20261010-143415/diagnosis/)。批后3区间也通过。
这不是CPU拒绝，也不是时钟失败。

修复恢复**基线已有且仅对子进程生效**的启动参数，未调用Set-ExecutionPolicy、改注册表、
系统策略或组织策略；资源采集改为先保留二进制流、再解析，非UTF-8错误留原字节hex、真实
退出码，启动异常退出码未知而非补0。增加该错误回归及准确新归档的WSL→Windows UNC
受控入口重放（仅合成资源数据，不冒充真实门禁）。修复提交和干净验证另绑新身份。

本轮唯一recovery额度已用。e0353bf检查只能认证其当时的session和失败调用，**不能移用到
修复后的新内容/session**，也不自行再采20区间。修复后仅验证/初始化新空session；新的正式
恢复须外部审计后重新授权一次有限recovery。旧campaign及本次失败session均保留，不改写成绩。
当前没有完整搜索轨迹、前缀结果或候选复测；修复后的实际验证与下一轮边界如下。

### 修复后的准确内容与有限验证

最终运行内容为 `7405fcc37074ab815294ba401d5cf5e8280f3d5f`，归档
`/var/tmp/matrix-autotuner-p3-policy-content-7405fcc37074ab815294ba401d5cf5e8280f3d5f`。
[干净验证](../evidence/p3_resource_policy/20261010-143415/clean-7405fcc3/summary.json)
20个捕获命令全部退出0：53项WSL针对性测试（2项Windows专用跳过）、36项Windows
测试、导入/CLI/20唯一配置、独立空缓存n17/O2/s8 fresh且289元素通过、实际初始化和
真实UNC入口受控重放。教师原件严格字节相同；50个运行文件逐项记录Git blob、实际
字节SHA及LF身份。重放为合成资源数据，不是正式资源采样或第二次时钟复核。

期间验证辅助代码自身另有路径传递错误：0fbd3b2的最后重放失败，不掩盖该entry退出1。
跨WSL Python-c字面量将Windows反斜杠加数字解释为转义；仅把测试路径改为正斜杠。
其11条错误被新运行器保留原字节/RC3，120.000162秒安全结束，未崩溃或启动目标。
随后准确7405fcc归档重放2.495秒通过。完整失败和修复证据均保留。

修复后正式空session `3768a29ade69408da4c5d0c4404ba44e`，目录
`evidence/p3_resource_policy/20261010-143415/campaign-7405fcc3/`，只初始化，0观测/0执行/0复测。
它的时钟和正式门禁**未执行**。实际e0353bf批次独立验收为 true/false/true/false；
修复后session为 true/false/false/false，其中第三项是未执行而非采样失败。
两者comparison_ready均false，尚无6行预算结果。

### 独立结论、历史保护与成本

[交付独立汇总](../evidence/p3_resource_policy/20261010-143415/delivery_analysis.json)
重新核验原始端点、运行/冻结身份、实际失败调用绑定、历史字节和原始流，不仅信任summary。
20个MONO/RAW绝对差范围0.000142–0.010402秒，0失败；REALTIME/RAW亦0失败。
Windows A/B同调用UTC/QPC为30.649647/30.647741、30.627787/30.614535秒，均通过。
批前/批后各3区间及两次宿主检查通过。未据此断言旧异常根因或校准旧成绩。

旧清单10161个evidence/code原始字节项、新近历史234个Git字节项全部匹配（分开计数，
不声明两清单的唯一文件总数）。旧冻结归档/编译器/候选/reference共32项匹配；
原检查点/JSONL/run_id/完整观测/3+2部分样本和PAUSE_REQUEST不变，无正式进程且runner锁可获取。

本轮4096目标执行、候选复测及放弃目标尝试成本均0；实际失败campaign的Windows完整
调用2.105102秒，检查点只保存0.095894秒累计活动、wait=0，异常尾段没落账，不能由0
推导资源采集无成本。外层resume57.442800秒、recovery101.456010秒，分别包含对应
门禁14.563771/15.707523秒与边界/恢复检查等，不能全部相加。
已捕获辅助命令QPC区间并集685.578757秒，含有限验证/合成重放/编译n17/初始化，排除本次
汇总及后续核验、编辑/模型/离线/推送和未捕获准备操作。逐操作/来源见汇总；失败日志保留。
旧campaign活动7120.754915秒、门禁/等待1165.348475秒不变，属于旧数据，不追加本轮成本。
所有范围按包含关系分列，完整端到端前缀成本仍unknown。

### 下一轮具体入口（本轮不执行）

先由外部审计复核，并明确授权新一次有限recovery；不把e0353bf通过文件移用到新session。
在Windows项目根目录执行（路径由[冻结新计划](../evidence/p3_resource_policy/20261010-143415/corrected_session_plan.json)给出）：

```powershell
$policyPlan = Get-Content -Raw evidence/p3_resource_policy/20261010-143415/corrected_session_plan.json | ConvertFrom-Json
$policyArgs = @('--content-sha', $policyPlan.content_commit, '--auxiliary-sha', $policyPlan.content_commit,
  '--archive-directory', $policyPlan.archive_directory, '--campaign-directory', $policyPlan.campaign_directory,
  '--git-identity', $policyPlan.git_identity, '--session-id', $policyPlan.session_id)
$policyRecovery = 'evidence/p3_resource_policy/20261010-143415/recovery-corrected-next-round'
python scripts/start_p3_first_seed.py --mode recover @policyArgs --output $policyRecovery
# 仅这次新恢复的20区间、来源/检查点、独立检查均通过后；resume还会重新执行Formal门禁
python scripts/start_p3_first_seed.py --mode resume @policyArgs --recovery-directory $policyRecovery --output evidence/p3_resource_policy/20261010-143415/resume-corrected-next-round
```

若目录已存在须选新的唯一目录，不能覆盖。只运行两条12配置首种子轨迹及候选复测。
