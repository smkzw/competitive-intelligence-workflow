# 00 · v1 仓库 Review（重基线依据）

本文件来自用户提供的专家包，是重基线输入；不代表本次开发已重新执行这些 v1 测试或获得清理历史/强推授权。本机当前结果只记在 STATUS。

> 对象：`smkzw/competitive-intelligence-workflow` main（517 commits，2026-08-10 → 10-12）。
> 方法：干净克隆 + `uv sync --frozen` + 分组跑测试 + 代码/文档/仓库卫生扫描。下列数字均为本次实测。

## 1. 结论

v1 的**领域知识是资产，工程形态是负债**。
- 资产：终点/时间点/安全语义规则、来源策略、CT.gov/PubMed/中国来源连接器的经验、康哲设计 tokens、F01–F11 自查清单。
- 负债：14.9 万行 Python 只负责「校验 + 渲染」，真正的研究由外部 Agent 宿主（Codex/Hermes/OMP）完成；
  信任链是「模型签发模型」；门户终验连续 24 轮未通过，最近约 50 次提交几乎全是门户呈现微修（第十五–十九「根因包」）。
- 判断：继续在 v1 上修补的边际收益已为负。按用户决定 **重基线**：保留知识，换掉骨架。

## 2. 实测 Bug 与问题清单

### P0（阻断 / 安全 / 合规）
| # | 问题 | 证据 | v2 处理 |
|---|---|---|---|
| P0-1 | 干净克隆测试无法跑完 | `tests/pdf/*` 与 `tests/renderers/test_pdf_vertical_slice.py` 依赖 `reportlab`，但它不在依赖里 → 收集失败、整套中断 | v2 删除 PDF/PPTX 渲染；依赖与测试同仓声明 |
| P0-2 | 验收夹具缺失 | `fixtures/acceptance/current-v2/catalog.yaml` 未入库（34 条测试引用） | v2 夹具全部入库且小（≤50KB） |
| P0-3 | acceptance + application 两组：**60 failed / 39 errors / 261 passed / 5 skipped** | 见 §3 分类 | v2 测试 31 条全绿，CI 必须全绿才合并 |
| P0-4 | 公共仓库泄露本机路径 | 967 个文件含个人目录绝对路径 | v2 规则禁止；见 04_AGENT_RULES |
| P0-5 | 公共仓库含第三方全文 | 会议 PDF（EADV）、PMC 渲染 DOM 等入库 | v2 原文只进本地 CAS，`.gitignore` 排除数据目录 |
| P0-6 | 仓库体积失控 | `.git` 1.2GB、工作树 3GB；runs 2708 / docs 929 / packets 834 / output 662 / prompts 612 / reviews 471 个文件入库 | v2 禁止提交运行产物；旧仓建议 `git filter-repo` 清理（见 §6） |
| P0-7 | 信任根自签 | REVIEW F01：独立模型签发 = 另一个模型说「对」 | v2：确定性原文核验（`verify/quote.py`）为根，二次模型仅作可选附加 |
| P0-8 | 安全语义错误 | F06：`Non-serious TEAE` → `any_teae`；Grade 误归 ≥3 | v2 `domain/semantics.py` + 单测覆盖 |
| P0-9 | 数值投影错误 | 192.5% 类比例（事件数 ÷ 人数）；分母借用（F05） | v2：比例只在 `count_participants` + 同组明确分母时派生；单测覆盖 |

### P1（正确性 / 可维护性）
| # | 问题 | 证据 |
|---|---|---|
| P1-1 | 超长函数 | 48 个函数 >200 行；`application/run_service.py::run_project` **2054 行** |
| P1-2 | 遗留渲染器仍在 src | `pdf_native` 5664 行、`pptx_master` 3539 行、`html_ppt` 3504 行（需求已改为平台内 HTML） |
| P1-3 | 「通用」渲染器硬编码具体项目 | `report_a.py` PNH 专用正则/翻译表（约 L1273、L1643）；`report_b.py` 写死 NCT 标签（L277）；`html_ppt` 讲稿写死药名/NCT |
| P1-4 | 测试与模型漂移 | B `matrix_view` 测试用 `comparison_rows`，模型要求 `rows`（`report_b.py:1534 ReportBPortalData`）；`test_r13` 断言 `width: 32px` 过期；A 人群描述残留英文 `randomized`；preview 测试期望 `failed` 实为 `capability_blocked`（环境依赖未标记 skip） |
| P1-5 | 测试套件太慢 | 6111 条，此环境 28 分钟只跑到 27% |
| P1-6 | 运行时不适合 Web 平台 | 研究依赖外部 Agent 宿主；编辑服务是本机 loopback；没有服务化的运行/恢复/状态模型 |
| P1-7 | 文档不可交接 | `STATUS.md` 108KB；HANDOFF 全是内部简写；ARCHITECTURE 指向过时 v1.3/PNH runbook/abc-v23；PRD v2.4 多层「最新裁决覆盖」 |
| P1-8 | 流程膨胀 | 每轮新增 packets/prompts/reviews，形成「写计划 → 审计划 → 修计划」循环，停滞原因在 9/22 REVIEW 已被识别但模式未改 |

### P2（体验）
- 门户信息密度高但不可筛选；中文临床表述与英文原文混杂；覆盖率作为「门」而不是可见指标，导致不过门就没有产出。

## 3. 测试失败分类（acceptance + application）
| 类别 | 原因 | 性质 |
|---|---|---|
| 夹具缺失 | `catalog.yaml` 未入库 | 仓库问题 |
| 环境 | Playwright 浏览器未安装；`reportlab` 缺失 | 依赖声明问题 |
| 真实漂移 | `rows` vs `comparison_rows`、CSS 32px、英文残留、`capability_blocked` | 代码/测试不同步 |

## 4. 删除 / 保留 / 新增

**删除（不移植）**：PDF/PPTX/HTML-PPT 渲染；本机编辑/同步/撤销/配置/离线分享（FR13–16，用户确认不需要）；
模型签发链；packets/prompts/reviews/runs 入库机制；所有项目专用硬编码。

**保留并移植**（见 05_PORTING_MAP）：`policies/*`（终点族 registry-v7、终点、时间点、study-role、innovation ontology、source-policy、recovery strategies）、
`connectors/*` 经验（CT.gov、PubMed、中国来源模型、监管、权威公众号）、康哲 tokens、REVIEW F01–F11 作为回归用例来源。

**新增**：单用户 Web 平台（FastAPI）、内嵌最小 Skill Harness、SQLite + CAS 事实库、确定性原文核验、覆盖率台账、
中国检索路线（必跑 + 反向扩展）、字段分级（critical/standard）、ECharts 门户。

## 5. 多 Skill 工作流是否合适？

**合适，但要收敛边界**：
- 用代码：抓取、CT.gov 结构化解析、原文核验、比例派生、图表与渲染、覆盖率统计。
- 用 Skill（LLM）：需求理解、候选发现与反向扩展、纳排判断、实体归并、非结构化原文抽取、中文要点撰写。
- v1 的 16 个内部 Skill 收敛为 **9 个**（intake、universe-china、universe-global、coverage-review、extract-results、extract-design、analysis-a/b/c），
  另有 4 个代码阶段（trial_evidence、verify、render、以及 CT.gov 解析）。
- Skill 不再由外部宿主执行，而由平台内嵌的最小 Harness 执行：白名单工具、Pydantic 输出校验、步数预算、全程留痕、阶段可恢复。

## 6. 旧仓库处置建议
1. main 冻结为 `v1-final` tag，不再在 v1 上开发。
2. 公共仓库清理（专家建议，未授权执行）：用 `git filter-repo` 移除 `runs/ output/ packets/ prompts/ reviews/` 与第三方 PDF/DOM，替换个人目录路径；强推前先备份。
3. v2 在 `rebaseline-v2/` 目录（或新仓库）开发；v1 仅作为移植参考只读。
