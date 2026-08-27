# Task 5.5 独立科学复核精简包

复核对象：`fixtures/positive/a-atopic-dermatitis/research-content.json`

规范化研究内容摘要：`dc439a8c872e8f85224718bcb53eb1e170f51a2192a2a19178bf32865e45abc4`

## 规模与硬边界

- 适应症：特应性皮炎；数据截止：2026-08-18（Asia/Shanghai）。
- 38 个创新治疗项目、43 项试验、65 个来源版本、271 条受众事实。
- 19 个有公开关键结果的产品均有治疗组/对照组疗效，并至少有两组任何 TEAE 或任何 SAE。
- 中国药物临床试验登记平台连续三次返回 HTTP 202 / FSS JavaScript challenge；记录为技术阻断，并保留 ClinicalTrials.gov、主要报告和企业正式披露等替代路线，未写成“未找到”。

## 本轮重点变更

- Amlitelimab：疗效改为 COAST 1（NCT06130566）第 24 周 EASI-75，Q12W 39.1% 对安慰剂 19.1%；安全性精确分母来自 STREAM-AD（NCT05131477）并在表中明确显示不同试验；2026-07-24 已停止 AD 开发且不申报。
- Rocatinlimab：疗效改为 HORIZON（NCT05651711）第 24 周 EASI-75，178/543=32.8% 对 25/183=13.7%；安全性精确分母来自 NCT03703102 并明确显示不同试验；2026-03-03 已停止全部试验并继续安全随访。
- 乐德奇拜单抗：RADIANT-AD（NCT06477835）第 16 周 EASI-75 74.2% 对 34.4%，任何 TEAE 60.9% 对 64.9%；2026-04-30 港交所公告显示中国 NDA 重新受理。
- 司普奇拜单抗：NCT05265923 第 16 周 EASI-75 66.9% 对 25.8%，任何 TEAE 71.3% 对 66.3%；不再以 52 周单臂合并 TEAE 88.1% 冒充同期对照。
- Crisaborole：删除无法从所绑来源复核的任何 TEAE 29.4%/32.0%，只保留登记可核的 SAE 3/510 对 0/247。
- Tralokinumab、Nemolizumab、Abrocitinib：不再把 ClinicalTrials.gov 的 `otherNumAffected` 误写成任何 TEAE。
- Eblasakimab：保留历史 TREK-AD，但标为原开发主体清算、资产处置和后续开发未核实。
- SHR-1819：II 期 NCT05549947 与 2026-05-28 同行评议主要报告交叉绑定；第 16 周 EASI-75 采用 600 mg Q4W 组 85.4% 对安慰剂 37.8%，任何 SAE 采用 3 个治疗组合并 7/120 对 3/37。同时纳入成人 III 期 NCT06468956（停止招募）和青少年 III 期 NCT07309055（招募中），产品阶段按当前最高 III 期呈现。
- AK120：III 期 NCT06383468 状态未知且未公开结果；另将 II 期 NCT05048056 作为独立历史试验纳入，登记原文 `whyStopped` 为临床研究及开发策略调整。不得把单试验终止写成产品终止，也不得删除这项历史。
- 全部试验的期别改为直接读取 ClinicalTrials.gov `designModule.phases`，不再用产品当前阶段覆盖代表试验期别。
- 12 个已获批产品的当前状态改绑药监机构现行材料或企业中国批准正式公告；ClinicalTrials.gov 不再承担批准事实的来源。境外批准不外推为中国批准，中国状态未核实即明确标注未核实。
- 面向用户的状态、给药途径和机制缺失说明已统一为中文临床语境；删除“待闭合”“AD 已获批”等内部工作语或中英夹杂表达。

## 建议抽查产品

度普利尤单抗、曲罗芦单抗、司普奇拜单抗、乐德奇拜单抗、Amlitelimab、Rocatinlimab、Tezepelumab、Eblasakimab、CM326、IBI356、SHR-1905、SKB575/HBM7575。

复核者应直接按产品和 `source_id` 分段读取完整 JSON；本文件只用于导航，不能替代原始来源正文或最终结论。
