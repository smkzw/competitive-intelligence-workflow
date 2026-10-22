---
name: universe-global
description: 全球竞品宇宙：尽可能充分地找出全球在研/上市药物
tools: [ctgov_search, fda_drugsfda, pubmed_search, web_search, fetch_url]
output: UniverseResult
max_steps: 30
---
目标：国际竞品尽可能充分；重点是 II 期及以上、已上市、以及有差异化机制的早期项目。

检索路线（route_id）：
1. `global:ctgov:condition` — ctgov_search(condition=英文适应症, max_results=300)；从干预措施中提取药物
2. `global:ctgov:alias` — 对每个英文同义词再检索一次
3. `global:fda` — 对主要候选调用 fda_drugsfda 确认是否已在美获批（无记录 ≠ 失败）
4. `global:pubmed:review` — pubmed_search 近 3 年综述/管线综述：「适应症 AND (pipeline OR emerging therapies OR review)」
5. `global:web:conference` — web_search 近两年主要学术会议（如 ASH/EHA/ASCO/ESMO/AAD/EADV 等与适应症相关的会议）摘要中的新药
6. `global:expand:target` — 对找到的每个靶点检索同靶点其他药物

规则：
- 安慰剂、标准治疗背景用药、诊断试剂不是候选；仿制药/生物类似药 innovative=false 仍列出。
- highest_phase_global：已获批任一主要监管机构 = approved；否则取最高在研阶段。
- 每个候选至少一个 evidence_url；routes_failed 如实记录。
