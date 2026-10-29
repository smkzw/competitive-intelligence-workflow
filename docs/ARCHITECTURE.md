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
| 核对 | `ciw.verify.*` | 主抽取 + 异构原文核对补漏 + 确定性校验，写核对账本 | 改原件 |
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
| `Source` | `source_id`=来源类型、URL、内容哈希的稳定组合；`kind`(ctgov/europepmc/pubmed/cde/nmpa/company/wechat)；`url`、`title`、`publisher`、`published_at`、`fetched_at`、`sha256` |
| `Trial` | `trial_id`(NCT 或 CTR)；`ids`；`acronym`、`title`、`phase`、`status`；`dates`(start / primary_completion / completion / results_first_posted)；`sponsor`、`collaborators`、`countries`、`china`；`enrollment`；`design`；`arms[]`；`eligibility`；`outcomes_planned[]`；`product_ids[]`；`relevance` |
| `Arm` | `arm_id`、`label`、`type`(CT.gov armGroups.type)、`role`(experimental/active/placebo/none/other)、`interventions[]`、`description` |
| `Product` | `product_id`；`name_en`、`name_zh`、`codes[]`；`target`、`mechanism`、`modality`、`route`；`company`、`china_partner`；`innovative`、`inclusion_reason`；`is_own` |
| `OutcomeResult` | `trial_id`、`outcome_key`；`type`(PRIMARY/SECONDARY/…)；`title`、`description`、`timeframe`、`time{value,unit,weeks}`；`concept_id`、`domain`；`param_type`、`dispersion_type`、`unit`、`population`；`groups[{group_id,title,arm_id,role,n,value,spread,lower,upper}]`；`analyses[{group_ids,param_type,value,ci_pct,ci_lower,ci_upper,p_value,method}]`；`locator` |
| `SafetySummary` | `trial_id`、`timeframe`、`other_threshold`；`groups[{group_id,title,arm_id,role,serious{n,N},other{n,N},deaths{n,N}}]`；`terms[{term,organ_system,serious,stats[{group_id,n,N,events}]}]` |
| `Event` | 非结构化来源抽出的里程碑：`product_id`、`event_type`(approval/filing/topline/phase_start/licensing)、`region`、`date`、`detail`、`numbers[]`、`quote`、`status` |
| `Verification` | `fact_key`、`status`(registry/verified/needs_review/rejected；兼容历史dual_agreed/arbitrated)、`calls[{family,model,value,quote_ok}]` |

事实 ID 一律由自然键加内容哈希生成，同一原件重跑时 ID 不变。

## 5. 核对（`ciw.verify`）

```
原件文本 + 抽取 Schema → DeepSeek主抽取
    → cms-smk glm-5.3-flash读取原文与候选，核对、纠错、补漏
    → 确定性原文/数值/日期/业务字段校验
         ├─ 通过 → verified
         └─ 未确认/冲突/不支持 → needs_review
```

- 两个模型家族必须不同，角色仅extractor_a/verifier；不再分派Qwen或第三模型。核对者可见候选，不宣称盲审。确定性校验失败时仅向同一GLM回送错误条目纠正一次；正常条目不重跑，超次或仍失败保留待核，修复阶段不接受新增身份。
- 主抽取或核对调用失败记任务失败，不当作无数据。核对者未确认的A条目保留待核；B补漏和修正也须通过原文校验。
- 每个数字都必须带原文引语，并且这个数字字面出现在引语中。做不到就判失败，不靠模型自报置信度。
- 调用记录（模型、prompt 哈希、响应哈希）写进 `ciw.sqlite`，按 (prompt 哈希, 模型) 缓存，重跑不重复计费。
- 后端走 OpenAI 兼容接口；key 只从环境变量或 key 文件路径读取，不进日志、不进 release。测试使用 `FakeBackend`。
- 核对者在同一身份下返回冲突值时进入待核，不采用数组首条；A的冲突可由B依据原文修正。
- 私有DGX的系统DNS失败时，仅对已配置的HTTPS Tailscale主机使用本机`tailscale dns query`的唯一私网答案建立连接；保留原主机TLS/SNI验证，不改系统DNS、端点、模型或服务。调用元数据记录解析方式，不记录私网IP或凭据。
- EventItem的事件日期须有连续原文支持实际动作；发布日期、宣布已批准和历史数据回顾不能补作事件日期或新顶线事件。

### 论文补充

`sources.europepmc` 按未公布结果的核心 II/III 期登记号分页查询，保存 API 原件；只有摘要正文中的明确登记号可绑定研究。综述、方案、事后或亚组分析不自动作为主要结果。网络失败与尚未检索的编号保留在 coverage，离线重跑不会将其变成零结果。

`sources.pubmed`仅在Europe PMC失败时使用NLM正式ESearch/EFetch补查；分页完整性与PMID集合须匹配，原始XML保存入CAS，摘要按PMID对应的XPath定位。只有摘要字面登记号可绑定；综述、撤稿及更正类型不自动采纳为主要结果。成功的逐编号查询可复用，失败可续查；两个来源coverage分别保留，不把503清零或用检索元数据代替摘要。只有完成全套分页及PMID集合校验的来源进入候选；失败原件可保留用于诊断，但不被扫描采纳。刷新失败仍保留上一次成功的来源集合，不将失败的新片段混入。相同PMID按既有最新观测版本规则去重，同刻冲突保留待核；补生成C可携带已核对PubMed事实，不重查。无新依赖或第三核对角色。

`verify.publications`复用同一crosscheck。D18允许按论文原文明示分组投影为`OutcomeResult(kind="publication")`：能明确对应登记臂时保留arm_id；否则使用论文组别ID、arm_id为空，并保留研究关联。登记记录不改写，汇总不分摊。来源明确P值及比较符原样进入Analysis。结果保留原始人群、单位、引用定位和核对状态；已明确的差值方向记录在 `Analysis`，不依赖组均值是否存在或舍入后相减是否相等。来源报告的组间差可以单独进入 B，未报告的组数值不补零，空的单组图不显示。登记与论文记录并存；audit 对论文样本回查原始摘要及引用数字。

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

`analyze.design_excerpts`按配置主题索引原始设计文本，给出完整条款、来源ID、原字段与Unicode码点强调区间。渲染层只转义/强调这些区间；搜索与强调重叠、非BMP字符和HTML字符不会改变原文。研究摘要、详细描述、模型设计描述分别保存在既有Design对象，不新建本体或执行引擎。

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
uv run ciw render --workspace ...                 # 新呈现版本产生新release，保留旧文件
```


## 10. 自助研究（D19）

`research.py`用既有两角色提出并核查英文适应症检索词与终点/设计索引；该计划不是事实。CT.gov完整分页获取后，用原始DRUG/BIOLOGICAL干预建立来源绑定的候选和运行时YAML，创新属性未知、未核实名称属性留空，交给同一pipeline。已取登记对象传给流水线，不重复获取。论文和采集来源仍走原有核对规则。

工作台通过显式配置的CI源码位置启动同一个`ciw research`子进程，私有文件保存提交与执行状态。子进程独立于HTTP连接并用标准库文件锁串行化网页任务；接口重启不杀任务。查询与报告文件按真实身份隔离，幂等键防重复启动，失败/中断复用同一工作区。历史release/current不因失败被覆盖。这里不新增执行平台、科学签发或额外核对模型。

独立UC测试后的纠偏：登记结果优先使用测量class时间，其次结构化timeFrame，最后才从标题找时间，避免把条件人群的早期应答周数当成结果周数。多时点列表保持汇总语义。临床问题内部保留可切换frames，按原始定义/人群/描述区分上下文；仅消除机械测量措辞，不对未知临床定义作等价裁决。图、组值表和统计表共同消费当前frame；原文定义/人群折叠展开。历时线也使用同一上下文身份，原始全量观测保留。

共享合并分析仅在原文明确pooled/合并及多个已知研究ID、且组值或比较内容完全一致时在frame中合并展示，保留全部source_records与原始results。相同数值本身不构成同一队列。没有可确认方向/臂角色的来源统计另以原文组名、统计量、原值、CI/P及链接呈现，不借数组顺序分配试验组/对照组。

C终点定义直接投影原始PlannedOutcome.description并标记阈值；治疗时长主题使用专门的文字角色规则，不混入入排中的避孕/既往窗口、终点评估或每次给药间隔。给药与背景方案保留逐臂及研究描述原文，未知结构化字段不填造。样本量图和配表共享筛选，缺失原因不影响真实0。

候选属性低思考试验只在ProductAttrItem调用处复制现有DeepSeek后端，GLM与临床来源抽取不变；角色始终仅两种。请求reasoning_effort写入收据及模型缓存键，无显式思考配置时沿用原缓存键。低思考候选需真实来源质量与延迟复验，不凭配置宣称性能提高。

### D20 报告优先与资料复用

`research --report A|B|C`只生成所选门户；`--reuse-research`读取已完整取得的登记source集合与原YAML，不重新规划/检索，也不更新原件获取日期。完整分页结束才写research-context；旧工作区仅可由真实current与成功覆盖证明复用资格。失败前已取原件和模型缓存保留。

`pipeline.run`显式区分报告任务与已完成门户集合；B/C跳过A属性，A/C不启动B论文抽取。补生成时将已有门户与新门户投影至同一新release，保留同源已核对属性与论文事实。高级YAML `ciw run`默认仍完整生成A/B/C。

release记录`rendered_reports`，工作台由committed current与实际HTML存在共同决定入口；任务running/failed不使旧报告消失。新增类型沿用原任务/工作区，重复点击不重复执行，同时只运行一个补生成。原子切current在完整渲染之后。

工作台结果适配器同时投影数值分面的rows、comparisons与source_statistics；不重新计算、重新匹配或给无对照记录补对照。组值按result/group身份、来源分析按result/path身份区分，值状态和论文/登记来源不改标。相同来源记录重复引用去重，冲突不能first-wins；公开候选保留药物、研究和期别。读模型候选数是投影记录数，不冒充原始结果数。

多疾病登记的原始Trial/OutcomeResult保持不变，比较输入按来源组投影并保留每组范围；跨出所选人群的analyses只保留在原始观测。未分明组仍在原始观测详情展示源内组图和完整表，不做跨源归并。设计主题的metric_patterns只作检索展开，原patterns不被覆写，方法限定与完整上下文保留；入选/排除角色取自原文，不能将排除阈值改为入选阈值。弹窗关闭/替换时释放其图表与ResizeObserver。

release JSON及门户文件不覆盖已有不同字节；相同内容重复写保持原generated_at。呈现资产digest只决定报告版本，不参与LLM缓存失效；`ciw render`为新版呈现创建新release，不改历史快照。

D20续审修复：新站点开始写入前记录私有未完成标记，文件以临时文件原子替换；全部成功后移除标记，再允许切current。只有带对应未完成标记且从未成为current的候选可恢复半文件；所有已完成历史目录都禁止覆盖不同字节，不能仅保护当前指针。重复来源记录返回库中原元数据，避免内存返回值与CAS账本的获取日期冲突。

### 来源驱动的临床问题索引

检索前计划不作为实际终点覆盖证明。B（或启用模型的整套YAML运行）对尚未索引的真实结果标题＋完整定义按唯一内容去重，小批交给既有DeepSeek/GLM，核对分类与简短中文临床问题名。逐条校验描述身份、原标题和对应原文引语；失败/遗漏进入问题队列，不解释为没有临床结果。不能把组织学阈值因“count/eosinophil”字样直接排除为PD。原数值、单位、人群、时间、比较规则及来源均不改。

同题不同定义使用不同索引，<不合并为≤；新索引绑定精确标题和原始定义，不建立跨观察签发流程或大型医学本体。语义近似研究能否同框仍由原有比较逻辑决定，本次补索引不能充当正向横比已通过。

索引按来源描述/Schema/指令复用，非代码hash；C/A只复用已核对条目，不等待新的B模型调用。已采用临床概念随release保存，后续补生成无需阶段缓存也可重建同源临床视图，旧快照原样保留。

来源索引续审修复：检索前模型计划显式记为provisional，旧运行仅在持久计划的标题/字面词组完全对应时恢复该标记；用户维护字典不按ID或中文标签猜来源。来源精确标题/定义索引优先于泛化计划，计划排除可读取定义，避免有明确阈值仍显示“阈值未明确”。缓解/应答标签须有对应原文或明确阈值达标支持，连续标志物计数变化不能只凭两模型同意提升为缓解；标签重复阈值时须保留原比较符。该防错规则不宣称用确定性字符串证明全部临床语义，真实方法验收仍待。未运行的临床索引留下内部问题记录，不阻断不依赖它的A/C任务、不在首页增设解释横幅。

临床索引优先级修复：显式记录configured/research_plan/source_index来源；当前配置优先于已采用来源映射，来源映射优先于检索前计划。旧计划身份还须比较方向/域/来源定义，用户改过的字段不被降为provisional。不能用连续计数定义中顺带提及的另一个缓解终点来重命名当前计数；这不是判定一切连续组织学测量均非临床。

### C来源章节与原文条款

DesignTopicKind共用lookup/treatment_duration/eligibility_threshold/endpoint_definition。登记结果或终点描述不能进入入排阈值主题；终点定义不从既往入排经历推断。只迁移确切匹配已保存模型计划的旧运行主题，人工配置不猜改。给药期限按原始句/分句筛选，排除随访与末次给药后窗口；条件性再治疗的“必要时”保留，拆分显示时完整句在上下文中可读。原研究叙述/终点/入排均不改写。

D21普通DGX/glm临时替代CMS核对，DeepSeek主抽取不变；候选采用abb167a的配置与缓存合同。AB模型切换由推理网关负责，等待7200秒，不调用管理接口或重发健康请求。

D22：用户确认CMS恢复并要求切回，当前核对恢复cms-smk/glm-5.3-flash，DeepSeek抽取不变；实际无临床内容连通请求返回同名模型并正常结束。原D21运行结果和缓存不改标，已发健康请求不强制中断。

### 共同测量轴

既有临床family负责相关性，不能代替数值条件。normalize.comparison_axes按来源版本、研究及唯一测量定义建立局部上下文；verify.comparison_axes仅复用原有两角色核对明确分析集/基线/期别/估计策略，保存逐成员原字段引文及人群标签。确定性守卫保留统计形式、数值方向、阈值、单位维度和期别差异。精确单位别名不换算数值；未知分析集不由可用数据或N猜测。

analyze.comparison_axes把已核对的测量轴用于同一临床问题的数值图及历时图，时间点/区间仍精确分面，各研究/序列/人群保持独立。原值、N、来源、原单位及原定义完整留在对应表与详情，不进行合并估计、排名或跨试验相减。模型内容键按来源上下文/Schema/指令，成功任务及待核项可恢复，原source-index与family缓存不失效；A/C只复用已保存映射。发布物携带comparison_axes，旧版缺省兼容。

### 单一写入与增量问题目录

run、research和render共用工作区原生文件锁，同一对象/线程可重入，其他进程/线程在写阶段前明确返回忙碌；进程退出由操作系统释放，旧锁文件不代表仍有任务。取消等待本身不证明执行已结束，不能重启同一作业。

family仅为新来源指标归组，已有有效来源哈希与引文的成员不因新增来源而被重新拆分。新增成员可以沿用已核对主题标签，并经同一来源守卫加入唯一对应主题；同目录的失败批仍复用原抽取和成功核对缓存。比较轴保留历史任务记录，同时列出active_task_ids，只按当前输入任务报告状态；待核任务记reviewed，不冒充已采纳。模型只复制context_标识，来源ID保存在绑定清单，不混用科学身份。

### C来源条款与主题横比

analyze.design_excerpts共享原字段清单和当前项目主题ID。简短明确的原文确定性投影；verify.design_clauses仅整理复杂列表、叙述及多疾病候选，复用原crosscheck及内容缓存，不增加第三模型。返回短原文、逻辑父条件、明确队列、入排角色及连续原文引文，逐字段校验；源Trial不改写。阶段缓存按原字段、Schema和指令键入，后续A/B读取接受项，网络失败不发布新current。未取得可核条款的主题不冒充已整理，完整入排/研究描述仍在详情。C.topic_catalog及row.design_excerpts共同驱动点选主题表，渲染层只投影，不推断阈值或疾病关系。

共享源字段/阈值/角色/列表上下文位于normalize.design，避免verify逆向依赖analyze。列表父句在Key等入排标题、同级同类新列表项处结束；连续原文及原角色始终保留。修复校验器时，原模型提示与成功答复内容键不随代码变化；仅尚不符合当前守卫的条目按具体错误补核。

模型传输仅重试已返回的HTTP429：普通类别最多6次/180秒，明确并发、上下文池容量、换模或繁忙时最多16次/900秒，且服从更短原超时。等待满足Retry-After与5/10/20/40/60秒退避下限。额度信号优先终止；401/503/网络超时及已受理推理不重发。错误流仅消费一次并关闭，只留类别/参数枚举和退让元数据，失败不进成功缓存；不改模型、鉴权或服务配置。

列表父句与唯一子句分处原文时，分别保存连续字面定位和原核对者的子句quote；只有解析器证明同一已引导列表、无同级/分段终止且匹配唯一时才绑定。完整上下文保留中间的其他分支，不拼接引文、不把其他分支采纳为当前子句。重复、跨入排、跨同级项或改写条件继续待核。

429等错误回执仅从OpenAI error或网关detail结构保留运行类别，不保存原始错误消息；类别是按服务错误描述归类，不能替代引擎容量实测。模型目录GET与实际推理接纳分开记录，不从目录200推导能生成报告。

### C中文阅读投影

`verify/design_labels`只消费已保留条款的原始text、条件、队列和时点，既有DeepSeek抽取与GLM核对后形成独立reading字段；原text/source_quote/context与事实值不改。渲染直接投影reading并就地展开原文，不做翻译或医学推断。阅读缓存独立按来源内容、Schema与指令键入，同原子跨主题复用，并复用既有最多12项的批处理，32K为短原子的分批目标，单个长上下文保持完整并独立发送，逐原子账本保留真实来源；既有design-clause任务及缓存不失效。A/B仅复用已有阅读结果，不新增C调用。未核条目保留原文并在内部缺口中记录。

设计入排的依赖句由同源逐字引文定位，保留based-on/provided等连接词后的完整适用依据，不从其他同值的独立条目借条件。旧缓存项仍按当前守卫检查，未符合者不投影；原任务/schema/指令不变，仅必要的GLM修复请求补全条件。阅读层修复只支持已证明的N-hour、N个月、A1c(HbA1c)源内别名及同值单位展开缩写；独立数值、方向及时间保留。已保存B项重检必须有两家族、真实最终核对响应ID、完整item及当前源字段对应，复用既有_review_binding，不手写或重组模型输出。
共享图表的HTML tooltip在实际图卡/视口范围内换行，保留完整研究身份、原值/单位/N，不靠confine处理超长单行，不缩字或裁内容。

NMPA采集收件箱保留首次证书及按内容与观察记录另存的后续版本；当前摄取按实际带时区observed_at选择最近完整原件，不按文件名/采用顺序覆盖。相同内容的当次核查保存在独立目录列表，A→B→A再观察仍产生新的当前版本，旧原件不覆写；同时间内容冲突进入问题记录。快速列表查询用微秒文件名且排他创建，避免秒级同名覆盖。CLI对查询或详情失败返回非零，公开详情超时只记录标题/必需字段数量、验证码/网络/遮罩状态，不采集凭据或整页私有上下文；不因暂未复现超时而改写popup/选择器。

无新模型调用的重建从现有verifications及llm_cache读取精确source_id/task对应verified条目，重验schema、当前source quote与最后相关B原响应；同批别的身份repair不撤销正常条目，后续同身份修订也不能倒退采用旧B。产品和研究绑定仍通过当前投影函数重验。只读复用不重写原核对记录、不调模型；未核/不完整/同键冲突不采纳，部分失配保留其余合法条目并记来源partial。完整定义及并列临床条件的源摘录不得截成仅数值，数值比较词中的or/and不误作分支；原文展示只做字面包含去重和转义，独立时间字段保留。

嵌套列表＋定义来源采用明确的同一Schema表示约定：完整连续分支定义放text，真实上位父句放condition，不拼接其他同级分支。仅原字段确有这类结构时附加此抽取指引，按自然指令内容形成任务键；其他平坦来源任务保持原键，不按代码hash失效。中文检查另拦截已观察的negative-perfect既往史被改成“签署ICF后同等时长”的相反时间方向；这是有界语言形式守卫，原文及GLM核对和独立来源复验继续保留，不宣称通用时序理解已解决。

列表父句定位只允许省略行首空白或无序项目符号，医学词句、编号、队列标签均不视为装饰。condition_source仍精确指向原文切片，完整分支上下文不变。仅同源同任务、因来源定位规则误拒的needs_review项可用原始双家族调用及真实最终B响应逐项重检；保留原calls和先前状态/原因，不改指令键、不新发来源模型调用、不扩展到缺B或其他待核原因。
