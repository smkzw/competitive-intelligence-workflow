# Task 10.6 实施步骤：首版 HTML-only RC

## 阶段 A：合同、provenance 与恢复生产者

- [ ] A01：独立审计当前 bundle、fresh-install、full-matrix、recovery、receipt 合同与 canonical v1.3；冻结缺口表。
- [ ] A02：先写 clean-source provenance、HTML-only 最终包内容、`recovery-package-v1` manifest/receipt 与恢复演练负向测试。
- [ ] A03：实现最小 bundle provenance、dirty/source mismatch/required-content fail-closed 和 recovery producer，完成定向与相邻回归。

## 阶段 B：source closure 与唯一 RC

- [ ] B01：建立显式 release source set，完成唯一 gate、Phase 0–10 确定性回归、schema/package/legacy scanner 和无损 source-closure checkpoint。
- [ ] B02：在隔离 clean worktree 创建唯一 RC commit/tag；验证当前工作树和用户改动未被 reset、checkout、clean 或覆盖。

## 阶段 C：最终包、安装和真实矩阵

- [ ] C01：从 RC commit 构建/验证/fresh-install HTML-only bundle，记录 source/package/catalog/scope/RC digest 与安装解析入口。
- [ ] C02：在全新 release root 用最终安装入口为八个适应症分别重跑 A/B/C，生成 24 个新门户、项目、run/job/session/artifact/verdict。
- [ ] C03：验证 24 个独立 HTML 门户的宇宙/来源/GateSpec、科学 QC、页面 coverage、图表—默认折叠完整表格—证据下钻一致性、搜索/筛选/URL/键盘；所有物理页面在 Chromium/WebKit 覆盖桌面/平板/手机/窄屏四类视口，三宿主只消费同一最终 bundle。
- [ ] C04：由当次 A/B/C HTML artifact manifests 实际计算 `formats=1`；拒绝 PDF/PPT、CSV/XLSX、雷达、证据成熟度和 monitoring artifact 以及所有旧摘要/旧 receipt。

## 阶段 D：恢复、独立验收与冻结

- [ ] D01：构建 recovery package，在一次性隔离根完成 fresh-install → 恢复项目 → 继续手动刷新 → 代表性 HTML 重建演练。
- [ ] D02：生成 pre-RC host receipt 与 final owner-stage release receipt，完成显式绑定；required-v1 closure 仅余 `legacy-absence` future owner。
- [ ] D03：完成科学、视觉、包、恢复独立 PASS/VETO 和 Codex 实际 HTML 产物验收；P0/P1=0，P2 已修复或有证据的明确 non-impact disposition。
- [ ] D04：完成治理审计、final report、freeze record；仅在所有门通过后输出 `RC_FROZEN`，否则保留不可变 checkpoint 并无损暂停。

## 关键前置与阶段门

执行与检查 Agent 必须从工作区完整读取 `docs/specs/competitive-intelligence-workflow-design-v1.3.md`；上下文注入的截断片段、既有 Skill 文案或历史 ZCode 摘要不能替代完整合同。

每个阶段只在前一阶段检查点由 Codex 接受后继续。A 阶段不得创建 RC commit、写外部 acceptance root、调用真实宿主、安装最终 bundle 或触碰真实旧根。B 阶段不得把局部 gate 绿灯、旧摘要或未解释 source drift 写成 source closure。C/D 阶段不得从 source checkout、旧 bundle、旧 run/job/session/artifact/verdict 或宿主私有缓存运行。

每个阶段 checkpoint 同时执行精确磁盘卫生：只清理由本阶段生成、可再生、已被摘要或哈希替代且不再被测试/恢复引用的缓存、临时件和失败测试副本；记录目标及释放字节。规范文档、科学原始证据、未验收门户、fixture、receipt 和当前/上一恢复点默认保留；禁止 broad glob、`git clean`，旧根不进入盘点。

## 固定范围和恢复规则

- 首版只发布 A/B/C 独立站点式 HTML；PDF、HTML-PPT、PPTX、CSV/XLSX、雷达图、证据成熟度视图和 scheduled monitoring 不进入 v1 bundle 或验收集合。
- 公开入口是安装 Skill 的“竞品调研”关键词；一句话自主研究和可选 typed `research-package` 使用同一严格 schema 和门槛。未指定报告类型时用宿主原生 Ask 解释并选择 A/B/C，历史截止日可选；每个新项目只询问一次 Yaozh 访问条件。
- 类型化控制图由应用持有；LangGraph 不是基础依赖、科学真源或离线恢复前提，任何未来适配器都必须可移除。
- 首份报告的竞品宇宙必须逐项执行全球/中国必查来源以及别名、靶点、企业和试验反向扩展，并由 clean-context 独立复核；任何固定数量或 Top-N 都不构成闭包。
- R2.2 已实现：四类扩展采用类型化回执并绑定实体/来源/查询摘要，最后连续两轮零
  新增才收敛；独立 reviewer/producer 身份与上下文隔离并绑定候选宇宙摘要；A/B/C
  产品运行共享唯一项目级 universe identity。Publication/manual gate 与逐对象
  GateSpec 仍须分别完成，不能由本项绿灯替代。
- 登记关联的主要结果、延长期主要结果、关键长期暴露/安全性发表物必须检查；必要论文不可访问时只建立一个 Markdown manual-supply gate，用户一次响应后同一快照不得重复追问。补件核验后在投递目录原地规范重命名，先记录原名、SHA-256、DOI/登记号和新名，冲突失败关闭且不修改文件字节。
- 关键缺失/异常零值要做两条不同替代恢复检索和 clean-context 独立复审；缺独立审查能力则预检失败。Yaozh 仅为可选浏览器会话辅助商业来源，凭据和令牌不入任何 artifact。
- B 的 48/50 周等近窗口只有临床构念、定义、方向、单位、估计目标、分母、分析集和分析形式兼容时共框并标差异；不兼容即拆分。
- B 气泡图只使用疗效×总体安全性、疗效×严重风险、持续性×停药风险三组版本化临床预设及指定大小语义；不默认排名、综合评分或研发建议。
- 任何技术失败、访问阻断、未公开、未报告、明确为 0、冲突和不适用状态必须分开保存；不能用空白、总完成率或旧证据替代关键单元。
- A/B/C 报告都必须先渲染并绑定门户字节，再由 `review issue` 的真实独立进程生成 receipt 与 issuance record；晋级时复核正式 verdict 有效期。研究包自审、手写 receipt、同身份/同会话和漂移门户全部失败关闭；等待期间允许多次纯复用 resume，并按来源图验收。
- 当前产品研究交接必须由严格 v1.3 审计信封按规范路径和 SHA-256 绑定所选 A/B/C 专属科学载荷，并在 manifest 发布后复核当前字节；松散 `report-data.json` 或未绑定专属包只允许留在明确的 fixture/兼容测试路径，不能完成产品 CLI 运行。非论文来源的 publication 分类必须为 `not_applicable`，不能因来源可访问而冒充主要结果论文。
- 同一产品运行可选择多个报告类型，但必须分别生成 A/B/C 独立门户且不得生成融合首页；共享节点只能在节点键和实际输入摘要同时一致时复用，恢复只重算未完成报告及其下游。
- 每个项目的 Yaozh 初始回答仅允许 `available`、`unavailable`、`skipped` 三态并只落盘一次；同值重放必须字节幂等，改答、篡改、跨项目替换和软链接失败关闭。该记录不含凭据。三态已接入来源计划和宿主预检：仅 `available` 启用 `required=false` 辅助路线，另外两态为非阻断 `not_applicable`；会话失效只形成绑定项目回答摘要、提示自行登录的类型化可选访问回执，不覆盖项目回答或阻断核心研究。药智在来源政策 1.1 中无 `direct` 权限。真实浏览器适配器与登录态探测仍待完成。
- 每次首次或恢复运行均重新执行能力探测，不复用历史 preflight 或运行时探针缓存；矩阵通过唯一应用层边界原子写入 `capabilities/preflight.json`，读取缺失回执不得产生目录副作用，软链接和非普通目标失败关闭。研究能力阻断发生在来源研究前；仅 HTML 验收能力阻断时保留研究事实但禁止 format；药智登录单独缺失不阻断。`capability_blocked` 必须与证据不足及技术失败分开记录并可从同一项目恢复。
- B/C 双重穷尽后必须先闭合 `report_evidence` 终态再原子发布 blocker；终态 manifest 要能以对应报告 research-package 摘要重复验证和恢复。
- A/B/C HTML 只允许通过共享未发布渲染事务进入规范版本目录：先写 staging，再原子换名并写 `html.manifest.json`；无绑定中断残留可精确恢复，任何已有产物清单、覆盖投影、artifact store、当前运行清单或科学复核状态绑定都必须拒绝覆盖。
- 核心问题可回答时带限制交付，核心不可回答时只显示简洁证据不足页并保留内部审计包；可选空模块省略或一句话说明，不生成空坐标轴或固定零值占位。
- 只重排失败节点及其下游；保留已锁定事实、历史快照、latest 指针和 added/changed/withdrawn diff。刷新由用户手动触发，之后检索、差异识别和页面重建自动完成；不建设定时监测、后台轮询或无人触发刷新。
- Task 10.6 不读取、inventory、validate、apply、chmod、删除或 absence-check 真实旧根；`legacy-absence` 只作为 `pending_future=1` 保留。

## 最终信号

```text
RC_FROZEN reports=3 formats=1 hosts=3 recovery=passed pending_future=1
```

发布状态只允许 `DEVELOPMENT_CANDIDATE → RC_FROZEN → RELEASED`。`formats=1` 必须来自当次 HTML artifact manifests 的实际 closure；`reports=3` 表示 A/B/C 报告族，24 个门户由 full-matrix closure 单独证明。上述信号不是脚本退出码别名，也不能由 worker 自行宣布；本任务不得宣称 `legacy_absent=passed`。
