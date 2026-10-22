---
name: extract-results
description: 为一个药物补充疗效/安全性结果（论文、会议摘要、监管审评），逐字引用原文
tools: [pubmed_search, pubmed_fetch, web_search, fetch_url, fda_drugsfda]
output: ExtractionResult
max_steps: 24
---
输入：一个药物、适应症、已知试验（trials_with_registry_results 中的试验 CT.gov 已有结构化结果，不要重复抽取）。

步骤：
1. 找关键结果来源：pubmed_search（药物名 AND 适应症 AND (phase 3 OR randomized)）、会议摘要（web_search）、
   FDA 审评/说明书（fda_drugsfda 的 documents）。
2. **必须先用 pubmed_fetch / fetch_url 读取原文**，再从读取到的文本中抽取；未读取的来源不得作为 source_url。
3. 每个事实：
   - field：result.primary.value / result.key_secondary.value / result.secondary.value /
     safety.sae.any / safety.discontinuation / safety.death.all_cause / safety.ae.term
   - entity：试验号（NCT/CTR）优先，没有就写药物名
   - endpoint：终点原文名称；timepoint：原文时间点；arm：原文组名（不得改写）；population：分析人群原文
   - stat_type：count_participants（人数）/ count_events（事件次数）/ proportion（%）/ mean / ls_mean_change / hazard_ratio 等
   - denominator：仅当原文明确给出该组 N
   - quote：**从读取文本中逐字复制**、包含该数值的一段（≤400 字）
4. 原文没有的写进 gaps（例如「III 期 52 周数据未公开」），不要推断、不要换算、不要把未报告写成 0。
