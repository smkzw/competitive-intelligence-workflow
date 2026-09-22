# 独立科学复核任务（报告 A · 项目 abc-v100 · PNH 竞品调研工作流 · 第 44 轮）

你是独立上下文复核者，与生产者（GLM/ZCode 主线程）无共享会话。你的结论将绑定正式回执，必须基于你自己对仓库文件的真实检查，不得臆测。

## 工作目录
当前目录即项目根 `runs/pnh-vertical/abc-v100` 所在仓库（阵发性睡眠性血红蛋白尿症竞品调研项目，合同版本 1）。

## 必读材料
1. `runs/pnh-vertical/abc-v100/state/scientific_review/A/review_request.json` — 复核请求（含全部绑定字段）
2. `runs/pnh-vertical/abc-v100/reports/A/v1/html/` — 已渲染门户
3. `runs/pnh-vertical/abc-v100/evidence/library/{a,b,c}-research-package.json` — 科学载荷

## 本轮重点（round-4 会商 12 项修复的落地验证）
上一轮你方 veto 的问题已按会商排期修复，请逐项独立复核：
- A r43 p1/p2（特定指标归入总体键）：载荷概念分布应为 any_teae≈117/generic_ae=61/discontinuation_ae=28/serious_teae_subset=7/aesi=2；"Incidence of TEAEs of Special Interest" 应入特别关注、"TEAEs Leading to Treatment Discontinuation" 应入因 AE 停药
- A r43 矩阵空态：matrix.html 任何TEAE 轴现在应有气泡（此前 0/146 类别不匹配）；空态文案若仍出现须与事实一致
- A r43 明细表：安全表事件列应显示原测量标题（measure_label），同组重复行可区分；分母缺失区分"无法归属（登记组名不一致）"与"未公开"
- A r43 组名：安全行组别解码/标注一致性
- B r57 issue-1（分面半翻译）、issue-2（-declared 影子行重复计数——渲染层应已过滤）、issue-3（监管批准两列）
- C r41 issue-1/2（安全/免疫原性终点不再写"疗效评价"——检查对应行）、issue-3（克隆大小量表）、issue-4（未译标注）、issue-5（人群柱图全1时改说明+表格）、issue-6（"签名"→"设计要素组合"）
- 通用：事实可溯源、中文原生、诚实边界（同既往轮次标准）

## 产出（必须）
写文件 `runs/pnh-vertical/abc-v100/state/scientific_review/A/verdict.json`，UTF-8 JSON：
- `schema_version`: "1.0"
- `criteria_version`, `project_id`, `contract_version`, `report_kind`, `report_version`, `report_object_id`, `candidate_snapshot_id`, `candidate_content_digest`, `gate_result_key`, `coverage_set_id`, `coverage_digest`, `source_refs`, `locators`, `review_input_digest` — **逐字段原样复制** review_request.json 中 scientific_context 的对应值
- `verdict_id`: "verdict-omp-deepseek-abc100-a-r44"
- `verdict`: "accepted" 或 "veto"
- 如 veto：必须携带 `issues` 数组（≥1 条），每条含 issue_id/severity/category/description_zh/source_version_id/fragment_ids（从 review_request.json 的 scientific_context 逐字复制）；accepted 则不得携带 issues
- 如 veto：`veto_disposition` = "recoverable" 或 "exhausted"
- `reviewer_id`: "omp-cms-router-deepseekflash-max"
- `reviewed_at`: 当前 UTC 时间（ISO-8601）；`valid_until`: reviewed_at + 30 天

## 绑定字段速查（仍以 review_request.json 为准逐字复制）
- `criteria_version`: `A_MATURITY_V1`
- `project_id`: `project_075af52cb182908485e6e705`
- `contract_version`: `1`
- `report_kind`: `A`
- `report_version`: `v1`
- `report_object_id`: `report_A`
- `candidate_snapshot_id`: `report-snapshot_734b307f9f463cc3b7278816`
- `candidate_content_digest`: `966a8f985b83956c973dfb1a162c54d76f3f4d20132e147ee4df171d85daf073`
- `gate_result_key`: `gate-evaluation_61cb44b0221b19c0c5a9ebeb`
- `coverage_set_id`: `coverage-set_70f623d90d86e88d4fdb66b3`
- `coverage_digest`: `1da7f7253d0426872665d527cb2e75326738ae5a17f8938b2096165f8ed67b07`
- `review_input_digest`: `None`

## 执行纪律（最高优先级）
- 读到此提示词后**立即直接开始执行**，不创建任务、不规划、不提问、不等待
- 完成写文件后正常退出（退出码 0）
