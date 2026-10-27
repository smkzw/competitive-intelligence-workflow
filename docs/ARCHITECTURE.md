# 架构 v2

## 1. 一句话

```
indications/<slug>.yaml ──► ciw pipeline ──► workspace/releases/<id>/release.json + site/{A,B,C}
                                                   │
                     医学经理工作台 evidence_design ◄─┘（ciw_release 适配器读 release；门户经路由托管）
```

## 2. 分层与依赖方向

只允许从上往下依赖，由 `tests/test_layering.py` 守住。

| 层 | 包 | 职责 | 不允许 |
|---|---|---|---|
| 配置 | `ciw.config` | 读取并校验适应症 YAML 和模型档位 | 访问网络 |
| 来源 | `ciw.sources.*` | 检索、获取、原件入 CAS；解析采集收件箱里的原件 | 做科学判断 |
| 抽取 | `ciw.extract.*` | 原件 → 带定位的事实（确定性；或 LLM 候选） | 跨试验比较 |
| 归一 | `ciw.normalize.*` | 干预→产品、结果组→臂、时间点、概念 | 渲染 |
| 核对 | `ciw.verify.*` | 异构模型抽取 + 确定性比对 + 仲裁，写核对账本 | 改原件 |
| 分析 | `ciw.analyze.*` | A 全景矩阵、B 临床问题分组与组间差、C 设计矩阵 | 读原件 |
| 发布 | `ciw.release` | 组装 release.json（Schema 校验）、内容哈希、current 指针 | 推断 |
| 渲染 | `ciw.render` | release → 三个门户（Jinja2 + ECharts） | 任何科学或翻译逻辑 |
| 编排 | `ciw.pipeline`, `ciw.api`, `ciw.cli` | 阶段串联、可恢复、对外门面 | — |

## 3. 工作区

```
<workspace>/
  raw/sha256/<aa>/<sha256>.<ext>   原件 CAS（不可变，可重放）
  captures/<source>/...            浏览器采集收件箱（CDE / NMPA / 公告 / 公众号）
  ciw.sqlite                       来源、事实、核对账本、LLM 缓存
  stages/<stage>.json              阶段产物（可单独重跑下游）
  releases/<release_id>/release.json
  releases/<release_id>/site/{A,B,C}/index.html ...
  releases/current.json            唯一 current 指针
  logs/run-<ts>.jsonl              运行日志（不入库）
```

`<workspace>` 由调用方给出。工作台默认读 `CIW_WORKSPACE_<SLUG>` 环境变量；没有设置时用 `~/Developer/ciw-workspaces/<slug>`。

## 4. 数据模型（`ciw.models`）

| 对象 | 关键字段 |
|---|---|
| `Source` | `source_id`=来源类型、URL、内容哈希的稳定组合；`kind`(ctgov/europepmc/cde/nmpa/company/wechat)；`url`、`title`、`publisher`、`published_at`、`fetched_at`、`sha256` |
| `Trial` | `trial_id`(NCT 或 CTR)；`ids`；`acronym`、`title`、`phase`、`status`；`dates`(start / primary_completion / completion / results_first_posted)；`sponsor`、`collaborators`、`countries`、`china`；`enrollment`；`design`；`arms[]`；`eligibility`；`outcomes_planned[]`；`product_ids[]`；`relevance` |
| `Arm` | `arm_id`、`label`、`type`(CT.gov armGroups.type)、`role`(experimental/active/placebo/none/other)、`interventions[]`、`description` |
| `Product` | `product_id`；`name_en`、`name_zh`、`codes[]`；`target`、`mechanism`、`modality`、`route`；`company`、`china_partner`；`innovative`、`inclusion_reason`；`is_own` |
| `OutcomeResult` | `trial_id`、`outcome_key`；`type`(PRIMARY/SECONDARY/…)；`title`、`description`、`timeframe`、`time{value,unit,weeks}`；`concept_id`、`domain`；`param_type`、`dispersion_type`、`unit`、`population`；`groups[{group_id,title,arm_id,role,n,value,spread,lower,upper}]`；`analyses[{group_ids,param_type,value,ci_pct,ci_lower,ci_upper,p_value,method}]`；`locator` |
| `SafetySummary` | `trial_id`、`timeframe`、`other_threshold`；`groups[{group_id,title,arm_id,role,serious{n,N},other{n,N},deaths{n,N}}]`；`terms[{term,organ_system,serious,stats[{group_id,n,N,events}]}]` |
| `Event` | 非结构化来源抽出的里程碑：`product_id`、`event_type`(approval/filing/topline/phase_start/licensing)、`region`、`date`、`detail`、`numbers[]`、`quote`、`status` |
| `Verification` | `fact_key`、`status`(registry/dual_agreed/arbitrated/needs_review/rejected)、`calls[{family,model,value,quote_ok}]` |

事实 ID 一律由自然键加内容哈希生成，同一原件重跑时 ID 不变。

## 5. 核对（`ciw.verify`）

```
原件文本 + 抽取 Schema
   ├─ 模型 A（家族 X）独立抽取 ─┐
   └─ 模型 B（家族 Y）独立抽取 ─┴─► 确定性比对（字段级规范化 + 原文引语校验）
                                    ├─ 一致且引语都在原文中 → dual_agreed
                                    └─ 不一致 → 模型 C（家族 Z）看到两份候选与原文后仲裁
                                         ├─ 选中一份且其引语校验通过 → arbitrated
                                         └─ 否则 → needs_review（进入待核队列）
```

- 家族不同是硬约束，由配置校验保证；默认 A=deepseek，B=qwen，C=glm，都在 DGX 上。
- 每个数字都必须带原文引语，并且这个数字字面出现在引语中。做不到就判失败，不靠模型自报置信度。
- 调用记录（模型、prompt 哈希、响应哈希）写进 `ciw.sqlite`，按 (prompt 哈希, 模型) 缓存，重跑不重复计费。
- 后端走 OpenAI 兼容接口；key 只从环境变量或 key 文件路径读取，不进日志、不进 release。测试使用 `FakeBackend`。
- 同一抽取器在同一身份下返回冲突值时进入待核，不采用数组首条。
- 私有DGX的系统DNS失败时，仅对已配置的HTTPS Tailscale主机使用本机`tailscale dns query`的唯一私网答案建立连接；保留原主机TLS/SNI验证，不改系统DNS、端点、模型或服务。调用元数据记录解析方式，不记录私网IP或凭据。
- EventItem的事件日期须有连续原文支持实际动作；发布日期、宣布已批准和历史数据回顾不能补作事件日期或新顶线事件。

### 论文补充

`sources.europepmc` 按未公布结果的核心 II/III 期登记号分页查询，保存 API 原件；只有摘要正文中的明确登记号可绑定研究。综述、方案、事后或亚组分析不自动作为主要结果。网络失败与尚未检索的编号保留在 coverage，离线重跑不会将其变成零结果。

`verify.publications` 复用同一 crosscheck，按明确登记臂投影为 `OutcomeResult(kind="publication")`。结果保留原始人群、单位、引用定位和核对状态；已明确的差值方向记录在 `Analysis`，不依赖组均值是否存在或舍入后相减是否相等。来源报告的组间差可以单独进入 B，未报告的组数值不补零，空的单组图不显示。登记与论文记录并存；audit 对论文样本回查原始摘要及引用数字。

论文组名优先匹配登记臂名及经核实的别名，矛盾的干预关联不改写；问题写入当前待核集合。来源明确的“X vs Y groups … LS mean difference”保留原句作为方向证据，不由数值正负号或舍入均值反推。只有摘要实际提供的分析N才进入对应结果。

## 6. 中国来源（采集收件箱）

CDE、NMPA、药企公告、公众号这四类，都需要真实浏览器，或者会遇到反爬。处理方式：

1. `tools/capture/*.mjs` 是 ego-browser 脚本，负责把列表页和详情页原件存进 `captures/<source>/`。每个原件旁边配一个 `.meta.json`，记录 url、fetched_at、query。
2. 流水线的 `sources.captures` 把收件箱原件入 CAS，然后按来源分派：
   - **CDE 登记**：确定性 HTML 解析，得到登记号、题目、申办方、期别、状态、首例入组日期、组别、终点。
   - **NMPA 批准**：确定性解析，得到批准文号、药品名、上市许可持有人、批准日期。
   - **公告和公众号文章**：正文文本交给 `verify.crosscheck` 抽取 `Event`。

运行时本身不依赖浏览器。没有采集到的来源，在 release 的 `coverage` 里写成“未采集”，不显示为“无数据”。

## 7. 门户（`ciw.render`）

- 每个门户是一个目录，包含 `index.html`、少量子页、一个共享 `data.js`（取自 release 的对应子集）、`app.js`、`style.css`，以及内置的 `echarts.min.js`。
- 所有中文标签、角色、单位、比较对、核对标签都由 release 给出；JS 只做排序、筛选、绘图和跳转。
- 本品统一用强调色，并在 A 矩阵、B 图、C 矩阵中置顶。

## 8. 工作台接入

| 工作台侧 | 内容 |
|---|---|
| `services/api/app/ciw_release_adapter.py` | `CiwReleaseEvidenceAdapter` 实现 `EvidencePackageAdapter`：<br>- `products / trial_designs / efficacy_results / safety_results` 从 release 映射；<br>- `source_hash` = `release_id`；<br>- 待核队列映射为 `quality_gates` |
| `evidence_design_manifest.py` | 新增 `adapter_type="ciw_release"` 分支 |
| `evidence_package_adapters.py` | 新增包配置 `crswnp_ciw_release`，并绑定到 `proj_mgk10_crswnp` |
| `main.py` | `GET /api/projects/{pid}/evidence-design/packages/{package_id}/reports/{report}/{path}`：托管 current release 的门户文件，带路径穿越防护 |
| 前端 `EvidenceDesignWorkspace.jsx` | 当前包带 `report_links` 时，显示“竞品全景 / 临床结果 / 设计先例”入口，在页内打开 |

CI 侧不依赖工作台代码；工作台只读 release 文件。HTML 不作为工作台 AI 的输入（工作台红线）。设计 studio 消费的是 release 的结构化 `trials[].design`。

## 9. 运行与测试

```bash
uv sync
uv run pytest                                     # 单元测试 + 小夹具，几十秒内完成
uv run ciw run indications/crswnp.yaml --workspace ~/Developer/ciw-workspaces/crswnp
uv run ciw status --workspace ...                 # 阶段、计数、待核数量、coverage
uv run ciw render --workspace ...                 # 只重渲染 current release
```
