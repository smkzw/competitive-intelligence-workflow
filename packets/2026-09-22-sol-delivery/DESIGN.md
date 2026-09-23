# 工程设计：复用现有系统，统一真实数据链

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
FactVersion内容身份包含完整科学上下文；显示标签不能当主身份，同值不等于同事实。计划N/实际N、组期、人群、终点实例/角色分别保存；不可依赖field后缀或数组顺序。

### 派生DAG

最小派生记录：输入fact版本集合、算法/规则版本、参数、输出、单位、公式与适用范围。n/N粗率与来源调整率不同，只有明确公式自动重算；编辑n/N不能覆盖LS mean/调整率。
叙事、医学裁决、分面也记录依赖，输入变则失效。扩展既有impact边，检查无环/无悬空/同revision；不引入graph DB。manifest闭包含被引用source_versions、fragments、facts、derivations、规则、产物和审阅证据。只用manifest在空目录恢复必须可追溯。

### 共享查询与ViewState

三层不可混淆：WorkspaceMembership保留全部相关研究/观察；FacetPlan按人群/终点/统计/时间分面；NumericFrameEligibility决定同轴资格。不可比较不能删除成员。
查询集Q=可绘P∪不可绘U且不相交；图形可多事实→一个点，但点须保存输入集合。不要强行一事实一气泡。
ViewState含schema/revision/report/page、query/filter、selected item、合法字段/分面/布局、视觉状态、返回焦点/滚动。图例隐藏/缩放与研究筛选不同，不从DOM反推事实，不建立任意代码查询DSL。
复用已打包ECharts dataset/encode适用部分；科学资格先于图库。关系图/树/时间轴不强制一种组件。[官方dataset文档](https://echarts.apache.org/handbook/en/concepts/dataset/)只支持数据与配置分离，不能替代医学判断。

## 4. 安全数值与C实例

分母输入保存source version、study、module/measure、原始group、期别、分析人群、窗口、统计对象；跨模块采用需明确关系与理由。标题只给候选、同N只校核；来源确有分母但模型丢字段时修提取，不全部设unknown掩盖缺陷。otherNumAtRisk不能泛化到任意复合TEAE。
Safety保留polarity、seriousness、TEAE、relatedness、grade集合/关系、父子测量及measure_object；未知原文仍可查。数值投影含原值/规范值、单位/方向、分母来源、公式、对照对象、时间、大小口径和不可绘理由。前端轴域取投影后实际值，无对照不做差值，未知治疗N不冒称治疗N。

C身份区分研究/方案版本、outcome_id、角色、组/队列/期别、时间语义；同ID矛盾要显式。全universe逐研究记录已有/缺失/冲突，每个终点时间独立校验。按显式arm–intervention关系建给药，不能一律arm1。
DesignClause为受限条款结构：原文/译文、母子关系、AND/OR/NOT/例外、阈值/单位、适用条件、主题、来源/版本。检索同义不等医学等价；母句完整可展开。无需通用NLP本体或新向量数据库作为必需依赖。

## 5. 修订事务与接受语义

用户显式保存即保存授权，不加新人工审批：
1. 校验typed修改、目标身份、expected_revision、幂等request_id。
2. 追加user_modified事实/事件；源字节和旧quote不改，保留用户依据。
3. 计算派生/消费闭包，staging重建关联A/B/C图、表、文字、索引和引用。未生成的报告不必凭空生成，但后续必须消费新事实。
4. 验证实际文件hash、所有受影响页面、来源闭包、无混版和集合守恒。
5. 成功才原子切current，失败旧current保持；重试不重复版本，撤销追加历史版本。
6. 旧独立接受只属旧revision；新用户修订可读/分享但明示未独立复核。自动未审候选不能冒充正式完成。

复用CorrectionService的事件/冲突/历史，不直接套现有owner审批→独立QC流程到每次用户保存。正式科学接受另行执行。开发候选/RC_FROZEN/RELEASED是发布状态，review_state是正交内容状态。
刷新三方比较base source / user current / new source：源未变留用户修改；用户未改而源变生成更新；双方改同字段显式冲突；保留撤回历史但正确移出有效比较。diff展示事实及来源变化，不只是文件差异。

## 6. 本地编辑与离线分享

按需loopback服务，默认127.0.0.1；严格Host/Origin、会话/CSRF、限定资源ID、路径/symlink、导入类型/大小；拒绝file/null任意Origin、通配CORS、任意shell/路径。
分享从current生成，非旧HTML+patch。闭合本地JS/CSS/图标/合法数据/配置，不把file:// fetch JSON作为必需条件；可内嵌或本地script分片。离线源外链可显示元信息和合法摘录，受限原文不承诺离线可得。
分享不含凭据、绝对路径、商业全文、开发源/日志；Skill安装包和报告分享包不同。配置严格schema和版本迁移，不执行函数/HTML。机器ID可以保留绑定但不放用户字段墙。
模块assets建议作为唯一作者来源；根副本若仍有其他轨消费者，通过构建同步。先查实际消费者再统一，不用改hash掩盖漂移。

## 7. 迁移和范围

旧快照不重写成新规则已接受，只读兼容或新派生候选。CAS去重不移走仍被引用字节。源不够就限制结论，不能造字段通过。
优先标准库及既有组件；新依赖记录必要性/许可/离线成本。本轮不加云账户、多租户、PKI、通用DSL、新数据库/图引擎、全UI框架迁移。W00确定schema双副本策略；W08以实际安装验明。

