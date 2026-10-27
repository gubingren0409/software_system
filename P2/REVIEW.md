# Project 2 最终交接（Stage C）

项目已完成。Stage A 与 Stage B 的实现、正确性验证、正式计时和剖析均已通过外部审核；[最终报告](README.md)按 Checkoff Item 1、Checkoff Item 2、Write-up 1–7 顺序覆盖九项作答。Stage C 仅修订报告文字、入口和交接说明，并保存离线检查记录，没有新增性能测量或修改算法、测试驱动、公共构建配置及 K=16。没有未完成的必需事项。

## 已审核对象与本次修改

本次外部审核通过的对象为 [Stage B 固定提交](https://github.com/gubingren0409/software_system/commit/2c658124d92f2d9e14f55f33f6f64f2156a55a0c)：`2c658124d92f2d9e14f55f33f6f64f2156a55a0c`。其审查 ZIP 的 SHA256 为 `cde4f7b3449b790fe4be51bccc2c55dd4419904eba7e74e2c606f8561b996a57`；包内1578个文件与该提交逐字节一致，Stage A 的490个历史证据文件保持原样。

Stage C 处理三项文字意见：

1. **Write-up 6：** 将单缓冲随机输入变慢的具体原因明确写为可能解释，说明混合两类输入的整进程剖析未单独隔离边界检查、控制流和数据依赖。
2. **Write-up 5：** 说明3%是预先约定的工程取舍规则，不是统计显著性或等效性检验；保留K32搜索最小、K16按规则入选的决策，明确确认组每候选只有一个独立进程、每类五次，不能证明跨运行稳定性或K16普遍最优。
3. **Write-up 7：** 明确f减少分配的效果，同时保留大规模随机输入约3%的正向观察、其他条件收益很小或方向相反的事实；不把范围重叠当显著性检验，也不把减少分配写成普遍时间收益。

报告的过程性标题改为“基线实验小结”和“优化版本的比较方法与正确性”，保留现有精确表格，没有新增图或截图。统一结论明确c在两个随机规模下最快、m/f在逆序下更快，五步没有单调加速。历史原始记录、快照、ELF和汇总数值均不改写；本阶段检查记录另存于 [results/stage-c](results/stage-c/)。

## 固定起点与证据

仓库为 [software_system](https://github.com/gubingren0409/software_system)，分支 `Project02`，本地 worktree 为 `E:\software_system\Project02`。Stage C 开始时工作区干净，HEAD为上述已审核的Stage B提交，没有已有后续提交或改动需要覆盖。更早的Stage A固定提交为 `3f3f0651d517bfc189c3f3bc89ffd6fa0c658e83`。

Stage A 原始证据目录的 Git tree 为 `c33d3fcf182c2127f4f771d395838d2058674c2c`，Stage B为 `6e42a5e314170e34065c19a1df04da1cae5bcf05`；Stage C保持这两个目录不变，没有重跑长实验，也没有改写历史summary。[results/stage-b](results/stage-b/)保存已审核的五个优化版本实验，原始题目在 [original](original/)。

每个命令目录保存 `command.txt`、`metadata.json`、`stdout.txt`、`stderr.txt`，记录实际 argv、cwd、起止 UTC、退出码和墙钟时长。Stage B 另有 `identity.json`，关联实际二进制 SHA256、源码清单 SHA256、构建清单 SHA256 与环境覆盖。三阶段各自冻结源码和 ELF：

| 用途 | 快照和构建清单 | 数据 |
|---|---|---|
| a/i/p 基础选择 | [selection/build-manifest.json](results/stage-b/selection/build-manifest.json) | [selection](results/stage-b/selection/) |
| 五个 K 搜索与确认 | [tuning/build-manifest.json](results/stage-b/tuning/build-manifest.json) | [tuning](results/stage-b/tuning/) |
| 最终六版本比较 | [final/build-manifest.json](results/stage-b/final/build-manifest.json) | [final/native](results/stage-b/final/native/)、[profile](results/stage-b/profile/) |

早期快照用于早期选参，不能冒充最终实现。最终 [source/homework](results/stage-b/final/source/homework/) 与当前提交的 homework 源码逐字节对应。最终目录保存五份 ELF：正式 Release、正确性 Debug、递归 inline 关键字关闭对照、分配诊断、故障注入；后二者不进入正式时间表。Release 与关闭递归关键字的 ELF 哈希相同，说明此处关键字没有改变生成代码。

## 审核意见处理

1. **95.35% 与 94.45% 的差异已解释并离线验证。** [Perf 6.8.12 的 `annotation__calc_lines`](https://github.com/gregkh/linux/blob/v6.8.12/tools/perf/util/annotate.c) 先过滤单条指令贡献不超过 0.5% 的项，再合并源行。第20行完整 period 为 `1,299,100,602 / 1,362,398,487 = 95.35393751505245%`，过滤后为 `1,286,723,959 / 1,362,398,487 = 94.4454923634982%`，少计 `12,376,643`、即 `0.908445151554253` 个百分点。[核对结果](results/stage-b/audit/annotate-filter/stdout.txt)逐指令列出是否保留，原始采样及95.35%结论未改。
2. **区分测试组与算法选择。** `-b` 只选择 random/inverted 计时组；Stage A 仅注册 a，历史实验仍有效。现在 `--variant a|i|p|c|m|f|all` 选择算法，默认 a 保持旧命令语义。正式脚本全部显式指定单版本。输出有 N/R/seed/输入指纹和实际调用次数，未知版本、选项与非法参数退出非零。
3. **Stage A 离线校验只依赖其冻结证据。** 汇总脚本读取 `results/stage-a/source`，验证完整29项源码/ELF清单、哈希和官方基线；没有移除完整性检查。新派生汇总用 `frozen_sources_covered_by_manifest` 替代历史工作源码相等标记，其余历史数值逐项相同。交付检查同样验证冻结清单，允许当前优化源码继续演进。
4. **禁用弱关联复用。** Stage A 的旧 `--resume` 直接报错；独立重跑构建从保存的 Stage A 源码复制。Stage B 不实现 resume，已有命令目录拒绝覆盖，不会自动拼接不同二进制的历史数据。

Stage A 原先的 Clang `-always-inline`、Perf 缺少 libelf/DWARF、Perf 写 DrvFS、旧 `cg_annotate` 参数失败及处理记录完整保留在 [stage-a](results/stage-a/)。Stage B 使用已可用的完整 Perf 6.8.12，采样先写 Linux `/tmp` 再复制，保留复制文件和对应 ELF 的哈希。Stage B 没有掩盖失败的实验重跑。汇总时发现 `perf report` 的 `3K/2K` 样本头是缩写，解析器已改读 `perf record` 的精确 `3019/2581`；只重新生成派生 JSON，没有重新采样。

## 实现与选参决策

- **i：** 从 a 派生，局部 static inline 的复制、归并、分配/释放包装。a、util.c/h 保持原样。Clang 已自动内联 a 的复制与归并，i 没有稳定原生收益。
- **p：** 从 i 派生，用指针推进复制与归并，保留两份哨兵临时区。机器码并非完全相同，但本次没有可靠速度改善。
- **c：** a/i/p 四格时间比的等权几何平均分数为 `1.00000 / 1.01631 / 0.99157`。按事先固定的“最佳3%内视为并列，优先简单实现”规则选 a，固定作为 c 的基础。
- **K：** N131072、seed42、每候选三进程×每类三次，搜索8/16/32/64/128。K32综合最小，K16在其3%内，按预设“小阈值优先”工程规则固定16，3%不是统计显著性或等效性检验。独立seed43、N1048576确认中，每候选只有一个独立进程、每类五次；K32综合时间比K16为0.96628，random约快7%，inverted近持平。这提示K32可能更适合大规模随机输入，不能证明跨运行稳定性或K16普遍最优；不据此改选阈值，不追加搜索。候选与确认数据均保留。
- **m：** 从 c 派生，只复制左半区，右半区原地读取；`j-k=n1-i` 保证不覆盖未读右侧。每次归并仍分配/释放，根临时空间从 `4(n+2)` B 降到 `4ceil(n/2)` B。
- **f：** 从 m 派生，长度超过K时每次正常完成的顶层调用申请、释放各一次，递归后序复用；没有持久缓存或计时外预分配。小数组直接插入排序，无需分配，m/f申请失败退出1。f与m峰值临时堆空间相同，主要减少重复分配与累计请求量。

所有内部辅助函数保持 static，公共接口与归并结构保留。最终公共配置为 DEBUG=0、Clang18.1.3、`-O3 -DNDEBUG -g -Wall -std=gnu99 -gdwarf-3`，另加相同的内联诊断开关。没有通过改变基线公共工具或编译等级制造收益。

## 正确性与边界

[verification.json](results/stage-b/correctness/verification.json)保存全部结论，原始输出位于 [correctness](results/stage-b/correctness/)。Release/Debug六版本各230个模式与子数组用例，涵盖空、单元素、2/3、奇数、非二次幂、K±1、正序/逆序/随机/重复/全相等、非零起点及区间外保持。完整N33/R1每版本实际调用234次，全部逐元素匹配可信qsort参考。尺寸表包含重复的K邻域项，没有把230写成不同长度数。

Memcheck为0错误、退出时0活动字节、66,033次分配与释放相等。8条非法命令退出1；故障版本把结果写成全零，虽然有序，仍以元素不匹配退出1。单版本与all模式输入指纹相等；同种子可复现，换种子改变随机输入。

原题输入域为0..2147483647；a/i/p/c保留UINT_MAX哨兵，不支持以本次结果宣称任意uint32_t输入正确。CLI限制N<=INT_MAX/2，避免原基线中点加法溢出；空区间为内部合法数组上的测试。没有为扩展输入域悄悄改写a。

独立分配诊断N131073、起点3：a/i/p各262144次申请，c16384、m8192、f1次，释放数相同，退出时活动字节均0。c/m/f峰值请求分别524300/262148/262148 B；这是排序请求的空间，不含分配器元数据和递归栈。诊断与故障构建没有混入性能结果。

## 实际矩阵与结果范围

正式矩阵为六版本×N131072/1048576×五进程，每进程random/inverted各五次，共60个进程、600次排序。固定CPU0、seed20261026，版本顺序轮换，正常时间、Cachegrind和Perf顺序执行。每格报告五个进程均值的中位数与最小—最大范围。输入生成/复制/指纹/校验/日志在计时外，算法内部申请释放在计时内。本轮a重新测量，Stage A旧时间不参与正式加速比。

| 结果 | N131072 random / inverted | N1048576 random / inverted |
|---|---:|---:|
| c/a加速 | 1.407 / 1.610 | 1.333 / 1.470 |
| m/a加速 | 1.217 / 2.367 | 1.111 / 2.196 |
| f/a加速 | 1.222 / 2.362 | 1.144 / 2.171 |
| f/m加速 | 1.005 / 0.998 | 1.030 / 0.989 |

c四格均改善且在两个随机规模下最快；m/f逆序收益大，随机比c慢。f减少分配的效果明确，但未观察到跨输入、跨规模稳定的额外时间收益；大规模随机输入有约3%的正向观察，小规模随机输入收益很小，两个逆序格略慢。最小—最大范围描述波动，其重叠本身不是显著性检验。i/p没有稳定整体收益，五步没有单调加速，f也不是所有输入下都最快。完整24格表与波动见正式报告及 [native-summary.csv](results/stage-b/summary/native-summary.csv)。WSL/宿主调度和频率波动存在，未用严格空闲门槛，结论限于本次输入与环境。

每版本一组Cachegrind，N131072/R5、相同seed、共10次排序。实际模拟模型I1/D1各32KiB、8路、64B行，LL64MiB直接映射、64B行；WSL lscpu可见L3为32MiB，两者区分。整进程包含驱动与参考qsort，源文件独占统计不包含被调函数成本。六组qsort.c的Ir都为276939211。m减少D1缺失但增加排序文件Ir和条件分支，因此缓存改善不等于随机时间改善。f把malloc.c整进程Ir从m的10945131降到15544，但merge仍是主要工作。

i递归inline开关对照私有代码同为480B、规范化指令相同、ELF哈希相同；编译器明确拒绝递归内联。i的I1/LLi为1954/1743，a为2022/1764，没有实测指令缓存退化。代码体积与理论展开代价分开解释，没有把理论可能性写成观测。

i/f各采一组N1048576/R5的Perf，精确样本数3019/2581，丢失均0，四种用户态计数的运行比例均100%。采样完整进程，参考qsort及比较器合计45.14%/54.54%；共享memmove无法仅凭平面报告全部归给候选排序。硬件计数与采样独立运行，Cachegrind又使用不同N，不能混用绝对次数。源码/汇编注释和原始perf.data均保存。缺少可用的真实终端截图会话，交付原始文本与可读注释，没有伪造截图。

## 最简离线复核

仓库根目录执行，Python标准库即可，不需要WSL、Clang或Perf，也不会启动性能实验。派生输出目录须不存在：

```bash
python3 P2/scripts/summarize_stage_b.py --destination /tmp/p2-stage-b-review
python3 P2/scripts/verify_delivery.py
python3 P2/scripts/verify_stage_b_delivery.py
```

第一条从原始stdout计算600条时间和24格统计，验证全部三阶段快照/ELF及捕获身份、指纹/均值、Cachegrind源文件和总数、选参和递归inline证据；它也离线重算Stage A并逐项确认历史数值相同。第二条检查Stage A报告表格、冻结清单、原题哈希、Perf复制和报告链接。第三条检查Stage B表格、链接、快照及二进制清单、Perf复制和完整交付。所有命令均在本次交付前通过，生成的表与报告一致。

如需单独复算Stage A：

```bash
python3 P2/scripts/summarize_stage_a.py --destination /tmp/p2-stage-a-review
python3 P2/scripts/check_stage_a_audit.py
```

若需要重新测量单个版本，可在WSL中编译后用 `./sort --variant f -b -s 20261026 1048576 5`，或直接运行保存的Release ELF；这不是离线复算。完整历史运行的精确命令在各目录的command.txt中。`run_stage_b.py`分阶段执行且拒绝覆盖，最终构建依赖已完成的选参决策，不能把对空目录执行最终阶段当作自动重做全部阶段。原始证据目录不应重用为新实验输出。

## 固定交付与验证

Stage C的完整提交SHA、固定报告/交接链接、最终ZIP路径与完整SHA256在本次集中交付消息中提供，并与上文已审核的Stage B对象区分。ZIP注释记录对应完整提交SHA，同名 `.zip.sha256` 文件提供校验值；历史Stage B审查ZIP保留。

确认已检出交付消息指定的固定提交后，可按以下命令生成和逐文件验证审查包。显式关闭Windows自动行尾转换，使ZIP字节与Git提交一致：

```bash
git -c core.autocrlf=false archive --format=zip --output=/tmp/p2-final-review.zip HEAD
python3 P2/scripts/verify_delivery.py --zip /tmp/p2-final-review.zip
python3 P2/scripts/verify_stage_b_delivery.py --zip /tmp/p2-final-review.zip --commit "$(git rev-parse HEAD)"
sha256sum /tmp/p2-final-review.zip
```

ZIP含原题、源码、脚本、全部历史实验证据与本阶段离线检查记录，不含.git、凭据、无关临时目录及旧审查ZIP。交付前检查九项作答、全部报告表格与链接、29项Stage A及61项Stage B清单，离线复算600次正式排序并确认历史数值一致；随后核对本地/远端SHA及ZIP全部文件与固定提交一致。本阶段不再扩展性能实验。
