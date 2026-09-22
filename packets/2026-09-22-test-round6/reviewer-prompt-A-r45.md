# 独立科学复核任务（报告 A · 项目 abc-v101 · PNH · 第 45 轮）

你是独立上下文复核者，与生产者无共享会话。基于自己对仓库文件的真实检查给出结论。

## 材料
1. `runs/pnh-vertical/abc-v101/state/scientific_review/A/review_request.json`（绑定字段）
2. `runs/pnh-vertical/abc-v101/reports/A/v1/html/`（已渲染门户）
3. `runs/pnh-vertical/abc-v101/evidence/library/{a,b,c}-research-package.json`（科学载荷）

## 本轮重点（round-5 veto 项的修复验证）
- A r44：①复合测量（多方面并列标题）现判 composite_ae（复合不良事件指标），不再冒充因 AE 停药/严重 TEAE 子集——验证 discontinuation_ae 仅剩真实停药指标；②矩阵人单位行现按分子/分母派生发生率（7/7 不得显示 7%）；③安全行组别已解码；④类目上下文并入事件标签
- B r58：①基线域影子行渲染层已过滤（安全域上一轮已过）；②筛选面板英文长句/拼接串带标注
- C r42：①安全/免疫原性终点 → "安全性评价/免疫原性评价"（不再"疗效评价/其他临床疗效指标"）；②克隆大小量表列不再标"血红蛋白"；③值列英文原句带"（登记原文，未译）"标注
- 通用：事实可溯源、中文原生、诚实边界

## 产出
写 `runs/pnh-vertical/abc-v101/state/scientific_review/A/verdict.json`（UTF-8 JSON）：
- schema_version "1.0"；criteria_version/project_id/contract_version/report_kind/report_version/report_object_id/candidate_snapshot_id/candidate_content_digest/gate_result_key/coverage_set_id/coverage_digest/source_refs/locators/review_input_digest — **逐字复制** review_request.json scientific_context 对应值
- verdict_id: "verdict-omp-deepseek-abc101-a-r45"；verdict: "accepted"|"veto"
- veto 必带 issues 数组（issue_id/severity/category/description_zh/source_version_id/fragment_ids 逐字复制）；accepted 不得带 issues
- reviewer_id: "omp-cms-router-deepseekflash-max"；reviewed_at 当前 UTC；valid_until +30 天

## 绑定字段速查（以 review_request.json 为准）
- `criteria_version`: `A_MATURITY_V1`
- `project_id`: `project_5ecb89579d91348e3df116f6`
- `contract_version`: `1`
- `report_kind`: `A`
- `report_version`: `v1`
- `report_object_id`: `report_A`
- `candidate_snapshot_id`: `report-snapshot_ed9da7e6427588023e4abb6e`
- `candidate_content_digest`: `79c7dbf9c4a6af1e39a9884e7863f2db6a736dfad44a2051226bd7bdd0d4a31e`
- `gate_result_key`: `gate-evaluation_d4d6655d80f9e640e7b2033b`
- `coverage_set_id`: `coverage-set_7352263d2edd8115f8008c00`
- `coverage_digest`: `0a9c00e74636849c2106614771a472744cb128cfaa873468bdc9144c7fb986cb`
- `review_input_digest`: `None`

## 执行纪律
立即执行，不提问不等待；完成后退出码 0。
