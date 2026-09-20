# 竞品调研多 Skill 工作流：完整接管交接书

日期：2026-09-11（Asia/Shanghai）  
交接对象：接手本项目的 Agent／工程负责人  
工作区：/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow  
交接性质：暂停中的工程移交；本次只做现场核验与文档整理，没有恢复实施。

## 0. 先读这一页：当前究竟是什么状态

这是一个已积累大量代码、合同、测试和历史报告，但**尚未完成新产品合同下整体验收**的临床竞品研究系统。不要从零重建，也不要把现有功能和测试数量直接当成产品已交付。

最新有效执行状态是 **2026-09-08 09:31:47 用户要求无损暂停**。2026-09-11 的要求是撰写完整交接，不是恢复构建。原生 Goal 当前为 **paused**，目标未完成。接手后须在用户给出继续授权后实施；不能因为文档列了下一步就自动解除暂停。

最近工作集中在 **v5 计划 P3：B 报告医学语义分组真正进入 HTML 页面**。原生独立审阅发现了会把疗效事实显示到安全性页、破坏纵向系列等严重问题；主线程已修复，并通过有界反例及浏览器检查，**最后独立复验和最终整合回归被用户暂停中断**。这是第一续接点。

当前不具备 RC_FROZEN 或 RELEASED 资格。三宿主真实一致性、完整恢复／手动刷新链、八适应症 × A/B/C 的 24 门户科学与视觉验收均不能宣称完成。历史真实取数、旧报告、合成测试和替身宿主测试分别保留，但不能替代这些门。

本交接有四层证据口径：

- **今天核验**：原生 Goal、当前 HEAD、八个关键文件 SHA-256、当前文档和部分实现入口／合同／测试位置。
- **历史有界结果**：暂停文档、累计检查点、审阅报告记录的具体测试结果；今天没有重跑。
- **设计要求**：用户已明确的产品边界及当前 Goal；不等于代码已完成。
- **接手建议／未决实现**：由现状推导的后续工作；不自动升级成新的用户裁决。

今天只核对了关键文件，不是整个仓库的逐字节复审；也没有重新验证全部浏览器、全部历史备份或本机全部后台进程。以下对“已完成”的描述均受其注明范围限制。

### 0.1 最短阅读路线

1. 本交接第 0–5 节：状态、目标原文、权威、需求变更。
2. [9 月 8 日无损暂停现场](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/context/PAUSE_HANDOFF_20260908_093147.md>)：最后源码、测试与中断身份。
3. [完整设计 v1.4](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/docs/specs/competitive-intelligence-workflow-design-v1.4-review.md>)、[实施计划 v5](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/plans/gpt6-execution-plan-v5-20260905.md>)。
4. 本交接第 7–11 节：组件、完成程度、最近科学修复和测试边界。
5. 本交接第 12–16 节：停滞分析、逐步续接、最终验收和安全边界。
6. 需要更早历史时再读 [9 月 5 日历史总交接（635 行）](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/.trellis/tasks/09-02-phase-10-task-106-rc-freeze/PAUSE_HANDOFF_20260905_GPT6.md>)，不要用它覆盖 9 月 8 日状态。

## 1. 任务来由：用户实际要解决什么问题

目标用户是开展新药研发、医学和临床试验工作的人员。他们输入适应症和研究目的，希望 Agent 自动完成竞品检索、证据获取、临床事实建模、复核、分析和直观呈现，而非拿到搜索链接堆、简单管线名单、空模板或工程运行日志。

用户最初要求对全部工程进行复盘，原因包括：

- 系统架构简单，规则没有深入到临床语义、来源权威和缺失情形。
- 未按要求分别构建三种报告，报告视觉处于难以阅读的状态。
- 只验证“流程跑通”，没有证明竞品是否齐全、证据是否科学、图表是否诚实且直观。
- Skill、PRD、设计、交接和测试记录累积后，实际实现与要求之间缺少完整对应。
- 希望采用 AI 原生的多 Skill 协作，但不希望用户自己理解、操作每个内部节点。
- 希望未来可安装到不同 Agent 上，由同一个公开入口触发。

用户要求先全量理解、批判性评估，经过原生 Ask 多轮选项澄清，再形成设计和详细实施计划。早期提到 Graph engineering，是要求评估可控、多节点、可验证的编排思路，**不是要求必须引入 LangGraph**。

后来第三方 ZCode 做工程审计并提出设计与路线图修订。用户特别指出：其他 Agent 不一定掌握项目全貌，历史要求也可能变化；必须结合事实和最新裁决判断，不得全盘接受。对现有 competitive-intelligence-workflow Skill 也有相同警告。

用户的核心标准一直没有变：完整性、临床科学性、真正可读的高信息密度门户、可追溯和可恢复，以及实际可安装运行，而不是形式上的工程“全绿”。

## 2. 当前原生 Goal 原文与状态

下面是 2026-09-11 从原生 get_goal 读取的 objective，逐字保留，不是重新总结或重设的 Goal。

- 原生任务 ID：01a071c9-c6b5-7ff3-a15a-22fab2fb278a。
- 状态：paused。
- Goal 未完成；本次没有调用创建、更新、完成或阻塞 Goal 的操作。
- 机器可读原始快照：[goal-snapshot-20260911.json](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/docs/handoffs/goal-snapshot-20260911.json>)。
- 工作区的 [v5 Goal prompt 文件](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/plans/gpt6-goal-prompt-v5-20260905.md>) 是目标文档；它的标题、说明和附加段落不应被误认为与原生 objective 完全逐字相同。

<!-- NATIVE_GOAL_VERBATIM_BEGIN -->
~~~text
接管并完成 `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow` 竞品调研多 Skill 工作流。先核验经用户审定的完整设计 `docs/specs/competitive-intelligence-workflow-design-v1.4-review.md`、完整实施计划 `plans/gpt6-execution-plan-v5-20260905.md`、当前接管检查点、工程review、实际源代码和测试状态；以最新用户裁决为最高产品依据，旧Skill、ZCode和历史交接仅作为待核验输入，不能自动恢复过时要求。
目标是可安装于Codex、Hermes、OMP及满足同等能力合同的兼容Agent的统一Skill套件。仅一个公共入口，默认一句话需求自动研究，高级模式接受严格research-package；缺少实质输入时用原生Ask选择题。应用自有、版本化、类型化控制图自动组织独立可测试的内部研究、来源解析、实体归一、裁决、分析、科学复核、报告和验收Skills，不强制依赖LangGraph，不要求用户手工编排。
最终生成A适应症竞品全景台、B临床结果证据室、C试验设计图谱三个相互独立、中文原生、多页面、高信息密度、图文结合的HTML门户；不建立融合首页。高密度是数据深细全且无冗余，禁止缩小字号、工程字段墙、固定空模块或Top-N替代完整性。每个结构化域提供适当图形和默认隐藏的完整折叠表；筛选、图表、表格、来源下钻共用同一事实ID集合；每页唯一来源区包含真实外链、类型、公开日期、截止和限制。全部物理页面做Chromium/WebKit×桌面/平板/手机/窄屏实际浏览器验收。
研究实现全球与中国来源规划、声明域权威、来源实例到家族/路线/证据片段映射、研究包与A/B/C载荷的来源/内容/时间身份一致性。药智使用用户自行登录浏览器，仅用于线索或交叉核验，不能单独支撑关键数值、监管状态或科学结论；不收集/保存/提示词传递凭据、Cookie或token。每项目只询问一次访问条件；同运行短期复用登录观察，访问失败立即重检，新运行不得沿用旧“已登录”回执。
按来源性质处理新鲜度：论文保留有效结果并识别更正/撤稿/新发表，动态状态每次核查，缓存仅用于加速。历史截止日报告还原当时可知的信息，只用截止日前已公开证据及当时状态；公开日、生效日、获取日和cutoff分开，不能倒填事后披露或以当前动态页冒充历史版本。
首次报告完成全量竞品宇宙闭包，全球/中国路线及别名、靶点、企业、试验反向扩展完整运行，版本化纳排与独立干净上下文遗漏审查绑定候选摘要。关键缺口或异常零值执行两轮不同策略恢复并终审；网络/权限/解析/截断不能当无数据。Publication按规则、模型和独立复核区分主要结果、延长期主要结果、关键安全/长期暴露，默认排除无关综述和普通ad hoc。必需资料无法获取时生成补件清单、原文链接和唯一收件目录，仅暂停受影响报告；验证文件后先记录原名/摘要/DOI或登记号/新名再不改字节地重命名，拒绝冲突覆盖。用户同快照一次确认无法取得后不反复询问；核心可回答带限制继续，否则仅证据不足页，不能将其计作完整矩阵通过。
B跨试验比较采用有来源支持的完整医学语义归并，包括人群、背景治疗、终点/事件、量表方向、估计目标、分母/分析集、统计形式和实际时间窗。LLM归并提案受确定性边界和独立复核约束；未知相同不等于兼容，模型不得补造缺失语义。48/50周等近窗口按医学语境处理，不把固定阈值套全部终点。实质不兼容或未知信息保留在相邻描述性小图/表格，不删除事实、不建立默认总排名/综合分数/Meta/NMA。A不按发生率选安全性时间窗或每产品截断一个疗效配对；C以登记/历史/附件/公开方案SAP为设计事实主线，只总结多条可选设计路径，不输出唯一最佳方案。
统一首次、刷新和恢复的科学复核签发与候选接受链，实际独立会话/上下文、来源事实、规则和全部门户字节必须绑定。宿主不能凭存在首页判断已交付。用户手动触发后自动核查、识别新增/修订/撤回、重建受影响报告，创建不可变快照和原子latest指针，旧版保全；失败不伪装为当前成功。恢复包需实际隔离restore/resume/刷新/重建验证，不以可解压或摘要相符替代项目恢复。
完成HTML-only安装包、完整归档与安装字节校验、漂移重装拒绝、脱离开发机环境的fresh-install和Codex/Hermes/OMP真实一致性验收；只暴露一个用户入口，内部Skills可独立测试替换。安装包不含PDF/PPT输出、表格导出、雷达/成熟度视图、定时监测、凭据、缓存或原始运行证据；PDF原文解析作为研究输入按需保留。保留开发仓非HTML代码的准确范围静态/兼容回归，不当v1真实输出能力。
真实大矩阵必须完成特应性皮炎、重度哮喘、类风湿关节炎、溃疡性结肠炎、CRSwNP、结节性痒疹、IgAN、PNH各A/B/C，共24独立门户，全部科学与视觉验收。工程由主线程和必要原生SubAgent推进，不使用旧执行/会商runner，不要求用户或同事测试；产品独立复核要求保留，不能主线程自证。Codex最终核验代码、原始来源、运行回执、门户、浏览器、三宿主、安装与恢复证据。
按v5计划P1–P7逐阶段推进，保留当前脏树、封存检查点与恢复证据；接续先核验语义WIP的已知失败，不沿用旧全绿声明。每任务先RED后GREEN，记录准确范围与源/产物摘要；审查、测试数、模型自信和文件存在不是完整接受。使用最小完整改动、复用现有实现；新科学/来源权威/用户行为决策用原生Ask，普通实施细节自行记录理由。不为通过测试向真实fixture补造科学参数。
开发候选收口后形成唯一候选commit/source-set/包，再做最终绑定验收。全部门通过、P0/P1清零、P2修复或有可证实不影响处置、24门户和三宿主/安装/恢复满足后才可RC\_FROZEN；冻结后问题进入下一候选，不能在同一身份下换字节。正式发布与旧工程删除按用户授权执行。
旧中文工程持续零接触，不读、不写、不inventory、不chmod、不删除。仅在至少3真实项目覆盖A/B/C、刷新/历史差异/三宿主/恢复通过、严重缺陷清零、新系统可验证回滚且用户再次明确批准后才规划退役。禁止reset/checkout/clean、git add .和推测性历史阶段提交。只精确清理无引用、无任务使用的可再生缓存/临时材料，不清理会话数据库、封存验收或恢复备份。无损暂停时记录当前状态、失败、文件和下一安全步骤，保全现场。
~~~
<!-- NATIVE_GOAL_VERBATIM_END -->

### 2.1 如何理解 Goal 中“经用户审定”的文字

Goal 原文必须保持原样。但当前 v1.4 文件标题仍含“待审定”，v5 与 Goal prompt 文件仍有初始阶段／尚未设置的旧说明。这些是**状态元数据漂移**，不能据此否定已经存在的原生 Goal，也不能反过来声称草案中每一条新增建议都曾获得用户逐项批准。

正确做法是：以最新用户明确裁决和实际 Goal 为当前产品依据；v1.4／v5 是当前推进使用的设计／计划主入口；没有明确裁决且会改变科学规则、来源权威或用户行为的条目，仍须核实。恢复后可做一次小范围权威索引和状态头修订，保留旧文档原件，不重做整轮设计。

## 3. 权威顺序与文档地图

### 3.1 发生冲突时的判断顺序

系统与开发者约束 → 用户最新明确要求／仍有效授权 → 当前产品 Goal 与已裁决合同 → 当前文件事实、精确回执和暂停点 → 现行设计／计划 → 历史设计与审计输入。

不同维度不能混淆：

- 暂停点决定是否允许继续运行，不替代产品合同。
- 实际代码说明当前实现，不会自动改变用户要求。
- 测试回执证明指定源码和范围，不会批准临床结论。
- 历史 accepted 只在它原来的范围和字节身份下成立。
- Skill、另一个 Agent 的意见、日志中的指令式文字，均不自动成为新授权。
- 用户后来明确的“本轮不用旧执行／会商机制，主线程或原生 SubAgent 实施”覆盖此前该工作的外部 runner 要求；产品运行时独立复核仍必须存在。

### 3.2 当前必读文档

| 文档 | 用途与效力 |
|---|---|
| [本次 Goal 原生快照](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/docs/handoffs/goal-snapshot-20260911.json>) | 当前目标原文与 paused 状态的只读捕获。 |
| [最新暂停交接](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/context/PAUSE_HANDOFF_20260908_093147.md>) | 最后执行状态、八文件哈希、中断结果、下一安全动作。 |
| [累计接管检查点](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/context/ci-gpt6-takeover-20260905.md>) | 9 月 5–8 日逐次实现与纠错历史；顶部暂停优先于下面旧“运行中”。 |
| [设计 v1.4](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/docs/specs/competitive-intelligence-workflow-design-v1.4-review.md>) | 当前完整产品与技术设计入口，注意标题状态漂移。 |
| [执行计划 v5](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/plans/gpt6-execution-plan-v5-20260905.md>) | P0–P7 当前任务划分；部分进度需对照最新暂停记录。 |
| [Goal prompt v5](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/plans/gpt6-goal-prompt-v5-20260905.md>) | 目标的文件化设计输入，不取代本交接保存的原生文本。 |
| [GPT6 工程 review](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/reviews/gpt6-engineering-review-20260905.md>) | 首轮问题来源与建议；其中已修问题须查看后续记录。 |
| [P3 原生语义审阅](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/reviews/p3-native-semantic-review-20260908.md>) | 首轮医学分组消费缺陷；第二轮及最后修复以暂停文档补充。 |
| [恢复独立复核](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/reviews/p52-native-recovery-review-20260906.md>) | 恢复窗口的有界审阅结果，不等于完整产品恢复通过。 |
| [安装独立审计](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/reviews/p52-native-install-audit-20260906.md>) | 安装隔离／完整性问题与当时范围，后续补修另见 checkpoint。 |

### 3.3 正式旧基线、审计输入与封存历史

| 文档 | 阅读方式 |
|---|---|
| [v1.3 正式设计](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/docs/specs/competitive-intelligence-workflow-design-v1.3.md>) | 重基线后的正式历史基线；未被修改部分仍提供详细合同。 |
| [v1.3 路线图](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/plans/competitive-intelligence-workflow-roadmap-v1.3.md>) | M／R 阶段历史，不从头重新执行。 |
| [Codex 执行计划 v3](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/plans/codex_execution_ci-rebaseline-rebuild-v3.md>) | 受控重基线及 R2 历史工作。 |
| [v1.2 设计](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/docs/specs/competitive-intelligence-workflow-design-v1.2.md>) | 更早完整规格，包含已被排除的输出／监测等历史要求。 |
| [最早重构任务 PRD](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/.trellis/tasks/08-10-ci-workflow-rebuild/prd.md>) | 2026-08-10、75 任务与四格式阶段的历史入口，不是当前范围。 |
| [ZCode 工程审计](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/reviews/zcode_ci_engineering_audit_20260902.md>) | 问题与证据输入，不是无需核验的指令。 |
| [ZCode 路线图](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/plans/zcode_revised_roadmap_20260902.md>)／[执行计划 v2](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/plans/zcode_execution_plan_v2_20260902.md>) | 保留原件。旧 chmod、积压提交、表格导出等建议不得直接执行。 |
| [ZCode 意见处置](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/reviews/zcode_disposition_ci-rebaseline-rebuild_20260904.md>) | 查采纳、调整与不采纳理由。 |
| [HTML-only 决策 ADR 0013](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/docs/decisions/0013-site-first-v1-delivery-scope.md>) | 首版范围依据；涉及更晚用户变更时，再对照当前 Goal 与设计。 |
| [9 月 2 日原暂停现场](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/.trellis/tasks/09-02-phase-10-task-106-rc-freeze/PAUSE_HANDOFF_20260902_114643.md>) | 当时 Task 10.6A、worker_01 PENDING 和旧脏树背景。 |
| [9 月 5 日 GPT6 历史总交接](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/.trellis/tasks/09-02-phase-10-task-106-rc-freeze/PAUSE_HANDOFF_20260905_GPT6.md>) | Phase 0–10、重基线和 R2 历史的详细索引。 |
| [Task 10.6 PRD](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/.trellis/tasks/09-02-phase-10-task-106-rc-freeze/prd.md>)／[design](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/.trellis/tasks/09-02-phase-10-task-106-rc-freeze/design.md>)／[implement](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/.trellis/tasks/09-02-phase-10-task-106-rc-freeze/implement.md>) | 原四阶段冻结框架仍可用于最终源闭合；不是现在直接跳入冻结的许可。 |
| [R2.2 闭包完成检查点](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/.trellis/tasks/archive/2026-09/09-05-r22-universe-closure-runtime/checkpoint_20260905_r22_complete.md>) | 有界闭包运行合同历史，不代表所有真实适应症均闭包。 |
| [R2.3 Publication 完成检查点](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/.trellis/tasks/archive/2026-09/09-05-r23-publication-manual-product-gate/checkpoint_20260905_r23_complete.md>) | 补件状态机历史，不代表所有出版物获取与 OCR 实际完成。 |
| [R2.4 当前任务](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/.trellis/tasks/09-05-r24-gatespec-blocker-closure/prd.md>)／[R2.5 药智任务](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/.trellis/tasks/09-06-r25-yaozh-browser-adapter/prd.md>) | 具体来源／门控工作背景，以后续修复更新解释。 |

全局方法学文件为 [/Users/smkzw/.codex/AGENTS.md](/Users/smkzw/.codex/AGENTS.md)，项目覆盖层为 [AGENTS.md](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/AGENTS.md>)。恢复时重读实际版本，不恢复过时的路由表。

### 3.4 已发现的导航／元数据漂移

- 根 README 仍描述 v1.2、四种输出和早期阶段，不能用它判断当前产品范围。
- 项目 AGENTS 的产品版本说明仍指向 v1.3；方法学可用，但该版本提示不代表 v1.4／当前 Goal 无效。
- 累计 checkpoint 是逆序追加，存在旧“仍运行”“未设置 Goal”。顶部明确暂停以及原生 Goal 优先。
- v5 部分 P3 进度仅到第一轮审阅，不含最后域碰撞／纵向修复。
- B page catalog 仍有历史安全事件频率／差值选择等规则，需要与中性、不截断及当前语义合同核对；本次只记漂移风险，不把尚未完整追踪的条款一概宣布为线上缺陷。
- 本次只新增交接入口，不批量改写这些历史文档。接手恢复后集中修订一个权威索引和必要状态头即可。

## 4. 需求演变：哪些仍有效，哪些已被替换

| 主题 | 早期／第三方材料 | 当前有效要求 |
|---|---|---|
| 输出格式 | HTML + PDF／HTML-PPT／PPTX，formats=4 | 首版只交付 HTML，formats=1；非 HTML 输出代码留开发仓，不入安装包。PDF 论文输入解析不等于 PDF 输出。 |
| 报告形态 | 三报告实现不充分，容易共用一个仪表盘换色 | A/B/C 三个完全独立多页门户，无融合首页。 |
| 视觉密度 | 容易以拥挤字段、固定模板理解高密度 | 深、细、全、无冗余；不缩字号，不堆空字段，不用 Top-N 冒充完整。 |
| 多宿主 | 曾讨论是否延后分发 | Codex／Hermes／OMP 真宿主、fresh-install 与核心合同一致性保留；其他 Agent 按能力合同兼容，不空口保证。 |
| 编排框架 | Graph engineering／LangGraph 讨论 | 应用自有版本化类型图；不强制依赖 LangGraph。 |
| 入口 | 手工准备材料／工程操作偏多 | 一个公开 Skill；默认一句话，另有严格 research-package 高级模式。 |
| 提问方式 | 开放式多轮讨论 | 所有实质问题用原生 Ask 选择题，避免要求用户手敲；无必要不反复询问。 |
| 药智凭据 | 旧交接曾提本地环境变量存账号／token | 仅用户自行登录浏览器；不收集、不写入提示词、文件、日志、回执、包、快照的凭据／Cookie／token。 |
| 药智权限 | 企业来源可能被误作唯一依据 | 可选，项目问一次；只发现线索／交叉核验，不能单独证明关键数值／监管／科学结论。 |
| 药智有效期 | 旧已登录回执可能长期有效 | 用户裁决：同一运行短期复用，访问失败立即重检；五分钟是当前实现默认，不是用户指定的医学／产品常数。 |
| 数据新鲜度 | 缓存可能被当作最新资料 | 用户裁决：论文有效结果可复用；动态状态每次核查；缓存只加速，识别更正／撤稿／新发表。 |
| 历史截止 | 有可能用现页按日期过滤 | 用户裁决：还原当时公开可知内容和当时状态，不能事后倒填。 |
| 刷新／监测 | 定时监测与增量任务 | 全部人工触发；触发后自动刷新、差异识别、重建；不做定时监测。 |
| 表格导出 | ZCode 曾建议 CSV／XLSX | 明确不提供文件导出；完整原位折叠 HTML 表格仍必须有。 |
| 排名／图形 | 雷达、成熟度、综合分数等可选想法 | 不提供雷达／证据成熟度画像；默认不排名、不综合疗效安全分数、不做 Meta/NMA。 |
| Publication | 可能要求齐全但无失败路线 | 必需论文分类＋一次性补件门；无法获得不反复问，按核心可回答程度限制交付或证据不足页。 |
| 跨试验比较 | 字符串精确匹配或通用近窗口 | 医学语义完整单元＋确定性硬边界＋独立复核；未知≠等价，48/50 周不是所有终点通用 ±2 周。 |
| 真实验收 | 先跑通，或让同事试用 | 八适应症各 A/B/C；执行与独立复核由模型完成，主线程最终验收，不让用户／同事承担测试。 |
| RC 前分发 | 可能先向同事正式发包 | 首版正式同事分发不在 RC 前；内部隔离真实宿主验证仍要做。 |
| 脏树处理 | 依猜测把历史积压分阶段提交 | 保全脏树、清单、备份；验证后明确 release source-set，不猜历史提交，不 git add .。 |
| 旧根保护 | ZCode 建议先 chmod -R a-w | 当前要求零接触：不读、不写、不盘点、不 chmod，不做前置删除。 |
| 旧根退役 | 2 项目或 2 周 burn-in | 至少 3 真实项目覆盖 A/B/C，刷新／历史差异／三宿主／恢复／回滚过门，严重缺陷清零，再获用户明确删除批准。 |
| 工程执行机制 | 曾要求外部执行／会商与 120min 静默等候 | 本次接管阶段用户明确由主线程或原生 SubAgent，不用旧 runner。产品独立上下文要求不撤销。 |
| 连续实施 | 按 Goal 不形成无谓阶段暂停 | 继续授权下持续推进；最新“无损暂停”覆盖更早持续推进要求。今天交接不代表继续授权。 |
| 清理磁盘 | 用户要求定期清理无用材料 | 仅精确、无引用、可再生且未被任务占用的缓存；不删失败反例、原始证据、会话库、封存验收或恢复备份。 |

## 5. 产品合同：接手不能丢失的临床与呈现细节

### 5.1 三类报告不是一个模板的三种标题

**A：适应症竞品全景台。** 面向全部创新竞品宇宙、机制／靶点、模态、开发阶段、中国与全球状态、试验组合、监管与企业关系。预期用管线全景、关系图、阶段矩阵、地域时间线和有临床前提的疗效／安全图形。不能默认只展示明星产品或用固定数量结束研究。

**B：临床结果证据室。** 重点是疗效、安全性、基线、亚组、长期暴露与试验处置。默认输出事实汇总和中性差异，不给竞品总排名／研发建议。三种版本化气泡预设是：疗效信号 × 总体安全性（治疗组样本量或暴露量）；疗效信号 × 严重风险（有效分析集规模）；获益持续性 × 停药风险（长期暴露量）。只有完整语义基本可比才同图，原值、方向、时间、分母必须保留。

**C：试验设计图谱。** 重点是研究架构、人群、完整入排、终点定义、实际时间点／访视、治疗期、估计目标、样本量与统计设计。登记、历史版本、附件、公开 protocol／SAP 是主要设计事实来源，不应用结果论文替代所有设计信息。可总结设计模式和多条候选路径，不能仅凭适应症生成唯一最佳方案。

三类都要中文原生、独立导航、多页、图文结合；叙事／方法／限制不要机械制图。每个结构化域采用合适图形＋默认折叠完整表，不能空坐标轴、零值占位伪装有证据。数据分页／滚动是可用性处理，前提是全量可达且图表／表格／筛选事实集合一致。

### 5.2 来源、时间与科学权威

应区分来源家族、具体来源实例、来源路线、原始文件、派生文本、定位片段和事实。URL 存在不等于内容支持结论；摘要声明存在不等于原始外部字节已核验。

全球／中国必查路线和声明域政策共同约束权威。商业数据库只能发挥其获准作用。数字／监管状态／临床结论需可追溯的原始或权威来源。不同来源冲突必须记录和裁决，不能静默挑一个更符合预期的值。

公开时间、生效时间、首次公开状态、获取时间和报告截止分别建模。日精度不能被伪装成精确零点；历史截止不允许倒填事后披露信息。已发表论文既有结果可以继续有效，但必须处理撤稿、更正和新证据；动态管线／监管状态要实际重新核查。

### 5.3 完整性与缺失

首次报告要运行全球／中国必查、别名、靶点、公司和试验反向扩展，再由独立干净上下文查漏。189 个登记记录不是 189 个竞品，更不是闭包证明。固定 Top-N、达到某个数量或抓到热门产品都不能替代完整性。

关键模块缺失或异常零值要有两轮不同策略恢复；网络、权限、解析、分页截断必须区别于真实无数据。可选字段可以省略，核心仍可回答时明确限制；核心不能回答则只交付简洁证据不足页。该页不是完整报告矩阵的 accepted 项。

### 5.4 Publication 与用户补件

必需：主要结果、延长期主要结果、关键安全／长期暴露论文。默认排除普通综述、一般 ad hoc 或无关探索性分析；不能仅按标题关键词决定所有情况，要规则、模型和独立复核合用。

必需文件不能下载时，列 Markdown 补件清单、原文链接、唯一收件目录，仅暂停受影响报告。收到文件后校验类型、DOI／登记身份、字节摘要和冲突，先记录原名与新名，再原地规范重命名且不改字节。重名、错文件、扫描 PDF、登记号不一致均有负向场景。

用户同快照一次确认无法获取后，不再循环询问。扫描 PDF 不能通过编造文本绕过；OCR 如实际需要，要走当前获准工作负载门，不能在交接期间启动模型。

### 5.5 医学语义比较

人群／疾病严重度／背景治疗、治疗方案、终点或事件、量表方向、实际时间窗、估计目标、分母、分析集、统计形式、伴发事件等构成整体。字符串相同不是同义；未知字段相同不是已证明相容。

模型可以提出语义归并，但不能填造缺失定义，不能绕过尺度、方向、分母、分析集等硬冲突。近似时间必须有适用范围和医学理由，48/50 周不是通用阈值。旧研究未报告现代 estimand 也不应被强迫补造；可留在明确限制的描述性相邻图表，不能丢事实或伪装比较证据。

提案身份和来源声明摘要只是候选完整性机制，不是实际独立复核者签发 accepted 的替代。最终复核还需真实独立上下文、实际来源与产物身份绑定。

## 6. 历史规划与里程碑：避免重复建设

### 6.1 2026-08-10 原 Phase 0–10

以下是历史实现主题，不是按当前合同重新验收通过的清单：

| 历史阶段 | 已有实现／资产主题 | 当前应如何使用 |
|---|---|---|
| Phase 0–1 | 仓库、项目合同、SQLite、事件、快照、入口与预检 | 复用并修共享边界，不另起一套项目数据库。 |
| Phase 2 | 本体、实体、全球／中国来源、摄取、定位、事实／结论 | 与新的来源实例、时间和原始字节链对齐。 |
| Phase 3 | 科学门、缺失恢复、隔离 QC、no-draft | 核实真正进入公共流程，不仅 helper 测试。 |
| Phase 4 | HTML 壳、筛选、URL 状态、图表／表格、抽屉、浏览器工具 | 共用基础但保持三套信息架构。 |
| Phase 5 | A 报告 | 旧单对／Top-N／矩阵等问题部分已改，不能整体照搬。 |
| Phase 6 | B 疗效、安全、纵向、基线与处置 | 当前 P3 主战场，语义与页面消费重构。 |
| Phase 7 | C 设计、入排和综合 | 有代码，仍需按完整 C 合同实际验收。 |
| Phase 8 | PDF、HTML-PPT、PPTX | 开发仓保留兼容，首版输出／安装包排除。不要续跑旧格式主线。 |
| Phase 9 | 刷新、监测、宿主、包 | 手动刷新与宿主保留；定时监测移出范围。 |
| Phase 10.1–10.3 | 历史矩阵、重建／宿主演练 | 封存历史，不重复包装成当前 24 门户验收。 |
| Phase 10.4–10.5 | 迁移／切换工具与证据 | 已封存；不得改历史接受记录。 |
| Phase 10.6 | A–D 源闭合、候选包、恢复、冻结框架 | 尚未真正冻结；新目标先补实现与真实验收。 |
| Phase 10.7–10.9 | 旧根干运行、退役与终验收 | 前置条件和再次删除授权未满足，不启动。 |

### 6.2 9 月 2–5 日重基线与重构

ZCode 在当时快照报告了 77 个 mypy 错误、3 个 Ruff 问题以及大规模未提交积压。它揭示了重要问题：局部文件通过曾被表述成全局通过。那些数字是当时状态，**不是今天仍剩 77／3 个错误**。

随后 R0／M0 做受控重基线，R1／M1 做 v1.3 与正式计划。相关历史检查点认可的是当时明确范围的完成，不是全产品完成。

历史 M1 备份记录位置：/Users/smkzw/Documents/AI Products/.ci-rebaseline-backups/ci-workflow-m1-20260904T082040Z。记录为 18,878 节点、5,888,661,178 字节、当时零可写文件，摘要 1e7e3aeeb031d0391a7fb333fb9825869047835cc54aff46b268fee7575b9d22。**今天未重新验证该备份；它不包含后续全部工作，不能当当前代码的完整恢复包。**

R2.1 建自动研究工作项／包入口；R2.2 建闭包运行合同；R2.3 建 Publication 补件产品门；R2.4 深化 GateSpec／缺失与恢复；R2.5 建药智权限／会话观察合同。之后 GPT6 接管 review 形成 v1.4 与 v5，并在来源、验收、安装、A 图表和 B 语义上持续补修。

### 6.3 新旧阶段映射

v3 的 R 阶段、v5 的 P 阶段以及缺陷等级 P0/P1/P2/P3 是不同坐标系，不要混用。

| 新计划阶段 | 主体内容 | 当前情况 |
|---|---|---|
| P0 | 完整 review、设计、计划与目标形成 | 文档和 Goal 已存在；状态头需精简校正，不要重复启动整套访谈。 |
| P1 | 共享来源／合同／交付接受边界 | 多项确定性漏洞已修并有有界回归，整套最终验收未完成。 |
| P2 | 来源获取、时间、闭包、Publication、药智 | CT.gov 原始链有真实取数；其余真实来源与历史、OCR／药智端到端仍有缺口。 |
| P3 | 医学语义完整建模与实际分组消费 | 当前暂停点；第二轮严重缺陷已修，最后独立复验／整合门待重跑；完整临床单元仍未收口。 |
| P4 | A/B/C 独立门户及所有页视觉／交互 | A 及 B 有实质改进，但 A 矩阵／行级来源与 B/C 全覆盖仍未完成。 |
| P5 | HTML-only 安装、三宿主、刷新／恢复 | 安装隔离和恢复有界合同进展较大；最终新包与三真宿主、完整实际恢复未完成。 |
| P6 | 八适应症 × 三报告真实矩阵 | 尚无整个新矩阵完成的验收证明，不能以旧生成物填表算通过。 |
| P7 | 唯一 RC source-set／commit／包与最终绑定 | 未完成，不具备冻结资格。旧根退役另受用户再次授权约束。 |

## 7. 系统如何工作：前后端与内部 Skills 的组件地图

### 7.1 实际技术形态

这是 **Python 研究／证据／编排引擎 + SQLite／内容寻址存储 + Jinja 静态多页 HTML + 本地 JS／ECharts** 的组合，不是必须长期运行一个 React 前后端服务的业务网站。

公共 CLI 为 ci-workflow；项目依赖与锁定环境在 [pyproject.toml](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/pyproject.toml>) 和 [uv.lock](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/uv.lock>)。Python 版本边界为 >=3.12,<3.14。基础选择包括 Pydantic、Jinja、Playwright、PDF 输入解析工具等；版本以锁文件为准，不因交接擅自升级。

HTML 是用户最终门户；项目内部的数据库、JSON、回执和工程诊断不是面向医学用户的首屏内容。离线资产和相对链接需要同时支持实际使用方式；存在文件不代表页面可读或已接受。

逻辑主链：

一句话／research-package → 项目合同与预检 → 来源规划／获取 → 原始证据与派生文本 → 实体／事实 → 闭包／缺失恢复／Publication → 独立科学复核 → A/B/C 专属分析 → 静态门户 → 浏览器与交付接受 → 不可变快照／latest → 用户再次手动刷新及事实差异。

每一步要有类型化输入输出、完成／失败状态、恢复路线、幂等键和证据回执。用户不负责手工拼这些步骤。

### 7.2 组件职责与接手入口

以下路径除注明外均相对英文根目录；不是要求现在全部重写。

| 层 | 主要路径 | 含义与注意点 |
|---|---|---|
| 公开产品入口 | [公开 Skill](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/skills/competitive-intelligence-workflow/SKILL.md>)；src/ci_workflow/cli.py | 入口说明与命令；安装后只公开一个 Skill。Skill 文件存在不证明入口全自动能力已完成。 |
| 入口／项目 | application/intake.py、project_service.py、autonomous_research.py、research_package_submission.py、capability_preflight.py | 区分自然语言组织研究与高级包；真实宿主独立上下文能力不能用静态假回执代替。 |
| 总装配 | [run_service.py](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/application/run_service.py>) | 图节点 handler 与 A/B/C 生成、恢复、回执收集的交汇点，改合同须查所有消费者。 |
| 类型化控制图 | graph/types.py、typed_skills.py、executor.py、reducer.py、state.py、registry.py、guards.py、recovery.py、impact.py、transitions.py | 应用自有状态与控制图；重试、恢复、影响传播必须与合同一致。 |
| 图定义 | graph/definitions/new_report.py、correction.py、refresh.py、monitoring.py | 首次／纠正／手动刷新有效；旧 monitoring 代码不因此进入首版包或产品。 |
| 核心领域 | domain/ 下合同、实体、证据、事实、claims、research_package、publication、public_provenance 等 | 将身份、科学事实和展示分开；不能在 renderer 用私有字段重新裁决科学事实。 |
| 来源规划 | sources/planner.py、policy.py、receipts.py、retries.py；connectors/ | 全球／中国与声明域；区分来源家族与来源实例，明确失败类型。 |
| 实际 CT.gov | [ctgov_fetch.py](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/sources/connectors/ctgov_fetch.py>) | 分页、版本一致性、原始 CAS、严格 JSON 与逐登记记录派生；不能把当前数据当历史全貌。 |
| 摄取／研究 | application/source_research_service.py、fresh_research_ingestion.py、fresh_research_primitives.py、fresh_b_research_package.py、fresh_c_research_package.py | 包、来源、日期与实际载荷的绑定；源和重开消费链应共用校验。 |
| Publication／定位 | ingestion/classifier.py、fragmenter.py、identity.py、locators.py、manual_inbox.py、publication_gate.py | 正文派生、证据定位、补件校验与状态机，不应以解析成功冒充正确论文。 |
| 科学门／缺失 | gates/evaluator.py、models.py、coverage.py、exhaustion.py、blocker_audit.py | 计数、arm 覆盖、异常零值和恢复策略分别建模。 |
| 复核签发 | qc/scientific.py、review_receipt.py；application/review_issuer.py、scientific_review_transition.py | 实际独立上下文与源码／事实／产物绑定；不要另造可手填 reviewer 字符串即 accepted 的旁路。 |
| 接受／交付查询 | application/visual_acceptance.py、acceptance_boundary.py、delivered_artifacts.py、latest_delivery.py | 首页存在不等于交付；必须走锁定快照、合同和接受事件链。 |
| A 领域与渲染 | reports/a/；renderers/portal/report_a.py、templates/a/、report-a 资产 | 管线／状态／试验与全部观察。还要消除旧矩阵／产品档案的单对选择。 |
| B 领域与渲染 | reports/b/semantic_contract.py、semantic_grouping.py、efficacy.py、safety.py、baseline*、disposition*；renderers/portal/report_b.py | 当前主工作区。完整输入先分组、页面只投影，不能切片后改变科学分组。 |
| C 领域与渲染 | reports/c/design.py、eligibility_source.py、synthesis.py、contracts.py、pages.py；renderers/portal/report_c.py | 设计事实、人群、完整标准及模式分析；旧有模板不是新 C 完整验收。 |
| 共用视图 | reports/common/ 的 chart_specs、evidence_view、coverage、view_state、study_roles、page_registry 与 page catalogs | 共用事实与呈现合同，不复用同一个总仪表盘代替三产品。 |
| 浏览器前端 | assets/portal/ 与 renderers/portal/assets/；filters、URL state、global search、page shell、evidence drawer | 过滤／图表／表格／抽屉必须同事实 ID；双份共享 JS 和 manifest 必须同步。 |
| 持久化 | storage/sqlite.py、migrations.py、content_store.py、event_store.py、checkpoint_store.py、project_contract_store.py、manifest_store.py、snapshot_store.py、render_transaction.py、source_derivation.py | SQLite 状态／事件与 CAS 原始字节、锁定快照；旧记录不回写伪装升级。 |
| 刷新／恢复 | application/refresh_service.py、correction_service.py、terminal_recovery.py；graph/recovery.py | 首次／刷新／恢复应共用科学接受边界，不能仅恢复“命令继续执行”。 |
| 宿主／安装 | hosts/base.py、codex.py、hermes.py、omp.py、receipt.py；application/fresh_install.py、host_smoke_runner.py、host_smoke_scenario.py | 安装隔离、实际宿主能力、同合同与恢复身份。替身 smoke 不是真宿主验证。 |
| 发布工具 | tools/build_bundle.py、bundle_contract.py、install_bundle.py、verify_bundle.py、build_recovery_package.py、verify_release_receipts.py | 包、source-set、恢复／接受证据绑定；构建成功不能独立宣布发布。 |
| 开发门 | [tools/gate.sh](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/tools/gate.sh>) | 精确范围 quality-only，不含全部 integration／browser／真实矩阵。 |

内部 Skill catalog 已有研究、抽取、身份冲突、来源、科学 QC、报告、视觉等分工；监测相关历史 Skill 必须保持首版排除。内部拆分可独立测试／替换，但“目录中有 SKILL.md”不等于宿主自动按合同调度、失败恢复和复核能力已落实。

实际内部目录为 skills/_internal/，不是 skills/internal/。现有 16 个内部入口可按下列职责导航；内容是需要对照新合同核验的实现材料，不自动获得规范优先权：

| 内部 Skill 名称 | 目标职责／接手关注点 |
|---|---|
| intake-preflight | 需求入口、宿主能力与项目合同；实质缺项才 Ask，真实独立上下文不可静默降级。 |
| ontology-universe | 适应症消歧、本体、创新疗法与完整候选宇宙。 |
| source-routing | 全球／中国／商业路线与声明域来源权威。 |
| ingestion-identity | 来源获取／摄取、文档及版本身份，连接原始字节证据链。 |
| extraction-normalization | 结构化抽取、字段标准化，不能补造源中没有的事实。 |
| identity-conflict | 产品／企业／试验等实体对齐和冲突裁决。 |
| coverage-gates | 闭包、覆盖、缺失恢复和阻断／限制交付判断。 |
| analysis-a／analysis-b／analysis-c | 三个各自独立的专属分析 Skill，不是同一模板的三个标志位。 |
| scientific-qc | 以独立输入上下文审查事实、来源、医学可比和完整性。 |
| visual-design-director | 面向具体报告数据规划信息结构与图形；不得改写事实来适配布局。 |
| render-deliver | 渲染、版本与交付边界；生成文件不直接等于 accepted。 |
| visual-package-qc | 实际视觉、交互和包质量检查，与科学 QC 分工但共同绑定产物。 |
| correction-refresh | 用户触发后的纠正／刷新、影响范围与版本差异。 |
| monitoring | 历史保留项，当前首版明确排除，不得因目录存在重新启用定时功能。 |

### 7.3 必须保持的身份关系

项目合同 → 本次研究运行 → 具体来源版本／原始字节 → 派生文本／定位 → 事实 ID → 科学候选分组 → 独立接受回执 → 门户字节 → 锁定快照 → latest 指针。

不能用以下东西相互替代：来源家族与实例、URL 与内容、文本摘要与 PDF 原始摘要、proposal 与 accepted、合成 reviewer 与真实上下文、首页与交付、安装包与已安装运行环境、可解压备份与已恢复项目、临床登记记录数与竞品数。

## 8. 已实现／已验证的进展及准确边界

### 8.1 共享合同、门控与安全

- Gate 的“独立有效事实数”和“必需 arm 全覆盖”已拆开，阻止跨 arm 重复借用同一事实满足全部覆盖。
- A/B/C Jinja 自动转义漏洞已补：原 .html.j2 命名没有被旧自动选择策略覆盖，三个 renderer 显式 autoescape。存在实际 Chromium 负向验证和门户回归，但不是全产品 XSS 安全审计。
- 站点清理采用先完整校验再删除，未知文件等失败不应半删旧站；**没有**证明所有磁盘 I/O 失败、断电与 kill 都具完整事务回滚。
- 商业来源 URL／声明域不能通过改 label 冒充官方来源。

### 8.2 来源、时间与原始证据链

- ResearchSource 实例与 SourceDefinition 家族分离；提交及重开校验 URL、标题、规范文本摘要、获取时间、角色／类型／出版信息，拒绝重复歧义。
- 闭包 review digest v2 绑定规范完整来源集合；旧 v1 历史可读，不自动补签接受。
- locator_detail 与结构化 EvidenceLocator 逐步取代仅可读字符串；同来源的定位改变要使相应身份发生变化。
- date-identity-v2 将公开／生效／首次公开状态、精度、时区与定位纳入来源版本；同内容但关键日期改变应成为新版本，CAS 可以复用字节。
- 日精度与 instant 区分；未提供的旧可选字段不强行序列化，避免破坏历史摘要。历史准入不把自然日当精确零点。
- SourceTextDerivation 绑定原始 SHA／字节数／媒体类型到规范文本 SHA、提取器与版本；PDF 文本层／UTF-8 派生可追溯，migration 0010 采用追加记录。不能要求 PDF 二进制 SHA 等于正文文本 SHA。
- 扫描 PDF OCR 实际链仍待，不得用假正文填补。
- CT.gov 实际获取器使用标准库，记录原始分页 CAS、游标、总量、平台版本；限流、拒绝、超时、坏 JSON、重复键、NaN、预算耗尽、截断不是无数据。
- ctgov-study-json-v1 从原始响应准确切出指定位置／NCT 的 JSON 对象，保留原数值 token；不是重新序列化后假称原始字节。
- **真实取数证据**：2026-09-06 PNH 检索 189 登记记录、2 页、5,682,837 字节，逐记录离线重开。精简索引为 [CT.gov 实际获取回执](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/reviews/ctgov-live-acquisition-20260906.json>)，原始 CAS 在 .artifacts/source-cas/ctgov-live-20260906。
- 上述真实取数不证明竞品全量闭包、历史状态重建、中国路线齐全或任何最终 A/B/C 报告接受。其他来源的动态核查、更正／撤稿以及跨来源历史还原仍需端到端完成。

### 8.3 药智

已实现项目访问选择和运行期登录观察分离；yaozh observe／check 消费本运行／宿主／回答摘要／开始时间，旧无 run 回执不沿用。同运行短期观察有五分钟实现默认，最新失败优先，失败立即要求重检。

尚缺已登录浏览器的实际访问适配、访问失败自动 observe、真实来源取回与交叉核验完整 smoke。可选跳过不应阻塞其他合法来源路线。任何 Agent 都不得为“测试便利”导出会话 Cookie／token。

### 8.4 交付、latest 与恢复

- delivered_artifacts 不再仅扫描 index；要求 accepted 链、锁定快照、项目合同、截止／时区、来源谱系、整站摘要和 delivery_ready 事件，拒绝符号链接等边界绕过。
- visual_acceptance 及公共 CLI 已从 B 泛化为 A/B/C，不应让 A/C 只有内部函数可接受。
- latest_delivery 按报告维护原子指针；子合同草稿期间旧 accepted 可读，历史重放不倒退；重试不得改写旧接受历史。
- format 节点 v1.3 明确 site_relative_path／manifest_relative_path，六类 handler 显式给出，恢复不能靠 artifact_id 猜路径或扫描全部历史 reports。
- 当前运行新建和复用产物都要验证整站／快照／项目合同。旧完成节点没有必要引用时明确 fail-closed，保留现场，不偷偷补历史。
- A 提交后恢复窗口有 committed-render-input-v1：绑定全部规范数据、合同、源码、资产和依赖；仅 resume 下验证 generated 清单与锁定快照后复用，不覆盖旧字节。
- **B/C 对应提交窗口尚未全部实现**。手动刷新入口到真实复核签发、差异、重建、恢复的整链也未完成。
- Erdos 最后有界独立复核为 42 项通过，解决该切片两个 P1 和遗漏 A 回归；它不等于 24 个项目或三宿主真实恢复接受。

### 8.5 A 门户与共享图形

- 疗效不再只显示百分比／每产品一对：纳入负值、真实零、非百分比、多剂量观察，按真实临床条件拆分。
- 安全性不按最高发生率挑时间窗；保留组别和观察窗。全展开超长页改为每页 60 观察、全部可遍历，不是 Top-N；这不是用户指定的临床阈值。
- 点击图形／逐项按钮按精确 row_id 下钻，修复点 12 周 2% 却弹出 52 周 80% 等错事实问题。
- 移除为防重叠而移动数据坐标的抖动，曾有移动 12 个百分点的反例。气泡面积改按 N 比例；视觉重叠仍需处理，但不许篡改数据坐标。
- 来源区／抽屉已显示校验后的真实安全外链、类型、日期；报告级来源明确标为报告级，不能说成每个产品专属引文。拒绝本机／私网公共链接。
- 尚缺 A 矩阵与部分产品档案旧单对逻辑的完整语义重构、行级／逐页筛选后的精确来源绑定、全页密度和可访问性终验。局部坐标／面积测试不是临床可比验收。

### 8.6 安装与宿主

- fresh_install 采用独立 uv 运行环境、清理宿主环境影响的启动路径和 -I/-B/-S bootstrap；导入前校验安装文件集合、lstat 类型、模式、缺失／额外／字节漂移。
- 同包重装也必须查实际安装字节，不能仅看旧收据。Sartre 补目录和入口权限／集合问题，主线程有新候选定向复验。
- 可移植的是安装归档，**不是已经安装的 venv 可任意搬动**；新目录应 fresh-install。首次安装可能需要网络，不承诺空气隔离。
- 构建后端为版本范围锁定，不是整个后端工具链的逐字节可重复构建保证。
- host_smoke_runner 区分新空目录和恢复已有项目；旁置包／catalog／项目／宿主身份先核验后派发。scenario／CLI 的 resume 路径和幂等已有修订。
- 历史包 338 文件／15 CLI 等数字只指当时候选，后续源码已变化。**当前最终包必须重建**。
- 真实宿主用例存在跳过记录；替身调用、适配合同通过不等于 Codex／Hermes／OMP 三个真实运行。
- 恢复归档摘要正确不等于隔离 restore → resume → refresh → rebuild 已跑通。

## 9. 精确暂停点：P3 医学语义与 B 实际 HTML

### 9.1 为什么这一块重要

此前有语义 helper、硬边界和报告组件，但实际 renderer 可能在不同页面自行 regroup，或通过旧字符串／时间桶逻辑绕过新规则。因此“领域单测通过”仍可能生成错误报告。P3 当前工作就是把整个观察池的科学分组真正接入所有相关页面。

主要代码：

- [semantic_grouping.py](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/reports/b/semantic_grouping.py>)
- [semantic_contract.py](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/reports/b/semantic_contract.py>)
- [report_b.py](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/renderers/portal/report_b.py>)
- [正式语义提案反例](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/tests/reports/b/test_semantic_grouping_proposals.py>)
- [实际浏览器消费测试](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/tests/browser/test_b_semantic_proposals.py>)

SemanticGroupingProposal 是 frozen、extra forbid 的 **proposal**：绑定观察对、摘要、兼容／时间声明、producer 与理由。它不是 accepted 回执；model_copy 也需重新校验，不能复制成伪接受状态。

语义摘要现在纳入投影事实、完整输入声明的 _source_binding 与 b-candidate-hard-axes-v2 政策版本。候选按稳定 row ID 排序，采用 complete-link，A–B 与 B–C 兼容不推出 A–C 兼容。完整输入先确定 scientific_group_id，页面只投影，不能按筛选子集重新决定科学分组。

### 9.2 第一轮独立审阅：四类 P1

Sagan 在干净上下文用反例确认：

1. 无模型提案时仍可绕过硬时间边界，例如旧 near-year 桶把不应等同的窗口合并。
2. 输入顺序和产品页切片会改变成员，AB／BC 关系在没有 AC 的情况下产生不稳定结果。
3. 来源定位从 page 1 改到 page 99 不会让原候选失效。
4. 基线、处置、矩阵等描述域忽略明确 veto。

主线程先补 RED，再修全部跨试验 hard guard、稳定 complete-link、完整声明／定位摘要、全站分组／页面投影；描述域显式否决必须拆开，未支持的正向归并拒绝，不假称已经具备科学支持。

首轮原反例保留于 tmp/semantic-independent-w1RHFS/test_independent.py。

### 9.3 第二轮审阅：两类 P1、一类 P2

| 问题 | 实际影响 | 当前修复 |
|---|---|---|
| 同 row ID 跨域被静默去重（P1） | 疗效 EASI=60 与安全 TEAE=2 同 ID 时，实际安全页可能显示 60；事实修改后页面也可能投影旧值。 | _project_record 带域；_dedupe_records 拒绝缺 ID／同 ID 不同域或摘要，只允许真正相同记录去重；逐页投影核验域和事实摘要。 |
| 全局单点组破坏同试验纵向（P1） | 12／24 周系列变成独立单点条形，丢失纵向含义。 | 从完整输入一次建立 product／trial／arm 的 within_trial_longitudinal 专用描述系列；纵向页使用它，保留真实时间与行。 |
| 跨域正向提案被两边静默忽略（P2） | overview／profile 分域后，提案两端不在同域，候选未被明确处理。 | 分域前拒绝跨域提案，不以静默降级伪装支持。 |

站点重置移到这些校验之后；新增“冲突输入拒绝后原站点字节不变”的测试。第二轮原反例、实际错误安全页截图保留于 tmp/semantic-rereview-a4bUhi/。

**状态：代码已修、有界测试已通过；最后独立复验未完成，不是已最终 accepted。**

接手还要挑战孤立／不存在观察引用、未支持域、重复投影、各真实页消费者等相邻场景。这里是待查清单，不是未经测试就认定它们都是现存缺陷。

### 9.4 尚未实现的完整 P3 目标

目前修补的是实际消费的完整性与硬边界，不是全部医学语义系统：

- 疾病／严重度／目标人群／背景治疗／治疗组／伴发事件等完整临床单元仍需贯通。
- 时间近似的来源、适用终点、临床场景和版本政策没有全部收口；旧固定 ±2 周不能当普遍医学政策。
- 未知、缺失与有证据支持的“不适用”需要类型化区分。
- 实际来源支持的 LLM 提案和真实独立复核签发链尚未接受。
- _source_binding 绑定“提供的声明”，不自动证明外部论文／PDF 原始字节真实一致。
- 现有 review_issuer／scientific_review_transition 要复用。部分回执机制偏 external_subprocess_session，需要适配真正原生独立上下文证据，而不是绕过它。
- 不得为了通过新合同向真实 fixture 填造 estimand、分析集、疾病严重度等参数。

## 10. 最后测试结果：哪些可以说通过，哪些不能

今天没有运行测试；本节来自暂停点与历史回执。

| 时间／范围 | 结果 | 允许的结论 |
|---|---|---|
| 第二轮正式反例初跑 | 5 个新增反例失败、其余 28 通过 | 有明确 RED，不是先实现后补“总能过”的测试。 |
| 第二轮修复后 B 领域＋新浏览器 | 277 passed，10.44 秒 | 当时该组合通过；早于随后新增旧站点保全测试。 |
| 随后正式 20 项＋审阅原 8 项 | 28 passed，3.64 秒 | 包含旧站点保全及真实 HTML 的有界修复证明。 |
| 两个科学源码与相关静态检查 | strict-mypy／Ruff 通过 | 只覆盖注明文件；不是整库所有类型和浏览器。 |
| 修订前完整 quality-only gate | 活跃 986、保留兼容 20、分层 7；Ruff 与 mypy 217 源通过 | 早于第二轮最新修复，不能继承给最终源码。 |
| 修订前完整 integration | 723 passed，196.83 秒 | 同上，不能继承。 |
| 较早共享资产＋B 相邻浏览器 | 101 passed，137.82 秒 | 对应当时资源与源码，不是 24 报告所有页。 |
| 最后一轮 gate，exec9693 | Ruff 全 src/tests/tools 与 strict no-incremental mypy src/tools 217 源完成；单元约 58% 时被暂停，exit143 | **中断未完成**，不是 gate 通过，也不据此认定产品代码失败。 |
| 最后一轮 integration＋B 相邻浏览器，exec59392 | 164 passed 后 KeyboardInterrupt，exit2，31.74 秒 | **整套中断未完成**；中断栈 source_research_service.py:418 不是自动缺陷归因。 |
| Sagan 最后一次复验 | 仅静态读取／起始 SHA；没有反例重跑、没有结束 SHA、没有 accepted | 独立复验未完成。 |

9 月 8 日停止的是已确认属于本任务的进程；当时确认相关 PID 已不存在。今天没有全机进程清查；不要拿文档中的旧 PID 去 kill，PID 可能被复用。

### 10.1 浏览器证据的范围

共享 charts.js 修复了类别隐藏、中文换行、局部水平滚动以及 WebKit 容器方向键滚动；report-b.css 的强制宽度覆盖被移除。键盘处理只作用于滚动容器自身焦点，不劫持子控件／组合键。

早前 320px 双引擎截图在 output/playwright/ci-b-semantic-proposals-20260908/，主线程查看过 Chromium。它们早于最后全部科学源码修复，不是当前最终全页视觉接受。

新合同最终要求 **Chromium 与 WebKit × 1440×900、1024×1366、390×844、320×568**，覆盖全部物理页面和交互。局部测试用过 1440／768／390／320 宽及 900 高等参数，不能直接等同这个最终矩阵。

### 10.2 开发门真实覆盖

tools/gate.sh 当前默认包括：

- Ruff：src、tests、tools。
- mypy：src、tools，strict、no-incremental，准确声明范围。
- tests/unit 与 tests/contract 的活跃层。
- 同两个目录内保留格式轨的有界兼容 smoke。
- 分层合同检查。
- 禁旧路径静态检查。

它**不包含**全量 integration、全部 reports、浏览器、所有保留 PDF／PPT 轨、真实临床来源矩阵、真实宿主与完整恢复。

--require-clean 只增加工作树干净检查，不代表可发布；当前脏树不能靠删除文件“满足”它。--source-set 是历史基线漂移诊断，不是最终 RC 源闭合证明。不要缩小检查范围或取消失败用例以制造全绿。

## 11. 当前现场身份与保全材料

### 11.1 今天重新确认的身份

HEAD：bb27ec9d750cf02fb64da5dfe665b2f4b262922d。

下列八项 2026-09-11 重新计算，与 9 月 8 日暂停记录一致：

~~~text
263d15ccfec23a598246cf0f4949ff165598e350a7db700293001c8a727ed54e  src/ci_workflow/reports/b/semantic_grouping.py
702e8ac3b9829cc39e98df6d35c59142b13eb2e44ccde894b81ef9d1c704d07c  src/ci_workflow/renderers/portal/report_b.py
b8a1b54b3dba4bcca6be3dbe45ca4a6761b956317cf5c532ba03c084cc19e5d3  src/ci_workflow/renderers/portal/assets/report-b.css
664c93f22eb0ae2d043920c8f1e288c59871c41a3f149ccd81f5b55fa03608ee  assets/portal/charts.js
664c93f22eb0ae2d043920c8f1e288c59871c41a3f149ccd81f5b55fa03608ee  src/ci_workflow/renderers/portal/assets/charts.js
f0694332a889d648ae660fb1391cf4323918497257793540871b0014d7a40527  assets/portal/manifest.json
7750244980c246cb4602c556dceb5f13de93523ec5b6be15e96205a72e561b56  tests/reports/b/test_semantic_grouping_proposals.py
cf09180c9eca2d9f354db76cea6bf8fb7e7dca6f7820d9f588e07b6cf2c78d20  tests/browser/test_b_semantic_proposals.py
~~~

这证明八项一致，不证明全仓所有文件未被其他 Agent 修改。

9 月 8 日保存的 git 状态有 1,215 条 normal 模式条目；[状态索引](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/context/PAUSE_20260908_093147_git-status.txt>) 是目录折叠的状态，不是文件备份。今天交接初稿阶段检查为 1,218 条 normal 状态项，其中 152 个跟踪状态项（151 个其他变更、1 个删除），1,066 个未跟踪条目／目录。后续交接入口写入还会改变数量。**这些数字不应当成全文件个数或用户改动的完整分类。**

本轮没有提交产品代码；此 HEAD 只是最后提交，不包含全部实际产品 WIP，因此不能用 git show HEAD 代替当前现场。

### 11.2 必须保留的证据

- 最新暂停文档、状态索引和累计检查点。
- 当前未提交源／测试／资产及其关联合同。
- tmp/semantic-independent-w1RHFS/、tmp/semantic-rereview-a4bUhi/；tmp/semantic-final-oSL4Xo/ 是未完成审阅现场，不得冒充 review 结果。
- output/playwright/ci-b-semantic-proposals-20260908/ 的截图及其他关联原始失败证据。
- CT.gov 原始 CAS 和精简索引；不能把真实抓取材料当可随便重建的缓存。
- 恢复审阅反例、包源清单、安装完整性回执与早前接受记录。
- 封存的 Task 10.5 及更早检查点，不回写以适配新代码。
- 原生 review 句柄仅作追溯：Sagan 01a07e96-8cbf-77e1-a1bb-28417f5f3ce5 已停止；其他 Agent 可能无法访问。没有可用句柄时以新干净上下文复核，不假装续用了旧独立身份。

## 12. 停滞分析：直接原因、工程原因与责任

### 12.1 直接停止原因

最后停下是用户明确“无损暂停”，并非系统自判目标已完成或无法推进。测试被安全中断，证据保留。今天用户决定交由另一个 Agent 继续，因此交接整理优先。

没有现有证据证明这次暂停由 CLI 更新、剩余额度、磁盘不足、账号不可用或必须等待用户回答的新科学问题造成。不要把历史环境事件猜成当前 blocker。

### 12.2 为什么长期投入后仍未收口

**一、完成定义早期偏向过程，偏离产品终点。** 有大量 graph／schema／receipt／test，却没有同步证明完整竞品宇宙、所有报告页实际临床含义、三宿主和新 24 门户。模型、脚本与页面分别“过了”不表示全链已过。

**二、规则与实际展示之间存在多次裁决。** 领域层分组后，renderer 又按页面、产品、时间桶或默认配对重新处理，导致科学规则旁路。最新 P3 的事实串域、纵向系列丢失即来源于这种接口不闭合。

**三、共享身份与恢复边界重复实现。** 来源实例／家族、事实 ID、来源版本、候选组、快照、运行输出、新建／复用产物曾各走不同路径。补一条路径后漏掉 A 或跨域消费者，继而出现整合回归。

**四、规范多次变更而导航没有收敛。** 四格式改 HTML-only、定时改手动、旧包／分发计划改 24 真报告与更严格来源科学门，方向合理，但旧 README、Skill、设计标题、计划进度和检查点仍并存。新 Agent 很容易误续过时阶段。

**五、局部“通过”的表述历史上超出检查范围。** 最早类型检查误报与后续 helper 通过但真实页面出错，都说明测试必须声明准确入口和源码身份。主线程对此负有整合与报告责任，不能把问题归咎于审阅者或用户。

**六、真实研究链比工程证明链推进更慢。** 当前已有 CT.gov 真取数，但中国来源、历史版本、Publication／扫描文档、实际药智，以及实际独立科学签发并未同步形成所有适应症完整端到端证据。合成用例再多也不能补这个缺口。

**七、大规模脏树与历史产物提高恢复成本。** 工作仍主要在未提交现场，最终 source-set 没有形成。大量逆序记录容易让人重跑或遗漏；反复在变化源码上运行宽回归又不能产生统一最终身份。

这些原因是现有材料支持的工程分析，不是逐个组件新一轮全仓审计的结论。独立审阅发现真实严重错误是有价值的；问题在于更早没有把强反例和实际页面消费纳入同一验收单位，而不是“审阅太多所以应该取消”。

### 12.3 不建议采用的“加速”方式

- 不建议全部推倒，改用 LangGraph 或新前端框架期待自动解决科学接口。
- 不建议继续堆文档、再加一套 reviewer 字符串／事件库／图执行器。
- 不建议先生成 24 个外观模板再补证据，或向真实 fixture 填造缺字段。
- 不建议放宽 unknown、覆盖、旧引用恢复、包完整性等门来通过旧测试。
- 不建议把证据不足页、历史报告、工程 smoke 或静态替身计算成新矩阵 accepted。
- 不建议在这次交接中继续做代码收尾、清缓存、创建 RC commit 或启动代理。

## 13. 后续解决方案与建议取舍

### 13.1 应保留的技术路线

保留类型化控制图、Pydantic 合同、SQLite／CAS、Jinja 三套门户、共享浏览器组件、现有 package 与恢复基础。它们已有大量可复用的正确工作；当前没有证明必须更换框架。

以“同一事实集合、一次科学裁决、所有页面只消费”为主线，从超大 renderer 逐步移出医学选择逻辑。先以已发现反例保护边界，再移动职责，避免为了代码好看而引入一次无可验证的大重写。

### 13.2 应优先补齐的功能／质量能力（既定范围内）

1. **单一当前状态／权威索引**：只维护一个可读进度表，标已实现、待接受、未实现；历史原件保留，旧标题加导航即可。
2. **完整医学观察合同与未知状态**：字段不是填表任务，要来源绑定、明确 unknown／not-applicable／incompatible，并能保留描述性事实。
3. **统一事实视图模型**：A/B/C 图表、表格、筛选、下钻、来源使用同一事实 ID；在生成前检查全域 ID 冲突与漂移。
4. **实际独立复核适配**：支持宿主真正可证明的独立上下文，把原始输入与冻结产物交给复核，接受链不依赖主线程声明。
5. **来源时间与版本差异**：动态来源重查、历史版本、论文更正／撤稿作为可追溯事实差异，来源不足时显式失败或限制。
6. **真实端到端竖向样例**：选已有取数基础的 PNH 或 IgAN 完成一个开发项目的研究→A/B/C→复核→手动刷新→恢复，暴露接口缺口后扩到八适应症。此样例不豁免 24 门户终验。
7. **内部诊断而非用户首屏诊断墙**：完整性、缺件、来源访问与恢复原因留工程证据；医学用户看清晰限制和真正证据。
8. **准确最终源身份**：稳定后受控收敛 release source-set，最后重建包与验收，不以旧包或单 HEAD 代替当前现场。

这些是对现有目标的实现建议；若某条改变科学归并规则、来源权威或用户可见行为，先用原生 Ask 给出选项。用户已经裁决的新鲜度、历史截止和药智短期复用不必再问。

### 13.3 应移出／保持排除的内容

首版包不纳入 PDF／PPT 输出、CSV／XLSX 导出、雷达、证据成熟度视图、定时监测、默认综合排名、Meta/NMA。已有非 HTML 开发代码和相应有界兼容合同不在本次交接删除。用户也未授权现在大规模清理历史 Skill／证据或旧工程。

## 14. 恢复授权后的详细行动计划

以下是交接建议的执行顺序，不是今天已经执行，也不是新的自主恢复授权。

### 第一步：重锚现场，避免从陈旧状态继续

1. 显式指定英文根目录；不要依赖宿主默认 cwd。
2. 读当前全局／项目 AGENTS、本交接、最新暂停、v1.4／v5。
3. 读取实际 Goal 状态；若新 Agent 没有共享原生 Goal，使用本交接的原文作为接管输入，不假称已恢复原来的任务对象。
4. 核对 HEAD、八哈希和当前 git 状态；有外部改动时先逐项比较，不覆盖。
5. 确认真正自己的运行任务／句柄；不要按文档旧 PID 管理进程。
6. 更新一个当前 checkpoint 的状态头，说明用户何时授权恢复与本轮方法。当前用户机制是主线程＋必要原生 SubAgent，不用旧执行／会商 runner。
7. 如需受控备份，先明确当前 source／证据范围、体积与恢复方式，不复制整个巨大工作区形成无穷备份。

只读核验命令示例：

~~~sh
cd "/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow"
git rev-parse HEAD
git status --short --untracked-files=normal
shasum -a 256 src/ci_workflow/reports/b/semantic_grouping.py src/ci_workflow/renderers/portal/report_b.py src/ci_workflow/renderers/portal/assets/report-b.css assets/portal/charts.js src/ci_workflow/renderers/portal/assets/charts.js assets/portal/manifest.json tests/reports/b/test_semantic_grouping_proposals.py tests/browser/test_b_semantic_proposals.py
~~~

所有命令只能指向新英文工程。不要访问旧中文目录确认是否存在。

### 第二步：关闭暂停中的 P3 有界修复，不宣称整个 P3 完成

1. 以目前冻结字节给原生独立只读 reviewer，范围是第二轮两 P1／一 P2 和相邻消费者；提供原反例、当前代码、类型合同、真实页面判断标准。
2. 复用旧上下文仅在真实句柄可用且恢复兼容时；否则新干净上下文，不从主线程“已通过”摘要推定接受。
3. 重跑域碰撞、事实摘要漂移、输入重排、全页→产品页、纵向 12／24 周、跨域提案拒绝、冲突输入旧站点保全。
4. 挑战孤立提案／不存在引用／不支持域等边界，区分已有缺陷与纯待查场景。
5. 出现新问题先 RED 后 GREEN，再核查全部共享消费者。科学源码审阅期间保持冻结，前端独立写集不与其重叠。
6. 最终独立结果必须有实际测试／产物检查、结束身份与明确结论；pending、空目录、只有读文件均不算 accepted。

恢复后测试命令：

~~~sh
uv run pytest tests/reports/b tests/browser/test_b_semantic_proposals.py -q --tb=short
uv run pytest tmp/semantic-rereview-a4bUhi/test_rereview.py -q --tb=short
bash tools/gate.sh
uv run pytest tests/integration tests/browser/test_b_portal.py -q --tb=short
~~~

先确认临时反例实际路径与适用依赖；临时反例是独立证据，不替代正式测试。中断过的宽门要完整重跑，不能只把剩余用例计数拼上旧结果。测试输出准确记录 scope、源码／资产身份、终态和未涵盖事项。

### 第三步：完成医学语义竖向链

1. 从研究包的原始临床观察梳理完整语义字段、unknown 与有证据 N/A。
2. 保留原值和来源定位，设计版本化临床时间政策；需新医学裁决时再 Ask，不用通用 ±2 周替代。
3. 模型只生成带来源的候选；确定性门与真实独立复核共同决定是否能同图。
4. 接现有科学签发／接受链，补原生上下文证明；不要再加自由填字符串旁路。
5. B 疗效、安全、基线、处置、长期、矩阵与产品页都消费统一完整视图；同试验纵向描述与跨试验比较分开。
6. 正向、负向、恢复、幂等、来源变更和页面事实一致性全部留回归。
7. 不能兼容就相邻小多图，未知不丢事实；不能因为缺少现代参数就伪造历史试验设计。

### 第四步：并行但受控地收口 P2／P4

**来源线**：动态核查、历史公开可知、全球／中国路线闭包；Publication 获取与补件；扫描文档实际 OCR；药智已登录浏览器与失败重检；原始字节→派生→事实的提交和重开一致性。

**门户线**：A 矩阵／产品档案消除旧单对；全部页行级／逐页真实来源；B 全域语义视图与可读性；C 完整入排、方案时间／访视／统计设计与多个可选模式。图形选择基于实际数据，不生成空坐标轴或字段墙。

分工只用于独立写集。主线程持有共享合同／run_service／科学接受边界，避免多个 Agent 同时各改一套身份规则。

### 第五步：P5 安装、真实宿主与真实生命周期

1. 固定候选输入与源集合，构建新的 HTML-only 包；不复用 9 月 6 日旧包当最终候选。
2. 在新隔离目录 fresh-install，验证归档／安装集合、权限、环境、真实入口说明和恢复指引。
3. 逐个真实 Codex／Hermes／OMP 验证同合同、独立上下文能力、失败与恢复；不可创建独立上下文必须预检失败。
4. 补 B/C 提交后恢复窗口，运行完整 restore／resume／手动刷新／重建，不仅验 ZIP。
5. 首次、刷新、恢复都绑定真实复核签发、锁定快照、latest 与新增／修改／撤回差异；失败不覆盖旧 accepted。
6. 未满足真实运行条件要准确写 unavailable／未验，不用替身冒充真实门，也不要求用户／同事承担测试。

### 第六步：P6 八适应症完整矩阵

| 适应症 | 规模／关注点 | 必须交付 |
|---|---|---|
| 特应性皮炎 | 拥挤竞品宇宙、多终点／人群／时间 | A、B、C 三独立门户 |
| 重度哮喘 | 拥挤、表型与背景治疗等语义 | A、B、C |
| 类风湿关节炎 | 拥挤、多机制与复杂方案 | A、B、C |
| 溃疡性结肠炎 | 拥挤、诱导／维持与定义差异 | A、B、C |
| CRSwNP | 中型、终点与方案差异 | A、B、C |
| 结节性痒疹 | 较小／关键试验敏感 | A、B、C |
| IgAN | 较小／关键试验敏感 | A、B、C |
| PNH | 稀有／关键试验敏感 | A、B、C |

表中的关注点是测试规划，不是本交接新生成的临床结论。每项必须有真实来源／完整性／科学／视觉／交互接受，不是生成三个 HTML 文件即通过。

执行模型负责检索和生成，独立上下文分别复核遗漏、医学语义、来源、视觉与交互，主线程最终审阅实际文件和浏览器。用户／同事不是测试资源。已有历史资料可合法复用，但其新鲜度、历史截止和身份必须重新按当前合同处理。

### 第七步：P7 唯一候选、最终冻结与后续发布

1. 从已验证源和规范证据建立明确 release source-set；保留原脏树和历史，不猜测性提交。
2. 形成唯一候选 commit、安装包与相关 manifest；该身份之后的检查必须使用它实际构建的字节。
3. 绑定 24 门户、独立复核、浏览器回执、三宿主、fresh-install、恢复包与实际恢复结果。
4. P0/P1 为零；P2 已修或有可证明不影响科学性／可用性的处置；P3 可列后续。
5. 所有门满足才输出 RC_FROZEN。冻结后不在相同身份下修改代码／测试／catalog／runner，问题进入下一候选。
6. RELEASED 与对同事正式分发按实际用户授权执行，不能把内部验证等同正式发布。
7. 旧工程至少三真实项目覆盖 A/B/C 等条件满足后，仍需用户再次明确删除授权。

## 15. 最终验收账本应该如何记录

建议在既有 checkpoint／验收表中按下列维度维护，不新增一套复杂治理系统：

| 层级 | 完成证据 | 不能替代它的材料 |
|---|---|---|
| 开发 | 精确范围 Ruff、strict-mypy、分层单元／合同、旧路径检查 | 单文件通过、旧源码 gate、未结束进程。 |
| 内部 Skill | 正向、负向、恢复、幂等和实际消费者 | 仅 schema／SKILL.md 存在。 |
| 科学 | 全量闭包、真实来源、Publication、完整语义、独立复核 | 记录数、fixture、proposal 字符串、主线程自证。 |
| 报告 | 全事实图表／折叠表同集、行级下钻、每页来源、限制正确 | 首页存在、只有截图、空模板。 |
| 视觉 | 两浏览器 × 四精确视口 × 所有物理页＋交互 | 单页／单引擎／旧截图／仅溢出自动检查。 |
| 包装 | HTML-only 集合、凭据扫描、安装字节／模式、隔离运行 | 仅可解压、开发仓 import 成功、旧包。 |
| 宿主 | 三个真实宿主合同／能力／恢复与最终门户语义一致 | StaticCapabilityProbe、mock、skipped。 |
| 生命周期 | 实际 restore／resume／refresh／diff／rebuild | 摘要匹配、只恢复文件未运行。 |
| RC | 同一 source-set／commit／包／24 门户／接受证据绑定 | 多个源码时期测试数相加、旧 accepted 挪用。 |

“deferred”“not applicable”“evidence insufficient”“unavailable”“interrupted”要单列，不算 accepted。科学上可证明不适用与为躲测试而写 not_applicable 是不同概念。

## 16. 授权、安全、资源与协作规则

### 16.1 禁止触碰旧中文工程

- historical: 旧中文工程路径（已停用、禁止接触）是 `/Users/smkzw/Documents/AI Products/` + `竞品调研工作流`。此路径只为说明禁止范围；**不得读、写、盘点、chmod、删除，甚至不需要确认是否存在**。当前宿主默认 cwd 可能仍是它，所以每个 shell 调用必须显式 workdir 指向英文工程。

不因 AGENTS 的旧 overlay、ZCode 旧建议或迁移工具存在，就执行旧根操作。10.7 以前零接触；最终退役还需要最新用户再次批准。

### 16.2 Git 与文件保全

- 不 reset、checkout、clean，不 git add .，不以恢复便利为理由丢弃用户改动。
- 已跟踪删除也是用户现场的一部分，不自动补回。
- 不猜历史阶段生成一串提交；先确认当前真实源集合。
- 不改 Task 10.5 及更早封存记录去适配新合同。
- 文件编辑用最小完整改动；失败反例、原始证据、回执应保留。
- 本次交接不做提交、代码修复或资源清理。

### 16.3 清理磁盘

用户要求定期控制磁盘增长，但不是允许清空 tmp／output／.artifacts。需要先分类：可再生且未被运行引用的缓存、规范证据、原始 CAS、失败反例、恢复备份、最终产物、用户资料。

仅精确处理确认无引用、无活跃任务占用的可再生对象，记录目标与理由、保留必要摘要／恢复方式。避免复制全仓造成新的容量增长。会话数据库、Codex 归档／线程历史、封存接受、恢复备份不属于通用清理对象。

9 月 8 日记录：mypy 31MB、pytest 284KB、ruff 152KB、tmp 206MB、output 337MB、artifacts 1.0GB、可用 424GiB。当时缓存小且活跃，没有删除。**这些是历史数据，今天没有重查，不用于当前容量判断。**

### 16.4 代理协作与提问

本阶段继续授权后可由主线程与必要原生 SubAgent 实施／只读复核，不使用旧执行／会商 runner。独立复核要冻结输入与产物，提供原始来源和标准，不交给 reviewer 仅有说服性的“修好了”摘要。

只有真实运行并返回合格结果才可算独立复核；pending、拒绝启动、失效句柄、空目录、无结束身份均不接受。不得因为有空闲代理配额就增加无价值层级。

用户要求原生 Ask 选择题；涉及新科学规则、来源权威、可见行为实质变化时提出清楚的选项。一般实施细节自行处理。已明确的新鲜度、历史截止、药智观察复用与首版排除项不要反复重问。

遇用户“无损暂停”立即保全当前输入、源、失败、进程终态与下一安全动作；不要先完成未经要求的工程收尾，不以 complete／blocked 假装暂停。

## 17. 可以直接交给下一 Agent 的接管提示词

以下提示词必须配合本完整交接，不是替代它；若用户还未授权继续，则只读接管：

~~~text
你接管的是竞品调研多 Skill 工作流，不是从零开发项目。唯一允许工作的工程根是：
/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow

先完整阅读：
docs/handoffs/competitive-intelligence-workflow-handoff-20260911.md
context/PAUSE_HANDOFF_20260908_093147.md
context/ci-gpt6-takeover-20260905.md
docs/specs/competitive-intelligence-workflow-design-v1.4-review.md
plans/gpt6-execution-plan-v5-20260905.md
docs/handoffs/goal-snapshot-20260911.json

项目当前 paused，Goal 未完成。用户明确继续后再实施，不因移交自动恢复。
旧中文工程零接触；所有 shell 显式指定英文 workdir。保留大规模脏树、封存历史与失败证据，不 reset/checkout/clean/git add .，不猜测提交、不清理交接证据。

当前是一个入口、内部类型化多 Skill、三独立中文多页 HTML 门户：
A 全景、B 临床结果、C 试验设计。首版无 PDF/PPT 输出、CSV/XLSX、雷达、成熟度、定时监测、默认排名或 Meta/NMA。
新鲜度按来源性质；历史截止还原当时公开可知；药智只用用户已登录浏览器，同运行短期复用，失败重检，不采集凭据。

先核对 HEAD 和交接中八 SHA。最近 P3 第二轮的同 ID 跨域串事实、纵向系列丢失、跨域提案静默忽略已修，有界测试通过，但最终独立复验、完整 gate/integration/B browser 被用户暂停中断，不能沿用旧全绿。
从这些反例和真实 HTML 消费复验开始；不要再造语义 helper 或把 proposal 当 accepted。
完成完整医学单元、原始来源／时间、真实独立复核签发、A/B/C 页、手动刷新恢复、HTML-only fresh-install、三个真实宿主和八适应症 24 门户后，才允许同一候选身份下 RC 验收。

本阶段由你或原生 SubAgent 做工程，不使用旧执行／会商 runner；产品独立复核不能主线程自证。必要新决策用原生 Ask 选择题；其他实施自行推进并准确记录范围。
不要把生成文件、synthetic fixture、mock 宿主、历史报告、evidence-insufficient 页或不同源码时期测试数算成最终接受。
~~~

## 18. 本次交接整理完成范围

2026-09-11 本次工作选择：**direct，只读证据核验＋交接文档整理**。不涉及新的科学结论接受或产品改造，所以未新派执行／会商／原生复核节点。

已做：读取当前原生 Goal；检查最新暂停及关键历史设计／计划／review；核对 HEAD 与八关键哈希；定位当前实现和测试入口；整理需求演变、完成／缺口、停滞分析、权威地址及可执行续接步骤；保存 Goal 原文。

未做：恢复 Goal、启动工程测试、重新生成报告、运行药智／OCR／真实宿主、修改产品代码、提交、清理、读取旧中文根、重新验证全仓或最终备份。

交接自身校验：主文档与根入口的本地链接已核对目标存在；Goal 原文与机器可读快照一致（2,765 字符）；八关键文件 SHA-256 全部与暂停记录一致。此校验只证明交接导航、目标抄录和指定现场身份，不是产品测试或接受。

本交接的目的，是让继任者从真实现场继续，而不是通过交接宣布项目完成。项目仍暂停，最后修复仍待最终接受，整体 Goal 仍未达成。
