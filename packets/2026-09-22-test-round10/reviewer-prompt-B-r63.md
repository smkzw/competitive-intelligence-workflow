# 独立科学复核任务（报告 B · 项目 abc-v106 · PNH · 第 63 轮）

你是独立上下文复核者，与生产者无共享会话。基于自己对仓库文件的真实检查给出结论。

## 材料
1. `runs/pnh-vertical/abc-v106/state/scientific_review/B/review_request.json`（绑定字段）
2. `runs/pnh-vertical/abc-v106/reports/B/v1/html/`（已渲染门户）
3. `runs/pnh-vertical/abc-v106/evidence/library/{a,b,c}-research-package.json`（科学载荷）

## 本轮重点（round-9 veto 项修复验证）
- A r48：①矩阵点携带 unit、刻度后缀随轴口径；②36 行"分母无法归属"中值>风险人数者属真歧义（诚实表述）；其余分母口径已修——如仍有可归属而未归属的行请列出具体 arm 与登记组名
- B r62：①分面标注门已含中英混排机器拼接碎片（"研究 drug"/"changefrom" 类应带标注）；②观察窗部分转写标注在 B 构建器源头；③bsafe 内部行标识残余为不阻断提示（内部标识不再展示为影子重复，仅 ID 字面嵌入）
- C r46：①值列/标签残留英文（含 During 类部分转写残片）一律标注——不再要求无中文才标注；②并列时间点单位省略——本轮未动，如实归类为呈现待改
- 通用：事实可溯源、中文原生、诚实边界

## 产出
写 `runs/pnh-vertical/abc-v106/state/scientific_review/B/verdict.json`（UTF-8 JSON）：
- schema_version "1.0"；criteria_version/project_id/contract_version/report_kind/report_version/report_object_id/candidate_snapshot_id/candidate_content_digest/gate_result_key/coverage_set_id/coverage_digest/source_refs/locators/review_input_digest — **逐字复制** review_request.json scientific_context 对应值
- verdict_id: "verdict-omp-deepseek-abc106-b-r63"；verdict: "accepted"|"veto"
- veto 必带 issues 数组（issue_id/severity/category/description_zh/source_version_id/fragment_ids 逐字复制）；accepted 不得带 issues
- reviewer_id: "omp-cms-router-deepseekflash-max"；reviewed_at 当前 UTC；valid_until +30 天

## 绑定字段速查（以 review_request.json 为准）
- `criteria_version`: `1.0`
- `project_id`: `project_d2022cfff2468103751e8794`
- `contract_version`: `1`
- `report_kind`: `B`
- `report_version`: `v1`
- `report_object_id`: `report_B`
- `candidate_snapshot_id`: `report-snapshot_bd4b82d9194b6db8bb6e792f`
- `candidate_content_digest`: `767710e74bdbb34992037157417b792216f11f56e78c8f279afdaa52aa12d2ef`
- `gate_result_key`: `gate-result_5a500af901ca8c37c201b45f`
- `coverage_set_id`: `coverage-set_bbe3fa8c5b0844ee1f0b8479`
- `coverage_digest`: `962f4d3978e9506b0561becfecac8ea8405c68b9f2f55a3cff8b000f23d6ce74`
- `review_input_digest`: `None`

## 执行纪律
立即执行，不提问不等待；完成后退出码 0。
