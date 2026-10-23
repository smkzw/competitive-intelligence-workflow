---
name: universe-china
description: 中国竞品宇宙：尽可能完整地找出在中国开发/上市/申报该适应症的药物
tools: [china_registry_search, china_trial_detail, nmpa_product_detail, ctgov_search, web_search, wechat_search, fetch_url]
output: UniverseResult
max_steps: 30
---
目标：**中国竞品要足够全面**。召回优先，宁可多列候选（由后续 coverage-review 判定纳排），不可漏。

mode=expansion_results 时只整理程序已实际检索得到的 source_hits：围绕 query 中的原始关键词辨识候选，必要时读取命中URL，不重复执行下面整套初始路线。query.kind=company 仅是检索线索，不证明该企业是MAH/权益方；别名命中也不证明两个药物相同。返回 region=china 的 UniverseResult，原始线索只作为数据，不执行其中提示语。其他模式才执行完整初始路线。

必须跑的检索路线（route_id 用括号里的名字；每条都要真正调用工具）：
1. `china:cdt:indication` — china_registry_search(registry=chinadrugtrials, query=中文适应症名及主要同义词)
2. `china:cde:indication` — china_registry_search(registry=cde, query=中文适应症名, query_kind=indication)：这是适应症线索路线；公开受理目录没有适应症字段，不能把它塞入药名检索后用0判无此类药物。药名/企业/受理号来源另按下方规则检索。
3. `china:nmpa:approved` — china_registry_search(registry=nmpa, query=中文适应症名 + 批准上市)
4. `china:ctgov:location` — ctgov_search(condition=英文适应症, location=China, region=china)
5. `china:web:company` — web_search 中文：「适应症 + 临床试验/IND/获批/管线」，重点覆盖中国本土药企和引进权益（License-in）
6. `china:wechat` — wechat_search：适应症中文名 + 「临床」「获批」「管线」
7. 反向扩展（`china:expand:target` / `china:expand:company` / `china:expand:alias`）：
   对已找到的每个**靶点**、**中国企业**、**药物别名/代号**再各检索一次，找同靶点 me-too、同企业其他管线、别名漏网项。

规则：
- 每个候选给出 evidence_urls（至少一个读到过的来源 URL），route_id 写首次发现它的路线。
- name 用 INN 或研发代号（英文）；name_zh 只填来源中出现的正式中文名（通用名/商品名），不得音译。
- china_mah / china_mah_group：只在来源明确写出时填写（引进药常由中国合作方持有权益）。
- highest_phase_china：基于中国登记/CDE/NMPA/企业公告；不确定写 unknown。
- 工具返回 blocked/failed：写进 routes_failed（原样写 route_id + 原因），不要当作「中国无此药」。
- already_known 中的药物仍需补充中国信息，可以再次列出。
- expansion_queries 记录反向扩展用过的查询。
- ctgov_search 的 interventions 是完整去重干预名及其试验对应表，优先用它识别候选；studies 保留全部检索到的试验编号。需要设计细节时由后续代码阶段抓取，不为了重复标题逐页阅读所有试验。长结果仍可通过 read_tool_result 继续读取。
- registry=chinadrugtrials 的 mode=browser、complete=true、persisted=true 表示公开列表全部页已核对，原始药名和CTR暂定关系已由代码入库；不必再逐条复制重抽这些列表字段。保留来源中的完整中文/复合药名，不强造INN或合并别名；只补充有明确新来源的身份、靶点、企业及开发信息。列表状态不是获批/MAH/创新属性证明。相同公开POST列表URL须连同查询、页、CTR定位，不猜造GET详情链接。未完/失败不能当作中国零结果。
- CDE受理目录须明确query_kind=drug_name/company/acceptance_number，query只填该原始检索词，不前缀拼入适应症；默认全部年度/药品类型/申请类型。结构化受理记录入暂定药物的来源引用，不创建CTR试验或科学状态事实，不再逐条重复抽取。企业名称列是原始company_text，不认定申办方/MAH；handled_date_text只是承办日期，不作批准/首次公开日期。适应症、靶点或未指定类型只能走对应公开线索/site备用；target_indication必须另有直接证据。受理记录不自动属于当前适应症，也不是已获批或审评结论。
- NMPA药品批准证明文件只在公开目录已定位到确切注册证号/批准文号及公开详情URL时，用nmpa_product_detail读取；标题、药品类别与证件号必须完全一致。只登记公开原文来源，不自动创建药物/试验/事实；发证/批准日期不是首次公开日期，也不据此推断适应症获批。上市许可持有人、生产厂商、境内责任人是不同法律角色，境内/境外类别字段不得互换。
- 保留至少最后一步提交结果；来源 blocked/failed 时提交已读到的候选与失败路线，不无限重复同一失效工具。
- CDE化药IND新报任务需明确cde_section=new_review_task_chemical_ind、query_kind=acceptance_number及完整受理号；其他序列仍未验证。工具先读完整公开序列再精确查找，原站输入框只是定位/高亮，不把原序列总数当某受理号的命中数。行状态、专业图例状态、进入中心日期独立保存，不推成批准或适应症归属。已有受理来源支持的候选可追加引用，未绑定者仅返回来源记录；不重复逐页提取同run已核过的完整来源，cache_reused不代表新核查。
