# 与 SPEC 官方 Base 结果比较

参考结果：[SPEC 官方 Base Report：Sugon I620-G20，2015-02-23 首次发布](https://www.spec.org/jvm2008/results/res2015q1/jvm2008-20150120-00018.base/SPECjvm2008.base.html)；[Summary Report](https://www.spec.org/jvm2008/results/res2015q1/jvm2008-20150120-00018.html)。该结果明确标注 `Run is compliant`，采用 SPECjvm2008 1.01。查阅日期：2026-09-30。为便于离线复核，保存了[官方 Base 报告网页快照](official_reference_base.html)，SHA-256 为 `8472daef33df919535faf0b21b02b7ecc3a8c72b92bd8f49002e56d4faf016b3`。本机数据来自 [SPECjvm2008.007 文本报告](../specjvm2008/results/SPECjvm2008.007/SPECjvm2008.007.txt) 与 [实测环境记录](../environment/environment_info.txt)。

## 环境对照

| 项目 | 本机实验 | SPEC 官方结果 |
|---|---|---|
| 综合 Base 分数 | 421.24 ops/m | 853.15 ops/m |
| CPU | AMD Ryzen 9 7940HX，x86-64 | Intel Xeon E5-2660 v3，x86-64 |
| 核心 / 逻辑 CPU | 16 / 32，单 CPU | 20 / 40，双 CPU |
| Benchmark 线程 | 16 | 40（多数吞吐项；Sunflow 为 20） |
| 主频信息 | WSL `lscpu` 未报告 MHz；[Windows WMI 采样](../environment/host_cpu_comparison.txt)：当时 1984 MHz、报告最大 2401 MHz | 官方报告标称 2600 MHz，CPU 名称注明最高 Turbo 3.30 GHz |
| 内存 | WSL 分配 7.4 GiB，另有 2.0 GiB swap | 256 GiB |
| JVM | OpenJDK 7u75 RI，HotSpot 24.75-b04，默认参数 | Red Hat OpenJDK 7，HotSpot 24.45-b08，报告无 JVM 命令行调优 |
| OS | Windows 11 宿主上的 WSL2 Ubuntu 24.04 LTS | Red Hat Enterprise Linux 6.5 |
| 运行类别 | 完整 Base，SPEC 报告合规 | 完整 Base，SPEC 发布报告合规 |

## 结果对照

以下均为两份报告列出的同名 workload 或 workload 组，单位为 ops/m。倍率为“官方 / 本机”，按公开得分直接计算，未按线程数或频率做规范化。

| 指标 | 本机 | 官方 | 官方 / 本机 |
|---|---:|---:|---:|
| 综合 Base | 421.24 | 853.15 | 2.025 |
| `compress` | 551.55 | 1225.96 | 2.223 |
| `derby` | 820.63 | 1705.74 | 2.079 |
| `sunflow` | 350.25 | 491.28 | 1.403 |
| `startup` 组 | 26.74 | 37.86 | 1.416 |
| `scimark.large` 组 | 90.84 | 159.77 | 1.759 |
| `crypto` 组 | 676.52 | 2876.14 | 4.251 |

## 差异解释与边界

官方机器大多数吞吐项使用 40 benchmark 线程，本机正式 Base 固定为 16；前者还有 20 个物理核心和 256 GiB 内存。并行度、可容纳的工作集与内存带宽都可能对吞吐有利。`startup` 组主要测单 JVM 启动，线程数量差异不足以解释其约 1.42 倍差距，这提示 OS 启动路径、单线程行为或 JVM 实现也可能起作用，但没有单独实验可归因。

两边虽然都是 Java SE 7 HotSpot，却是不同发行构建（24.75-b04 与 24.45-b08），类库、密码学 Provider 和 JIT 细节可能不同；`crypto` 组差距最大，但仅靠总分无法判定究竟由 Provider、CPU 指令、线程数还是其他因素主导。官方 RHEL 6.5 与本机 WSL2 Ubuntu 24.04 的内核、调度和虚拟化层不同，也可能影响结果。官方 CPU 给出标称频率，本机仅取得 WMI 采样值，不能把频率比当作性能比。

因此这组比较的结论是“在各自已披露环境下，官方 Base 综合分约为本机的 2.03 倍”；它不构成对单个 CPU 或 JDK 版本优劣的受控实验。要拆分原因，需在相同线程数、JDK、OS、内存和功耗条件下逐项改变一个因素。本作业的官方结果比较只提供观察与合理假设。SPEC 对可比性和披露的要求见 [Run and Reporting Rules](https://www.spec.org/jvm2008/docs/RunRules.html)。
