# STATUS

**2026-10-23｜M1实施中，未完成端到端验收**

## 当前合同与入口
- 权威：01_PRD、02_ARCHITECTURE、03_PLAN、04_AGENT_RULES；Trellis为根 .trellis/tasks/10-23-rebaseline-v2-m1。历史在该任务和Git，不将旧根HANDOFF当当前暂停指令。
- 仅实施英文工程的rebaseline-v2；单用户独立Web服务/内嵌9 Skills/HTML A/B/C。v1宿主包、编辑/分享/24门户合同不带入v2，历史和未知脏树保留，旧中文工程零接触。
- 包SHA256：5cad486b8b2ac7aea50fc074d9f223353d72d951f01f9d97677351d6d808a4c6；分支codex/rebaseline-v2-m1。阅读77c48a24、终点4b5e6468及最新运行/搜索安全代码2cbab03927fbe22cc2212f3fa4105862cfec0992均已push/核远端exact；v2代码无遗留未提交改动。
- 用户模型顺序cms-router/glm-5.3-flash → DGX/deepseek → DGX/qwen；凭据只由注册配置进入子进程环境，无全局服务/路由改动。

## 本节点完成及证据
- 本次运行恢复/搜索安全节点：4个输出恢复RED、worker凭据泄漏行为反例与owner9个检索状态RED后修复；相关71PASS、全v2 **341PASS/2.00s**、Ruff/JS/sh/600-80门通过，现有弃用警告1项。worker实际CodeBuddy/deepseek-v4.1-flash/max/165.156s/38tools/no fallback，owner已验收有限代码，非医学/浏览器会商。
- 只有finish_reason=length才同模型同输入扩大一次预算，8192→16384上限；不接受截断JSON，不改effort，不永久增大后续预算，失败后既定备用顺序不变。两次用量安全留痕，不保存推理正文；新真实运行已启动但未返回，不冒充实际通过。
- 搜索HTTP/传输/JSON错误不再把凭据URL或服务原文回显；HTTP200错误/损坏结果不判无竞品。SerpApi文档明确的Success+Fully empty仍是合法空结果；中国site备用blocked/failed有独立覆盖行。测试全离线，搜索提供方仍未配置。
- 次要终点根因3生产RED：解析缺完整定义、同字段last-wins、主要/次要及不同定义误合组。统一集合投影，完整定义/时间/事实引用保留；同名不同定义与主要/次要分开，不以字符串相近擅自认定医学等价。
- R4固定77容器来源重建：284研究/6580事实，580主要+2876次要全部进入C和摘要规划；2488非空次要定义补回，其他科学字段0变化。46份采用来源hash逐项核对，旧R3源/事实/HTML不改。
- 回执ciw-data/design-source-replay-r4/secondary-projection-audit.json：原JSON定位逐项核对次要定义，C投影/摘要各测量实例及共享研究上下文无遗漏；critical864=862match+2unknown/0mismatch。
- 完整研究最大111395字符，单终点最大1483、共同研究上下文最大3874；预算2RED后按完整终点分包，每包重复研究背景，保留研究分包标识/总终点数，不把分包算研究。151任务/最大23984字符，23研究分53包；不截定义、不提高全局24000预算、不新增平台或表。
- 本节点相关57PASS后，全v2 **318PASS/1.97s**；Ruff全src/tests/scripts、生产JS/fetch_assets.sh语法、600行文件/80行函数门通过（create_app既有路由例外）。现有TestClient弃用警告1项。仅证明所运行v2范围。
- 阅读节点已提交77c48a24：规范状态/年龄中文化、7列设计表、完整主要定义/组别说明、入排OR原句折叠、首页去重复工程KPI；保留检索覆盖。正文/按钮/图表字号16起、紧凑间距、充分用宽屏；当前次要终点/索引继续折叠，避免新增默认英文墙。
- 标签执行节点ciw2-m1-c-labels：实际CodeBuddy/deepseek-v4.1-flash/max、100.161s/24工具/no fallback。worker92例，owner整合；guard审计/review gate通过并归档，原prompt/report/stdout保留。有限相邻测试只读例外已记录，无科学/审美接受结论。
- 新阅读候选ciw-data/browser-m1/c-reading-r4-01/C.html：SHA2e965c9604eb3d810f1a558bf998f552ccd80ac7cb4a25ea8e81ea2f71286c28，12283219字节；284研究/282样本点/5明确零值。普通生产renderer生成，只读源DB；receipt绑定当前源码/模板/资产hash。不是创新竞品宇宙或模型报告验收。
- 康哲仅融合6.1.3/KZ6-1007-A08阅读层级、中文/字体、图表规则，不加装饰动画/框架；尚未获得真实屏幕视觉接受。新HTML较大，后续须实屏观察加载/折叠/检索响应，不用隐藏事实换性能。

## 当前真实运行及旧终态
- 新隔离R4 analysis_C已实际启动：project prj_f21d0823b44a/run run_a37cd8cba43b/句柄97920，scope=stage/pipeline_acceptance=NOT_RUN。完整151任务含580主要/2876次要；未返回，禁止定期轮询/重派/延迟杀。只等该句柄终态；旧42007不可再等。
- 源码固定ciw-data/runtime-code/2cbab03927fbe22cc2212f3fa4105862cfec0992/rebaseline-v2；115归档文件逐字比对、ECharts固定hash、实际import/Skill路径断言通过。源R4只读SQLite备份完整/6580事实，46不可变CAS blob校验后hardlink复用，避免重复存全文。新数据ciw-data/model-stage-r4/data；原R4/R3及旧运行不改。runtime.json及启动脚本SHA62001df7b7c65e5cf67be8ed9e8155c184ce0355ac7cd0c4bd3602ceaeae1c2b保留；只把两条必要注册连接传子进程环境，无凭据文件/全局变更。
- 隔离analysis_C：project prj_2f42f9210053 / run run_0e7b5e4a65fc / attempt0002已failed，42007正常返回，不再等待或重启。scope=stage/pipeline_acceptance=NOT_RUN。28合格缓存批/22非空/130要点，31有效模型事件=DeepSeek13+Qwen18；无新报告文件。失败GLM502、DeepSeek/Qwen输出8192耗尽。原回执SHA9e1ef51d10f79d5fc6be3795f4e14ef9483c443c1d005190b703ac29391acb53，owner审计ciw-data/model-stage-r3/attempt-0002-owner-audit.json。
- 已冻结运行源码91e8399c102948a9cfe2c6ba495096fd5ce90ad0，ciw-data/runtime-code/同SHA/rebaseline-v2；111归档文件对Git逐字核、ECharts固定hash、导入/Skill路径核对，61项开始/结束hash另记。SQLite备份before-attempt-0002-91e8399c.sqlite3完整。
- 该终态进程使用旧62任务投影，不含次要终点修复；61源码hash开始/结束完全相同，28批输出schema/当前verified引用核验通过，但不能提升为新C/M1全验收。有效model事件用量396104 total tokens不含失败请求，不能冒充完整成本。原冻结树/数据库/回执保持不变。
- 主模型真实曾144.583s返回空必需submit；产品主请求300s，显式备用时主路只试1次，DGX显式1800s。无备用保留3次；不伪造模型/effort。
- 原生产run_524b14044e4e三次恢复和隔离attempt0001均已终态failed；原回执不覆盖，不等待73175/87975等旧句柄。各次用过GLM/DeepSeek/Qwen，但不据此声称有合格报告。

## 已具备的共同底座
- 完整官方CT.gov分页实测18页/1787唯一研究=官方totalCount，原字节hash核对；只是来源分页，不是创新筛选完成。无50/15/30静默处理截断；预算未完保存ID/partial并明确failed。
- 摄取按完整来源+解析器版本原子采用、NCT/字节核对；失败旧current不变，旧源/事实只读，独立论文不随登记刷新自动撤回。network_checked/cache_reused/imported分开；缓存不伪装200或本次核查，A→B→A按实际观察读取。
- 纳排全候选分批、字面身份/明确ID、共享别名待核、失败单元恢复；当前不靠子串/去标点/同名取首项。完整原文分页、同项目授权；模型日志大于20k用既有CAS保全文，不记reasoning正文。
- 摘要引用当前verified事实；空数据不调用模型生成工程说明墙；无空图/缺失补0。无检索工具Skill首步仅结构化提交，必需字段/实际模型身份校验，安全错误回执和用量保留。
- ECharts6.1.0/Apache-2.0固定SHA b66b25aeb4df84e33199dc21694014d336d222cbd9deb0e5a7c14bd6aa0d0fd0。
- 同样6580事实只读查询优化实测6.3048s→0.0105s且集合hash相同；不是整页600倍结论。

## 未完成 / 待决定
- M1：完整真实模型流水线正向报告、创新范围、实际论文修订全链、同候选四桌面宽度1440/1600/1920/2560及筛选/证据键盘操作未签收；离线/来源组件通过不代替这些门。
- Ego47已失，原生选择题等待是否创建替代空间；不触碰其他任务空间/用户缓存、不用其他浏览器冒充实屏。此前1920空数据截图只对应旧负向切片。四宽/正向视觉/键盘均NOT_RUN。
- 全网搜索/微信未配置，中国浏览器适配和3适应症专家金标准未具备；相应覆盖blocked不是无竞品。M2≥95%召回未验收。
- M3 A / M4 B / M5全球与历史资格 / M6加固未验收。B组—药原设计关系、跨源分面仍待对应工作包；不借用C修复宣称全消费面通过。
- 历史截止日逐版本资格未实现；当前守卫在模型/来源前拒绝历史请求、数据/HTML409，表单暂不开放。不能只移除守卫称as-of实现；延迟旧源重放和跨源冲突仍待M5。

## 下一安全动作与复盘
1. 本次两代码节点白名单提交/push及远端exact已完成；继续保留全部v1脏树和原始来源，不提交CAS/数据库/原文，不再重跑已完成固定来源重建。
2. 新R4真实阶段已启动；原冻结旧阶段审计已完成，不再重跑。新句柄终态后核结构化输出/所有分包与引用、源码hash及正常renderer；仍是stage而非全流水线，不盲借旧62任务摘要或旧视觉。
3. Ego授权后复用一个专用空间验当前R4；先真实加载/检索/折叠与四宽，再验模型摘要和论文修订。等待不阻塞可独立的来源/产品工作。
- 最重要教训：来源库存在不等于消费完整，必须核对测量实例集合；不以测试总数、HTTP200、固定数量相等或旧截图替代临床/实屏验收。
- 每个根因族一次RED、一批完整修复、相关回归，提交前一次全v2；不用逐标签三路会商或新造流程平台。当前Goal active，无损历史保留，不是暂停或交付完成。
