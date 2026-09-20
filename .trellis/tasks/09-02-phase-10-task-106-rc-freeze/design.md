# Task 10.6 设计：首版 HTML-only RC、全矩阵与恢复

## 规范依据与状态

- Canonical 设计：`docs/specs/competitive-intelligence-workflow-design-v1.3.md`
- Canonical 路线图：`plans/competitive-intelligence-workflow-roadmap-v1.3.md`
- Canonical 执行计划：`plans/codex_execution_ci-rebaseline-rebuild-v3.md`
- ZCode 处置：`reviews/zcode_disposition_ci-rebaseline-rebuild_20260904.md`

本文件只定义 Task 10.6 的实现与验收合同；所有 checklist 仍由 Codex 在真实证据通过后勾选。Task 10.6 不读取、inventory、validate、apply、chmod、删除或 absence-check 真实旧根。

## 首版 release scope

首版只验收 A/B/C 三个独立多页面 HTML 门户。八个适应症分别运行 A、B、C，共 24 个真实来源门户；三宿主消费同一个最终 HTML-only bundle。PDF、HTML-PPT、PPTX、CSV/XLSX、雷达图、证据成熟度视图、scheduled monitoring、后台轮询和无人触发刷新不进入首版 bundle、默认 preflight、artifact closure 或验收集合。用户手动触发后，来源复核、差异识别、快照和 HTML 重建自动完成；每个结构化数据集使用适当图形和默认收起、原位展开的同一事实集完整表；每页底部只有一个聚合外部来源区，用户可见表格不含内部 locator。

公开入口是一个安装 Skill，触发词为“竞品调研”，支持一句话自主研究和可选 typed `research-package`。未指定报告类型时使用宿主原生 Ask 解释并选择 A/B/C，历史截止日可选，每个新项目只询问一次是否具备 Yaozh 访问条件。宿主 Agent 将自主研究结果编成严格 package，确定性引擎只从 package、已接受事实和锁定快照继续。Yaozh 为可选浏览器会话辅助商业来源，不是唯一权威，凭据/令牌不入 artifact。

控制图由应用自身持有并版本化。LangGraph 不是基础依赖；未来如提供适配器，也只能消费同一类型化节点/事件合同，不得持有科学真源或成为三宿主一致性及离线恢复的前提。

A/B/C 候选一律在 HTML format 后进入 `rendered_unreviewed`。review request 必须绑定生产上下文、事实谱系、HTML manifest 与站点目录真实字节；只有安装包内 `review issue` 启动独立宿主进程后同源生成的 receipt 与 issuance record、正式 verdict 字节和晋级时有效期全部核验通过，才可单向晋级。研究包自审不能授权报告，手写自洽 receipt 不能授权报告；等待回执期间允许任意次纯复用 resume，验收按 `run.node.reused` 来源图闭合而不是固定两次运行。

登记关联的主要结果、延长期主要结果、关键长期暴露/安全性发表物必须检查；综述、普通 ad hoc 和无关探索性分析默认排除，分类由规则、模型和阻断边界的独立复核共同完成。必需论文不可访问时只建立一个 Markdown manual-supply gate；用户一次响应后同一快照不得重复追问。补件核验通过后在投递目录原地规范重命名，操作前记录原名、SHA-256、DOI/登记号、新名和冲突检查，不复制、不移动且不修改文件字节。关键缺失/异常零值需要两条不同替代恢复检索和 clean-context 独立最终复审，缺独立审查能力即预检失败。

B 的模型辅助整体临床构念分组必须受确定性冲突守卫：48 周和 50 周等近窗口仅在构念、定义、方向、单位、估计目标、分母、分析集和分析形式兼容时共框并标差异；不兼容时拆分。

B 气泡图只使用版本化临床预设：疗效×总体安全性（大小为治疗组样本量/暴露量）、疗效×严重风险（大小为有效分析集规模）、持续性×停药风险（大小为长期暴露量）；仅完整临床语义基本可比时同图。常规输出为事实汇总和中性差异，不默认排名、综合评分或研发建议。

## 分阶段状态机

### 10.6A 合同、provenance 与 recovery producer

**输入**：Task 10.5 已封存检查点、当前工作树、R0 inventory（若已接受）、本设计和 recovery schemas。
**步骤**：

1. 审计 bundle/fresh-install/full-matrix/recovery/receipt 当前字节和来源；worker 报告只是输入，不是接受结论。
2. 扩展 bundle manifest 和构建/验证合同，保存 `source_commit`、package/catalog/release-scope 摘要和 required final content；dirty tree、source mismatch、未知字段和缺 required content 在输出前失败关闭。
3. 固定 RC identity：`sha256(canonical_json({schema_version, source_commit, bundle_sha256, package_manifest_sha256, catalog_sha256, release_scope}))`。Git commit 即使是 SHA-1，也不能直接冒充 SHA-256。
4. 保留 pre-RC `host-receipt` 和 acceptance root final owner-stage `release-case-receipt` 双层；freeze record 显式绑定两层而不静默改 catalog 指针。
5. 生成严格 `recovery-package-v1` manifest/receipt schema、构建器和只写隔离临时目录的恢复演练测试。
6. 治理 cutover/legacy 工具作为 sidecar，不进入安装运行时 bundle；工具摘要只写 RC governance record。

**阶段门**：A 阶段不得创建 RC commit、写外部 acceptance root、调用真实宿主、安装最终 bundle 或触碰真实旧根。只有 provenance/required-content/dirty/mismatch/unknown-field/recovery focused tests 和相邻回归由 Codex 审计接受后才能进入 B。

### 10.6B Source closure 与唯一 RC commit

**步骤**：

1. 建立显式 release source set：批准源码、typed Skills、schema、HTML 合同、必要本地资产、测试、脱敏 fixtures 和治理记录；排除 runs/logs/tmp/cache/凭据/旧可运行流水线/未批准归档。
2. 运行唯一全量 gate、schema/package/legacy reference scanner 和 Phase 0–10 确定性回归；metrics 必须填声明的检查范围、命令、输出和未运行项。
3. 确认 research-package schema、GateSpec、宇宙 closure、manual gate、双重恢复、clean-context review、A/B/C 页面合同和 HTML-only scope 均有版本摘要。
4. 在隔离 clean worktree 建立唯一 RC commit/tag；不使用 reset/checkout/clean 获取“干净”，并保存用户改动未被覆盖的证据。

**阶段门**：source set 完整、gate 全绿、所有漂移有处置、唯一 RC identity 可计算且 Codex 接受后才能进入 C。任何局部 gate 绿灯、旧摘要或未解释修改都停止。

### 10.6C Final bundle、fresh install 与 24 门户

**步骤**：

1. 从唯一 RC commit 构建 HTML-only bundle，逐文件核对 manifest、source/package/catalog/scope digest 和 required content。
2. fresh-install 到新隔离目录；所有产品命令必须解析到安装入口，不从 source checkout、旧 bundle 或宿主私有缓存运行。
3. 在全新 release root 为八个适应症分别运行 A/B/C，生成 24 个新 run/job/session/project/artifact/verdict；旧 ID、旧 receipt、旧截图、旧摘要和旧 evidence 明确拒绝。
4. 每个门户执行宇宙/来源/GateSpec/科学 QC、页面 responsibility、图表—表格同集、页底外部来源区、证据下钻、搜索、筛选、URL、键盘、控制台和链接检查；所有物理页面在 Chromium/WebKit 覆盖桌面、平板、手机、窄屏（至少 1440×900、1024×1366、390×844、320×568），检查中文可读性、遮挡、溢出和空图。
5. 三宿主各自 fresh-install 并从同一个最终 bundle 触发“竞品调研”，收集真实入口和失败关闭回执；不得在同一进程伪造三个宿主。
6. 由当次 A/B/C HTML artifact manifests 实际计算 `formats=1`；如果出现 PDF/PPT、CSV/XLSX、雷达、成熟度或监测 artifact，当前 v1 closure 失败。

**阶段门**：24 个门户和三宿主回执全闭合、旧证据拒绝、`formats=1` 实算且 Codex 接受后才能进入 D。

### 10.6D Recovery、独立验收与 freeze

**步骤**：

1. 构建 recovery package；只包含当前 RC、批准迁移资料、清单、当次验收记录和恢复所需输入，不包含可运行旧流水线、凭据、缓存或绝对路径。
2. 在一次性隔离根执行 fresh-install → restore project → 用户触发后自动 refresh/diff → representative HTML rebuild；回执绑定 recovery digest、演练结果和 RC identity。
3. 生成 owner-stage receipts；pre-RC host receipt 与 final `release-case-receipt` 的绑定必须可追溯；只有 `legacy-absence` 保持 `pending_future=1`。
4. 科学、视觉、包和恢复由生产者之外的验证者分别 PASS/VETO；验证者不得静默改产物。Codex 重开实际 HTML 页面和证据后作最终接受。
5. 记录 P0/P1=0；每个 P2 已修复或有证据的明确 non-impact disposition；任何 pending/rejected 仍阻止冻结。
6. 写 final report/freeze record；source tree 在 commit 后不回写运行回执。

**阶段门**：只有 24 门户、三宿主、恢复演练、owner-stage closure、独立 verdict 和实际 HTML 证据全部通过，才允许输出 `RC_FROZEN`。Task 10.6 不关闭或验收旧根 absence。

## 关键绑定

每份最终证据绑定：RC commit、`bundle_sha256`、package manifest digest、catalog digest、release-scope digest、case digest、project/run/job/session、input/artifact/verdict digest、科学复核 request/receipt/issuance record、门户字节、来源/事实/声明快照和时区时间。恢复回执还绑定 recovery package digest、隔离根身份和实际演练结果。

`coverage_set` 逐项列出页面责任、产品、试验、声明、图、表和证据引用；v1 只有一条 HTML `coverage_projection`，与 coverage_set 的差异必须为零。报告页面不得泄露 internal locator。

## Q1–Q6 已裁决合同

| 问题 | Task 10.6 固定处置 |
|---|---|
| Q1 RC identity | `sha256(canonical_json({schema_version, source_commit, bundle_sha256, package_manifest_sha256, catalog_sha256, release_scope}))`。 |
| Q2 receipt 层级 | pre-RC host receipt 与 final owner-stage release receipt 双层保留，freeze record 显式绑定。 |
| Q3 future owner | 仅 `legacy-absence` 为 `pending_future=1`；本任务不触碰真实旧根。 |
| Q4 治理工具 | cutover/legacy 工具是 governance sidecar，不进 runtime bundle；摘要进 RC record。 |
| Q5 运行入口 | 产品从安装 bundle；治理 verifier 从 clean RC worktree；receipt 绑定同一 RC。 |
| Q6 formats | 从当次 A/B/C HTML artifact manifests 实际计算，v1 必须为 1。 |
## 失败与恢复

- 每阶段先写不可变 checkpoint；失败保留源、摘要、日志、部分回执和下一安全动作。
- 只重排失败节点及其下游；已锁定事实、已接受门户和其他格式不因局部失败而被静默重写。
- 不用 `git reset --hard`、`git checkout --`、`git clean` 或覆盖用户改动取得 clean。
- 不用总完成率掩盖关键字段；路由技术失败、访问阻断、未公开、未报告和明确零保持不同状态。
- manual gate 一次用户响应后不在同一快照追问；官方证据不足则阻断/证据不足页面，不生成草稿或空门户。
- 发现 P0/P1、旧 receipt、非最终入口、scope 漂移、非法分组、视觉否决或恢复失败时不输出 freeze；进入新候选或修复 checkpoint。

## 最终信号

```text
RC_FROZEN reports=3 formats=1 hosts=3 recovery=passed pending_future=1
```

发布状态只允许 `DEVELOPMENT_CANDIDATE → RC_FROZEN → RELEASED`。`reports=3` 表示 A/B/C 报告族；24 个门户由 full-matrix closure 单独证明。信号不是脚本退出码别名，必须由实际 artifacts、receipts、verdicts 和 Codex acceptance 支撑；本任务不得宣称 `legacy_absent=passed`。
