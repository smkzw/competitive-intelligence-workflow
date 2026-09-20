**审阅结论：R2 已具备较完整的类型化证据控制链，但不能无保留地认定“R2.4 只剩来源新鲜度”。建议先核验并修复下述门槛问题，再优先推进 R3 的 B 类医学语义兼容门；Yaozh 真实浏览器适配作为独立可选来源切片随后实施。**

本次未修改文件、运行项目测试或操作浏览器。仅对允许文件进行静态分析，并提取其中两个函数做无落盘内存探针；探针使用替代依赖，不能证明完整产品链可达性。下文测试数量均为检查点记载，未经本次重跑。当前 Goal 原始记录、部分运行服务和原始 runner receipts 不在白名单内，因此不声称最终验收，也不提供虚假的完成百分比。

**一、阶段完成度与架构判断**

| 范围 | 观察事实与证据锚点 | 审阅判断 |
|---|---|---|
| R0 | 路线要求 inventory、外置恢复快照、用户变更映射与来源边界；本次未获准读取这些原件。[路线图](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/plans/competitive-intelligence-workflow-roadmap-v1.3.md:58) | **无法独立确认全部完成**；后续开发门通过不能补证 provenance。 |
| R1 | 当前设计、路线图、执行计划对 HTML-only、独立门户、入口、刷新和发布边界基本一致。Task 10.6 同步文件及 disposition 不在白名单。 | **核心三文档一致，完整退出证据未全部复核**。 |
| R2.1 | 包模型严格绑定报告载荷；入口测试覆盖一句话、历史截止日和图节点。真实药智、真实三宿主明确未完成。[执行计划](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/plans/codex_execution_ci-rebaseline-rebuild-v3.md:176) | **工程链已有实现，宿主自主研究体验尚未获得真实运行证明**。 |
| R2.2 | 模型实际校验四类扩展、最后两轮零新增、独立身份/上下文及候选摘要；检查点明确限定完成范围。[模型](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/domain/research_package.py:895) | **完成声明有实现支撑**，不等于真实适应症竞品宇宙已经穷尽。 |
| R2.3 | 正式 publication 裁决、逐纳入试验检索回执进入包校验；检查点记录补件、OCR 交接及局部恢复。[检查点](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/.trellis/tasks/archive/2026-09/09-05-r23-publication-manual-product-gate/checkpoint_20260905_r23_complete.md:5) | **切片完成声明基本一致**；真实出版商、付费墙、真实补件未验收。 |
| R2.4 | P3–P5 已勾选，P2/P6 开放；记录最终产品链 579、活跃开发测试 945、安装相关 28 passed/1 skipped。[检查点](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/.trellis/tasks/09-05-r24-gatespec-blocker-closure/checkpoint_20260906_p3_p5.md:20) | **已有大量闭包工作，但“仅剩新鲜度”需修订**，见下述发现。 |

架构方向仍符合批准合同：一个公开入口、内部类型化 Skills、审计信封绑定 A/B/C 专属载荷，**双层载荷本身不构成第二事实库**。但“满足合同”应分层表述：

- **独立复核、不可变阻断历史：**已有身份、摘要、原子发布和恢复重验机制；来源审阅声明与最终门户签发仍是不同接受层。[复核合同](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/docs/specs/competitive-intelligence-workflow-design-v1.3.md:451)
- **三独立门户：**文档和部分实现支持；本次未读取 A/C 渲染器或重开物理页面，不能确认完整页面责任及视觉表现。
- **手动刷新差异：**合同明确，但相关实现不在白名单，不能由普通 resume 推定刷新、撤回差异和局部重建已经完成。
- **三宿主可安装：**隔离安装测试有价值；真实入口、工具映射、独立签发仍未闭合，不能把不同 `--host` 参数视为三宿主真实运行。

**二、P0–P3 发现**

以下严重度表示建议处置优先级；“P1 候选”不表示已复现端到端漏洞。

**P0：本次未确认。**有限文件审阅不能证明全系统 P0 为零。

**P1-1｜已确认合同差异：B 关键基线规则排除了监管材料。**

- **事实：**样本量、年龄、性别、严重程度四项关键基线规则只允许 `primary_trial_report` 和 `clinical_trial_registry`。[B 规则](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/policies/gates/B-v1.yaml:72)；批准设计允许监管材料支持基线，来源政策也给官方监管来源的基线域 `direct` 权限。[设计](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/docs/specs/competitive-intelligence-workflow-design-v1.3.md:257)
- **推断：**论文不可得、但监管材料已完整披露逐组基线时，可能被错误阻断，影响“官方证据充分则带限制继续”。
- **建议：**修订该来源映射并补一正一负产品用例：合格监管基线可以满足门槛；药智或公司总结不得因此获得同等资格。无需新增产品裁决。

**P1-2｜局部算法缺陷，产品可达性待核验：终点逐组覆盖可能被数量补足。**

- **事实：**`covered` 在剔除跨组复用事实之前计算，`contributing` 随后排除跨组事实，最后仍使用旧 `covered` 加总事实数判定。[evaluator.py](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/gates/evaluator.py:409)
- **探针结果：**两个组共同引用事实 F，再给组1加入独立事实 F1、F2，函数返回 `satisfied`；有效谱系只剩 F1、F2，组2没有独立有效事实。
- **推断：**若上游允许这些绑定到达此函数，会违反“每组独立证据”合同。本次未读取其上游模型，不能声称完整产品绕过已成立。
- **建议：**先用真实模型及产品提交入口复现；按过滤后的有效绑定重新计算组覆盖。若上游已拒绝，也应补回归并消除函数内部不一致。

**P1-3｜R3 必须关闭的语义风险：共同缺失可能被当作兼容。**

- **事实：**B 分组键使用相同的 `estimand-not-reported`、`denominator-not-reported` 等缺失标记；48–56 周被映射为同一时间带，随后按键直接分桶。[分组逻辑](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/renderers/portal/report_b.py:2723)
- **探针结果：**两项试验缺少上述语义、实际时间分别为48和50周时，可得到相同键。
- **推断：**键相同只证明表达一致，不能证明临床兼容。该问题支持优先推进 R3；不能仅凭当前渲染器判定上游全部语义门均缺失。
- **建议：**未知语义不得自动取得共框资格；缺少版本化规则时分列，并保留原始时间和差异说明。

**P1-4｜已知未完成：新鲜度仍需“裁决＋实现＋验证”。**

- **事实：**GateSpec schema 没有新鲜度字段；研究包虽保存获取、发表、生效日期，仍不等于逐单元的新鲜度判断。[schema](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/schemas/gate-spec.schema.json:179)
- **推断：**“只剩用户回答”低估剩余工程量。还需统一历史截止日、来源版本时间、复核年龄、覆盖单调性及恢复行为。
- **建议：**将其明确列为未完成实现切片，避免用重新下载时间替代内容版本新鲜度。

**P2｜适用性、能力与证据证明强度需收紧。**

- **事实：**开发成熟度目前从“监管来源＋观察值”推导获批、从监管事实的“不适用”推导暂停/终止，而非读取明确状态事件。[成熟度推导](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/gates/evaluator.py:126)
- **推断／建议：**这不必然证明产品绕过，但属于医学语义债务；补合法监管材料反例，确认是否影响适用规则。若能漏评关键单元，应升级 P1。

- **事实：**`login_browser` 只启动新 Chromium 页面；独立上下文能力读取环境声明。安装测试把能力全部设为 true，显式真实宿主测试也沿用该环境构造器。[预检](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/application/capability_preflight.py:249)、[测试环境](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/tests/hosts/test_fresh_install.py:214)
- **推断／建议：**这些只能证明部分工具或合同能力。真实宿主验收须排除测试覆盖值，分别证明已登录会话连接、独立审阅签发及 Chromium/WebKit 可用性。

**P2｜治理和磁盘卫生存在可误执行的文字。**

- **事实：**执行 metrics 的模型身份仍记为 `default`；当前检查点标题状态称 conference pending，正文又记录会商已通过；实施计划允许删除“runner 原始日志”。[metrics](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/metrics/ci-r24-gatespec-blocker-closure-20260905_execution_metrics.md:5)、[实施计划](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/.trellis/tasks/09-05-r24-gatespec-blocker-closure/implement.md:15)
- **推断／建议：**摘要不足以独立证明精确模型身份，但不据此认定路由违规。同步实际身份和当前待办；同会话两轮属于一条审阅链。删除条款应改为引用与恢复依赖确认后的精确归档规则，**保留当前 runner evidence、测试证据、fixture、快照及受保护运行时状态**；只有摘要不能替代原始证据。

**P3｜维护建议。**B 渲染器同时持有别名归一、时间带、语义分桶和呈现逻辑。随 R3 切片逐步把兼容裁决收束到报告领域层，渲染器消费已裁决分组；无需开展无关的大规模重构。

**三、计划处置与下一最小切片**

建议依赖顺序：

**R2.4 门槛反例核验/修复 → 新鲜度合同落地 → R3 B 兼容门 → Yaozh 可选真实适配 → 门户、三宿主、刷新恢复及24门户验收。**

新鲜度等待裁决期间，可以准备 B 类型合同和反例；不应把未关闭的 M2 宣布完成。

| 处置 | 建议 |
|---|---|
| 必需修订 | 更新“仅剩新鲜度”声明；处置上述 P1/P1候选；统一监管基线来源资格。 |
| 必需新增 | 有版本的 B 兼容裁决：候选分组、逐维条件、通过/拆分/未知、理由和输入摘要。 |
| 建议优化 | 合并当前状态摘要，保留历史；去掉重复语义裁决，保留不同 blocker 的专用类型及共同发布边界。 |
| 延后 | Yaozh 批量覆盖和三宿主全面适配；不能因此删除已批准的可选来源能力。 |
| 未来版本 | PDF/PPT、表格导出、雷达、成熟度视图、定时监测继续排除在 v1 外。 |

**下一最小实施切片：先完成“逐组事实覆盖＋监管基线来源”两个门槛反例。**验收条件：

1. 用真实模型复现或证据性排除跨组计数路径；缺少任一组独立有效事实必须阻断。
2. 完整监管基线通过；缺组、缺严重度、低权威来源仍阻断。
3. 产品入口、恢复及 no-draft 链验证一致，修复不能靠改标签、删对象或降低门槛通过。
4. 运行聚焦、相邻及阶段要求检查，将结果绑定当前修订；不重写历史接受记录。

随后 B 最小切片只处理**一个临床构念、两项试验、48/50周**：模型提出候选，确定性规则逐维裁决；兼容者保留实际时间共框，不兼容或关键语义未知者拆分；图表使用同一事实集合、不池化、不排名。涉及显示变化时，再执行对应物理页面的双浏览器四视口检查。

**四、Yaozh 的正确安全边界**

现有一次回答、会话失效独立回执及来源降权方向正确。[访问回执](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/application/yaozh_access.py:50)、[来源政策](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/policies/sources/source-policy-v1.yaml:70)

建议真实适配严格遵循：

- 由宿主操作用户已登录会话；不复制配置目录，不读取 Cookie、存储、授权头，不自动登录。
- **内容与回执分离：**只提取获准业务字段；回执保存项目/运行、回答摘要、路线、访问时间、结果和脱敏内容摘要。禁止全量 DOM、HAR、调试响应或带账户信息截图落盘。
- 临床数值仅用于找原始来源；其他适用域最多交叉核验。与官方证据冲突须保留冲突并追溯。
- 会话失效、验证码、工具缺失、解析失败分别记技术状态；不改初始回答，不伪装“科学无数据”，不阻断可由公开来源完成的报告。
- 首个真实切片仅验证一个查询的成功、会话失效和无凭据产物三分支，不先建设批量爬取系统。

**仍需用户裁决的事项**

实质产品裁决仍是新鲜度：可变状态与固定历史结果是否采用不同政策、默认复核窗口，以及历史截止日采用“当时已公开知识”还是另一明确时间口径。建议按声明域区分来源版本资格与复核年龄，避免一个 TTL 淘汰所有旧论文。

上述门槛修复、未知语义不得自动共框、Yaozh 非阻断与无凭据边界，已有批准合同依据，无需重新向用户索取同一授权。

