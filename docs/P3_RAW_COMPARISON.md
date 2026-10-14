# RAW首种子比较入口与三配置独立验证（2026-10-14）

本阶段基于`e1b3a7ee26da346efa50da564199e53ec91cccda`。只实现独立入口和进行
O3/s128→O3/s64→O3/s24验证；**不运行真实Random/Greedy搜索**。
正式P3 execution_complete / timing_checks_pass / comparison_ready均仍为false。

## 关闭的历史Grid

测量内容`3cc9e0d03ba682569fca0e91f28d364f2dab73fa`、session
`f705a488d7b442789973381e2190c944`已经关闭，不再追加或修改。
原120条记录、20组中位数、controller、claim、证书及预算全部原样保存。
O3/s24待机样本不删除、不替换、不退款，不校准成绩。
correctness_pass、timing_contract_pass、uninterrupted_execution是三个不同结论；
前两项的历史冻结检查通过，不能证明组内未暂停。

## 新入口与科学测量身份

[`raw_comparison_protocol.json`](../configs/raw_comparison_protocol.json)明确授权独立RAW比较，
不删除[`campaign.py`](../autotuner/campaign.py)原Grid-only拒绝逻辑，不恢复旧campaign。
[`start_raw_comparison.py`](../scripts/start_raw_comparison.py)是Windows QPC主控；
[`raw_comparison.py`](../autotuner/raw_comparison.py)是WSL fresh测量及轨迹状态机；
[`raw_comparison_contract.py`](../scripts/raw_comparison_contract.py)独立复算证据。

新执行内容SHA和新session写入准确归档的plan；继承测量内容3cc9e0d独立记录。
教师原件、工作C、输入/参考、容差、20空间、编译选项、RAW契约、测量及搜索源码、资源v2
保持原字节。继承科学协议的规范化哈希分别为measurement `df2f365a…`、timing `936591ac…`、
resource `38e07371…`，完整值在新协议及plan中。
有效target保留已审核的科学源码绝对路径，以复用经哈希核验的build/reference；
新cache仅将这两个目录链接到已核验缓存，performance目录独立，不读取旧性能样本。

初始化分别创建新的空validation和search session，均不执行目标或reference生成。
搜索入口需要额外精确绑定SHA/session/协议的授权文件，本阶段不提供该文件。
Random与Greedy各12唯一配置，4/8/12是同一12轨迹的前缀；原无放回及七邻居实现不改。
每个策略只收到自身config/classification/score，不能收到Grid、验证、复测或另一算法数据。
各算法前缀候选内部去重复测，跨算法不共用样本；复测不反馈、不改变已完成轨迹。

## 连续性与固定预算（采集前声明）

Windows控制线程申请ES_CONTINUOUS|ES_SYSTEM_REQUIRED，核验非零返回，finally中同线程释放。
这是临时请求，不更改全局电源策略，**不能保证阻止用户合盖**。运行时需接电、开盖。
保存System日志起始RecordID，按新RecordID保存Kernel-Power 42/506待机、107/507唤醒及
Power-Troubleshooter 1原始消息/XML。日志回卷、启动身份变化或查询失败不能冒充连续性通过。
任何组内待机保留原样本和成本，标受扰、不接纳完整组并停止，不重试或补跑。

组测量在WSL完成启动、身份及门禁检查后发READY；宿主QPC紧贴RUN发送及FINISHED接收，
来宾整数RAW端点包围ConfigurationEvaluator.evaluate。两者覆盖同一评估操作，宿主另含传输
包络开销；两者均不包括WSL启动、setup、门禁及组边界探针。没有猜测开销扣除。
`abs(QPC包络−评估RAW)>max(30秒,评估RAW×5%)`即停止核查，不能用其校准核心成绩。

一次fresh准入：默认libc、不绑核、持续原生进程，固定10亿次短工作后100亿次长工作，
共2区间，120秒探针预算。原L/U及保守RAW范围、20ms通信/读取跨度、5ms+1%U容差均不变。
独立审计从整数端点复算，新证书绑定新SHA/session/初始checkpoint/比较协议，旧Grid证书不适用。
组前后各一个fresh短探针，矩阵核心计时外串行执行；MONOTONIC仅警告。

验证活动QPC预算固定3600秒，从准入资源检查前至收尾，包含门禁、探针、setup核验、18次目标、
正确性和连续性检查。独占claim禁止重启重置预算；失败即停，不循环准入或重测失败组。
资源策略v2不改，Formal等待含采集/重试最多120秒。搜索预算建议独立43200秒（12小时），
仅作为后续外审方案，不是当前执行许可；新阶段不借旧Grid余量。

## 验证与复现入口

19项新受控回归只使用假执行器：唯一性、前缀/候选映射、自身观测隔离、fresh/replay、
身份/证书、独占预算、待机/时长差及异常释放。没有重复历史110项或额外n17。

```powershell
python -B -X utf8 scripts/verify_raw_comparison_code.py
# 先提交运行代码，再导出准确SHA；输出路径必须全新
python -B -X utf8 scripts/prepare_raw_comparison.py --content-sha <完整SHA> --output <新目录>
# 从plan.windows_archive_directory的准确归档运行，仅validation_plan
python -B -X utf8 scripts/start_raw_comparison.py --plan <validation_plan.json>
python -B -X utf8 -m scripts.raw_comparison_contract --plan <validation_plan.json> --output <新审计.json>
```

实际执行计数、结果、成本、停止原因和历史保护见本阶段证据入口；以下待实际运行后填写，
不得把假执行器成绩、旧Grid或未执行值当成本轮18次验证结果。
