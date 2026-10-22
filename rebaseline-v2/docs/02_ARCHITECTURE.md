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
| coverage_review | Skill | ABC | 是 | 别名归并、纳入/排除/待定 |
| trial_evidence | 代码 | ABC | 是 | 按药物检索 CT.gov，干预名匹配后入库设计/结果/AE 事实 |
| extract_results | Skill | B | 否 | 论文/会议/FDA 结果抽取（逐字引用） |
| extract_design | Skill | C | 否 | 中国登记/论文方法学设计抽取 |
| verify | 代码 | BC | 是 | 原文核验 + 分级 + 可选二次模型 |
| analysis_A/B/C | Skill | 各自 | 否 | 中文要点（不新增事实） |
| render | 代码 | ABC | 是 | 写门户快照；平台也实时渲染 |

可恢复：同一 run 重跑时跳过 `succeeded` 阶段。非阻断阶段失败 → 记录并继续（运行状态 succeeded + 错误说明）。

## 2. 数据模型（store/db.py）
- `projects` `runs` `stages` `agent_steps`：运行与留痕。
- `sources`：每次抓取（URL、原始字节 digest、纯文本 digest）。**抽取只能引用本项目已读取的来源**。
- `entities`（drug/company/trial/target，含别名、发现路线、纳排）+ `links`（drug-trial / drug-company / drug-target）。
- `facts`：追加式；`supersedes` 指向被取代的版本；`tier` `status` `quote` `quote_start/end` `context`（组/时间点/人群/统计对象/分母/终点）。
- `coverage`：每条检索路线的状态（ok/failed/blocked）、命中、新增实体。

## 3. 信任模型
1. 代码解析的结构化注册数据（CT.gov）：`extracted_by=code:ctgov`，按 JSON 路径直接取值 → verified。
2. LLM 抽取：必须给 `source_url` + 逐字 `quote`；verify 阶段检查 来源已读取 → 片段在原文中 → 数值在片段中。
3. critical 且通过 → 可选 `CIW_LLM_CHECK_MODEL` 二次核对（只回答 YES/NO），不同意 → conflict。
4. 门户：未核实/冲突的 critical 字段只进表格（红色标记），不进图表数值轴。

## 4. DSH（内嵌最小 Skill Harness）
- Skill = `skills/<name>/SKILL.md`：frontmatter（name/description/tools/output/max_steps）+ 正文（工作说明）。
- System prompt = Harness 通用规则 + Skill 正文；User = 任务 JSON。
- 模型只能调白名单工具；工具异常以 `{"status":"tool_failed"}` 回给模型（不当作无结果）。
- 输出只能通过 `submit_result`，Pydantic 校验失败把错误回给模型重试；预算耗尽抛 `AgentBudgetExceeded`。
- 新增 Skill：写 SKILL.md + （必要时）在 `domain/models.py` 增加输出模型 + 在 stages 中接入。

## 5. 中国来源现状（实测）
- 药物临床试验登记与信息公示平台：对 httpx 返回 HTTP 202 + JS 挑战页 → 记 `blocked`，退回 `site:` 全网搜索。
- CDE/NMPA：前端渲染为主 → 同上。M2 实现 Playwright 适配器（真实浏览器、限速、缓存）。
- CT.gov `query.locn=China` 可用（PNH 实测 52 条）。

## 6. 配置（环境变量）
`CIW_DATA_DIR` `CIW_SKILLS_DIR` `CIW_LLM_BASE_URL` `CIW_LLM_API_KEY` `CIW_LLM_MODEL` `CIW_LLM_CHECK_MODEL`
`CIW_WEBSEARCH_PROVIDER`(tavily|bing|serpapi|none) `CIW_WEBSEARCH_API_KEY` `CIW_WECHAT_SEARCH_CMD`
`CIW_NCBI_API_KEY` `CIW_HTTP_TIMEOUT_S` `CIW_MAX_AGENT_STEPS` `CIW_ACCESS_TOKEN`。
