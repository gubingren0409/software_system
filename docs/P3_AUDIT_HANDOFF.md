# P3 审计入口（首个正式批次执行中）

授权：用户要求 P2 完成后开始 P3。P2 保留基线
`37b10327909d9d4134a2d4d68aae0e27b4fc483c` 已推送，尚未获得外部审计通过。

当前新增 P3 独立轨迹、私有观测恢复、预算前缀和各候选独立复测，C 核心与 P2 测量/
搜索 schema 2 不变。[冻结规则](P3_PROTOCOL.md)、[campaign 配置](../configs/p3_campaign_protocol.json)、
[运行器](../autotuner/campaign.py)、[只读后处理](../scripts/audit_p3_evidence.py)、
[受控回归](../tests/test_campaign.py)、[干净验收脚本](../scripts/run_p3_clean_validation.py)。

初始资源只读快照：[2026-10-09 开始快照](../evidence/p3/environment/start_20261009.json)。
正式/干净验收内容提交：`e308bfb873e6811c50ad685a979af345302fda8d`。
campaign schema 1 规范化哈希：
`bf7e5fd63656c6bb68714cffd8a060bac8e17db15138ef1b88e8b59b6d5c7461`。
独立归档 `/var/tmp/matrix-autotuner-p2-content-e308bfb873e6811c50ad685a979af345302fda8d`
没有 .git、初始 pycache 或 PYTHONPATH 依赖；旧 p2 名称来自复用导出器，不代表内容
仍是 P2。Git/实际执行身份分别记录，老师原件哈希再次确认一致。

## 已完成的验收（仅诊断）

- [干净验收摘要](../evidence/p3/validation-e308bfb/summary.json)：PASS，24 Python
  文件 AST、CLI帮助、20唯一配置、40项单元测试、verify_p1、空缓存 n17/O2/s8 fresh
  及正确性通过；[命令、stdout/stderr/退出码](../evidence/p3/validation-e308bfb/commands.json)。
- [n130全十轨迹审计](../evidence/p3/validation-e308bfb/diagnostic_audit/audit.json)：
  120次配置评估（每轨迹内去重，跨轨迹独立重测）、720次搜索执行+19组候选复测114次，
  共834次新执行；全局配置空间仍只有20种。所有轨迹
  仅使用自身观测；已完成批次续跑前后ID集合完全相同，没有新增目标执行。
- [真实暂停恢复审计](../evidence/p3/validation-e308bfb/pause_resume_audit/audit.json)：
  保存第一配置的1条部分样本，恢复后留作放弃记录并完整重测；12次配置及1组复测
  共78条有效完整执行、1条放弃记录。旧尝试没有被补成五次测量。

## 正式状态与证据

首批冻结为 seed=20261008 的随机/贪心各12配置（4/8前缀），各预算不同候选独立
复测。完整阶段仍是10条轨迹；本入口未宣称五种子稳定性完成。

- [固定Git身份](../evidence/p3/content-e308bfb/git_identity.json)，本地实际使用的CRLF字节
  SHA-256为`30ced7f0323364c604ebcc0983bb8ede0a2bc03a04521efa40f67ebe60d4ec67`；
  Git规范化LF内容SHA-256为`3fe4e5ef2d1bf2e62f1981a3469e7b764069605ba654ae05f4afe44176c5c10f`。
  两者解析内容相同。28行CRLF、Git blob为`398064667de4b8b0870824a61cb995dc421645d3`；
  [字节身份记录](../evidence/p3/content-e308bfb/identity_bytes.json)。
  不能把通用build/p2身份文件覆盖后直接用于旧实验续跑。
- [正式session与身份](../evidence/p3/campaign-e308bfb/session.json)、
  [检查点](../evidence/p3/campaign-e308bfb/checkpoint.json)、
  [启动命令及控制台记录](../evidence/p3/formal_controller.json)、
  [门禁](../evidence/p3/campaign-e308bfb/gates/)、
  [构建/reference manifests](../evidence/p3/campaign-e308bfb/manifests/)。
- setup与n4096 reference已经完成，data SHA-256与P2完全相同。01:18只读正式门禁
  PASS；setup后首配置门禁曾因宿主内存低于2GiB而拒绝。随后资源恢复，O1/s64启动。
  没有放宽门槛或停止其他应用。[初始门禁快照](../evidence/p3/environment/pre_formal_20261009.json)。
- [逐次原始证据](../evidence/p3/campaign-e308bfb/trajectories/)、
  [阶段完整性复核](../evidence/p3/postprocessing/audit.json)。audit PASS仅表示已保存
  记录一致，部分状态不得解释为正式阶段全部PASS。当前只读复核并未
  改变正在运行的策略数据；空预算表不构成搜索比较结论。

01:42进度快照：随机种子20261008完成1/12配置，首配置O1/s64五次中位数
54.993200129秒、均值54.7871725618秒、样本标准差0.6600945951秒、CV=1.2048%、
MAD=0.586264908秒；六次执行均fresh/force、退出0并验证16777216项、零错配。
O0/s24预热472.340622065秒已通过，计分五次尚未完整；贪心轨迹尚未开始。
这是首批1/24配置、全计划1/120次配置评估，不能宣称完成正式P3比较或候选复测。

本阶段仅对一个自有reference文件做过一次POSIX_FADV_DONTNEED建议，数据仍在且
操作前哈希相同。[操作记录](../evidence/p3/environment/reference_page_advice_20261009.json)
表明建议成功返回，但不证明Windows回收；01:30:41门禁恢复早于01:31:01操作，
不能归因。操作发生于O0预热期间、非计分样本；不重复作为新测量策略。该诊断脚本
与绘图脚本是交付辅助文件，不替换e308bfb的正式归档/测量模块。后台I/O扰动未量化。

继续同一批次必须使用相同归档、身份和campaign根目录；`--resume`会核验全部原始
样本、内容、编译器、输入/reference、配置与协议。已有运行器存活时不要重复启动，
全局文件锁会拒绝第二个P3运行器。需要完成其余种子时将limit增至10。

```bash
cd /var/tmp/matrix-autotuner-p2-content-e308bfb873e6811c50ad685a979af345302fda8d
PYTHONDONTWRITEBYTECODE=1 env -u PYTHONPATH python3 -m autotuner campaign \
  --content-sha e308bfb873e6811c50ad685a979af345302fda8d \
  --git-identity /mnt/e/software_system/project01/evidence/p3/content-e308bfb/git_identity.json \
  --campaign-directory /mnt/e/software_system/project01/evidence/p3/campaign-e308bfb \
  --trajectory-limit 2 --resume
```

待审计：策略是否严格使用自身观测；每组是否完整 fresh/force；失败与部分样本是否
不计分；预算前缀与候选复测是否分离；资源 gate/暂停身份是否完整；P2 原表比较与
P3 跨 session 时间差是否明确区分；未校准时钟/环境压力是否要求另环境重新测量。

本入口为阶段状态，不替代 P2 完整性证据或外部审计意见。最终提交 SHA 只在提交和
推送后终端交接提供，不为把文档写进自身 SHA 而循环提交。

进度快照内容提交`ec68c6cf78807c023d3ed864d16b9bb45c4ed563`另从无.git/初始pycache
的归档复核：26个Python AST及核心模块导入、CLI帮助、20唯一配置、归档中正式
记录审计均PASS。[归档复核日志](../evidence/p3/progress_archive_smoke.json)、
[快照审计](../evidence/p3/progress-archive-audit/audit.json)。该固定快照含1个完整
配置与8条完整目标执行；后续实时进度写在原campaign目录，不能把快照当最终P3。
正式target/CLI/测量/搜索/配置对e308bfb无改动，复用其40项单测和空缓存实际小规模
验收；没有在正式目标运行期间再开诊断目标。辅助绘图仅AST检查，尚无足够正式
预算前缀数据生成图或完整算法比较。
