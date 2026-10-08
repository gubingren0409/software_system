# P2 时钟域核查（不修改测量协议）

2026-10-08 20:38核对O0/s24原始日志时发现：目标CLOCK_MONOTONIC与Python
process_wall_seconds相符，但GNU time/UTC间隔更短。20:41--20:49进行限定成本的
只读诊断；未改系统时钟、NTP、clocksource、频率策略、目标源码或冻结协议。

## 已验证事实

- O0/s24第四次测量：核心476.844574051秒、Python单调进程墙钟478.863255638秒，
  GNU time elapsed为7:38.07，UTC before/after间隔约458.09秒。
- 五个1秒探针的realtime与monotonic间隔相近，RAW约为前者的97.2%。
- 十个3秒探针中第四个：monotonic=3.010248239秒，realtime=1.762572137秒，
  二者差1.247676102秒。这是时钟间隔不一致的直接证据，不是矩阵结果错误。
- 长探针的睡眠段monotonic合计约30.079秒；包住完整WSL调用的Windows
  Stopwatch为29.7486535秒、Windows UTC为29.7508593秒。包装耗时还含启动、
  状态查询与落盘，不能直接用一个比率校准目标程序所有样本。
- 当前WSL clocksource是tsc；timedatectl显示NTP=yes、NTPSynchronized=yes。
  查询timesync-status时Offset=-1.608300秒，Frequency=-38.339ppm。该值不能直接
  解释全部间隔差，根因未确认。
- x86_64下对四种clock_id直接syscall与glibc读取比较，差别只有调用先后的微秒级，
  未发现简单绕过vDSO即可消除差异的证据。

## 解释边界与处理

Linux定义允许REALTIME因同步发生跳变；MONOTONIC避免这种不连续跳变但仍可受
频率校正影响；RAW不应用该类校正。因此RAW与MONOTONIC不同不自动证明哪一个
接近真实物理时间。[Linux时钟文档](https://man7.org/linux/man-pages/man2/clock_gettime.2.html)、
[内核timekeeping说明](https://docs.kernel.org/core-api/timekeeping.html)。

本轮不引入事后校准系数、不删掉较慢样本、不换时钟或更改系统级设置。继续完成
冻结schema 2协议下的Grid；所有分数明确是该环境中的CLOCK_MONOTONIC核心时间，
而非已校准的物理时间。这个限制会影响绝对秒数及较小性能差异的解释，需由外部
审计者裁决是否在后续更稳定的时钟环境中新建session复测。不能据此声称全局最优、
环境完全稳定或精度已通过独立校准。

## 原始证据

- `../evidence/p2/environment/clock_probe_20261008.json`：初次短探针、命令与系统状态。
- `../evidence/p2/environment/clock_probe_long_20261008.json`：逐间隔四时钟读数。
- `../evidence/p2/environment/host_clock_bridge_20261008.json`：Windows包装命令、
  完整stdout/stderr、退出码和两个宿主计时源。
- `../scripts/check_p2_clocks.py`、`../scripts/check_p2_host_clock.ps1`：复现入口；
  正式运行器不导入、不调用这些诊断脚本。
- 初次未参数化探针由原版本恢复并按当时记录的哈希核验，字节快照在
  `../evidence/p2/environment/clock_probe_sources/check_p2_clocks_initial.py`，SHA-256为
  `a62eb06e0d20b473f990c53f047c3faa01971cb1201a3bd16f02f132b45c1beb`，与初次JSON
  一致；快照只供来源核验，正常复现使用scripts中的参数化入口。
- `../evidence/p2/environment/clock_syscall_comparison_20261008.json`保留实际执行的
  只读Python命令、原始stdout/stderr和退出码。
