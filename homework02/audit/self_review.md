# 三轮自审记录（A2 必做部分）

这是研究产物的自审记录，不把“脚本存在”当作“通过”。最终机器输出另见 [final_core_verification.log](../logs/final_core_verification.log)。

## Round 1 — Correctness Audit

- **逐项来源：** 从 `.007.raw` 的 operation/毫秒数重算 38 项与 11 组；与 `.txt`、`.html`、`.summary`、`.sub` 的 Composite/合规标签交叉核对。`verify_goal1.ps1` 现在还检查早期 `artifact_sha256.txt` 中六份核心文件的旧哈希，避免“重新生成 manifest 就掩盖原始文件变化”。
- **发现并修正：** 原 `verify_submission.ps1` 在 Git 查询失败时可能继续 PASS，且把选做 JVM 参数文件、无 `report.md` 等误作核心条件。现改为 Git 仓库/分支 fail-closed，仅检查本 Goal 交付物；派生 CSV、官方快照、Markdown 数字和图均有源数据复验。[最终核查脚本](../scripts/analysis/run_final_verification.ps1)还把一个不存在的 `GIT_DIR` 注入子进程，要求验证器明确失败，并把预期失败写入日志；不改仓库分支或原件。
- **时间线与异常：** OOM 日志机器时间 `15:06:31–16:00:50`、正式 Base `16:10:03–18:25:15` 不重叠；`install.log` 原头 `16:48` 不是测量日志时间。旧行保留并附校注，原始运行日志不改。Java 7 reporter 的字体异常位于测量后；文档不再写“全程无错误”。失败 OOM 也有 `EXIT_STATUS=0`，所以退出码不单独决定有效性。
- **归因审查：** 文本将“测得”、“官方设计”和“可能机制”分开，保留 raw reporter 前后双哈希缺失、主机遥测缺失、诊断与 Base 不可混用等限制。
- **官方定义复查：** 发现 `crypto.aes` 不能被简写成“纯 AES 微基准”：SPEC workload 说明还包含 DES/CBC 路径和不同长度输入。已同步更正背景与六项分析，避免拿 AES-NI 假设解释整个子项。

## Round 2 — Depth Audit

- **Workload：** 由原四项扩展为六项，增补 FFT small/large；全部 warmup/正式/Δ/% 从 raw 生成的 CSV 核查。增加 operation 不等量、组分几何平均、JCE Provider、Derby 锁/分配、Sunflow 内部并行及 SciMark 工作集边界。明确 7.08 的 small/large 分数比不是内存惩罚。
- **官方 Reference：** 搜遍 SPEC 的全部六条公开 Base，而非只保留原有 Sugon；仅后三条满足 1.01/Java 7。选 Huawei 为资源/拓扑较近的主参考、原 Sugon 为 OpenJDK 补充，拒绝把跨机倍率归因于核心数。两份官方 HTML 快照和 14 个组分有哈希/单元格复验。
- **额外验证价值：** `perf`、`time -v` 在 WSL2 可启动，故以独立 `.015`/`.016` 做 `compress` 与 `sunflow` 两个单项诊断；发现后者的整进程上下文切换明显更多，符合其内部多线程设计。`perf context-switches:u=0` 与 `time -v` 非零相冲突，被排除。计数覆盖 whole process 且虚拟化映射未校准，不把它升级为正式迭代的瓶颈判决。缺少可靠温度/历史遥测时，不再做低信息量的大量重复来伪证热降频。
- **新旧环境比较：** 当前诊断时 WSL kernel `6.18.40.1`，正式实验时记录为 `6.18.33.2`；在诊断文档增加这一额外混杂因素，并用当时的遥测可用性日志限定 Windows CPU load 快照的解释范围。

## Round 3 — Presentation Audit

- **图表：** 保留官方 `.007/images/all.jpg` 的原样拷贝作证据；另外四图由已核验 CSV 生成。Base 组图把 startup 放在独立尺度，官方图只画无量纲同名倍率；warmup 图曾有标签压在深色柱上，已改为独立数值栏；三次重复图明确写出非零、放大的 y 轴与 `n=3`，防止视觉过度暗示。
- **冗余与导航：** 不重写现有 README；方法、环境、workload、官方比较、重复与诊断各自独立，审计/风险文件说明证据边界。附可复现脚本说明、CSV 与最终运行日志，而非只放静态插图。
- **最终检查：** 对代码/分析文档执行限定范围的 `git diff --check`、重新生成图、执行 `verify_goal1.ps1` 和 `verify_submission.ps1`，对 Markdown 相对链接作存在性检查。新 SPEC 输出和 `perf` 原始日志保留工具自身的尾随空格与换行，不为通过风格检查而改写一手证据。通过不代表已完成 SPEC 官方投稿或获得对性能差异的单因果证明。
