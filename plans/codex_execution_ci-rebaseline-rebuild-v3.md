# Codex Execution Plan: ci-rebaseline-rebuild v3

- **状态**：canonical / rebaseline-approved
- **日期**：2026-09-04
- **目标**：在不触碰真实旧根、不丢弃用户改动、不继承旧证据的前提下，把竞品调研多 Skill 工作流重建为“一句话自主研究 + 可选 typed research-package + 确定性引擎 + A/B/C 独立 HTML 门户 + 三宿主安装”的首版产品，并完成 8 个适应症 × A/B/C = 24 个门户的真实来源验收和 Task 10.6 RC 冻结。
- **设计规范**：`docs/specs/competitive-intelligence-workflow-design-v1.3.md`
- **路线图**：`plans/competitive-intelligence-workflow-roadmap-v1.3.md`
- **输入证据**：ZCode 审计/路线/计划及 Task 10.6 handoff；输入文件保持原样，不作为规范。

本计划取代 ZCode `zcode_execution_plan_v2_20260902.md` 对未完成工作的执行安排。v1.2 只作为历史来源；其兼容条款仅按 canonical v1.3 附录 C 的明确纳入执行，不得凭“v1.3 未提及”恢复旧产品面。已完成的 Phase 0–10 历史 checkpoint 不被重写；每个新阶段必须用当次文件、命令、浏览器、数据库或恢复锚点证明，不得使用“代码存在”“局部测试通过”“旧 receipt”代替验收。

---

## 0. 总体合同

### 0.1 首版 release scope

首版只交付站点式 HTML：A、B、C 各一套独立多页面门户。PDF、HTML-PPT、可编辑 PPTX 的历史代码/schema 可保留，但不进首版安装 bundle、默认能力预检、artifact closure、full-matrix 产物或验收集合。首版也不实现 CSV/XLSX 导出、雷达图、证据成熟度视图、定时监测、后台轮询或无人触发刷新；用户手动触发后，来源复核、差异识别、快照和 HTML 重建自动完成。

`formats` 不得硬编码，必须由当次 artifact manifests 计算，首版必须得到 `formats=1`。全部结构化数据先图后完整折叠表；表格与图使用同一事实集；每页一个聚合外部来源区；用户可见表格不含内部文件路径或 locator。

### 0.2 入口和研究合同

公开入口 Skill 使用中文触发词“竞品调研”，接受一句话最小输入（适应症 + 可选报告类型），并可选接受 typed `research-package`。报告类型未指定时，使用宿主原生 Ask 以带解释的 A/B/C 选择项提问；历史截止日可选，每个新项目只询问一次是否具备 Yaozh 访问条件。没有 package 时，宿主 Agent 自主执行来源研究、适用性判断、下载和初筛，再编成同一 package；用户不负责写内部 schema。确定性引擎只接受严格校验的 package，不以模型记忆、聊天、旧报告、截图或任意互联网搜索补科学事实。

Yaozh（`vip.yaozh.com`）是可选浏览器会话辅助商业来源，不能单独支撑核心结论；入口最多询问一次用户是否具备访问条件，无账号时跳过、会话失效时提示用户自行登录。凭据、Cookie、令牌和授权头不得进入 package、日志、回执、快照、bundle 或截图。

### 0.3 证据与恢复合同

竞品宇宙在门槛计算前关闭，并由独立节点复核。关键缺失或异常零值必须做两条不同替代恢复检索和 clean-context 最终复审；缺少独立审查能力即预检失败。登记关联主要、扩展/补充、关键长期/安全发表物必须检查。必需论文不可访问时建立一个 Markdown manual-supply gate；用户一次响应后同一快照不得再次追问，官方证据足够则带限制继续，否则输出证据不足审计包/页面。

B 的模型辅助整体临床构念分组必须受确定性守卫：48 与 50 周等近窗口只有定义、方向、单位、估计目标、分母、分析集和分析形式兼容时共框并标注差异；不兼容即拆分。A/B/C 门槛中的 `reported_zero`、未报告、未公开、访问阻断、技术不可用、冲突和 route failure 分开建模。

### 0.4 禁止和边界

不做 Top-N、任意评分/排名、跨试验池化或 Bucher/Meta/NMA/MAIC/STC。LangGraph 不是基础依赖；任何可选图运行适配器都不得持有科学真源或成为离线恢复前提。暗色主题未纳入 v1，但不是科学性永久禁项。当前 R0–R6 以及 Task 10.6 不读取、inventory、chmod、修改、删除或 absence-check 真实旧根。没有明确授权，不写外部发布位置，不创建 RC，不处理真实凭据。

---

## 1. 全局质量和身份纪律

### 1.1 唯一质量门

实现统一 gate（脚本或等价命令），范围必须明确记录：

```bash
uv run ruff check src tools tests \
  && uv run mypy --strict src/ci_workflow \
  && uv run pytest tests/unit tests/contract -q \
  && uv run python tools/check_no_legacy_refs.py
```

命令范围不可缩小后宣称“质量门通过”。测试可在开发期间按最小 focused 集合运行，但阶段接受必须附完整 gate 输出或 digest，以及未运行项。不得使用 `# type: ignore` 盖住错误；确需使用时逐条记录原因和数量。

### 1.2 release identity

所有最终证据绑定 `schema_version`、`source_commit`、`bundle_sha256`、`package_manifest_sha256`、`catalog_sha256`、`release_scope`、case digest、project/run/job/session、input/artifact/verdict digest 和时区时间。

固定 RC identity：

```text
release_candidate_sha256 = sha256(
  canonical_json({
    schema_version,
    source_commit,
    bundle_sha256,
    package_manifest_sha256,
    catalog_sha256,
    release_scope
  })
)
```

Git commit 即使是 SHA-1 也不得填作 SHA-256。pre-RC `host-receipt` 与 acceptance root 的 final owner-stage `release-case-receipt` 保持双层；freeze record 显式绑定二者。

### 1.3 bundle/source 边界

产品运行必须来自安装 bundle；治理 verifier 可来自 clean RC worktree，但回执必须绑定同一 RC identity。cutover/legacy 工具是治理 sidecar，摘要进入 RC governance record，不进入运行时 bundle。bundle 不含凭据、日志、缓存、旧可运行流水线、未批准归档、绝对路径或未来格式运行时。

---

## 2. R0：provenance recovery 和工程基线

### R0.1 dirty-tree inventory

**目标**：解释当前树，不进行 destructive cleanup。

**步骤**：

1. 固定当前 HEAD、状态、路径类型、历史 checkpoint 和用户变更映射；保存不可变 inventory/digest。
2. 按来源区分长期项目修改、前序任务、运行产物、worker 修改和用户修改；不能把总 dirty count 归因给单一任务。
3. 建立全量可恢复快照和候选来源边界；R2–R4 完成前不得把候选清单称为最终 release source set。
4. 任何路径摘要、来源、许可或迁移理由无法解释时停止并建立 blocker。

**验收**：inventory、逐文件哈希、外置只读恢复快照、候选来源边界、用户改动保留证据、未解释项为零或有明确 blocker；不创建 RC commit。

### R0.2 quality gate

**目标**：封堵局部绿灯 false-green。

**步骤**：

1. 让唯一 gate 在当前 RED 树可执行并正确非零返回；保留原始输出。
2. 修复全仓 ruff/mypy strict/contract/unit 门禁错误，优先最小行为保持修复。
3. 所有 worker metrics 填写声明的检查范围、命令、输出摘要和未运行项。

**验收**：全量 gate 通过；任何仍未运行的浏览器/科学/恢复层不被写成已通过。

### R0.3 provenance/dirty fail-closed

**目标**：构建、验证、fresh-install 和 receipt 具有可核验源身份。

**步骤**：

1. bundle manifest 保存 source commit、package/catalog/scope 摘要和 required content。
2. dirty tree、source mismatch、unknown field、missing required content 在输出/发布前失败关闭。
3. fresh-install 测试只写隔离临时目录；旧 run/job/artifact/verdict 不得进入新 evidence closure。
4. recovery package schema/receipt 校验 identity、摘要、路径边界和演练结果。

**验收**：正向和负向测试覆盖 source/manifest/dirty/required-content/unknown-field；不得以 worker 自报代替当前字节审计。

### R0.4 里程碑磁盘卫生

**目标**：控制长周期执行的磁盘增长，同时不破坏证据链和恢复能力。

**步骤**：

1. 每个里程碑 checkpoint 前后盘点本轮新增空间，区分可再生缓存/临时件/失败测试副本、原始科学证据、规范回执和不可变快照。
2. 仅删除由本轮生成、目标精确、已不再被测试或恢复引用的可再生内容；先记录目标、字节数和留存替代物，不使用 broad glob 或仓库级 clean。
3. 原始科学证据、未验收门户、规范文档、checkpoint、manifest、receipt 和最近一个可恢复快照默认保留；大体积历史证据转入外置内容寻址存储后，仓库只保留摘要指针。
4. 当前旧工程在用户未来再次明确批准前继续零接触，不纳入空间盘点或清理。

**验收**：checkpoint 记录 retained/removed targets、释放字节和恢复依据；无法证明可再生或无引用的内容不删除。

---

## 3. R1：canonical contracts（本执行包交付）

### R1.1 设计、路线和执行计划

**产物**：

- `docs/specs/competitive-intelligence-workflow-design-v1.3.md`；
- `plans/competitive-intelligence-workflow-roadmap-v1.3.md`；
- `plans/codex_execution_ci-rebaseline-rebuild-v3.md`。

**必须明确**：权威顺序；一句话自主研究 + 可选 package；HTML-only、`formats=1`；三独立门户/24 门户矩阵；Yaozh optional；论文/manual gate；宇宙 closure/两条恢复/clean-context review；B 48/50 语义分组；手动刷新；v1 非目标；旧根边界。

### R1.2 ZCode disposition 和 Task 10.6 同步

**产物**：一份 ZCode disposition review；Task 10.6 `prd.md`、`design.md`、`implement.md` 更新为 canonical v1.3。

**Q1–Q6 固定合同**：

| 问题 | 处置 |
|---|---|
| Q1 RC identity | 复合 canonical JSON SHA-256，绑定 source/package/catalog/scope。 |
| Q2 receipt | pre-RC host receipt 与 final owner-stage release receipt 双层保留，freeze record 显式绑定。 |
| Q3 future owner | 仅 `legacy-absence` 保持 `pending_future=1`；Task 10.6 不触碰旧根。 |
| Q4 cutover 工具 | governance sidecar，不进 runtime bundle；摘要进 RC record。 |
| Q5 入口 | 产品从安装 bundle，治理 verifier 从 clean RC worktree；绑定同一 RC。 |
| Q6 formats | 当次 artifact manifests 实算，v1 只能为 1。 |

**验收**：四组文档中的 scope、signals、边界、Q1–Q6 和阶段门一致；不将任何 checklist 勾选当作主 Agent acceptance。

---

## 4. R2：typed multi-Skill、来源和门槛

### R2.1 公共入口和宿主研究

实现公开入口 frontmatter/安装包触发词“竞品调研”、一句话最小输入、可选 package 和非技术中文阻断指引。自主研究结果必须进入 package；package 是确定性引擎唯一科学入口。入口不要求用户配置竞品列表、来源或研究方案。

**验收**：入口触发、最小输入、可选 package、无内部术语文案、失败指引和三宿主一致性测试。

**2026-09-05 实施状态**：项目运行首次进入研究等待态时会生成类型化自主研究
任务，包含全球/中国基线、四类反向扩展、报告专属路线、完成条件和可选 Yaozh
Ask 合同。新增 `research submit` 以严格 v1.3 审计信封绑定 A/B/C 专属载荷
字节；产品 CLI 只接受提交 manifest，松散输入失败关闭。自然语言理解和原生 Ask
继续由公开 Skill/宿主持有，不重复建设自然语言 CLI。单报告与多报告产品链均已
通过集成和隔离 bundle 验证；多报告在同一项目运行中保持 A/B/C 独立门户，并以
节点键和输入摘要共同约束复用。项目级 Yaozh 初始回答已持久化且同值幂等、改答或
篡改失败关闭。三态回答已接入类型化来源计划和能力预检：仅 `available` 增加
`required=false` 的药智已登录浏览器辅助路线，`unavailable/skipped` 明确为非阻断
`not_applicable`；运行期登录失效由绑定项目回答摘要、且不进入核心依赖的类型化
路线访问回执提示用户自行登录。
药智在来源政策 1.1 中无任何 `direct` 权限，临床结果仅为 `lead_only`。真实药智
浏览器适配器、登录态探测和三宿主入口实测仍待完成。

核心能力矩阵已从说明性节点升级为产品执行门。首次运行和 `--resume` 都重新执行
真实探测并清空同一运行时探针的上一轮缓存，结果经唯一应用层边界原子写入
`capabilities/preflight.json`；读取缺失回执无创建目录副作用，软链接和非普通目标
失败关闭。研究必需能力缺失在来源研究前返回独立 `capability_blocked`/退出码 5；
仅 HTML 浏览器验收能力缺失时允许研究完成但禁止 format；药智登录缺失保持非阻断。
CLI、fixture 和运行服务均通过显式探针合同测试，生产默认仍使用实机探针。

A/B/C 渲染已改为未发布 staging 事务：只有站点原子换名并写入
`html.manifest.json` 后才形成提交点。无绑定中断残留可按当前报告版本精确恢复；
已有产物清单、覆盖投影、artifact store、当前运行清单或科学复核状态绑定时严格
拒绝覆盖。原始站点渲染函数不是产品发布入口。

### R2.2 本体和宇宙 closure

实现创新药/组合组件/方案 eligibility、研究角色与 publication role 分离、全量分层竞品集合。全球/中国必查来源和别名、靶点、企业、试验反向扩展分别记录查询、发现集合与闭合回执；候选范围锁定并由 clean-context 独立复查后才求值。关键异常缺失/零值执行两条不同替代恢复和 clean-context 独立复查。

**验收**：空宇宙、拥挤适应症初搜少量、区域路线缺失、别名/靶点/企业/试验反向扩展漏跑、边界本体、传统背景治疗、特殊早期试验、默认排除、重复策略去重和 closure 缺独立 reviewer 的负向测试。

**2026-09-05 实施状态**：R2.2 合同与产品运行门已闭合。`ResearchPackage` 现以
类型化 expansion receipt 取代任意字符串证明，逐项绑定四类扩展、路线/尝试、输入
与发现实体、来源、查询摘要、结果类别和诊断；候选实体绑定纳排处置与版本化本体
规则。最后连续两轮零新增才可收敛，技术失败不得冒充无发现。独立闭包复核绑定不同
producer/reviewer 身份和上下文及 `reviewed_universe_sha256`；项目、截止日、来源
政策、实体或尝试字节漂移均失败关闭。产品运行以审计包摘要形成 A/B/C 共用的唯一
项目级 universe identity，同一运行只完成一次 universe 节点。历史重复闭包模型已
从产品能力模块移除，未建设第二状态库。

### R2.3 source policy and manual gate

实现 registry-linked primary、extension、关键长期/安全发表物检查和按声明域来源角色；以规则 + 模型 + 独立复核区分必需 publication 与默认排除的综述、普通 ad hoc、无关探索性分析。Yaozh 只作 optional browser-assisted 商业来源。实现单一 Markdown manual-supply gate、用户一次响应、不重复追问、内容识别、摘要/标识匹配，以及用户投递目录中的原地规范重命名；重命名前保存原名、SHA-256、DOI/登记号和新名映射，执行碰撞保护且不复制、不移动、不修改文件字节。

**验收**：来源回执分类；凭据扫描；必需论文可访问/不可访问分支；官方证据足够时带限制继续，官方证据不足时 evidence-insufficiency page/blocker；错误不能改写成“无证据”。

**2026-09-05 实施状态**：Publication/manual-supply 产品门已完成。`ResearchSource`
按来源类型约束论文分类；正式 publication 裁决、跨路线家族获取尝试、逐纳入试验
检索回执、独立复核、单快照单次用户门、错文件恢复、扫描 PDF 的 OCR 交接、严格
replacement/resubmit，以及不可得后的带限制继续或 `evidence_blocked` 均已接入产品
运行并通过执行/会商/测试门。Yaozh 真实浏览器适配器与会话探测仍未完成，继续作为
来源适配切片验收，不得因 R2.3 Publication/manual gate 完成而推定完成。

### R2.4 GateSpec and blockers

实现逐对象逐字段 GateSpec、适用性、成熟度、缺失/零/冲突状态、路由/信息增益闭合、独立科学 QC 和 no-draft。核心问题可回答时带限制交付；核心问题不可回答时内部输出审计包、对用户只显示简洁证据不足页。可选空模块省略或一句话说明，不生成空报告、空坐标轴、固定零值墙、草稿或占位门户。

**验收**：正/负门槛、冲突、访问阻断、parser failure、技术恢复、历史快照和 blocker audit 断言。

**2026-09-05 续接状态**：已用既有双重穷尽与唯一 blocker 发布合同接通
B/C `recovery_required → evidence_blocked`，并完成 A/B/C 两阶段科学复核迁移：
首次渲染固定为 `rendered_unreviewed`；仅实际 `scientific-review-v1` 回执、
同源 issuance record、形式化 verdict 工件字节、权威持久化谱系、独立
producer/reviewer 身份、review request、门户字节绑定和不可变候选摘要全部
闭合且结论在晋级时仍有效后，才允许单向晋级
`scientifically_reviewed_rendered_candidate`，且晋级复用原 HTML 字节。
等待回执与晋级后允许任意次受控 resume；真实来源验收按复用来源图闭合，
不再假设只有两个 run。安装包已纳入签发入口和科学复核 Python 导入闭包，
保留格式门只表述为 2 文件/20 断言的 bounded compatibility smoke，不冒充
18 文件全轨或 v1 产品验收。
旧 preview fixture 已改为按实际数据自锁快照并保持 preview-only；HTML-only
活跃门与保留的非 HTML 基础回归已显式分层，未通过缩小检查范围隐藏债务。
B/C 双重穷尽路径现先形成规范 `report_evidence` 终态，再原子发布 blocker；终态
manifest 可按报告专属 research-package 内容摘要校验并重复 resume。来源等级不足
但已有数值时，阻断页保留双重穷尽的合法缺口状态，不把 `reported_value` 误写为
缺口枚举。
R2.4 仍保持未完成：逐对象 GateSpec、完整 blocker audit、三宿主真实签发
及 Yaozh 真实浏览器来源适配尚需按各自验收关闭；R2.2 与 R2.3 已有独立完成
checkpoint，不再重复建设。Task 10.2 的三个外部 A/B/C 正向
验收项目因旧 `package_digest` 被当前门正确拒绝，留待 R5 用当前候选重新生成。
证据见 `.trellis/tasks/09-02-phase-10-task-106-rc-freeze/checkpoint_20260905_r2_review_runtime_fixture_rebaseline.md`
及本阶段执行/会商归档。

**2026-09-06 R2.4 更新**：逐对象/逐适用单元 GateSpec、失败码与恢复路线、候选宇宙
不可删减、来源/成熟度/缺失/零值/不适用/冲突边界、两轮真实恢复与类型化信息增益、
独立遗漏复核、三类专用 blocker、原子幂等恢复及 no-draft 产品链已经闭合。最终产品链
`579 passed`，全仓开发门和 328 文件 HTML-only 实包校验通过；两轮独立会商未发现新增
P0/P1。R2.4 仍只因来源新鲜度模型、默认窗口和历史截止日语义需要用户通过原生 Ask
裁决而保持开放。三宿主真实签发与 Yaozh 浏览器适配分别属于后续宿主/来源切片，不再
混入 R2.4 完成定义。

---

## 5. R3：A/B/C 数据投影

### R3.1 A landscape console

交付完整创新药宇宙、产品档案、开发组合、监管/企业/交易/专利/历史边缘观察和结果披露状态；`result_bearing` 最低疗效/安全证据不足则恢复/阻断，不删产品。主要图形覆盖管线全景、靶点—产品关系、阶段矩阵、地域状态时间线、疗效比较、安全热图和多维气泡图；不按明星产品或排名截断。每个结构化数据集适当图 + 完整折叠表。

### R3.2 B evidence comparison room

交付疗效、纵向、安全、基线/人群、试验完成/处置、试验暴露、亚组、矩阵和档案页面。基线按可比较组门槛；完成情况字段强制建模但非阻断。语义分组由模型辅助整体临床构念候选 + 确定性冲突守卫；48/50 周近窗口按兼容合同共框且标注，不兼容拆分；不池化、不默认排名或自动研发建议。气泡图采用三组版本化临床预设：疗效×总体安全性（大小为治疗组样本量/暴露量）、疗效×严重风险（大小为有效分析集规模）、持续性×停药风险（大小为长期暴露量）；只有完整临床语义可比时同图。安全热图保留色值语义、数值和缺失状态；不增加雷达/成熟度视图。

### R3.3 C design atlas

交付登记优先设计事实、完整公开入排、干预/对照、剂量/疗程/随访/终点/样本量/操作特征、逐试验下钻和设计模式/差异/权衡/多路径。主要图形覆盖设计模式地图、试验时间轴、终点—时间窗矩阵、入排主题分布、组别结构和方案差异；只输入适应症时总结有证据的多条候选路径或明确拒绝唯一建议。

### R3.4 共用合同

保存原文与规范化值、统计形式、单位、方向、分析人群、分母、时间窗、来源定位、差异标签、声明和快照身份。每页一个外部来源区，表格无内部 locator。图、表、抽屉和网址状态使用同一 filtered row set。

**验收**：schema/data-contract tests；GateSpec coverage；A/B/C 页面责任 coverage_set；B 兼容/拆分和无池化测试；C 多路径测试；没有一份报告依赖另一份页面才能打开。

---

## 6. R4：站点式 HTML 产品

### R4.1 三门户信息架构

A、B、C 各自至少两个互通物理页面，分别使用 landscape console、evidence comparison room、design atlas 信息架构，不合并为超级门户，不用单页长文档或首页摘要替代完整页面责任。

### R4.2 交互和渲染

实现全局搜索、跨页下钻、分层筛选、URL 状态、键盘证据下钻、焦点返回、reduced-motion、图先表后、默认收起且原位展开的完整表格、每页底部聚合外部来源区、清晰类型化空状态和离线 file:// 运行。默认首屏不显示工程阶段、Gate、提示词、覆盖率诊断或内部字段。正式 Logo 本地嵌入；无远程字体/图片/脚本和运行时 JSON fetch。

### R4.3 HTML-only 排除

不添加 CSV/XLSX 导出、雷达图、证据成熟度矩阵、PDF/PPT 运行时或定时监测。无可绘制数据时不生成空坐标轴；可选模块不足时省略或一句话说明，核心不足时进入证据不足页。表格必须完整可查看；未来导出或可视化能力需新版本合同，不得在 v1 catalog 隐式保留验收要求。

### R4.4 真实视觉和科学验收

对 A/B/C 所有物理页面在 Chromium/WebKit 覆盖桌面、平板、手机和窄屏四类真实视口（至少 1440×900、1024×1366、390×844、320×568），检查长表、折叠表、筛选、证据下钻、空状态、控制台、链接、中文可读性、遮挡、溢出、无障碍和源码/数据一致性。视觉/科学验证者只能 PASS/VETO，不能静默改产物；Codex 做最终接受。

**验收**：每门户真实截图/浏览器日志、coverage projection 与 coverage_set 差异为零、独立 scientific/visual verdict；`file://` 和静态服务器均可运行。

---

## 7. R5：安装包、刷新和恢复

### R5.1 HTML-only bundle

从 clean source set 生成一个 HTML-only 通用核心 bundle 和 Codex/Hermes/OMP 轻量适配层；安装后只暴露一个用户入口，内部 Skills 独立可测试。manifest 列出 schema、设计合同、HTML 运行时、A/B/C Skills、scope、source/package/catalog/RC 摘要和 required content。不得把 governance sidecar、旧流水线、凭据、缓存、原始运行证据、未来格式运行时或其运行依赖打包。

### R5.2 三宿主

Codex/Hermes/OMP 各自 fresh-install，按同一关键词触发入口，以同一最小输入执行；宿主适配器不改变来源、门槛、状态、快照或验收语义。产品命令来自安装 bundle；治理 verifier 从 clean RC worktree 运行并绑定 RC。

### R5.3 手动刷新和历史

用户手动触发刷新后，系统从最新接受快照、回执和缺口账本自动重新核验，生成 immutable snapshot、latest pointer 和 added/changed/withdrawn diff，只重算受影响页面。不得建设 scheduled monitoring、后台无人轮询或自动发布未经接受的报告。

### R5.4 recovery-package-v1

恢复包只含当前 RC、批准迁移资料、清单、验收记录和恢复所需输入；一次性隔离根执行 fresh-install → restore project → continue manual refresh → rebuild representative HTML。回执绑定 recovery digest、演练结果、RC/bundle/package/catalog/scope identity。

**验收**：bundle/fresh-install、三宿主入口、手动刷新 diff、恢复 schema/receipt、隔离重放、无旧 receipt/旧 run、秘密/绝对路径/远程依赖扫描。

---

## 8. R6：真实矩阵、Task 10.6 和冻结

### R6.1 真实 A/B/C 矩阵

在全新 release root 对八个适应症分别运行 A、B、C，共 24 个独立 HTML 门户：特应性皮炎、重度哮喘、类风湿关节炎、溃疡性结肠炎、CRSwNP、结节性痒疹、IgA 肾病、PNH。每个项目使用新 run/job/session/artifact/verdict；旧 evidence、旧 receipt、旧摘要和旧截图必须被拒绝。

### R6.2 Task 10.6A

只在临时目录完成 bundle/fresh-install/recovery/receipt 负向测试和当前字节审计；不创建 RC commit，不访问旧根。只有 source/manifest/required-content/dirty/mismatch/unknown-field/recovery contracts 当前测试全绿，且主 Agent接受，才进入 B。

### R6.3 Task 10.6B

建立显式 release source set；完成 Phase 0–10 确定性回归、schema/package/legacy scanner 和全量 gate；在隔离 clean worktree 创建唯一 RC commit/tag。任何 source drift、未解释用户改动或测试范围缩小都停止。

### R6.4 Task 10.6C

从 RC commit 构建并验证最终 HTML-only bundle，fresh-install 后从安装入口执行 24 门户矩阵和三宿主回执。artifact manifests 实算 `formats=1`；不得生成或验收 PDF/PPT、导出、雷达、成熟度或 monitoring artifacts。

### R6.5 Task 10.6D

完成 recovery package 隔离演练、manual refresh、代表性 HTML 重建；生成 owner-stage receipts，执行科学、视觉、包、恢复独立验收和 Codex 实际门户检查。`legacy-absence` 仍是唯一 future owner，当前不读取或检查旧根。

### R6.6 冻结信号

仅当 24 门户、三宿主、恢复、全部适用门禁、P0/P1=0、P2 repair 或证据充分 non-impact disposition、最终安装入口和双层 receipt closure 全部通过，才允许：

```text
RC_FROZEN reports=3 formats=1 hosts=3 recovery=passed pending_future=1
```

发布状态只允许 `DEVELOPMENT_CANDIDATE → RC_FROZEN → RELEASED`。`reports=3` 表示 A/B/C 报告族，24 门户是 full-matrix 资产；`pending_future=1` 不是旧根验收通过，Task 10.6 不得宣称 `legacy_absent=passed`。

---

## 9. Worker/validator 责任和证据

| 角色 | 可执行 | 不可宣称 |
|---|---|---|
| 实现 worker | 授权文件中的代码、schema、测试和局部证据 | 最终科学/视觉/包/恢复接受、RC_FROZEN |
| execution/conference agent | 按合同运行测试、浏览器、恢复和会议，返回 PASS/VETO 证据 | 静默修产物、放宽门槛、代替 Codex 接受 |
| Codex | 集成、实际产物重开、最终接受、RC freeze | 在证据缺失时假设通过 |
| Task 10.6 | source closure、bundle/fresh install、24 门户、三宿主、恢复和 freeze contracts | 真实旧根 inventory/apply/delete/absence-check |

每份 worker report 必须记录：边界、读写文件、命令和精确范围、观察、证据路径、未运行项、失败/阻断和下一动作。报告是证据，不是授权。

关键负向矩阵必须包含：拥挤领域初搜只找到少数竞品；网络故障被误判为无数据；Yaozh 无账号/会话失效；必需论文不可下载且用户确认无法取得；48/50 周可近似分组而不同量表/方向/估计目标/分母/分析集不可误合并；无数据图不生成空坐标轴；publication 重名、错误文件、扫描 PDF 或登记号不一致；刷新后的新增/修订/撤回进入差异页；宿主无独立上下文能力时预检失败。

---

## 10. 阶段检查点、回滚和停止

每阶段先写不可变 checkpoint，后进入下阶段。失败时保留源码、摘要、日志、部分 receipt 和下一安全动作；不使用 `git reset --hard`、`git checkout --`、`git clean` 或覆盖用户文件获得假 clean。

每个 checkpoint 同步执行 R0.4 磁盘卫生：先审计本阶段新增内容，再精确清理已由摘要/哈希替代的可再生缓存和失败临时件。清理不能先于验收证据落盘，也不能删除当前或上一可恢复点、真实来源文件、未验收报告或仍被测试引用的 fixture。

以下任一情况禁止继续：

- gate 只跑了局部范围却被宣称全绿；
- source/bundle/package/catalog/case/receipt/RC identity 不一致；
- 旧 run/receipt/artifact/verdict 进入当前 closure；
- 宇宙、关键缺失、异常零值缺少独立 closure/两条替代恢复/clean-context review；
- manual gate 重复追问用户或把技术失败写成无证据；
- B 分组跨越不兼容定义/尺度/方向/估计目标/分母/分析集；
- A/B/C 页面缺表、缺来源区、泄露 locator、图表与表格不是同一事实集，或真实浏览器溢出；
- P0/P1 未清零，P2 无修复或 non-impact disposition；
- 任何步骤试图访问真实旧根或将 PDF/PPT/导出/雷达/成熟度/监测偷偷纳入 v1。

可恢复范围只包括当前失败节点及其下游；已锁定事实和通过产物不因另一路失败而回滚。格式、来源、schema、scope 或监测合同的恢复必须建立新版本，不回改已冻结 RC。

真实旧根退役不属于 Task 10.6：只有新系统至少完成三个覆盖 A/B/C 的真实项目，且用户触发刷新、历史差异、恢复、三宿主运行通过、严重缺陷清零并具备可验证回滚后，才可再次请求用户明确批准；批准前继续零接触，批准后才建立精确 inventory 和退役任务。
