# 正式报告整理（仅离线，基于已审0050066）

本轮只重组课程报告、生成已有数据的派生图表及检查提交内容。
真实性能、矩阵、时钟探针、资源门禁、恢复、续跑和新搜索执行均为0。
所有旧session、分数、失败、claim及预算不变。

输入为完整RAW Grid、三配置独立验证和最终首种子交付。`scripts/report_offline.py`
只读其原始JSONL与终态组，从五次测量重算中位数、样本CV、MAD、前缀和成本，
与既有CSV交叉核对；不导入运行器、不调用子进程、不签发任何准入证书。
输出到新目录，已存在目录拒绝覆盖。统计复算不代替历史原始时钟/资源审计。

## 已执行检查

- [最终派生统计/输入SHA](derived-release/summary.json)：从原始JSONL与组独立重算，Grid20/120执行、
  验证3/18执行、首种子27完整组/162已接纳+6精确放弃=168唯一记录及六行前缀，与既有CSV一致。
- [最终报告检查](checks-release.json)：在最终图表/入口修订后通过，并校验实际20唯一配置、源码语法和性能差异百分比。
- [Windows离线绘图输出](operations/offline_release_figures.stdout.txt)、[WSL标准库复算](operations/wsl_offline_standard_library.stdout.txt)。
- [实际CLI帮助](operations/wsl_cli_help.stdout.txt)、[20配置列表](operations/wsl_list_configs.stdout.txt)、
  [真实主控参数帮助](operations/raw_controller_help.stdout.txt)、[准备入口帮助](operations/raw_prepare_help.stdout.txt)。只执行`--help`，不prepare/run。
- [Markdown浏览器检查](operations/markdown_browser_release.stdout.txt)：三图加载、七节标题可见；
  临时截图仅用于本轮排版检查，不是实验终端截图，不提交截图/HTML或渲染缓存。

图表草稿、中间重复统计和临时预览不提交，最终数据为`derived-release/`；数值没有改动。
操作记录保存真实argv、stdout/stderr、PID、退出码和QPC，存在并行/嵌套，不能全部相加。
该QPC是报告整理辅助成本，不写入任何实验活动或余额。

已有目录拒绝测试`offline_existing_directory_rejected`按预期退出1，最终派生没有被覆盖。
首次进程查询`no_live_experimental_targets`的正则被WSL外层shell解释，退出2，不能作为无进程证明；
改用[无元字符的ps查询](operations/no_live_targets_ps.operation.json)，stdout/stderr为空、退出1表示未匹配目标进程。
本轮未启动任何矩阵/探针；所有离线子命令已退出。一次辅助计数单行命令括号笔误已修正，不涉及运行代码或数据。
生成SVG的行末空白通过纯格式整理去掉；图形路径、文字、计分和数据不变，Git diff检查通过。

## 保护与限制

[交付状态与范围](delivery_status.json)、[最终暂存范围验收](checks-packaging.json)。
本轮基线为0050066完整SHA（见[要求对应](../../../docs/REPORT_ACCEPTANCE.md)）。
原Grid/验证/首种子session及原件、C/策略、协议、claim、证书、检查点、失败和预算不变。
16个实际统计输入记录运行时字节SHA；Git范围检查只准许报告/派生文件及必要入口链接变更。
首种子四项true保持，五种子整体false保持；本轮不签发新时钟/资源证书，不重审全部历史实验。
报告继续披露单种子、跨日跨段、Grid s24待机及低宿主内存警告。

要求对应、自审及操作记录与本轮派生数据仅为提交说明。
正式报告是仓库根目录`report.md`；本文件不是第二份课程报告。
