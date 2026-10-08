# 关键终端截图：来源、命令与验收

执行模式：**补齐已有结果的截图**。本次未启动 SPEC 性能 workload、完整 Base、选做矩阵或 OOM 复核；仅读取已有证据并运行 `--check`/只读校验。工作仓库为 `E:\software_system\course_repo`，分支 `homework02`，起点提交为 `6a485a8c9a2e783014c950ab37edbc30b7a32ee3`。截图采集阶段未进行 Git 提交；整理后的报告、截图和来源记录统一纳入 `homework02` 分支的本地提交，不推送远端或提交老师平台。

## 提交材料与图片路径

| 材料 | 仓库内位置 |
|---|---|
| 第 1—7 题报告 | [homework02/README.md](../../README.md) |
| 完整 Base `.007` 与原三次重复 `.008`—`.010` | [完整 results 目录](../../specjvm2008/results/) |
| 48 次堆参数对照的逐轮结果与统计 | [结果 CSV](../../analysis/jvm_parameter/heap_parameter_results.csv)、[汇总 CSV](../../analysis/jvm_parameter/heap_parameter_summary.csv) |
| 9 次独立失败复核 `.066`—`.074` | [verification_results](../../specjvm2008/verification_results/)、[复核 CSV](../../analysis/jvm_parameter/oom_reverification_results.csv) |
| 安装、运行、失败、重复、GC 日志 | [logs](../../logs/) |
| 正文使用的 8 张终端截图 | [images/terminal/2026-10-08-set2](../../images/terminal/2026-10-08-set2/) |
| 命令、来源哈希与截图日志 | [evidence/terminal_screenshots/2026-10-08-set2](2026-10-08-set2/) |

主报告的图片使用相对于 `homework02/README.md` 的 `images/...` 路径，来源索引使用相对于本文件的 `../../images/...` 路径；均不依赖本机盘符、临时目录或外部图床。图片及对应记录随同 Markdown 进入 Git 提交，推送同一分支后即可按仓库相对路径引用。首轮校准截图另行保留，不替换正文采用组。

[Git 图片校验器](../../scripts/screenshots/verify_git_assets.py)直接读取暂存区或提交树，检查路径大小写、图片格式、截图及来源文件是否入库，并比对截图哈希；本地文件存在但未进入 Git 的情况会报错。整理提交前的完整验收记录见[提交准备日志](2026-10-08-set2/commit_preparation_verification.txt)。

Windows 原生采集记录保留 CRLF 与控制台空格填充，不为通过格式检查而改写日志。`.gitattributes` 仅对这些 JSON/TXT 记录设置相应空白检查口径，仍按 `-text` 原样入库；报告和代码的空白检查保持启用，图片与来源文件内容由哈希校验。

## 采集方法与文件位置

启动宿主 Windows 的**可见 conhost + PowerShell 终端**，实际执行[显示脚本](../../scripts/screenshots/show_terminal_evidence.ps1)，完成文件查询后将终端置前，以 `System.Drawing.Graphics.CopyFromScreen` 直接读取桌面像素。DWM 可见窗口边界用于限定截图区域；未绘制、拼接、改写终端文字，没有以日志渲染 PNG 冒充屏幕截图。每个窗口在 PNG 和元数据保存完成后才关闭。

正文采用 `2026-10-08-set2` 下的 **8 张截图**，采集于北京时间 2026-10-08 23:09:54—23:10:53。`2026-10-08` 下的首轮 3 张校准截图和日志另行保留，未插入正文；首轮当前 Java 的 stderr 虽在真实屏幕出现，却未进入 PowerShell transcript，正式采用组已在命令内部 `2>&1` 合并并重新采集。

每张图的同名 `.json` 保存采集时间、精确执行脚本块、输入文件相对路径及 SHA-256、窗口坐标、可见行数、PNG 哈希、显示脚本哈希；`.txt` 是该终端实际 transcript。界面的 “Read-only step” 是步骤说明，**不是逐字完整 shell 命令**；精确命令以 `.json.commands` 和显示脚本为准。窗口顶部是可重执行的显示脚本入口。

| 正文位置 | 截图 | 原始来源 / 含义 | 命令和来源记录 | 实际终端日志 |
|---|---|---|---|---|
| 第 2 题，图 1 | [历史环境](../../images/terminal/2026-10-08-set2/historicalenvironment.png) | `environment_info.txt`、`base_run.log`；历史 OS/CPU/Java/JAVA_HOME/启动命令 | [JSON](2026-10-08-set2/historicalenvironment.json) | [TXT](2026-10-08-set2/historicalenvironment.txt) |
| 第 2 题，图 2 | [当前环境](../../images/terminal/2026-10-08-set2/currentenvironment.png) | CIM、WSL 系统查询和 `java -version`；不是历史环境 | [JSON](2026-10-08-set2/currentenvironment.json) | [TXT](2026-10-08-set2/currentenvironment.txt) |
| 第 2 题，图 3 | [完整 Base](../../images/terminal/2026-10-08-set2/base.png) | `.007.txt`、`.007.raw`；日期、11 组、421.24、compliant | [JSON](2026-10-08-set2/base.json) | [TXT](2026-10-08-set2/base.txt) |
| 第 5 题，图 8 | [compress 三次重复](../../images/terminal/2026-10-08-set2/repeats.png) | `.008/.009/.010` 六份 raw/TXT；从原始 TXT 计分值复算 SD/CV | [JSON](2026-10-08-set2/repeats.json) | [TXT](2026-10-08-set2/repeats.txt) |
| 第 7 题，图 10 | [堆参数矩阵](../../images/terminal/2026-10-08-set2/heapmatrix.png) | 原 48 次的 raw/TXT/运行/GC 日志及结果 CSV | [JSON](2026-10-08-set2/heapmatrix.json) | [TXT](2026-10-08-set2/heapmatrix.txt) |
| 第 7 题，图 15 | [Derby GC](../../images/terminal/2026-10-08-set2/derbygc.png) | 已校验 CSV 与 Derby 原始输入；两种窗口分别注明 | [JSON](2026-10-08-set2/derbygc.json) | [TXT](2026-10-08-set2/derbygc.txt) |
| 第 7 题，图 17 | [9 次 OOM 复核](../../images/terminal/2026-10-08-set2/oomsummary.png) | 独立 `.066`—`.074` raw/TXT、运行和 GC 日志 | [JSON](2026-10-08-set2/oomsummary.json) | [TXT](2026-10-08-set2/oomsummary.txt) |
| 第 7 题，图 18 | [OOM 原始示例](../../images/terminal/2026-10-08-set2/oomraw.png) | FFT large / 512 MiB / Run1 `.069` 原始 log/meta/TXT | [JSON](2026-10-08-set2/oomraw.json) | [TXT](2026-10-08-set2/oomraw.txt) |

报告开头统一说明：前序实验时忘记及时截屏，撰写报告期间根据保存的日志、原始结果和实验记录，重新执行读取、汇总与验证命令，复现结果展示后截图；未重新运行性能实验，实验时间以原始记录为准。各图图注只说明图中内容，当前环境检查仍与正式实验环境区分。没有新性能 Result ID。

第 1 题用已有官方资料解释；第 3、4 题保留 workload 与官方比较的数据表/分析图；第 6 题保留失败定位和解决过程。图 4—7、9、11—14、16 明确属于 SPEC reporter 或数据分析图，不称为原生终端截图。

## 只读验证与原始证据保护

采集前实际执行的校验见[采集前验证日志](2026-10-08/pre_capture_verification.txt)：核心 raw/TXT、原 48 次、GC 增强统计、9 次独立失败复核全部通过。采集窗口中再次执行相应 `--check`。统计没有手工打印成模拟运行输出；三次重复的均值、样本 SD 和 CV 由[只读计算脚本](../../scripts/screenshots/summarize_repeats.py)从原始文件计算。

保留了任务开始时的[旧清单快照](2026-10-08/original_evidence_manifest.csv)。旧总验证把 mtime 当成实验内容，Git 检出后 1,124 个 mtime 均变化，但所有初始内容哈希一致。已最小修改清单检查：验证路径、角色、字节数和 SHA-256，mtime 仅作为历史参考；仍会拒绝真实内容变化。报告改为老师第 1—7 题后，仅同步相关校验器的章节定位。原始 Base、48 次矩阵、9 次复核、成绩 CSV 与原日志均不修改。

本次只读验收命令（从仓库根目录执行）：

```powershell
pwsh -NoProfile -File homework02/scripts/verify_submission.ps1
python -B homework02/scripts/jvm_parameter/build_optional_data.py --check
python -B homework02/scripts/jvm_parameter/build_enhancement_data.py --check
python -B homework02/scripts/jvm_parameter/build_oom_reverification.py --check
python -B homework02/scripts/jvm_parameter/verify_optional.py
python -B homework02/scripts/jvm_parameter/verify_enhancement.py
python -B homework02/scripts/jvm_parameter/verify_oom_reverification.py
python -B homework02/scripts/screenshots/verify_screenshots.py
```

[本次最终验收日志](2026-10-08-set2/final_verification.txt)独立于原有 `logs/*verification.log`，不覆盖历史验收记录。截图身份/路径、来源哈希、完整关键输出、图注、章节、全部原始证据保护及工作区范围由新增截图校验器检查；最终 8 张图已逐张目视核对。

浏览器显示检查见[渲染校验日志](2026-10-08-set2/render_check.txt)：Pandoc 按 GFM 渲染 Markdown，Chrome 本地检查 **18/18 张正文图片加载成功**；逐张检查终端原图，并目视核对报告开头、Base 的截图与图注、Derby 的截图/图注/机制图。浏览器生成的报告预览仅作布局 QA，未列为终端截图。整页预览的自动滚动截图出现空白，改用对应 Markdown 小节预览完成目视检查；正文图片加载检查正常，不涉及性能运行。

## 重新读取 / 手动截图的最短步骤

本次没有待补截图项。若以后需要在另一个桌面重新采集，打开 Windows PowerShell 7，进入实际目录，执行：

```powershell
cd E:\software_system\course_repo\homework02
.\scripts\screenshots\show_terminal_evidence.ps1 -View Base -Session manual-new-session
```

将 `Base` 依次替换为 `HistoricalEnvironment`、`CurrentEnvironment`、`Repeats`、`HeapMatrix`、`DerbyGC`、`OOMSummary`、`OOMRaw`。每个 Session/View 不可重复，脚本拒绝覆盖。调整字体与窗口让命令、来源和关键输出同屏，用 **Win+Shift+S** 截取真实终端；保存到独立目录。无 `-Capture` 只显示和记录证据，不生成 PNG。

自动原生截图需通过可见 `conhost.exe` 启动并添加 `-Capture`，否则不能以隐藏工具输出冒充真实屏幕。此次自动采集的完整入口和实现均在显示脚本中；**不要执行 `run_base.sh`、`run_base.ps1` 或任何性能运行脚本来补历史截图**。

## 采集时遇到的问题

- 原生终端最大行数受显示器/DPI/字号限制，最初 `WindowSize=48` 报“不能高于 45”；调节先后顺序时又触发缓冲区不能小于当前窗口的错误。只发生于截图窗口设置，未启动 benchmark。最终按 `MaxPhysicalWindowSize` 与实际窗口尺寸调整，PNG/JSON 记录实际行数，若内容超出可见区则拒绝采集。
- Git 检出后的 mtime 与旧清单不同：已按上述稳定字段验证，不以此绕过内容校验。
- 首轮 `java -version` 的原生 stderr 未进入 transcript：采用组明确 `2>&1`，保留了完整版本输出；旧校准资料未覆盖。

以上问题与历史实验失败分开记录。未新增、修改或回填任何性能数据。
