# Task 10.3 无损暂停检查点（2026-09-02）

## 当前状态

- 状态：已无损暂停，Task 10.3 尚未完成或关闭。
- 本轮范围：站点式 HTML 与三宿主全矩阵预演；未开展 PDF、HTML-PPT 或 PPTX 构建。
- 临时 HTTP 服务已正常停止，ego(lite) 任务空间 24 已关闭；候选包、安装根、报告、截图、回执、运行记录和审评报告均保留。

## 已完成并保留的实现

- `src/ci_workflow/application/acceptance_runner.py`
- `tools/run_acceptance.py`
- `tests/acceptance/test_full_matrix.py`
- `tests/acceptance/test_legacy_negative_regressions.py`
- Task 10.3 的 PRD/设计已统一为 ego(lite) 浏览器验收，覆盖 1024、1280、1440、1920 四档宽度。
- `uv run python tools/run_acceptance.py --suite full` 已通过：`SUITE_REHEARSAL_RECEIPTS_OK cases=23 rehearsed=16 future_owner=2 not_applicable=1 outside_suite=4 formats=1 release_cases_closed=0`。
- 验收相关测试 89 项通过，acceptance runner、CLI、host smoke 的 Ruff/Mypy 检查通过。

## 当前候选与运行锚点

- 候选根：`/Users/smkzw/Documents/AI Products/competitive-intelligence-acceptance/task-10.3-20260902-r13j`
- 候选包：`dist/competitive-intelligence-workflow.tar.zst`
- SHA-256：`740882274b151e04075627535f12fc92a69609c26457369690cf4eeaa6294e10`
- 文件数：417；已验证并安装至 `candidate-install/`。
- 全矩阵项目：`project/`
- 运行标识：`run_1677d25996abae1cbabb0478`
- 预发布预演标识：`pre-rc-run_abc58f6466b8f43ff7d0d743`
- 全流程结果：`PRE_RC_REHEARSAL_OK reports=3 formats=1 hosts=3 cases=23 rehearsed=16 future_owner=2 not_applicable=1 outside_suite=4 release_cases_closed=0 pre_rc_run_id=pre-rc-run_abc58f6466b8f43ff7d0d743`
- Codex、Hermes、OMP 三宿主均以独立真实会话、进程和运行完成 smoke，并绑定同一候选包摘要。

## ego(lite) 用户视角证据

- A/B/C 共 57 条路由均已在 1024×768、1280×800、1440×900、1920×1080 实际打开检查。
- 结果：标题、主内容、Logo 正常；破图 0；页面整体无横向溢出；未发现面向用户可见的内部工程标签。
- A 报告气泡交互：点击后药物详情抽屉可打开，并显示泰瑞奇单抗疗效、安全性与产品概览内容。
- B 报告总览筛选交互通过。
- C 报告设计矩阵筛选通过：选择一个产品后，69 行收敛为 12 行；按产品筛选时非匹配试验列的计算样式为 `display:none`。
- 截图：`ego-a-overview.png`、`ego-b-overview.png`、`ego-c-design-map.png`。
- 浏览器回执：`project/verification/{A,B,C}/v-fixture-001/ego-receipt.json`。

## 独立视觉审评状态

- 正式审评包：`ci-phase10-task103-r13j-visual-review`
- 上下文：`context/ci-phase10-task103-r13j-visual-review_conference_context.md`
- 审评目录：`runs/conference/ci-phase10-task103-r13j-visual-review/`
- Gemini 3.7 Flash（同一既有会话 `01a05dc8-4250-7000-8fe2-3f702caad1d2`）：A/B/C 通过，仅提示 C 页吸顶表头高度 P2。
- ZCode GLM-5.3-Flash（同一既有会话 `sess_ed57a277-45bb-468d-9a56-0e86956c4c3a`）：更正复核已完成，撤销 C 筛选 P1；整体放行，保留 B 基线四页内容重复、完成情况标题词序不一致两项 P2。报告：`named_zcode_followup.md`。
- MiniMax-M3（同一既有会话 `01a05dc8-4671-7000-a63a-64be418f32b6`）：首轮结论混入旧适应症和与已批准口径冲突的判断；更正提示已写入 `prompts/conference/ci-phase10-task103-r13j-visual-review/named_minimax_correction.md`，尚未在原会话执行。

## 保留的恢复信息

- 早先误装的 Playwright 浏览器缓存已可恢复地移至 `~/.Trash/ci-task103-playwright-cache-20260902/`；未清空废纸篓。
- 未删除 Task 10.2/R12、R13j 候选、宿主回执、ego(lite) 回执、截图或审评记录。
- 当前代码树含用户及既有未提交改动；恢复时不得覆盖或重置。

## 下一安全动作

1. 在 MiniMax 的原会话 `01a05dc8-4671-7000-a63a-64be418f32b6` 执行既有更正提示，不新建会话、不替换模型。
2. 综合 Gemini、ZCode 更正版和 MiniMax 更正版，仅处理有实际页面证据支持的问题；不得补造未公开临床数据。
3. 优先判断并处理 B 报告四个基线页面可见内容重复和完成情况标题词序不一致两项 P2。
4. 若修改代码，必须生成全新候选并重新完成 ego(lite) 四宽度检查、三类交互检查、全矩阵预演和三宿主 smoke；不得覆盖 R13j。
5. 若无需修改，完成正式审评结论、治理审计、Trellis 收口后，才可判断 Task 10.3 是否完成。

