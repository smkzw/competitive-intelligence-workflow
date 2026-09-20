做最终一轮：先核对摘要和关键配对是否仍成立，再给出无自相矛盾、可执行的接受/拒绝结论。# Conference Participant Output: ci_phase5_a_data_matrix_science_review_v2 - general_grok46

## Boundary Check

- Role: `general_grok46` / Grok Build `grok-4.6`. Same-session continuation round 3 (final participant pass). Advisory only; Codex remains final authority.
- No production writes, no report-file write, no sibling outputs, no other-participant files, no live web fetch, no self-claimed browser/PPT/visual/regulatory acceptance.
- Review object for this pass (context source of truth, independently re-hashed): `.artifacts/a-data-matrix-recheck-candidate-v2/research-content.json` → content digest **`40f10108d8ab422a0b8adfcb149ebb6cd351e37cb66d73bc7e25d80d44d9664f`**. Counts: 38 products, 49 trials, 76 sources, 6,780 efficacy, 10,222 safety; 24 有公开关键结果 / 4 已有部分公开结果 / 10 暂无公开关键结果.
- Preview-v6 `report-a.js` is byte-identical to `src/ci_workflow/renderers/portal/assets/report-a.js` and contains `data-trial-id` / `data-arm-detail`. Chromium was **not** re-run in this process; pairing was recomputed from locked JSON using the same week-16 / EASI-75 matchers as the JS.

## Independent Work Product

### Contradictions from earlier rounds — resolved

| Round | Claim | Error | Resolution |
|---|---|---|---|
| 1 | Reject `cae2c338…` for ICP 2/25、AK120 混组、611 口径、TQH 缺 II 期、状态文案、矩阵 `trial_id` 过宽 | Valid **for that digest** | Keep as history. That hash is **not** the live object |
| 2 | Reject `40f10108…` because Amlitelimab COAST 1 第24周 39.1% 无安全性 | Mixed **canonical labeled EASI-75 rows** with **default matrix filter (EASI-75 × 第16周)** | **Withdrawn.** Default matrix cannot select COAST 1 week 24 |
| 2 | Treat product heatmap max as a blocker | Chair: heatmap is **intended** product-level max, labeled in copy | **Withdrawn as reject.** Residual documentation only |
| 2 | Call InnoCare 8.0% still “reconstructed 2/25” | After repair, n/N are null; 8.0% is in the locked extract | **Withdrawn.** Residual = thin extract, not fabricated counts |
| Prompt header vs context | Header still names `cae2c338…` | Context SoT and loop log name `40f10108…` and forbid reusing the old conclusion | This pass scores **`40f10108…` only** |

### Final verdict

**接受 `40f10108…` 作为本轮 A 类科学复核对象。**

含义（可执行）：六个指定修复项关闭；默认气泡矩阵按同试验 + 同 `arm_detail` 取安全性；AK120 合并组 TEAE 不进入默认矩阵。  
**不包括：** 正式 `research-package.json`、替换当前入口、PPT/PDF、浏览器/视觉最终验收、现时网页权威。这些仍归 Codex。

### 指定六项（关闭）

| 项 | 证据 | 结论 |
|---|---|---|
| ICP-332 | EASI-75 64.0% / 8.0%，numerator/denominator 均为 null。T←PubMed；C←InnoCare 摘录「安慰剂组 8.0%、80 mg 64.0%、120 mg 64.0%」。PubMed 差值 56.0 个百分点与 64−8 一致。TEAE 19/25 vs 17/25 仍来自 PubMed；SAE 保持未公开 | 关闭。禁止再写 2/25、16/25 |
| AK120 | status=已有部分公开结果；comparable=[]；TEAE term=`任何TEAE（AK120多剂量合并）` 71.1/69.2；疗效 `arm_detail`=`AK120 300 mg Q2W`（无负荷剂量） | 关闭。默认矩阵键 `任何TEAE` 不命中 |
| 611 | `研究药相关上呼吸道感染` 2/30 vs 0/32 | 关闭 |
| TQH2722 | trials=`nct06552520` + `nct05970432`；status 写明 II 期数值经多轮检索未找到 | 关闭。未伪造率 |
| 产品状态 | 艾玛昔替尼「III期主要疗效与安全性结果已公开」；Difamilast「III期随机对照疗效及长期安全性结果已公开」；不再写「登记未公开数值结果」与论文打架 | 关闭 |
| 矩阵同组 | `safetyFor(id, term, trialId, armDetail)`；气泡写入 `data-trial-id` / `data-arm-detail` / title 含 `display_id` | 关闭（见下复算） |

### Amlitelimab（独立复算，纠正第2轮）

从 v2 JSON 按 JS `isEasi75` + `isWeek16` 筛选，并要求同一 `trial_id+endpoint+timepoint+unit+population` 上治疗组+对照组齐全：

- 成对上下文均在 **`nct05131477`（STREAM-AD）**，不是 COAST 1。
- 治疗组 42.9%（`125 mg KY1005 (Part 1)`）对安慰剂 11.4%（`Placebo (Part 1)`）。
- 同 `arm_detail` 的任何TEAE = **67.5%**（Baseline through week 24）。
- 与 chair 记录的 v6 气泡及测试 `data-trial-id == nct05131477`、AK120 气泡 0 一致。
- 包内仍保留 COAST 1 第24周 39.1% vs 19.1%、该 NCT 数值安全性 0 行。那是**另一时间点的疗效行**，不是默认矩阵点。产品「有公开关键结果」由 STREAM-AD 成对疗效+TEAE/SAE 支撑，与默认矩阵试验一致。

残余：疗效 endpoint 原文含 “Week 16 and Week 24”；安全性窗为 Part 1 至第24周。同试验同剂量，时间窗不完全等同，**不是跨试验拼点**。

### 热图

无 `trialId` 的产品级最高发生率 + 中文注记「同一产品有多项公开结果时显示最高发生率」= 本轮 **预期产品横向比较**，不作为拒绝理由。

### 保留的有用证据（非阻断）

- 艾玛昔替尼 NCT04875169：74/112 vs 24/111；TEAE 74/112 vs 72/111；SAE 2/112 vs 3/111，与 PMC 摘要一致。
- GR1802：75.0%/32.5% 及 Table 3 与 403 恢复摘录一致；30/40、13/40 由 n=40 反推。
- Rezpeg：42%/17%；不含 ISR 的 TEAE 与 SAE 隔离正确。
- APG777 / Eblasakimab / Difamilast：部分公开边界正确；Difamilast comparable 为空。
- Bempikibart：AD `nct05509023`；斑秃 NCT 不在 trials。
- 10 个无关键数值产品空值与检索闭环一致；ANB032 文案已写未达终点，`result_status` 仍为「暂无公开关键结果」（分类残余）。

## Evidence And Assumptions

### Evidence

- `compute_research_content_digest(v2 artifact)` = `40f10108d8ab422a0b8adfcb149ebb6cd351e37cb66d73bc7e25d80d44d9664f`.
- Six-item row checks as in the table above (this process, current files).
- Matrix matcher reproduction: 42.9 / 11.4 / TEAE 67.5 on `nct05131477` + `125 mg KY1005 (Part 1)`.
- v6 JS == source JS; `test_a_matrix_keeps_amlitelimab_on_one_trial_and_excludes_ak120_pooled_safety` **read, not executed**.

### Inference

- Default 第16周矩阵不会画出 COAST 1。第2轮拒绝是筛选项判断错误，不是数据又坏了。
- InnoCare 8.0% 与 JAMA 差值一致，支持同一试验 topline；不能替代未保存的官网 HTML。

### Recommendation（给 Codex 的动作）

1. **记录本角色对 `40f10108…` 的科学接受**（范围=六项修复 + 默认矩阵同试验同组）。
2. **不要**把 `cae2c338…` 或第2轮「Amlitelimab 矩阵跨试验」写进最终否决。
3. Codex 自己完成 v6 Playwright/1024 px 视觉签字（本角色未跑浏览器）。
4. 视觉通过后，将 `scientific_review.status=accepted` 且 `reviewed_content_digest=40f10108d8ab422a0b8adfcb149ebb6cd351e37cb66d73bc7e25d80d44d9664f` 写入研究包。digest 不一致则 fail-closed。
5. **本会商 out of scope：** 生成/替换正式入口。那是接受绑定之后的另一步。
6. 非阻断可选项：InnoCare 补 raw HTML；`isWeek16` 收紧复合 “week 16 and week 24”；ANB032 改为「有结果无精确率」；英文登记题名中文化（中文审阅归 Codex）。

### Uncertainty

- 未在本进程执行 Chromium；6 个气泡的计数以 chair 记录 + 测试源为准，本角色只复现了 Amlitelimab 一对数值。
- 未打开 InnoCare 现时网页。
- 未对 6,780/10,222 条 CT.gov 展开行逐格重核。
- 预览路径 context 仍写 v5，loop log 与磁盘为 v6；审 JS 用的是 **v6=source**。

## Risks, Gaps, And Verification Needs

- **Risk:** 若只绑定旧 hash `cae2c338…`，会把已修缺陷重新锁进包。
- **Risk:** 若有人用「canonical EASI-75 = COAST 1」当默认图，仍会看到无安全性的第24周。默认第16周筛已挡住矩阵；产品页需靠现有试验标签区分。
- **Gap:** context 预览仍写 v5；以 v6 为准。
- **Codex owns:** 浏览器实跑、视觉、正式包写入。

### Objections, solutions, decision points, questions

**Objections**
1. 科学接受 ≠ 入口切换。Scope 禁止本会商生成正式报告。
2. 复合 Week 16+24 结局当第16周轴，是匹配粗糙，不是跨试验。

**Proposed solutions**
- Bind digest then stop. Optional matcher tightening = new digest + new review.

**Decision points**
- 本角色：**接受 `40f10108…`**。
- 热图产品内最大值：**不拒绝**。
- 正式包：**等 Codex 视觉绑定后再写**。

**Bounded questions**
1. 正式包是否在 Codex 视觉签字后立即绑定本摘要？安全路径：是，且 digest 必须逐字相等。
2. 复合时间点是否本轮就改 JS？安全路径：**不改**，避免无故换 hash。

**Safe provisional path:** Chair records science accept of `40f10108…`. No package file until Codex attaches review metadata to that exact digest.

## Recommended Next Step

Codex: (1) adopt **`40f10108d8ab422a0b8adfcb149ebb6cd351e37cb66d73bc7e25d80d44d9664f`** as the accepted science snapshot for this conference; (2) run/own v6 browser acceptance; (3) only then write `scientific_review` bound to this digest; (4) do not generate or switch the live A-class entry inside this conference scope; (5) discard `cae2c338…` and the round-2 matrix-mix reject as superseded. This participant output is not visual, production, or regulatory acceptance.
