# Conference Output: ci-1007-publication-atoms-review-v1 - evidence_single_object round2
## Output

### Verdict

**REVISE。P1-A、P1-B、P2-D 的主要修正通过；P2-C 新增数值正确，但五条 LTE severe facts 的结构化行路径仍指向 Any TEAE，九条新增 severe facts 的中文标签/说明也仍描述 Any TEAE。**

这是 holding source facts 内部的证据身份矛盾，不涉及要求开放 numerical frame、current 或 release。未修改任何文件，未静默修复。

| 原问题 | 本轮闭包结果 |
|---|---|
| P1-A：LTE group/time/unit/composite/EAIR 身份 | 原25条 context 的指定字段修正通过；新增5条 severe context 的这些字段也正确，但其 clause scope 行路径另有错误 |
| P1-B：主要终点 ICE/missingness | **通过**，8个主要终点格＋1个 narrative 均附完整精确原文 |
| P2-C：severe totals 与空白 severity-stratum EAIR | 9个新增数值及原件引用通过；**行路径、标签/说明尚未闭合** |
| P2-D：dupilumab 脚注 a/b | **通过**，原说明已纠正，4条新增 severe facts 均附脚注 a |

### 1. 实际执行的完整性检查

完整解析 v2/v3 JSON，没有以截断预览代替完整读取。执行一次 `.venv/bin/python -B -c` grouped verification，设置 `PYTHONDONTWRITEBYTECODE=1`，退出码 **0**；随后对发现的 severe 行身份矛盾做只读定点核对，没有重跑广泛测试。

#### 冻结摘要与原件

- v3：1,268,401 bytes，实测 SHA-256  
  `74415ca2ecfcecc994cdab0e99885304b3d89b81e0c1162125f39858e8ced151`，匹配指定摘要。
- v2：1,137,294 bytes，实测 SHA-256  
  `a33c450adb06bd397102d88f3367d53630afd01e7290d3e8cf081a3755724ae4`，匹配指定摘要。
- `source_set` 与 v2 **完全相等**。
- PMID37142763 原件：172,525 bytes，实测摘要  
  `2bb91f3c0ec34d8aebf9a6c4bf879d866cc66d214f4fc5e6e81a59ec6992dd71`。
- PMID41405008 原件：123,886 bytes，实测摘要  
  `5354b1ad692e3127692bc7d11a131558fa12f41f72d18001f37b034a1fe51cd0`。

#### 检查计数

| 检查 | 实际结果 |
|---|---:|
| 全部 facts 经生产 `ResearchFact` 及嵌套 context schema 验证 | 118/118 通过 |
| 全部 fact `raw_value`、`original_text` 与生产原件提取器重放一致 | 118/118 通过 |
| Clause context 引用重放 | 1,149 次引用；按 source/path/quote 去重后84条，84/84通过 |
| 原109条的 raw value、locator、source ID、disclosure state、original text 保持不变 | 109/109通过 |
| 原 facts 删除 | 0 |
| 新增格原始值核对 | 9/9通过 |
| 新增格实际行引用、endpoint 与列标题引用核对 | 9/9通过 |
| LTE 原25＋新5条的 group/time/unit/composite/metric 字段 | 30/30通过 |
| 上述30条附治疗期定义 | 30/30通过 |
| 上述30条中6条 EAIR 附 at-risk/first-event/post hoc 脚注，且 normalized value 为 null | 6/6通过 |
| 8个主要终点格＋1个 narrative 附完整 ICE 原段 | 9/9通过 |
| 新4条 dupilumab severe facts 附治疗期脚注及 severe 脚注 a | 4/4通过 |
| 三个 severity EAIR 空白格仍未生成数值 fact；原件提取器拒绝空白引用 | 3/3通过 |
| 新5条 LTE severe facts 的 `scientific_scope.row_label_path` 与实际数值行一致 | **0/5通过** |

Grouped check 对实际引用和 endpoint 的通过，**不意味着所有自由格式 `scientific_scope` 字段语义正确**。最后一项错误来自随后对存储行路径的定点关系核对。

v3 实际事实构成为：

| 来源 | Definition | Narrative | Population | Primary result | Safety total | 合计 |
|---|---:|---:|---:|---:|---:|---:|
| PMID37142763 | 13 | 2 | 8 | 8 | 20 | **51** |
| PMID41405008 | 9 | 2 | 9 | 0 | 47 | **67** |
| 合计 | 22 | 4 | 17 | 8 | 67 | **118** |

没有读取 writer report、owner helper 或私人推理；没有网络/browser/git/DB/递归 dispatch/cleanup，没有 code/docs/source/accepted/current 或 runner report 写入。

### 2. 仍需修订的具体问题

#### R1 — 五条 LTE severe facts 的行路径指向错误统计对象

**优先级：P1；P2-C 未闭合。**

受影响的精确 fact IDs：

```text
pubfact:PMC13308661:/article/body[1]/sec[3]/sec[2]/sec[1]/table-wrap[1]/table[1]/tbody[1]/tr[8]/td[2]
pubfact:PMC13308661:/article/body[1]/sec[3]/sec[2]/sec[1]/table-wrap[1]/table[1]/tbody[1]/tr[8]/td[3]
pubfact:PMC13308661:/article/body[1]/sec[3]/sec[2]/sec[1]/table-wrap[1]/table[1]/tbody[1]/tr[8]/td[4]
pubfact:PMC13308661:/article/body[1]/sec[3]/sec[2]/sec[1]/table-wrap[1]/table[1]/tbody[1]/tr[8]/td[5]
pubfact:PMC13308661:/article/body[1]/sec[3]/sec[2]/sec[1]/table-wrap[1]/table[1]/tbody[1]/tr[8]/td[6]
```

原件：

`.artifacts/1007-publication-source-dates-v1/source-library/evidence/raw/sha256/53/5354b1ad692e3127692bc7d11a131558fa12f41f72d18001f37b034a1fe51cd0.bin`

**证据：**

五条的 `source_clause_context.scientific_scope.row_label_path` 均为：

```text
/article/body[1]/sec[3]/sec[2]/sec[1]/table-wrap[1]/table[1]/tbody[1]/tr[1]/td[1]
```

该原生格是：

> `Any TEAE`

但实际数值位于 tr8，其行标签是：

```text
/article/body[1]/sec[3]/sec[2]/sec[1]/table-wrap[1]/table[1]/tbody[1]/tr[8]/td[1]
```

> `Any severe TEAE`

五条的 `result_context.endpoint` 和实际 row continuation 已正确写为 tr8 / `Any severe TEAE`；因此是**同一 fact 内的指针矛盾**。例如 `5.60` 自身引用正确，scope 行路径却指向总体 Any TEAE，而不是 severe 合计。

**风险／推断：**

依赖该行路径读取 endpoint 的消费者可能将 severe 合计解释成 Any TEAE。本轮未运行消费者，不能声称已经发生误投影；源事实内部矛盾本身已足以阻止 bounded closure。

**具体修复：**

只将上述五条的 `scientific_scope.row_label_path` 改为 **tr8/td1**。不要改 raw value、cell locator、正确 row continuation、EAIR 脚注或既有 severity-stratum tr4。

#### R2 — 九条新增 severe facts 的中文标签/说明仍丢失 severe 限定

**优先级：P2；属于新增事实身份闭包。**

受影响：

- R1 所列五条 LTE facts。
- 以下四条 dupilumab facts：

```text
pubfact:PMC10202800:/article/body[1]/sec[2]/sec[8]/p[1]/table-wrap[1]/table[1]/tbody[1]/tr[2]/td[2]
pubfact:PMC10202800:/article/body[1]/sec[2]/sec[8]/p[1]/table-wrap[1]/table[1]/tbody[1]/tr[2]/td[3]
pubfact:PMC10202800:/article/body[1]/sec[2]/sec[8]/p[1]/table-wrap[1]/table[1]/tbody[1]/tr[2]/td[4]
pubfact:PMC10202800:/article/body[1]/sec[2]/sec[8]/p[1]/table-wrap[1]/table[1]/tbody[1]/tr[2]/td[5]
```

dupilumab 原件：

`.artifacts/1007-publication-source-dates-v1/source-library/evidence/raw/sha256/2b/2bb91f3c0ec34d8aebf9a6c4bf879d866cc66d214f4fc5e6e81a59ec6992dd71.bin`

**证据：**

九条均有：

```text
label_zh = "任何 TEAE"
```

四条 dupilumab 的说明为：

> `至少一件 TEAE 的人数和百分数。`

五条 LTE 的说明为：

> `总体治疗期至少一件 TEAE。时间列使用各自表头中的 N。`

原生行却分别为：

- dupilumab：`Patients with any severe adverse eventa`
- LTE：`Any severe TEAE`

新增 facts 的 `field_id`、endpoint 与 severity-vs-seriousness 提示已保留 severe；中文说明没有保留该限制，且 LTE 的说明未区别总体率列与事件时间窗列。

**具体修复：**

- dupilumab：标签可用“任何重度不良事件”；说明为“发生任何重度不良事件的患者人数和原文百分数；重度不等于严重（SAE）”。
- LTE：标签可用“任何重度 TEAE”；n(%) 格说明保留相应总体治疗期或事件发生时间窗；`5.60` 格明确为源报告的 severe TEAE EAIR、单位 `/100 person year`，而非人数或百分比。
- 保留原文英文 endpoint、所有数字和既有严重性/严重程度区分，不生成新的医学判断。

#### R3 — `coverage_note_zh` 仍报告 v2 数量

**优先级：P2；冻结候选自身的覆盖说明，不是额外文档任务。**

`candidate-v3.json` 顶层 `coverage_note_zh` 仍称：

- dupilumab 共47条、`safety_total 16`。
- nemolizumab 共62条、`safety_total 42`。

实际分别是 **51条/20条**与 **67条/47条**，合计118条。

**具体修复：**

更新该字段的四个数量，说明本轮已加入两篇 severe totals，并继续注明 tr4 severity-stratum EAIR 空白未补值。原有非全文覆盖、AESI/PT 分项未逐格提取等范围限制应保留。

### 3. 已闭合的科学语境修正

#### P1-A：holding LTE contexts

原25条及新5条均已：

- 将 `group_id` 指向原生药物组表头，`group_title` / `arm` 为 **Nemolizumab Q4W**，不再把统计列作为治疗组。
- 总体 n(%) 与 EAIR 使用 `treatment period`；后三列分别为 `<12 months`、`12–<24 months`、`≥24 months`。
- `source_unit` 分开表达 `n (%)` 或 `/100 person year`，不再夹入时间窗与N。
- 复合人数/百分比格使用 `composite_count_and_percent`；裸零保持原文单值。
- `metric="unresolved"`，`denominator_candidates=[]`，没有授予数值等效/计算资格。
- 原五条带 result context 的 EAIR 将 normalized value 改为 null；新增 `5.60` 也为 null。

原文 EAIR 脚注完整重放：

> “number of patients having a specific event divided by total exposure time at risk, multiplied by 100”

> “person-years up until the first event or end of treatment period”

> “This was calculated post hoc.”

治疗期、re-entry 排除和 durability rollover 的原文限制仍保留。没有把时间窗N当作 continuous/naïve/re-treatment 队列，没有把治疗期死亡与 follow-up 死亡合并。

这些结论不覆盖 R1 的错误行路径。

#### P1-B：主要终点 ICE

以下原生全文段已正确附到8个主要终点格及1个 narrative：

```text
/article/body[1]/sec[4]/sec[8]/p[2]
```

其中包括：

> “Patients with missing data at the timepoint or who used rescue/prohibited medications/procedures before the timepoint were considered non-responders.”

> “Data collected after discontinuation were included in the analysis.”

九条的 scientific scope 明确区分 binary ICE 规则，并有：

```text
continuous_outcome_imputation_not_applied = true
```

未将同段 continuous WOCF/MI 规则应用到这些 binary responses；主要终点原值、时间点及 contrast/P 的非arm身份保持不变。

#### P2-C：新增格数值、表头与空白

新增原值全部匹配：

| 来源/原生行 | 依原生列顺序新增值 |
|---|---|
| dupilumab Table3 tr2，PRIME placebo/dupilumab；PRIME2 placebo/dupilumab | `5 (6.7)`、`3 (4.0)`、`1 (1.2)`、`2 (2.6)` |
| LTE Table2 tr8，总体n(%)、EAIR、三个事件时间窗 | `53 (10)`、`5.60`、`30 (6)`、`23 (6)`、`5 (2)` |

新增 context 的 category 为 `teae`、endpoint 明确 severe；没有归为 `sae`。

**`5.60` 仅来自 tr8/td3。** tr4/td3 的 severity-stratum EAIR 仍为空白，未补值；tr2/td3、tr3/td3 也保持空白。新增 scope 明示不得互填或重复合计。该数值部分通过，身份闭包仍需 R1/R2。

#### P2-D：脚注关系

`dup-discontinuation-and-relatedness-limits` 已明确：

- b 属于因TEAE停止治疗行，不是重度行脚注。
- a 属于 severe 行。

四条新增 dupilumab severe facts 均附精确脚注 a：

```text
/article/body[1]/sec[2]/sec[8]/p[1]/table-wrap[1]/table-wrap-foot[1]/p[2]
```

> “Considered unrelated to the study intervention except for two events of sepsis and mesenteritis, experienced by one placebo-treated patient in PRIME.”

并保留脚注规定的 **24 weeks of treatment**及按实际接受干预分析的安全性人群。没有据此生成未报告的 treatment-related TEAE 总计。

### 4. Bounded disposition 与限制

Owner 已明确 holding source facts 和 severe-total 范围，**无需再作范围决策或补充原件**。剩余修复均有精确证据与位置：

1. 五条 LTE severe facts 的 scope 行路径改为 tr8。
2. 九条新 severe facts 的标签/说明保留 severe 限定和列角色。
3. `coverage_note_zh` 同步118条的实际分类数量。

安全暂行路径：保留 v3 为 `proposal_not_accepted`，不授予 numerical frame/current/release 权限；不要改已经核对通过的原始值、脚注、ICE段或空白格。

本轮没有验证消费者是否执行 holding gate，也没有进行产品、医学、监管或发布接受。**本报告不推荐对当前摘要直接作 ACCEPT_BOUNDED；修订后应由 Codex 核对新摘要及上述定点变更，最终 authority 仍属于 Codex。**
