# 工作记录

时间均为 Asia/Shanghai，日期 2026-10-08。本文记录 P0 的实际操作、失败与修复；
正式报告只引用稳定结论。

## 材料、仓库与分支

- 11:57-11:59：从 `E:\software_system` 扫描 PDF、源码、构建文件和 `AGENTS.md`。
  找到 P1 PDF 与一份 C 源码；未发现 `AGENTS.md`；确认 P1 目录本身不是仓库。
- 11:59：确认课程仓库为 `E:\software_system\course_repo`，远程同时包含课程
  Gitea 与 GitHub；原 `homework02` 工作区无未提交改动。
- 11:59：首次 `git ls-remote` 失败，错误指向不可用的 `127.0.0.1:7897`。
  检查发现全局 Git proxy 指向 7897，而当前代理实际监听 10808；直接连接 GitHub
  又被 reset。未修改全局配置，改为对单次只读/推送命令显式传入
  `-c http.proxy=http://127.0.0.1:10808` 与 HTTPS 同值，远程查询成功。
- 12:00：远端 GitHub/Gitea 均无 `project01`。先从缓存的 `github/master` 建本地
  分支；在原 worktree 切换时既有 `homework02/` 因基线不同显示为未跟踪。
  文件未删除、未修改。立即切回 `homework02`，改用独立 worktree
  `E:\software_system\project01`，消除误提交风险。

## 环境和说明核查

- 独立只读核查分别负责作业要求、源码和环境；主控统一整合文件与 Git。
- PDF 使用 `pdfinfo`、`pdftotext -layout` 完整读取，并用 SHA-256 标识；PDF 仅一页。
- 环境分别在 Windows 宿主与显式 `wsl.exe -d Ubuntu-24.04` 中采集。没有输出完整
  环境变量、凭据或私钥，没有修改系统设置。
- 首次写主机环境日志因 `evidence/p0` 尚不存在而失败；创建目标目录后重跑成功。
- 初版主机采集脚本对缺失的 CMake 显示命令错误但沿用旧 `$LASTEXITCODE=0`。
  改为先检查命令存在性，缺失时明确记 `exit_code=127`。
- 在加入 Windows 版本字段后，PowerShell 的异构对象默认格式器使后续 CIM 对象
  在文件中显示为空行。为每组对象显式 `Format-List/Format-Table | Out-String` 后
  重跑，最终日志包含完整属性。
- WSL `perf stat true` 失败，退出码 2；原因是包装器找不到与
  `6.18.40.1-microsoft-standard-WSL2` 匹配的 linux-tools。按 P0 约束未安装系统包，
  将性能计数器记为不可用。

## 原始源码与诊断

- 原始源码复制前后 SHA-256 均为
  `188d011109c4470e1f41829216e8677a5c2d8f2b7c8a44215652320dbdf6de15`。
  复制目标目录首次尚不存在而失败；创建 `code/original/` 后重新逐字节复制成功。
- 独立只读分析先用临时文本注入 n=17 reference 时出现一次 printf 换行转义错误，
  GCC 报 `missing terminating " character`；修正转义并启用 `set -e` 后成功。
- 另一条临时 O0-O3 循环命令中的 `$opt` 被 PowerShell 提前展开，只生成 `mm_O`；
  改用四条显式 GCC 命令后成功。主控随后也在正式 P0 脚本中编译 O0/O1/O2/O3，
  四级均无警告，日志已入库；临时分析文件未写入仓库。
- 主控建立独立诊断副本，使用 n=65、朴素 i-j-k `long double` reference 和逐元素
  组合误差门限。老师分块循环结构保持不变；结果消费与 reference 位于计时区外。

## 有限预实验

- 12:03：运行 `bash scripts/run_p0_preexperiment.sh`，所有案例严格串行。
- 原件 O0/O1/O2/O3 无警告编译；反汇编发现 O3 的 `mulsd`/`addsd`/写回，当前 GCC 未
  消除核心计算。
- n=65 下 O0/O3 × s=8/24/64 共 6 个有效案例全部 PASS，failed_entries=0；
  s=128 两次均按原接口退出 255 并打印 `Invalid input values.`。
- O1 调试构建在 Valgrind 下以 s=24 运行，退出 0、0 errors；唯一一次 4,096-byte
  分配已释放，未发现非法访问、未初始化值使用或泄漏。
- 首次用 PowerShell 内联 Bash 命令追加 Valgrind 退出码时，跨 shell 的 `$code`
  处理导致记录为空；虽然 Valgrind 输出已经是 0 errors，该记录不合格。改为直接
  运行仓库脚本，最终命令文件正确记录 `exit_code=0`，自动检查也通过。
- 验证脚本报告 `preexperiment_verification=PASS`。没有运行 n=4096，没有启动完整
  20 组合搜索，也没有把诊断耗时用于最优配置判断。

## Git 完成记录

主内容提交 `a62a33c56851e319bb19a8a10ae67ac64106a2c0` 已推送至 GitHub
`project01`，`ls-remote`、显式 fetch 后的跟踪引用与本地 HEAD 三者一致。第一次
复核 fetch 遗漏了单命令 proxy 覆盖，仍访问失效的 7897 并失败；使用 10808 的
同一只读命令重试成功。原始结果见 `evidence/p0/remote_verification.txt`。

加入该远程记录后会产生最后一个文档提交。为避免“文档包含自身 SHA”造成循环，
最终固定 SHA 及其远程一致性只在终端交接消息中给出。
