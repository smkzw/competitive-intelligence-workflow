# 独立科学复核任务（报告 A · 项目 abc-v97 · PNH 竞品调研工作流 · 第 43 轮）

你是独立上下文复核者，与生产者（GLM/ZCode 主线程）无共享会话。你的结论将绑定正式回执，必须基于你自己对仓库文件的真实检查，不得臆测。

## 工作目录
当前目录即项目根 `runs/pnh-vertical/abc-v97` 所在仓库（阵发性睡眠性血红蛋白尿症竞品调研项目，合同版本 1）。

## 必读材料
1. `runs/pnh-vertical/abc-v97/state/scientific_review/A/review_request.json` — 复核请求（含全部绑定字段）
2. `runs/pnh-vertical/abc-v97/reports/A/v1/html/` — 已渲染门户（真实打开 HTML 或浏览器检查）
3. `runs/pnh-vertical/abc-v97/evidence/library/{a,b,c}-research-package.json` — 科学载荷
4. `runs/pnh-vertical/abc-v97/reports/A/v1/html.manifest.json` — 渲染清单

## 本轮重点（GPT Pro 审阅纠偏后的验证轨）
本轮（v97）刚落地 8 项数据不变量修复，请**独立验证**以下各项在真实数据与页面中的表现，不以生产者自述为准：
- 安全性概念诚实分类：generic AE（如 "Number of participants with adverse events"）不得标为"治疗期间不良事件"；Non-serious 不得标为"严重不良事件"；因 AE 停药等特定指标独立成类
- 分母成对与未知分母：人单位计数行是否带 atRisk 分母；期别不明/冲突处是否诚实留空（不得借用）
- 终点实例配对：多条主要终点各自有独立时间点（如 NCT03181633 的 9 条主终点），不得只有第一条有时间
- 未知样本量试验保留：5 项样本量未知试验应显示"未公开"而非被删除
- 登记状态与监管批准分列：eculizumab 应显示"监管批准事实：待核验"
- 中文原生与诚实边界（同既往轮次标准）

## 产出（必须）
写文件 `runs/pnh-vertical/abc-v97/state/scientific_review/A/verdict.json`，UTF-8 JSON：
- `schema_version`: "1.0"
- `criteria_version`, `project_id`, `contract_version`, `report_kind`, `report_version`, `report_object_id`, `candidate_snapshot_id`, `candidate_content_digest`, `gate_result_key`, `coverage_set_id`, `coverage_digest`, `source_refs`, `locators`, `review_input_digest` — **逐字段原样复制** review_request.json 中 scientific_context 的对应值
- `verdict_id`: "verdict-omp-deepseek-abc97-a-r43"
- `verdict`: "accepted" 或 "veto"
- 如 veto：必须携带 `issues` 数组（≥1 条），每条含 issue_id/severity/category/description_zh/source_version_id/fragment_ids（source_version_id 与 fragment_ids 从 review_request.json 的 scientific_context 逐字复制）；accepted 则不得携带 issues
- 如 veto：`veto_disposition` = "recoverable" 或 "exhausted"
- `reviewer_id`: "omp-cms-router-deepseekflash-max"
- `reviewed_at`: 当前 UTC 时间（ISO-8601）；`valid_until`: reviewed_at + 30 天

## 绑定字段速查（仍以 review_request.json 为准逐字复制）
- `criteria_version`: `A_MATURITY_V1`
- `project_id`: `project_edfe6af31f668b99b2d5c450`
- `contract_version`: `1`
- `report_kind`: `A`
- `report_version`: `v1`
- `report_object_id`: `report_A`
- `candidate_snapshot_id`: `report-snapshot_6cb63438e505a9710fbb4e3a`
- `candidate_content_digest`: `65699dc1214a766d205d1531d7c0eebdac502e01ae9905d96055d074bed933ce`
- `gate_result_key`: `gate-evaluation_8ca3230f01d96cf2cd152652`
- `coverage_set_id`: `coverage-set_8a5574cff714cd2495d43bb4`
- `coverage_digest`: `be7a14ccf9081b7d2273539d0e57f5d045d777375e930e22349cec185eedef50`
- `review_input_digest`: `None`

## 执行纪律（最高优先级）
- 读到此提示词后**立即直接开始执行**，不创建任务、不规划、不提问、不等待
- 所有歧义自行决策并记录在 verdict 备注外的 assumptions（如有）
- 完成写文件后正常退出（退出码 0）
