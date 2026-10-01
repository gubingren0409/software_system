# `-Xmx` 选做实验三轮质量复审

复审对象：`analysis/jvm_parameter/`、`logs/jvm_parameter/`、`images/jvm_parameter/`、`specjvm2008/results/SPECjvm2008.017`–`.065` 与相关脚本。正式 Base `.007` 不属于选做数据，复审只核对其未改变。

## Review 1：正确性与证据链

- 计划矩阵为 4 workload × 4 heap 配置 × 3 次 = 48；最终生成器确认 48/48 条计划元数据、39 条有效分数、9 条失败、118,230 条 GC 事件。
- 每个有效分数均由 raw、TXT 与控制台交叉核对；解析器拒绝 OOM、`NOT VALID`、缺正式分数或不完整 raw。失败分数保持空值，不写为 0。
- Result ID 唯一且由 SPEC 自动分配；计划运行使用 `.017`–`.025`、`.027`–`.065`。`.026` 是外部会话中断的 partial raw，仅列为额外失败证据，不计入 48 次。
- derby 512 MiB 与 FFT large 512/1024 MiB 的重复失败均保留命令、时间、退出码、raw/TXT、控制台和 GC。外层退出码为 0 的 FFT OOM 仍判 invalid，避免“退出码即有效”的错误。
- `SPECjvm2008.007.raw` SHA-256 在控制器运行前后均核验为 `4ae651e312061d09760743ab9908129b633e9ce1e5b5b296c13d4a30605e05ad`；历史 `.013/.014` 只比较方向，不并入新统计。
- CSV 由原始文件机械生成；`build_optional_data.py --check` 与 `plot_optional.py --check` 通过。均值只纳入有效样本，SD 用 `n−1`，CV 和 invalid_n 明示。

结论：分数、ID、有效性和统计口径有可回溯证据；没有覆盖 `.007`，没有把选做单项混成正式 Base Composite。

## Review 2：JVM 机制推理

- `-Xmx` 被准确描述为最大堆上限，而非初始堆、实际占用或 GC collector；默认实际 `MaxHeapSize` 由 Java 7 `PrintFlagsFinal` 获取。
- 机制链限定为：容量上限可能影响自适应分代/GC 触发与 live set 容纳能力，从而关联吞吐；没有写成“更大堆必然更快”。
- compress 的低 GC/2560 MiB 低分、sunflow 的小堆 GC 压力、derby 1024 MiB 的 Full GC 区和 FFT 的 OOM 容量门槛分别解释，没有用一个机制强套四项。
- 2560 MiB 对 derby +2.900%、FFT +1.481% 均与小样本 CV 对照，不宣称稳定提升；sunflow/2560 MiB GC 更少但吞吐未超过默认，用于反驳简单单调因果。
- GC 总时间明确为整个 Java 进程的事件暂停之和，不伪称 measurement-only、CPU 时间或总 GC 开销；不完整失败进程未与完整进程求均值。
- 未采集 live-set、分配剖析、硬件计数器、频率、温度与宿主负载时序的限制已列明。

结论：解释与 Java 7 Parallel GC/ergonomics 相容，同时把观察、推断和未测因素分开。

## Review 3：报告、复现与提交质量

- README 的选做章节独立置于必做结论之后，重复声明 `.007`/421.24 不变；没有重写必做结论或把单项称为合规完整 Base。
- 设计、workload 选择、逐 workload 结果、GC、总结合并为可导航文档；三张图均由最终 CSV 生成并经视觉检查，`n=0` 明示失败而非零分。
- 控制器使用交叉配置顺序、独立 JVM、运行前时钟检查和宿主防休眠；每次命令含 `--base -bt 16`、固定 GC 选项和唯一日志路径。
- 900 秒 watchdog 是 derby 首次异常后追加的协议修正，报告明确承认并保留首次人工终止及后续自动终止证据，没有伪称事前预注册。
- 最终重放控制器逐项跳过已有 48 个 run_key 并输出 `OPTIONAL_48_ATTEMPTS_CAPTURED=true`；不会因额外 `.026` 元数据误判计划完成度。
- 复现命令、环境快照、原始结果、衍生数据、图表脚本和验证脚本均在仓库；最终提交前还需执行全套 optional/core verifier、重建 evidence manifest 并检查 Git 状态。

结论：文档集能够从结论追溯到 CSV、日志和 SPEC raw，并明确披露中断、OOM、watchdog 与小样本局限。
