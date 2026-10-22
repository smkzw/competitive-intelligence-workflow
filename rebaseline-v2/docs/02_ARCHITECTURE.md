# 02 · 架构

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
| universe_china | Skill | ABC | 否 | 中国必跑路线 + 反向扩展 |
| universe_global | Skill | ABC | 否 | CT.gov / FDA / PubMed / 会议 |
| coverage_review | Skill | ABC | 是 | 全量候选分批纳排；明确ID写回，不擅自合并实体 |
| trial_evidence | 代码 | ABC | 是 | 按药物检索 CT.gov，干预名匹配后入库设计/结果/AE 事实 |
| extract_results | Skill | B | 否 | 论文/会议/FDA 结果抽取（逐字引用） |
| extract_design | Skill | C | 否 | 中国登记/论文方法学设计抽取 |
| verify | 代码 | BC | 是 | 原文核验 + 分级 + 可选二次模型 |
| analysis_A/B/C | Skill | 各自 | 否 | 中文要点（不新增事实） |
| render | 代码 | ABC | 是 | 写门户快照；平台也实时渲染 |

可恢复：同一 run 从最早失败阶段重新计算依赖分支，之前成功的前置阶段不重跑；待重算下游立即置 pending，不能沿用上轮空成功。非阻断阶段失败 → 记录并继续（运行状态 succeeded + 错误说明）；这不是产品验收信号。
`IncompleteWork`是例外：即使该阶段允许后续继续，存在预算/未完成单元时run最终仍failed，部分产物可用但不能显示工作已全完；runner保留partial output。CLI对失败或带错误运行返回非零，普通被拦来源仍依既有非阻断合同处理，不加新发布状态。
Service在初始化模型前检查项目与resume_run归属，不存在或跨项目请求返回明确冲突且不修改旧run。历史截止日暂由共同availability守卫阻断：启动产生失败记录，不发模型/来源请求；report_data与HTML入口也拒绝输出未筛选的历史报告，Web返回409。M5须完成逐版本资格后替换此守卫，不能直接解除检查。

## 2. 数据模型（store/db.py）
- `projects` `runs` `stages` `agent_steps`：运行与留痕。
- `sources`：按项目/URL/原始字节digest复用内容版本，保留首次存储时间。每次网络核查、缓存复用、导入另在agent_steps记录source_observation；只有network_checked含network_checked_at及实际HTTP状态。**抽取只能引用本项目已读取的来源**。
- `entities`（drug/company/trial/target，含别名、发现路线、纳排）+ `links`（drug-trial / drug-company / drug-target）。
- `domain/identity.py`只做大小写/空白形式归一及字面名称/已知别名匹配，保留标点，不推断药学等同。scope、trial_evidence和verify复用；scope缓存绑定该规则源码hash。明确且唯一的试验关联用drug-trial；宽检索/共享别名保留drug-trial-candidate（pending及原干预名），沿用links不增表。后来字面关系确认时保留候选记录并标resolved_literal_match；不是自动解决剂型/组合药学语义。
- `facts`：追加式；`supersedes` 指向被取代的版本；`tier` `status` `quote` `quote_start/end` `context`（组/时间点/人群/统计对象/分母/终点）。
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
- 真实主模型曾在144.583s返回，产品主请求改为300s而非120s；显式配置备用时主路仅尝试一次，然后按用户顺序切换，避免三次取消同样慢请求。独立无备用保留3次策略，DGX仍用显式路由时限，不改全局服务/effort。
- harness任务/assistant/工具记录超过20k时先写现有CAS，agent_steps只记有效JSON指针（digest/format/字符数），不截成破损JSON；assistant先排除reasoning正文。诊断读取验证CAS摘要，旧截断日志仅在固定数据重建及原前缀吻合时兼容，不重写历史。
- 只有思考信息、没有可用正文/工具结果，或必需提交未履行，属于协议未完成：立即记录并仅走已配置备用，不把它当作正常回复耗尽整个工作单元。错误回执保留类别、实际模型与可用用量，不记录服务原始错误正文或凭据。
- 大数据摘要先建立全部完整记录的预算内任务，再执行；无固定Top-N。多批要点超预算时继续有界归并，输出至多6条；不收敛即明确失败。完整门户数据不裁剪。
- 真实58775字符输入在主模型120秒超时后，摘要改为≤24000字符整包，并移除fact_id已能定位的重复URL/来源ID/locator，不移除临床定义。次要终点全量保留后，单研究最高111395字符；现按完整终点及重复共同研究上下文分包，标记study_part/总主要次要数，所有测量实例恰好覆盖一次。只剔除与端点记录重复的来源引用，未知未映射引用仍保留；单定义/共同上下文过大明确失败。R4实际284研究/580主要/2876次要规划151任务、最大23984字符；这是输入规划，不是模型或医学验收。旧冻结62任务仅覆盖此前投影。
- 分批复用沿用 stages 表的内部内容键，不增建任务平台/数据库。键绑定实际输入/事实ID、代码、规则、Skill、schema及指定模型；只缓存类型/引用合格结果，不冒充专业审阅。角色为 cache 的记录与真实 model/model_error 分开。
- `pipeline/scope.py` 在调用前规划所有完整候选批次（≤30项/≤60000字符），共享别名歧义按全项目集合判断而非批次碰巧命中。显式ID须在当前批且名称匹配；旧名称式结论只按全项目唯一的字面名称/别名兼容，不删除标点。重复、缺项、错绑均待核。无绑定问题的批次沿用stages内容键恢复，另绑定项目来源集合id/digest/text_digest；来源变化保守失效，正常null结论可复用。逐批事务写回，不重做已完成未变批次，不建新表。
- `pipeline/extraction.py`以完整研究及其全部事实引用规划输入，`read_project_fact`返回当前项目完整值/上下文并复用长结果分页。`queries.py`仅共享项目读取，`recovery.py`仅复用现有stages来源绑定回执，不增执行平台或表。输入、提取器/工具实现、Skill、schema、模型及已读取/引用来源版本改变时重做对应单元；来源包括无输出事实时已读取的资料。引用URL同秒新版本按rowid稳定择新，未知/跨项目来源不借用。
- ctgov.search及模型工具默认完整游标；正整数是显式检索预算，输出标full/explicit_bounded。去重保留源序，缺失登记号、循环游标和无新增页明确失败。试验摄取/抽取默认无静默15/30上限，显式工作预算保留pending_trials/pending_drug_ids/pending_units；完成单位同run来源版本复用，不冒充新模型调用或刷新。源变化后的科学事实投影另需M5完成，不能由回执缓存替代。
- 开发入口run_live.py支持对已有隔离候选的`--only-stage`验证，直接调用同一生产Stage；analysis成功后调用同一renderer。回执scope=stage、pipeline_acceptance=NOT_RUN，与完整研究模式分开；记录实际模型/用量、开始结束源hash及运行脚本hash。该运行成功不自动满足M1或发布门，禁止覆盖原项目/冻结输入来做阶段试验。
- 新增 Skill：写 SKILL.md + （必要时）在 `domain/models.py` 增加输出模型 + 在 stages 中接入。

## 5. 中国来源现状（实测）
- 药物临床试验登记与信息公示平台：对 httpx 返回 HTTP 202 + JS 挑战页 → 记 `blocked`，退回 `site:` 全网搜索。
- CDE/NMPA：前端渲染为主 → 同上。M2 实现 Playwright 适配器（真实浏览器、限速、缓存）。
- CT.gov `query.locn=China` 可用（PNH 实测 52 条）。

## 6. 配置（环境变量）
`CIW_DATA_DIR` `CIW_SKILLS_DIR` `CIW_LLM_BASE_URL` `CIW_LLM_API_KEY` `CIW_LLM_MODEL` `CIW_LLM_CHECK_MODEL`
`CIW_WEBSEARCH_PROVIDER`(tavily|bing|serpapi|none) `CIW_WEBSEARCH_API_KEY` `CIW_WECHAT_SEARCH_CMD`
`CIW_NCBI_API_KEY` `CIW_HTTP_TIMEOUT_S` `CIW_MAX_AGENT_STEPS` `CIW_ACCESS_TOKEN`。
