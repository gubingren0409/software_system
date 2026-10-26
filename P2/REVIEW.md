# Project 2 第一阶段交接

阶段结果：已完成待审。范围为 Checkoff Item 1、Checkoff Item 2、Write-up 1。其他排序优化及选做题留到下一阶段，官方 `sort_i/p/c/m/f` 占位实现保留，没有加入本阶段测试。

## 仓库与成果

工作仓库为 `https://github.com/gubingren0409/software_system`，分支 `Project02`。本地独立 worktree 位于 `E:\software_system\Project02`，起点为 `057d4e5a0d70e88ab3ab24db13900440dbd69ebb`。初始工作区干净，只有通用 README；未发现现成的本课程 P2 代码或结果。P1 中名称含 P2 的文件属于其内部阶段，没有复用为本项目证据。

- 正式阶段报告：[README.md](README.md)。
- 全部原始结果：[results/stage-a/](results/stage-a/)，包括六组 sum 模拟、两组 sort 模拟、十个原生排序进程、正式 Perf 数据和短测。
- 测量源码：[source/](results/stage-a/source/)，含调试信息的二进制：[binaries/](results/stage-a/binaries/)。
- 源码/二进制 SHA256：[build-manifest.json](results/stage-a/build-manifest.json)；官方版本差异：[official-source-diff.patch](results/stage-a/summary/official-source-diff.patch)。
- 可复算汇总：[summary.json](results/stage-a/summary/summary.json)、[sum CSV](results/stage-a/summary/sum-cachegrind.csv)、[正常逐次计时](results/stage-a/summary/native-trials.csv)、[热点行样本权重](results/stage-a/summary/isort-source-periods.csv)。

每个命令目录保存 `command.txt`、`metadata.json`、`stdout.txt` 和 `stderr.txt`，包含精确 argv、工作目录、起止 UTC、退出码和墙钟时长。Cachegrind 下的程序耗时仅随原始输出保留，未作为正常性能使用。所有交付材料均进入本分支，不依赖审核者读取本机绝对路径。

## 修复与失败尝试

1. 原始 Homework 的 `-always-inline` 被 Clang 18 拒绝，错误见 `original-build/homework-debug/`。仅移除公共旧参数，保留两种优化等级、断言设置和共同调试信息，每次 `--always-make` 重建。
2. 驱动按输入类型清零时间，将 `-s` 接入实际 `rand_r` 状态，使用 `qsort` 逐元素验证并在失败时退出非零；移除重复 `sort_a`，增加 `-b` 固定一个版本和恰好 `2R` 次排序。修正空区间和单元素检查，保留基线算法、接口和内部 `static`。
3. `sum.c` 只增加编译期 U/N 覆盖宏，默认值仍为一千万/一亿，种子及 `uint32_t` 累加未改。Recitation Release 增加 `-g`，仍为 `-O1 -DNDEBUG`。
4. 默认 `/usr/bin/perf` 6.18.54.1 关闭了 libelf/DWARF，能计数却不能解析符号，诊断在 `perf-diagnostics/`。改用已有的 `/usr/lib/linux-tools-6.8.0-146/perf` 6.8.12，未替换默认工具。正式四种用户态事件均实际可用，计数运行比例均为 100%。
5. Perf 写 DrvFS 返回 `Bad address`，失败目录为 `preflight/perf-record/`；改写 Linux `/tmp` 后产生 28 个预检样本，再复制进仓库。该数据最初由缺少 libelf 的工具读取，`preflight/perf-report/` 只有地址，`perf-annotate/` 虽退出 0 却显示无法注释，均未认作通过。完整工具成功读取同一份有效数据，结果在 `perf-report-symbols/`、`perf-annotate-symbols/`。正式样本为另一份 `checkoff1/perf.data`，788 个样本、丢失 0 个。
6. 本机 `cg_annotate` 把位置参数都视为 Cachegrind 数据，最初追加源码路径导致 `writeup1/annotate-debug/` 失败。改为只提供原始数据文件并自动注释，成功结果为 `annotate-debug-retry1/`。Debug 模拟和十个正常计时进程均复用已完成的有效数据，没有重跑。

正确性检查包括 Debug/Release 各六组正常规模、种子重复与差异检查、子数组和边界、无效规模拒绝，以及“输出全零但仍有序”必须退出 1。记录见 [preflight/verification.json](results/stage-a/preflight/verification.json)。`sort_a.c` 和 recitation `isort.c` 与官方 ZIP 逐字节相同。汇总脚本另检查当前源码等于测量快照、清单哈希相符、平均值匹配逐次计时、Cachegrind 全部源码计数之和匹配原始总数。

## 统计口径与限制

热点占比统一按 `perf script` 样本的 `period` 加权。第 20 行为 `1299100602 / 1362398487 = 95.35394%`，分母含 `isort` 的 779 个样本和未解析行号的样本；最高指令 `isort+0x60` 为 67.64566%。`perf annotate` 的源行摘要另显示 94.45%，两种输出存在差异，均原样保留；报告采用逐样本导出可直接复算的口径。两者最高源行与指令一致，不将占比当精确逐行时间。正式 Perf 头部显示 `max_precise=0`。

Cachegrind 自动识别的模型为 I1/D1 各 32 KiB、8 路、64 B 行，LL 为 64 MiB、直接映射、64 B 行；WSL `lscpu` 可见 L3 是 32 MiB。两者明确区分。固定 N 一百万比较 U=4096、262144、10000000、33554432；固定 U 一千万比较 N=一百万、一千万、一亿，重合项复用，共六组完整模拟。

正常排序时间为五个独立进程各自的五次平均值，再取中位数与范围；两种构建、两类输入共保存 100 条排序时间。固定逻辑 CPU 0，并交替版本顺序，未设置严格空闲门槛。WSL 与宿主调度仍会造成波动，结论只用于本组输入与环境。

本阶段无实质阻塞。当前执行环境未提供可用的真实终端截图会话，因此没有截图，以完整原始输出交审。下一阶段实现并比较 `sort_i/p/c/m/f`，继续使用修复后的驱动和 `DEBUG=0`。

## 最简复核与重新运行

在仓库根目录，以下命令仅用 Python 标准库读取证据、检查一致性并向新目录写派生结果，不编译或启动性能实验：

```bash
python3 P2/scripts/summarize_stage_a.py --destination /tmp/p2-stage-a-review
```

独立重做三个实验需 Ubuntu、Clang、Make、Valgrind 和支持 libelf/DWARF 的 Perf。输出目录须为新目录，命令会重新构建和运行：

```bash
python3 P2/scripts/run_stage_a.py all \
  --perf /usr/lib/linux-tools-6.8.0-146/perf \
  --out /tmp/p2-stage-a-rerun
python3 P2/scripts/summarize_stage_a.py \
  --out /tmp/p2-stage-a-rerun --destination /tmp/p2-stage-a-rerun-summary
```

其他机器的 Perf 路径与自动缓存配置可能不同，应保存实际配置解释结果。正常时间不要求逐条相等。`prepare_stage_a.py`、`diagnose_perf.py`、`finish_preflight.py` 记录本机这次准备与修复过程，不应在已交付目录重跑。

`perf.data` 的记录路径、交付路径和 SHA256 见采样目录中的 `copied-artifact.json`。正式程序 Build ID 为 `1936959c6035465f69ef771edff11904c39ccd58`，二进制为 `binaries/isort-debug.elf`，源码为 `source/recitation/isort.c`。其他目录重新注释旧样本时，可先用完整 Perf 的 `buildid-cache --add` 加入该二进制，再用 `--prefix/--prefix-strip` 映射旧源码路径；提供的可读注释可直接阅读。
