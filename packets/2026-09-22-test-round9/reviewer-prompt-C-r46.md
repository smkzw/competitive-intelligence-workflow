# 独立科学复核任务（报告 C · 项目 abc-v105 · PNH · 第 46 轮）

你是独立上下文复核者，与生产者无共享会话。基于自己对仓库文件的真实检查给出结论。

## 材料
1. `runs/pnh-vertical/abc-v105/state/scientific_review/C/review_request.json`（绑定字段）
2. `runs/pnh-vertical/abc-v105/reports/C/v1/html/`（已渲染门户）
3. `runs/pnh-vertical/abc-v105/evidence/library/{a,b,c}-research-package.json`（科学载荷）

## 本轮重点（round-8 veto 项修复验证）
- A r47：①composite_ae 分母口径修复——56 行复合指标全部获得 atRisk 分母（此前 0）；②矩阵刻度后缀随轴口径；③筛选维度组名残留英文标注；④残余 ~12 行值>风险人数属真歧义，"分母无法归属"为诚实表述；⑤载荷内嵌复核声明悖论仍待裁决，不作 veto 依据
- B r61：①影子行清洗扩展到 legacy 顶层列表（report.js 嵌入数据应无 bsafe-*-declared）；②观察窗部分转写残留英文在 B 构建器源头标注
- C：r45 已 accepted；本轮快照更新做一致性确认
- 通用：事实可溯源、中文原生、诚实边界

## 产出
写 `runs/pnh-vertical/abc-v105/state/scientific_review/C/verdict.json`（UTF-8 JSON）：
- schema_version "1.0"；criteria_version/project_id/contract_version/report_kind/report_version/report_object_id/candidate_snapshot_id/candidate_content_digest/gate_result_key/coverage_set_id/coverage_digest/source_refs/locators/review_input_digest — **逐字复制** review_request.json scientific_context 对应值
- verdict_id: "verdict-omp-deepseek-abc105-c-r46"；verdict: "accepted"|"veto"
- veto 必带 issues 数组（issue_id/severity/category/description_zh/source_version_id/fragment_ids 逐字复制）；accepted 不得带 issues
- reviewer_id: "omp-cms-router-deepseekflash-max"；reviewed_at 当前 UTC；valid_until +30 天

## 绑定字段速查（以 review_request.json 为准）
- `criteria_version`: `1.0`
- `project_id`: `project_a6b1a92b4354558d980bd253`
- `contract_version`: `1`
- `report_kind`: `C`
- `report_version`: `v1`
- `report_object_id`: `report_C`
- `candidate_snapshot_id`: `report-snapshot_b53a83cdf6a929b5a70df04c`
- `candidate_content_digest`: `ff65145b9e8117d4722a8c4c12a3eb4f47f4ec0ae781f934164ad85b6138fa83`
- `gate_result_key`: `gate-result_93760bba54b31663dda14b97`
- `coverage_set_id`: `coverage-set_a9c654c34ac44ed257d1d4af`
- `coverage_digest`: `ca32cd23d937db6f272edfb4b8b5a8059140ab7b3afcbd72537c25d5fcb767b1`
- `review_input_digest`: `None`

## 执行纪律
立即执行，不提问不等待；完成后退出码 0。
