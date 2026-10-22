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
Service在初始化模型前检查项目与resume_run归属，不存在或跨项目请求返回明确冲突且不修改旧run。历史截止日暂由共同availability守卫阻断：启动产生失败记录，不发模型/来源请求；report_data与HTML入口也拒绝输出未筛选的历史报告，Web返回409。M5须完成逐版本资格后替换此守卫，不能直接解除检查。

## 2. 数据模型（store/db.py）
- `projects` `runs` `stages` `agent_steps`：运行与留痕。
- `sources`：每次抓取（URL、原始字节 digest、纯文本 digest）。**抽取只能引用本项目已读取的来源**。
- `entities`（drug/company/trial/target，含别名、发现路线、纳排）+ `links`（drug-trial / drug-company / drug-target）。
- `domain/identity.py`只做大小写/空白形式归一及字面名称/已知别名匹配，保留标点，不推断药学等同。scope、trial_evidence和verify复用；scope缓存绑定该规则源码hash。明确且唯一的试验关联用drug-trial；宽检索/共享别名保留drug-trial-candidate（pending及原干预名），沿用links不增表。后来字面关系确认时保留候选记录并标resolved_literal_match；不是自动解决剂型/组合药学语义。
- `facts`：追加式；`supersedes` 指向被取代的版本；`tier` `status` `quote` `quote_start/end` `context`（组/时间点/人群/统计对象/分母/终点）。
- `coverage`：每条检索路线的状态（ok/failed/blocked）、命中、新增实体。
- 发现工具逐批保存登记原名与药物—试验关系，最终模型提交失败不抹掉已读来源；不据此推断创新属性或监管身份。
- 同一 RunContext 的相同 GET 复用已抓 CAS 字节，新的运行/恢复上下文重新核查网络；不会把历史缓存当作本次核查。工具结果访问授权仍限定当前 Skill。

## 3. 信任模型
1. 代码解析的结构化注册数据（CT.gov）：`extracted_by=code:ctgov`，按 JSON 路径直接取值 → verified。
2. LLM 抽取：必须给 `source_url` + 逐字 `quote`；verify 阶段检查 来源已读取 → 片段在原文中 → 数值在片段中。
3. critical 且通过 → 可选 `CIW_LLM_CHECK_MODEL` 二次核对（只回答 YES/NO），不同意 → conflict。
4. 门户：未核实/冲突的 critical 字段只进表格（红色标记），不进图表数值轴。
5. verify的实体写回必须唯一关联本项目既有实体或明确登记号；未知/共享别名不默认落到父药物。原抽取事实不删除，阶段输出identity_issues/unresolved_entities；其余正常事实继续核验。候选关联和身份问题不代表科学验收通过。

## 4. DSH（内嵌最小 Skill Harness）
- Skill = `skills/<name>/SKILL.md`：frontmatter（name/description/tools/output/max_steps）+ 正文（工作说明）。
- System prompt = Harness 通用规则 + Skill 正文；User = 任务 JSON。
- 模型只能调白名单工具；工具异常以 `{"status":"tool_failed"}` 回给模型（不当作无结果）。
- 输出只能通过 `submit_result`，Pydantic 校验失败把错误回给模型重试；预算耗尽抛 `AgentBudgetExceeded`。
- 最后两次交互提示剩余预算；最后一次只开放 submit_result 并请求该函数，不再无限追加检索。即使强制提交，结构/来源校验仍照常。
- 模型按明确环境配置顺序备用；错误或缺失的实际模型身份拒绝采用，返回的真实模型与使用量留痕，不用请求名冒充响应身份。
- 只有思考信息、没有可用正文/工具结果，或必需提交未履行，属于协议未完成：立即记录并仅走已配置备用，不把它当作正常回复耗尽整个工作单元。错误回执保留类别、实际模型与可用用量，不记录服务原始错误正文或凭据。
- 大数据摘要先建立全部完整记录的预算内任务，再执行；无固定Top-N。多批要点超预算时继续有界归并，输出至多6条；不收敛即明确失败。完整门户数据不裁剪。
- 分批复用沿用 stages 表的内部内容键，不增建任务平台/数据库。键绑定实际输入/事实ID、代码、规则、Skill、schema及指定模型；只缓存类型/引用合格结果，不冒充专业审阅。角色为 cache 的记录与真实 model/model_error 分开。
- `pipeline/scope.py` 在调用前规划所有完整候选批次（≤30项/≤60000字符），共享别名歧义按全项目集合判断而非批次碰巧命中。显式ID须在当前批且名称匹配；旧名称式结论只按全项目唯一的字面名称/别名兼容，不删除标点。重复、缺项、错绑均待核。无绑定问题的批次沿用stages内容键恢复，另绑定项目来源集合id/digest/text_digest；来源变化保守失效，正常null结论可复用。逐批事务写回，不重做已完成未变批次，不建新表。
- 新增 Skill：写 SKILL.md + （必要时）在 `domain/models.py` 增加输出模型 + 在 stages 中接入。

## 5. 中国来源现状（实测）
- 药物临床试验登记与信息公示平台：对 httpx 返回 HTTP 202 + JS 挑战页 → 记 `blocked`，退回 `site:` 全网搜索。
- CDE/NMPA：前端渲染为主 → 同上。M2 实现 Playwright 适配器（真实浏览器、限速、缓存）。
- CT.gov `query.locn=China` 可用（PNH 实测 52 条）。

## 6. 配置（环境变量）
`CIW_DATA_DIR` `CIW_SKILLS_DIR` `CIW_LLM_BASE_URL` `CIW_LLM_API_KEY` `CIW_LLM_MODEL` `CIW_LLM_CHECK_MODEL`
`CIW_WEBSEARCH_PROVIDER`(tavily|bing|serpapi|none) `CIW_WEBSEARCH_API_KEY` `CIW_WECHAT_SEARCH_CMD`
`CIW_NCBI_API_KEY` `CIW_HTTP_TIMEOUT_S` `CIW_MAX_AGENT_STEPS` `CIW_ACCESS_TOKEN`。
