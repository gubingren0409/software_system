# `-Xmx` 选做实验预注册设计

研究问题：在同一台 AMD Ryzen 9 7940HX、同一 WSL2 Ubuntu 24.04 安装、OpenJDK 7u75 RI、SPECjvm2008 1.01 与 `-bt 16` 下，Java 最大堆设置如何与四类 workload 的吞吐及 GC 行为关联？`-Xmx` 规定最大堆容量，不等于初始或实际占用；改动它可能影响可用堆、分代大小的自适应选择、GC 触发和系统内存压力，但**不预设“越大越快”**。[Oracle Java 7 `-Xmx` 说明](https://docs.oracle.com/javase/7/docs/technotes/tools/solaris/java.html)

## 固定条件与唯一有意变化

| 维度 | 协议 |
|---|---|
| 机器/系统 | 原 A2 实验机器，固定使用 `Ubuntu-24.04` WSL 发行版；每轮记录内核、内存快照和时钟检查。新实验与 2026-09-30 `.007` 不视为同一时段受控比较。 |
| 套件/JVM | 原版 SPECjvm2008 1.01；测量 JVM 固定为 `/home/gubingren/java/java-se-7u75-ri`，不改套件或 properties。 |
| 命令 | 每轮只选 **一个** workload：`java [固定 GC 记录选项] [本轮 -Xmx 或空] -jar SPECjvm2008.jar --base -bt 16 <workload>`。默认 120 s warmup、240 s measured；没有完整 Peak 或第二份合规 Base。 |
| GC 记录 | 各轮一律加 `-XX:+PrintGCDetails -XX:+PrintGCTimeStamps -Xloggc:<本地 ext4 路径>`；先单独验证 Java 7 支持。记录是**整个 Java 进程**（含 check、warmup、measurement、reporter 阶段）的事件，不伪称精确的 measured-only GC。Oracle [Java 7 选项说明](https://docs.oracle.com/javase/7/docs/technotes/tools/solaris/java.html)。 |
| 四种堆配置 | `default`（不传 `-Xmx`）、`xmx512m`、`xmx1024m`、`xmx2560m`；不改变 `-Xms` 或 collector。每种配置另保存 JVM 实际 `MaxHeapSize` 输出，避免把名义值误当实际值。 |
| 工作负载 | `compress`、`derby`、`sunflow`、`scimark.fft.large`，见[选择理由](workload_selection.md)。 |
| 重复 | 每个 workload × 配置 **3 次独立 JVM 启动**，目标 48 次尝试。轮次配置顺序：R1=`default,512,1024,2560`；R2=`2560,1024,512,default`；R3=`512,default,2560,1024`。不挑最好的一次；每轮都留日志。 |

控制器在每轮启动前比对 Windows UTC 与 WSL 墙钟（超过 3 s 则停止，不在测量中校时），并仅在运行期间防止宿主休眠。GC 日志、benchmark 输出和 SPEC 结果首先写到 WSL ext4，运行后原样拷贝到仓库；避免直接向 WSL 的 `/mnt/e` 9p 挂载写 GC 流。所有输出按 workload/config/repetition 唯一命名；绝不覆盖现有 `.007` 或 `.013/.014`。结果由套件自动分配新的 `SPECjvm2008.NNN`，将实际 ID 记录在运行索引，**不把人为目录名冒充 SPEC ID**。

Java 7 测量 JVM 的内置图表生成器可能在基准运行结束后抛出已见于课程主实验的 AWT 异常；每轮仍保留原样控制台日志与 raw，并用已安装的 Java 8u41 RI **仅对该 raw 运行 reporter** 生成 TXT/HTML。reporter 是另一进程、在计时结束后执行，不重新测量，也不以其 JVM 版本充当被测 JDK；其日志独立保存。若 reporter/TXT 不足以验证分数，该次不计入有效分数。

## 有效性与分析边界

一轮的进程退出码不单独代表有效：必须联合原始 raw、文本报告的 `Run is valid, but not compliant`、该项 warmup/正式分数、默认时长、无 `NOT VALID`/OOM，才能列为有效单项。若 512 MiB 或任何配置失败，记录命令、时间、错误、结果目录（若生成）及缺失字段；不把失败写成 0 ops/min，也不在统计中偷偷删除。若同一单元有效样本不足 3，均值/样本 SD/CV 只按实际 `n` 标注，不能声称完成最低重复要求。

统计单元是**同一 workload 内不同堆配置**。每组保留所有有效单项，计算均值、样本标准差（`n−1`）、CV；同时展示逐轮数据与失败率。比较中的观察与机制推断分开。GC 日志的总停顿时间若可从事件解析则计为“记录到的 GC 事件持续时间之和”，不等于 CPU 时间，也不自动等于整个 workload 的独立因果效应。配置可能改变 JVM 自适应堆布局或 GC 时序，且宿主负载/频率/温度与运行顺序仍可能混杂；三次重复只是波动估计，不构成显著性证明。

历史 `.013` 默认 546.46 与 `.014` `-Xmx2560m` 536.04 ops/min 仅作方向核查：它们是 2026-09-30 的**单次顺序运行**且无本轮固定 GC 记录选项，不能并入新 `n=3` 统计或当作本轮 baseline。正式 `.007` 421.24 Base ops/min 完全独立、不修改。

## 同一实验机上的执行与复算

从仓库根目录运行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File homework02/scripts/jvm_parameter/run_optional.ps1
python homework02/scripts/jvm_parameter/build_optional_data.py
python homework02/scripts/jvm_parameter/plot_optional.py
python homework02/scripts/jvm_parameter/build_optional_data.py --check
python homework02/scripts/jvm_parameter/plot_optional.py --check
python homework02/scripts/jvm_parameter/verify_optional.py
```

控制器按 `run_key` 发现已完成的 `.meta` 后跳过，因此中断后可续跑；发现仅有部分本地日志而无 `.meta` 会拒绝覆盖，须先人工核对损坏/中断原因并保存现场。`build_optional_data.py --allow-incomplete` 只用于运行中的**临时监测**，不能作为最终统计或提交完成证据。所有方法脚本记录了本机 WSL 发行版、JDK 与套件路径；迁移到另一机器需先校对这些路径，不可直接把旧结果当新复现。

2026-10-01 19:53（北京时间），控制器因外部会话中断而在计划的 `compress/default/Run3` 正式测量中停止。该次套件已分配 `.026`，但 raw XML 未闭合、没有 measured score 或正常退出码；控制台、GC、raw 与[中断元数据](../../logs/jvm_parameter/interrupted/compress__default__r3_interrupted.meta)均原样保留。它是计划外的**失败尝试证据**，不计为 Run3、不写成 0 分；恢复时重启一个全新的 JVM 完整执行同一计划单元。

`derby/-Xmx512m/Run1` 随后出现 live heap 几乎不下降的连续 Full GC，超过常规约 8 分钟的单轮墙钟时间后仍未结束 warmup。为使“失败也可复现”且防止单一配置无限挂起，从该异常被识别后统一规定每个 Java 测量进程墙钟上限为 **900 秒**，通过 GNU `timeout --signal=TERM --kill-after=30s 900s` 实施；当前已运行的首个异常轮也按从进程启动起 900 秒的相同阈值外部终止。watchdog 高于正常轮时长且仅在失效时触发；触发后保存退出状态、日志、GC 与 partial raw，分数留空。它是异常处理协议的中途补充及局限，不能伪称运行前预注册；后续所有轮次都保留命令中的 watchdog 证据。
