# Task 10.6 PRD：首版 HTML-only RC、全矩阵与恢复演练

## 规范依据

- Canonical 设计：`docs/specs/competitive-intelligence-workflow-design-v1.3.md`
- Canonical 路线图：`plans/competitive-intelligence-workflow-roadmap-v1.3.md`
- Canonical 执行计划：`plans/codex_execution_ci-rebaseline-rebuild-v3.md`
- 处置评审：`reviews/zcode_disposition_ci-rebaseline-rebuild_20260904.md`
- 历史约束：Task 10.5 已封存检查点和 pause handoff 保持原样，仅作暂停现场与来源证据；handoff 中的 `formats=4` 等旧合同不再生效。v1.2 仅按 canonical v1.3 附录 C 明确纳入的条款继续生效。

本任务仍是 Task 10.6 only。本文同步首版发布范围和最终 RC 合同，不表示任何阶段已经完成或接受。

## 目标

把此前的 pre-RC 与 rehearsal 转化为唯一、可复现、可恢复、可追溯的首版 HTML-only release candidate。最终结论必须来自 clean source commit 构建的 HTML-only bundle、该 bundle 的 fresh install、全新 release root、全新 run/job/session/receipt、24 个真实来源门户、三宿主回执、真实恢复演练和独立验收；不能继承 Task 10.2/10.3 或其他旧摘要、旧 artifact、旧 receipt、旧 verdict 或旧完成状态。

公开产品入口是安装 bundle 中的一个 Skill，支持一句话“竞品调研”自主研究和可选 typed `research-package`。内部研究、裁决、分析、渲染与复核 Skills 具有类型化合同且可独立测试，但不要求用户理解或手工编排。宿主 Agent 把自主研究结果编成严格 package，确定性引擎只从 package、已接受事实和锁定快照继续。A/B/C 是三个独立的高密度多页面 HTML 门户，不是一个 combined portal。

用户未指定报告类型时，入口用宿主原生 Ask 解释并选择 A/B/C；历史截止日可选。每个新项目只询问一次是否具备 Yaozh 访问条件，无账号时跳过、会话失效时提示用户自行登录。必需 publication 补件在指定目录核验后原地规范重命名，操作前记录原名、SHA-256、DOI/登记号和新名，执行冲突检测且不修改文件字节。

## 首版范围

首版 artifact closure 只接受站点式 HTML：

- 八个适应症分别运行 A、B、C，共 24 个独立门户：特应性皮炎、重度哮喘、类风湿关节炎、溃疡性结肠炎、CRSwNP、结节性痒疹、IgA 肾病、PNH；
- 每个结构化数据集有适当图形和同一事实集的完整折叠表；每页一个聚合外部来源区；可见表格不含内部文件 locator；
- Yaozh 是可选浏览器会话辅助商业来源，不能作为唯一权威；凭据、Cookie、令牌和授权头不进入任何 artifact；
- 登记关联的主要结果、延长期主要结果、关键安全性或长期暴露发表物必须检查；综述、普通 ad hoc 和无关探索性分析默认排除，阻断边缘由版本化规则、模型判断和 clean-context 独立复核共同裁决。必需论文不可访问时只建立一个 Markdown manual-supply gate。用户一次响应后同一快照不得再次追问；
- 首份报告必须完成全球/中国必查来源以及别名、靶点、企业和试验反向扩展的竞品宇宙闭包，再由独立干净上下文复核；不能用固定数量、Top-N 或明星产品替代闭包；
- 关键缺失或异常零值必须有两条不同替代恢复检索和 clean-context 独立最终复审；缺独立审查能力时预检失败；
- 可选字段缺失可省略或简述；核心问题仍可回答时带明确限制交付；核心问题不可回答时只交付简洁的用户可见证据不足页，完整 blocker audit 留在内部，不渲染空坐标轴、固定零值墙或大量空模块；
- B 的近时间窗（例如 48 周/50 周）只有临床构念、定义、方向、单位、估计目标、分母、分析集和分析形式兼容时共框并标注差异；不兼容即拆分；
- B 气泡图只采用三组版本化临床预设：疗效信号×总体安全性（大小为治疗组样本量或暴露量）、疗效信号×严重风险（大小为有效分析集规模）、获益持续性×停药风险（大小为长期暴露量）。常规输出只做事实汇总和中性差异，不默认给出竞品排名、综合分数或研发建议；
- 应用自有类型化控制图是唯一编排合同；LangGraph 不作为基础依赖、科学真源、三宿主一致性或离线恢复前提；
- v1 不生成 PDF、HTML-PPT、可编辑 PPTX、CSV/XLSX、雷达图或证据成熟度视图，不建设 scheduled monitoring、后台轮询或无人触发刷新；用户手动触发后，来源复核、差异识别、快照和 HTML 重建自动完成。历史非 HTML 代码/schema 可保留，但不进 v1 bundle、默认 preflight、artifact closure 或验收集合。

## 必须交付

1. clean source commit/tag 与 source/version/dependency/contract/migration 摘要；dirty tree、source mismatch 和 required-content 缺失必须失败关闭。
2. 由该 commit 构建并逐文件核验的 HTML-only `.tar.zst`、bundle manifest 和 SHA-256。包必须包含当前 v1.3 设计合同、HTML 运行时、A/B/C typed Skills、schema、required catalog 和安装入口；cutover/legacy 工具是仓库治理 sidecar，摘要进入 RC 记录但不进入运行时 bundle。
3. 从最终安装入口完成的新鲜 A/B/C HTML 矩阵：8 个适应症 × 3 个报告 = 24 个门户；三宿主各自消费同一个最终 bundle。旧 run/job/session/artifact/verdict 和旧 bundle 必须拒绝。
4. 所有 24 个门户的来源/宇宙闭合、GateSpec、页面责任、图表—表格一致、页底来源区、证据下钻、筛选/网址状态，以及桌面/平板/手机/窄屏四类视口的真实 Chromium/WebKit 视觉和科学 QC 证据。
5. 只包含本 RC、批准迁移资料、清单和本次验收记录的 recovery package；不得包含可运行旧流水线、凭据、缓存或绝对路径。
6. 一次性隔离根中的 fresh install → 恢复项目 → 继续手动刷新 → 代表性 HTML 重建演练，以及严格 `recovery-package-v1` 回执。
7. owner-stage `case-receipts/<case_id>.json`、pre-RC host receipt 与 final owner-stage receipt 的显式绑定、最终科学/视觉/包/恢复独立 verdict、pre-cutover verdict 和最终验收报告。

## 关键身份和 receipt 分层

固定 RC 身份为：

`release_candidate_sha256 = sha256(canonical_json({schema_version, source_commit, bundle_sha256, package_manifest_sha256, catalog_sha256, release_scope}))`

Git commit 即使是 SHA-1，也不能直接填作 SHA-256。保留两层 receipt：

- catalog/运行阶段的 pre-RC `host-receipt`；
- acceptance root 的 final owner-stage `release-case-receipt`。

freeze record 必须显式绑定两层 receipt、RC identity、bundle/package/catalog/scope digest、case digest 和当次运行身份；不得为了减少路径而静默改写历史 catalog 指针。

## 验收信号

仅当所有门均通过时允许输出：

```text
RC_FROZEN reports=3 formats=1 hosts=3 recovery=passed pending_future=1
```

- `reports=3` 表示 A/B/C 三类报告族；24 个门户由 full-matrix closure 单独证明；
- `formats=1` 必须由当次 A/B/C HTML artifact manifests 实际计算，不能硬编码；
- `pending_future=1` 只能表示唯一的 `legacy-absence` future owner，Task 10.6 不执行旧根 absence 检查；
- 发布状态只保留 `DEVELOPMENT_CANDIDATE → RC_FROZEN → RELEASED`；Task 10.6 不得宣称 `legacy_absent=passed`；
- P0/P1 必须为零；P2 必须已修复或有证据的明确 non-impact disposition；
- 任一 pending/rejected、旧 digest、非最终安装入口、dirty build、手动资料门未处置、宇宙/关键缺失未双重穷尽、科学/视觉/包/恢复否决都必须阻止冻结。

## 绝对边界

- 不读取、不 inventory、不 validate、不 apply、不 chmod、不删除、不 absence-check 真实旧根、旧全局 Skill 或归档副本；
- 不覆盖既有 pre-RC/R13 证据；最终 release root 使用全新版本目录和全新 IDs；
- 不把测试替身、源码 checkout、旧 bundle 或 pre-RC receipt解释为真实宿主/最终发布通过；
- 不在源闭合和确定性回归前创建 RC commit；不因“需要 clean tree”而丢弃或重置用户改动；
- 不把 PDF/PPT、CSV/XLSX、雷达图、证据成熟度视图或定时监测偷偷加入 v1；
- commit/tag 是本地冻结动作；发布、真实迁移、旧根切换和删除不在本任务授权内；
- 不输出 `RC_FROZEN`，直到 10.6C/D 全部门实际通过且 Codex 明确接受。
