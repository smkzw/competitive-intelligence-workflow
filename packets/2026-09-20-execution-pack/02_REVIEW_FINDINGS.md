# 增量代码审阅清单与证据边界

固定基线：`d6cb6d51e1b5a5e2abdacea485ea84b5268dc7ca`。GitHub main 本轮核对仍为该提交。

本轮读取重点覆盖共享摄取、事实模型、修订/发布、影响传播、C构建/输入门槛、安全分类和运行时前端资产。未取得完整可执行 checkout；未运行全仓测试、完整生产研究、三宿主安装验收或真实A/B/C浏览器验收。不得将本文称为全量发布审阅通过。

P1 表示需要在本次功能交付前处理的科学正确性/完整性/核心行为问题，不表示已证明患者危害或所有产物存在此误差。“候选”必须由实施Agent补充生产路径复现或有证据排除，不能直接当已解决。

## 本轮执行证据

`evidence/new_probe_results.json`：Python3.13.5，8项窄范围检查中7项所要求不变量失败，1项SAE正向对照通过。运行模式为`transcribed_source_excerpts`。除完整`ids.py`经Git blob哈希核对外，所带文件是明确标识的源码函数摘录，不是假装下载的完整仓库。R08仅验证ID表达式与最小SQLite冲突行为，不是实际研究摄取端到端。

第一轮探针文件放在`probes/phase1/`及`evidence/phase1_original_results.json`，标签明确为第一轮结果；它们的结果不能冒充本轮重新跑完整仓库。

## 问题列表


### F01 | P1 | 已报告零值模型反转

**证据等级**：第一轮抄录模型探针；未做仓库端到端。

**源码锚点**：[src/ci_workflow/renderers/portal/report_a.py](https://github.com/smkzw/competitive-intelligence-workflow/blob/d6cb6d51e1b5a5e2abdacea485ea84b5268dc7ca/src/ci_workflow/renderers/portal/report_a.py)；[src/ci_workflow/domain/enums.py](https://github.com/smkzw/competitive-intelligence-workflow/blob/d6cb6d51e1b5a5e2abdacea485ea84b5268dc7ca/src/ci_workflow/domain/enums.py)。

**观察**：EfficacyRow 只允许 REPORTED_VALUE 携带 value。reported_zero+0 被拒绝，reported_zero+null 反而接受。

**影响与限定**：明确零值是科学事实，不能以改成缺失或丢弃其状态绕过。

**修复与验收方向**：统一 numeric value/disclosure 不变量，保留原始零值证据；将同一测试覆盖 A/B 图、表和证据显示。

### F02 | P1 | 等价时间表达被政策身份拆开

**证据等级**：静态确定分支；全域回归待跑。

**源码锚点**：[src/ci_workflow/reports/b/semantic_contract.py](https://github.com/smkzw/competitive-intelligence-workflow/blob/d6cb6d51e1b5a5e2abdacea485ea84b5268dc7ca/src/ci_workflow/reports/b/semantic_contract.py)；[policies/timepoints/compatibility-v1.yaml](https://github.com/smkzw/competitive-intelligence-workflow/blob/d6cb6d51e1b5a5e2abdacea485ea84b5268dc7ca/policies/timepoints/compatibility-v1.yaml)。

**观察**：时间规则按原始单位命中后还要求同 rule_id。同锚点的28天/4周会命中不同规则；168天未有对应范围规则。

**影响与限定**：无临床实质差异的写法可能制造单试验图；不能通过把累计区间当单时点解决。

**修复与验收方向**：先标准化锚点、时点/区间/计划与可精确换算单位，再做窗口政策；自然月和累计窗另行处理。

### F03 | P1 | 不可绘制状态被表格统一写成尚未公开

**证据等级**：静态确定；已核对运行时资产 blob 相同。

**源码锚点**：[assets/portal/charts.js](https://github.com/smkzw/competitive-intelligence-workflow/blob/d6cb6d51e1b5a5e2abdacea485ea84b5268dc7ca/assets/portal/charts.js)；[src/ci_workflow/renderers/portal/assets/charts.js](https://github.com/smkzw/competitive-intelligence-workflow/blob/d6cb6d51e1b5a5e2abdacea485ea84b5268dc7ca/src/ci_workflow/renderers/portal/assets/charts.js)。

**观察**：renderTable 对 !isRenderable 的值和状态均使用“该指标结果尚未公开”，没有沿用同文件的细分披露标签。

**影响与限定**：不适用、来源冲突、技术未解析与未披露混淆。

**修复与验收方向**：图、表、证据使用同一状态映射；数据披露状态与数值可绘制状态分开。

### F04 | P1 | 样本量与不适用模型不能准确表达边界

**证据等级**：第一轮模型探针；实际漏试验未证实。

**源码锚点**：[src/ci_workflow/renderers/portal/report_a.py](https://github.com/smkzw/competitive-intelligence-workflow/blob/d6cb6d51e1b5a5e2abdacea485ea84b5268dc7ca/src/ci_workflow/renderers/portal/report_a.py)。

**观察**：TrialRow.sample_size 为必填 gt=0，拒绝未知和零入组；SafetyRow 允许“不适用”与数值同时存在。

**影响与限定**：全景不得以虚构1例或计划数代替真实未知/零；不适用不应成为数值容器。

**修复与验收方向**：区分 planned/actual 和 disclosure；规则按数据类型应用，不把人数与事件次数混淆。

### F05 | P1 / 产品替换 | C 文本签名与第一条选择不代表完整设计

**证据等级**：静态确定；新方向下不再作为活跃交付门。

**源码锚点**：[src/ci_workflow/reports/c/synthesis.py](https://github.com/smkzw/competitive-intelligence-workflow/blob/d6cb6d51e1b5a5e2abdacea485ea84b5268dc7ca/src/ci_workflow/reports/c/synthesis.py)。

**观察**：同字段仅取 observation_id 字典序首条；只有至少两类完整签名且每类≥2项研究才形成路径。

**影响与限定**：多终点、多组、多时期事实被压缩；稀有设计先例不能正常作为路径。

**修复与验收方向**：保留全量 observation 与关系，改为设计维度索引；旧路径只留历史兼容，不再强制。

### F06 | P1 / 产品替换 | B 的严格等价承担共同展示许可

**证据等级**：静态确定；由用户决定升级展示合同。

**源码锚点**：[src/ci_workflow/reports/b/semantic_contract.py](https://github.com/smkzw/competitive-intelligence-workflow/blob/d6cb6d51e1b5a5e2abdacea485ea84b5268dc7ca/src/ci_workflow/reports/b/semantic_contract.py)；[src/ci_workflow/reports/b/semantic_grouping.py](https://github.com/smkzw/competitive-intelligence-workflow/blob/d6cb6d51e1b5a5e2abdacea485ea84b5268dc7ca/src/ci_workflow/reports/b/semantic_grouping.py)。

**观察**：硬轴字符串相等、缺失拒判、跨原桶需要正向复核归并；共同展示高度受兼容桶限制。

**影响与限定**：安全守卫本身有价值，但不能把不等价研究排除出共同研究工作空间。

**修复与验收方向**：拆分 WorkspaceMembership / FacetPlan / NumericFrameEligibility。保留所有相关研究与严格共轴守卫。

### F07 | P1候选 | 分组柱图坐标冲突保留第一行

**证据等级**：局部分支确定；生产输入能否触发待测。

**源码锚点**：[assets/portal/charts.js](https://github.com/smkzw/competitive-intelligence-workflow/blob/d6cb6d51e1b5a5e2abdacea485ea84b5268dc7ca/assets/portal/charts.js)；[src/ci_workflow/renderers/portal/assets/charts.js](https://github.com/smkzw/competitive-intelligence-workflow/blob/d6cb6d51e1b5a5e2abdacea485ea84b5268dc7ca/src/ci_workflow/renderers/portal/assets/charts.js)。

**观察**：同 categoryKey+seriesKey 的重复记录只保留第一条，但整体 rowIds 仍含全部记录。

**影响与限定**：若上游未纳入多剂量/时期等身份，表有多条而图只一条。当前不能声称全部多臂图已丢数。

**修复与验收方向**：明确 series/item 复合身份；坐标冲突必须拆维度/分面或拒绝，不取首条、不均值聚合。

### F08 | P2 / 产品差距 | 现有筛选抽屉不等于层级工作台

**证据等级**：已读脚本静态审查；不是全仓不存在断言。

**源码锚点**：[assets/portal/portal.js](https://github.com/smkzw/competitive-intelligence-workflow/blob/d6cb6d51e1b5a5e2abdacea485ea84b5268dc7ca/assets/portal/portal.js)；[assets/portal/charts.js](https://github.com/smkzw/competitive-intelligence-workflow/blob/d6cb6d51e1b5a5e2abdacea485ea84b5268dc7ca/assets/portal/charts.js)。

**观察**：已有筛选/URL/单事实证据；selectByRowId 找到首个图后 break，每个 rowId 只保存一个表格元素。

**影响与限定**：同一事实多视图联动有限；不能用有按钮证明配置保存、组合及多层下钻全流程存在。

**修复与验收方向**：统一 ViewState / query result / event bus，一对多 DOM/图映射；做真实连续任务浏览器验收。

### F09 | P1 | C 入排标准硬截断与短条款丢弃

**证据等级**：本轮 R01/R02 窄函数探针复现；作用域为 PNH packet builder。

**源码锚点**：[packets/2026-09-11-pnh-vertical/build_pnh_c_audit.py](https://github.com/smkzw/competitive-intelligence-workflow/blob/d6cb6d51e1b5a5e2abdacea485ea84b5268dc7ca/packets/2026-09-11-pnh-vertical/build_pnh_c_audit.py)。

**观察**：_split_eligibility 返回 inclusion/exclusion 各[:10]；分段只保留长度≥8。12/11条输入变10/10，短条款“HIV+”被丢弃。

**影响与限定**：原始已公开设计未全量进入下游，增加前端下钻不能恢复未入库条款。不能据此断言全部安装路径都截断。

**修复与验收方向**：删除任意数量/长度截断；保留原文 inventory、父子逻辑与拆分覆盖；在通用提取器回归而非只修 packet。

### F10 | P1 | C 首个主要终点和第一治疗组代表全部

**证据等级**：静态确定 PNH packet 构建行为。

**源码锚点**：[packets/2026-09-11-pnh-vertical/build_pnh_c_audit.py](https://github.com/smkzw/competitive-intelligence-workflow/blob/d6cb6d51e1b5a5e2abdacea485ea84b5268dc7ca/packets/2026-09-11-pnh-vertical/build_pnh_c_audit.py)。

**观察**：primaryOutcomes 仅取[0]；各干预描述合成一个 regimen 绑定 arm1；目标人群压到600字符；此段未遍历全部次要终点。

**影响与限定**：共主要终点、定义细节、次要终点与分组给药无法由该路径完整表达。

**修复与验收方向**：全量主/次要终点及描述与时间点建关系；逐组/期间关联干预，保留完整人群原文。

### F11 | P1 | 缺失盲法默认成为开放标签

**证据等级**：静态确定 PNH packet 默认值链。

**源码锚点**：[packets/2026-09-11-pnh-vertical/build_pnh_c_audit.py](https://github.com/smkzw/competitive-intelligence-workflow/blob/d6cb6d51e1b5a5e2abdacea485ea84b5268dc7ca/packets/2026-09-11-pnh-vertical/build_pnh_c_audit.py)。

**观察**：masking缺失时 or "NONE"，后续 NONE 显示开放标签；comparative/single_arm 声明来自固定试验集合。

**影响与限定**：未知被转换成肯定事实；演示选择不能作为通用语义事实生产。

**修复与验收方向**：缺失与明确NONE区分；设计类型由来源结构和证据决定；固定研究列表明确为fixture范围。

### F12 | P1 | C 规范化破坏数字标点

**证据等级**：本轮 R03/R04 窄函数探针复现。

**源码锚点**：[src/ci_workflow/reports/c/synthesis.py](https://github.com/smkzw/competitive-intelligence-workflow/blob/d6cb6d51e1b5a5e2abdacea485ea84b5268dc7ca/src/ci_workflow/reports/c/synthesis.py)。

**观察**：全Unicode标点变空格；_compact_clause 又直接用于显示。0.5 mg BID→0 5 mg bid；5-10 mg 与5.10 mg均归为5 10 mg。

**影响与限定**：小数点/范围符号既是显示信息也是临床语义，不能当可删除标点。

**修复与验收方向**：原文显示不经过破坏性规范化；检索规范化与typed数值语义分开，保留小数、范围、运算符。

### F13 | P1 / 必改合同 | C 候选路径要求实际卡住科学输入边界

**证据等级**：本轮沿调用链确认，不再仅是假设。

**源码锚点**：[src/ci_workflow/application/fresh_c_research_package.py](https://github.com/smkzw/competitive-intelligence-workflow/blob/d6cb6d51e1b5a5e2abdacea485ea84b5268dc7ca/src/ci_workflow/application/fresh_c_research_package.py)。

**观察**：design_paths必填；_content_is_closed调用_validate_design_paths，路径不足2条直接报错。

**影响与限定**：不是只隐藏一个可选模块；完整先例也可能因无两条生成路径被拒绝。

**修复与验收方向**：新schema中路径非必需，移除数量 gate，保留试验设计事实、来源与端点时间关系完整性；支持旧包迁移。

### F14 | P1 | 事实版本身份缺字段且冲突被忽略

**证据等级**：本轮 R08 真实表达式的抄录+最小SQLite示例；非完整ingestion运行。

**源码锚点**：[src/ci_workflow/application/fresh_research_ingestion.py](https://github.com/smkzw/competitive-intelligence-workflow/blob/d6cb6d51e1b5a5e2abdacea485ea84b5268dc7ca/src/ci_workflow/application/fresh_research_ingestion.py)；[src/ci_workflow/application/source_research_service.py](https://github.com/smkzw/competitive-intelligence-workflow/blob/d6cb6d51e1b5a5e2abdacea485ea84b5268dc7ca/src/ci_workflow/application/source_research_service.py)。

**观察**：version_id仅用fact_id/field_id/(normalized_value or disclosure_state)/fragment；规范值存在时状态、原文等变化不影响ID；随后INSERT OR IGNORE。

**影响与限定**：同规范值“0”从reported_value改reported_zero时ID相同，最小SQL演示只留下旧状态。用户小修尤其需要避免。

**修复与验收方向**：绑定完整科学内容摘要；冲突比较完整序列化内容，相同键不同内容报错/明确新版本。A和共享摄取两条路径一并消重。

### F15 | P1 | 逐事实证据定位未进入持久化事实边

**证据等级**：静态确定所读摄取路径；报告JSON可能仍保留细定位。

**源码锚点**：[src/ci_workflow/application/fresh_research_ingestion.py](https://github.com/smkzw/competitive-intelligence-workflow/blob/d6cb6d51e1b5a5e2abdacea485ea84b5268dc7ca/src/ci_workflow/application/fresh_research_ingestion.py)。

**观察**：每个capture只生成一个包含全文的fragment；每条事实都使用fragments[fact.source_id]，未使用fact.locator与fact.original_text新建精确片段。

**影响与限定**：底层fact_evidence只能回到源捕获片段；不能等同于可靠逐条证据绑定。

**修复与验收方向**：以source_version+精确locator+原文范围摘要创建/复用fragment；单源多条事实各自能回到相应字段/表/段。

### F16 | P1候选 | 同源重新获取回执可被旧ID跳过

**证据等级**：局部ID/追加逻辑确定；完整refresh影响待验证。

**源码锚点**：[src/ci_workflow/application/fresh_research_ingestion.py](https://github.com/smkzw/competitive-intelligence-workflow/blob/d6cb6d51e1b5a5e2abdacea485ea84b5268dc7ca/src/ci_workflow/application/fresh_research_ingestion.py)。

**观察**：source-receipt ID由project/report/source_id组成；追加只检查receipt_id是否已存在，不比较内容。

**影响与限定**：同source_id的新来源版本或访问尝试可能不追加新回执，不能用已有记录证明本次核查。

**修复与验收方向**：区分逻辑来源、访问尝试、不可变来源版本；回执绑定实际attempt/version内容；相同ID不同内容拒绝。

### F17 | P1 | 安全性分类忽略否定和treatment-emergent限定

**证据等级**：本轮 R05/R06复现，R07 SAE正向对照通过。

**源码锚点**：[src/ci_workflow/application/source_research_service.py](https://github.com/smkzw/competitive-intelligence-workflow/blob/d6cb6d51e1b5a5e2abdacea485ea84b5268dc7ca/src/ci_workflow/application/source_research_service.py)。

**观察**：_outcome_category对class_title含serious即SAE；Non-serious adverse events→sae。通用AE别名也直接→teae。

**影响与限定**：这是来源结果覆盖/分类函数行为，不在本轮断言所有产物已显示相同误标签。

**修复与验收方向**：保留源类别；显式处理non-serious/否定词；无时间定义不升级TEAE；正向SAE/TEAE和混合类别均需回归。

### F18 | P1 / 功能缺口 | 现有修订登记并非全报告同步执行

**证据等级**：静态接口合同确认。

**源码锚点**：[src/ci_workflow/application/correction_service.py](https://github.com/smkzw/competitive-intelligence-workflow/blob/d6cb6d51e1b5a5e2abdacea485ea84b5268dc7ca/src/ci_workflow/application/correction_service.py)。

**观察**：CorrectionProposal绑定单report/report_version；publish要求调用方传new_snapshot_manifest、rebuilt_artifacts、independent_qc，主要登记新版本。

**影响与限定**：复用此服务不等于已有HTML编辑→共享事实→全报告同步。

**修复与验收方向**：增设协调器，将单次typed修订落到共同fact version，计算跨A/B/C影响并原子提交；复用事件/幂等/现有审核能力。

### F19 | P1候选 | 修订发布校验尚不能证明实际重建闭合

**证据等级**：仅限_publish_materials所读函数；未认定全系统review链可绕过。

**源码锚点**：[src/ci_workflow/application/correction_service.py](https://github.com/smkzw/competitive-intelligence-workflow/blob/d6cb6d51e1b5a5e2abdacea485ea84b5268dc7ca/src/ci_workflow/application/correction_service.py)。

**观察**：rebuilt_artifacts只验证非空ID和hash格式，未在此函数读取产物字节/比较受影响集合；independent_qc先校验结构和快照绑定。

**影响与限定**：一组自洽元数据并不能证明实际每个相关HTML都重建。正式review issue有另行信任链，不可据此泛称全系统任意JSON可过审。

**修复与验收方向**：调用统一产物验证器，逐文件实际hash/版本/受影响覆盖匹配；正式核验复用现有receipt/issuance，不另建薄弱入口。

### F20 | P2 / 扩展点 | 现有影响图缺少明确事实派生边

**证据等级**：静态类型限制确认；现有其他依赖表达仍需查。

**源码锚点**：[src/ci_workflow/graph/impact.py](https://github.com/smkzw/competitive-intelligence-workflow/blob/d6cb6d51e1b5a5e2abdacea485ea84b5268dc7ca/src/ci_workflow/graph/impact.py)。

**观察**：固定source/fact/claim/page/format且只能相邻层连接，不能直接表达n,N→rate等fact→fact依赖。

**影响与限定**：全报告同步必须处理计算图而不仅页面归属。

**修复与验收方向**：先查可复用计算依赖，再扩展typed有向无环依赖并校验循环；不要独立于现有ImpactGraph再手工维护一套页面清单。

## 已核对、不要误报的事项

1. `builder.py::resolve_portal_asset` 优先读取包内 assets。已分别读取包内 `charts.js` 与 `portal.js` 的 blob SHA，与根目录文件一致：`956d94118fefa1706e31cec273b692d944f5f77c` / `23f5ee595baf12a17b55902010f93a2f4435c41d`。因此本轮前端局部分支结论适用于该包内副本；不应报当前两副本已经漂移。未来改造应建立单一作者文件和构建复制校验。
2. `tools/bundle_contract.py` 递归包含 policies，并排除延期格式/监测路径；根目录 package-manifest 未逐项列出某政策不等于漏打包。
3. `tools/gate.sh` 自述 quality-only，不能把其通过代替浏览器、真实科学内容、安装及恢复验收；也不应把未覆盖浏览器说成脚本撒谎。
4. 原有TypedSkillGraph、executor、来源任务、独立review issue存在。需验证声明/执行/实际宿主轨迹一致，不凭SKILL.md长短判断是否多Agent。
5. 没有把“有源码遗留PDF/PPT模块”误报为v1必定发布那些格式；只在确认无活跃依赖后移动/隔离代码，不删除历史证据。

## 仍需实施Agent完成的全链路审查

- 所有本轮“候选”问题：构造实际research-package走真实入口，核对最终图/表/数据库而非仅函数返回。
- 研究入口/来源路由/历史可知性/获取回执/全文补件/跨源身份和结果去重；查询穷尽与独立复核。
- 主图、节点声明与运行调度的对应关系；失败分类、取消/重试、并发写、断点恢复和无进展循环。
- 来源→事实→规范化/派生→声明→A/B/C产物的实际依赖登记；同源更新和用户修订冲突。
- HTML脚本嵌入转义、用户编辑/导入配置的XSS与路径防护；离线实际断网阅读、分享闭包及增量修订。
- 全部现有产品层测试及正式8适应症×A/B/C矩阵、三宿主和恢复合同，按现行未被用户推翻的范围执行。

不得因本轮未覆盖而推断这些链路已有漏洞，也不得因本轮未复现而标为通过。新的确证发现加入同一清单，不另造第二份相冲突审阅总表。
