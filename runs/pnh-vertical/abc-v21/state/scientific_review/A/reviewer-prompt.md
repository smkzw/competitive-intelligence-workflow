# 独立科学复核任务（报告 A · 项目 abc-v1 · PNH 竞品调研工作流）

你是独立上下文复核者，与生产者（GLM/ZCode 主线程）无共享会话。你的结论将绑定正式回执，必须基于你自己对仓库文件的真实检查，不得臆测。

## 工作目录
当前目录即项目根 `runs/pnh-vertical/abc-v1` 的绝对路径仓库（阵发性睡眠性血红蛋白尿症竞品调研项目，合同版本 1）。

## 必读材料
1. `state/scientific_review/A/review_request.json` — 复核请求（含全部绑定字段）
2. `reports/A/v1/html/` — 已渲染门户（overview.html 等，可用浏览器或直接读 HTML）
3. `evidence/library/{r}-research-package.json`（r = a/b/c，对应你的报告类型）— 科学载荷：事实、来源、声明、独立复核签发
4. `reports/A/v1/html.manifest.json` — 渲染清单

## 复核要点（科学性与诚实性）
- 事实可溯源：门户展示的产品/试验/结果是否回到 CT.gov 登记来源（source_id=ctgov-pnh-page-1/2，抽查 ≥3 项）
- 中文原生：用户可见文案为中文，无工程术语/内部状态名泄漏
- 诚实边界：证据不足处是否显式声明（如"暂无公开记录""未公开披露"），有无空图表墙/占位符/虚构数值
- 声明绑定：claims 的 fact_ids 是否指向包内事实
- 已知限制确认：B 报告宇宙为 6 项基线完整试验（complete_set 策略）；中国路线访问受阻（G7-2）如实记档——这些是合同允许的诚实边界，不构成否决理由

## 产出（必须）
写文件 `state/scientific_review/A/verdict.json`，UTF-8 JSON，结构如下：
- `schema_version`: "1.0"
- `criteria_version`, `project_id`, `contract_version`, `report_kind`, `report_version`, `report_object_id`, `candidate_snapshot_id`, `candidate_content_digest`, `gate_result_key`, `coverage_set_id`, `coverage_digest`, `source_refs`, `locators`, `review_input_digest` — **逐字段原样复制** review_request.json 中 production/scientific_context/request 的对应值（source_refs、locators 用 scientific_context 里的）
- `verdict_id`: "verdict-omp-gemini38-abc21-a-a"
- `verdict`: "accepted" 或 "veto"（依据你的真实复核结论）
- **如 veto**：必须额外携带 `issues` 数组（至少 1 条阻断问题），每条结构：
  `{"issue_id": "issue-<编号>", "severity": "blocking", "category": "<类别如 科学语义/单位口径/事实可溯源>",
    "description_zh": "<中文描述：门户呈现 vs 登记来源的差异及位置>",
    "source_version_id": "<从 review_request.json 的 scientific_context.source_refs[0].source_version_id 逐字复制>",
    "fragment_ids": ["<从 review_request.json 的 scientific_context.locators[].fragment_id 逐字复制>"]}`
  没有 issues 的 veto 无法签发；如结论是 accepted 则不得携带 issues 与 veto_disposition
- 如 veto：`veto_disposition` = "recoverable" 或 "exhausted"
- `reviewer_id`: "omp-google-antigravity-gemini38flash-high"
- `reviewed_at`: 当前 UTC 时间（ISO-8601）
- `valid_until`: reviewed_at + 30 天

## 约束
- 除上述 verdict.json 外不得修改任何文件
- 结论必须真实：抽查后若发现问题，如实 veto 并在心中记下理由（回执链会拒绝空泛结论）
- 完成后正常退出（退出码 0）
