# 正式 RAW Grid v1：协议冻结与资源阻塞的部分结果

## 当前：f19f9f84之后的一次分段续跑（2026-10-12）

测量内容、session及以下首段原始结果不变。新外层助手已单独冻结为7a8dc17f；
一次四小时授权窗口在Formal预检耗尽后停止，新增时钟区间/矩阵调用/配置均0。
原五组、30条字节前缀、controller、初始检查点和证书全部保持。
两段活动包络只累加各自QPC时长：13883.0691008+133.3351975=14016.4042983秒。
当前仍5/20、30/120；不得重复调用领取新窗口。
详见[分段方案、完整读数、预算及审计](P3_RAW_GRID_SEGMENT.md)。

## 首段历史记录（已获f19f9f84外审接受）

本轮基点 `3755c4a9d1c387e891fdcc89151250020895370a`，用户已接受22区间候选诊断，
授权修复衔接、一次新恢复和通过后新的20配置Grid。不是P3算法比较完成。
候选协议 `configs/raw_timing_protocol.json`、教师原件、历史成绩/失败/暂停标记保持原样；
`d6811cad` / `2c270825458a4857a5ac9df5aadf597b` 仍空，不写观测。

## 协议与身份

新增 [`raw_formal_timing_protocol.json`](../configs/raw_formal_timing_protocol.json)，
版本 `2026-10-11-raw-formal-v1`，measurement schema6、target schema2绑定同一规范化哈希。
RAW结果schema2、整数先相减和double精确round-trip校验不变；工作C仅改协议版本常量，
核心循环、输入、独立reference和误差容限不变。辅助MONOTONIC保留但不准入、不校准。
新版缺失/null/错误binding启动前拒绝；旧schema1–4只能使用明确历史MONOTONIC契约。
旧契约测试读真实历史协议，不从新版删除binding。候选schema5继续禁止正式准入。

effective target在原配置目录解析所有源码及timing协议路径，之后写入绝对路径；
独立输出目录不需要偶然存在同名协议。旧P3入口不能运行新RAW；新入口
[`start_raw_grid.py`](../scripts/start_raw_grid.py)只实现本轮Grid，campaign继续禁止。

先提交最终运行内容，再从准确SHA导出Windows及WSL干净归档。
Git blob身份、执行字节SHA256及换行分别保存；教师C必须原字节相等。
新session初始化只查询身份/编译器，不编译或执行矩阵/生成reference。
初始化检查点另存不可变 `initial_checkpoint.json`。无旧观测/性能缓存导入。

## 一次恢复（必须先于4096）

原生探针保持已接受的volatile uint64固定工作量；libc、不绑核。
十个短区间各10亿次，第5、10个后各加100亿次长区间：共12区间、300亿次更新、
50条响应（HELLO + 每区间MODE/READ/WORK/READ + QUIT），同一持续存活PID。
不靠sleep或来宾时钟结束工作。每条原始流和JSONL立即flush。
发送前先写进度，然后紧贴write/flush记录send QPC；读取响应立即记recv QPC，
再解析、写文件。原始记录不删除、不补采。

`L=(He_send-Hs_recv)/Frequency`，`U=(He_recv-Hs_send)/Frequency`；
RAW保守范围 `[RAW1_end-RAW2_start, RAW2_end-RAW1_start]`。
通信不确定性、RAW端点读取跨度各≤20ms，`a=5ms+1%*U`，
整个RAW范围须在 `[L-a,U+a]` 内，另报未加容差 `[L,U]`。
整数端点决策复用已审checker，所有区间完整、可判定、RAW通过才签发。
来源/content/session/初始检查点/协议/资源及原始证据都绑定到新证书；独立重算而非读PASS。
候选22区间、旧恢复证书绝不能代用。
Recovery资源v2原规则，CPU只警告；资源与采集整体QPC预算240秒。
资源拒绝、任何时钟失败/过宽/超时都保存并停止，不再次recovery。

## Grid及停止规则

恢复开始起Windows QPC总预算8小时。n4096/random/seed20261008，原20配置；
固定优化外层O0/O1/O2/O3，块内层8/16/24/64/128。每配置1预热+5fresh，中位数。
无失败时120次矩阵调用，reference生成/探针/测试另计。本轮不额外做Grid最优复测，
重复波动来自每组5个样本；后续同协议算法比较/独立复测另授权。

setup和每组前Formal v2：五样本CPU平均≤30%、峰值≤60%；宿主物理及commit余量≥512MiB，
宿主物理<2GiB警告；WSL可用≥2GiB，根盘≥1GiB。每次等待包含采集/重试最多120秒。
不以NTP、MONOTONIC差异等新增门槛；运行中目标自身CPU不受准入门槛限制。

每组前后各1个fresh默认libc/不绑核、固定10亿次的QPC/RAW有界检查（各60秒预算），
位于矩阵计时之外、与矩阵串行。before绑定组index/attempt，after另绑定实测组文件SHA。
六次成功原始测量只有同时通过两侧检查才进入completed和Grid表。
组后检查失败保留六样本及临时聚合，不记完成/最佳；任何执行失败不筛成功子集。
不自动重试失败组，不拼部分组；完整组恢复须重验六原始样本、来源/协议/证书和组检查。
资源/时钟/测量/预算失败立即保存检查点停止。每60秒保存及报告进度。

## 成本和验收口径

核心/验证/进程/配置组/新setup可信来宾成本用RAW；外层调用、资源等待、时钟采集及8小时
预算用Windows真实QPC。reference C自己的generation_seconds及历史MONOTONIC字段仅原始
未校准元数据，不能当可信总调优成本或用于校准RAW。
核心/验证在进程内，进程和lookup/I/O在组内，setup/组/门禁/探针在外层QPC内，不能全部相加。
测试、干净导出、身份核查等辅助操作单列，不混进120个矩阵样本。

独立审计 [`audit_raw_grid.py`](../scripts/audit_raw_grid.py)重验实际源码/编译器/二进制/reference、
恢复证书、20唯一配置及原始JSONL/流、fresh属性、正确性/RAW端点、组两侧、统计和成本。
`grid_complete` / `grid_timing_checks_pass`与P3的 `execution_complete` /
`timing_checks_pass` / `comparison_ready`分开：本轮没有Random/Greedy，P3三项仍false。
旧Grid继续仅历史参考，不混表、不按比例校准。

本轮证据根：[20261011-021601](../evidence/p3_raw_grid/20261011-021601/)。
最终运行内容 `3cc9e0d03ba682569fca0e91f28d364f2dab73fa`。
WSL归档 `/var/tmp/matrix-raw-grid-content-3cc9e0d03ba682569fca0e91f28d364f2dab73fa`；
Windows归档位于本机Temp同SHA目录，完整路径、Git/字节SHA见
[final-content/plan.json](../evidence/p3_raw_grid/20261011-021601/final-content/plan.json)。
新空Grid session `f705a488d7b442789973381e2190c944`，初始化执行矩阵/reference均0。
双干净归档各110项相关测试，Windows跳过2项、WSL跳过3项，适用项均通过；
CLI及20唯一配置通过。独立空缓存一次n17/O2/s8 fresh、289元素及RAW契约通过，
该诊断矩阵1次/reference生成1次另计，不是4096或正式Grid观测。
[干净验证记录](../evidence/p3_raw_grid/20261011-021601/final-content/clean_validation.json)。
预冻结3e41eb5归档和计划保留，未初始化/采集/执行矩阵，已由最终3cc9e0d替代。
以下为冻结之后的实际执行结果；不将未执行项补写为成功。

## 实际结果（2026-10-11，停止交付）

状态 **RAW_GRID_RESOURCE_BLOCKED / PARTIAL**。唯一恢复入口退出0，准确归档独立复算
12/12区间、50响应、同一原生PID1905全部完整，`recovery_eligible=true`。
恢复资源+采集外层QPC125.2688552秒，原生96.4690597秒（包含关系，不相加）。
恢复host最低3618062336B、commit余量23163277312B、WSL可用6271893504B，
CPU平均5.6%/最大8%，资源PASS无警告。不是用候选22区间代替恢复证书。

按冻结顺序完成O0的5个配置；5次预热+25次测量，共30个唯一run_id、30次fresh目标执行。
每条都returncode0、success、全16777216元素校验，最大绝对/相对误差均0，RAW整数契约通过。
每组两侧各一fresh探针，10/10通过。累计本轮新探针22区间、110响应、11个正常退出原生进程；
与上一轮候选的22区间是两套不同证据。全部22个RAW保守范围也落在未增加容差的[L,U]内。
最大通信不确定性13.591ms，最大RAW读取跨度160ns，RAW失败0。
MONOTONIC辅助警告9个：恢复零起点8/9；O0/s16两侧、s24两侧、s64两侧、s128组后。
全部保留，不作RAW硬门槛、不校准或继续追查原因。

| 已完成配置 | 五次测量中位数/RAW秒 | CV（样本标准差/均值） | MAD/RAW秒 |
| --- | ---: | ---: | ---: |
| O0/s8 | 445.151418584 | 0.5110% | 1.159226646 |
| O0/s16 | 458.686277198 | 0.1134% | 0.369688772 |
| O0/s24 | 439.467950311 | 0.6709% | 2.900536455 |
| O0/s64 | 422.557072653 | 0.2796% | 0.216587803 |
| O0/s128 | 416.593961898 | 0.2536% | 0.557350426 |

**已测五项中**最低中位数是O0/s128，不能称20配置最优或与旧Grid作同协议比较。
O1/O2/O3的15个配置全部未执行；不产生新Grid完整热力图，不用旧值或零填补。
[五行有效表](../evidence/p3_raw_grid/20261011-021601/final-content/grid-f705a488/grid_summary.csv)、
[20槽状态表](../evidence/p3_raw_grid/20261011-021601/final-content/grid_status_20.csv)及原始JSONL
分别保留真实分数、未执行状态和全部五重复值。没有独立候选复测或搜索轨迹。

### 为什么停止：资源，不是RAW

O1/s8前Formal门禁的三次完整采集均仅因host_memory拒绝：

| 采集 | 最低Windows可用/bytes | 最低commit余量/bytes | WSL可用/bytes | CPU均值/最大 |
| --- | ---: | ---: | ---: | ---: |
| 0 | 521515008 | 16061382656 | 4782800896 | 6.4% / 19% |
| 1 | 437022720 | 16142254080 | 6348546048 | 8.8% / 24% |
| 2 | 189259776 | 16507396096 | 6426779648 | 19.2% / 30% |

宿主512MiB底线为536870912 bytes；以上不能用WSL容量或整个Vmmem工作集相加补足。
第四次采集在剩余预算内超时，退出1、timed_out=true、stdout为空，判为未知/拒绝而非通过。
门禁等待120秒预算耗尽；实际QPC120.5548004秒，约0.555秒是轮询/终止收尾越过边界，
不是继续启动正式目标的额外预算。主控退出2，停止原因为`Configuration Formal resource wait exhausted`。
原始[门禁manifest、四次操作及原始读数](../evidence/p3_raw_grid/20261011-021601/final-content/grid-f705a488/group_checks/4361ea9b921f4f668e6eaa6952757169/resources/)
全部保留。内存变化原因未知，没有结束用户应用、修改资源v2或重采recovery。
O0/s8曾在52.9658347秒内从host_memory拒绝恢复通过，旧REJECT仍保留；
其余组也保留host低于2GiB警告，不能把门禁通过称为性能稳定性保证。

30次目标的GNU time实测最高RSS394852KiB（约385.6MiB），不是整个系统峰值。
目标major faults和reported swaps均0；保存的WSL vmstat pswpin/pswpout均0，不能外推到未采时刻。
运行中WSL可用最低4232232960B；408份宿主快照均可读，WSL约5秒/宿主约30秒采样，非连续保证。
全量分页/交换、运行前后和快照见[resource_quality.json](../evidence/p3_raw_grid/20261011-021601/final-content/resource_quality.json)。

### 审计、历史保护和成本

[准确归档独立审计](../evidence/p3_raw_grid/20261011-021601/final-content/grid_audit_archive.json)
无证据错误，evidence_integrity_pass=true；恢复eligible及全部已采RAW检查通过。
grid_complete=false、grid_timing_checks_pass=false：15个配置及其两侧检查未执行，不是已采RAW失败。
P3 execution_complete、timing_checks_pass、comparison_ready仍false，因为没有两算法正式比较。
新session五完整组、无活动组/部分执行/放弃组；checkpoint ready不是完整Grid完成标识。
初始化matrix/reference0；本轮小矩阵1/reference1、正式矩阵30/reference生成1分别计数。

教师原C字节SHA256为`188d011109c4470e1f41829216e8677a5c2d8f2b7c8a44215652320dbdf6de15`；
工作C为`eda8461e3992e1a4a44737d29969ca24fddd3fba85035bb1b1e31559273110e1`。
正式timing规范化JSON哈希`936591ac5303e832788dc5f35ecac4c7807f52c3662666f13ef35f187b320847`，
measurement哈希`df2f365aec3fbce2b195a739b452234d9789b4fea3be3b6a0211549f0de2fb61`；
资源v2哈希`38e073716eafc5356d775509414018415bba05ac6e87e4e29be93663b90da9d9`未改。
文件字节SHA与规范化JSON哈希不是同一口径，逐文件Git blob/执行SHA/CRLF见plan。
GCC13.3.0实际路径/usr/bin/x86_64-linux-gnu-gcc-13，编译器SHA为
`1b99826121ae6682a634e5efe09bd3e3df58ce58e0b28f849114ab5b89139c26`。
探针二进制SHA为`51170d65035e84f6a3345f6b2189f48c8b08e54e9f9195b0cd35a9baa93aa3bd`；
四候选/独立reference构建与数据哈希见session/manifests和references，二进制与大数据留在WSL缓存。

11017个历史文件、53个原d681归档文件和三个campaign字节/检查点/原始ID保护通过：
d6811cad和7405fcc3仍空，e308bfb仍3完整/23原始（18完整组执行、5部分执行），暂停标记未动。
旧Grid、旧失败及旧候选证据不改标，不迁移或按比例校准。

实际成本（下列存在包含关系，不能全加）：

- 恢复开始至安全停止外层QPC：13883.0691008秒，约3小时51分23秒，含辅助衔接排错间隔。
- 唯一Formal调用外层QPC：13543.6365919秒；含setup、门禁/等待、组检查和测量。
- 五个完整配置评估RAW累计：13182.402289135秒；含核心13091.892078813秒、验证45.03772941秒等嵌套成本。
- setup RAW43.698116229秒，内含四级构建4.109816197秒和独立reference39.588301114秒。
- Formal门禁含采集/等待QPC248.3801606秒；仅纯等待时间未独立计量。
- 所有原生探针QPC132.7716517秒，内含恢复原生96.4690597秒；恢复资源+采集125.2688552秒另为外层范围。
- 搜索、候选复测和放弃目标执行成本本轮均0；干净验证/导出/后处理/推送等辅助操作单列，不作为核心成绩。

[costs.json](../evidence/p3_raw_grid/20261011-021601/final-content/costs.json)与
[逐操作命令、QPC、退出码](../evidence/p3_raw_grid/20261011-021601/closed_operation_verification.json)
保留来源。reference自身generation_seconds是MONOTONIC原始元数据，不用于可信总成本。

两次辅助CLI调用失败原样保留：直接脚本缺包导入根；随后-m调用仍被capture的ROOT固定到工作区，
九个Git内容相同但LF/CRLF不同的文件被严格字节审计拒绝。改从准确归档导入capture并以归档cwd
运行模块入口后，同一原始恢复独立重算通过，再开始唯一Formal调用；未改冻结字节或重采。
收尾第一次误读自身尚未闭合的operation，原脚本/日志另存；只修正派生助手并重新后处理，
没有矩阵、reference或探针执行。见[修正来源和原失败索引](../evidence/p3_raw_grid/20261011-021601/final-content/auxiliary_invocation_correction.json)。
真实终端stdout/stderr和退出码已存；未捕获真实终端截图，不制作或为截图补跑实验。

## 下一步入口（本轮不再执行）

先外审以上部分结果及资源原因。只读复算必须从准确Windows归档运行，避免工作区行尾/导入影子：

```powershell
Set-Location -LiteralPath 'C:\Users\28489\AppData\Local\Temp\matrix-raw-grid-3cc9e0d03ba682569fca0e91f28d364f2dab73fa'
$rawGridPlan = 'E:\software_system\project01\evidence\p3_raw_grid\20261011-021601\final-content\plan.json'
$rawGridReview = 'E:\software_system\project01\evidence\p3_raw_grid\20261011-021601\readonly-review-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.json'
python -B -X utf8 -m scripts.audit_raw_grid --plan $rawGridPlan --output $rawGridReview
```

当前部分Grid审计退出2是未完成状态，须同时读取errors为空及完整性true，不能读退出码认作计时失败。
后续运行入口为该归档`scripts/start_raw_grid.py --plan <同一plan> run`，但必须另获续跑授权、
先封存本轮controller/审计/检查点，核对原恢复与QPC同一epoch/频率及剩余8小时预算、资源门禁。
不得重置总预算或把过期恢复当新证书；若原窗口耗尽，先交外审决定新session/恢复安排，不自行拼成绩。
本轮已停止，无自动第二次recovery、无Random/Greedy、无额外Grid。
