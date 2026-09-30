# `compress` 三次重复实验

同一 WSL2 Ubuntu 24.04 环境、同一 OpenJDK 7u75 RI、同一 SPECjvm2008 1.01 安装及 `-bt 16`。三次均运行 `java -jar SPECjvm2008.jar --base -bt 16 compress`，保留默认 120 秒预热和 240 秒正式迭代。由于只选择了一个 workload，SPEC 报告均写明 `Run is valid, but not compliant`；这些是稳定性分析数据，不是完整 Base 综合成绩。逐次命令、时间、得分及结果编号见 [CSV](repeat_test_results.csv)，原始输出见 `../logs/repeat_compress_run{1,2,3}.log`，对应 raw/TXT 位于 `../specjvm2008/results/SPECjvm2008.008` 至 `.010`。

| 运行 | 正式 `compress` 得分 (ops/m) | 预热值 (ops/m) | 结果目录 |
|---|---:|---:|---|
| Run1 | 557.34 | 550.34 | `SPECjvm2008.008` |
| Run2 | 545.48 | 545.17 | `SPECjvm2008.009` |
| Run3 | 522.15 | 548.53 | `SPECjvm2008.010` |

平均值 541.657 ops/m；最小值 522.15、最大值 557.34，极差 35.19 ops/m（均值的 6.497%）；样本标准差 17.904 ops/m，变异系数 3.305%。三次按时间顺序下降，Run3 的正式值也低于其预热值。以上统计由 [CSV](repeat_test_results.csv) 中的三条 SPEC 得分计算，没有使用预热成绩代替正式值。

每次都是新的 JVM 进程，即使配置相同，也会重新经历类加载、JIT 编译、堆扩张与垃圾回收；120 秒预热不能保证这些行为在三次运行中完全一致。WSL2 的宿主调度、其他后台任务、CPU 动态频率和温度也可能改变可用计算资源。此次没有采集 GC 日志、温度或频率时间序列，因而不能确定下降的具体原因，更不能把趋势归因于某一种机制。重复结果说明报告单个成绩时应同时保留完整配置和波动范围。

工作负载和预热机制依据：[SPECjvm2008 User’s Guide](https://www.spec.org/jvm2008/docs/UserGuide.html)。
