# 工程设计：复用现有系统，统一真实数据链（0923V1 桌面修订）

本文件规定足够实施的边界，不要求为每个概念新建服务、Skill或文件。生产实现以完整定义/调用方为准，不迁移语言或前端框架。

## 1. 最小架构

入口/预检 → 合并SourcePlan → 获取/抽取/独立遗漏复核 → 来源版本/精确片段/事实版本 → 关系与语义裁决/派生 → 查询/成员集合/分面/数值资格 → A/B/C独立门户 → 候选/独立审阅/浏览器 → 当前交付与离线分享。

用户保存 → expected_revision → 新事实 → 影响闭包 → staging重建 → 实际字节与闭包校验 → 原子current。

公共事实是唯一数据真源，门户仍为三个独立产品。单独生成A、B或C不依赖其他门户先生成。

## 2. 复用与必要改动

| 现有组件 | 继续承担 | 补齐 |
|---|---|---|
| cli/intake/ProjectContract/capability_preflight | 入口、Ask、能力状态 | 两输入模式同合同；真实独立上下文探测，不能StaticCapabilityProbe冒充 |
| RunContext/run_service/typed_skills/executor | 工作区身份、控制图、失败恢复 | 合并SourcePlan、输入显式化、脱离PNH和/tmp；更新过时C完成条件 |
| sources/publication_manual_gate/source_research_service | 获取、政策、补件 | 新鲜度、历史cutoff、获取尝试和闭包真实回执 |
| domain/facts + CAS/SQLite | 原始证据、事实版本 | 全科学context内容身份、精确定位重提取、引用闭包及迁移 |
| review_issuer/scientific_review_transition | 请求、实际签发、接受 | 生产者不能自签；首次/刷新/修订一致；缺签发fail closed |
| reports/common/view_state | 稳定row/事实/页面投影 | 公共查询/配置、跨页联动与修订再投影 |
| reports/b/semantic_* | 医学归并和边界 | 相关性、分面、数值资格分层；反例覆盖实际消费者 |
| reports/c/* | 实例、观察、原文 | 角色/组/期身份统一、完整DesignClause索引，取消强制方案生成 |
| graph/impact + CorrectionService + render_transaction | 影响分析、事件、原子渲染 | 派生fact依赖、跨报告revision、用户保存与独立接受分开 |
| portal/builder/assets/templates | 三门户/资源 | 单一作者来源、typed数值投影、配置/编辑/分享 |
| bundle/fresh_install/host_smoke/acceptance | 安装、宿主、恢复 | HTML-only清单、实际运行字节、脱离开发目录 |

必须修完整调用链；新helper通过而实际门户仍用旧fallback，不算完成。

## 3. 身份、查询与派生

### 来源和事实

source_id是逻辑来源，source_version_id绑定真实字节和必要元信息。获取attempt独立于content：本次核查同字节也有本次回执；网络失败有失败记录但不称已确认新鲜。同次请求重放幂等，不把旧attempt_index=1无限沿用。
fragment绑定来源版本与精确locator：JSON索引/字段、表/行/列、PDF页/段/表。original_quote来自实际原始对象，不能生成“某行登记事实”。规范值/翻译另记derivation。历史粗片段保留但不得伪装已逐条核验。
登记结果的原始数值和分母分别是可按字段路径重提取的原子事实；`n/N` 形成的显示比例是派生输出，不能把比例文本写成来源直接原文。原子事实版本应保留类别、试验、组别、终点、时间和数值角色；已有来源事实未带这些扩展字段时保持原有序列化/历史身份。缺少 `numAffected` 只产生待核问题，不得由 `numAtRisk` 合成原子零值。原子事实入库只是门户逐事实闭包的前置步骤，仍须显式报告行绑定、派生输入与公式、来源区和快照恢复。
0924V1 增量：采集器先保存完整候选，不由两个解析器独立裁决分母；同组的 N 还须比较统计单位、测量实例、class/category、分析人群和期别。相同 N 只有上下文一致才可复用，冲突集合与每个 locator 均保留，比例拒绝派生。单原子缺失/解析失败/语义冲突分别记 scope+reason，不能扩大成整测量丢失；0/0 是两个真实零而不是 0% 风险率。来源的 domain 与 metric 分开：`efficacy / adverse_events / immunogenicity / pk_pd / biomarkers / other / unresolved` 为轻量标签，不加大本体，科学类别由统一语义函数决定，A/B/C 使用同一结果而各自筛选展示。ADA 阳性不等于 AE 或临床疗效。
FactVersion内容身份包含完整科学上下文；显示标签不能当主身份，同值不等于同事实。计划N/实际N、组期、人群、终点实例/角色分别保存；不可依赖field后缀或数组顺序。
`SourceFactVersion` 的科学摘要排除 report/page/row 引用；`ConsumerBinding` 将一个版本映射到 A/B/C 合法行。兼容旧只读 v2 摘要与新 v3 身份，旧快照不补签不迁移为新 accepted。同一原子新增消费者不制造冲突；改原值/来源版本/人群/时间才使科学版本变化。研究—产品和结果组别通过显式 arm–intervention 关系投影，缺关系为 unknown。

### 派生DAG

最小派生记录：输入fact版本集合、算法/规则版本、参数、输出、单位、公式与适用范围。n/N粗率与来源调整率不同，只有明确公式自动重算；编辑n/N不能覆盖LS mean/调整率。
当 B 疗效领域行与来源 view 使用不同 row ID 时，必须由显式 `source_view_row_id` 连接，并逐项核对产品、试验、终点、组别、人群、单位、原值和分母；缺失或错指针失败关闭。`value_basis` 是类型化的粗率/模型估计/报告估计依据；有分子分母不自动意味着展示百分比可由 n/N 重算。历史夹具不因新增合同改写冻结字节，实际研究包须在提取与裁决阶段补齐这些字段及其来源证据。

B 疗效展示投影必须保持报告值、计数与统计依据三个概念分开：模型/报告估计值在图上使用报告值，原始分子分母只作并列事实，不参与重算；声明粗率但与 n/N 不符时拒绝。估计值保存若改变计数，必须同时提交重新核实的当前估计文本和规范值；单独更新一个估计表示也拒绝。用户修订披露以实际可见来源 view 行 ID 索引，但 binding 仍保持领域身份；同一当前 revision 中旧修订保留各自 request/revision。来源名称只能取已明确记录的版本标签，不能把未知来源硬标为 ClinicalTrials.gov。当前历史 PNH 合成样本只能证明投影/事务行为，不能代替精确原文与来源版本闭包。
叙事、医学裁决、分面也记录依赖，输入变则失效。扩展既有impact边，检查无环/无悬空/同revision；不引入graph DB。manifest闭包含被引用source_versions、fragments、facts、derivations、规则、产物和审阅证据。只用manifest在空目录恢复必须可追溯。

### 共享查询与ViewState

三层不可混淆：WorkspaceMembership保留全部相关研究/观察；FacetPlan按人群/终点/统计/时间分面；NumericFrameEligibility决定同轴资格。不可比较不能删除成员。
共享图形的 `comparison_context_id` 由研究、结局实例、人群、分析集、期别、访视/区间等已证明字段组成，再按明确 arm 拆系列；未知关联保持独立面板或未绘制原因。不得以跨系列第 n 次出现、数组顺序、标题相似或数值接近拼成伪对照。PresentationPlan 继续作为唯一几何合同，筛后 1/2 个观察应重新选择紧凑形态，同时保留图例/缩放/焦点与原查询身份。
查询集Q=可绘P∪不可绘U且不相交；图形可多事实→一个点，但点须保存输入集合。不要强行一事实一气泡。
ViewState含schema/revision/report/page、query/filter、selected item、合法字段/分面/布局、视觉状态、返回焦点/滚动。图例隐藏/缩放与研究筛选不同，不从DOM反推事实，不建立任意代码查询DSL。
复用已打包ECharts dataset/encode适用部分；科学资格先于图库。关系图/树/时间轴不强制一种组件。[官方dataset文档](https://echarts.apache.org/handbook/en/concepts/dataset/)只支持数据与配置分离，不能替代医学判断。

### 0923V1 桌面 PresentationPlan 与图形边界

只开发桌面宽屏；以 1440/1600/1920/2560 CSS px 为四档真实浏览器门。统一 Shell 工作区与几何 token，但保持 A 景观、B 临床问题、C 设计先例各自的信息架构。当前 A 的 1760、B 的 1440、C 的 1180 最大宽度是待统一的旧规则；先查实际模板和消费者，再使桌面工作区流式使用可读空间，长段正文维持短行。12 列逻辑栅格和 4/6/8/12 跨度、约 2240px 超宽上限、y≤280px 核心起点只是待浏览器校准的默认工程值，不是放宽科学内容或隐藏限制的理由。证据侧栏打开时以分析区可读宽度决定并列还是抽屉。

在现有 `ReportQuery/ViewState` 上加入最小 `PresentationPlan`，输入由当前查询和科学投影产生：query digest/revision、facet/NumericFrame、全部 fact/observation ID、可绘制与未绘制理由、实体/观察/glyph/series 数、标签长度、统计形式/单位/值域和布局模式。输出为表达 kind、grid span、目标绘图区宽高及上限、AxisPlan 与选择理由。单观察默认为紧凑事实行，2–4 个同框观察为小型配对，复杂矩阵与全量表才占整行；无数值时展示真实原因和全量入口。A CSS 条形与共享 ECharts 读取同一表达决策，不能仅改变 `barMaxWidth` 或用更高优先级 CSS 遮盖旧宽度规则。

AxisPlan 由统计形式和科学资格决定，不仅由单位决定。受试者比例可用 0–100，变化百分比和有符号差值不得被 `%` 统一封顶；小数采用与数据量级相称的刻度。显式轴域也须覆盖有效数据。一个 NumericFrame 的多面板同域，不同语境明确标为独立尺度。真实零保留零，缺失、未报告、冲突、解析失败各有独立披露状态。共享层必须把“未绘制”与“未公开”分开，不让各报告层重复补造状态。

所有相关 facet 可见或可操作选择，计数和不可同轴原因可查；默认选择次序稳定且保存，不从 `points[0]` 决定。相同 category+series 下的多个不同观察保留独立 glyph、显式可追溯汇总，或给出解释性冲突，不能 first-wins。图形选中以 fact/observation ID 建立一对多目标索引，所有可见 glyph 与表行同步；单次动作只开一次正确证据。Escape 回实际触发者，若触发 DOM 已因分页/重排消失则回同事实或列表的稳定锚点。图形事件或实际 glyph 几何用于命中，不以固定 30px 偏移猜测；容器变化后 `ResizeObserver` 或等价机制触发 resize/重建映射，dispose 清除旧实例与事件。

旧“首页初始 DOM 必含全量疗效行”迁移为数据全量和可验证可达：分页/虚拟化的总数、范围、稳定 ID 并集、最后一条搜索和返回位置均要测试；替代测试先落地，再退出旧实现细节断言。安全呈现默认密集对照，热图仅在同事件定义、统计对象、时间/分析语境和单位可比时使用；同值同色、零与缺失区分、来源正确。固定颜色种数断言退出，科学约束保留。

## 4. 安全数值与C实例

分母输入保存source version、study、module/measure、原始group、期别、分析人群、窗口、统计对象；跨模块采用需明确关系与理由。标题只给候选、同N只校核；来源确有分母但模型丢字段时修提取，不全部设unknown掩盖缺陷。otherNumAtRisk不能泛化到任意复合TEAE。
Safety保留polarity、seriousness、TEAE、relatedness、grade集合/关系、父子测量及measure_object；未知原文仍可查。数值投影含原值/规范值、单位/方向、分母来源、公式、对照对象、时间、大小口径和不可绘理由。前端轴域取投影后实际值，无对照不做差值，未知治疗N不冒称治疗N。

用户 2026-09-23 裁决：ClinicalTrials.gov 不良事件统计中的 `numAffected` 缺失，即使同组 `numAtRisk` 存在，也只能记“未知，待核”，保留精确来源路径并触发恢复，不得解释为 0、生成零事件或零风险率。只有原始记录明确给出数值 `0` 才可标为真实零。历史载荷中由字段省略推断出的零值须在 W07 重提取时复核；旧审计 PASS 不能沿用。

C身份区分研究/方案版本、outcome_id、角色、组/队列/期别、时间语义；同ID矛盾要显式。全universe逐研究记录已有/缺失/冲突，每个终点时间独立校验。按显式arm–intervention关系建给药，不能一律arm1。
DesignClause为受限条款结构：原文/译文、母子关系、AND/OR/NOT/例外、阈值/单位、适用条件、主题、来源/版本。检索同义不等医学等价；母句完整可展开。无需通用NLP本体或新向量数据库作为必需依赖。

## 5. 修订事务与接受语义

用户显式保存即保存授权，不加新人工审批：
1. 校验typed修改、目标身份、expected_revision、幂等request_id。编辑补丁有省略/设置/清除三态；仅字段白名单可清除。清除数值的当前层语义固定为“用户清除，待重新核实”，原来源数值继续可查，依赖派生失效；不得转写成来源未公开，`reported_value + null` 不得并存。
   数据库存储的 `fact_versions.disclosure_state` 保留原来源披露口径；显式清除写入 append-only 用户修订上下文，`_public_fact` 合成有效当前状态 `user_cleared`。来源事实模型和旧数据库枚举不得接纳 `user_cleared` 作为原来源状态；报告图、表、索引、证据抽屉均消费有效当前状态，同时在原来源字段保留旧值和定位。清除任一数值核心字段时，同一当前版本清除关联分子、分母、阈值和派生结果；不完整恢复必须失败关闭。此分层避免为用户层操作重建带外键的历史事实表。
2. 追加user_modified事实/事件；源字节和旧quote不改，保留用户依据。
3. 计算派生/消费闭包，staging重建所有实际绑定的A/B/C图、表、文字、索引和引用。以同一真实逻辑事实合法绑定 A+B 的正向测试证明一次保存的扇出；C 仅在确实引用时重建。未生成的报告不必凭空生成，但后续必须消费新事实。
4. 验证实际文件hash、所有受影响页面、来源闭包、无混版和集合守恒。
5. 成功才原子切current，失败旧current保持；重试不重复版本，撤销追加历史版本。
6. 旧独立接受只属旧revision；新用户修订可读/分享但明示未独立复核。自动未审候选不能冒充正式完成。

复用CorrectionService的事件/冲突/历史，不直接套现有owner审批→独立QC流程到每次用户保存。正式科学接受另行执行。开发候选/RC_FROZEN/RELEASED是发布状态，review_state是正交内容状态。
刷新三方比较base source / user current / new source：源未变留用户修改；用户未改而源变生成更新；双方改同字段显式冲突；保留撤回历史但正确移出有效比较。diff展示事实及来源变化，不只是文件差异。

## 6. 本地编辑与离线分享

按需loopback服务，默认127.0.0.1；严格Host/Origin、会话/CSRF、限定资源ID、路径/symlink、导入类型/大小；拒绝file/null任意Origin、通配CORS、任意shell/路径。
分享从current生成，非旧HTML+patch。闭合本地JS/CSS/图标/合法数据/配置，不把file:// fetch JSON作为必需条件；可内嵌或本地script分片。离线源外链可显示元信息和合法摘录，受限原文不承诺离线可得。
分享不含凭据、绝对路径、商业全文、开发源/日志；Skill安装包和报告分享包不同。配置严格schema和版本迁移，不执行函数/HTML。配置中的 revision 绑定当前交付包内**所选报告的实际页面版本**，项目 current revision 另存于分享清单；未受事实修订影响的 C 可保留旧页面版本并从该页面原样导出配置，不强行重渲染或伪改版本。机器ID可以保留绑定但不放用户字段墙。
模块assets建议作为唯一作者来源；根副本若仍有其他轨消费者，通过构建同步。先查实际消费者再统一，不用改hash掩盖漂移。

当前 W00 已确立 `src/ci_workflow/renderers/portal/assets` 为唯一作者源，根 `assets/portal` 为发包镜像；构建前逐字节与 manifest 校验，不恢复双作者模式。分享包默认直接显示 current generation 的修订事实和配置，不依赖原浏览器 localStorage、旧绝对路径或手工 patch；单 A/B/C 与联合包都需在新浏览器、移动目录及断网环境实际打开。

## 8. 0923V1 实施边界与并行关系

D1 桌面 Shell/PresentationPlan 与 D3 共享交互由一个共享接口所有者合并；D2 科学图形/facet 接其计划。W07 真实来源闭包可与桌面结构并行：先选多组、多期、零值、缺失、多终点和复合安全类别的小批真实记录，贯通原始 source version→精确 locator/原文→事实/派生→snapshot→页面，再扩到当前 4412 条采用事实。未定位须区分原始来源缺失、解析失败和已有来源未映射；报告级来源列表不能代替事实级闭包。W04 同时补三态编辑和合法 A+B 扇出。A/B/C 在共享接口稳定后各自推进桌面布局，不排队等另一门户全验收。任何新作者源字节导致旧截图或浏览器收据失效时，只重验受影响闭包；历史报告保持原样。

## 7. 迁移和范围

旧快照不重写成新规则已接受，只读兼容或新派生候选。CAS去重不移走仍被引用字节。源不够就限制结论，不能造字段通过。
优先标准库及既有组件；新依赖记录必要性/许可/离线成本。本轮不加云账户、多租户、PKI、通用DSL、新数据库/图引擎、全UI框架迁移。W00确定schema双副本策略；W08以实际安装验明。
