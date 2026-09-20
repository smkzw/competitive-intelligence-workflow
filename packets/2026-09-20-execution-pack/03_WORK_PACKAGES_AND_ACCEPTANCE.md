# 工作包、行为验收与回归要求

**A/B/C 是平行产品线，不设业务优先级。** WP01–04的依赖顺序是复用基础设施的工程要求。多个Agent可在共享接口冻结后同时承接WP05A/B/C；单Agent不得以“先做完B”推迟A/C的完整验收。

所有路径均是已知现有入口；具体新增文件可在相应包内按现有风格命名。不要因为建议了一个新概念就创建同名服务、数据库和Skill三份权威。机器工作单在`work_items.json`，验收用例在`acceptance_cases.json`。

## 1. 实施顺序

```text
WP00 基线/规格/回归
 ├── WP01 科学完整性 ──┐
 ├── WP02 共享事实 ────┼── WP04 修订与原子同步 ──┐
 └── WP03 交互基础 ────┼── WP05A / WP05B / WP05C ┼── WP06 分享 ── WP08 整体验收
                      └── WP07 多Skill共享执行 ──┘
```

已查源码位置不能仅据文件名判定调用。先追踪真实入口、调用方、序列化和安装副本，再改代码并补集成回归。

## WP00 — 基线、规格升版与全链路审查补齐

依赖：无；报告范围：A / B / C。

现有入口：`AGENTS.md`、`docs/specs/competitive-intelligence-workflow-design-v1.3.md`、`tools/gate.sh`、`tests`。

- 记录HEAD与工作树；核对更新，不回退用户代码
- 把五项用户决策写入新规格及合同变更记录
- 建立红测试，追踪候选问题到实际入口
- 核对当前产物/测试/安装范围，不以历史回执作新验收

完成证据：BASE01, BASE02。涉及问题：F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11, F12, F13, F14, F15, F16, F17, F18, F19, F20。

## WP01 — 科学值与完整性缺陷修复

依赖：WP00；报告范围：A / B / C。

现有入口：`src/ci_workflow/renderers/portal/report_a.py`、`src/ci_workflow/application/source_research_service.py`、`src/ci_workflow/reports/c/synthesis.py`、`packets/2026-09-11-pnh-vertical/build_pnh_c_audit.py`。

- 统一零/缺失/不适用及计划实际样本量
- 修复安全类别否定与TEAE限定
- 数值/运算符与原文保真
- 全量入排和主次终点，各组各期间干预完整解析；缺失不变开放标签

完成证据：SCI01, SCI02, SCI03, SCI04, SCI05。涉及问题：F01, F04, F09, F10, F11, F12, F17。

## WP02 — 共同事实身份、逐条证据与派生依赖

依赖：WP00；报告范围：A / B / C。

现有入口：`src/ci_workflow/domain/facts.py`、`src/ci_workflow/application/fresh_research_ingestion.py`、`src/ci_workflow/application/source_research_service.py`、`src/ci_workflow/graph/impact.py`、`src/ci_workflow/storage`。

- 复用AtomicFactVersion，消除报告私有事实身份的重复权威
- 来源捕获和逐事实fragment分离
- 完整内容版本键+冲突校验+本次访问回执
- 补全派生DAG与fact到所有消费视图的映射
- 数据库迁移及旧包上下文映射，不按显示文本硬合并

完成证据：DATA01, DATA02, DATA03, DATA04, DATA05, DATA06。涉及问题：F14, F15, F16, F20。

## WP03 — 共同视图状态、查询与图表交互基础

依赖：WP00；报告范围：A / B / C。

现有入口：`assets/portal/charts.js`、`assets/portal/portal.js`、`src/ci_workflow/renderers/portal/assets`、`src/ci_workflow/renderers/portal/builder.py`、`src/ci_workflow/reports/common`。

- 统一ViewState和typed QuerySpec，不以DOM可见性作为科学结果真源
- 稳定item/fact身份与一对多图表表格联动
- 分面/字段/允许图形组合、下钻返回、配置保存导入
- 细分missing状态、碰撞拒绝/显式拆分、虚拟化与按需图表
- 单一资产作者来源，构建副本hash校验

完成证据：UI01, UI02, UI03, UI04, UI05, UI06。涉及问题：F03, F07, F08。

## WP04 — 实际事实修订与跨报告原子同步

依赖：WP01, WP02, WP03；报告范围：A / B / C。

现有入口：`src/ci_workflow/application/correction_service.py`、`src/ci_workflow/graph/impact.py`、`src/ci_workflow/application/refresh_service.py`、`src/ci_workflow/cli.py`、`src/ci_workflow/storage`。

- typed correction命令+当前版本乐观锁+显式用户保存
- 复用事件/事实版本并增加跨报告协调
- 只按有证据公式重算，失效旧叙事/复核状态
- 真实文件hash与受影响闭包验证
- 新增按需loopback编辑入口与安装启动器，安全限制

完成证据：EDIT01, EDIT02, EDIT03, EDIT04, EDIT05, EDIT06, EDIT07, EDIT08, EDIT09, EDIT10。涉及问题：F18, F19, F20。

## WP05A — A 独立景观门户垂直实现

依赖：WP01, WP02, WP03；报告范围：A。

现有入口：`src/ci_workflow/renderers/portal/report_a.py`、`src/ci_workflow/renderers/portal/templates`、`src/ci_workflow/reports/common`。

- 完整创新宇宙可达、实体/机制/地域/阶段联动
- 产品→轨迹→试验→结果/事件→证据下钻
- 原始事实与自动派生状态分离
- 接入共同配置与修订，不依赖B/C页面存在

完成证据：A01, A02, A03, A04。涉及问题：F04, F08。

## WP05B — B 全研究分面比较垂直实现

依赖：WP01, WP02, WP03；报告范围：B。

现有入口：`src/ci_workflow/reports/b/semantic_contract.py`、`src/ci_workflow/reports/b/semantic_grouping.py`、`src/ci_workflow/renderers/portal/report_b.py`、`policies/timepoints/compatibility-v1.yaml`。

- WorkspaceMembership/FacetPlan/NumericFrameEligibility三层
- 全部相关研究可达，角色和差异显著标示
- 精确时间换算与临床窗口、时点区间语义
- 同一问题跨试验图/表、控制组与多臂保留
- 接入共同编辑、图表组合与保存配置

完成证据：B01, B02, B03, B04, B05, B06。涉及问题：F02, F06, F07, F08。

## WP05C — C 设计先例库垂直实现

依赖：WP01, WP02, WP03；报告范围：C。

现有入口：`src/ci_workflow/reports/c/contracts.py`、`src/ci_workflow/reports/c/synthesis.py`、`src/ci_workflow/application/fresh_c_research_package.py`、`src/ci_workflow/renderers/portal/report_c.py`、`skills/_internal/analysis-c/SKILL.md`。

- 全量DesignClause及嵌套逻辑、数值/时间/上下文索引
- 关键词/中英同义主题/点选/试验对照/只看差异
- 一项有效试验即可先例交付，无强制路径生成
- 保留原文和来源版本，计划/结果/不同方案版本不混淆
- 接入共同事实修订和保存配置

完成证据：C01, C02, C03, C04, C05, C06, C07。涉及问题：F05, F09, F10, F11, F12, F13。

## WP06 — 静态分享包与配置修订可携带

依赖：WP04, WP05A, WP05B, WP05C；报告范围：A / B / C。

现有入口：`src/ci_workflow/application/delivered_artifacts.py`、`src/ci_workflow/application/latest_delivery.py`、`src/ci_workflow/cli.py`、`tools/bundle_contract.py`、`src/ci_workflow/renderers/portal`。

- 导出当前有效版本，不分发陈旧HTML+待手动导入patch
- A/B/C独立目录与共同资源依赖闭合
- 配置/修订历史/来源入口和manifest绑定
- 无Python/Agent/联网即可读取，编辑可由本地工作流重新打开
- 只打包允许分享数据，不含凭据或工作目录

完成证据：SHARE01, SHARE02, SHARE03, SHARE04, SHARE05。涉及问题：F18, F19。

## WP07 — 共享研究任务与多Skill执行效率

依赖：WP00, WP02；报告范围：A / B / C。

现有入口：`src/ci_workflow/application/autonomous_research.py`、`src/ci_workflow/application/run_service.py`、`src/ci_workflow/graph/typed_skills.py`、`src/ci_workflow/graph/executor.py`、`skills/_internal`。

- 合并研究需求与来源获取任务，不重复科学抽取
- 同内容解析缓存包含版本政策；动态状态本次核查
- 记录实际协作/复核/重试/进展，避免主Agent手写自证
- 局部阻断不回滚其他共享成果
- 宿主执行与typed合同一致性

完成证据：LOOP01, LOOP02, LOOP03, LOOP04。涉及问题：F16。

## WP08 — 整合、安装、科学与浏览器验收

依赖：WP01, WP02, WP03, WP04, WP05A, WP05B, WP05C, WP06, WP07；报告范围：A / B / C。

现有入口：`tests/unit`、`tests/contract`、`tests/reports`、`tests/browser`、`tests/integration`、`tools/gate.sh`、`tools/run_acceptance.py`。

- 执行行为验收矩阵和全部活跃层回归
- 实际浏览器不同视口/断网/两标签页/清存储重开/分享往返
- 安装入口与三宿主，保留现行正式矩阵范围
- 报告所有未通过而非只展示成功截图
- 先真实验证，再生成提交/产物/证据回报

完成证据：END01, END02, END03, END04。涉及问题：全量整合。

## 2. 行为验收矩阵

以下是必须实施的验收，而非本轮已通过的结果。数字案例为合成测试，不构成任何真实药物或试验结论。

| ID | 场景 | 输入/动作 | 必须观察到 |
|---|---|---|---|

| BASE01 | 记录基线 | HEAD不同或工作树有用户未提交改动 | 不覆盖、不重置，记录差异并复用当前修复 |
| BASE02 | 红测试真实 | 本包候选问题走当前实际入口 | 确证或以输入/调用/产物证据排除，不静默skip |
| SCI01 | 零与缺失 | reported_zero=0/null；未报告/不适用携数值；zero人数 | 0正确，缺失不当0；不合法组合失败；计划实际明确 |
| SCI02 | 安全类型 | SAE/Non-serious AE/AE/TEAE/混合分类 | 否定不误判，AE不升级TEAE，正确阳性不回归 |
| SCI03 | 数字保真 | 0.5、5-10、5.10、≤、±、小数阈值 | 原文和显示不损坏，不同含义不归成同签名 |
| SCI04 | 条款完整 | 18条入选+21条排除，短条款，嵌套项目 | 全量可定位；不按长度/数量删项 |
| SCI05 | 多元素完整 | 2个主要/多个次要终点；3组2期间；未知masking | 全部保留、正确组别配对；unknown不变open-label |
| DATA01 | 内容版本 | 同规范值改状态/原始表达/上下文 | 新版本或明确冲突，不能IGNORE吞掉 |
| DATA02 | 逐条定位 | 一篇来源的两张表各一事实 | 每事实定位回自己字段，非仅共同全文fragment |
| DATA03 | 别名非误合并 | 同产品别名与不同人群的同名终点 | 产品正确消歧；不同事实上下文不强合并 |
| DATA04 | 计划实际分开 | C计划N与B实际N及A汇总同页 | 独立事实身份；修一处不覆盖另一事实 |
| DATA05 | 来源新版本 | 同source_id不同字节/获取尝试 | 本次回执不复用旧的，版本绑定闭合 |
| DATA06 | 派生DAG | n,N→粗率→试验内派生→多个页面；人为环 | 正确完整传播；拒绝环/缺边导致伪同步 |
| UI01 | 多视图同事实 | 点击某点同时存在两图两表 | 所有对应位置同选中，数据身份不靠dataIndex |
| UI02 | 查询守恒 | 筛选后有可绘图和不可绘图记录 | 可绘+非可绘覆盖匹配集，非可绘显示准确原因 |
| UI03 | 配置往返 | 修改字段/排序/分面/图例/布局并重开 | 恢复等价ViewState与事实选择，不依赖旧浏览器缓存 |
| UI04 | 坐标碰撞 | 多臂同role、多剂量、多时期 | 没有第一条获胜；显式维度/分面或诊断 |
| UI05 | 下钻返回 | 三级以上下钻后返回、URL前进后退 | 筛选/选择/滚动/焦点一致，不跳回全量 |
| UI06 | 导入与脚本安全 | 恶意标签/HTML/script结束串/非法维度JSON | 不执行输入，严格校验配置；合法中文照常显示 |
| EDIT01 | 跨报告同步 | 合成事实n20/N80，修n24；多个A/B视图共用 | 粗率25%→30%，相关图表正文一致；不相关C事实不变 |
| EDIT02 | 已报告统计量 | 来源调整率和n/N派生粗率同时存在 | 只重算明确粗率，来源调整率不被替换；矛盾可见 |
| EDIT03 | 语义修改 | 终点时间窗/单位/分析集改变 | 重新分面并失效相应裁决；不能继承旧compatible标记 |
| EDIT04 | 原子失败 | B已生成候选新产物时C相关生成失败 | current仍完整旧版；不会宣布全部同步；可恢复 |
| EDIT05 | 并发标签页 | 两标签页基于同旧事实提交不同修改 | 一次成功、一次明确冲突；不能后写无声覆盖 |
| EDIT06 | 幂等与撤销 | 重复保存同请求；再撤销 | 不重复创建相同修订，撤销产生新历史版本 |
| EDIT07 | 叙事失效 | 模型生成解释依赖被改事实 | 旧解释不继续标当前有效，可显示失效理由并重算 |
| EDIT08 | 核验状态 | 编辑已独立核验内容后分享 | 原始版和旧回执保留；新内容标用户修订而非重新通过 |
| EDIT09 | 实际产物校验 | 提交正确格式hash但文件缺失/字节不同/漏页面 | 校验拒绝；不以结构正确回执通过 |
| EDIT10 | 本地接口安全 | 非预期Origin/Host、路径穿越、symlink、无会话写入 | 拒绝越权；合法本地typed修改能工作 |
| A01 | 全宇宙 | 临床前、早期、终止、撤回和结果性项目 | 纳入集合与来源处置一致，不因没结果删产品 |
| A02 | 全景联动 | 机制→产品→地区事件→试验→证据 | 图表/列表统一筛选；能返回原状态 |
| A03 | 地域分轨 | 中国与境外阶段/监管状态不同 | 不互相覆盖，来源日期与事件身份明确 |
| A04 | 独立交付 | 只请求A | A完整可读，不依赖B/C输出目录 |
| B01 | 默认分面 | 同问题3研究，24/26/52周有实际差异 | 3项均可达，近窗规则和长期分面清楚 |
| B02 | 不可共轴 | 不同量表/绝对与变化/均值与中位数/不同分母 | 同工作空间查看，但不误共轴/池化 |
| B03 | 时间锚点 | 28d/4w；0–24周累计/24周评估；不同基准日 | 精确换算只在同语义；累计与单点不误合并 |
| B04 | 完整治疗语境 | 多臂、活性对照、单臂、支持研究 | 角色保留；无对照不伪造比较效应 |
| B05 | 未知仍可查 | 某研究estimand未公开 | 可达并标未知，不伪造字段以获得兼容 |
| B06 | 独立交付 | 只请求B | B完整自足，无A生成前置 |
| C01 | 单研究可用 | 一项核心设计完整但没有第二种路径 | C先例正常交付，无候选路径数量阻断 |
| C02 | 全文无丢失 | 条款inventory→解构→索引→对照表 | 每条有映射，不截条数/长度；母子句可还原 |
| C03 | 布尔逻辑 | AND/OR/NOT、例外、条件适用人群、洗脱时限 | 搜索可命中主题，展示完整关系不反转含义 |
| C04 | 按需横查 | 关键词→主题→点选研究→只看差异→原文 | 同义匹配不冒充临床等价，完整句和阈值可下钻 |
| C05 | 字段一对多 | 共主要终点/多剂量/多时期/多个方案版本 | 配对保留；不按首条覆盖 |
| C06 | 修订反映索引 | 修改某条门槛/译名/分类 | 检索/分类/矩阵/原文对照更新，原始quote不覆写 |
| C07 | 独立交付 | 只请求C | C无需先完成A或B，试验列表来自共同身份层 |
| SHARE01 | 无环境读取 | 断网新浏览器/清存储，解压改路径，双击HTML | A/B/C图、表、来源、配置一致且无远程依赖 |
| SHARE02 | 用户修订可携带 | 修改并同步后导出分享 | 同事默认打开就是当前修订，不需手动修补JSON |
| SHARE03 | 配置与单报告 | 分别导出A/B/C单份和组合包 | 每包资源依赖闭合且状态恢复，无强制融合首页 |
| SHARE04 | 版本错配 | 把旧配置/patch用于另一快照 | 显式校验/可解释迁移；不静默绑定同名字段 |
| SHARE05 | 内容边界 | 扫描导出包 | 不含token、绝对工作目录、商业会话/未经授权全文 |
| LOOP01 | 去重效率 | ABC同时需要同登记记录和论文 | 每内容/提取版本只做必要获取解析，三报告都可用 |
| LOOP02 | 动态新鲜度 | 动态页面不变与网络失败两种情况 | 重新核查回执存在；失败不称本次已确认 |
| LOOP03 | 局部阻断 | C附件失败，A/B已有充分资料 | 共享完成节点复用，不整项目重复检索 |
| LOOP04 | 真实回环 | 重试无进展/独立审阅/进程中断 | 诊断/恢复/预算有实测，不靠生产者自填通过 |
| END01 | 三门户平等 | A/B/C各自连续任务和组合场景 | 三个均通过，不宣布一个成功等于整体完成 |
| END02 | 浏览器覆盖 | Chromium/WebKit，1440×900、1024×1366、390×844、320×568 | 操作/焦点/遮挡/console/链接均实测，失败有记录 |
| END03 | 安装与来源矩阵 | 全新安装、三宿主、现行8适应症×ABC正式范围 | 从安装入口验证，不复用旧回执冒充新验收 |
| END04 | 迁移恢复性能 | 旧项目迁移、崩溃恢复、代表与压力数据集 | 历史可读、相同输入可复现，记录耗时/内存/查询p95；不删数据保性能 |

## 3. 必需的测试层次

**窄函数/模型**：零值、缺失、时间、符号、安全类别、数值类型、条款逻辑。  
**应用集成**：research submit/实际摄取→fact/fragment→typed查询→共享修订→真实产物文件；从实际入口测，不仅直接new模型。  
**前端浏览器**：选择/筛选/分面/下钻/编辑/撤销/配置/分享往返；捕获console、network、截图及实际字段断言。  
**安装与恢复**：实际bundle入口、迁移、独立宿主、崩溃中断、重开和新目录移动。

`tools/gate.sh`继续作为quality-only使用；在其现有基础外执行报告/集成/浏览器测试。不要改脚本标签把覆盖不足变为“发布通过”。保留未被用户推翻的正式24门户与三宿主矩阵；开发阶段可用PNH、AD和合成异质试验快速迭代，但不能把该子集称正式全验收。

## 4. 改造范围的增加、删除与保留

| 处置 | 项目 |
|---|---|
| 增加/补齐 | 共享fact映射、精确片段、派生DAG、共同ViewState、B分面合同、C完整条款索引、实际修订协调器、本地编辑入口、静态分享闭包 |
| 从活跃路径移除 | 医学批注、C强制候选路径与套话权衡、任意条款长度/数量截断、首条获胜、未知→NONE/0等补值 |
| 合并重复实现 | A旧摄取与通用摄取的共同底层逻辑；前端两份人工维护脚本；重复的原子事实定义和报告型身份 |
| 保留并修正 | 科学缺失状态、证据原文、独立复核、现有CAS/SQLite/EventStore、快照/历史、typed控制图、文件离线阅读 |
| 不新增 | 注释协作、云服务/用户账号、自动方案生成、跨试验Meta/池化/评分、无请求后台监测、未经授权的PDF/PPT/CSV/XLSX交付 |

对于旧C路径、旧schema、遗留格式测试，删除运行依赖不等于毁掉历史读取。先标旧版适配，确认引用，再隔离/归档。不得用删除测试证明新合同通过。

## 5. 工程回报模板

每个工作包只回报一次主记录：

```text
WP-ID / 实际提交与HEAD
变更入口：具体文件和函数
修复前：测试/运行/截图/数据库定位
修复后：同场景结果、assert、实际产物
影响：哪些A/B/C页面和事实；哪些未改变
剩余：失败、未测、环境阻断与实质风险
```

总体回报必须分开：代码完成、单元/集成、浏览器、科学/来源、安装/宿主、迁移/分享。任何没有实际执行的层标“未验证”。模型数、token量、审阅轮数、页面数、JSON数不得单独作为质量指标。

## 6. 性能与完整性一起验证

建立至少两个明确标记的合成负载，建议代表负载500项试验/2万观察/1万设计条款，压力负载2000项试验/20万观察；实际规模由现有真实用例核对并记录，不把建议数字伪称用户合同。记录环境、首屏、查询和筛选p50/p95、同步影响范围、峰值内存及清理。不能通过删除记录、只索引首几条或跳过不兼容试验达到性能指标。

当工作空间超过可读密度，使用分页/虚拟化/折叠/按需加载与精确计数，不一次初始化所有图。静态阅读的数据分片使用可离线执行的本地脚本或内嵌数据；不把运行时fetch本地JSON作为file://的必需条件。

