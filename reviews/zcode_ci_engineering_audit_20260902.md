# 竞品调研多 Skill 工作流 · 工程审计与推荐建议

- 审计日期：2026-09-02
- 审计者：ZCode（用户委托的外部工程 review，非 trellis 治理链内的 self-review）
- 审计对象：`/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`（新工程，HEAD `bb27ec9`，847 项脏树）
- 参照基准：v1.2 设计规格、2026-08-10 重构实施计划（1968 行）、Task 10.6 暂停 handoff（`PAUSE_HANDOFF_20260902_114643.md`）、旧根两份决策记录（D-00~D-44）、用户 2026-09-02 两轮共八项裁决（第一轮：多宿主分发/旧根可删/可先投产/治理交 Codex；第二轮：药智网纳入/skill 包分发/手动刷新/首版仅 HTML）
- 方法：文档全读 + git 历史核对 + 源码/测试/治理产物抽样 + 真实报告产物（AD-A、PNH-B、fixture-C 门户与 8.5 HTML-PPT 截图）实物查看 + 单元测试/ruff/mypy 实际运行
- 局限：未运行全量 2689 项测试（浏览器/Office 轨未执行）；worker_01 未完成部分未逐字节审计（按 handoff 保持 PENDING）；视觉评估基于存档截图而非新渲染

---

## 1. 用户原始要求 → 规格 → 实现的追溯链

### 1.1 需求演进四阶段（均已核实）

| 阶段 | 载体 | 核心内容 |
|---|---|---|
| ① 初稿访谈（07-27~08-07） | 旧根《提问与决策记录》D-00~D-16 | 三类报告定位、读者=医学经理/总监+高管、药智网+八类公开源+四公众号、康哲美学、全自动 LOOP+唯一人工中断点 |
| ② 深化访谈（08-08） | 《深化提问与决策记录》D-17~D-44 | 7 维 PICOS 扩展、专用图表族（雷达/瀑布/泳道/热力图）、高级分析（四象限、速度排名、宽严/创新度指数、聚类、Bucher）、全交互（Excel 导出、暗色、书签） |
| ③ 重构访谈+规格冻结（08-09~08-10） | v1.2 规格及其内化的 D01–D70 | 科学真源+控制图+门槛体系；**主动废除②中大部分评分/排名类需求**（附录 B）；HTML/PDF/HTML-PPT/PPTX 四轨 |
| ④ 实施（08-10~09-02） | 实施计划 + trellis 治理链 | Phase 0-10 分解；当前推进至 10.6A（被用户无损暂停） |

**结论：需求链路完整、无断档，②→③的大幅收窄是有意识的科学严谨性取舍（可从 v1.2 附录 A/B 逐条对应），不是遗漏。** 但③收窄时未向用户逐项回显"哪些②需求被永久放弃了"（见 1.3），这是沟通缺口而非工程缺口。

### 1.2 核心需求落地状态矩阵

| 原始需求（编号） | v1.2 规格 | 实现现状 | 判定 |
|---|---|---|---|
| 最小输入全自动（D-08） | §3.1 | CLI `project create/run` + research-package 交接 | ⚠️ 部分偏离（见 1.4-A） |
| A=适应症百科全书+汇总对比（D-09） | §12 十一类页面 | 真实 AD 门户：12 静态页 + **38 个产品独立档案**，全站导航/搜索在位 | ✅ |
| A 历时路线图（D-09） | §12.3 开发时间线 | 产品档案含开发时间线（regulatory/patents/history_edge 模板均有时间线） | ✅（建议增强，见 5.2） |
| B=横向多维对比+雷达/气泡图（D-09/D-29） | §13 | 真实 PNH 门户全页面族（疗效/安全/基线/完成情况/矩阵/plan-deviation/loss-exit） | ✅ 主体；雷达图仅 chart_specs 声明，未见页面落地（见 5.2-R1） |
| C=PICOS 延伸+单试验完整+多试验对比（D-09/08-08 七维） | §14 十二类页面 | fixture C 门户 12 页；真实 C 走过 blocked→补件→恢复全链 | ✅ |
| 证据门槛+不造假（D-12） | §8.7 GateSpec | 39 schema + gate evaluator + no-draft 全负断言测试 | ✅ |
| 来源体系（D-05：药智网/八类源/公众号） | §11 | connectors 六类解析器 + 五公众号（新增"中国药审"） | ⚠️ 药智网已裁决纳入、待实现（见 1.4-B/§4.6） |
| 冲突裁决规则（D-06） | §11.1 声明—来源策略 | source-policy + conflict_sets + 裁决版本化 | ✅ |
| 康哲美学（D-07/D-11） | §15/§16 双合同 | 令牌化 CSS + 合同摘要锁定 + 11 轮视觉会商打磨 | ✅ |
| PDF/PPT 按需（D-07） | §16 四格式 | PDF 原生 ReportLab、HTML-PPT 运行时、PPT Master 串行收据链 | ✅（代码层） |
| 持续跟踪/增量更新（D-04/D-32） | §17 | refresh_service + refresh_candidates + 合同版本化 | ✅ |
| 全交互：Excel 导出/暗色/书签（D-33） | §16.1 仅两种导出物；**暗色被禁** | Excel/CSV 导出**零实现** | ❌（见 5.2-R2） |
| 高级分析：四象限/速度排名/指数/聚类/Bucher（D-20/21/26/27/36/37） | **附录 B 明确禁止** | 未实现（正确） | ✅ 维持禁止 |
| 三宿主可安装（D-16/D-18 语境） | §6 | codex/hermes/omp 适配器 + fresh-install + host-smoke-v1 | ✅ 代码层，10.6C 待终验 |

### 1.3 被永久放弃的原始需求清单（建议向用户回显确认一次）

②阶段立项、③阶段静默放弃或反转的：竞争态势四象限（D-20）、研发速度排名（D-21/40）、入排宽严指数（D-26）、方案创新度指数（D-27/41）、相似度聚类 PCoA+Ward（D-36/43）、Bucher 虚拟间接比较（D-37）、瀑布图、企业关系网图、给药泳道图、暗色模式、书签标注。**本审计认同全部放弃**（理由：任意权重评分与跨试验合成结论对医学读者是误导源，v1.2 的"事实可比、不做裁决"路线科学上更稳），但建议在 v1.3 或用户指南里保留一张"需求墓地"表，避免未来反复。

### 1.4 已知偏离项

- **A（架构性偏离，已成事实但未成文）**：设计书 §9/§11 的"来源路由与检索"内部 Skill 是自动路由；实际落地为**宿主 Agent 手工检索 → research-package JSON → 确定性引擎**（`source_research_service.py` 自述"宿主 Agent 与确定性执行器之间的交接合同"）。`src/ci_workflow` 全包无 HTTP 客户端。这是更诚实的架构（LLM 检索、代码管门槛），但**规格与实现双重本体**：connectors 定位漂移为"解析器库"，§10.3 双重穷尽在手工模式下部分沦为文书。**建议：写 ADR 正名 + 规格 v1.3 附录追认**（详见 4.3/5.1-F1）。
- **B（未实现来源，已裁决补齐）**：药智网企业版路线（D-05/D-23）在 v1.2 中未获指定来源资格。用户 2026-09-02 已裁决纳入（凭据用 Edge Lite joincare 账户本地联调），落地路径见 §4.6 与 5.2-F2/F9；需补一条 D 级决策与来源政策条目。
- **C（流程性偏离）**：见第 3 节 P0-1/P0-2。

---

## 2. 六条报告标准逐项评估（基于实物证据）

用户标准：**完整、全面、横向可对比、可视化、清晰明确、美观亮丽**。评估对象：真实数据 AD-A 门户（`a-values-matrix-fix-final-v5`）、真实 PNH-B 门户（10.2 run）、fixture C 门户、8.5 HTML-PPT 全页截图、R13 安全页全页截图。

| 标准 | 现状 | 证据 | 差距 |
|---|---|---|---|
| **完整**（不截断、不空壳） | **达标且是本项目最强项** | A 门户 38 产品档案逐药可下钻；no-draft 负断言覆盖 A 空宇宙/B 无适格试验/C 缺关键设计等全部阻断分支；真实 C 走过 blocked→补件→恢复 | 无重大差距 |
| **全面**（字段覆盖） | 达标 | 39 个 schema 覆盖九组状态、D70 基线/处置字段族全建模（含非阻断的披露状态矩阵）；类型化缺失状态（未报告/未公开/技术不可用/为 0 分列） | 分子细节/交易金额/专利族为非阻断扩展层，符合设计取舍 |
| **横向可对比** | 主体达标 | 终点/时间窗兼容规则+小多图自动拆分；气泡矩阵（x=疗效信号、y=倒序 TEAE、面积=N）；安全热图产品×事件；证据抽屉同链下钻 | **R1 雷达图未落地**（D-29 需求，chart_specs 已声明）；**R3 证据成熟度矩阵未呈现**（D-30 双轴信号有字段无视图） |
| **可视化** | 达标偏上 | ECharts SVG 离线、图前表后合同、热图单元格印数值+类型化缺失 | **R4 安全热图无色标图例、无对照/分母上下文列**（视觉抽查实测）；HTML-PPT 部分页密度偏低（13/20 页下半幅近空） |
| **清晰明确** | 达标 | 中文原生文案合同有测试把关（prompt/log 标签禁入首页）；证据抽屉逐字段定位 | 无重大差距 |
| **美观亮丽** | 中上水平 | 康哲令牌浅色系统一、双浏览器全路由截图验收、11 轮视觉会商已打磨 A 类 | 中文字号偏小（1024 宽全页截图实测）；长表跨页节奏、图表图例体系仍有打磨空间（见 5.2 清单） |

**总评：六条标准里"完整/全面/清晰"已达产品级；"横向可对比/可视化/美观"达到中上，与"亮丽"尚差一轮系统性的呈现层打磨**——而且差距是具体可列举的（第 5.2 节），不是抽象的。

---

## 3. 工程问题清单（按优先级）

### P0（阻塞一切后续验收/投产，先于 10.6 续接处理）

**P0-1 Git 断层：8/27（Task 5.5）后 6 天工作零提交**
- 事实：Phase 6→10.6 全部源码（44 新增+24 修改 src/tools/tests 文件）在 847 项脏树中；worker 改动/用户改动/运行证据不可归因（handoff §6 自认）。
- 后果：10.6B"clean commit + dirty fail-closed"无法启动；无回滚点。
- 方案：①先修 P0-2；②按 Phase 6/7/8/9/10 逻辑分组快照提交（治理 md/json 单独 1-2 个 commit）；③`.gitignore` 补 `runs/`、`logs/`、`tmp/`、`Products/`；④把"任务收尾 `git status` 仅剩白名单路径"写入 workflow-state enforcement 行 + `task.py finish` 钩子（workflow.md 113-118 行注释已预言过此故障模式）。

**P0-2 全局质量门静默失效（false-green 治理层复发）**
- 事实：当前树 `mypy --strict src/ci_workflow` **77 错/19 文件**（pdf_native 系 ~35、html_ppt ~10、report_b 8、run_service 4）；ruff 3 错。而 Task 10.5 检查点声称"Ruff、mypy 通过"——实为按文件粒度局部通过。这正是附录 B 禁止的"QC 退出 0=完成"在治理层复发。
- 方案：①集中修复（估 1-2 天，pdf_native 占半）；②建单一 `gate` 命令（ruff+mypy strict 全仓+fast 测试段），**worker 报告接受前必须附 gate 全量输出**；③execution metrics 模板增设"声明的检查范围"必填字段。

**P0-3 合同冲突未裁决先派工**
- handoff §7 Q1-Q6 未裁决，worker_01 已按个人解读改 `bundle_contract.py` required content（Q4 冲突方向）。
- 方案：严格按 handoff §9 顺序——先裁决写入 design/checkpoint，再审计字节。裁决建议：**Q1** 复合摘要 `sha256(canonical_json({schema_version, source_commit, bundle_sha256, package_manifest_sha256, catalog_sha256, release_scope}))`（repo commit 是 SHA-1，不能冒充 SHA-256）；**Q2** 保持双层信封、freeze producer 显式绑定；**Q3** `legacy-absence` 坚持 `pending_future=1`，修 `verify_release_receipts.py` 可 accepted 漏洞；**Q4** cutover 工具**不进运行时 bundle**，按 10.5 裁决作仓库治理工具、摘要入 RC 记录，同时显式修订计划中"fresh bundle 含 cutover tools"条款；**Q5** 产品入口用安装包、治理 verifier 用 clean RC worktree、receipt 绑同一 RC 身份；**Q6** `formats` 由当次 artifact manifests 实际计算——首版按 HTML-only 裁决（§4.5）即为 `formats=1`，仍须由当次 manifest 计算而非硬编码。

### P1（持续放血，投产前处理）

- **P1-1 治理开销失衡**：667 个治理文件（metrics 148/reviews 297/plans 105/context 214/conference 34）；logs 1.5GB（单视觉会商 226MB）、.artifacts 1GB（A 门户 ~103MB final 复制 v1/v2/v4/v5 四份+3 candidate）。**判断材料已备好（本清单+第 4.4 节），按用户裁决交 Codex 定瘦身方案**；本审计仅建议两条硬约束：全量证据只在 `runs/`（gitignore+归档），reviews 只存 digest+指针+抽样截图；同任务视觉会商上限 2 轮，第 3 轮起主 Agent 直修+单验证者复核。
- **P1-2 旧根只读防线无强制力**：旧根 `verification/A|B|C/v-fixture-001/` 于 9/2 05:49 被写入（疑似 `fixture run --project` 指错目录）；`.pytest_cache` 9 月被更新。`check_no_legacy_refs.py` 只防代码引用，防不住运行时写入。方案：立即 `chmod -R a-w` 旧根；排查写入来源。**用户已裁决旧根可删——但删除是 10.8 的终点动作，burn-in 期间只读强制仍必需。**
- **P1-3 规格与实现双重本体**（见 1.4-A）：写 ADR + 规格 v1.3 附录追认 research-package 架构。
- **P1-4 巨型文件**：`reports/a/pages.py` 4669 行/184 函数、`renderers/portal/report_b.py` 4044 行、`acceptance_runner.py` 3026 行、`run_service.py` 2533 行。mypy 错误分布证明 Phase 8 后代码纪律松动。冻结前把 `report_X.py` 拆"数据投影/站点组装"两层即可，不必大重构。
- **P1-5 杂项**：`migration/`（legacy 清单）与 `migrations/`（SQL）改名消歧（如 `legacy-migration/`）；清 `Products/`、`tmp/`、`spikes/` 残留；pyproject `>=3.12` 与计划书"3.11+"文档同步。

### 已核实为**健康**、无需动的部分

九组状态枚举严格落地；SQLite 真源+内容寻址证据+append-only 触发器；fixture catalog+case digest+current-run 绑定（真实防住旧证据复用，10.2 诊断目录里 noncanonical-version/indication-mismatch 被 fail-closed 拦下是正面证据）；单元测试 536/536 通过（47s）；无出网设计使确定性引擎名副其实；暂停 handoff 质量极高（Q1-Q6 识别即高质量审计产物）。

---

## 4. 用户裁决的落地路径（2026-09-02 两轮共八项已确认）

第一轮：多宿主分发 / 旧根可删 / 可先投产+QC loop / 治理密度交 Codex。第二轮：药智网纳入来源政策（凭据用 Edge Lite joincare 账户本地测试）/ 同事拿 skill 包按关键词调用 / 全部手动触发不自动刷新 / **首版输出仅 HTML 门户**。

### 4.1 多宿主分发 → 保留三宿主合同全量；分发形态确认为 skill 包
- 保留：codex/hermes/omp 适配器一致性测试、bundle/fresh-install 合同、host-smoke-v1 真实宿主执行、10.6C 最终包三宿主重跑。
- 不减配：`HA09` 真实宿主 smoke（防同进程伪造三份 receipt 的设计是真金白银的价值）。
- 可延后：LangGraph 适配器 E1 维持 indefinite defer（设计书本就定为 RC 后非阻断）。
- **分发形态裁决（第二轮）：同事拿到的是 skill 安装包，在各自 Agent 中通过特定关键词调用公共入口 Skill。** 由此新增两条要求：①公共 `SKILL.md` 的关键词触发词、最小输入引导和错误提示是最终用户的第一触点，其文案质量与安装文档要按"产品说明书"标准验收（现仅按"能力边界描述"验收）；②宿主能力预检的失败提示必须给非技术医学同事可执行的修复指引（如"请联系管理员安装 Playwright"），这是分发后最主要的求助来源。
- **含义：P0-1/P0-2 修复后，10.6B-D 的验收链必须走完才能分发——不能拿脏树+红灯门禁的包给其他宿主装。**

### 4.2 旧工程可删 → 删除链保留，建议加 burn-in
- 顺序：**先投产运行 ≥2 周（真实报告 ≥3 个适应症）→ 10.6 RC 冻结 → 10.7 干运行+授权 → 10.8 精确删除+残留扫描**。归档副本方案不替代删除（用户已明确可删），但 burn-in 保证删的时候新系统已被真实使用验证。
- 删除前动作：旧根内**未迁移资产的最后一次盘点**（`_ref/share_all_msgs.json` 的 D-12~D-16 证据链、七份旧报告的脱敏回归样本是否已按迁移清单闭合）。

### 4.3 先投产 + QC loop → 双轨制（本审计核心路线建议）
- **A 轨（投产轨）**：P0 修复后，用当前引擎出真实报告。QC loop 复用现有资产：`verify_portal` 双浏览器全路由 + 科学 QC 门 + 视觉会商（限 2 轮）+ 用户抽读。每个真实项目天然是 10.6C"fresh-source A/B/C"的预演。
- **B 轨（验收轨）**：10.6B-D 按裁决后的合同推进，投产发现的问题按正常修复流进入下一 RC 候选。
- 两轨交汇：投产 2-3 周后选一个稳定点做 RC commit（此时真实使用已替代大部分"合成 fixture 全矩阵"的信心价值）。
- **投产轨前置条件只有三个：P0-1 提交、P0-2 gate 全绿、Q4 裁决（避免 bundle 合同返工）。**

### 4.4 治理密度 → 交 Codex 判断（本审计只提供材料）
- 数据：667 治理文件/3.5 周；每任务固定开销 = execution packet + 3 worker 会商 + conference 评审 + metrics/reviews 归档；11 轮视觉会商中 Task 10.2 一项占 5 轮。
- 因果观察：治理负担上升期（Phase 8 后）恰是提交纪律与全仓门禁失守期——**注意力被搬运证据消耗，挤掉了真正校验**。判断时应把"治理密度 vs 校验有效性"作为一体权衡，而非独立成本项。

### 4.5 首版仅 HTML 门户 → 剩余验收链大幅收缩（第二轮裁决，影响最大）

- **裁决**：首版输出只要 HTML 门户；PDF、HTML-PPT、PPTX 均不需要。
- **处置原则：代码保留、验收摘除。** Phase 8 已建成的三条格式轨（原生 PDF ~15 文件、HTML-PPT 运行时+投影、PPT Master 收据链）不删除、不降级，作为后续版本能力；仅从首版 RC 验收合同中移除。
- **直接收缩项**：
  1. RC 冻结信号 `RC_FROZEN reports=3 formats=4 hosts=3` → **`formats=1`**；
  2. full-matrix 的 PPTX 八项确认中断、G1-G3 三个 PPT Master 串行作业、`--prepare/--resume` 两阶段编排中的 PPTX 分支全部摘除；
  3. Task 8.10 跨格式覆盖（`coverage_projection` 四格式比对）降为 HTML 单格式自洽校验；
  4. capability preflight 默认不再检查 PPT Master/PowerPoint/Poppler（保留代码路径，选择对应格式时才检查）；
  5. `required-v12` catalog 中 `formats=4` 相关 case 族（`b-interaction-cross-format`、`kangzhe-and-large-project-runtime` 的 PPT 部分、full-matrix 的 12-artifact 断言 → 3-artifact）需重新生成；
  6. handoff Q6（formats=4 权威来源）随之简化：冻结信号由当次 A/B/C × HTML 的 artifact manifests 实际计算。
- **工作量影响**：剩余 10.6B-D + 10.9 的验收体量估计下降 40-50%；PPT Master 串行作业（不可并行、主 Agent 逐页制作）原本是剩余链路中最大的时间黑洞，摘除后 RC 冻结路径显著变短。
- **必须的合同动作**：写一份《首版发布范围定义》（release-scope-v1），正式声明 formats=1、监测移除、刷新为手动，作为 required-v12 catalog 再生成和 10.6 冻结合同的合法依据——**不能靠口头范围收缩去跑验收链**，否则 runner 里的 12-artifact 断言会全部 fail。
- **对投产轨同样有利**：QC loop 只需 `verify_portal` 双浏览器全路由 + 科学 QC 门，无需 Office/PDF 环境。

### 4.6 药智网企业版纳入来源政策（第二轮裁决）

- 需新增一条 D 级决策：药智网（vip.yaozh.com）获得指定来源资格，声明域按 D-05 的 API 分类（全球药物/中国上市/全球临床/注册/说明书/FDA/企业），来源角色与披露成熟度按"商业数据库"类标注，与官方登记/监管交叉核验，不单独直接替代官方来源。
- **凭据边界（沿用 D-23 + v1.2 §18.3/18.4）**：用户名/密码存本地安全配置（环境变量或本机配置文件，路径不入库不入包），bundle/日志/回执零凭据，秘密扫描保持强制。用户已授权实施阶段用 Edge Lite 浏览器中 joincare 账户做本地联调。
- **工程量**：新增 `sources/connectors/yaozh.py`（D-05 已记录 API 细节：端点 `https://vip.yaozh.com/api/{globaldrugs,cfdadrug,clinical,zhuce,instruct,fdadrug,company_filter}`，响应包在 `data.List.res`），走与 CT.gov 拉取器相同的"纯 HTTP+分页+限速+回执"模式（见 5.2-F2/F9）。
- 中国来源覆盖因此显著增强：药智网 + CDE/chinadrugtrials + 丁香园 + 五公众号，中国竞品的身份/状态/交易字段获取难度下降。

---

## 5. 推荐清单

### 5.1 新增约束（低成本高杠杆）

| # | 约束 | 动机 |
|---|---|---|
| C1 | 全仓 `gate`（ruff+mypy strict+fast 测试）为唯一绿灯口径；worker 报告必附 gate 输出 | 封堵 P0-2 复发 |
| C2 | 任务收尾 git 白名单检查进 workflow enforcement + `task.py finish` 钩子 | 封堵 P0-1 复发 |
| C3 | 证据保留策略：全量产物只在 `runs/`（gitignore）；`reviews/` 只存 digest+指针+抽样截图；同门户迭代禁全量复制 | 直接止血 1GB+ 磁盘与 667 文件 |
| C4 | 旧根 `chmod -R a-w` 机械强制（10.8 前一直生效） | 封堵 P1-2 |
| C5 | 报告六标准固化为**逐报告类型的视觉评审 checklist**（现有 conference 评审的收口版），每条含"实测截图锚点"字段 | 把"美观亮丽"从主观轮询变成可核对项 |
| C6 | HTML-PPT 页面信息密度下限（除封面/章节页外，内容页主区留白 >40% 触发否决） | 13/20 页实测密度偏低 |

### 5.2 新增功能/呈现方式（按价值排序）

| # | 功能 | 依据 | 量级 |
|---|---|---|---|
| F1 | **`ci-workflow research scaffold`**：给定适应症生成待填 research-package 骨架+schema 即时校验+来源清单模板（CT.gov 查询 URL、CDE/登记平台链接、公众号检索式、PubMed 检索式） | 检索已确认为宿主手工模式，这是当前**最大产能瓶颈**；架构已在 1.4-A 正名后此命令是自然配套 | 小（1-2 天） |
| F2 | **来源拉取器双件套：CT.gov + 药智网**（纯 HTTP+分页+限速+回执，不出浏览器；药智网凭据走本地安全配置） | CT.gov API 干净公开、药智网已获用户裁决纳入（4.6）；两者都是"最机械的下载劳动"，自动化后宿主 Agent 专注判断性检索；解析器基础已就绪 | 中 |
| F3 | **表格级 CSV/XLSX 导出**（每个图下完整表加"导出"按钮，从 view model 投影） | 恢复被静默放弃的 D-33；医学经理把数据带进 Excel 是真实高频需求；"视图不回写事实"合同天然兼容 | 小 |
| F4 | **B 类雷达图落地**（疗效/安全维度归一化雷达，可逆+原始值表，chart_specs 已声明） | 恢复 D-29；横向可对比短板 R1；规格已允许（§15.3"明确归一化的雷达图"） | 小 |
| F5 | **证据成熟度矩阵视图**（产品×试验矩阵，披露渠道级×设计类型双轴信号） | 恢复 D-30 的呈现意图；字段已有（`disclosure_maturity`），缺的只是视图；高管读者"一眼看出证据水平" | 小 |
| F6 | **A 产品档案"适应症开发路线图"增强**：现状是开发时间线；增强为适应症×年份泳道图（同一分子跨适应症扩张轨迹） | D-09 原文"每个适应症/药物的历时路线图"；对"这个药下一步会不会打我们的适应症"是医学经理核心问题 | 中 |
| F7 | **安全热图补强**：色标图例、对照列/分母列、可切换"率值/绝对数" | 横向可对比短板 R4（视觉抽查实测）；v1.2 §13.4"数值必须印在单元格中"已达标，缺的是图例与上下文列 | 小 |
| F8 | **刷新"变化亮点"页**：手动 refresh 后门户首页顶部"本次更新：新增 X 试验、Y 字段变更、Z 状态迁移" | D-04 持续跟踪的呈现闭环；用户已确认刷新为手动触发（第二轮裁决），此页让每次手动刷新的结果可被快速感知；refresh_candidates 数据已有，缺聚合呈现 | 小 |
| F9 | **《首版发布范围定义》release-scope-v1**（formats=1、监测移除、刷新手动） | 4.5 的合同动作；required-v12 catalog 再生成与 10.6 冻结合同的合法依据 | 小（文档+catalog 再生成） |

### 5.3 明确不建议恢复/不建议做的项

- 维持 v1.2 禁止：四象限综合图、研发速度排名、入排宽严指数、创新度指数、任意加权评分、Bucher/MAIC/NMA、暗色模式、Top-N 截断。理由：均为"替读者做裁决"的功能，与"事实可比、结论留给读者"的产品哲学冲突；D13→D31→v1.2 的演进方向一致且正确。
- **自动监测（§17.3 / Task 9.3 monitoring skill）：按第二轮裁决移出范围**（用户确认全部手动触发）。已建 monitoring 代码保留但标记 `not_applicable` 回执路径（catalog 中 E1 条目同款处理），不进入首版验收。
- PDF/HTML-PPT/PPTX 三条格式轨：**首版摘除、代码保留**（见 4.5），待真实使用反馈决定是否在 v1.1 恢复。

### 5.4 路线图（按 HTML-only 首版收缩后修订，自暂停点起）

1. **第 1 周（P0+投产启动）**：修 77 个 mypy 错+建 gate → 分组快照提交 6 天积压 → Q1-Q6 裁决落档（Q6 按 formats=1 简化）→ 写 release-scope-v1 + ADR 正名 research-package 架构 → 旧根 `chmod -R a-w`。**并行启动投产轨第一个真实项目**（新适应症）。
2. **第 2 周（投产 QC loop + 范围收缩落地）**：required-v12 catalog 按 formats=1 再生成、full-matrix runner 摘除 PPTX 分支；投产轨跑通 QC loop（verify_portal 双浏览器+科学 QC+限 2 轮视觉会商）；F1 research scaffold + F3 表格导出 + F7 热图补强（小件三合一）。
3. **第 3 周（RC 收口）**：10.6A 收尾（worker_01 重审+负向测试）→ 10.6B source closure + RC commit → 10.6C 用最终包重跑 fresh A/B/C + full-matrix（formats=1，无 PPT Master 作业，预计 1-2 天可完成原需 1 周的环节）→ 10.6D 恢复演练+RC_FROZEN。F4 雷达图/F5 成熟度矩阵/F8 变化亮点页视投产反馈排入。
4. **第 4 周起（分发与删除）**：10.7 切换干运行+授权；skill 包分发给首批同事（关键词触发验收=F2 的 SKILL.md 文案标准）；视 burn-in 情况排期 10.8 删除旧根。F2/F9 拉取器双件套（含药智网 joincare 联调）在第 3-4 周窗口实施。
5. 治理瘦身方案由 Codex 基于第 4.4 节材料并行给出，不阻塞主线。

---

## 6. 裁决记录（两轮八项，2026-09-02 全部闭合）

| # | 问题 | 用户裁决 | 落地章节 |
|---|---|---|---|
| 1 | 产品定位 | 多宿主分发的正式产品 | §4.1 |
| 2 | 旧工程处置 | 确认不用即可删除 | §4.2（含 burn-in 建议） |
| 3 | 投产门槛 | 当前系统即可出真实报告+QC loop | §4.3 双轨制 |
| 4 | 治理密度 | 交 Codex 判断 | §4.4 材料已备 |
| 5 | 药智网 | 纳入来源政策；凭据用 Edge Lite joincare 账户本地测试 | §4.6 |
| 6 | 分发形态 | skill 包，同事按关键词在 Agent 中调用 | §4.1 |
| 7 | 刷新方式 | 全部手动触发，不做自动增量刷新 | §5.3（监测移出范围） |
| 8 | 首版格式 | 仅 HTML 门户；PDF/HTML-PPT/PPTX 均不需要 | §4.5（代码保留、验收摘除） |

**残留的少量实施级确认**（不需要现在回答，实施时顺带处理即可）：
- release-scope-v1 文档中 `formats=1` 后，`coverage_projection`/`artifact-manifest` 的四格式 schema 字段保留但首版只产 HTML 一条（schema 不破坏，后续恢复格式无需迁移）；
- skill 包关键词触发词的最终措辞（建议中文短词，如"竞品调研"，写入 SKILL.md frontmatter 与安装文档）；
- 药智网凭据的本地存储位置（环境变量 `CI_YAOZH_*` 或本机配置文件，实施时定，原则只有一条：不入库不入包不入日志）。

---

## 附录：关键证据索引

- Git 断层：`git log` 最后提交 `bb27ec9` 2026-08-27；`git status --porcelain | wc -l` = 847；src 脏文件 68（44 新增+24 修改）
- 质量门：`mypy --strict src/ci_workflow` = 77 errors/19 files（pdf_native/c.py 16、report_b.py 8、flowables.py 8、a_pages.py 7、run_service.py 4 等）；`ruff check` 3 errors；`pytest tests/unit` = 536 passed/47s；全量 collect 2689 tests
- 治理体量：metrics 148 文件/reviews 297/plans 105/context 214/conference 34；logs 1.5GB（conference 779M+execution 664M）；runs 774M；.artifacts 1.0G（a-values-matrix-fix-final-v1/v2/v4/v5 各 ~103M）
- 旧根污染：`竞品调研工作流/verification/{A,B,C}/v-fixture-001/` mtime 2026-09-02 05:49；`.pytest_cache/v/cache/nodeids` 9 月更新
- 真实产物：AD-A 门户 12 静态页+38 产品档案（`a-values-matrix-fix-final-v5/reports/A/v1/html/`）；PNH-B 门户（`runs/acceptance/task-10.2-20260901-123524/.../reports/B/v-real-b-pnh-20260901/html/`，含 safety/plan-deviation/loss-exit）；C blocked→恢复链（`research/c-real/html-initial-blocked`→`html-preview`）
- 视觉抽查：`docs/acceptance/runs/8.5/screenshots/a-matrix.png`（HTML-PPT 13/20 页，密度偏低）；`reviews/ci_phase5_a_values_matrix_fix_screenshots/final-v1/chromium-1024-safety-full.png`（热图无图例/无对照列/字号偏小，数值标注与类型化缺失达标）
- 架构偏离：`grep -rn "urllib|requests|httpx" src/` 仅 `urllib.parse`；`source_research_service.py` 文档字符串自述交接合同
- 未实现确认：Excel/CSV 导出 grep 零命中；雷达图仅 `chart_specs.py` 声明
- 治理链状态：10.6A in_progress（worker_01 PENDING）；10.5 检查点 `checkpoint_20260902_completed.md`
