---
name: extract-results
description: 为一个药物补充疗效/安全性结果（论文、会议摘要、监管审评），逐字引用原文
tools: [pubmed_search, pubmed_fetch, web_search, fetch_url, fda_drugsfda]
output: ExtractionResult
max_steps: 24
---
mode=identity_enrichment 时只为输入药物补全来源档案，不抽试验结果、不重复登记表：读取官方监管/公司/公告原文，输出同一 ExtractionResult。可用字段为 identity.target、identity.modality、identity.developer、identity.rights_holder、status.china_mah_group、status.china.development、status.global.development；value必须是原文字符串，不把“III期”改写为phase3。entity写输入药物原名，source_id须为本次实际读取版本，quote逐字完整支持药物与值，不能只有靶点/公司而无药物关联。必要时从evidence_urls定位，再正常读取；不能把搜索摘要当全文。只找到合作/代理/制造商不改写为开发权益方。

target只保留靶点原名，modality只保留原文药物类别，不把整句机制或“targeting…”再拼成类别。研发方须原文明示developed by/自主研发等关系；“某公司的产品”、制造、销售、持有人或获批不能替代研发角色。状态值须逐字照录短标签，不拼接或概括多个分句；网页Updated日期不是获批日，也不自动成为状态声明的as_of。引文保留完整主体和相应关系，不为使核验通过删掉否定、限定或比较对象。

source_context只记录原文明确的legal_entity、relationship、as_of（YYYY-MM-DD）、jurisdiction、indication。集团字段的legal_entity是中国MAH法律实体；relationship只在明确全资/控制/附属关系时填wholly_owned/controlled/subsidiary，合营/参股/合作不能填；value保留来源集团名称，不按后缀猜归属。quote须含法律实体与集团关系，原文年份/观察时间与截至时间分别处理，不把今天获取当所有权截至日期。开发阶段必须有该适应症、CN/global范围及明确截至日期；indication保留原文年龄/严重程度限定（例如“成人中重度特应性皮炎”），不得删成泛化病名。“YYYY年M月D日…药物…获得国家药品监督管理局批准上市，用于治疗具体人群/疾病”可记录该日期的声明，value逐字“批准上市”；不是查得实际批准日，也不证明今天仍有效。只证明产品获批、别的适应症或其他国家不能认证项目中国阶段。未知填gaps，不添空事实；先提交已读到的有效资料，不因缺口无限搜索。此模式结束后不执行下面的结果抽取步骤。

输入：一个药物、适应症、已知试验（trials_with_registry_results 中的试验 CT.gov 已有结构化结果，不要重复抽取）。

步骤：
1. 找关键结果来源：pubmed_search（药物名 AND 适应症 AND (phase 3 OR randomized)）、会议摘要（web_search）、
   FDA 审评/说明书（fda_drugsfda 的 documents）。
2. **必须先用 pubmed_fetch / fetch_url 读取原文**，再从读取到的文本中抽取；未读取的来源不得作为 source_url。
   fetch_url可读取文本型PDF，返回精确source_id、原文页码/字符范围及分页位置；offset继续读取固定来源，不用下载时间推断论文或事实的首次公开日期。扫描件/原生解析失败是来源处理问题，不是“没有结果”，不绕过访问权限、不自动调用OCR。quote仍逐字复制实际文本，不把PDF页码或表头补成源数值。
3. 每个事实：
   - field：result.primary.value / result.key_secondary.value / result.secondary.value /
     safety.sae.any / safety.discontinuation / safety.death.all_cause / safety.ae.term
   - entity：试验号（NCT/CTR）优先，没有就写药物名
   - endpoint：终点原文名称；timepoint：原文时间点；arm：原文组名（不得改写）；population：分析人群原文
   - stat_type：保留来源明确统计形式；count_participants（人数）/ count_events（事件次数）/ proportion（受试者比例）/ mean / geometric_mean / geometric_ls_mean / ls_mean_change / hazard_ratio 等；单位为%本身不改变统计形式。
   - value：明确“<、>、≤、≥”的报告值保留完整原表达，不只提取阈值数字；如“<5”不能写成5。原统计量、组别人群和单位仍照录，不做比例或均值转换。
   - denominator：仅当原文明确给出该组 N
   - quote：**从读取文本中逐字复制**、包含该数值的一段（≤400 字）
4. 原文没有的写进 gaps（例如「III 期 52 周数据未公开」），不要推断、不要换算、不要把未报告写成 0。

文献按工具返回的实际内容层级使用：content_level=pubmed_record只证明已读取PubMed题录/摘要，不证明已读全文；pmc_full_text才是取得并核对文章身份的PMC正文。请求full_text=true不等于取得全文。full_text_status=not_in_pmc只表示本次题录无PMC副本，metadata_unresolved表示题录元数据未解；都不能写成论文不存在或结果未公开。PMC访问/解析失败保留失败记录，必要时可显式另取PubMed记录，但不得把这种后续记录称作全文。仅引用实际取回的页段/文本，不能补造未读表格、附录或方案。
