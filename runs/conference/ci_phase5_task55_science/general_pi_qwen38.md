All round-6 checks pass. Final report:

# Conference Participant Output: ci_phase5_task55_science - general_pi_qwen38

## Reviewed digest:
`dc439a8c872e8f85224718bcb53eb1e170f51a2192a2a19178bf32865e45abc4`

Computed in-process via `compute_research_content_digest(json.load(...))` on the current `fixtures/positive/a-atopic-dermatitis/research-content.json` (7,931,422 bytes): computed == required, **MATCH: True**. `FreshAResearchContent.model_validate` passed mechanically: 65 source ids unique; all `first_disclosed_at ≤ data_cutoff` (2026-08-18T23:59:59.999999+08:00); 271 facts reference in-package sources; fact ids unique; 39 claims reference in-package facts; all required refs bound; every 已公开 safety row has trial+arm. Scale confirmed: 38 products / 43 trials / 65 sources / 271 facts / 39 claims (-38 efficacy / 152 safety).

## P0/P1:
**无。**

## 中文表达复核:
1. **禁忌内部表达已清除**：对 `report_data` 全字段做字符串扫描——"闭合"、" AD"、"待更新"、"未从官方页面" 四类 0 命中；不再出现 "待官方页闭合"/"境外已获批；中国状态待官方页闭合" 等内部工作语。"未核实"、"未公开登记"、"登记所列地区" 为自然中文临床表达（非工程术语），保留正确。✓
2. **适应证措辞**：upadacitinib "美国特应性皮炎适应证已获批；中国特应性皮炎适应证状态未核实"；baricitinib "欧盟特应性皮炎适应证已获批；中国状态未核实"；ruxolitinib-cream "美国特应性皮炎适应证已获批…"；tapinarof、roflumilast-cream 同。"特应性皮炎适应证" 显式化，且境外批准未外推为中国批准（中国状态均带"未核实"）。crisaborole为"美国已获批"（适应证为湿疹，未加性皮炎限定——符合其 label 的 full label 语境，非错误）。✓
3. **开发状态用 "特应性皮炎" 而非 "AD"**：amlitelimab status="2026年7月停止特应性皮炎开发，不再申报"（fact raw 同，src=sanofi-20260724）；tezepelumab status="因未达到预设疗效而终止特应性皮炎开发"（fact raw 同，src=ctgov-nct03809663）。状态事实与来源保持一致。✓

## 科学与谱系回归:
- **12 个已获批产品 current_status 全部仍绑定 `regulatory_label_or_approval`**（all 12 regulatory: True）——dupilumab→sanofi.cn、abrocitinib→pfizer.cn、stapokibart→NMPA、tralokinumab/baricitinib→EMA EPAR、其余→openfda labels。本次中文修订未改来源绑定。
- **疗效/安全性/多试验/规模未回归**：38 产品 / 43 试 / 65 来源 / 271 事实 / 39 声明；19 个"有公开关键结果"产品门槛保持；SHR-1819 三试（II 核心 + 成人III ACTIVE_NOT_RECRUITING + 青少年III RECRUITING）与 AK120 双试（III UNKNOWN + II TERMINATED）分别保留；43项 trial phase 无一项标"已上市"仍未回归。- 数字领域闭环（上轮锁定的摘要值）未因表述改动而变：疗效 37.9/10.3、15.8/7.1、85.4/37.8、39.1/19.1 等不变；SAE rounding 0 错。

## 残余非阻断问题（P2/P3）:
- P2：openfda label 无字面 "United States" 令牌（法域由 FDA label 语义隐含），主张仍正确。
- P2：单一剂量臂疗效值（SHR-1819 600mg Q4W、tezepelumab 210mg Q4W、rocatinlimab 300mg Q2W）经 population/时间窗显式，显示层需跟随后续剂量标签。
- P2：`乐德奇拜单抗` 中文名全来源 0 次（来源为英文披露）；身份/NDA 有 HKEX 强支撑，中文商用名未回源。
- P3：claims 层仅覆盖疗效+宇宙合成；SAE/TEAE 与状态逐项在 facts 层（合同允许）。

---

**Decision: ACCEPTED**

Reviewed digest: `dc439a8c872e8f85224718bcb53eb1e170f51a2192a2a19178bf32865e45abc4`（复算一致）

P0/P1: 无

中文表达复核: "闭合"、" AD "、"待更新"、"未从官方页面" 等内部表达在 report_data 0 命中；乌帕替尼、巴瑞替尼、芦可替尼乳膏、他匹那罗夫、罗氟司特乳膏状态均显式 "特应性皮炎适应证" 且境外不外推中国（中国状态带"未核实"）；Amlitelimab、Tezepelumab 开发状态用 "特应性皮炎" 而非 "AD"，事实与来源一致。

科学与谱系回归: 12 个已获批产品 current_status 全部绑定 regulatory_label_or_approval 未变；38 产品 / 43 试 / 65 来源 / 271 事实 / 39 声明，19 结果产品门槛保持，SHR-1819 三试与 AK120 双试多试验分别保留，43 试无"已上市"期别。疗效/安全性/SAE rounding 未回归。

残余非阻断问题（P2/P3）: openfda 无字面 "United States" 令牌、剂量臂显性标注、乐德奇中文名回源、claims 覆盖可优化。均不阻却。
