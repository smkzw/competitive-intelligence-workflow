# Conference Output: ci-1007-publication-atoms-review-v1 - evidence_single_object

## Output

### 1. Bounded verdict

**REVISE — 数字与原文转录核对通过，但冻结候选的部分科学语境字段需要修订。**

最高影响问题：**OLYMPIA LTE 的 25 条 `ResearchResultContext` 将列标题同时用作时间点和单位。** 总体列的时间点被写为 `n (%)`，暴露调整率列的时间点被写为 `Exposure time adjusted incidence rate (/100 person year) a`；分时段列又将时间窗、N 和单位合并写入 `source_unit`。原文引用完整，不能据此声称这些结构化字段也正确。

另一个实质缺口：**dupilumab 主要终点候选没有关联原文关于 rescue/prohibited medication、缺失值与停药后数据的完整分析规则。**

本结论仅挑战两篇原件与冻结候选。不是临床、监管、发布、全来源覆盖或最终接受结论；Codex 保留最终 authority。没有发现所选 **66 个数值单元格的转录错误或错列**。

### 2. 输入完整性、实际检查与覆盖

#### 冻结输入

实际读取并计算 SHA-256：

| 输入 | 字节数 | 实测 SHA-256 |
|---|---:|---|
| `candidate-v2.json` | 1,137,294 | `a33c450adb06bd397102d88f3367d53630afd01e7290d3e8cf081a3755724ae4` |
| `review-material-v2.json` | 444,931 | `f600357a7f1f8730a51b4a70ef5f97c63f4d777ef4e81baa40cad4d3f543f71d` |
| PMID37142763 原生 XML | 172,525 | `2bb91f3c0ec34d8aebf9a6c4bf879d866cc66d214f4fc5e6e81a59ec6992dd71` |
| PMID41405008 原生 XML | 123,886 | `5354b1ad692e3127692bc7d11a131558fa12f41f72d18001f37b034a1fe51cd0` |

四个摘要均与上下文声明一致。独立递归展开 review transport 的引用后，**整个 `candidate` 对象与完整冻结 proposal 相等**，不是仅比较事实数或部分字段。100 个唯一引用对象对应 1,040 次引用。

原生 XML 的 article metadata 也分别匹配：

- PMID37142763 / PMC10202800 / DOI `10.1038/s41591-023-02320-9`。
- PMID41405008 / PMC13308661 / DOI `10.1111/jdv.70266`。

#### 事实覆盖

| 来源 | Definition | Narrative | Population | Primary endpoint result | Safety total | 合计 |
|---|---:|---:|---:|---:|---:|---:|
| PMID37142763 | 13 | 2 | 8 | 8 | 16 | 47 |
| PMID41405008 | 9 | 2 | 9 | 0 | 42 | 62 |
| **合计** | **22** | **4** | **17** | **8** | **58** | **109** |

实际执行：

- **109/109** facts 经现有 `ResearchFact` schema 验证成功；fact IDs 无重复。
- **109/109** facts 的 `original_text` 和 `raw_value` 均与生产 `extract_locator_quote` 从对应原件重新提取的文本相等。
- **100/100** 唯一 clause references 的原文引用重放一致。
- **66/66** scoped 数值单元格核对了原生值、行标签与列绑定，最终无差异。
- 三个 nemolizumab 严重程度 EAIR 空白格均确认为无文本；生产提取器拒绝以空白节点提供引用，未被补零。
- 41 条 facts 有 `ResearchResultContext`；definition/narrative/population 三类中 **0 条**带该对象。
- 所选数值格中 52 个含复合表达且 `normalized_value=null`，没有将其隐式重算为比例、差值或其他单值。

读取范围包括：

- 初始 context 与 Codex plan。
- 两个完整 JSON，经内存解析逐条核对，不以工具预览截断代替完整读取。
- dupilumab 原生 Table 2、Table 3 的表头、行、脚注；主要终点定义、修订、分析人群、主要结果、安全性正文、统计方法与相关图注。
- nemolizumab 原生 Table 2 全表及脚注；Table 1 所选 population headers；试验、剂量、队列、主要安全性终点、分析方法、处置/暴露、安全性正文、摘要与相关图注。
- 上下文明确授权的三份生产合同文件中相关类和引用提取器实现。

工具：只读 `read` 与内存解析/确定性验证；生产重放通过 `.venv/bin/python -B -c`，设置 `PYTHONDONTWRITEBYTECODE=1`，退出码 0。首次空白格检查遗漏 `EvidenceLocator.document_role`，只产生 reviewer 构造错误；补齐后仅重试该失败步骤，确认原生空白拒绝。初版行绑定检查错误地要求 dupilumab 安全性 facts 必须含 `row_label_path`；检查改为接受其实际使用的精确 continuation 后，66 格全部通过。这两项不是候选缺陷。

没有读取 writer report、私人推理或早期意见；没有网络、browser、git、DB、安装、临时脚本、源文件或 runner report 写入；没有接受/current 写入。运行身份按本会话声明为 Pi / openai-codex / gpt-6.1-sol；**独立运行回执与 thinking-effort attestation 未在本轮验证，应由 runner/Codex 核对**。

### 3. 可复现定位约定

以下缩写展开为精确原件和 XPath；集合表达用于明确受影响事实，不是模糊类别定位。

**D 原件：**

`.artifacts/1007-publication-source-dates-v1/source-library/evidence/raw/sha256/2b/2bb91f3c0ec34d8aebf9a6c4bf879d866cc66d214f4fc5e6e81a59ec6992dd71.bin`

- `D2 = /article/body[1]/sec[2]/sec[3]/p[2]/table-wrap[1]/table[1]`
- `D3 = /article/body[1]/sec[2]/sec[8]/p[1]/table-wrap[1]/table[1]`
- D fact ID 为 `pubfact:PMC10202800:` 加对应 XPath。

**N 原件：**

`.artifacts/1007-publication-source-dates-v1/source-library/evidence/raw/sha256/53/5354b1ad692e3127692bc7d11a131558fa12f41f72d18001f37b034a1fe51cd0.bin`

- `N2 = /article/body[1]/sec[3]/sec[2]/sec[1]/table-wrap[1]/table[1]`
- N fact ID 为 `pubfact:PMC13308661:` 加对应 XPath。

### 4. 优先问题与具体修复

#### P1-A — LTE 的时间、单位与复合值类型混入列标题

**证据／受影响 facts**

25 条 result contexts：

`pubfact:PMC13308661:{N2}/tbody[1]/tr[r]/td[c]`

其中：

- `r ∈ {1,5,6,7,10}`
- `c ∈ {2,3,4,5,6}`

代表事实：

`pubfact:PMC13308661:/article/body[1]/sec[3]/sec[2]/sec[1]/table-wrap[1]/table[1]/tbody[1]/tr[1]/td[3]`

其值为 `197.49`，`normalized_value="197.49"`，但：

- `timepoint` 是 `Exposure time adjusted incidence rate (/100 person year) a`。
- `source_unit` 也是同一完整标题。
- `metric="unresolved"`。

总体 Any TEAE 的 `452 (89)` 则将 `timepoint` 写为 `n (%)`。分时段 Any TEAE 的 `292 (71)` 将 `source_unit` 写为 `12–<24 months (N = 409) n (%)`。

这些值均与原文一致；错误在字段角色，不在转录。

原生表头明确区分：

- `N2/thead[1]/tr[2]/th[1]`：`N = 508`，覆盖总体人数/比例和 EAIR 两列。
- `N2/thead[1]/tr[2]/th[2]`：`By the time of occurrence of event`，覆盖后三列。
- 表 caption：`Summary of treatment‐emergent adverse events during treatment period (safety population).`

原生 EAIR 脚注位于：

`/article/body[1]/sec[3]/sec[2]/sec[1]/table-wrap[1]/table-wrap-foot[1]/fn[3]/p[1]`

> “Exposure‐adjusted incidence rate is calculated as the number of patients having a specific event divided by total exposure time at risk, multiplied by 100.”

> “The total exposure time at risk is calculated as person‐years up until the first event or end of treatment period … This was calculated post hoc.”

另外，上述 25 条中的 **18 个复合 count/percent 格**被标为 `raw_value_type="single_source_token"`，而 dupilumab 同类格使用 `composite_count_and_percent`。例如 `452 (89)`、`2 (<1)`、`1 (<1) b`。这至少造成跨论文类型描述不一致；是否被下游解释为 scalar，本轮没有执行消费者，不能声称已证明误投影。

**推断／风险**

`197.49` 是受事件特异性 at-risk exposure 定义约束的患者发生率，不是百分比、事件数或 `452/1002.66×100` 的自行计算结果。单位标题不是时间点。总体治疗期安全性也不能由文章标题强制改写为固定 “week 100”。

**建议**

保留原始引用和值，仅修订既有语境字段：

1. 原始完整标题留在引用/`group_title` 中。
2. 总体人数与 EAIR 的时间语境绑定到来源定义的 treatment period；分时段列分别表达 `<12 months`、`12–<24 months`、`≥24 months`。
3. 单位与时间、N 分开；明确 EAIR 为 patients per 100 person-years at risk，保留 post hoc 与 first-event censoring 脚注。
4. 复合 count/percent 格使用与另一篇一致的复合类型描述；不得把 `<1` 变成 0 或精确百分比。
5. `metric` 未解决前不要把已规范化的率或裸零视作可比较数值。若本阶段仅允许原文 holding facts，可采用已存在的保守做法：暂不赋予不准确的 `result_context`，而非新增模型。

这是修订结构化科学身份，不要求计算或自动拆格。引用已完整保存，不应误报为“EAIR 脚注缺失”。

#### P1-B — dupilumab 主要终点缺少完整 intercurrent-event / missingness 关联

**受影响 facts**

全部 8 个主要终点格：

- `pubfact:PMC10202800:{D2}/tbody[1]/tr[2]/td[c]`，`c ∈ {2,3,4,5}`。
- `pubfact:PMC10202800:{D2}/tbody[1]/tr[3]/td[c]`，`c ∈ {6,7,8,9}`。

以及原文叙述 fact：

`pubfact:PMC10202800:/article/body[1]/sec[2]/sec[3]/p[2]`

候选保留了该结果段中的 missing-data 数量与 non-responder 描述，但冻结候选及 100 个引用对象中，没有以下关键统计段：

`/article/body[1]/sec[4]/sec[8]/p[2]`

其原文：

> “Patients with missing data at the timepoint or who used rescue/prohibited medications/procedures before the timepoint were considered non-responders. Data collected after discontinuation were included in the analysis.”

同段还规定 binary response 的 Cochran–Mantel–Haenszel 分析及调整因素。

**推断／风险**

只保留“缺失者算 non-responder”和 FAS/ITT 描述，没有完整说明哪些患者被计为 responder；使用 rescue/prohibited interventions 的处理也影响该主要终点。停药不等于从分析删除。这不是转录错，但属于本轮要求挑战的 endpoint/population/missingness 语境缺口。

**建议**

将该精确原文段追加为 8 条主要终点格的 clause continuation，并注明：

- timepoint 缺失或此前使用 rescue/prohibited medication/procedure → non-responder。
- 纳入停药后采集的数据。
- 表中差异为来源声明的 Mantel–Haenszel estimator，不是简单相减。

不要把同段关于 continuous outcomes 的 WOCF/MI 规则错误套到这四个 binary arm cells；也不要将 supplemental/sensitivity analysis 与 Table 2 主分析合并。

#### P2-C — severe 安全性覆盖存在未明示的遗漏，不应当作“无可引用数据”

**证据**

nemolizumab 已提取 `N2/tbody[1]/tr[4]` 的 Severe 分层，且正确记录该行 EAIR 空白。但原生 **`tr[8]` 是另一行 `Any severe TEAE`**，其格为：

| 单元格 | 原文 |
|---|---|
| `N2/tbody[1]/tr[8]/td[2]` | `53 (10)` |
| `N2/tbody[1]/tr[8]/td[3]` | **`5.60`** |
| `N2/tbody[1]/tr[8]/td[4]` | `30 (6)` |
| `N2/tbody[1]/tr[8]/td[5]` | `23 (6)` |
| `N2/tbody[1]/tr[8]/td[6]` | `5 (2)` |

这些格未生成 facts。已提取的重度 facts 是：

`pubfact:PMC13308661:{N2}/tbody[1]/tr[4]/td[c]`，`c ∈ {2,4,5,6}`。

dupilumab 的原生 `D3/tbody[1]/tr[2]` 也有 `Patients with any severe adverse eventa`，四组依次为 `5 (6.7)`、`3 (4.0)`、`1 (1.2)`、`2 (2.6)`，未提取。候选 19 个 missing/conflicting scopes 没有专门明示这两行的排除。

**不确定性／范围**

冻结任务不是全文完整提取；不能仅凭未提取就要求扩大到全部安全性表。但本轮明确包括 severity，且候选已收 nemolizumab severity 分层，因此 **5.60 的遗漏需要明确处置**，不能由 tr4 空白推出 severe EAIR 不存在。

**建议与 Codex 决策点**

- 若 severe total 属于本次指定合计：从原生 tr8 提取 `5.60`，保留其 EAIR 身份；相同 n/% 不要成为重复计数。
- 若 severe total 明确不在本次提取范围：增加精确排除说明，指出 tr8 有来源数据但未提取。
- 同样明确 dupilumab severe 行是否排除，不得与 `treatment-emergent SAE` 行等同。

安全暂行路径：仍保持该严重程度分层 EAIR 空白；**不得从 tr8 借值填 tr4，也不得填 0**。

#### P2-D — 一个 missing-scope 说明误称脚注对象

受影响 scope：`dup-discontinuation-and-relatedness-limits`。

其描述使用“重度事件脚注”措辞，却指向并引用：

`/article/body[1]/sec[2]/sec[8]/p[1]/table-wrap[1]/table-wrap-foot[1]/p[3]`

> “bIn PRIME, one event each of Hodgkin’s disease and neurodermatitis … In PRIME2, one event of urticaria.”

原生表中 **b 标记挂在 TEAE leading to treatment discontinuation 行**。Severe 行挂的是 **a**，位于同一 foot 的 `p[2]`：

> “aConsidered unrelated to the study intervention except for two events of sepsis and mesenteritis, experienced by one placebo-treated patient in PRIME.”

**建议**

修正文案为停药行脚注 b；如果要保留 severe-relatedness 描述，另关联脚注 a。无需改动数字，也不能由这些限定语生成未报告的 treatment-related TEAE 总计。

### 5. 已核对正确、应继续保持的边界

- **主要终点分配正确。** PRIME week 24 为 `14 (18.4)` / `45 (60.0)`；PRIME2 week 12 为 `18 (22.0)` / `29 (37.2)`。另一试验在同一行的非主要格未误提为 primary。
- **contrast/P 不是 arm observations。** `42.7 (27.8 to 57.7)`、`16.8 (2.3 to 31.2)` 及对应带 hierarchy rank 的 P 格均保留复合原文、无 arm `result_context`。不应将前者改成未调整的百分比相减结果。
- **两种分析人群 N 未合并。** D2 疗效列为 76/75/82/78；D3 安全性列为 75/75/82/77，符合各自表头。安全性按实际收到的干预分析，报告 24 周治疗期，不能延伸到 12 周 post-treatment follow-up。
- **study/cohort 身份保守。** PRIME/PRIME2 使用来源作用域 entity labels，没有凭两个并列 NCT 分配登记号。LTE 安全性没有归到 OLYMPIA 1/2 导入试验，NCT03181503 的 phase 2b/结果 phase 2a wording 差异保持未解决。
- **LTE 时间窗不是队列。** 表头 N=508/409/286 是事件发生时间窗，不是 continuous/naïve/re-treatment 队列 307/174/27。安全性 N=508 不得扣除 27；处置图注明确再治疗组只纳入 safety results。表未提供按队列分列的安全性结果。
- **relatedness 有来源限定。** 原文脚注把 relationship 缺失也列入 drug-related TEAE；候选 related-TEAE note 已保留该点。不能将相关合计称为全部均有肯定因果判断。
- **死亡 period 未合并。** LTE 表的 `1 (<1) b` 是治疗期死亡，心肌梗死，判为与治疗/方案操作无关；正文另报 follow-up 期终末期肾病死亡并注明 data not shown。不能把两例合入该表，不能将后两个时间窗的裸零扩展成全部随访零死亡。
- **停药对象未合并。** dupilumab 是 TEAE 导致 treatment discontinuation；LTE 是 TEAE 导致 trial discontinuation。LTE 正文 AE 51/508 与表内 TEAE 44 (9) 均保留，原件没有给出可安全采用的差额解释，不应将 7 例归因于特定 period/cohort。
- **展示精度保留。** 摘要 `197.5` 与表 `197.49`；正文 related serious rate `0.7` 与表 `0.70`，未互换。
- **缺失不是零。** 三个 severity EAIR 空白格未提取；图像型表/处置图没有伪造单元格。显式零仅限所属原生格。
- **没有由题名或 epub 日推断数据可及性。** 本轮也未验证更广来源可及性或版本公开历史。

### 6. Codex 的 bounded questions 与安全暂行路径

1. **本阶段目标是原文 holding facts，还是可进入数值框架的已解决 observations？**  
   原始引用可核对；25 个 LTE result contexts 的字段角色仍不准确。推荐在现有 proposal 内纠正，或保持 evidence-only 而不赋予这些 contexts；本轮未证明任何下游 gate 会自动阻止误用。

2. **severe total 是否属于指定合计？**  
   需明确处理 LTE `Any severe TEAE` 的 EAIR `5.60`，以及 dupilumab severe 行。若不提取，记录“有原生数据、范围外排除”，而不是让空白 severity 格造成没有 severe-rate 数据的印象。

上述决策**不阻碍本轮 REVISE 结论**。无需扩展检索、registry 联接、医学签署或全工作流审阅。

建议闭包：修正 P1-A、补充 P1-B 的精确 clause、明确 P2-C 范围并纠正 P2-D 文案；由 Codex 对修订后新摘要核对相应 facts。未受影响的原始数字、引用、零/缺失、登记未分配与 source-scoped 身份应保持不变。
