---

# 独立科学复核输出

## 1. Decision: ACCEPTED

## 2. Reviewed digest

`dc439a8c872e8f85224718bcb53eb1e170f51a2192a2a19178bf32865e45abc4`

通过 `compute_research_content_digest(payload)` 在 `PYTHONHASHSEED=0/1/42/random` 四个独立 Python 进程下稳定复算。与 packet `dc439a8c872e8f85224718bcb53eb1e170f51a2192a2a19178bf32865e45abc4` 完全一致。`FreshAResearchContent.model_validate` 通过；`gate_status="passed"`。

规模：38 产品 / 43 试验 / 65 来源 / 271 事实 / 39 声明，与 packet 全部对齐。

## 3. P0/P1

无。

- Codex chair 明确禁止的四个内部表达 `闭合` / ` AD ` / `待更新` / `未从官方页面` 在 `report_data` 用户可见字段中**0 处命中**。
- 12 个含"已获批"语义的产品 `product.current_status` 全部仍绑定 `regulatory_label_or_approval`（0 个违规）。
- 给药途径字段（route）全部为自然中文："皮下注射"/"口服"/"外用"/"静脉或皮下注射"/"给药途径尚未公开"。
- 机制字段（mechanism）全部为自然中文 + 靶点 + "作用于…；具体机制尚未获得充分公开资料"。
- 38 efficacy + 38 safety 事实全部可在源结构化路径或派生计算下验证，0 个回归缺失。

## 4. 中文表达复核

针对 chair 列出的三个产品修订点：

- **乌帕替尼**：`"美国特应性皮炎适应证已获批；中国特应性皮炎适应证状态未核实"` ✓；源 `openfda-upadacitinib-label` 含 `treatment of adults and pediatric patients 12 years of age and older with refractory, moderate to severe atopic dermatitis`（Rinvoq + atopic dermatitis 200 字符窗口内共现）。
- **巴瑞替尼**：`"欧盟特应性皮炎适应证已获批；中国状态未核实"` ✓；源 `ema-olumiant-epar` 含 `adults and children from 2 years of age with moderate to severe atopic dermatitis`（Olumiant + atopic dermatitis）。
- **芦可替尼乳膏**：`"美国特应性皮炎适应证已获批；中国状态未核实"` ✓；源 `openfda-ruxolitinib-label` 含 `topical short-term and non-continuous chronic treatment of mild to moderate atopic dermatitis... patients 2 years of age and older`（Opzelura + atopic dermatitis）。
- **他匹那罗夫**：`"美国特应性皮炎适应证已获批；中国状态未核实"` ✓；源 `openfda-tapinarof-label` 含 `topical treatment of atopic dermatitis in adults and pediatric patients 2 years of age and older (1.2)`（Vtama + atopic dermatitis）。
- **罗氟司特乳膏**：`"美国特应性皮炎适应证已获批；中国状态未核实"` ✓；源 `openfda-zoryve-label` 含 `Indications and Usage, Atopic Dermatitis (1.2) 10/2025`（Zoryve + atopic dermatitis）。

Amlitelimab：`"2026年7月停止特应性皮炎开发，不再申报"` ✓；源 `sanofi-20260724` 含 `discontinuation of clinical development of amlitelimab... in moderate-to-severe atopic dermatitis`（amlitelimab + atopic dermatitis）。

Tezepelumab：`"因未达到预设疗效而终止特应性皮炎开发"` ✓；源 `ctgov-nct03809663` 的 `whyStopped: Tezepelumab as a monotherapy in atopic dermatitis did not reach the targeted efficacy level...`。

境外→中国批准无外推：9 个境外已获批产品的 status 均含"中国状态未核实"或"中国特应性皮炎适应证状态未核实"。

`route` 与 `mechanism` 字段的"未公开"措辞统一为自然中文"尚未公开"或"尚未获得充分公开资料"（无"待官方页闭合"残留）。

## 5. 科学与谱系回归

- **38 产品**：universe_closed=True，全部为创新药，无回归。
- **43 试验**：phase 全部直接读取 `designModule.phases`，0 个 mismatch；trial.registry_status 43 项仍全部绑 `clinical_trial_registry`。
- **65 来源**：43 ctgov + 2 pubmed + 8 公司/会议披露 + 12 监管依据（3 中国监管 + 2 EMA EPAR + 7 openFDA label），结构与上一轮一致。
- **19 个有公开关键结果产品**：efficacy 38 行 trt/ctl 完整、safety 38 行（带 value）全部在 `adverseEventsModule.eventGroups[].seriousNumAffected/seriousNumAtRisk` 或非 ctgov 源文本可定位。
- **38 个 efficacy fact**：36 个 ctgov 路径直接命中，2 个 Roc HORIZON（32.8%/13.7%）从 pubmed-41314226 摘要 `178 [33%] of 543` 与 `25 [14%] of 183` 派生（178/543=32.78%、25/183=13.66%，属可审计确定性计算）。
- **38 个有效 safety fact**：0 miss，0 regression。
- **SHR-1819 多试验修订未破坏**：`nct05549947` PHASE2/COMPLETED（核心，疗效绑 `springer-shr1819-20260528`）；`nct06468956` PHASE3/ACTIVE_NOT_RECRUITING（成人 III 期支持）；`nct07309055` PHASE3/RECRUITING（青少年 III 期支持）。
- **AK120 多试验修订未破坏**：`nct06383468` PHASE3/UNKNOWN（核心 III 期）；`nct05048056` PHASE2/TERMINATED（II 期历史，`whyStopped: Clinical study and development strategy adjustment`）。
- **CDE 阻断**：`route_attempts` 三次连续 `china-drug-trials-public-site` 全部 `result_class=captcha_required`，与"未找到"严格区分。
- **gate_status=passed**。

## 6. 残余非阻断问题

- **P2（轻微）**：`report_data.products[].status` / `regulatory[].status` / `history[].status` 三处仍含 ctgov `overallStatus` 的工作语字面翻译，如"已停止招募"（22 处，对应 `ACTIVE_NOT_RECRUITING`）、"登记进行中"（21 处）、"招募中"（12 处）、"登记招募"（6 处）、"登记未公开数值结果"（18 处）。这些不是 chair 本轮明确点名的"闭合/AD/待更新/未从官方页面"四项，但是 ctgov API 状态字段的直译，对终端临床医生可读性略欠。如要彻底面向用户，下一轮可改为更口语化中文，例如：
  - `"已停止招募"` → `"已停止入组"`
  - `"登记进行中（已停止招募）"` → `"试验仍在进行，但已停止招募新受试者"`
  - `"登记招募"` / `"招募中"` → `"正在招募受试者"`
  - `"登记未公开数值结果"` → `"试验已完成但未公开主要结果"`
  
  当前版本仍可被医学专业人员理解，且 chair 本轮指明的四项禁用表达已全部清空。建议作为下一轮可读的展示优化，不阻断本轮验收。

- **P3（轻微）**：4 处 `efficacy.endpoint = "vIGA-AD 治疗成功"`、`vIGA-AD` 中含英文字母"AD"——这是 endpoint 命名本身（Validated Investigator Global Assessment for Atopic Dermatitis），不是缩写替代。"AD"在医学专有名词内嵌属于专业惯例，不属于 chair 禁用的"中英夹杂"。
