# 独立科学复核任务（报告 B · 项目 abc-v97 · PNH 竞品调研工作流 · 第 57 轮）

你是独立上下文复核者，与生产者（GLM/ZCode 主线程）无共享会话。你的结论将绑定正式回执，必须基于你自己对仓库文件的真实检查，不得臆测。

## 工作目录
当前目录即项目根 `runs/pnh-vertical/abc-v97` 所在仓库（阵发性睡眠性血红蛋白尿症竞品调研项目，合同版本 1）。

## 必读材料
1. `runs/pnh-vertical/abc-v97/state/scientific_review/B/review_request.json` — 复核请求（含全部绑定字段）
2. `runs/pnh-vertical/abc-v97/reports/B/v1/html/` — 已渲染门户（真实打开 HTML 或浏览器检查）
3. `runs/pnh-vertical/abc-v97/evidence/library/{a,b,c}-research-package.json` — 科学载荷
4. `runs/pnh-vertical/abc-v97/reports/B/v1/html.manifest.json` — 渲染清单

## 本轮重点（GPT Pro 审阅纠偏后的验证轨）
本轮（v97）刚落地 8 项数据不变量修复，请**独立验证**以下各项在真实数据与页面中的表现，不以生产者自述为准：
- 安全性概念诚实分类：generic AE（如 "Number of participants with adverse events"）不得标为"治疗期间不良事件"；Non-serious 不得标为"严重不良事件"；因 AE 停药等特定指标独立成类
- 分母成对与未知分母：人单位计数行是否带 atRisk 分母；期别不明/冲突处是否诚实留空（不得借用）
- 终点实例配对：多条主要终点各自有独立时间点（如 NCT03181633 的 9 条主终点），不得只有第一条有时间
- 未知样本量试验保留：5 项样本量未知试验应显示"未公开"而非被删除
- 登记状态与监管批准分列：eculizumab 应显示"监管批准事实：待核验"
- 中文原生与诚实边界（同既往轮次标准）

## 产出（必须）
写文件 `runs/pnh-vertical/abc-v97/state/scientific_review/B/verdict.json`，UTF-8 JSON：
- `schema_version`: "1.0"
- `criteria_version`, `project_id`, `contract_version`, `report_kind`, `report_version`, `report_object_id`, `candidate_snapshot_id`, `candidate_content_digest`, `gate_result_key`, `coverage_set_id`, `coverage_digest`, `source_refs`, `locators`, `review_input_digest` — **逐字段原样复制** review_request.json 中 scientific_context 的对应值
- `verdict_id`: "verdict-omp-deepseek-abc97-b-r57"
- `verdict`: "accepted" 或 "veto"
- 如 veto：必须携带 `issues` 数组（≥1 条），每条含 issue_id/severity/category/description_zh/source_version_id/fragment_ids（source_version_id 与 fragment_ids 从 review_request.json 的 scientific_context 逐字复制）；accepted 则不得携带 issues
- 如 veto：`veto_disposition` = "recoverable" 或 "exhausted"
- `reviewer_id`: "omp-cms-router-deepseekflash-max"
- `reviewed_at`: 当前 UTC 时间（ISO-8601）；`valid_until`: reviewed_at + 30 天

## 绑定字段速查（仍以 review_request.json 为准逐字复制）
- `criteria_version`: `1.0`
- `project_id`: `project_edfe6af31f668b99b2d5c450`
- `contract_version`: `1`
- `report_kind`: `B`
- `report_version`: `v1`
- `report_object_id`: `report_B`
- `candidate_snapshot_id`: `report-snapshot_36eb1f66397a5fdeb4521406`
- `candidate_content_digest`: `21574eac980e10c1e28b1237dc9a01f5d24135af546b55344aaeda06abc282e6`
- `gate_result_key`: `gate-result_9940a728aa3427ff2dc088c3`
- `coverage_set_id`: `coverage-set_2bbfd5215af8cfcffbaa1fe5`
- `coverage_digest`: `2f87770e3a484c8e1ed8782011345108f9c3d2122a2a2d2d6ddbb5bce8326eb1`
- `review_input_digest`: `None`

## 执行纪律（最高优先级）
- 读到此提示词后**立即直接开始执行**，不创建任务、不规划、不提问、不等待
- 所有歧义自行决策并记录在 verdict 备注外的 assumptions（如有）
- 完成写文件后正常退出（退出码 0）
