# Conference Output: ci-1007-publication-atoms-review-v1 - evidence_single_object round3
## Output

### Verdict

**ACCEPT_BOUNDED — 仅确认 R1/R2/R3 在以下精确 v4 摘要上的修正闭合：**

`6e545087d448f04b49046327ee9628c5c574447337320e254e6a88a3947f1c82`

五条 LTE severe scope 行路径、九条 severe 中文标签/说明、51＋67＝118 的覆盖数量均核对通过。没有发现此次修订改变原始数值、来源身份、引用、状态或已核对的 ICE/EAIR contexts。

这是**同会话定点确认性闭包**，不是新的独立全候选 clearance，不是正式科学采用或最终医学/产品接受。v4 仍为 `proposal_not_accepted`，没有应用它的权限。

原两次 **REVISE** 判定继续适用于各自旧摘要：

- v2：`a33c450adb06bd397102d88f3367d53630afd01e7290d3e8cf081a3755724ae4`
- v3：`74415ca2ecfcecc994cdab0e99885304b3d89b81e0c1162125f39858e8ced151`

### 1. 实际执行与检查范围

只直接读取本轮授权的七份文件：v3/v4、两份原生 XML，以及三份生产合同/提取器文件的相关范围。完整解析两个 JSON，未以截断预览代替完整检查。

执行一次 grouped read-only validation：

- `.venv/bin/python -B -c`
- `PYTHONDONTWRITEBYTECODE=1`
- 退出码 **0**
- 检查错误列表 **为空**

未运行仓库广泛测试；未读取 writer report、私人推理或 holding library；没有网络、browser、git、DB、临时 helper、递归 dispatch、cleanup 或任何文件写入。

#### 摘要验证

| 输入 | 字节数 | 实测 SHA-256 |
|---|---:|---|
| v4 | 1,271,006 | `6e545087d448f04b49046327ee9628c5c574447337320e254e6a88a3947f1c82` |
| v3 | 1,268,401 | `74415ca2ecfcecc994cdab0e99885304b3d89b81e0c1162125f39858e8ced151` |
| PMID37142763 XML | 172,525 | `2bb91f3c0ec34d8aebf9a6c4bf879d866cc66d214f4fc5e6e81a59ec6992dd71` |
| PMID41405008 XML | 123,886 | `5354b1ad692e3127692bc7d11a131558fa12f41f72d18001f37b034a1fe51cd0` |

均匹配指定冻结值。

#### 检查计数

| 检查 | 结果 |
|---|---:|
| v4 全部 facts 经生产 `ResearchFact` 及嵌套 context schema 验证 | 118/118通过 |
| v3/v4 fact ID 集合一致、无新增或删除 | 118条一致 |
| 原始值、normalized value、locator、source/entity identity、original text、disclosure state、result context 不变 | 118/118通过 |
| Clause continuations 与 relations 完全不变 | 118/118通过 |
| Fact 差异仅在指定 R1/R2 字段 | 118/118通过 |
| 受影响9格与原件数值重放一致 | 9/9通过 |
| 实际行、列身份及其 continuation 核对 | 9/9通过 |
| LTE severe scope 行路径 | 5/5通过 |
| Severe 中文标签/说明 | 9/9通过 |
| Dupilumab severe 治疗期与脚注 a | 4/4通过 |
| 新 severe LTE context 的 group/time/unit 保持正确 | 5/5通过 |
| Severe EAIR 说明及原生脚注 | 1/1通过 |
| 三个 severity-stratum EAIR 空白未生成 fact、原件提取器拒绝空白引用 | 3/3通过 |

**引用数量区别：**

- 本轮9条受影响 facts 包含 **100次 context reference occurrences**。
- 按 source/path/quote 去重为 **32条唯一原文引用**；实际重放 **32/32通过**。
- 整个候选有 **1,149次 context reference occurrences**，与 v3 相同；本轮没有重新对全部引用进行科学审阅。
- 本轮重放9个 fact 原文格，不宣称重新逐条原件审阅全部118条 facts。

### 2. R1：五条 LTE severe 行路径闭合

原件：

`.artifacts/1007-publication-source-dates-v1/source-library/evidence/raw/sha256/53/5354b1ad692e3127692bc7d11a131558fa12f41f72d18001f37b034a1fe51cd0.bin`

定义精确路径：

```text
N2 = /article/body[1]/sec[3]/sec[2]/sec[1]/table-wrap[1]/table[1]
```

受影响 fact IDs 为以下精确集合：

```text
pubfact:PMC13308661:{N2}/tbody[1]/tr[8]/td[c]
c ∈ {2,3,4,5,6}
```

五条的 `source_clause_context.scientific_scope.row_label_path` 现均为：

```text
/article/body[1]/sec[3]/sec[2]/sec[1]/table-wrap[1]/table[1]/tbody[1]/tr[8]/td[1]
```

实际原文：

> `Any severe TEAE`

该路径与 cell locator、`result_context.endpoint`、已有 row continuation 一致，不再指向 tr1 的 `Any TEAE`。

原始格值保持：

| 列 | 值 | 来源列角色 |
|---|---|---|
| td2 | `53 (10)` | 总体治疗期 n(%) |
| td3 | `5.60` | 总体治疗期 EAIR |
| td4 | `30 (6)` | `<12 months` |
| td5 | `23 (6)` | `12–<24 months` |
| td6 | `5 (2)` | `≥24 months` |

**`5.60` 仍仅属于 tr8/td3。** tr4/td3 的 severe severity-stratum EAIR 仍为空白，没有借值、填零或新增 fact；tr2/td3、tr3/td3 也维持空白。

### 3. R2：九条 severe 中文标签/说明闭合

#### Dupilumab 四条

原件：

`.artifacts/1007-publication-source-dates-v1/source-library/evidence/raw/sha256/2b/2bb91f3c0ec34d8aebf9a6c4bf879d866cc66d214f4fc5e6e81a59ec6992dd71.bin`

定义精确路径：

```text
D3 = /article/body[1]/sec[2]/sec[8]/p[1]/table-wrap[1]/table[1]
```

受影响 fact IDs：

```text
pubfact:PMC10202800:{D3}/tbody[1]/tr[2]/td[c]
c ∈ {2,3,4,5}
```

原生行：

> `Patients with any severe adverse eventa`

四条标签现为 **“任何重度不良事件”**；说明明确患者人数、原文百分数、24周治疗期安全性人群、重度不等于严重（SAE），并保留脚注 a 的相关性限定。

原始值仍为 `5 (6.7)`、`3 (4.0)`、`1 (1.2)`、`2 (2.6)`；列标题仍对应 PRIME/PRIME2 的各自实际治疗组及安全性 N。

脚注定位：

```text
/article/body[1]/sec[2]/sec[8]/p[1]/table-wrap[1]/table-wrap-foot[1]/p[1]
```

原文明确：

> “Patients are listed according to the study drug they received … Results are reported for the 24 weeks of treatment.”

Severe 脚注 a 位于同一 foot 的 `p[2]`：

> “Considered unrelated to the study intervention except for two events of sepsis and mesenteritis, experienced by one placebo-treated patient in PRIME.”

两者均保留并重放通过，没有生成未报告的相关 TEAE 总计。

#### LTE 五条

R1 所列五条的标签现为 **“任何重度 TEAE”**，不再描述 unrestricted Any TEAE。

说明正确区分：

- 总体 n(%)：患者人数和原文百分数，所属 treatment period。
- td4–td6：各自事件发生时间窗，明确不是 cohort。
- td3 `5.60`：源报告的治疗期暴露调整发生率，单位 `/100 person year`，不是人数或百分比，未授予数值共轴资格。

原有 group、timepoint、unit、composite type 和 `metric="unresolved"` 没有改变；`normalized_value` 仍为 null。Severe facts 的 category 保持 `teae`，而不是 `sae`，英文 endpoint 保持 severe。

EAIR 脚注位置：

```text
/article/body[1]/sec[3]/sec[2]/sec[1]/table-wrap[1]/table-wrap-foot[1]/fn[3]/p[1]
```

实际原文仍完整保留：

> “number of patients having a specific event divided by total exposure time at risk, multiplied by 100”

> “person-years up until the first event or end of treatment period”

> “This was calculated post hoc.”

没有由率值推导 n/N，没有合并治疗期、follow-up、事件时间窗或队列。

### 4. R3：覆盖数量闭合

`coverage_note_zh` 已与实际事实构成一致：

| 来源 | Definition | Narrative | Population | Primary result | Safety total | 合计 |
|---|---:|---:|---:|---:|---:|---:|
| PMID37142763 | 13 | 2 | 8 | 8 | 20 | **51** |
| PMID41405008 | 9 | 2 | 9 | 0 | 47 | **67** |
| 合计 | 22 | 4 | 17 | 8 | 67 | **118** |

说明保留 severe 与 serious 的区别、LTE tr8 EAIR `5.60` 与 tr4 空白分开、不互填或重复合计，以及非全文/全部次要终点/全部图表覆盖的限制。

### 5. Delta 与未变条件

观察到的全部 fact 修改是 **9条 facts、23个叶字段差异**：

- 9个 `label_zh`。
- 9个 `scope_note_zh`。
- 5个 LTE `scientific_scope.row_label_path`。

其他109条 facts 完全未改。全部118条的原始值、引用、source identity、状态、result contexts 和 context references 均保持 v3 内容，因此已核对的 ICE/EAIR contexts 没有被本次修订改变。

顶层另有：

1. R3 指定的 `coverage_note_zh` 更新。
2. 新增 `owner_literal_closure` 元数据。

后者是此次闭包的追踪声明，不是 clinical fact 变更；其内容保留旧 REVISE、`new_independent_ACCEPT_for_this_digest=false`、`scientific_adoption=false`。**其中外部报告摘要与 owner 执行声明没有在本轮独立验证**，不作为本结论证据。其他顶层字段与 v3 一致。

### 6. Remaining limitations / bounded disposition

**R1/R2/R3 无剩余阻断；无需额外原件或范围决定。** 可向 Codex 建议将这三项在精确 v4 摘要上记为已闭合，不推翻旧摘要的 REVISE。

保留边界：

- 本次不是独立 fresh clearance。
- 不签署 whole-candidate numeric equivalence、日期历史、fulltext/universe closure、current、Chinese C、visual 或 release。
- 不验证消费者如何执行 holding/numerical-frame gate。
- 不将 schema、quote replay 或 scalar 值视作科学接受。
- 不授权应用候选或修改 `proposal_not_accepted`。

最终医学、专业、产品与发布接受仍由 Codex 保留。
