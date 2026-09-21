# 独立视觉验收审阅任务（报告 C · abc-v64 · HTML 门户）

你是独立上下文视觉审阅者（身份 omp-cms-router-deepseekflash-max），与生产者（zcode-main-thread-glm53）相互独立。你的结论将以你的身份签署进正式视觉验收记录，必须基于你自己对渲染页面的真实检查。

## 工作目录（必须在此目录内操作）
`/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`（仓库根）。
被验收站点（绝对路径）：`/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/runs/pnh-vertical/abc-v64/reports/C/v1/html`

## 材料（均相对项目根）
1. `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/packets/2026-09-18-omp-visual/visual-plan-c.json` — 视觉策划书（七验收域判据在 acceptance_matrix）
2. `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/packets/2026-09-18-omp-visual/render-evidence-c.json` — 真实呈现证据（30 个呈现目标：Chromium/WebKit × 5 视口 × 3 代表页，每目标含真实交互探测与截图路径）
3. `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/runs/pnh-vertical/abc-v64/reports/C/v1/html/` — 被验收站点（截图在 `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/packets/2026-09-18-omp-visual/screenshots/`）
4. 截图可自行用浏览器或读图复核；至少亲自检查 3 个页面（可结合读 HTML）

## 审阅域（七域，逐域独立判断）
copy_zh / hierarchy_density / typography_spacing / color_legibility / charts_tables / interaction_consistency / format_rendering

逐域对照策划书判据抽查：中文原生与诚实空态、层级密度、字号间距、颜色令牌与对比度、图表表格同源与单位口径、六类交互一致性、双引擎渲染一致性。若发现域内任一判据不成立，该域 status = "rejected"。

## 产出（必须）
写文件 `packets/2026-09-18-omp-visual/visual-verdict-c.json`，UTF-8 JSON：
```json
{
  "schema_version": "1.0",
  "verdict_id": "verdict-omp-deepseek-vis-abc64-c",
  "format": "html",
  "visual_plan_digest": "9ad43f4b9680a539df77ccb2902ff2e1d1fb2bcd9f886b1667f223229af81d02",
  "candidate_artifact_digest": "3f2f5e39d48d2cd9e8bd46179ada6da0468d20ac5d16fd2eb40b37a42061d91f",
  "render_evidence_digest": "8a59d561e0ed022df374bc6f5e9fefc7b7fb3ba296861897b59d5258e0ee2231",
  "producer_identity": "zcode-main-thread-glm53",
  "verifier_identity": "omp-cms-router-deepseekflash-max",
  "verdict": "accepted 或 rejected",
  "domains": [
    {"domain": "copy_zh", "status": "accepted 或 rejected",
     "criteria": ["<逐条复制策划书该域判据原文>"],
     "evidence_refs": ["<你自己检查过的具体页面/截图/证据目标路径，至少 2 条>"]}
    , ... 七域全部
  ],
  "created_at": "<当前 UTC 时间 ISO-8601>"
}
```
- 三个 digest 与 producer_identity 必须逐字复制上方给定值（摘要绑定由正式流程复核）
- criteria 数组逐字复制策划书该域的判据原文
- verdict 总体与逐域必须一致（accepted 当且仅当七域全 accepted）
- 只写上述字段，禁止添加任何其他字段

## 约束
- 除 verdict JSON 外不得修改任何文件
- 结论必须真实：不通过就 rejected，不要迁就
- 完成后正常退出（退出码 0）


## 执行纪律（最高优先级）
- 读到此提示词后**立即直接开始执行**：不要创建 Trellis 任务，不要进入规划模式，
  不要提出任何确认问题或等待任何回复——本任务没有交互确认环节。
- 所有歧义自行决策。完成后写规定的 verdict/verdict JSON 并正常退出（退出码 0）。
