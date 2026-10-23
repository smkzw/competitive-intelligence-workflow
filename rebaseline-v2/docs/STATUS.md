# STATUS

**2026-10-24｜Goal=active，连续实施｜M1–M6未全部完成，未交付**

## 当前入口与授权
- 唯一英文工程根内rebaseline-v2；产品权威01_PRD、02_ARCHITECTURE、03_PLAN、04_AGENT_RULES。本页替换更新，详细历史在根Trellis任务10-23-rebaseline-v2-m1/implement.md及Git，不另立规格。
- 单用户Web服务+内嵌9 Skills；v1多宿主包、编辑/分享、24门户不是v2发布门。未知v1工作树保留，旧中文工程零接触；不得reset/clean/add-all。
- 分支codex/rebaseline-v2-m1；本节点父HEADc13a155c72ea8061a13160580792dcb8b45d6f01（下载组件已push并fresh remote exact），本恢复节点提交以Git记录为准。
- 用户已解除暂停；历史暂停点10-23-rebaseline-v2-m1/PAUSE_HANDOFF_20261023_0810.md仅供恢复，不覆盖新实施授权。
- 模型cms-router/glm-5.3-flash→DGX/deepseek→DGX/qwen；密钥只在必要环境，不入文件/提示词/日志，不改全局路由。
- 用户永久授权本项目Ego专用空间缺失时自行替换，不再询问。目前63/p1复用；不改登录、缓存、其他任务空间或升级浏览器。

## 当前节点：旧登记详情兼容与真实扩展
- 77a318641783291a36312df1f1bbbe088e2d32c7已push/fresh remote exact。固定464条列表中确有10个旧_p标识；详情只收32hex造成3生产RED。列表/详情现复用单一valid_detail_id合同（32hex可带_p、正整数_p），不开放路径/查询/会话字符串，不去掉_p猜新ID。相关156PASS/0.43s；当前完整v2 **1014PASS/6.35s**、Ruff全src/tests/scripts及详情MJS语法PASS。
- ciw-data/china-legacy-detail-live-01使用原06/07列表DB的隔离只读拷贝，普通生产ingest_trial在Ego63/p1实际查询CTR20131043/1317_p、打开原页并采用22事实/0模型/原来源不变，源码运行前后hash一致。来源d42fa4eb24777332e4cae85b9220fe279dc2594e9550f2c4bd3b33b74a36861a，原文8fbf69f73cc9762ebe1d4502298b8baee6b5391f697f27850d1da0e3c43d828c；C5191ada0e73d3dd6a11a3ff923074b7959f96fe8c437199c706a8a6cb2e16e75。不是十条详情/完整M1/M2/医学视觉接受，随后扩大其余9旧ID完整族，不为凑数量跳过旧格式。
- 本轮新增候选/读图证据各1.3–8.7MB，测试缓存124KB；CAS已按不可变摘要硬链接复用，不复制同一原文。当前均有恢复/修复证据用途，不为124KB缓存收益清理唯一现场或别的agent_health日志。
- 旧归并任务只以原生文件事件等待唯一终态receipt，私有await-r4-terminal-01.py不读取进度/不固定轮询，也不重做151批；终态仍须owner审查。Goal active/连续实施。

## 上一完成节点：明确范围与来源失败的报告可用性
- 上一8596d3dd1718e274205a92822d167732c8f5925b已push/fresh remote exact。当前根因3RED/4正向加CT.gov明确排除RED后，相关83PASS/1.25s；完整v2 **1004PASS/6.94s**、Ruff全src/tests/scripts及portal.js语法PASS。只复用既有scope查询、非阻断IncompleteWork和下游恢复机制，不建新执行器。
- 中国抓取、设计C/结果B/管线A当前查询共用明确范围：研究本身排除或全部已关联药物明确排除时退出；混合父候选、unknown、无关系研究保留，不推断为纳入。CT.gov搜索再命中已明确排除试验也不重新采用。原事实/来源不删；B同一保留研究的全部已记录组别不因某药排除而被删。
- trial_evidence未完/单源失败继续渲染现有资料，但run仍failed、保留具体ID/原因。测试普通真实Stage定义：3项中1失败仍渲染2项，恢复仅补缺失1项后重建3项/变succeeded；不是mock整条执行器，也不是实际新来源网络验收。
- ciw-data/current-scope-live-01只在真实34事实/来源的隔离副本施加明确标注的控制性排除，再恢复unknown：A/C计数2→1→2、全部事实/来源行不变、恢复C与3990bfbe…逐字相等。不是专家纳排判定；此设计夹具无B结果，B仅有独立单测证据，不借它宣称真实结果范围验收。
- 下一实际扩展前发现兼容缺口：列表已支持32hex_p/正整数_p旧ID，详情却只收32hex。先复用列表合同关闭此族并实读旧记录，再扩大代表切片；不悄悄跳过旧研究以凑10条通过。旧52075保留冻结及已完成模型批，不固定轮询/重启。Goal active/连续实施。

## 上一完成：真实中文入排表达与阅读收口
- 中国原表流水线节点 **ec43388cbdbd6071518e1875ef295d42ec9ff718** 已push/fresh remote exact；当前阅读节点提交以Git为准。新增12族用例，初始6RED/5正向后扩充小数访视反例；相关61PASS/0.61s，当前完整v2 **996PASS/6.46s**、Ruff全src/tests/scripts及portal.js语法PASS，64生产Python/600-80规则PASS（create_app既定例外）。不为私有浏览器脚本修改重跑宽门。
- 既有源片段读取器支持IGA离散选择one_of=[2,3]（非区间）、同句紧邻BSA双侧界、括号AST/ALT及SCr/明确中文正常值上限单位；连接词、全部原文、原位置与段落保留，不跨行/条款/其他指标借值，不补未写单位。没有新增事实/模型/平台；新字段依据标签具体化，少字来源窗收敛至760px、标题20/body16px。
- ciw-data/china-reading-current-01复用相同34事实/事实SHA7f6d368f…、来源字节不变，0网络/模型；新C **3990bfbea9995292da71ee2e4f5da05d56e5c22961c2af76361581928fca0c2b**。真实CTR20263748现6项表达与原文一致。四宽×入排/来源8图在browser-03逐张实看，quote逐字/原文hash/深红700下划线/双侧值与ULN/合法来源/760宽/实际Esc回焦/AD101查询均通过，owner-review.md限定组件接受，不称完整M1/M2或全C医学视觉接受。
- 前两浏览器轮次几何断言失败留存：受控诊断证明1440下ECharts画布仍为上一尺寸时scroll1494，真实ResizeObserver/动画结束后scroll1440；第三轮等待实际尺寸/动画而非隐藏overflow/固定sleep或改产品断言。不是全仓代码失败，也不能把失败回执回写PASS。
- 下一有界项：核对native CTR与既有药物纳排的范围继承，按FR5检查来源单项失败后报告仍可得且运行不能假称完整成功；随后扩大真实来源设计切片。旧52075只在真实节点边界查终态，不复跑151原始模型批。Goal持续active，无暂停。

## 上一完成节点：中国登记原表已接入普通设计流水线
- 当前父HEAD6c8ef552；本节点正式提交见Git，以下不借用961旧门。2年龄/范围RED、4普通流水线/身份RED及3来源运行/原名字段RED后，相关204PASS/1.07s；当前完整v2 **984PASS/6.30s**、Ruff全src/tests/scripts PASS，64生产Python/600-80规则PASS（create_app既定例外）。5JS语法通过；首次shell检查错指不存在run.sh属NOT_RUN，实际scripts/fetch_assets.sh已单独通过，不为命令笔误重跑全仓。
- china_design按原字段保留所有终点/条件性PK、全部强度和对照、完整入排、年龄/范围、健康受试者、申请人及不同地域/计划/进度/实际人数；不从登记适应症推患者人群、不猜MAH。明确“曾用名”与主名分开，原字串保留。china_ingest核项目/run/CAS/CTR/详情/原文后整包原子采用；A→B→A及幂等/失败回滚/独立来源保留已验证，复用facts/links/stages，无新表/平台。
- 普通trial_evidence现处理项目内所有未排除CTR（默认无数量截断），逐来源/规则恢复、失败保留ID与原因，新run再核查；extract-design不再重复改写已结构化中国表。单元测试mock只替代网络边界，不是全宇宙实跑。
- 两真实捕获源在ciw-data/china-native-current-02隔离采用34事实，全部引文回原文存在、幂等二次新增0；两研究3主要+3次要终点、2/3组、18–45/18–65岁、健康人/患者信息、申请人和I/II期同源呈现。事实SHA7f6d368fb096fdb2859f0d3b9e35beb74f79a2b9dad097665dd28632da73dbb6；C **41f770795da4de8a5cf31e99d201b57397cf2d0d3b80a15bb19722a6cbf20e78**。0模型/新网络，属于既有真实源重放，不伪称本次全流程新检索；原两来源/旧DB/失败提案不改。
- Ego63/p1四宽×双研究/筛后单研究/完整入排/来源16截图及Esc真实回焦/查询保留已运行。原文逐字相等、阈值深红/700/下划线样式实测。初轮图捕获在动画结束前，原图保留；稳定等待动画后重拍在browser-stable-01，16张已逐图实看/owner-review.md留范围结论，不宣布全部视觉/医学或M1/M2通过。实看暴露新一族未覆盖表达：IGA“2或3”、BSA“≥5%且≤20%”、AST/ALT括号及中文正常上限应完整强调；原文均保留但提取/强调不完整，下一有界根因处理该族，不重跑来源/模型。少字来源阅读偏宽、部分新字段依据标签泛化亦保留待办。
- 原52075在此节点边界同handle等候仍pending，无终态回执；冻结runtime/151原始批/780要点/原DB不改、不轮询或重启。继续未完项，不设置暂停点。

### 本节点初始现场（历史观察，不当当前结论）
- 上一节点6c8ef55255542a6ee6f35d473a3bb3e2ea6770f9已push/fresh remote exact，完整门961PASS及备份/来源读取记录均已保全。现在直接处理共享事实/快照/临床身份消费面，合同尚在同一owner闭环，不再额外派一个同根因writer或重复模型改写；按材料性不确定和两次无新增证据失败重新评估协作。
- 新china_design.py纯解析器与8成族用例，缺模块RED→29相关PASS/0.16s/Ruff。先按已捕获表格复制原分期/随机化/设盲、完整入排、全部终点、全部强度组别、申请人、计划/实际/已入组进度及地域；不相加、不猜MAH、不由缺失补0。未填与解析不明分开，保留原始JSON定位与原文。
- ciw-data/china-design-parsing-01只读两实际源：CTR20264009源be66e5e4…→16候选事实（13逐格复制/3未知）、1主要+3次要终点/2组；CTR20263748源ee5ed367b2e48a21bf373b760d61304759983985e2783193a852a2498918ad31→14候选（12逐格复制/2未知）、2主要终点/3组/国内计划132。原条件性PK定义完整；次要终点未填不造一项空记录；所有quote经原文重读存在，0模型/新来源/事实采用。**尚未接DB原子采用、当前快照、全量CTR流水线或新页面验收**，不能用29代替新全门。
- 原AD101源中浓度标签与规格文字存在不一致，原样保留于组别/用法，不推算、对调或宣称剂量关系正确；该临床源疑点仅在内部记录，不向正文添加泛化防御提示。下一步围绕原子整包/版本与幂等/失败回滚、独立LLM事实保留、C临床身份与原分期/入排高亮/图表—表格同源做一批生产反例，再一次相关回归与节点宽门。Ego63/p1继续复用。

## 已提交节点：登记详情/来源绑定与数据备份（6c8ef552）
- 恢复节点ac7731dca91191ae83b65643fa0662eb8e2ad264已push/fresh remote exact。owner在同Ego63/p1观察中国登记详情；不会用列表期别/公司文本冒作详情或MAH。
- 新china_trial_detail工具已取得一个真实CTR的7临床表/6内表，完整中文入排、组别、终点原文保留；请求先核本项目列表来源/CAS/CTR/详情ID，读源不直接采用科学事实或法律角色。ciw-data/china-detail-live-01原普通列表1条/新详情源be66e5e4ab7488c32494e4c57c1662ff3a408aa426b1c0b73eb2c690362ac065、原文229a46ac…，本次browser_checked/同run二读cache_reused分开，0模型/原事实/实体/源不变；不是全量登记详情或M2接受。
- 完整族反例覆盖错CTR/详情/URL、重复身份、内表篡改、未绑定来源、跨项目、缓存损坏、同run/新run。首次模块缺失RED→141相关PASS；source_id合同4RED/1PASS及同URL错研究2RED后，现160相关PASS/0.49s/Ruff/新MJS语法PASS。来源同URL不等同同版本：明确source_id还须属于实际读集/项目/URL/CTR；无明确ID只能唯一匹配，错误明确ID不能回退借另一来源。完整当前门尚未执行，不借873历史门。
- 实际模型82760已终态failed：ciw-data/china-detail-model-01的90冻结依赖未变，真实GLM-5.3-flash3次/无模型错误/无fallback，源工具1/错误分页1/提交1，5提案但均错填域名/未绑定来源。模型说截断，实际工具日志有完整原文及source_id/URL，不能据模型自述认定传输截断。验证脚本还绕过extract_drugs的drug补全而KeyError，0事实采用/无C文件；不是生产verify本身缺drug。原回执/提案/源/冻结代码全部保留，无重键或冒称接受。
- owner删除模型payload重复JSON表及内部detail_id，精确来源置前、完整source_text仍可达，原始内表保留CAS。新增1RED后相关166PASS/0.61s（含5CLI分派mock测试）。新27751已终态：ciw-data/china-detail-model-02冻结90依赖/绑定runner摘要，完整普通extract_drugs→verify→C，真实GLM-5.3-flash3次/主路，无模型错误；源工具2次（其中同run缓存复用）、提交1。7事实全部正确来源绑定，仅3已核实/4因模型在值内加条目号、解释及单位字符串等未通过逐字/数值核验；主要终点仍漏提。**科学未接受，不等于完整M1/M2**；不改引文或放宽守卫凑PASS。
- 当前代码另用china-detail-current-01对同7提案/同源版本无模型重放：7幂等、状态/事实不变、同原元数据C字节仍e20204e…；新隔离展示副本只去除内部测试focus（原模型任务/DB/HTML不改），C为eb49768b…，尚未视觉验收。下一根因是按v2规则直接解析原有中文结构化临床表，接完整终点/入排/申请人身份，不为改措辞再跑模型。Ego63已无运行占用，可复用；旧52075独立归并未触碰。
- E03执行26997已终态：首路CodeBuddy rc0后runner按manifest走ZCode启动失败→Pi/MTPLX空输出→同Pi会话GPT6Luna/max续接，最终实际openai-codex/gpt-6-luna（runtime确认）、session01a16a3e-679c-7000-83eb-9264ba3c0a60/602.137s最终轮；顶层effective仍CodeBuddy，不能冒作实际终审模型。raw工具计数945未独立复计，不按此宣称独立操作/费用。首路最终输出/转备用理由保留不足，不反推首路质量失败。不是独立复核意见。完整345行/572测试及报告923ce19d…已读/先存worker-source.tar；原源码ba2c1362…/测试3e984804…均保留后才改。
- 最终worker已补符号链接祖先/重复清单键等问题；owner另组1RED/56PASS暴露SQLite backup不受连接timeout约束，现只对无进展BUSY/LOCKED加现有30s时限，健康拷贝不受总大小时限。57相关PASS/1.34s/Ruff；guard audit-execution/review-gate PASS，无额外Hermes/chair/conference。备份是DB+快照引用CAS，不含配置/凭据/任意缓存/外置大日志/生成门户，不是安装/分享/完整会话备份。
- 真实ciw-data/data-backup-live-01普通CLI exit0/0/1：1026事实（668结果）/1引用CAS/全部10表恢复逐行相等，原DB/存在的WAL/CAS及备份字节不变。A6724f004…/Be1b6903…/Cf97c7fd2…与同当前renderer原资料输出逐字一致；坏副本拒绝/无目标，0模型/来源请求。清单SHA bdb602c9ed171d7897588fcbb1ec1462de0c5e81a5f52e6d2530577f7bfc765e；不是完整M6或新视觉接受。
- 首次当前宽门10FAIL/948PASS揭示新增source_id默认None破坏旧提案“省略”语义。wrap序列化只省略真正未传入ID，明确null仍严格拒借来源；旧修订/事务合同不回退。相关124PASS/1.97s→当前完整v2 **961PASS/5.94s**、Ruff全src/tests/scripts、5JS/sh语法PASS，1既有TestClient警告；61生产Python/376函数符合600/80（create_app既定例外）。前次FAIL不改PASS；当前门不是旧冻结模型或整个产品通过。

## 已提交节点：CDE缺页恢复（组件，不是M2全验）
- E03句柄58566已真实终态，不再等待：CodeBuddy/codebuddy-cli/deepseek-v4.1-flash CLI max/session01a16a25-0fec-7d2a-832a-957eb0d3e422，278.974s/53tools/无fallback；modelUsage确认模型，后端effort/费用未知。原报告d7e4aec4…及两文件原字节先存worker-source.tar。owner读完整输出后新增4RED，修正真实受理元数据method=browser_form不匹配及非法complete标记；独立分工仅两新文件，owner持有共享调用者。
- 同项目/run/栏目/原始筛选/CAS限定；两生产MJS实际读新第一页，内容/总数/页长变化则全采，匹配则原生跳缺页；宿主复验新读/复用页和锚点，合并后完整集合校验。原始页/来源不改，cache_read与browser_checked分开，复用页保持原observed_at。实际脚本空结果反例1RED/4PASS修正新读页号1→真实0；来源失败不当零值。
- 218相关PASS/1.00s→完整v2 **873PASS/4.15s**、Ruff全src/tests/scripts、4JS/sh语法PASS，1既有TestClient警告；59生产Python/342函数符合600/80（create_app既定例外）。首次语法命令误用了不存在charts.js，未执行，随后仅重跑实际portal.js及3MJS；不把最终shell退出码冒充错误检查通过，不重跑已绿873套件。
- ciw-data/cde-review-recovery-01：首次明确注入第6实际页后失败，原源f64ce33632b8aa14a87641500ea9dbbeebb1d6be7d9dd7e2e38df9ced5bc0f17。第二段完全无补丁普通CLI --resume-output，同prj_49399f4c7e8c/run_1141c35995de复用2–6、新读1/7/8/9，闭合9页431条/精确匹配1，新源22e34853f68b7b2c214e2ea96f7441968c84ccef10faa89e5f5d08572bb60c65，13源码及入口hash前后相同。owner-audit逐旧页/新页/摘要/读集/模型事件核对，0实体/事实/模型。原子来源登记另有imported事件，原审计漏计后修正为实际5事件；未改源/重跑浏览器。受理恢复有生产适配器和实际MJS反例，真实链只跑审评序列；不冒称其他栏目、视觉或M2通过。
- 执行audit首次缺机器可读immutable route行而错误比对当前高峰route；按原manifest03:00离峰/原prompt/真实runner补回精确行并明确为派发后审计修复，原件不改。audit-execution与review-gate随后PASS；不是预派发audit/独立医学复核。无Hermes/额外chair；保留原失败与原输出，不以过程门替代产品验收。
- 健康52075固定ec32归并仍无终态输出；不轮询/重派/重键151旧批。下一有界工作：中国登记详情/其余来源及临床阅读缺口；只在节点完成后核对模型终态。Goal持续active，不设置暂停点。

## 已提交节点：当前事实JSON/CSV下载（c13a155c）
- 复用现有项目/鉴权/current_facts，标准库export.py在单一DB读取快照中关联本项目精确来源版本/摘要/实体；一条只读下载路由+工作台两链接。不调用模型/来源，不读CAS全文/日志/meta，不造共享包或备份。原facts API不变；缺失/跨项目来源保留None，不按同URL挑新源。
- JSON保留原始类型和context/quote；CSV用value_json/context_json区分0/null/false/空串/结构化值，文本公式前缀显式转义并列csv_escaped_fields。过滤、鉴权/404/422、历史日期/非有限值409均覆盖，不把坏值补0或null。6整族RED→19相邻PASS→扩展类型/公式/异常反例27PASS；当前完整v2 **828PASS/3.95s**、Ruff全src/tests/scripts、4JS/sh语法PASS，1既有TestClient警告；58生产Python/332函数符合600/80（create_app既定例外）。一次错路径仅未收集测试，修正后运行，不算产品RED。
- ciw-data/fact-export-live-01：原同源实际有**1026当前事实，其中668为result**。早前记录“668事实”是结果范围简称，不能当全部DB事实数量；f08e6c7a485d88d1bf899d05435ae6c788ae70e378bd2906ea007dc1bbc58157仍是完整1026集合hash，不改旧回执。JSON82317b8783a5761a4c8705a2400a501d69ec6ce6cdca38514fee38b35f6fc1c1/1583305bytes；CSV790c81f4daf91746e0a74a1d788532e4a76cb3e6d3ee64ec8311daa187388851/1115218bytes。
- 实际生产HTTP端点及Ego63/p1原生点击两次下载/saveAs，两个文件与HTTP逐字一致；owner-audit逐ID/严格JSON类型/完整context、原文与精确来源digest重读核对，旧事实/源不变，0网络来源/0模型。原浏览器NOT_RUN回执不回写；新browser-12记录真实下载。工作台视觉截图当时最小化失败，NOT_RUN，不借旧截图宣称通过。
- 浏览器已回固定B文件，停工作台自动刷新；明确核对自建PID41656(probe-fact-export-01.py)/84559(preview-publication.py)后仅SIGINT停止两个临时服务，源/下载/截图/回执均未删，健康52075未触碰。下载不是完整M6；队列/取消/总成本/备份仍未完成。

## 已提交节点：单位与报告正文清理（df1846fa）
- 同一labels.py精确映射常见单位/统计形式，B图/表共用，原始单位和统计可原位展开；未知文本保持原样，不换算值、不把比例/概率混同。移除A/B/C检索路线正文和无用读取；项目工作台仍显示实际路线，生产Web测试确认，不删覆盖证据或来源。
- 7RED/3PASS→145相关PASS/0.61s；旧测试要求把内部route_id塞在报告的实现断言迁移为实际工作台HTTP200含记录、报告无内部诊断。当前完整v2 **814PASS/3.75s**、Ruff全src/tests/scripts、4JS/sh语法PASS，1既有TestClient警告；门后仅labels说明文和规范/记录更新，无行为变化。
- ciw-data/browser-current/outcome-reading-02只读同668源重渲染A/B/C，事实仍f08e6c7…、0网络/模型；A6724f004b417bb74b2ceb7aebd1aa6298ffe370b31071faebf6a5c7f85971318，Be1b6903adb0fb690e71edad3a48d604c074feae438485484916ab96dfd331661，Cf97c7fd2b25ec7049d5eaf2703d40573590080f44d6eff0b263e3bdc8059cfd5。移除无用coverage查询及说明文后，当前renderer重放逐字等同，owner-audit另绑定当前消费hash，不回写原回执。
- Ego63四宽18截图全部实看，16采纳：B临床/PK各四宽、A/C各四宽；2560初轮两图动画中态拒收保留，仅补两张稳定图，不重跑其余14张。按实际ZRender animation.isFinished核终态，未关闭产品动画或改用户偏好。单位显示“分·均值”“ng/mL·均值”，上下错位减少压线；原单位实际展开、实际glyph→正确事实/来源均通过。大值图顶端标值留白及英文指标标题仍须后续根因包，不宣称完整视觉/医学接受。
- 本轮截图06最小化失败/07Ego window-target不支持均保留；按用户已有授权用原生Raise恢复同物理Ego窗口后续验收成功。原生树附带的其他页面未操作、未抄入证据；不改登录/缓存/空间/版本，不再提Ego问题。下一有界任务仍是未完成来源/临床语义与终态恢复，不为同一像素反复全仓会商。

## 已提交节点：B结果领域与同查询阅读（55b3c5fe）
- 原执行311行分类器/59测试不能直接采用；先归档原字节，再经一次独立源复核，按PK/PD混合、分析物身份、缩写展开、生存终点、描述背景五类根因纠偏。现97行标准库投影，七域仅改变阅读，不改来源、事实、单位或数值资格，不新增本体/药物字典/审批。
- B先按真实同源组—干预绑定，再按测量词及明确局部分析物投影。PRIMARY/SECONDARY不决定疗效。领域+文本共同驱动图和完整表；有临床结果时优先临床，其他领域/缺数值仍可达。
- 生产挑战18RED/1PASS→缺domain整合RED→113相关PASS/0.64s；一处描述回退故障修正后同族全绿。当前完整v2工作树 **804PASS/3.37s**、Ruff全src/tests/scripts、4JS/sh语法PASS，1既有TestClient警告；57生产Python/328函数符合600/80，create_app既定例外。不是v1/全产品门。
- 真实已捕获官方记录只读生产重放：668结果/70图组完整保留，临床602/安全12/药代45/免疫原性6/复合未解3；默认临床55组。3条PK/PD原值及ug/mL、L/ug保留，不误写全为药物浓度。0新网络/模型，事实SHA f08e6c7a485d88d1bf899d05435ae6c788ae70e378bd2906ea007dc1bbc58157不变。
- 候选ciw-data/browser-current/outcome-reading-01：B HTML SHA94b4551c7ee3b34a5cddd72b118a0430aa75110d08aca02b6592e1aa71b48c10；9消费资产逐hash绑定、JS/CSS/ECharts实际内嵌核对，来源container50bc0483d2b3cfb6ebe207a71afe94575ca15e30acc707dbb4634ab56532dee2。
- Ego63四宽1440/1600/1920/2560共20截图全部实看：四领域16图+临床筛后4图；16px/无页面横溢，查询200/668、空0隐藏图、恢复668/70。实际mouse glyph→fct_035e967c5d20正确行/焦点/来源URL。owner-audit.json独立核对全部ID/图片/源码，原NOT_RUN回执不回写。
- 只接受领域/查询组件，不接受整个B美学或医学横比。实看遗留：英文长指标/单位、PK局部标值拥挤、覆盖诊断占屏、安全图、跨研究语义及论文绑定。file预览导航不是正式服务/导出验收。
- 仪器问题分开保留：两次误写测试路径均未运行，不算产品RED；初版截图用不存在的isFinished失败，改为预先监听实际finished后完成；私有回执键名错误只重建回执，已有HTML逐字相同不重复生成。未删除旧失败证据。
- 执行真实CodeBuddy/deepseek-v4.1-flash/max611.31s/35tools/session01a169ed-4f92-7209-b7e9-eefaebc32206/no fallback，原报告b02c42e650f2295cc6c66a8a0c743dcdf95cd88b363e0e234ba8c7e6f17a4007。原源码a2bf0a49…/测试3c02130e…保留于worker-source.tar。
- 独立C03实际Pi/openai-codex/gpt-6.1-sol请求high149.385s/38tools/session01a169fb-1cbf-7000-abda-37ad228f8650/report6eb7a94cc0c1af122d5528fbcd9739dd44397036824191597cdfa5e1e0c0c6a4；首选GLM启动失败、其余两路不可用后走manifest fallback。runner顶层effective误留GLM，不能冒作实际模型。内部effort不可独立证明。原冻结审阅REVISE，owner落实修复；guard review-gate PASS，非专业批准或新候选全量独立review。

## 健康模型与恢复：不得重跑151批
- 唯一仍待终态的模型句柄 **52075**：隔离ciw-data/r4-synthesis-01，冻结ec32ca47c76e999565d724c8f994b74fa075c16a runtime；project prj_f21d0823b44a/run_4cc7aca0a632，SYNTHESIS_ONLY_COMPONENT_NOT_PIPELINE。
- 151原研究批逐输出hash固定，780完整要点，真实focus/metadata后首层76包/最大7999字符。旧DB/runtime只读、CAS硬链接，新DB备份；不重做来源/研究批、不迁移key。当前源码/Skill变化不作用于冻结运行。
- manifest/started/findings在上述目录，实际响应模型、终态及最终summary尚未核，不记PASS。健康运行不固定轮询/重派/强停；阶段终态后核receipt、实际models、部分缓存及原源hash，失败只恢复兼容归并。
- 旧49763已failed（wrapper0不是成功），run_a37cd8cba43b/attempt0002；GLM502、DeepSeek空结构、Qwen8192→16384仍length/缺提交。151/151缓存及780要点已全核、46源/6580事实/62runtime源码不变，0归并缓存。terminal-audit-20261024.json SHAa202e67d04b84b94ca43bcf4117b2e56c1d587702e1a6716c6953aeabd91df79。
- 原R4事实SHAf903dc7b89a22bc4b1c83edb8696d7df96699166e3986b089700cd2828f1be53。成功事件DeepSeek1/Qwen107、tokens1339395只为该成功事件范围，不含失败/历史，不是完整成本。所有其他旧模型句柄均终态，不继续等待。

## 已提交组件与可复用证据
- **69fafc25 CDE新报化药IND**：普通生产工具9页/431行→CYHL2600085精确1行，source90e40cf0f9b822811ffe7a10542b46deab1fb7093ea128f8cd00875d28246ba8，12源码+CLI不变，0新实体/事实/模型；无本项目既有受理绑定所以0追加引用。原框只是定位/高亮，非过滤；行级状态与本页图例专业状态分离。ciw-data/cde-review-live-01/owner-audit-v2.json。源截图当时最小化/native user-changed停止，未签收；后续浏览器agent所有权恢复可用不追改旧记录。
- **5e6dbcd8 发布**：先全部模板/临时字节准备，再逐文件原子替换；模板/写入失败旧三文件不变、仅重试render、不重跑已成功analysis。真实ciw-data/report-publication-01正常/注入失败/重试字节核对；不是跨A/B/C事务或断电持久性。705历史门保留。
- **9c53728d A几何**：未知-only图不画，候选保留；同实体ID查询、唯一靶点不重复计药、图例独立、稀疏128/阶段208/密集最高328px。landscape-reading-02四宽17图实看；真实1/302候选及合成已知布局分开，不冒充真实MAH/靶点/阶段富集。700历史门保留。
- **7ea2d518 临床阅读**：668真实结果A/B/C同源，四宽22图；临床身份图轴、安全表折叠/同查询/逐行来源、短来源1040px/Esc回焦、完整入排2219字/8强调。clinical-abc-03 owner-audit绑定；首次截图脚本完成12图后超时只补缺步骤，原失败保留。696历史门保留。
- **ec32ca47 归并预算**：研究24000/归并8000字符，中间2/最终6要点，全部完整候选参与，单条超预算拒绝而非裁短；单元缓存独立恢复。694历史门，不等于实际模型已交付。
- **349cccf5 修订/入排**：抽取读集来源版本绑定、整批事务采用、同提案幂等、同科学上下文supersedes；C标量多观察完整并列、原值/引文/来源可达。入排无损source-span阈值#C00000/700/下划线，vIGA/队列/逻辑保留；共享临床身份NCT居次。clinical-reading-04四宽16图、284原文逐字hash相同；690历史门，仅组件。
- 论文选段实际开放源PMC/摘要重放保留299与旧300两观察、原事实不变；不是明确修订论文或完整模型研究。publication-revision-component及原独立会商证据保留。
- 中国登记464CTR/24页、缺页仅补23页、明确真空0均完成生产来源切片；CDE受理目录度普利尤单抗80申请/2页及真空0已验，企业/承办日期不冒充MAH/批准。全部原来源/回执见Trellis既有记录，非创新药全集或95%召回接受。
- 所有上述白名单提交均已push并fresh remote exact；未知v1改动、健康日志、原始CAS/DB/模型日志不入Git。旧失败、冻结源码/回执不改写。

## 总体进度与剩余门
| 阶段 | 当前具备 | 仍未完成 |
|---|---|---|
| M0 | 离线骨架/部分公开来源 | 不代表正式交付 |
| M1/C | 完整终点/无损原文/身份/修订/预算组件 | 归并终态、完整流水线、真实论文修订、最终科学与产品接受 |
| M2中国宇宙 | 登记及CDE受理/化药IND新任务、同run缺页恢复组件 | 登记详情、其他序列/栏目、NMPA、3专家清单/≥95%召回 |
| M3/A | 同查询/几何/未知保留 | 正式中文名/MAH集团/靶点/产品阶段真实富集及3适应症 |
| M4/B | 同源组身份/测量/领域/图表查询 | 跨研究医学归并、独立论文、关键50条准确率、安全图、最终视觉 |
| M5全球/历史 | 来源版本原子采用/缓存核查分离 | 历史事实版本公开资格/全球扩充，历史日期守卫不得删除 |
| M6加固 | 单文件发布/部分恢复/当前事实JSON-CSV下载/本地DB-来源备份恢复 | 队列/取消/完整成本/最终综合接受 |

## 下一条有界任务
- 白名单提交本登记来源/备份节点；26997/27751都已终态，不再等待或重派。下一条是中文登记临床表的确定性事实投影/完整入排与终点、明确申请人角色及原始期别显示，取代无效的单条提案改写循环；英文指标标题/图顶留白和其他M2/M6门继续保留。
- 冻结52075实际终态一到即核原始receipt/响应模型/源码和源hash；失败只做归并恢复，不碰151旧批。当前不因等待制造阶段暂停点。
- 登记详情/NMPA及真实名称MAH富集继续按现有M2/M3包推进，不另建平台。所需新来源访问按授权执行，缺失/受阻不写0。
