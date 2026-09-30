# SPEC 官方 Base 参考结果：双参照、非因果比较

2026-10-01 检索 [SPECjvm2008 官方已发表结果总表](https://www.spec.org/jvm2008/results/jvm2008/)，逐项阅读六份 Base 报告，形成 [候选清单](official_reference_candidates.csv)。公开列表只有 **6 条 Base**：前三条使用 1.00/Java 6，后三条才与本机的 1.01/Java 7 同代。因此没有为了凑“5–10 个同代候选”而混入 Peak 或别的基准。所有六条报告均标注 `Run is compliant`；本机 `.007` 仅为本地报告合规，**未被 SPEC 发布**。两份用于数值对照的官方页面保存为 [Huawei 快照](official_reference_huawei.html)（SHA-256 `35d27a41756762e642e4699a5a42846474ca57642b4f665f6d11fc28dcc41e95`）及 [Sugon 快照](official_reference_base.html)（`8472daef33df919535faf0b21b02b7ecc3a8c72b92bd8f49002e56d4faf016b3`），[核对脚本](../scripts/analysis/verify_official_data.py)检查 14 个官方分数与快照一致。

## 选择逻辑

| 角色 | 机器及官方证据 | 解释价值 | 明显差异 |
|---|---|---|---|
| 主参考：拓扑/资源尺度相对接近 | [Huawei RH 2285，Xeon E5645，Base 335.78](https://www.spec.org/jvm2008/results/res2012q1/jvm2008-20111230-00013.base/SPECjvm2008.base.html) | 1.01、Java 7、12 核/24 逻辑 CPU、24 benchmark 线程、48 GB，比 Sugon 的 40 线程/256 GB 更接近本机的 16 核/32 逻辑 CPU、16 线程/7.4 GiB WSL RAM | Oracle 7u02 HotSpot、SUSE Linux、双 socket；官方报告 `OS_TUNING` 等软件字段仍是占位符；依然不是同配置 |
| 补充参考：JVM 家族相对接近 | [Sugon I620-G20，Xeon E5-2660 v3，Base 853.15](https://www.spec.org/jvm2008/results/res2015q1/jvm2008-20150120-00018.base/SPECjvm2008.base.html) | 1.01、OpenJDK 7 HotSpot；原仓库已使用它，保留便于与旧分析核对 | 20 核/40 逻辑 CPU、40 benchmark 线程、256 GB、Red Hat OpenJDK 7u45/HotSpot 24.45-b08、RHEL 6.5，均与本机不同 |

同代第三条 [Sugon I840-G25，Base 897.23](https://www.spec.org/jvm2008/results/res2015q3/jvm2008-20150823-00019.base/SPECjvm2008.base.html)也是 OpenJDK 7，但 4 socket、40 核、40 线程、256 GB，作课堂尺度对照不优于 I620。前三条 1.00/Java 6 在候选表保留，作为筛选被排除的可追溯记录。这里未用机械“相似度总分”：Huawei 在硬件/线程尺度更有解释价值，Sugon 在 JVM 家族更接近；两者都不能被称为控制组。

## 七个同名指标的观察

数据直接来自本地 [11 组及 Composite CSV](base_result_table.csv)和逐项抄录、附源链接的 [官方报告 CSV](official_group_scores.csv)。用于比较的两份官方报告另存为 [Huawei 快照](official_reference_huawei.html)与[原有 Sugon 快照](official_reference_base.html)；[校验脚本](../scripts/analysis/verify_official_data.py)用其固定 SHA-256 及表格单元格验证 14 个官方分数。[比例图](../images/analysis/official_comparison.png)由两个 CSV 自动生成。单位 ops/min，倍率是“官方 / 本机”，**没有按线程数、频率、内存归一化**。`startup` 放在同一表是为了对照其倍率，图只画无量纲倍率，避免将它与吞吐组的绝对分数共用一个线性尺度。

| 指标 | 本机 `.007` | Huawei 主参考 | Huawei / 本机 | Sugon 补充 | Sugon / 本机 |
|---|---:|---:|---:|---:|---:|
| Composite | 421.24 | 335.78 | 0.797 | 853.15 | 2.025 |
| `compress` | 551.55 | 519.44 | 0.942 | 1225.96 | 2.223 |
| `derby` | 820.63 | 761.98 | 0.929 | 1705.74 | 2.079 |
| `sunflow` | 350.25 | 205.64 | 0.587 | 491.28 | 1.403 |
| `crypto` 组 | 676.52 | 522.70 | 0.773 | 2876.14 | 4.251 |
| `startup` 组 | 26.74 | 24.85 | 0.929 | 37.86 | 1.416 |
| `scimark.large` 组 | 90.84 | 73.14 | 0.805 | 159.77 | 1.759 |

## 能解释什么，不能解释什么

- **Composite：** Huawei 比本机低约 20.3%，Sugon 高约 102.5%；不同方向本身说明“官方机器”不是单一尺度。Composite 是 11 组几何平均，不对应单个业务事务或 CPU 核心速度。不能从 2.025 倍推出“多 4 个物理核心使速度翻倍”。
- **`compress`：** Huawei 与本机得分接近（0.942 倍），尽管前者按报告为 24 benchmark 线程、本机为 16。算法、单核能力、JVM 版本、调度/内存、CPU 代际等同时变化，不能说线程越多一定高；Sugon 的 2.223 倍仍只是其完整环境下观察。
- **`derby`：** Huawei 0.929 倍、Sugon 2.079 倍。锁、对象分配、`BigDecimal` 和数据库路径都可能改变扩展性；未测锁等待/GC，因此不能指定哪个机制解释倍率。
- **`sunflow`：** Huawei 0.587 倍、Sugon 1.403 倍，与 `compress` 倍率明显不同。官方报告中的该项目内部 benchmark 线程分别为 12 和 20，本机 raw 为 16；渲染任务并行、浮点/缓存、JVM 和架构变化同时存在。不同倍率只支持“工作负载敏感性不同”，不支持特定核心或指令优势归因。
- **`crypto` 组：** Huawei 0.773 倍、Sugon 4.251 倍，跨度最大。组分是 AES、RSA、签名验签的几何平均；不能当成 AES 单项的倍率。Provider/JCE 实现、指令路径、线程数等均可能参与；没有 provider 或指令计数证据。
- **`startup` 组：** 0.929/1.416 倍。其各子项以单 JVM 启动为主，吞吐测试的 16/24/40 benchmark 线程差异不能直接解释这个组；OS 创建进程、磁盘缓存、类加载、JVM build/启动策略可能相关，但未被隔离。
- **`scimark.large` 组：** 0.805/1.759 倍。大数据集设计对内存层次更敏感，但容量 7.4/48/256 GiB、内存带宽、并行线程和 CPU 世代同时不同，不能以倍率证明单一内存容量效应。

这些比较遵循 [SPEC Run and Reporting Rules](https://www.spec.org/jvm2008/docs/RunRules.html) 的披露/公平使用精神：每个数字保留原环境，使用“观察”而不是“某因素造成”的表述。若需拆分因果，必须在同一机器上控制 JDK、线程、数据集、OS/功耗并同步计数；拿公开服务器结果和 WSL 笔记本作比例不具备这种控制。
