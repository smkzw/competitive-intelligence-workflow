# ZCode 审计输入处置评审：ci-rebaseline-rebuild

- **评审日期**：2026-09-04
- **评审对象**：`reviews/zcode_ci_engineering_audit_20260902.md`、`plans/zcode_revised_roadmap_20260902.md`、`plans/zcode_execution_plan_v2_20260902.md`、`docs/specs/competitive-intelligence-workflow-design-v1.3-draft.md`
- **处置者**：R1 contract worker（仅输出处置证据；Codex 负责最终接受）
- **规范结果**：`docs/specs/competitive-intelligence-workflow-design-v1.3.md`
- **同步结果**：`plans/competitive-intelligence-workflow-roadmap-v1.3.md`、`plans/codex_execution_ci-rebaseline-rebuild-v3.md`、`.trellis/tasks/09-02-phase-10-task-106-rc-freeze/{prd,design,implement}.md`

本文只处置 ZCode 输入，不修改 ZCode 原文和 v1.2。当前用户批准决策优先；ZCode 的事实观察可保留为风险证据，建议只有在与当前 scope 和安全边界一致时才升级为合同。

ZCode 文档使用的 `D71–D78` 在本文仅是逐项迁移标签，不构成这些条款此前已获批准的独立证据。它们的当前处置效力来自用户批准的 2026-09-04 重基线计划及其后续明确裁决。

---

## 1. 处置分类

- **ACCEPT**：与当前批准决策一致，进入 v1.3 canonical 和执行合同。
- **MODIFY**：方向有价值，但必须按当前产品边界、证据要求或旧根禁止边界改写后采用。
- **DEFER**：保留为未来版本/另行授权候选，不进入 v1 或当前 R0–R6 验收。
- **REJECT**：与当前批准决策冲突，不能以“恢复需求”或已有代码进入 v1。

---

## 2. 逐项处置

| ZCode 输入 | 处置 | v1.3 canonical 结论和理由 |
|---|---|---|
| P0-1：dirty tree / provenance 断层 | **ACCEPT + BOUNDARY** | 建立显式 source set、source/bundle/package/catalog/RC 摘要和 dirty fail-closed；不得 reset、clean 或覆盖用户改动。 |
| P0-2：局部质量门 false-green | **ACCEPT** | 使用单一全量 gate，worker 必须声明检查范围、命令、输出和未运行项；局部绿灯不等于接受。 |
| P0-3：Q1–Q6 未裁决 | **ACCEPT（裁决同步）** | Q1 复合 SHA-256；Q2 双层 receipt；Q3 仅 legacy-absence future owner；Q4 治理工具 sidecar；Q5 安装入口/治理 verifier 分离且同 RC；Q6 artifact manifest 实算 formats=1。 |
| 建议 `research-package` 为引擎唯一科学入口 | **MODIFY** | 采用 package-only deterministic ingress，但不强迫用户手填 package；公共入口接受一句话并由宿主 Agent 自主研究、初筛、编包。可选 typed package 走同一严格校验链。 |
| 引擎无任意 HTTP，宿主负责判断性检索 | **MODIFY** | 核心架构采用宿主自主研究 + 确定性引擎。任何直接拉取器必须明确白名单、可限速、可回放、带回执且不能成为核心或离线恢复前提；Yaozh 不升级为必需 API。 |
| F1 `research scaffold` CLI | **DEFER** | 一句话自主入口和可选 package 已满足当前用户合同；骨架 CLI 不是 v1 必需交付。未来若实现，不能把编包责任转给非技术用户。 |
| D71：药智网企业版纳入来源 | **MODIFY** | 保留为可选商业数据库、浏览器会话辅助来源；只能支持身份/中国状态/管线/关系线索，疗效安全数值不直接采纳，永不成为唯一权威。凭据、Cookie、令牌不进任何 artifact。 |
| 药智网 API 双件套 F2 | **DEFER / MODIFY** | 当前 v1 不把 Yaozh API 拉取器作为必需组件。后续实现需重新确认接口、凭据安全、分页限速、回执和来源角色；浏览器会话可作为可选路径。 |
| D73：首版仅 HTML | **ACCEPT** | v1 `formats=1`。PDF、HTML-PPT、PPTX 代码/历史可保留，但不进 v1 runtime bundle、默认 preflight、artifact closure 或验收。 |
| 四格式 coverage 降为 HTML 自洽 | **MODIFY** | 保留 `coverage_set/coverage_projection` 机制，但 v1 只生成 HTML projection，差异必须为零；不生成任何 deferred 格式 artifact。 |
| D74：CSV/XLSX 导出 | **REJECT FOR V1** | 当前锁定产品边界明确不生成 export files。HTML 提供完整折叠表；导出需新版本决策、schema、筛选/快照和安全合同。 |
| F4：B 雷达图 | **REJECT FOR V1** | 当前锁定边界明确不提供 radar chart；保留原始可比图、完整表和证据链，不用归一化图替读者做裁决。 |
| F5：证据成熟度矩阵 | **REJECT FOR V1** | 当前锁定边界明确不提供 evidence-maturity view。`disclosure_maturity` 和设计类型仍是事实字段，不能合成为分数或另建视图。 |
| F7：安全热图补强 | **MODIFY / ACCEPT BASE** | 安全热图属于 B 的基础可视化；数值、缺失状态、对照语境、分母和图例必须清晰。不得借 F7 引入雷达或成熟度矩阵。 |
| F8：刷新变化亮点页 | **MODIFY / DEFER** | 手动刷新、历史快照和 added/changed/withdrawn diff 是 v1 合同；单独“变化亮点”页不是首版必需，不能变成自动监测。 |
| D77：移除监测、刷新手动 | **ACCEPT / CLARIFY** | 不建设、不分发、不验收 scheduled monitoring、后台轮询或无人触发刷新；refresh 由用户显式触发，触发后来源复核、diff 和 HTML 重建自动完成。 |
| D76：Skill 包 + 关键词触发 | **ACCEPT** | 采用版本化 Skill bundle、公开入口和中文触发词“竞品调研”；入口文案产品说明书化，错误提供非技术中文修复指引。 |
| C1–C3：gate、git 白名单、证据分层 | **MODIFY** | gate、显式 source set、运行证据归档和不复制全量产物方向采用；具体 git hook/治理瘦身不得静默改动用户文件或降低科学/视觉证据。 |
| C4：对旧根 `chmod -R a-w` | **REJECT IN CURRENT SCOPE** | 当前 rebaseline 和 Task 10.6 明确不读取、inventory、chmod、修改或 absence-check 真实旧根。旧根处置需另行授权和独立合同，不能提前执行。 |
| C5：六标准视觉 checklist | **ACCEPT** | 每报告类型使用逐项视觉 checklist，必须有实际 Chromium/WebKit 截图锚点；验证者只能 PASS/VETO。 |
| C6：HTML-PPT 留白下限 | **DEFER** | HTML-PPT 不在 v1 runtime/验收；不把其历史视觉建议转成首版约束。未来恢复格式时另行恢复完整合同。 |
| A/B/C 真实项目投产 QC loop | **MODIFY** | 真实来源报告和 QC loop 可作为产品/验收输入，但当前 R0–R6 仍须完成独立 8×3=24 矩阵；不能用少量真实项目替代矩阵。 |
| 旧工程 burn-in 后删除 | **DEFER / BOUNDARY** | 作为未来受控切换候选保留；本 worker 不读取、inventory、修改、删除或 absence-check 旧根，Task 10.6 只保留 `legacy-absence` future owner。 |
| 24 个真实门户矩阵 | **ACCEPT / STRENGTHEN** | 当前锁定矩阵为八适应症 × A/B/C=24；每项用新鲜 source/run/job/session/artifact/verdict，独立门户、科学和视觉证据闭合。 |
| B 终点/时间窗兼容分组 | **MODIFY / ACCEPT** | 采用模型辅助整体临床构念 + 确定性冲突守卫。48/50 周等近窗口在定义、方向、单位、估计目标、分母、分析集和分析形式兼容时共框并标差异；其余拆分。 |
| 手工下载/人工中断规则 | **MODIFY** | 只有必需论文/附件自动路径穷尽后建立一个 Markdown manual-supply gate；用户一次响应后同一快照不重复追问。文件按内容核验后在投递目录原地规范重命名；先保存原名、SHA-256、DOI/登记号、新名和碰撞检查，不复制、不移动、不修改字节。 |
| “formats=4”冻结信号 | **REJECT** | 被当前 HTML-only 决策取代。冻结只允许 `formats=1`，且由当次 HTML artifact manifests 实算。 |

---

## 3. 当前批准决定与 ZCode 输入的关键冲突

### 3.1 自主研究和研究包不是二选一

ZCode 把宿主手工检索和 package 交接描述为事实架构，这一观察有效；但将其收敛成“用户必须准备 package”会违反当前最小输入合同。canonical 采用两层：公开入口负责一句话自主研究，确定性引擎只接受严格 typed package。两种入口的科学门槛、来源策略、状态和独立 QC 完全相同。

### 3.2 HTML-only 不等于恢复所有呈现增强

ZCode 正确识别了 v1.2 与用户 2026-09-02 裁决的格式范围变化，但其 CSV/XLSX、雷达和证据成熟度建议不能进入当前 v1。当前锁定产品决策明确排除 export files、radar chart 和 evidence-maturity view；完整折叠表和事实字段保留，不能将被拒绝功能悄悄改名后恢复。

### 3.3 Yaozh 是可选辅助来源，不是新的单一真源

ZCode 建议的 API 端点和 connector 方向仅是实施线索，不能升级为当前必需组件。Yaozh 访问采用一次性可用性询问和用户浏览器会话辅助；缺失它不能等于无证据，官方登记/监管/论文路线仍是核心。

### 3.4 旧根只读要求不能绕过当前边界

ZCode 建议 `chmod` 和旧根盘点，是旧工程治理风险的有效证据；当前执行边界明确禁止读取、inventory、chmod、修改和 absence-check 真实旧根。该建议因此只登记为未来受控 handoff，不在 R0–R6 或 Task 10.6 预执行。

---

## 4. 已同步的 Task 10.6 合同要点

Task 10.6 的三份 active 文档已按以下结果同步，尚不代表任何阶段被接受：

1. 10.6A 不创建 RC；只审计/测试 provenance、bundle、fresh-install、recovery 和 receipt；
2. 10.6B 使用显式 release source set 和隔离 clean worktree；不触碰真实旧根；
3. 10.6C 从最终安装 bundle 执行 8×3=24 个 HTML 门户和三宿主回执；旧 run/job/session/artifact/verdict 拒绝；
4. 10.6D 执行恢复包隔离演练、手动刷新、代表性 HTML 重建、owner-stage receipts 和独立验收；
5. 发布状态只保留 `DEVELOPMENT_CANDIDATE → RC_FROZEN → RELEASED`；`RC_FROZEN reports=3 formats=1 hosts=3 recovery=passed pending_future=1` 只能在全部门通过后输出；`legacy-absence` 是唯一 future owner，Task 10.6 不得宣称其已通过；
6. PDF/PPT、导出、雷达、成熟度和定时监测不进入首版 bundle 或 artifact closure；
7. P0/P1 必须为零；P2 必须修复或有证据的明确 non-impact disposition。

---

## 5. 未决但不阻断 R1 的实施细节

- Skill 包 manifest 的版本字段和最终安装文档排版在 R5 定稿，但触发词基线为“竞品调研”；
- Yaozh 本地安全配置的具体实现可在后续实现任务确定，原则固定为不入库、不入包、不入日志、不入回执；
- future release 是否恢复 PDF/PPT、导出、雷达、成熟度或监测需要新的用户决策和 release-scope 版本，不得由实现 worker 自行恢复；
- 真实旧根切换、删除和 absence closure 需要单独授权、精确 inventory、恢复包和独立验收。

这些细节不能被解释为当前 v1 的缺口，也不能阻止 R1 canonical contract 生效。
