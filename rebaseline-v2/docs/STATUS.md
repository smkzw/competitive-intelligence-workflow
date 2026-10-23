# STATUS

**2026-10-23｜用户已明确解除暂停，Goal=active｜M1/M2实施中，未交付**

## 唯一当前入口
- 产品权威仍为01_PRD、02_ARCHITECTURE、03_PLAN、04_AGENT_RULES；本状态不是新规格。
- 历史暂停/恢复依据：根Trellis任务 `10-23-rebaseline-v2-m1/PAUSE_HANDOFF_20261023_0810.md`，原件保留；本页为当前状态，历史paused/live句柄不覆盖用户新授权。
- 只实施英文工程rebaseline-v2。v2为单用户Web服务+内嵌9 Skills，不延用v1宿主包、编辑/分享及24门户旧验收合同。v1未知脏树保留，旧中文工程零接触。
- 分支codex/rebaseline-v2-m1；HEAD与本次核对远端exact均为 `2c02740f2caee990ca5cf808e98d27944c2875e7`。
- 当前M2根因包收尾中，完成当前全门后白名单提交；暂停WIP副本/diff/一致性DB不变。不reset/clean、不混入v1或运行资料。
- 模型cms-router/glm-5.3-flash → DGX/deepseek → DGX/qwen；凭据仅必要子进程环境，无全局路由/模型改动。

## 阶段进度（不是整体完成百分比）
- M0：离线骨架、部分公开来源冒烟具备；不是产品交付。
- M1/C：真实来源/完整终点投影和报告组件已接通；全流水线、论文修订与视觉交互未验收。
- M2：中国反向扩展代码在工作树，相关回归通过；中国浏览器适配、3份专家金标准、≥95%召回未完成。
- M3/A、M4/B、M5全球/历史资格、M6加固：有骨架/切片，均未完成对应正式验收。

## 同一真实模型阶段已恢复（原暂停记录保留）
- 新句柄49763已实际启动attempt0002：同run/同冻结2cb代码/同数据/模型顺序；预检全部冻结hash、46源字节、DB完整性及51缓存存在后恢复。脚本ciw-data/resume-r4-20261023.py；未重跑bootstrap/来源，不覆盖attempt0001。不定期轮询/重派，终态再核实际模型、缓存和渲染。
- run_a37cd8cba43b / prj_f21d0823b44a / attempt0001 / scope=stage/analysis_C；数据ciw-data/model-stage-r4/data。
- 用户暂停后只向已确认子PID69497发送SIGINT；子进程及父69466均退出，句柄97920已terminal，不再等待/重派。
- 使用冻结2cbab03927fbe22cc2212f3fa4105862cfec0992，冻结源码开始/暂停hash一致，46来源CAS逐项校验，6580事实保留。
- 按冻结生产任务键只读审计：**151批，51缓存有效，100待做；33非空、195条分批要点**。均按schema及当前verified引用核验。不是195条最终结论，归并未执行。
- 51有效模型事件均实际DeepSeek-V4.1-Flash-TF。有效事件480519 tokens不含失败/中断请求，不是总成本；成功事件output_recovery=0，不宣称真实扩容已验证。
- run/analysis_C库行仍running：原脚本未捕获KeyboardInterrupt。原STARTED回执不改，本暂停回执明确进程已停；不能误当健康任务或伪造failed/succeeded。
- 恢复必须同run/冻结代码/输入/规则/模型，复用51批，只重发未提交中断批并做剩余100批及归并/渲染。原start-r4脚本会新建目录，禁止重跑。
- 本地ciw-data/pause-20261023-0810/pause-audit.json含完整键、源/代码/WIP/截图hash。
- SQLite一致性备份integrity=ok，SHA e9c18f2153ac95cff0495839d38caa4bc38a7cf1c46342fe0bcb168d3af2ce3e；不重复复制CAS。
- 原attempt回执SHA cd99f6d06a99a5afabf29ed8a8b6b2055a576957b4ab9dcac396d846eaaefe2e未改。暂停前12文件副本及tracked.patch另存，不覆盖未知工作树。

## 当前C页面：已实看，视觉FAIL
- 用户已授权替代Ego空间，实际 **53 / p1**；暂停handOff保留，未finish、未清缓存/改登录，不再使用“授权待答”旧说法。
- 当前ciw-data/browser-m1/c-reading-r4-01/C.html：SHA 2e965c9604eb3d810f1a558bf998f552ccd80ac7cb4a25ea8e81ea2f71286c28，12283219字节。
- 来源组件284研究、580主要/2876次要终点、282样本点、5明确0；不是创新药全集或模型最终报告。
- 四张1440/1600/1920/2560×1080首屏截图均实看：同目录 `{宽度}-actual-first.png`。截前同调用确认innerWidth/scrollWidth等于目标，无整页横向溢出。
- **FAIL**：1440/1600期别饼图标签截短；两图绘图区高504px、卡片约596px，对照表接近首屏底部，主任务空间不足。尚未修复，不写“图形优化完成”。
- 初次1920-first.png实为1728×659（跨调用设备尺寸被还原），保留但退出验收；后四张actual截图才是有效宽度证据。
- 筛选page.fill因控件不在实际viewport超时；只读诊断仍空查询/284行。不是查无数据，也未证明产品筛选坏了；筛后/展开/来源/键盘均未完成，不记PASS。
- 只读预览63024/PID89464及旧8767/PID45481已停止、监听消失。HTML未删；p1暂停后指向已停预览，恢复重启单文件只读预览。
- Ego提示更新，本轮未升级，需用户批准，不能借此换浏览器。

## 工作树中的M2根因包
- 新生产顺序：发现→candidate_triage→universe_expand→coverage_review→后续；复用coverage-review Skill，无新增表/模型路由/平台。
- 别名/靶点/企业生成中国CT.gov及三登记/CDE/NMPA路线、全球CT.gov/搜索路线，最多3轮；预算pending可恢复；来源/解释分别缓存；blocked/failed不判空成功。
- 已排除候选不扩展，unknown保留。真实476候选元数据只读规划555种子/3330查询，非实际已跑查询或宇宙完整性。
- 隔离真实中国CT.gov查询1研究、17待查、0模型，ciw-data/expansion-source-smoke-01/receipt.json。随后发现otherNames含Placebo，不能作主动药别名；旧源/回执保留。
- 当前将既有精确placebo/安慰剂规则复用到别名、旧数据身份读取及扩展种子；原始otherNames仍保留。3RED后相关37PASS；扩大身份/纳排/恢复/扩展相关 **64PASS/1.10s**。
- 已捕获真实源离线生产重放完成：1研究，原控制别名保留、主动药匹配false、无控制检索种子、0网络/0模型；旧smoke回执hash不变。回执ciw-data/expansion-control-alias-replay-01/audit.json。当前最终v2 **361PASS/2.69s**、Ruff全src/tests/scripts、生产JS/sh语法及600/80尺寸门通过；1项既有TestClient弃用警告。不是中国宇宙/医学/视觉验收。
- 新expansion.py/smoke_expansion.py及两测试、修改的身份/CTgov/stages/两Skills/conftest等已保全；未知agent_health及v1改动不提交/清理。
- PRD/ARCH/PLAN已原位同步triage→expand→最终review及恢复/原始别名与身份采用合同，无第二套产品规格。

## 已有底座与未交付项
- CT.gov完整分页18页/1787唯一ID=官方总数，不等于创新药闭包。源版本原子采用/失败旧current不变；network/cache/import分开；独立论文不随登记刷新撤回。
- R4固定77容器重建46采用来源/284研究/6580事实；2488非空次要定义补回，其他科学值/上下文0变化。580主要/2876次要完整投影，按整终点+共同上下文分包151任务/最大23984字符，不裁尾部。
- 字面身份、共享别名待核、全量游标/全候选/未完单元恢复已具备；B组—药设计关系仍须对应包验收，不能借C证明。
- ECharts6.1.0固定hash、中文状态/7列设计表/完整原文折叠/16px底线已实现，康哲融合阅读功能子集，未获得审美接受。
- 旧R3 attempt0002终态failed（28旧批/0报告），原生产run_524b14044e4e旧尝试也failed，不等待/重跑或拼接R4通过。
- 搜索/微信未配置、中国适配/金标准未具备；历史as-of未实现且启动/数据/HTML守卫拒绝，不能移除守卫冒充完成。
- v2最终交付未完成：M1全链路/论文修订/视觉交互，M2召回，A/B正式门，历史资格及加固均待后续。

## 当前有界顺序
1. 读本页/暂停文档，核HEAD、WIP、冻结源码/DB/来源hash；不重跑摄取/来源重建/51缓存。
2. 同冻结代码/同run/注册环境接续100批，原run_live.py显式--resume-run与--only-stage analysis_C，保留attempt0001并生成新attempt。
3. 前端独立根因包：紧凑概览/期别完整标签；复用Ego53，四宽同候选实测检索/展开/键盘。不缩字体、不隐藏事实。
4. M2真实源离线反例→原位PRD/ARCH/PLAN→相关批→一次全v2/Ruff/JS/sh/尺寸门→白名单提交/push/远端exact。
5. 当前候选完整研究、论文修订及M2–M6正式验收未过前不宣称交付；现有授权继续实施，不形成无必要阶段性暂停。
