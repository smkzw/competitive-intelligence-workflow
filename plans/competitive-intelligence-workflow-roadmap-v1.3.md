# 竞品调研多 Skill 工作流 · canonical 路线图 v1.3

- **状态**：canonical / rebaseline-approved
- **日期**：2026-09-04
- **适用**：从 R0 provenance recovery 到首版 HTML-only RC、24 门户真实来源矩阵、三宿主安装和 Task 10.6 冻结。
- **规范设计**：`docs/specs/competitive-intelligence-workflow-design-v1.3.md`
- **执行计划**：`plans/codex_execution_ci-rebaseline-rebuild-v3.md`
- **审计依据**：`reviews/zcode_ci_engineering_audit_20260902.md`（只作证据/建议）；处置记录：`reviews/zcode_disposition_ci-rebaseline-rebuild_20260904.md`。

本文取代 ZCode `zcode_revised_roadmap_20260902.md` 对后续工作的路线建议；Phase 0–9 已接受历史记录和已封存检查点不被重写。本文不改变当前工作树，不创建 RC，不读取或操作真实旧根。任何预计时间仅用于排序，不是通过条件。

---

## 1. 目标和不可变约束

### 1.1 目标

交付一个可安装的、跨 Codex/Hermes/OMP 一致的公共入口 Skill：用户用一句中文触发词和适应症即可启动自主研究；宿主 Agent 将研究结果编成严格 typed `research-package`，确定性引擎执行身份、证据门槛、快照和渲染。A/B/C 各自是完整的高密度多页面 HTML 门户。

首版真实来源验收覆盖八个适应症 × A/B/C = 24 个独立门户：特应性皮炎、重度哮喘、类风湿关节炎、溃疡性结肠炎、CRSwNP、结节性痒疹、IgA 肾病、PNH。执行代理和独立会议代理负责运行/报告，Codex 负责最终接受。

### 1.2 不可变约束

- A 是景观控制台，B 是证据比较室，C 是设计图谱；不得合并门户或套用通用 dashboard。
- HTML 是 v1 唯一发布格式。PDF、HTML-PPT、可编辑 PPTX 代码/历史可保留，但不进入 v1 bundle、默认 preflight、artifact closure 或验收。
- v1 不生成 CSV/XLSX 导出文件，不实现雷达图，不实现证据成熟度视图，不建设定时监测、后台轮询或无人触发刷新；用户手动触发后，来源复核、差异识别和 HTML 重建自动完成。
- 每个结构化数据集必须选择适当图形并带同一事实集的完整折叠表；叙事和缺失解释不强行画图。每页一个聚合外部来源区；用户可见表格不得出现内部文件 locator。
- 研究包是确定性引擎唯一科学入口，但用户不需要手写它；公共入口提供一句话自主研究和可选 typed package 输入。
- 类型化控制图由应用持有；LangGraph 不是基础依赖，未来适配器不得成为科学真源、三宿主一致性或离线恢复的前提。
- 首次竞品宇宙关闭必须独立审查。关键缺失和异常零值必须做两条不同替代恢复检索，并在干净上下文完成最终独立复审；没有独立审查能力则预检失败。
- B 使用模型辅助整体临床构念语义分组和确定性冲突守卫；48/50 周等近窗口仅在构念、定义、方向、单位、估计目标、分母、分析集和分析形式兼容时共框并标注差异；其余拆分。
- 药智网企业版是可选浏览器会话辅助商业来源，不能单独支撑核心结论；凭据/令牌只留在用户本机安全边界，不进任何 artifact。
- 登记关联的主要、扩展/补充、关键长期/安全性发表物必须检查。必需论文不可访问时只建立一个 Markdown manual-supply gate；用户一次响应后不得在同一快照重复追问。
- 保存不可变历史快照、latest 指针、added/changed/withdrawn diff；刷新由用户手动触发，后续流程自动完成。
- P0/P1 必须为零；P2 必须修复或给出有证据的 non-impact disposition。未满足不得用文件存在、局部测试或旧 receipt false-green。
- 当前 R0–R6 不读取、inventory、chmod、修改、删除或 absence-check 真实旧根；旧根处置必须另有授权和独立合同。

---

## 2. 依赖和里程碑

| 里程碑 | 进入条件 | 机器可判定退出信号 | 失败动作 |
|---|---|---|---|
| M0 Provenance recovered | R0 取得当前树和历史的不可变 inventory | 全量只读恢复快照、候选来源边界、dirty-tree 语义、质量门范围、用户变更映射均有摘要；无未解释来源 | 停止；不创建 RC、不覆盖用户改动 |
| M1 Canonical contracts | M0 的证据可读 | v1.3 canonical、roadmap、execution v3、ZCode disposition、Task 10.6 三文档互相引用且 scope 同步 | 修合同；不推进 R2+ |
| M2 Typed research/evidence | M1；包/设计合同通过预检 | 一句话自主研究和可选 package 走同一 schema；来源、宇宙、manual gate、双重穷尽和 GateSpec 负向/正向测试通过 | 仅回到失败节点；不渲染报告 |
| M3 A/B/C HTML product | M2；对应报告门槛和科学 QC 可用 | A/B/C 各有独立多页信息架构、图先表后、页底来源区、原位证据下钻、筛选、网址状态和四类视口真实浏览器证据 | 回修页面/数据；不以首页替代完整门户 |
| M4 Package/hosts/recovery | M3；HTML 产物和 schema 通过 | Skill bundle 可 fresh-install；Codex/Hermes/OMP 三宿主语义一致；手动刷新/恢复可重放 | 保留 checkpoint，修复并重跑受影响阶段 |
| M5 Real matrix | M4；全新 release root 和最终 source set | 8×3=24 个新鲜来源 HTML 门户，逐门户门槛/科学/视觉证据闭合，旧 IDs 全拒绝 | 只修复失败 indication/report；不得删对象或复用旧证据 |
| M6 RC freeze | M5；Task 10.6A/B/C/D 全阶段通过 | `RC_FROZEN reports=3 formats=1 hosts=3 recovery=passed pending_future=1` | 不输出 freeze；保留失败证据，走下一候选 |

`M6` 的 `reports=3` 是 A/B/C 三类报告族，`formats=1` 是当次 A/B/C HTML artifact manifest 实际闭合值；24 门户是全矩阵场景，不与信号中的报告族数量混淆。

---

## 3. 阶段路线

### R0：provenance、质量门和源闭合基础

**目的**：在不清理或重置 dirty tree 的前提下，建立可恢复基线、候选来源边界和唯一质量口径；最终 release source set 延后到 R4。

**工作**：

1. 记录当前文件/变更/历史摘要及用户改动映射；运行前先固定 RED 基线，不把脏树归因给单一 worker。
2. 建立唯一 gate：`ruff`（`src tools tests`）、`mypy --strict src tools`、unit/contract 测试和 legacy reference scanner；范围写入 metrics。
3. 为 bundle provenance、manifest、catalog、case、source commit 和 release-scope 建立摘要绑定；dirty tree、source mismatch、未知字段和缺失 required content 必须失败关闭。
4. 显式定义候选来源边界；R2–R4 完成后再从 clean commit 生成最终 HTML-only release source set。运行日志、缓存、凭据、临时目录、旧运行时和未批准归档排除。
5. 将治理工具与安装运行时分开；切换/删除工具的摘要可以进入 RC governance record，但不进入安装 bundle。
6. 建立逐文件哈希的外置只读恢复快照；每个后续里程碑盘点新增空间，只精确清理已被摘要/哈希替代且可再生的缓存、临时件和失败测试副本。

**边界**：不读取、修改或校验真实旧根；不创建 RC commit/tag；不将局部测试绿色写成全仓 gate 通过。

**退出证据**：不可变 inventory、外置快照 receipt、gate 全量输出/digest、候选来源边界、dirty fail-closed 测试、用户变更保留说明。

### R1：canonical 设计、路线和 Task 10.6 合同

**目的**：把用户批准决策和 ZCode 审计建议变成单一规范，阻断 v1.2/ZCode/Task 10.6 三重漂移。

**工作**：

1. 发布自足的 `competitive-intelligence-workflow-design-v1.3.md`；v1.2 仅按 v1.3 附录 C 明确纳入的兼容条款继续生效，不作为平行规范。
2. 发布本 canonical roadmap 和 `codex_execution_ci-rebaseline-rebuild-v3.md`。
3. 发布一份 ZCode disposition review，逐项标明采用、修改、拒绝和理由；保留 ZCode 输入原文不改。
4. 同步 Task 10.6 `prd.md`、`design.md`、`implement.md`：HTML-only、24 门户、三宿主、手动刷新、Yaozh/manual gate、Q1–Q6、旧根边界、RC signals。

**退出证据**：文件路径、版本、scope、权威顺序、阶段门、Q1–Q6 和 v1 非目标在四组文档中可互相追溯。

### R2：typed multi-Skill、来源和证据门槛

**目的**：实现一句话自主研究 → typed research-package → 确定性事实/门槛链。

**工作**：

1. 公开入口 Skill：中文触发词“竞品调研”、最小输入、能力边界和非技术中文修复指引；未指定报告类型时用宿主原生 Ask 解释 A/B/C 并让用户选择，可选历史截止日，每个新项目只询问一次是否具备 Yaozh 访问条件；用户可选传 package。
2. package schema 严格校验；未知字段、非法状态、身份歧义、内部 locator、凭据和摘要不匹配失败关闭。
3. 实现本体/竞品宇宙全量关闭、组件/方案 eligibility、研究角色和来源角色分离；全球/中国必查来源以及别名、靶点、企业、试验反向扩展必须逐项有回执，独立 closure review 先于门槛。
4. 实现 registry-linked primary、extension、关键长期/安全发表物的来源任务；Yaozh 只作 optional browser-assisted 商业来源。
5. 实现一次 manual-supply Markdown gate、内容识别、投递目录原地规范重命名、操作前原名/SHA-256/DOI/登记号/新名映射、无字节修改和碰撞防护，以及用户单次响应规则。
6. 实现 GateSpec、typed missing states、冲突链、两条替代恢复检索、clean-context final review、blocker audit 和 no-draft。核心问题仍可回答时带限制交付，核心问题不可回答时只显示简洁证据不足页并保留内部审计包；可选空模块省略或一句话说明，不生成空坐标轴或固定零值占位。
7. A/B/C 门户统一采用 post-format 两阶段科学复核：review request 绑定生产上下文、事实谱系和门户实际字节；只有 `review issue` 产生的 receipt 与 issuance record 同时通过、正式 verdict 未过期时才晋级。允许任意次纯复用 resume，并按来源边验证运行谱系；不以研究包自审或固定两次运行替代独立复核。

**退出证据**：schema/contract 测试、来源回执和缺口账本、正负门槛用例、关键 absence/zero 恢复记录、manual gate 恢复记录、独立 review verdict。

**2026-09-05 进展**：已实现项目合同到类型化自主研究任务、报告专属来源路线和
完成条件；新增严格 `research submit`，用通用审计信封的 SHA-256 绑定 A/B/C
专属科学载荷，并使产品 CLI 拒绝松散 `report-data.json` 和未绑定载荷。来源
schema/model 漂移已修复，非论文来源不再伪装成主要结果论文。产品运行现可按同一
提交合同生成多个彼此独立的报告门户，共享节点按输入摘要隔离复用；项目级
`yaozh answer` 已实现一次回答、同值幂等和篡改/改答失败关闭；三态回答现已接入
来源计划与宿主能力预检：仅 `available` 启用 `required=false` 的已登录浏览器辅助
路线，`unavailable/skipped` 记录非阻断 `not_applicable`，会话失效只形成绑定回答
摘要并提示自行登录的类型化可选访问回执。来源政策 1.1 保证药智最多用于线索和交叉核验。B/C 双重穷尽后的
阻断决定现可发布、校验并重复恢复。A/B/C 渲染现采用共享未发布事务：无绑定
中断残留可按当前版本精确恢复，任何产物、运行或科学复核绑定都拒绝覆盖。
核心能力矩阵现已接入产品运行门：每次首次/恢复运行真实重检并原子保存
`capabilities/preflight.json`；研究能力缺失在来源任务前以独立结局停止，HTML
浏览器验收能力单独缺失则保留研究结果但阻止 format，药智登录单独缺失继续核心
路线。回执软链接、非普通目标、读取副作用和复用探针缓存均有负向/恢复测试。
Yaozh 浏览器抓取器和真实会话探测尚未实现，真实三宿主入口和 R2.4 整体闭包仍未完成，
不得据此进入 RC。

**2026-09-05 R2.2 更新**：竞品宇宙闭包合同已接入严格研究提交和产品运行：全球/
中国路线与四类反向扩展使用类型化真实回执，技术失败与真实零发现分离，最后连续
两轮零新增才可收敛；实体纳排、本体规则、来源策略、项目/截止日和候选字节进入
独立复核摘要。A/B/C 共享一个项目级 universe identity，不再按报告包各自造宇宙。
因此“R2.2-R2.4 整体闭包”中的 R2.2 已完成；该时点 R2.3 与 R2.4 尚未完成。

**2026-09-05 R2.3 更新**：Publication/manual-supply 产品门已闭合。正式裁决、
跨两个路线家族的获取尝试、逐纳入试验检索回执、独立复核、单快照单用户门、错文件
恢复、扫描件 OCR 交接、accepted replacement、受影响报告局部恢复，以及不可得后的
带限制继续/证据不足终态均已进入严格提交与产品运行。执行审计、独立会商、全 integration、
bundle/fresh-install 和全仓开发门通过。Yaozh 真实浏览器抓取与会话探测仍是独立未完成项；
R2.4 逐对象 GateSpec/blocker audit 仍未完成，均不得由本更新推定为完成。

**2026-09-06 R2.4 更新**：除新鲜度产品口径外，逐对象 GateSpec、候选宇宙锁定、恢复
信息增益、独立遗漏复核、专用 blocker 与 no-draft 产品链已通过 Codex 实际运行、两轮
独立代码会商、全产品链、全仓开发门和 fresh-install/bundle 校验。新鲜度模型、默认窗口
与历史截止日行为必须由用户通过原生 Ask 裁决，因此 M2/R2.4 尚不关闭；Yaozh 实际浏览器
和三宿主实机仍按各自后续里程碑验收，不作为本切片的伪阻塞或伪完成项。

### R3：A/B/C 数据合同和分析

**目的**：把已接受事实投影成三个不互相依赖的报告模型。

**A**：全量创新药产品、开发/监管/企业/专利和结果披露状态；result-bearing 项目最低疗效/安全记录，不删除失败或稀疏项目。主要图形覆盖管线全景、靶点—产品关系、阶段矩阵、地域状态时间线、疗效比较、安全热图和多维气泡图；不得只展示明星产品。

**B**：核心结果试验的疗效、安全性、基线、人群、处置；基线分组、统计形式、分母和披露状态严格建模；语义分组模型候选必须经确定性兼容守卫；无跨试验池化、默认排名或自动研发建议。气泡图固定使用疗效×总体安全性、疗效×严重风险、持续性×停药风险三组临床预设及其指定样本量/暴露量大小语义。

**C**：登记优先设计事实、完整入排条目、剂量/疗程/终点/时间/样本量；主要图形覆盖设计模式地图、试验时间轴、终点—时间窗矩阵、入排主题、组别结构和方案差异；只输入适应症时形成证据支持的多路径，不输出唯一最佳方案。

**共同**：每个结构化数据集都有适当图和完整折叠表；叙事/缺失解释用状态或文字；保存原始表达、规范化值、来源定位和声明关系。

**退出证据**：A/B/C GateSpec 通过/阻断/空宇宙测试，数据合同和冲突测试，B 48/50 周近窗口与不兼容拆分测试，C 多路径测试。

### R4：三个独立 HTML 门户

**目的**：在站点式 HTML 中完整呈现 A/B/C，而非将源码或数据状态泄露给读者。

**工作**：

1. A landscape console、B evidence comparison room、C design atlas 各自页面族；至少两个互通物理页面。
2. 图先表后、默认收起且原位展开的完整表格、全局搜索、跨页下钻、分层筛选、URL 状态、可选证据下钻、每页底部一个聚合外部来源区；默认首屏不显示工程阶段、Gate、提示词或内部字段。
3. 率值/零/未报告/未公开/技术不可用/访问受限/冲突等状态有不同中文呈现；表格无内部路径和 locator。
4. 安全热图、纵向图、基线图、处置图和设计图形按合同选择；不添加雷达图、证据成熟度视图、CSV/XLSX 导出。
5. file:// 与静态服务器可运行；离线本地资源；Logo、响应式、键盘和 reduced-motion 合同。
6. 所有物理页面在 Chromium/WebKit 覆盖桌面、平板、手机、窄屏四类视口（至少 1440×900、1024×1366、390×844、320×568）；整站路由、长表、筛选、证据下钻、空状态、中文可读性、遮挡和溢出均需证据。

**退出证据**：A/B/C 页面清单、coverage_set/projection、实际浏览器截图/日志、无障碍和控制台/链接检查、独立视觉 verdict。

### R5：安装包、三宿主、刷新和恢复

**目的**：证明最终用户得到的是可安装 Skill 包，运行/恢复不依赖源码 checkout、旧 receipt 或中心服务。

**工作**：

1. 构建 HTML-only bundle；包 manifest 实际列出 scope、schema、合同摘要、source/RC identity 和 required content。
2. Codex/Hermes/OMP fresh-install；公共关键词入口、能力预检和错误中文指引一致。
3. 用户手动触发后自动完成来源复核、immutable latest/diff 和受影响页面重建；不得安装/分发/运行 scheduled monitoring 或后台轮询。
4. recovery-package-v1 只含当前 RC、批准迁移资料、清单、验收记录和恢复所需输入；不含旧可运行流水线。
5. 让默认执行器仅凭规范 events/checkpoints 打开、恢复、刷新和代表性 HTML 重建；可选运行时缓存可移除。

**退出证据**：bundle/installation manifest、三宿主真实入口回执、manual refresh diff、recovery rehearsal receipt、秘密/绝对路径/远程依赖扫描。

### R6：真实来源矩阵、独立验收和 Task 10.6 冻结

**目的**：以新鲜来源、新 IDs 和最终安装入口完成 24 门户及 RC 冻结，不把历史结果伪装成当次通过。

**工作**：

1. 在全新 release root 对八个适应症分别生成 A/B/C；完成研究包、宇宙关闭、来源门槛、科学 QC 和门户视觉检查。
2. 只接受 final bundle、final source/RC identity、当次 run/job/session/artifact/verdict；所有旧摘要和旧 receipt 明确拒绝。
3. Task 10.6A 完成 provenance/recovery 负向测试；10.6B 完成 source closure、Phase 0–10 回归和唯一 RC commit/tag；10.6C 完成 bundle/fresh-install/24 门户/三宿主；10.6D 完成恢复、owner-stage receipts 和独立 verdict。
4. 只有 Codex 在所有门均通过后写 `RC_FROZEN`；`pending_future=1` 只保留 `legacy-absence` future owner，不提前访问真实旧根。

**退出证据**：每门户门槛/科学/视觉证据、full-matrix closure、owner-stage receipts、recovery receipt、最终报告和 freeze record。

---

## 4. Task 10.6 同步契约

### 4.1 Q1–Q6 固定裁决

| 问题 | canonical 裁决 |
|---|---|
| Q1 RC identity | `release_candidate_sha256 = sha256(canonical_json({schema_version, source_commit, bundle_sha256, package_manifest_sha256, catalog_sha256, release_scope}))`；Git commit 可以是 SHA-1，不能冒充 SHA-256。 |
| Q2 receipt 层级 | 保留 pre-RC `host-receipt` 和 acceptance root 的 final owner-stage `release-case-receipt` 双层；freeze record 显式绑定二者，不强行改写 catalog 指针。 |
| Q3 future owner | `legacy-absence` 是唯一 `pending_future`；当前 Task 10.6 不对真实旧根做任何检查。 |
| Q4 治理工具 | cutover/legacy 工具是仓库治理 sidecar；摘要进入 RC governance record，不进入可安装运行时 bundle。 |
| Q5 两个入口 | 产品运行来自安装 bundle；治理 verifier 来自 clean RC worktree；receipt 绑定同一 RC identity。 |
| Q6 formats | 由当次 A/B/C HTML artifact manifests 实际计算；v1 结果必须为 `formats=1`，禁止硬编码。 |

### 4.2 冻结信号

```text
RC_FROZEN reports=3 formats=1 hosts=3 recovery=passed pending_future=1
```

发布状态只保留 `DEVELOPMENT_CANDIDATE → RC_FROZEN → RELEASED`。冻结信号输出前必须有 P0/P1=0、P2 repair 或 evidence-backed non-impact disposition、24 门户矩阵 closure、三宿主回执、恢复演练、科学/视觉/包/恢复独立 verdict。信号不是测试脚本退出码的别名；Task 10.6 不得输出 `legacy_absent=passed`。

---

## 5. 质量、并行和停止条件

### 5.1 检查顺序

每个代码任务遵循 RED → 最小 GREEN → focused contract → 相邻回归 → gate → 提交/来源闭合。执行代理可以并行处理不同文件所有者；共享合同先由 R1 固定。任何 worker 报告必须说明检查范围、命令、输出摘要和未运行项，不能把局部测试写成全仓通过。

### 5.2 停止条件

以下任一情况立即停在当前检查点：

- source set、bundle、catalog、case、manifest、receipt 或 RC digest 绑定不一致；
- dirty tree、未知字段、缺 required content、旧 ID/receipt、非法状态迁移未被失败关闭；
- 竞品宇宙未独立关闭，关键缺失/异常零值缺少两条替代恢复或 clean-context 复审；
- 必需论文/附件不可访问但 manual gate、单次用户响应或官方证据充分性未记录；
- B 语义分组跨越不兼容尺度、方向、估计目标、分母或分析集；
- 页面使用了内部路径、缺少完整折叠表、图表与表格不是同一事实集，或浏览器实际溢出/键盘失败；
- P0/P1 存在，P2 未修复且无明确非影响处置；
- 任何人提出以旧根、旧 receipt、旧截图、局部测试、文件存在或 `ok=true` 替代当次证据；
- 需要读取/修改真实旧根或进行发布/删除，但尚无独立授权。

失败时保留源、摘要、日志、部分回执和下一合法动作；不得 reset、clean、覆盖用户改动或静默缩小范围。

### 5.3 后续版本和旧根

首版 RC 后的 PDF/PPT、表格导出、雷达、证据成熟度和监测均是未来版本候选，不属于当前路线的隐含待办。真实旧根切换、删除和 absence closure 另行受控：新系统须先完成至少三个覆盖 A/B/C 的真实项目，用户触发刷新、历史差异、恢复和三宿主运行通过，严重缺陷清零并具备可验证回滚；随后再次取得用户明确批准，才可建立精确 inventory 并执行退役。本路线和 Task 10.6 不提前触碰它。
