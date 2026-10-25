# 02 · 架构

M3来源档案沿用extract-results/ExtractionResult与现有逐药缓存/核验事务：trial_evidence→enrich_drugs（所有报告）→extract_results/extract_design→verify（所有报告）。SourceContext仅承载来源原有法律实体、关系、as_of、jurisdiction、indication，不覆盖临床组/量表/时间窗。共享drug_profiles只读当前已核实事实，A/B/C不消费发现attrs来认证靶点/阶段/集团；原attrs留作检索线索，不就地迁移历史事实。未解集团不从公司名猜测；来源原值与显示期别映射分开。
开发阶段的确切年龄/严重程度限定由profile_evidence.indication_qualifies统一检查项目疾病归属，限定原文保存在原context.indication；不是泛化疾病或临床等价算法。明确日期/药物/NMPA批准/治疗对象有直接语法关系的中文声明可核验，其余未知表达不自动接受。A阶段格显示每条合格观察的原状态、完整适应症及截至日，多观察不选max/latest；原事实/历史回执不重写，无新增表、字段或Skill。
当前阶段图使用同一phase_observations投影，逐条带phase/raw_value、范围、日期、来源类型、source_id/fact_id和不可映射原因；JS按完整口径分系列/矩阵行，保留全部观察而不排除有限定的事实。每口径/阶段按药物ID计数、全fact ID并集，不按标量unknown判断有无资料；标量只保留兼容字段，不再决定新图。后台新payload始终带观察数组，旧单值HTML输入只读兼容。来源中文标签沿用labels单一确切映射；不同日期的两阶段记录不表示互斥比例或临床疗效排名。
NAME_BOUND_FIELDS复用既有identity_basis回执：目标/模态保留注册品牌+名称依据，开发/权益/阶段只绑定实际名称依据与实体原名，初次采用/提交/当前读取/重放/离线核验一致；不另建subject表或审批。所有状态语法先排除计划/申请/被拒等非实际状态，不仅检查新增自然句分支。相同公司角色/显示名在默认层去重，引用、日期、法律实体和原事实均保留在共同阅读器。
普通构建复用setuptools build_py/sdist小hook，把唯一作者skills/*/SKILL.md复制到包内；源码可编辑模式与安装资源解析分开，CIW_SKILLS_DIR显式覆盖。已有构建目标出现未知文件或符号链接即失败，作者链接亦拒绝，不自动删除目录。ciw2 skills使用不创建资料的Settings且空集合返回2；没有新增依赖、doctor框架或后台安装器。

```
浏览器 ──HTTP──> FastAPI (web/app.py) ──> Service (service.py)
                                            │
                       ┌────────────────────┼─────────────────────┐
                 pipeline/runner.py    store/db.py (SQLite)   render/portal.py (Jinja2 + ECharts)
                       │                store/cas.py (原文)
              pipeline/stages.py ── 代码阶段：trial_evidence / verify / render
                       │
                 harness/agent.py ── Skill 阶段：intake / universe-* / coverage-review / extract-* / analysis-*
                       │   白名单工具 + submit_result(Pydantic 校验) + 步数预算 + 留痕
                 harness/tools.py REGISTRY ←── sources/*（ctgov, pubmed, openfda, websearch, wechat, china）
                                                  │
                                            sources/http.py：所有外部内容先入 CAS + sources 表
```

## 1. 流水线（DAG，按报告裁剪）
| 阶段 | 类型 | 报告 | 阻断 | 说明 |
|---|---|---|---|---|
| intake | Skill | ABC | 是 | 标准适应症、英文名、同义词、关注点 |
| universe_china | Skill | ABC | 否 | 中国必跑路线和来源候选 |
| universe_global | Skill | ABC | 否 | CT.gov / FDA / PubMed / 会议 |
| candidate_triage | Skill | ABC | 是 | 复用coverage-review，先排除明确背景；unknown保留 |
| universe_expand | 代码+既有Skill | ABC | 否 | 别名/靶点/企业驱动来源查询，最多三轮，新增线索交原universe Skill解释 |
| coverage_review | Skill | ABC | 是 | 全量候选分批纳排；明确ID写回，不擅自合并实体 |
| trial_evidence | 代码 | ABC | 否 | CT.gov按明确干预关系入库；范围内CTR按列表绑定详情原子采用。未完/来源失败运行仍failed，但后续可读已有事实；恢复重建下游 |
| enrich_drugs | 既有extract-results模式 | ABC | 否 | 逐药来源档案；固定源/读集、完整返回实体绑定、部分已完单元可采用，其他单元仍pending |
| extract_results | Skill | B | 否 | 论文/会议/FDA 结果抽取（逐字引用） |
| extract_design | Skill | C | 否 | 中国登记/论文方法学设计抽取 |
| verify | 代码 | ABC | 是 | 原文核验 + 同一实体/字段/上下文检查 + 分级 + 可选二次模型 |
| analysis_A/B/C | Skill | 各自 | 否 | 中文要点（不新增事实） |
| render | 代码 | ABC | 是 | 写门户快照；平台也实时渲染 |

`render/publish.py`用标准库在目标目录内建立独占临时目录：先准备所有HTML，再逐文件`Path.replace`，正常失败只清理自己新建的临时文件。模板或写入失败不截断旧报告；返回文件名仅在全部替换完成后。每份文件原子可见，不是跨A/B/C事务或断电持久性承诺；替换中途失败仍按既有runner失败/恢复语义处理，不新增发布平台。

档案证据规则只保留在domain/profile_evidence.py；assessment.inspect_fact供首次采用、恢复和离线复核共同调用，当前rule绑定该文件/身份规则/引文checker实际字节。上下文名称/日期共现不作关系证明：只接受明确支持的声明形式，未知/否定/其他地域/无关日期留为未核实，不增加审批或新Skill。许可记录过期时集团呈现保留原角色。旧事实/回执不改写，规则升级追加裁决；数字开头的科学标识与紧邻单位分别检查。

可恢复：同一 run 从最早失败阶段重新计算依赖分支，之前成功前置不重跑；下游立即pending，不能沿用旧空成功。普通非阻断来源失败记录并继续；analysis_A/B/C失败仍可渲染现有数据，但run最终failed，不以缺少摘要的整次运行冒作成功。
`IncompleteWork`是例外：即使该阶段允许后续继续，存在预算/未完成单元时run最终仍failed，部分产物可用但不能显示工作已全完；runner保留partial output。CLI对失败或带错误运行返回非零，普通被拦来源仍依既有非阻断合同处理，不加新发布状态。
Service在初始化模型前检查项目与resume_run归属，不存在或跨项目请求返回明确冲突且不修改旧run。历史截止日暂由共同availability守卫阻断：启动产生失败记录，不发模型/来源请求；report_data与HTML入口也拒绝输出未筛选的历史报告，Web返回409。M5须完成逐版本资格后替换此守卫，不能直接解除检查。

Service复用标准库Condition/deque及一个执行锁，在同一服务进程串行准入，后台队列与同步CLI共用锁；运行所有权和停止意图在内存，不建调度平台或自动接管旧running。排队取消采用SQLite条件更新，活跃取消通过每run的RunControl传递；RunCancelled继承BaseException，穿透既有逐条except Exception隔离，runner记录cancelled。普通CTR/CT.gov、反向来源扩展和抽取批次循环均在下一单元前检查，不丢已完成单元回执；Skill在新模型/工具前、FallbackLLM在进入下条原配置路线前检查。取消恢复与失败共用既有依赖重置机制；当前请求可完成，不宣称即时中断或跨进程互斥。

## 2. 数据模型（store/db.py）
- `projects` `runs` `stages` `agent_steps`：运行与留痕。
- `sources`：按项目/来源类型/URL/原始字节digest/正文text_digest/解析器text_parser_id复用不可变来源表示，保留首次存储时间。原件相同但正文或解析器改变时追加来源版本，不覆盖旧源/事实。每次网络核查、缓存复用、导入另在agent_steps记录source_observation；只有network_checked含network_checked_at及实际HTTP状态。**抽取只能引用本项目已读取的来源**。
- 文本PDF由既有原生pdftotext读取，CAS同时保存原件和未经重排的完整UTF-8 layout文本；meta.pages是1起页码及0起Unicode字符范围，meta.text_parser_id绑定二进制版本/解析实现/选项。普通fetch_url按固定source_id分页，失败原件保留、text_digest为空且独立source_parse问题；不能回传二进制伪正文/空结果。相同原件/规则复用解析仍须分别记录本次网络核查；同run读取缓存不伪装新HTTP。模型工作单元恢复也检查PDF解析器身份/CAS，不复用过时表示的解释；旧冻结运行不热升级。页码/获取时间不构成历史公开资格，论文科学内容和扫描件OCR另验。
- 原证书全部字段已捕获时，正式商品名采用只扩展nmpa_ingest的采用规则与新snapshot，不重取浏览器原件或改来源parser版本。identity.trade_name_zh/en保留逐格引文/JSON定位，不进入全局发现别名。profile_evidence只使用当前code:nmpa来源、唯一产品归属的商品名识别明确抗体类型同位语；常规措辞未支持仍保留待核。目标/类型fact_verdict的identity_basis含名称事实ID与完整依据摘要；DB当前读取、普通重放、离线复核与提交内复验一致检查，依赖变更不能借旧receipt认证，不新建关系库/审批平台。
- 名称依据同时含当前有效正式名称事实/实体原名及相关较长品牌的所有者，取名称字段时不递归投影目标事实。中文前缀碰撞按当前位置的已注册长品牌判别，保留合法中文后缀；不存在/未发现等否定不建立类型事实。requalify在写事务内核对当前成员/依据，失效项保留待核错误、不追加旧已确认回执或假计数。普通英文is-a抗体targeting形式与明确研发谓词共用profile_evidence，完整类型描述里的科学标识沿用同一数值边界。
- 原文核验只对有完整词界的逐字文本值采用其内部标识证据；未逐字命中的文本仍逐项核对数字，不因未知后缀跳过数量或科学标识。嵌套对象逐值处理，另一字段的原文命中不能认证错误数值；标量负数与靶点标识保持分离。
- 身份阅读沿用labels.registry_label精确显示映射和_trial共享宏，不增加药物/企业字典、数据字段或阅读器运行时。identity_evidence汇集名称/公司/集团及profile原引用；profile_evidence以source_id+quote+URL分组，仅复用同一引文，保留所有fact_id及各自日期/角色和许可metadata。默认一入口，原JS移动/归还同一个source-evidence-content，Esc回焦与无JS原生details保留；DOM显示去重不改变科学值或修订记录。
- 已注册前缀冲突及名称依据按两个方向判断；品牌后的合法剂型词在无竞争品牌时仍可使用。存在否定采用分句起始范围，不从正常PFS术语跨窗寻找“获批”。研发谓词禁止把药物所有格后的生产工艺当药物，区间端点额外核对完整数字/单位且不把短横线标识拆成人数。试算和真实复核均在事务内重查依据，只有真实复核追加回执。
- `entities`（drug/company/trial/target，含别名、发现路线、纳排）+ `links`（drug-trial / drug-company / drug-target）。
- `domain/identity.py`只做大小写/空白形式归一及字面名称/已知别名匹配，保留标点，不推断药学等同。scope、trial_evidence和verify复用；scope缓存绑定该规则源码hash。明确且唯一的试验关联用drug-trial；宽检索/共享别名保留drug-trial-candidate（pending及原干预名），沿用links不增表。后来字面关系确认时保留候选记录并标resolved_literal_match；不是自动解决剂型/组合药学语义。
- 共同research_aliases仅复用既有精确placebo/安慰剂排除；原otherNames仍在来源和研究元数据中，旧存量别名只在采用/身份/查询读取层过滤，AB-1与AB1不合并。检索候选和已确认科学身份不同。
- B的render/result_identity.py读取current verified design.arms，按(entity_id,source_id,source_snapshot,原组名)建立关系；仅去空白/大小写及明确Drug/Biological类型前缀，复用同研究已关联药物的name_owners。原组名/原值不改，组合全列、冲突不first-wins、控制标签不归主动药；trial_drugs仅作研究语境，drugs/arm_drugs才是图表和明细共同归属。关系事实ID与内部原因保留，缺来源/跨源或跨版本/未核实不自动借用，不增加表或猜测型组映射。
- B的render/results.py投影全部测量实例；严格fullmatch单访视，不复用旧parse_timepoint的宽文本首数字匹配。endpoint原定义、单位/paramType/dispersion/人群、非访视class/category与原窗共同分组；人口/统计/单位缺项不自动跨研究。每点绑定fact_id及来源组series。重复坐标不覆盖，非数值/未核实留表与内部plot_exclusions。positions包含已知缺测访视供断线，不生成零或新事实。portal.js只复用一个ECharts实例/ResizeObserver，完整组选择及同查询图/表/来源；系列编号颜色按完整组稳定，周显示在数值坐标构建时精确缩放，不对任意day刻度除7造循环小数。条形包含0，完整长表/定义原生折叠；无新框架/状态库。
- `facts`：追加式；`supersedes` 指向被取代的版本；`tier` `status` `quote` `quote_start/end` `context`（组/时间点/人群/统计对象/分母/终点）。
- `pipeline/verification.py`复用既有facts/DB.tx：先读源/可选模型检查，再在一个事务中关联实体并采用整批。提案ID绑定project/run/extraction-stage及原始提案，不含可变的核验状态；先识别已提交重放，再判当前修订对象。supersedes科学上下文不匹配则不隐藏原观察，原因仅在内部记录。enrollment_type沿用登记的ESTIMATED/ACTUAL含义进入抽取合同，不从人数大小推断。
- 抽取单元回执保存每条事实的宿主附加source_id（不是模型可填写字段），由本次读取集与精确URL确定；唯一匹配才绑定，歧义/未读为null。核验严格按同项目、同URL、同source_id读CAS；旧回执缺该键时只读兼容原按URL行为。Skill/schema/代码变化按既有恢复键失效，冻结运行仍使用自己的旧字节。
- C标量投影汇集每个字段的完整observations，唯一已核实语义值才进入概览数值轴；待核候选不遮盖已核实值，多值并列与完整来源均保留。引用可沿supersedes只读追溯历史值、原文及版本，含循环防护，不改历史记录。不新增事实库、审批流或缓存计划框架。
- `coverage`：每条检索路线的状态（ok/failed/blocked）、命中、新增实体。
- 发现工具逐批保存登记原名与药物—试验关系，最终模型提交失败不抹掉已读来源；不据此推断创新属性或监管身份。
- 同一RunContext的相同GET复用已抓CAS字节；新上下文再次调用fetch时不沿用旧HTTP缓存。已完成单元的恢复回执是固定来源复用，不声称发生新HTTP核查；新调研run不沿用上次单元回执。工具结果授权仍限定当前Skill。
- CT.gov代码事实按来源ID+解析器及其语义/分级代码hash形成snapshot；事实context保留stamp，links的ctgov-current仅作同项目/研究的可变当前指针（不是临床关系推断）。全量解析/源hash及登记号核对后，一个DB.tx完成实体元数据、事实、指针和append-only source_activation回执；失败完整回滚并记录source_rejection。源/事实不删改，普通登记版本不生成supersedes或科学撤回。current_facts仅按指针过滤code:ctgov；无指针的旧项目保持原读取行为，论文/LLM事实独立。
- 沿用links而不是把指针混进entities.attrs，是owner的最小实现选择；共同读取在DB中，其他消费者不各自解释。source_by_url优先采用最新网络/导入观察，不把缓存读取变成新鲜度；无观察的历史来源继续旧排序兼容。M5仍须完成历史资格、旧源延迟重放策略及跨来源消费冲突，不由当前指针自动解决。

## 3. 信任模型
1. 代码解析的结构化注册数据（CT.gov）：`extracted_by=code:ctgov`，按 JSON 路径直接取值 → verified。
2. LLM 抽取：必须给 `source_url` + 逐字 `quote`；verify 阶段检查 来源已读取 → 片段在原文中 → 数值在片段中。
3. critical 且通过 → 可选 `CIW_LLM_CHECK_MODEL` 二次核对（只回答 YES/NO），不同意 → conflict。
4. 门户：未核实/冲突的 critical 字段只进表格（红色标记），不进图表数值轴。
5. verify的实体写回必须唯一关联本项目既有实体或明确登记号；未知/共享别名不默认落到父药物。原抽取事实不删除，阶段输出identity_issues/unresolved_entities；其余正常事实继续核验。候选关联和身份问题不代表科学验收通过。
6. 当前引文裁决复用agent_steps(role=fact_verdict)追加回执，不增表、不覆写facts/sources/links/entities。回执绑定完整有类型的事实、原引文、固定source_id/raw/text SHA及实际quote.py+assessment.py字节规则。raw_current_facts保留成员/历史投影；current_facts统一叠加当前有效状态。旧LLM verified无有效当前回执按待核读取，已存unverified/conflict/unknown不自动升格；代码解析事实不受该迁移影响。科学supersedes与核验裁决不是同一事件。
7. 新采用事实与其裁决同一事务；同run恢复只重核固定版本，不再插入同一事实。暂时不可读/不可用/摘要错误的旧回执在普通恢复时也重核相同固定来源，恢复原字节后可重新确认；持久片段否定与无引文不重复重核。`ciw2 requalify --project ID [--dry-run]`离线读取本项目CAS，区分未绑定/不可读/摘要错误/片段不符，真实执行只追加回执；采用及复核专用BEGIN IMMEDIATE在跨连接读取最新回执前取得写所有权，普通只读导出仍为deferred事务，不建进程锁或调度器。归一化坐标不是原文坐标。B/C图、摘要查询、身份和JSON/CSV共用当前投影；C原位短状态与折叠具体原因一致，历史来源只标“当时已核实”等当时状态。
8. 核验数值直接保留整数精度、浮点指数及数值字符串的小数/千位形式，以Decimal比较，不先转float或裁指数尾数。缺失数字原因只列有界示例及剩余数量，fact_verdict完整JSON不受普通对话日志字符截断。核验失效不自动复活被supersedes替代的历史事实：当前后继保持待核，前驱仍在原始历史与C来源链可查；科学成员与核验状态分开，不重写历史或擅自选择旧值为当前真值。

## 4. DSH（内嵌最小 Skill Harness）
- Skill = `skills/<name>/SKILL.md`：frontmatter（name/description/tools/output/max_steps）+ 正文（工作说明）。
- System prompt = Harness 通用规则 + Skill 正文；User = 任务 JSON。
- 新抽取事实需要source_url/quote；已有已核实事实的摘要只按Finding合同引用fact_refs，不强迫重新抓取原文或添加schema没有的字段。共同规则不能与摘要输入/输出互相冲突。
- 候选发现沿用Universe合同的evidence_urls，不强迫增加该schema没有的quote字段；正式事实抽取合同的source_url/quote核验照常，不降低科学标准。
- 模型只能调白名单工具；工具异常以 `{"status":"tool_failed"}` 回给模型（不当作无结果）。
- 输出只能通过 `submit_result`，Pydantic 校验失败把错误回给模型重试；预算耗尽抛 `AgentBudgetExceeded`。
- 最后两次交互提示剩余预算；最后一次只开放 submit_result 并请求该函数，不再无限追加检索。即使强制提交，结构/来源校验仍照常。
- 无检索工具的Skill从首步仅开放submit_result并要求该函数；不存在可分页结果时不凭空提供read_tool_result。真正使用检索工具的Skill继续保留长结果读取及末步提交。
- 模型按明确环境配置顺序备用；错误或缺失的实际模型身份拒绝采用，返回的真实模型与使用量留痕，不用请求名冒充响应身份。
- 按[GLM官方工具协议](https://docs.z.ai/guides/capabilities/thinking-mode)，reasoning_content只在内存中随同一工具会话续接，assistant持久日志/回执不保存该正文。官方明确GLM-5.3/Flash强制thinking，本轮不尝试不受支持的关闭参数，不改指定模型或effort。
- 必需submit_result不只检查函数名/JSON可解析；缺少该工具schema的顶层required字段也属协议未完成，回执仅存缺失字段名、reasoning字符数及安全用量，不把空对象交付。其余完整Pydantic校验仍在harness；错误反馈不重复输入原文。
- finish_reason=length一律不接受；模型明确报告completion_tokens达到本次上限且所选submit_result缺少顶层required字段/无有效对象时，也按实际输出耗尽处理，即使finish_reason=tool_calls。两者都只在同输入、同模型上最多一次增加输出预算至min(原预算×2,16384)，保留真实结束原因及output_budget_exhausted，不把它改写成length。合格提交即使到上限也不重复；其余低用量结构错误仍交既有Pydantic反馈，身份不符不扩容，不改全局模型参数或effort，后续调用仍从原预算开始。output_recovery仅记录预算、前次安全错误/用量；成功model事件或最终model_error均保留，reasoning正文不入库。只在相同模型上恢复，不把新增请求冒充新模型意见。
- 真实主模型曾在144.583s返回，产品主请求改为300s而非120s；显式配置备用时主路仅尝试一次，然后按用户顺序切换，避免三次取消同样慢请求。独立无备用保留3次策略，DGX仍用显式路由时限，不改全局服务/effort。
- harness任务/assistant/工具记录超过20k时先写现有CAS，agent_steps只记有效JSON指针（digest/format/字符数），不截成破损JSON；assistant先排除reasoning正文。诊断读取验证CAS摘要，旧截断日志仅在固定数据重建及原前缀吻合时兼容，不重写历史。
- 只有思考信息、没有可用正文/工具结果，或必需提交未履行，属于协议未完成：立即记录并仅走已配置备用，不把它当作正常回复耗尽整个工作单元。错误回执保留类别、实际模型与可用用量，不记录服务原始错误正文或凭据。
- 大数据摘要先建立全部完整记录的预算内任务，再执行；无固定Top-N。多批要点超预算时继续有界归并，输出至多6条；不收敛即明确失败。完整门户数据不裁剪。
- 摘要接受边界复验非空白标题与每条正文，不因findings非空就放行无内容对象。被拒层的单元缓存留作原始回执，不自动删改；相同策略重复恢复可重现失败但不会继续消耗模型，明确诊断要求保留原研究资料并建立调整策略的新归并运行。该终止政策不冒充自动修复，目标是避免无效循环；真实最终选择的引用语义在实际结果复核，不由alias成员校验替代。
- summary_lineage.py只管理既有stages中的短引用谱系：每个summary_ref_*唯一映射一条factID，完整输入title/bullets及映射绑定basis digest，所有批仍不截正文。analysis_basis检查点存完整映射，日志只记指针；analysis_selection按每包保存选择/未选canonical引用及输入输出摘要，不是科学撤回，也不要求六条结论引用全体事实。代码签名同时绑定stages和lineage字节；同run缓存不跨run借用，请求模型与实际agent_steps响应模型分开记录，不倒改旧缓存身份。引用ID合格不证明叙事科学正确，真实最终摘要须复核。
- 中间每包上限ceil(要点数/2)、最多6，传输8k含真实元数据；所有摘要输出正文≤8k。进展至少25%条数或15%正文字符且不扩张，最多12层。检查点带schema/accepted及code/rules/Skill/schema摘要和requested_model，被拒层保留完整输出但status=failed，stage_output不能将它当成功恢复。普通有核实输入的空批、空最终、无效引用和膨胀结果在缓存前拒绝；无核实事实可合法为空。每包含缓存路径检查取消；旧冻结不迁移/改键。当前规则/输入资格及模型真实身份在新隔离run单独绑定，不重跑原研究。
- 真实58775字符输入在主模型120秒超时后，摘要改为≤24000字符整包，并移除fact_id已能定位的重复URL/来源ID/locator，不移除临床定义。次要终点全量保留后，单研究最高111395字符；现按完整终点及重复共同研究上下文分包，标记study_part/总主要次要数，所有测量实例恰好覆盖一次。只剔除与端点记录重复的来源引用，未知未映射引用仍保留；单定义/共同上下文过大明确失败。R4实际284研究/580主要/2876次要规划151任务、最大23984字符；这是输入规划，不是模型或医学验收。旧冻结62任务仅覆盖此前投影。
- 分批复用沿用 stages 表的内部内容键，不增建任务平台/数据库。键绑定实际输入/事实ID、代码、规则、Skill、schema及指定模型；只缓存类型/引用合格结果，不冒充专业审阅。角色为 cache 的记录与真实 model/model_error 分开。
- `pipeline/scope.py` 在调用前规划所有完整候选批次（≤30项/≤60000字符），共享别名歧义按全项目集合判断而非批次碰巧命中。显式ID须在当前批且名称匹配；旧名称式结论只按全项目唯一的字面名称/别名兼容，不删除标点。重复、缺项、错绑均待核。无绑定问题的批次沿用stages内容键恢复，另绑定项目来源集合id/digest/text_digest；来源变化保守失效，正常null结论可复用。逐批事务写回，不重做已完成未变批次，不建新表。
- `pipeline/extraction.py`以完整研究及其全部事实引用规划输入，`read_project_fact`返回当前项目完整值/上下文并复用长结果分页。`queries.py`仅共享项目读取，`recovery.py`仅复用现有stages来源绑定回执，不增执行平台或表。输入、提取器/工具实现、Skill、schema、模型及已读取/引用来源版本改变时重做对应单元；来源包括无输出事实时已读取的资料。引用URL同秒新版本按rowid稳定择新，未知/跨项目来源不借用。
- ctgov.search及模型工具默认完整游标；正整数是显式检索预算，输出标full/explicit_bounded。去重保留源序，缺失登记号、循环游标和无新增页明确失败。试验摄取/抽取默认无静默15/30上限，显式工作预算保留pending_trials/pending_drug_ids/pending_units；完成单位同run来源版本复用，不冒充新模型调用或刷新。源变化后的科学事实投影另需M5完成，不能由回执缓存替代。
- 开发入口run_live.py支持对已有隔离候选的`--only-stage`验证，直接调用同一生产Stage；analysis成功后调用同一renderer。回执scope=stage、pipeline_acceptance=NOT_RUN，与完整研究模式分开；记录实际模型/用量、开始结束源hash及运行脚本hash。该运行成功不自动满足M1或发布门，禁止覆盖原项目/冻结输入来做阶段试验。
- 新增 Skill：写 SKILL.md + （必要时）在 `domain/models.py` 增加输出模型 + 在 stages 中接入。

## 5. 中国来源现状（实测）
- `pipeline/expansion.py`复用注册工具、CAS和stages单元回执：每个别名/靶点/企业种子生成中国CT.gov+三登记/CDE/NMPA查询及全球CT.gov/全网查询，按实际参数稳定去重并保留实体owners。最多3轮，显式预算保存pending；只要新查询未做完就IncompleteWork，来源blocked/failed按FR5继续其他资料但expansion_complete=false。没有新增Skill/表/路由器。
- 来源回执先于模型解释保存，恢复不重复已完成fetch；source ID/digest、实现/规则、提供方及实际参数绑定。解释键另含任务、Skill、schema、模型与来源，采用和解释回执同一事务。空/损坏结构不算无结果，阻断/失败不缓存为成功；空候选集合不算宇宙接受。一次真实中国CT.gov扩展查到1研究，仅证明来源可执行；中国直连与召回门仍未过。
- 搜索响应先核验JSON对象、结果数组/条目及错误状态；无可核验集合不判0。SerpApi只有文档明确的Success+Fully empty为空成功例外（可含error）；见[官方状态合同](https://serpapi.com/api-status-and-error-codes)。请求失败只保留状态码/异常类别；site备用检索的blocked/failed单独记账，来源未接通不借安全测试算通过。
- 中国登记平台httpx直连挑战仍记blocked；显式CIW_CHINA_EGO_SPACE_ID启用现有Ego公开UI桥，复用指定空间p1，不创建/claim/profile discovery。随包sources/china_browser.mjs驱动普通搜索/Next，逐页校验查询、序号、总页/条数、CTR/公开详情ID及重复；全部收齐才返回mode=browser/complete=true。只提取公开表格，不存cookie/隐藏字段/运行原始报错。超时已获有效页入CAS但不签收完整；其他来源继续按FR5执行。site备用独立记账。
- 列表来源含公开POST request_context(method/registry/query)，不伪造GET详情URL；recovery对该上下文取本项目最近实际导入版本，其他查询不会相互失效。同上下文新版本仍失效，无scope旧回执只读兼容。browser_checked有实际浏览器核查时间，无虚构HTTP状态；imported与网络核查分开。
- 完整结构化登记行代码直接写暂定drug/trial和带来源/页/行的显式关系，保留整条药名和unknown纳排，不再将464条重复送模型抽取；科学纳排仍走既有coverage-review。没有新增事实表/Skill/浏览器框架。
- CDE受理目录已接同一Ego空间与现有CLI传输，单独cde_browser.mjs/cde_capture.py消费实际八列表头；只扩展现有_invoke的内部脚本/filters选项，不新建执行器。ChinaArgs.query_kind明确drug_name/company/acceptance_number；未指定/indication/target不进入药名框，按blocked/site路线记账。反向扩展把原词送单字段（中国登记也用原始关键词），不拼适应症到药名/企业框。CDE实现及配置空间进入来源缓存键，栏目+六筛选进入request_context；相同URL的不同查询不相互覆盖。
- CDE强制全部年度/类型，完整翻页并保留八列原值/原公司复合文本/空格。公司列→company_text，承办日期→handled_date_text，不认定申办方/MAH或获批/首次公开时间。受理引用放暂定drug.attrs，不生成trial或临床事实；纳排仍走既有coverage-review。CDE空tbody“暂无内容”+无pager保留真实文本/page_size=null，不造数字页脚。已观察的2015及以前选项原样保留；表单筛选在捕获JSON中，列表URI不接受查询/会话参数。错误/部分页保存有效来源但不签收完整。
- CDE新报化药IND切片使用cde_review_capture.py/cde_review_browser.py及同一Ego传输；既有工具增加明确cde_section，不另建执行器。完整十二列/本页图例/范围/分页核对后精确查找受理号；JSON locator保持原始pages数组位置。同受理号的不同观察保留，未知/冲突图形记录内部原因，不按图标名选状态。只追加到有本项目受理来源支持的既有候选引用，0新试验/临床事实。同run共用fetch_cache，以项目/run/空间/代码版本作键，CAS校验后标cache_reused并登记本次读集；新run重读公开页，缓存不伪装新核查。部分页保全但不成功缓存。其他审评序列/公示栏目仍待接通；登记详情原表与NMPA精确证书已另接通，全量应查详情/许可目录及M2专家金标准召回仍待验收。
- NMPA来源读取与事实采用分离：trial_evidence中的nmpa_evidence重查已发现证书，nmpa_ingest核来源及当前采用规则后，用实体原名或当前有来源名称唯一关联，原子采用identity.name_zh/name_en与status.china_mah；发现中文名/别名不作认证依据。nmpa-current在项目+证号+类别内只允许一个当前实体，指向source/snapshot/采用规则；全项目比较旧观察，跨实体新观察保留冲突，不产生第二个current。DB当前集合要求该精确绑定和当前采用规则；旧事实/源不改，规则升级重核固定源，不循环借旧规则名称认证自己。共享drug_identity用于A/B/C及组别/设计字段；共享company_evidence呈现字面日期，过期于观察日只作许可记录持有人。来源失败保留已完资料但运行未完成，身份未解和网络失败分记，不新增表/平台或审批。
- cde_resume.py为受理/审评共用的同run原始分页读取器：最新匹配来源已完整则不回退，未完整须CAS/范围/生产校验器验证；只读无事件写入。既有适配器登记cache_read并传第一页内容/总数/页长锚点；两个MJS先取新第一页，不匹配则全部新采，匹配则用实际分页跳转补缺口。宿主再核验实际新页/复用页和锚点，合并后重跑完整集合校验，保存reused_source_ids/reused_pages/new_pages_checked；旧来源不改写。明确空页元数据使用实际current=0，不用循环索引。共用实现hash进入相关缓存/冒烟清单；无新增框架或数据表。
- china_detail.py/.mjs注册china_trial_detail：先核本项目/run/列表CAS与CTR—detail_id绑定，再用同一Ego空间的原生查询及详情popup读取。只捕获基本身份和临床表/内表，联系人/研究者联系方式不进入该来源包；内表逐定位核对父单元格，完整原文另入text_digest。新源经register_text登记，browser_checked与同run cache_reused分开；缓存校验raw/text/context和代码版本，新run实际重读，不新建浏览器框架、数据表或自动事实采纳路径。公开详情URL不是单研究永久链接，原始CTR/detail_id保留在request_context及捕获字节中。
- ExtractedFact.source_id为可选精确版本指针。抽取调用者仍只接受本项目本次实际读取且URL一致的版本；中国登记设计/试验事实另需来源CTR匹配entity。未指定时只允许唯一来源，显式错误ID不能改挑另一个。已有verify原文/数字/上下文及事务采纳不变。extract-design的已知CTR输入给出detail_tool，工具脚本/解析版本进入该Skill单元失效键；不迁移旧冻结研究或伪装已做新核查。
- CT.gov `query.locn=China` 可用（PNH 实测 52 条）。

- `nmpa_detail.py/.mjs`注册nmpa_product_detail：只读已明确定位的境内/境外公开证书，不替代目录检索。沿用Ego传输/指定空间p1、现有CAS/sources/read-set/分页工具；严格官方HTTPS记录URL、类别/证号/表头/原字段绑定，MAH、制造商、境内责任人及发证/批准/有效日期分开。原始可见行与字面全文分别存储，published_date为空，不以许可日期倒证历史公开。按项目/run/空间/URL/证号/类别/实际代码键验证缓存的原字节/全文/上下文；新run重新浏览，读取与复用回执分开，无事实/实体自动采用。真实两证书40/16字段及同run复用/新run重核通过，仅该来源工具组件；全目录、适应症批准、集团和M2/M3仍未接受。CAS统一拒绝非64位小写SHA-256命名，非法元数据不触发目录外读取。

## 6. 配置（环境变量）
### 当前事实下载
复用DB.tx/current_facts和现有全局鉴权，export.py在单一读取快照内联结本项目实体与精确source_id版本，输出固定ciw2-facts-v1 JSON或UTF-8-BOM CSV；附来源digest而不读CAS全文/meta或日志。CSV保留value_json/context_json的JSON类型，其他文本公式转义留字段清单；不存在/跨项目来源不借用，非有限值明确409。一个只读下载路由和工作台链接，不加任务/缓存/表/模型路由，原facts API形状不变。
### C阅读层
沿用单一portal.js/kangzhe.css及Jinja。样本量图保留全部数据，用dataZoom限定可读窗口而非Top-N；密集/稀疏高度按数据量，期别独立高度和完整名称/计数图例。完整入排details为无JS基线；有native dialog时单个模态容器临时移动原DOM内容，关闭恢复原位/触发焦点，使用textContent显示研究名，不生成另一份科学数据。长原文与事实依据两列，保留原引文/链接，不引入下钻框架或新的状态库。

### 共用临床身份与入排强调
- `domain/outcomes.py`提供七种可逆阅读标签；B在同来源组—药物绑定之后投影，不写DB或扩展本体。原始标题保留，PK分析物仅用明确绑定的完整药名；缩写扩展/混合测量不被一个优先级规则吞并。`results.py`保留现有测量frame并附阅读域，未解记录不丢弃；B领域/检索共用可见fact集合，仍使用单一ECharts实例及完整表。分类不改变单位、人群、时间、源版本或数值资格。
- `render/trial_identity.py`为A/B/C共享临床身份读取投影：已确认关联药物/中文名、来源适应症、核实期别及来源支持的MAH/申办方。按精确项目别名显示中文适应症，不用项目标题覆盖不同疾病；MAH不取未核实attrs或推测集团。旧登记无current link时只读兼容唯一同研究code:ctgov来源。B先绑定真实组—药物，再附研究身份；图形稳定键仍为登记ID，标签为临床信息。
- `render/eligibility.py`返回规则与无损文本segments，不返回可信HTML；Jinja逐段转义后以有限语义角色强调。规则保留source_start/end、section_title和clause_start，按原条款/队列归组；原文DOM textContent必须逐字相同。vIGA与IGA不互换，复合逻辑按来源顺序保存，未识别语句不删改。
- C所有依据与完整入排复用一个native dialog，原DOM移动后归位，Esc回实际触发者。终点索引同研究筛选并报告可见/总数。摘要不重复带eligibility_reading/clauses全文副本，但保留结构化规则、完整原条款、队列和引用；不引入新执行平台。

### 环境项
`CIW_DATA_DIR` `CIW_SKILLS_DIR` `CIW_LLM_BASE_URL` `CIW_LLM_API_KEY` `CIW_LLM_MODEL` `CIW_LLM_CHECK_MODEL`
`CIW_WEBSEARCH_PROVIDER`(tavily|bing|serpapi|none) `CIW_WEBSEARCH_API_KEY` `CIW_WECHAT_SEARCH_CMD`
`CIW_CHINA_EGO_SPACE_ID`(可选已授权专用空间) `CIW_CHINA_BROWSER_TIMEOUT_S`(默认240秒)
`CIW_NCBI_API_KEY` `CIW_HTTP_TIMEOUT_S` `CIW_MAX_AGENT_STEPS` `CIW_ACCESS_TOKEN`。

### 当前归并与视觉集成（2026-10-25）

- 摘要复用现有read_project_fact；RunContext从当前run的analysis_basis检查点注入本包一对一短引用，只在该工具上下文解析。完整值和来源由已有工具分页返回，缓存不伪造医学语义接受。
- 前端复用现有Jinja/JS/ECharts。官方Kangzhe7.1.1的Logo/tokens/motion原字节与hash登记在static/kangzhe-assets.json；一个kz-site生命周期只挂环境光场和摘要/KPI指针光，不接管导航/图表/下钻、不旋转数据平面。pagehide释放、pageshow重挂，减少动态/打印正常阅读。
- 本产品是临床查阅任务，使用紧凑标题/统计栏、图表/表格/原文入口；不插入占据首屏的装饰电影或虚构进程。桌面1440/1600/1920/2560按实际可视区检验，正文18px、辅助16px；原文与证据完整保留。

### 纳入优先审评来源增量

- cde_priority.py/.mjs复用现有china_registry_search、Ego传输、CAS、同run fetch_cache及cde_resume/merge_capture；一个固定公开栏目和九列解析，不加执行器/表/权限/DSL。完整首锚和分页集合闭合后才精确查受理号；新run重新核查，同run缓存仅代表已读资料，不冒充新浏览器访问。
- 受理号缺失为来源字段级问题：原始文本和完整行保留，解析ID为null、记录具体原因；不删除整页，不用“无”当实体ID，也不伪造匹配。受理来源绑定成立才将原行和来源ID追加到cde_priority_refs，与cde_review_refs分离；不生成药物/试验/批准事实。
- 失败捕获在确认官方无凭据URL后保留原始JSON至既有CAS及source_capture_rejected指针，accepted=false；它不是合格来源或成功缓存。有效分页另以complete=false来源保全。缺首锚时重新核查完整目录，不能把新首锚补进旧捕获来冒充可恢复。普通trial_evidence复用china_evidence入口，按全部已证明受理ID批量读取两个新报序列及纳入优先目录；一个栏目一次完整捕获，不逐药重复抓全站。cde_evidence沿用stages来源绑定回执，规则/代码/证明集合与源版本共同决定同run复用；新run重新浏览。栏目失败单独pending，继续其他栏目与CTgov。受理证明必须经完整CAS与原行药名/受理号/页行/企业角色及日期核对；持有真实source_id不等于属于另一药物。

- priority_proposed复用同一cde_priority.py/.mjs的两个已观察栏目参数，不建新框架；列名/字段映射、tbody/控件及请求上下文均显式分离。parser默认仍为priority_included，另一栏目必须显式选择，错误列合同拒绝；同一source_id不得跨栏目缓存。拟优先原行无受理号时ID=null、原字节保留，只能成为未解来源，不按名自动借用接受关系。cde_priority_proposed_refs独立于已纳入引用；普通collector固定调度四个已验证范围。

- endpoint_label沿用显示专用完整语法，支持明确的应答阈值列表及较基线改善阈值；不读取药物/适应症字典。量表代码与备选阈值须一致，未知限定/统计/条件不缩写；原endpoint、frame hash、fact_id及原始数值不变，图/表共用，完整题目在原定义保留。该投影不参与科学匹配或共轴资格。

- 多阈值父题若有且仅有一个源分面代码与完整阈值列表印证，图题用该分面+较基线应答；完整表的父题短名和原定义仍保留全部备选阈值。不让EASI-50曲线的标题同时突出50/75/90三个结局；未知/冲突分面不猜。只改变label，不改变frame/id/分面集合或事实。

- summary_budget是既有摘要计划的确定性辅助模块，以当前事实完整工具响应和任务元数据计算预计展开量；软目标用于包装多个完整观察，硬上限允许单个完整观察。原始事实、引用映射、全文、报告分组不改。全量父任务若已有同签名合格回执，保持原任务并由_analysis_call原后检验复用；未完成父任务按完整要点拆，仍用原stages表及原子缓存。最终短正文亦检查展开量，新模块字节进入ANALYSIS_CODE_HASH；跨版本缓存须显式验证task/schema/Skill/source及后检验，不静默把旧key当新key。

### 站点地域口径

CT.gov countries原值保留；新trial.china_site带geographic_scope=mainland_china，countries保留locations_complete。只要明确有China即有大陆站点；不含China且部分地点缺失时为unknown，非false。A大陆站点计数仅用明确当前scope或来源国家列表的正向/完整性证据；C分别显示大陆/香港/澳门/台湾。旧宽域记录进入legacy_geography依据及内部遗漏ID记录，不进入当前大陆计数/摘要输入，原数据不改。地域标记不判定中国开发纳排。

### 来源后研究范围审查

现有药物纳排继续由coverage_review执行。trial_evidence后新增轻量trial_scope_review阶段，调用scope.review_orphan_trials；仅零项目drug-trial父关联的研究进入，不重复评判已有药物父项的研究。沿用9 Skills、ScopeResult和同一身份绑定/完整分批/缓存/事务，无新平台或schema。输入candidate_kind=trial明确研究语义，既有wire字段drug承载原研究登记名。显式false影响该研究的共享报告查询，null与缺失/重复/错误身份保留待核；不变更源层事实或链接。

### 范围缓存与CDE分类传递

复用现有scope_batch阶段记录，不加新schema或表。每批查缓存前取当前项目来源集合，模型/工具结束且结果身份检查无问题后按调用后的源集合记录；完整task、source id/digest/text_digest、code、Skill、schema、model、harness仍参与签名。后批新增来源使前批保守失效的行为保留，不声称逐来源依赖优化。CDE临时候选引用完整保留drug_type/registration_class，按同source_id+acceptance_number补全原引用；proven_acceptance_refs回查原始CAS时校验可选新增字段，旧引用不凭空补类别、返回原始行的真实字段。

### 当前摘要运行隔离与引用往返

Service.latest_findings在同一SQL中按project_id选created_at DESC,rowid DESC的最新run，再取该run对应analysis_<report>的succeeded/nonempty output；不跨run回退。当前run其他阶段failed仍可读取已成功对应分析；静态历史页与旧stage不改写。整stage升级失效由下节独立运行绑定处理；其完整项目接受仍单列。

summary_lineage.normalize_references读取本run的basis，只对task.verified_fact_ids的一对一map反查工具返回真实ID，转为该包短引用、去重同一事实；外来/其他包引用原样交成员校验拒绝，不静默过滤。新结果/缓存对象均不原地变更，resolve_summary恢复原科学ID及选择记录。旧schema/Skill缓存不改键伪装当前资格。

### 普通流程身份与阶段运行版本

复用stages表，不加调度平台/数据库。runner首次进入真正空运行时原子写入pipeline_scope:ordinary（project/run绑定）；有旧阶段/单元却没有相符普通流程身份的记录，在任何阶段、模型或来源调用前拒绝，保留其全部stage/unit/科学行，交合格恢复候选处理。不能把独立归并/临床抽取实验自动当作普通项目运行，也不补签旧版本。

stage_dependencies显式列出各阶段实际Python/来源脚本/Skill依赖；stage_versions绑定已加载函数及工厂配置、默认参数、相关模块/正则、Skill正文/工具顺序/输出schema/预算、请求模型与前置阶段名。只读资产变化仅失效render，不使研究/摘要单元因新增runner元数据而改key。Python行为使用已加载code对象，不用文件名/行号/对象repr冒充运行身份；从磁盘执行的脚本及模板/JS/CSS按实际字节绑定，阶段前后校验，变化不签成功。

render回执另绑定实际A/B/C文件的字节摘要；文件名输出JSON不足以证明页面存在或未被替换。标准备份不带门户，恢复后仅缺失/改动文件对应render失效，不重做研究。新渲染字节追加独立回执，不覆盖同名文件旧回执。成功输出与stage_version回执同一db.tx提交；回执追加且检查schema/内容/行名，失败或碰撞不覆盖历史。恢复跳过完全兼容前缀，从最早改变/缺失/顺序变化/输出不匹配处先置下游pending，再继续。失败或取消阶段不作成功缓存；同模型同规则合格单元仍可复用。内部身份/回执不进入计划阶段显示。此为显式依赖方案，不承诺发现未列出的外部依赖变化或两次快照间改后又还原的文件；完整运行/来源与医学接受不能由该控制组件替代。
