# STATUS

**2026-10-24｜Goal=active，继续实施｜M1/M2进行中，未交付**

## 当前入口与范围
- 产品权威：01_PRD、02_ARCHITECTURE、03_PLAN、04_AGENT_RULES；本页替换更新，不另立规格。
- 唯一英文工程根内rebaseline-v2；单用户Web服务+内嵌9 Skills。v1多宿主包、编辑/分享、24门户不是v2发布门；未知v1工作树保留，旧中文工程零接触。
- 分支codex/rebaseline-v2-m1。本节点父基线39ec673b；当前修订恢复提交以该分支Git记录为准。CDE20131812、登记4f20d0f5、B测量45c5ecf2/B归属c0485479/C阅读43a4bc86/来源扩展ad65b790已推送。以下门仅对实际范围成立。
- 历史恢复依据：Trellis `10-23-rebaseline-v2-m1/PAUSE_HANDOFF_20261023_0810.md`；原暂停回执/备份不改。用户已解除暂停，历史paused/旧PID不覆盖新授权。
- 模型cms-router/glm-5.3-flash → DGX/deepseek → DGX/qwen；凭据仅注册配置到必要子进程环境，不入文件/日志/提示词，不改全局路由。

## 当前节点：只恢复归并，不重做151批研究
- 临床阅读/修订恢复节点已白名单提交并推送349cccf54750531a503dd3a3236098fb5480b333，fresh remote exact；v1未知改动/健康日志未提交。下节690门及界面候选绑定该实现，不借新归并代码改写旧回执。
- 新根因包4个生产RED→29相关PASS；研究包仍24000字符，归并包单独8000（真实mode/metadata计预算），中间至多2/最终6条，全部完整候选参与，单条超预算拒绝而非裁短。输出超量在缓存签入前拒绝，成功归并可复用；未新增框架/配置平台。
- 当前完整v2开发门 **694PASS/3.53s**，Ruff全src/tests/scripts、3JS/sh语法通过，1既有TestClient警告。代码门已通过；隔离真实synthesis-only恢复尚未运行，后续须冻结代码、核旧151批/来源不变，再只处理780要点归并。它不等于M1完整流水线或产品接受。

## 已提交组件：临床身份与入排重点阅读
- 当前完整v2开发门 **690PASS/3.30s**，1既有TestClient弃用警告；Ruff覆盖src/tests/scripts、3JS及sh语法通过。生产src/ciw2 53个Python/313函数符合600/80（create_app为既定例外）；不包含v1，不代表产品交付。旧664/688门仅对当时范围成立。
- A研究列表、B真实组别结果、C设计/终点索引、摘要引用及图形共用trial_identity：药物/方案→适应症/期别→有来源角色→登记ID。正式中文名优先；不把未核实attrs写成MAH、不猜集团，不用试验全部药物污染B单臂归属。历史源只读兼容唯一code:ctgov来源，原科学ID/源/事实不改。
- 入排单一source-span投影含评分与检验阈值、单位、原位置、队列/完整条款；vIGA不冒充IGA。深红700/下划线标阈值，逻辑/否定有字重；原文安全转义、逐字可达。修正worker斜线误成OR、混合逻辑误归AND，再补真实队列标题/vIGA；相关49PASS，旧三项裸HTML字符串测试改为读取可见原文逐字断言，不回退强调。
- 当前正常renderer候选ciw-data/browser-m1/clinical-reading-04：284研究/6580事实不变，168研究/463明确阈值；HTML `836cb43c246612303d7425104569502b011eaf27fad8aec01d9501e114783201`，源事实hash仍f903dc7b89a22bc4b1c83edb8696d7df96699166e3986b089700cd2828f1be53。66消费文件hash已核；284份原文DOM与来源逐字hash相同。
- Ego63/p1实际四宽1440/1600/1920/2560×密集/筛后稀疏/入排/来源共16截图全部实看；正文16px、阈值#C00000/700/下划线、6026字原文完整、Esc回各实际触发者/保查询。终点索引筛后18/3237而非假全数；所有282样本点保留。receipt原NOT_RUN不回写，后验在owner-audit.json/browser-observed.json。
- 用户已全面授权本项目失效Ego专用空间自行替换，不再询问；62失效后获准63，今后复用/失效替换，不动登录/缓存/其他任务空间，不自行升级浏览器。候选01–03及其不足保留，不借旧图给04签收。
- 只接受身份/入排/阅读组件：未知中文名和MAH/集团来源富集、A/B当前真实候选实屏、未识别入排表达仍须后续完成。短来源单值弹窗仍过宽，后续收紧；不是完整C美学、医学判定或康哲全规范接受。
- 执行worker CodeBuddy/codebuddy-cli/deepseek-v4.1-flash/max，650.248s/94tools/session01a169ad-aa3a-70a6-8441-18d90212b036，无fallback，原报告SHA bc0a5367c1f9bd85789219e3e71f9421151bf618b87849c818d4bf60d1fdaf0c；原源码/测试已归档后owner修复与接通。worker不是独立审阅；preflight/audit-execution通过，最终owner审阅见本地review/metrics。

## 前一根因包：M1修订恢复与来源绑定
- verify改为外部读取后整批事务采用；同run/阶段/提案稳定ID，重放不新增、不降级；写入失败事实/实体全部回滚。enrollment_type及组/访视/人群/单位等上下文不符只保留独立观察，不隐藏原值。
- C标量完整observations；待核提案不遮盖已核实值，多已核实值并列、不按来源优先级或后写顺序选真值；数值图只画无歧义已核实观察。supersedes历史值/引文/来源原位展开，不修改旧事实。
- 抽取结果由宿主绑定实际读集内同URL唯一source_id，核验按项目/URL/版本读CAS；歧义/未读不猜最新。旧无source_id回执只读兼容，不自动迁移。失败抽取stage_output不被verify采用，实际恢复测试推翻会商F5，不新增快照缓存框架。
- 5RED/1PASS→临床上下文整族反例→80相关PASS；读集绑定另2RED→82相关PASS。全门一度663PASS/1FAIL：旧端到端夹具只预存论文却未让Skill读取，已改为真实fetch_url工具离线读取，原核验断言不放宽。最终**664PASS/3.24s、Ruff全src/tests/scripts、3JS/sh语法PASS**；58生产Python符合600/80门（create_app路由注册为既定唯一例外），1既有TestClient警告。
- 独立静态会商CodeBuddy/deepseek-v4.1-flash/max，567.39s/37tools/session01a1698d-86e5-74f4-826b-88d8f3e81a08/no fallback；实际modelUsage匹配。报告SHA5b52f6e54be02d2661ace52a92f0f9018225d6e5ad9fbce80b8a69dca40a166d。未独立运行pytest；原冻结包缺夹具、生成计划空节保留为过程问题，owner裁决/review-gate PASS。F8任意同批链/终点修订语义和F9原子写HTML仍未签收，不称全报告修复。
- 有界PubMed发现17篇、获取PMID35567671开放全文66949字及18616772摘要2507字，0模型，不是全量文献。真实PMC source SHA4243626e587ca1875745dcd151145ea70e379e3a26466e1ea9e71c956b2d6a2f；owner选段重放预计约300/实际299，2观察并存、重放仍2、旧事实不变。不是明确修订论文或真实模型抽取/M1接受；“约”的默认数值限定仍需后续显示族处理。
- C04普通renderer只读R4源：284研究/6580事实、580主要/2876次要、282样本点；HTMLb21299d979bf90e990029a3d921f168a4a4ace4533b9289d73406536f97535b3，旧候选/源字节不动。四宽1440/1600/1920/2560各密集/筛后单项/原文共12PNG已实看；16px/无页面横溢、9462字原文完整、Esc回实际触发者/保查询通过。候选生成后仅抽取绑定有额外修正，实际消费的renderer/JS/CSS/template字节不变，不冒充完整候选新模型运行。
- 新发现待修UI：样本量依据在窄单元格展开时长引文过窄，期别/状态依据入口重复，终点索引总数未随查询收敛。C04完整原文宽阅读的行为通过不等于整个C美学/所有来源入口通过。下一前端根因包统一同一宽阅读入口/查询索引，不加第二套弹层。
- 用户原生Ask批准替代空间62/p1及恢复Ego窗口；未改登录/缓存/其他空间、未升级。Browser.getWindowForTarget在Ego失败后，经原生窗口Raise恢复；失败截图/首轮空输入不触发input的仪器超时均保留，第二轮按实际可见集合检查。空间59失效，不再使用；继续复用62。
- 证据：ciw-data/publication-{discovery-01,fetch-01,revision-component}/，browser-m1/c-reading-r4-04/，conference ciw2-publication-revision；原始全文/DB/运行日志不入Git。Goal active，M1–M6仍未完成。

## 阶段进度
| 阶段 | 实际状态 | 主要未完成门 |
|---|---|---|
| M0骨架 | 离线骨架/部分公开来源冒烟具备 | 不是产品交付 |
| M1/C | 完整终点/阅读组件具备；151批完成、归并失败 | 归并恢复、完整流水线/论文修订/最终科学及产品接受 |
| M2中国宇宙 | 中国登记列表及CDE受理目录接通，真实全页/零结果；中国登记缺页恢复通过 | 登记详情、其他CDE栏目/NMPA、3份专家清单/≥95%召回 |
| M3/A、M4/B | 骨架与部分切片；B组归属生产路径修复 | 对应正式科学/图表/真实项目验收 |
| M5全球/历史 | 来源版本原子采用具备 | 历史公开资格/全球来源扩充 |
| M6加固 | 未完成 | 队列/取消/成本/导出/备份 |

## 同一R4真实模型阶段：终态failed，151批保全
- 原句柄49763已返回exit0/内部run failed，run_a37cd8cba43b / prj_f21d0823b44a，attempt0002；只跑stage/analysis_C，未生成新报告文件，pipeline_acceptance=NOT_RUN。不得再等旧句柄。
- 冻结`2cbab03927fbe22cc2212f3fa4105862cfec0992`代码/Skills/规则/模型和原数据；恢复启动已核冻结hash、46源、DB完整性、6580事实及缓存。没有重跑bootstrap/来源/51已完成批。
- 恢复基线151任务/51合格缓存/100待做；33非空、195分批要点仅为暂停时范围。当前B节点结束一次只读核对：80个batch succeeded行（较恢复+29）、51次cache回放；恢复后32条model事件为DeepSeek-V4.1-Flash-TF 1、Qwen3.8-Flash-Next 31。不是80批已完成最终审阅或模型总成本；完整键/引用终态再核。不定期轮询、不因等待替换运行。
- 终态只读审计ciw-data/model-stage-r4/terminal-audit-20261024.json：固定旧runtime重新规划151批，**151/151对应key、schema、report C及逐批事实引用全核，780条分批要点保留，无缺批**；46 CAS来源/6580事实hash及62运行源码前后均相同，0新网络/模型。回执SHA a202e67d04b84b94ca43bcf4117b2e56c1d587702e1a6716c6953aeabd91df79。
- 失败在后续synthesis：GLM502、DeepSeek空结构后Qwen输出8192→一次16384仍length且无必需提交，2026-10-23T17:18:39Z终止。恢复期成功事件实际DeepSeek1/Qwen107；成功事件usage prompt889535/completion449860/total1339395，不含失败/历史调用，不是全成本。下一步仅兼容复用151批后收敛归并，不改冻结代码或重新检索/总结151批。
- 原attempt0001 STARTED回执不改，原97920用户SIGINT终态不再等待。暂停一致性DB备份SHA e9c18f2153ac95cff0495839d38caa4bc38a7cf1c46342fe0bcb168d3af2ce3e；冻结源/WIP副本/diff在ciw-data/pause-20261023-0810。
- 冻结模型使用旧renderer，不随当前前端热更新。其产物和本轮C候选分开验收。

## CDE受理目录：来源工具切片完成，M2未验收
- 当前改动已白名单提交20131812/push远端exact，v2已跟踪工作树干净；未知健康日志和v1 WIP保留。647门仅覆盖本v2候选，不是旧v1或全产品接受。
- 同Ego59/p1/现有CLI，普通生产china_registry_search增加明确query_kind；仅drug_name/company/acceptance_number进公开受理目录，其余blocked/site，不将适应症或靶点当药名。年度/药品类型/申请类型全部；栏目+六筛选进入来源上下文。
- 原词用于中国登记反向检索、CDE药名/企业框，不再前缀拼入疾病；结构化查询范围和临床纳排分开。CDE实现与空间配置入来源键，已保存结构化行不再送第二个抽取模型。
- 实际cde-browser-live-03-current：度普利尤单抗全部年度80行/2页(50+30)/80唯一受理号，1暂定药物/0试验/0科学事实/0模型；源码9文件及入口SHA运行前后相同。CAS SHA cd088a30a57542b7734a9584d5b9238a3fd4656e3dd8994796492e04aa86d1c0；41原始空格子保留。不能把80个申请当80项AD试验/获批或MAH结论。
- 真空结果cde-browser-live-02-zero：官方无pager、单一“暂无内容”，0行、页长未提供(page_size null)，SHA9825bc01f44d51d73aebf0b2eda31d22135d74361ccbbb6cacdfb2b7f31541cd。来源不造“共0条”。03较02新增URI会话参数拒绝；当前解析器离线重读两CAS仍完整80/0，不称重新核查。原回执不改。
- 03之后仅更正china.py过时说明/失败提示及CLI帮助；反向构造旧文本核hash验证，来源读取/采用逻辑不变，不重抓80条。china.py文字在647门前修正，647门后仅CLI帮助另查；来源脚本/解析器版本以各回执为准，不回写历史hash。
- 企业名称仅company_text、承办日期仅handled_date_text，原始复合企业/空单元格/受理号保留，暂定drug.attrs带来源引用，不猜申办方/MAH/批准/首次公开日期。内部filter键applicant只是企业名称控件，不是已证实角色。真实2015及以前选项保留；CDE列表URI不接受查询/会话参数，筛选在捕获JSON。
- 官方侦察cde-public-source-01/page2.png已实看，页末76–80/总80/50条页与原数据一致。生产零结果截图尝试因Ego窗口最小化失败，NOT_RUN；未强制恢复窗口、未改登录或借旧截图签收。此处非A/B/C视觉验收。
- 同一CLI运输扩展后，中国登记09-zero-current实际生产工具仍明确0成功，SHAf1eeac7d8754896423fe9c7608fb5520319fb480d011ce7edd57e9326d8da4c0；不是再次全量抓464条。各运行0模型，R4模型不受影响。
- parser执行CodeBuddy/codebuddy-cli/deepseek-v4.1-flash/max，358.763s/36calls/session01a1696b-fb5b-7265-94d0-45538901d5c4/一轮/no fallback，输出SHA28ae5251362e9fb80d3dc430de31535e733971f58abb718e3973cf732890547b。owner完整阅读原267行源/451行测试，补角色/日期/真实零状态/年份/URI及接通；不是把worker116PASS当整合通过。preflight/audit/review-gate PASS；初始重复report路径格式FAIL在派发前修正，原prompt不回改；cleanup只dry-run，无独立科学会商。
- CDE节点完整v2 **647PASS/2.97s**（历史范围，当前门见顶节）；显式v2 Ruff、3JS/sh及56生产Python600/80门PASS。owner4RED+扩展3RED+会话URI2RED→289相关PASS后宽门；此前516/282/285仅对原范围有效。
- 受理目录之外的CDE审评/优先/突破/默示许可、NMPA、适应症归属/科学事实、金标准与M2门仍未过；CDE缺页自动补取未实现，不借中国登记的恢复证据签收。继续有界实现，不造暂停点。

## 中国登记公开浏览器：前一节点来源工具接受，不是M2完成
- 显式CIW_CHINA_EGO_SPACE_ID复用已授权Ego59/p1；不创建/claim/profile discovery，不改登录/缓存，不绕过控制。不再新增Playwright框架；保留未配置时blocked/site备用，其他来源的当下接通范围见上。
- 特应性皮炎真实列表：24页/464唯一CTR，161条不同原药物标签、464研究/464显式关系，全部unknown纳排，0临床事实/0模型调用；不是161种创新药或MAH/召回验收。
- ciw-data/china-browser-live-07为同06的prj_446b8ea5087c/run_ab02bcd2272e恢复回执；DB/CAS仍在06/data。来源SHA fc7f4fa3705a5da58e5e17930f428424fc417d0b835c9ee72274b61e41031e12，145826字节，完整24页/464行/CTR集合及CAS摘要实际核对。
- 06留下23页/444行的有效未完来源；07正常UI跳转只补第23页。元数据逐项记录reused_source_ids/reused_pages/new_pages_checked，不把旧23页冒称本次全部重新核查；旧失败回执不改。公开POST request_context分开查询缓存，同查询新版本仍失效，跨项目/跨run不借用。
- 真空结果ciw-data/china-browser-live-08-zero：明确0页/0记录与“暂无数据”占位，普通生产工具成功；SHA f1eeac7d8754896423fe9c7608fb5520319fb480d011ce7edd57e9326d8da4c0。失败/未配置/损坏页面仍不转零。
- 官方页面正向/空结果截图public-positive.png、public-zero.png已实际打开核对；分别在07、08-zero目录，SHA ab17d2e15c31c5ffce0551e5a8884e6f4e552f4d3a3ae1a2b3109252d3bd3c15/a21509fec79759d1124208d77a84e137b10a811fd0ace23eaeba79f42472ab74。只作来源页面证据，不是A/B/C视觉验收。
- 07/08同6源码文件hash冻结、运行前后相同。普通注册工具走真实Ego/生产解析/DB采用，不是手写demo；当前脚本和完整回执本地保留。页面来源成功不等于完整流水线、报告科学性或M2召回通过。
- 解析整字段/六列表头/查询/总数/重复/页集合；原始复合药名不取首项，保留public detail_id，不猜GET详情URL。现代32hex及实际旧数字_p/32hex_p均有反例；用户名/token/隐藏字段/运行原始错误不入来源。有效页在整批冲突时保留为未完CAS，错误页不混入已采用集合。
- 复盘：02漏读CLI stderr；03 glyph文本selector不匹配嵌套箭头；04–05早期detail_id形式未覆盖；06保留有效页后定位23页32hex_p，07仅补缺页。初始只看首页不足以确定全站schema；早期失败未保留原流导致多抓，已补来源恢复，不能把这些失败改PASS。01脚本注册错误属于执行入口，不是网络空结果。
- parser执行CodeBuddy/codebuddy-cli/deepseek-v4.1-flash/max，259.616s/33calls/session01a16946-164c-797f-9eb5-42b7c7205972/一轮/no fallback，输出SHA bf0f2b387c3c7a32448f5cbe01b45a721f9938ed8d9faf955253e84c4cc60781。owner修安全/真实旧ID/桥/恢复；preflight、audit-execution、review-gate实际PASS。没有独立科学review或额外Hermes节点；cleanup只dry-run，原始证据保留。
- 前一节点最终v2 516PASS/2.71s；Ruff/两JS/sh/54Python600/80 PASS。当前647门见上，不能沿用516冒充当前。早期512PASS/Ruff BLE001、各族RED/相关GREEN分别保留，不改写历史。

## C阅读组件：同源candidate03核验完成
- Ego旧53不存在；原生Ask批准替代并复用 **59/p1**。只读预览localhost49587/C3，句柄47130；不改登录/缓存/其他空间。Ego提示更新，未擅自升级。
- ciw-data/browser-m1/c-reading-r4-03/C.html：SHA `e96d5ca88c9f14db48abd2a5eecbbfb5c6eafb18de27834671d775ec84738ffc`，12,371,833字节。
- 正常生产renderer/同R4源：284研究/6580事实/580主要/2876次要终点/282样本点/5明确0；事实hash f903dc7b89a22bc4b1c83edb8696d7df96699166e3986b089700cd2828f1be53。不是创新药全集/模型最终报告。
- 1440/1600/1920/2560×1080密集、筛后单项、原文阅读共12截图全部实看。同目录dense-stable/interaction/restoration-browser JSON含实测及操作。
- 密集样本量336px/期别160px，完整期别计数不截短，对照表顶部743.98px（旧约947）；筛后两图区120px/表顶部527.98。不缩字号、删数据或伪点。
- 9462字入排从旧181px窄格改同页宽幅阅读，四宽正文806/900/1088/1463px，16px；事实依据独立列，原文不复制改写。英语仅主动打开原文层，不铺默认首页。
- 真实键盘焦点留原生dialog；原文滚动627.5px/背景0；Esc恢复原内容、触发焦点和查询。无JS/不支持dialog仍可原details读取。
- 原生键盘检索末项NCT00932074=1；无命中0且两图卡隐藏；恢复284/284、282样本点/5明确0不变。
- 候选01标签截短/504px判FAIL保留；02单项220/300px空白被owner拒收后修复。首次03截图未等ResizeObserver稳定不采用，dense-stable才采纳；不改历史FAIL或借旧图签收。
- 接受仅C来源阅读/几何/检索组件。A/B、模型全文、论文修订及最终医学/审美门未完成；不宣称完整康哲6.1.3影像/动效合规。

## B结果组归属：代码/真实源切片完成，B产品仍未接受
- 删除renderer删标点/子串first-wins和表格全试验药物冒归属路径。current verified同研究/来源版本design.arms+字面身份形成一套图/表投影；短中文名/代码合法、联合方案全保留、控制组不贴主动药。关系缺失/冲突保留原组名/值/引用，药物栏为“—”。不改原始来源、历史事实或运行中代码。
- 13项生产反例RED（前一次缺tier的夹具错误单列，不算产品RED）→根因修复→身份/流水线/解析相邻47PASS。正向、标点/前缀/复合冲突、共享别名、跨研究/来源/未核实、对照、联合方案与图表/表格一致均覆盖。
- 固定77个真实已捕获源只读扫描，78研究含明确同名组关系；代表性NCT04921345完整668结果，665绑定/3缺关系，0新网络/模型。原始值/事实集合保持，PK/ADA记录仍按来源保留，不据此当临床疗效接受。
- ciw-data/browser-m4/b-arm-identity-02/B.html，SHA45846a75f7c29b2c9c24c0983d8b94aa9016e3962443f93c3262ee23a08bb9cb；源SHA50bc0483d2b3cfb6ebe207a71afe94575ca15e30acc707dbb4634ab56532dee2。01原件不改，02只读同DB重新渲染当前模板。
- Ego59/p1旧02实际1920核对、原生筛选Cohort1.1=221条，药物归属正确，但**旧B视觉FAIL保留**：重叠标签、访视/类别丢失、12图上限、图表查询不联动及泛化提醒。以下新节点修同族消费路径；不将旧图冒充新验收。

## B测量呈现：当前06组件完成，不是M4正式验收
- _result_rows补完整class/category/paramType/dispersion/实例上下文；results.py严格单访视，聚合时间窗不取首数、矛盾不猜、月不固定换天、重复坐标不覆盖。缺测在折线上断开而非补零，事实原值/来源不变。
- 全部图组在同一ECharts位切换，不再12组截断或每条一卡；完整表默认折叠，指标原定义/人群/原窗完整可读。图/表同检索及fact_id定位，系列颜色/编号稳定，单访视收敛为紧凑对照。泛化提醒标题已移除，单位仍可见。
- 同一真实668事实→70组（18折线/52观察组），668逐fact ID完整一次覆盖、0遗漏/0新增；未改变PK/ADA科学域，也不宣称这些是临床疗效结论。M4语义/跨来源/临床结果验证仍待正式包。
- 当前ciw-data/browser-m4/b-measurements-06/B.html，SHA `80fdd0b60dfa95699f386d022f4f027947de8017005eba19441eecac3efa4b82`，2,234,534字节。源/事实hash沿用本页B归属切片，同DB只读渲染，无新来源/模型。正常renderer，不是手写demo。
- Ego59/p1，localhost58583/B，当前只读预览句柄88458；C预览47130仍保留。过时B预览58845/46358/29710/76757已确认所属PID后正常停止，只停自建服务、不删任何源/截图/回执。
- 当前06共10截图全部实看：四宽1440/1600/1920/2560密集3系列18点、cohort筛后1系列6点；16px/无横溢出。单访视3点绘图区192px、零基线且颜色对应原系列；完整70组末项可选，空查询隐藏图，恢复668行/70组及原选择。实际鼠标点击ECharts glyph→正确fact行/来源URL，非模拟emit。
- 03周刻度循环小数、05条形截断起点均在实看后拒收，原件留存；06精确坐标换算、条形包含0及稳定色后再验。没有用缩字号、裁数据或假点解决。06 owner-audit.json已核HTML、13源码/资产digest、10张PNG实际尺寸/hash及浏览器操作；生成回执NOT_RUN字段原样保留，后验另记，不回写历史。
- 只关闭该真实源测量/查询组件；单项原始研究不是跨试验临床等价、PK/PD分类、50条critical人工准确率或整个B交付。C03较早组件证据也不拼接成当前完整候选PASS。

## 测试、协作与复盘
- 前序B节点完整v2 388PASS/2.67s，当前中国来源节点最终516门见上，不能把旧门称当前。B节点9RED→相关32PASS；B归属47PASS、377宽门及C364宽门分别保留。不为文档收尾再跑宽门。
- 一次有界执行：CodeBuddy/codebuddy-cli/deepseek-v4.1-flash/max，session01a1690e-8288-7d63-a24c-f1f2424cb2d8，304.785s/36tools/return0，无fallback，输出hash核对。worker图例/数据窗/查询；owner补稀疏高度及宽幅阅读。
- 协作审计格式缺口保留：custom prompt缺解析器规定route bullet，audit-execution FAIL/prompt_route=null；真实runner身份/effort/hash另核。不改已派发prompt、不为标题重派、不伪造审计绿；下次dispatch前规范bullet。executor不是独立科学/审美review。
- Trellis implement/check在dispatch后发现seed并已改为当前PRD/规则2+2；prompt原含read set，不能冒称清单先前已修。raw证据在ciw-data，不入Git。
- 复盘：可达不等于好读，实看长原文和筛后态；少条目不能套密集卡。viewport/ResizeObserver采样时机、大范围computed-style超时与产品缺陷分开记账。

## 来源底座与已提交M2节点
- 发现→全量candidate_triage→universe_expand→最终coverage_review；复用Skill，不添平台/表/路由。别名/靶点/企业驱动中国CT.gov+三中国站点及全球路线，最多3轮；unknown保留，failed/blocked/pending不算空成功，来源/解释独立缓存。
- 真实中国CT.gov冒烟1研究/17待查/0模型；原Placebo保留，但共同身份/旧别名读取/种子排除精确控制标签。捕获源离线重放1研究、0网络0模型，原回执hash不变。节点361PASS/ad65b790已提交，不是召回通过。
- CT.gov18页/1787唯一ID=官方总数，不是创新药闭包。77容器采用46源/284研究/6580事实，2488非空次要定义补回，其他科学值/上下文0变化；151完整终点包最大23984字符，无截尾。
- 来源文档+解析器版本原子采用，失败旧current不变；独立论文不随登记刷新撤回；HTTP/缓存/导入分开。历史as-of未实施，启动/数据/HTML守卫拒绝，不删守卫冒充完成。

## 下一有界动作
1. 修订恢复节点按明确白名单提交并核远端exact；继续v2，不提交v1 WIP/未知健康日志/原始运行证据。Goal active，不创建暂停点。
2. 冻结R4已终态并核151合格批，下一根因包修归并输入/输出收敛并验证兼容恢复，只处理未完归并，不重跑151批或来源。
3. 宽阅读/重复入口/终点索引已接通，后续前端处理中文身份/MAH富集、短来源弹窗收紧及A/B真实候选；并继续M1明确修订论文链、M2登记详情/CDE审评/NMPA。按根因族→完整修改→相关批→里程碑宽门，不展开无限全页会商。
4. 搜索/微信未配置、其他CDE/NMPA适配/专家清单未具备；M1完整链/论文修订及M2–M6正式门未过不宣称交付。无须新用户裁决，不设人为暂停点。
