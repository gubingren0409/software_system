# 一次人工续用剩余额度（9f714a72 后）

本轮基点9f714a72f2c59e75839db89a67e870d9b320fe4d；用户明确授权：
保留旧尝试已用133.3351975秒，仅使用原剩余14266.6648025秒。
不是第三窗口，不重置旧claim，不改变测量或资源协议。
正式内容3cc9e0d03ba682569fca0e91f28d364f2dab73fa，session f705a488d7b442789973381e2190c944。

预声明顺序：冻结外层助手及干净验证→锁定旧记录和五个完整组→
原Formal资源门禁（含采样/重试120秒）→一次fresh默认libc不绑核的两区间准入→
index5至19串行，每组1预热+5fresh及原两侧RAW/QPC检查。
准入固定先10亿次、后100亿次整数更新，120秒，不补采；公式、20ms和5ms+1%U不变。
资源或时钟/身份/执行/预算失败，保存并停止；不重试失败组。

新claim只记录本次人工授权已领取；原claim、原controller、initial checkpoint、证书、
五组成绩、30条样本字节前缀和上次全部失败日志锁定，不删除或改写。
每60秒保存并报告进度；本次QPC＋133.3351975秒≤14400秒，累计加第一段≤28800秒。
暂停时长仅列UTC标签，精确可信时长unknown。嵌套成本不重复相加。
本轮不运行Random/Greedy、其他种子、独立最优复测或额外小矩阵。

执行前状态见[start_identity.json](start_identity.json)。实际执行状态和审计结果将在本目录追加，
此声明本身不证明资源、时钟或矩阵执行通过。

## 实际结果：RAW Grid完整，P3比较仍未完成

辅助内容957576ca39689e9b8a723006aeb8177562e1620b，测量3cc9e0d/session f705a488不变。
[准确归档/Git/字节身份](auxiliary_freeze.json)；[20项干净受控测试](operations/clean_controlled_tests.stderr.txt)通过。
原Formal预检先仅host_memory拒绝500543488B，再通过1919221760B，总71.505736s。
通过快照CPU8.4%/24%、WSL6203023360B、commit余量24678649856B、根盘223111458816B；
低2GiB警告/原REJECT保留，[全部资源独立复算/质量证据](resource_quality.json)。
唯一fresh续跑2区间/10响应RAW通过，均落在未加容差宿主边界内；MONO警告保留。
[原始流/manifest](window/admission/)、[独立端点复算](window/recomputed_admission.json)。
新增15配置/90fresh，完整20/120唯一run_id（20预热/100测量）/40组RAW检查；
原恢复12区间、本次附件2区间另计，无新恢复证书，无部分/放弃/性能缓存/复测/搜索。
本次build/reference生成0，原reference_generation_calls=1保持。
[原测量及外层独立审计](window/independent_segment_audit.json)：evidence_integrity/grid_complete/grid_timing=true，
P3 execution_complete/timing_checks_pass/comparison_ready=false。
[20行CSV](grid_summary_20.csv)、[20行可读表](grid_table.md)、
[完整120JSONL/检查点/组文件](../20261011-021601/final-content/grid-f705a488/)、
[原测量审计](window/frozen_measurement_audit.json)。最低观测O3/s12850.996291138s、CV0.4313%、MAD0.229528039s。
没有独立复测。[实际命令/PID/退出0/QPC](operations/manual_run.operation.json)、
[真实stdout](operations/manual_run.stdout.txt)、[stderr](operations/manual_run.stderr.txt)。

## 质量限制：合盖Modern Standby

[最初监控间隔](monitor_gap.json)保留当时unknown；[原Windows事件消息](operations/monitor_gap_power_events.stdout.txt)
确认506/507、Reason:Lid，20:23:27.022–20:59:36.239（UTC标签差2169.217s）。
O3/s24测量5/run6948e9aca2aa4b8eaf4b2085ef068731内发生，核心RAW65.122054088s、
资源前后UTC跨度2234.007349s；该组六次调用QPC2593.8447413s、RAW组评估417.886870885s。
[源/样本/组检查绑定](standby_analysis.json)。冻结RAW契约/两侧检查通过不证明计算内部连续。
原运行器未触发冻结失败规则，继续最后两组；不新增门槛、删样本、替换、重测或校准。
完成与质量限制并列，不宣称稳定性或物理时间绝对准确；整段休眠继续计预算，不用UTC差退款。

## 保护、成本及只读入口

[保护与进程退出核验](delivery_verification.json)：329个原session文件、101个上轮文件、11017更早文件、
旧五组/30条字节前缀/controller/initial/证书不变，live checkpoint/CSV合法追加，实验进程均退出。
本次QPC10313.8951424s，第二段含旧133.3351975s为10447.2303399s，累计24330.2994407s。
余3952.7696601s不再使用或构成第三窗口许可。[成本包含关系](costs.json)、[闭合辅助成本去重](final_cost_index.json)。
门禁/RAW组/外包装嵌套不相加；离线审核/人工等待仅UTC标签，精确可信时长unknown。
后处理初版列表含嵌套事件查询，实际运行[源码快照](executed_sources/finalize_remaining.py)及操作流保留。
仅修正派生字段说明，另建去重索引，不改正式执行或分数；[版本说明](postprocess_revision.json)。
交付版[后处理源码](finalize_remaining.py)未重跑覆盖原操作。
[热力图](figures/p2_heatmap.png)/[波动图](figures/p2_variation.png)均来自本RAW session，不是旧P2；
[绘图实际源码/工具身份](plot_identity.json)，图片已实看，无伪造终端截图。

只读复算（不采集时钟/门禁或运行目标）：

```powershell
python -X utf8 C:/Users/28489/AppData/Local/Temp/raw-grid-remaining-957576ca-9f3uvul3/content/scripts/raw_grid_segment.py audit --authorization E:/software_system/project01/evidence/p3_raw_grid/20261012-181149-manual-remaining/window/authorization.json
```

两个claim保留，所有任务实验进程退出。本轮停止，等待外审裁决休眠限制/比较范围；
不自动搜索、重跑Grid、独立复测或扩展种子。

最终[封装核验](packaging_verification.json)及[父调用退出后的54项闭合核验](closed_packaging_verification.json)通过；
966个新增/修改文件、87条新增相对链接无缺失，无超大/缓存二进制或凭据模式误提交。
去重的已捕获辅助QPC149.5839096s（不含编辑/模型/推送，不是整轮总成本），
不叠加已含其内部事件查询的正式包络；实际运行源码及Git字节已分别核验。
