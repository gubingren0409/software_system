# Project 2 Profiling Serial Merge Sort

学号：10245102457<br>
姓名：谷秉仁

- 操作系统：Ubuntu 24.04 LTS（WSL2）
- CPU：AMD Ryzen 9 7940HX，WSL 可见 16 核、32 线程
- 内存：WSL 可见 7.4 GiB

## 实验环境与运行方式

本阶段完成 Checkoff Item 1、Checkoff Item 2 和 Write-up 1。题目来源为[课程要求](original/course-requirements.docx)与 [MIT Homework 2](original/MIT6_172F18hw2.pdf)，代码来自[官方压缩包](original/MIT6_172F18_hw2.zip)。实验均在 `wsl -d Ubuntu-24.04` 中运行，完整 CPU 输出见 [lscpu.txt](lscpu.txt)。

| 项目 | 实际配置 |
|---|---|
| 内核 | `6.18.54.1-microsoft-standard-WSL2` |
| Clang | Ubuntu Clang 18.1.3 |
| 正式 Perf | `/usr/lib/linux-tools-6.8.0-146/perf`，版本 6.8.12，支持 libelf 和 DWARF |
| Valgrind | 3.22.0，显式启用缓存与分支模拟 |
| Homework Debug | `-DDEBUG -O0 -g -Wall -std=gnu99 -gdwarf-3` |
| Homework Release | `-O3 -DNDEBUG -g -Wall -std=gnu99 -gdwarf-3` |
| Recitation isort | 原题 `DEBUG=1`：`-Wall -O0 -g` |
| Recitation sum | 原题 Release 的 `-Wall -O1 -DNDEBUG`，增加 `-g` 供源码注释使用 |

原始 Homework 在 Clang 18 下报 `unknown argument: '-always-inline'`，因此从公共编译参数移除它，两种构建一致处理。每次切换模式都用 `make --always-make` 重新编译，分别保存二进制。默认 Perf 虽能计数，但未编入 libelf/DWARF，改用系统已有的完整版本；采样直接写 Windows 挂载盘出现 `Bad address`，改为写 Linux `/tmp` 后复制完整文件。

测试驱动修复了随机种子未接入 `rand_r`、不同输入计时累计、重复执行 `sort_a`、仅验证有序性和失败仍返回成功的问题。现在使用 `qsort` 参考结果逐元素校验，失败立即以非零状态退出；空区间与单元素检查也修正了边界条件。`-b` 仅运行一个版本的 random、inverted 测试，数据生成、备份和参考校验均在排序计时之外。`sort_a.c` 和 recitation 的 `isort.c` 与官方版本逐字节相同。这些是构建和测量框架修复，不计作排序优化收益。

## Checkoff Item 1

**作答**

瓶颈是插入排序的内层循环。按原题使用 `DEBUG=1` 构建、固定种子 42，以 `10000 10` 排序，`isort` 占全进程用户态周期样本权重的 **99.98%**。完整硬件计数如下，计数期间各事件均显示 100% 运行比例。

| 硬件事件 | 全进程用户态计数 |
|---|---:|
| cycles | 1,369,636,050 |
| instructions | 5,270,141,946 |
| branches | 752,986,666 |
| branch-misses | 114,172 |

硬件事件均可实际采集，分支误预测率为 `114172 / 752986666 × 100% = 0.01516%`。计数与采样分别运行相同输入配置，计数值不等于另一轮采样的估计事件总数。

主要命令如下；`$P2` 为本作业目录，`$PERF` 为上表中的完整 Perf 路径。

```bash
taskset -c 0 "$PERF" stat -x , \
  -e cycles:u,instructions:u,branches:u,branch-misses:u \
  -- "$P2/results/stage-a/binaries/isort-debug.elf" 10000 10

# 采样先写 Linux 文件系统，完成后复制进 results/stage-a/checkoff1/
taskset -c 0 "$PERF" record -e cycles:u -F 999 \
  -o /tmp/p2-isort-perf.data \
  -- "$P2/results/stage-a/binaries/isort-debug.elf" 10000 10
"$PERF" report -i /tmp/p2-isort-perf.data --stdio --no-children --sort=symbol
"$PERF" annotate -i /tmp/p2-isort-perf.data --stdio -l -s isort
```

正式采样得到 **788 个样本，丢失 0 个**。对 `perf script` 导出的样本按 `period` 加权，分母取 `isort` 全部样本权重，包含未解析行号的样本；[isort.c 第 20 行](recitation/isort.c#L20)的权重占比为 **95.35%**：

```c
while (index >= left && *index > val) {
```

最高权重的单条指令归于同一行，ELF 地址为 `0x11f0`，即 `isort+0x60`，占 `isort` 样本权重的 **67.65%**。对应的条件判断及邻近指令为 AT&T 语法：

```asm
11de: mov  -0x28(%rbp),%rax
11e2: mov  (%rax),%eax
11e4: cmp  -0x1c(%rbp),%eax
11e7: seta %al
11ea: mov  %al,-0x29(%rbp)
11ed: mov  -0x29(%rbp),%al
11f0: test $0x1,%al
11f2: jne  11fd <isort+0x6d>
```

随机输入下，每插入一个元素都可能反复比较并后移前面的元素，总工作量为二次量级。`-O0` 还保留了循环变量、布尔中间值在栈上的多次读写，因此这段循环执行了大量指令。观测到的分支误预测率很低，不能据此把主要瓶颈归为分支预测失败。`test` 的高占比表示周期采样的归属，不能说明这条指令本身有这么大的执行延迟；非精确采样存在偏移，还需结合邻近的加载、比较、分支和整个循环理解，不能当作精确逐行计时。

原始证据：[硬件计数](results/stage-a/checkoff1/perf-stat/stderr.txt)、[函数热点](results/stage-a/checkoff1/perf-report/stdout.txt)、[源码汇编注释](results/stage-a/checkoff1/perf-annotate/stdout.txt)。逐样本导出、`perf.data`、对应二进制及源码快照均保存在 `results/stage-a/`；行号加权结果可由汇总脚本复算。

## Checkoff Item 2

**作答**

默认工作集远大于 D1，但小于本次模拟的 LL，因此随机数组读取几乎都发生 D1 缺失，通常仍能命中 LL。完整默认配置为 `U=10000000`、`N=100000000`、种子 42；累加变量仍为原题的 `uint32_t`，保持模 `2^32` 的累加语义。原生与模拟运行均输出 `Value = 938895920`。

Cachegrind 实际采用以下配置，所有对照实验相同。这是模拟缓存配置；WSL 的 `lscpu` 显示 L3 为 32 MiB，两者不同，结果按模拟模型解释。

| 模拟缓存 | 容量 | 相联度 | 缓存行 |
|---|---:|---:|---:|
| I1 | 32 KiB | 8 路 | 64 B |
| D1 | 32 KiB | 8 路 | 64 B |
| LL | 64 MiB | 直接映射 | 64 B |

```bash
valgrind --tool=cachegrind --cache-sim=yes --branch-sim=yes \
  --cachegrind-out-file=/tmp/p2-sum-default.out \
  "$P2/results/stage-a/binaries/sum-u10000000-n100000000.elf"
cg_annotate --auto=yes --show-percs=no /tmp/p2-sum-default.out
```

下表为整进程统计，包含数组初始化、`rand_r`、循环和输出。`D refs = Dr + Dw`，D1 与 LLd 缺失数均为读缺失与写缺失之和，缺失率统一除以 `D refs`。

| U | N | D refs | D1 缺失 | D1 缺失率 | LLd 缺失 | LLd 缺失率 |
|---:|---:|---:|---:|---:|---:|---:|
| 4,096 | 1,000,000 | 6,049,980 | 1,929 | 0.0319% | 1,633 | 0.0270% |
| 262,144 | 1,000,000 | 6,308,051 | 987,486 | 15.6544% | 17,762 | 0.2816% |
| 10,000,000 | 1,000,000 | 16,045,903 | 1,626,020 | 10.1336% | 626,453 | 3.9041% |
| 33,554,432 | 1,000,000 | 39,600,341 | 3,098,740 | 7.8250% | 2,601,784 | 6.5701% |
| 10,000,000 | 10,000,000 | 70,045,899 | 10,618,685 | 15.1596% | 626,467 | 0.8944% |
| 10,000,000 | 100,000,000 | 610,045,907 | 100,546,117 | 16.4817% | 626,467 | 0.1027% |

默认配置中，`Dr=400033108`、`Dw=210012799`；D1 读/写缺失分别为 `99920671 / 625446`，LLd 读/写缺失分别为 `1050 / 625417`。初始化会顺序写入全部 40,000,000 B 数组，约有 `40000000 / 64 = 625000` 个缓存行的首次写入，解释了 LLd 缺失主要由写缺失构成。分支模拟记录的条件分支/误预测为 `110025526 / 3506`，间接分支/误预测为 `100000346 / 179`。

固定 `N=1000000` 改变 U 时，仅比较整进程缺失率会受初始化工作量影响。因此另看源码注释归于 [sum.c 第 38 行](recitation/sum.c#L38) `val = (val + data[l]);` 的读取，该行在四种配置下均有 1,000,000 次读取：

| 数组工作集 | 第 38 行 D1 读缺失率 | 第 38 行 LL 读缺失率 |
|---|---:|---:|
| 16 KiB | 0.0008% | 0% |
| 1 MiB | 96.9260% | 0% |
| 40,000,000 B，约 38.15 MiB | 99.9178% | 0.0024% |
| 128 MiB | 99.9746% | 50.3044% |

16 KiB 工作集能留在 D1 中；1 MiB 与约 38.15 MiB 的工作集超过 D1，但可留在模拟 LL 中。128 MiB 超过 64 MiB 的 LL，随机读取的 LL 缺失率约为一半，符合这个直接映射模型下的预期。这里的单行统计按编译器的源码归属读取，整进程其他缺失仍单独保留。

固定 `U=10000000`，将 N 从一亿降到一百万，D1 缺失总数由 100,546,117 降至 1,626,020，主要是工作量减少。第 38 行的 D1 读缺失率在三个 N 下仍分别为 `99.9178% / 99.91843% / 99.919275%`，没有改善访问局部性；LLd 缺失总数也仍在 626,000 左右，主要来自相同规模的初始化。整进程缺失率会随初始化与随机访问的占比变化，不能直接将其下降解释成局部性改善。

要减少缓存缺失，可在任务允许时缩小工作集，使其进入较近的缓存，或重排访问来增加同一缓存行、同一小块数据的连续复用。单纯减少 N 只能减少访问次数。本次对照只改变编译期 U/N 常量，保留原题随机访问和累加语义，没有把访问顺序优化混入默认配置。

原始证据：[默认 Cachegrind 输出](results/stage-a/checkoff2/cachegrind-u10000000-n100000000/stderr.txt)、[默认源码注释](results/stage-a/checkoff2/annotate-u10000000-n100000000/stdout.txt)、[六组完整统计](results/stage-a/summary/sum-cachegrind.csv)。

## Write-up 1

**作答**

`DEBUG=0` 的动态指令数明显减少，原生排序也更快，但指令数比例不能直接替代时间加速比。两种配置均使用初始 `rand_r` 种子 42、`N=131072`、`R=5`，由相同规则生成 random 和 inverted 输入。每个进程只选择 `sort_a`，每类输入排序 5 次，共 **10 次排序**。Debug 为 `-O0 -DDEBUG`，Release 为 `-O3 -DNDEBUG`，共同保留调试信息。

Cachegrind 各运行一次，均启用缓存与分支模拟。以下整进程统计包含输入生成、备份、参考 `qsort` 校验、分配释放、计时和输出，不是单次排序的统计。

| 指标与范围 | DEBUG=1 | DEBUG=0 |
|---|---:|---:|
| 整进程指令 Ir | 2,322,303,842 | 1,371,689,467 |
| 仅归于 `sort_a.c` 的指令 Ir | 1,050,540,590 | 478,575,530 |
| 整进程数据引用 Dr+Dw | 1,504,669,816 | 601,195,799 |
| 整进程 D1 缺失 | 4,383,757 | 4,384,234 |
| 整进程 LLd 缺失 | 51,169 | 51,204 |
| 整进程条件分支 Bc | 234,763,391 | 183,399,658 |
| 整进程条件分支误预测 Bcm | 19,456,727 | 9,364,961 |

`sort_a.c` 的一行汇总合并了该文件内的递归、归并和复制代码归属；它不包括 `malloc/free`、`util.c` 或参考排序的执行成本，不能作为整个排序调用的包含式指令数。该项与整进程总数分开列出，用于观察基线算法代码本身的变化。

正常耗时另行采集。Debug、Release 交替运行，各做 5 次独立进程实验，并固定到逻辑 CPU 0；每个进程分别取每类输入 5 次排序的平均值，下表再报告这 5 个进程平均值的中位数和最小—最大范围。计时边界为 `CLOCK_MONOTONIC` 紧邻 `sort_a(data, 0, N-1)` 的前后，包含其内部归并、内存分配与释放，不包含数据生成或结果校验。

| 输入 | Debug 中位数，ms［范围］ | Release 中位数，ms［范围］ | 中位数之比 Debug/Release |
|---|---:|---:|---:|
| random | 44.766［43.437–47.025］ | 15.537［15.044–17.795］ | 2.88 |
| inverted | 25.104［24.048–28.779］ | 15.478［14.895–16.586］ | 1.62 |

使用指令数的优点是：它能量化完成相同任务时执行的工作量，不依赖某一轮墙钟时间，较少受频率和调度波动影响；源码注释还能帮助判断哪些代码的动态指令减少了，适合比较固定输入下的实现和编译配置。

局限是：不同指令的成本不同，缓存与分支行为、指令依赖、流水线并行和内存等待都会改变每条指令的平均成本。整进程统计还混入驱动和参考校验；优化构建既改变编译优化等级，也关闭了断言，因此不能把所有差异仅归于 `-O3`。Cachegrind 的缓存和分支结果属于模拟，不能代替本机硬件事件；它运行时的耗时也不能用于正常性能加速比。

本次 Release 的整进程指令数降低，但 D1 缺失绝对数几乎不变。random 和 inverted 的原生中位数比分别为 2.88 和 1.62，也没有一个共同的“指令数加速比”。这些结果支持 Release 在本组输入和环境下更快，后续优化比较统一使用 `DEBUG=0`，并继续同时保留原生时间和剖析数据。

原始证据：[Debug 注释](results/stage-a/writeup1/annotate-debug-retry1/stdout.txt)、[Release 注释](results/stage-a/writeup1/annotate-release/stdout.txt)、[100 条正常计时记录](results/stage-a/summary/native-trials.csv)。各进程完整输出与两份 Cachegrind 原始文件保存在 `results/stage-a/writeup1/`。

## 本阶段结果小结

插入排序的热点位于第 20 行的内层循环条件及其后移操作；高样本占比需要结合循环工作量和采样偏移解释。`sum` 的随机访问在工作集超出 D1 后几乎每次都发生 D1 缺失，超出模拟 LL 后又出现明显的 LL 读缺失。归并排序基线的 Release 构建减少了动态指令并改善原生时间，但缓存缺失绝对数并未按相同比例下降，指令数只能作为性能比较的一项依据。
