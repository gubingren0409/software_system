# Matrix Multiplication Autotuner（P1）

正式课程报告：[report.md](report.md)。源码、报告和派生图表均在`project01`分支。

## 已完成结果

| 实验 | 范围 | 结果 |
|---|---|---|
| RAW Grid | 20配置，20预热+100测量 | 测得最低中位数O3/s128，50.996291138秒 |
| 三配置独立验证 | O3/s128→s64→s24，共18次fresh | 中位数51.602724641 / 52.784908609 / 63.240102045秒，不替换Grid |
| 首种子Random/Greedy | 搜索种子20261008，各12唯一配置；独立复测2/1组 | 两者最终选O3/s128；27完整组、162已接纳执行+6精确放弃记录=168条 |

首种子四项证据/执行/计时/比较验收通过。原计划五种子仅完成首种子，整体完成及比较仍为false。
原RAW Grid的O3/s24含待机；跨日、跨运行段及低内存警告保留，不校准旧数据，不外推跨种子稳定性。
本次只整理课程报告及离线派生图表，新增真实性能执行、时钟探针和资源门禁均为0。

## 查看与离线复算

在WSL Ubuntu-24.04、项目根目录中，以下仅查看帮助与配置：

```bash
python3 -m autotuner --help
python3 -m autotuner list-configs
```

离线复算原始JSONL中的五次测量、Grid、六行前缀与成本；仅向新目录写派生文件，
无需编译、reference缓存、资源门禁或性能执行：

```bash
python3 scripts/report_offline.py --output /tmp/project01-report-review-unique
```

已有目录会拒绝覆盖；请使用新的目录名。仅统计需要Python标准库；
如需重绘，再加`--figures /tmp/project01-report-figures-unique`，需要matplotlib。
已执行的[复算、来源哈希和图表检查](evidence/report_release/20261021/README.md)不改原数据。

## 代码与真实运行入口

- 三接口及单次执行：[autotuner/core.py](autotuner/core.py)、[target配置](configs/target.json)、[20配置空间](configs/config_space.json)。
- 三种策略：[autotuner/search.py](autotuner/search.py)；1预热+5fresh与中位数：[measurement.py](autotuner/measurement.py)。
- [老师原件](code/original/matrix_multiplication.c)与[工作副本](code/working/matrix_multiplication.c)分开保存；工作副本保留核心循环，增加输入、参数、RAW及校验外围功能。
- RAW比较准备：[prepare_raw_comparison.py](scripts/prepare_raw_comparison.py)，`--content-sha/--output/--mode`导出冻结内容、核验并初始化**新空session**；它会写文件、做准备，不是只读汇总。
- RAW真实长跑：[start_raw_comparison.py](scripts/start_raw_comparison.py)，`--plan`和搜索所需的`--search-authorization`；含准入、门禁、性能执行和一次性预算，不是报告重绘命令。

旧`python -m autotuner campaign`在当前RAW协议下拒绝，不能作为现行比较入口。
已关闭Grid/验证/首种子session和已领取claim不得重新执行，账面余额不构成运行授权。
本仓库没有适用于全部任务的统一`--algorithm`命令；更换目标需适配结果及正确性契约。

## 已归档证据

- [完整RAW Grid及待机限制](evidence/p3_raw_grid/20261012-181149-manual-remaining/README.md)
- [三配置独立验证](evidence/p3_raw_comparison/20261019-122200-user-retry4/README.md)
- [首种子最终结果、六行表及原始记录入口](evidence/p3_raw_first_seed/20261020-214028-09795d71-first-seed-finish/README.md)
- [审计交接及历史过程](docs/AUDIT_HANDOFF.md)、[工作记录](docs/WORK_LOG.md)

历史失败、旧MONOTONIC Grid、暂停状态、claim和预算均保留在原目录及Git历史，
不追认为当前成绩。课程报告覆盖三算法要求，不等于自定五种子扩展计划完成。
