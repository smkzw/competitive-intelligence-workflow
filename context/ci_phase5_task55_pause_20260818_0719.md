# Task 5.5 无损暂停记录

暂停时间：2026-08-18 07:19 CST  
暂停原因：用户要求立即无损暂停。  
恢复边界：继续 Task 5.5 收口；不得进入 Phase 6。

## 当前锚点

- 当前提交：`58a4a267cf4c66385d2e4ba07e2f5dff05814036`（`fix: close report A medical-manager review`）。
- 当前工作树包含尚未提交的矩阵可见性修正、相关测试修正和 Task 5.5 过程记录；`git diff --check` 通过。
- 已生成的 fresh A 产物仍是修改前版本：`.artifacts/a-fresh-source`。其清单绑定提交 `58a4a26`，因此在当前未提交代码重新生成前，不能视为最新工作树的验收产物。
- Phase 6 未开始，旧工程未改、未删。

## 本次暂停前刚完成的修正

- 将疗效—安全性矩阵的覆盖说明移到图表之前，明确区分“筛选范围”与“实际绘入”。
- 当前三维数据不足时，页面会显示“本图绘入 X 个产品；另有 Y 个因当前三维数据未完整公开而未绘入”，并可展开未绘入名单。
- 将矩阵口径说明移到图表右上，避免与横轴刻度重叠。
- 将筛选摘要从“当前显示全部”改为“筛选范围：全部/已选择”，避免误读为全部产品均已绘图。
- 1280px 响应式导航下，全局搜索需先打开“菜单”；已修正 `test_portal_runtime.py` 中一条旧测试的操作路径。

## 已通过的检查

- 矩阵定向浏览器测试：`4 passed in 4.62s`。
- Phase 5 总门：`200 passed in 30.44s`。
- Ruff：通过。
- strict mypy：通过（92 个源文件）。
- Minimax 独立真实医学经理复核：`ACCEPTED`，报告位于 `runs/conference/ci_phase5_task55_visual/visual_minimax_medical_manager.md`。
- 科学独立复核：两位复核者均无 P0/P1；报告位于 `runs/conference/ci_phase5_task55_science/`。

## 未完成与已知失败

- Grok 对修改前产物给出 `REJECTED`，唯一 P1 是矩阵未在首屏说明其余产品为何未绘入；代码已修，但尚未重新生成产物并在同一 Grok 会话复核。
- 全工程 `uv run pytest -q` 应用户指令中断，停止时结果为 `18 failed, 909 passed in 649.36s`，未跑完 1448 项。
- 已观察到的 18 项失败主要来自 1320px 响应式断点后的旧测试假设：测试在 1280px 直接操作已折叠的搜索、分组导航或焦点控件，没有先打开菜单。相关文件集中在：
  - `tests/browser/test_evidence_drawer.py`
  - `tests/browser/test_portal_shell.py`
- 另有两个独立信号需要恢复后查清：
  - `test_packaged_assets_match_repo_and_official_logo`：项目内打包设计资产与当前源资产不一致。
  - `test_static_server_and_file_protocol`：1280px 下 `.portal-page-title` 高度 36px、文字 scrollHeight 38px，存在 2px 纵向裁切。
- 不得把这些失败简单全部改测试；恢复后先判断 1280px 的真实用户交互是否应保留菜单折叠，再统一更新测试或修正应用行为。

## 恢复后的唯一安全顺序

1. 读取本文件、`context/ci_phase5_task55_context.md` 和 `.trellis/tasks/08-14-phase-5-report-a/implement.md`，检查 `git status`，不要重做已完成的来源研究。
2. 逐类复现并处理上述 18 项全工程失败；先修真实 2px 裁切和资产漂移，再统一处理 1280px 折叠菜单测试路径。
3. 重跑 Phase 5 总门、Ruff、strict mypy 和完整 1448 项回归。
4. 将当前修改提交后，重新生成 `.artifacts/a-fresh-source`，确保 run/snapshot/manifest/site digest/mtime 绑定新提交。
5. 重跑 50 路由 × Chromium/WebKit × 1280/1440/1920；把新矩阵截图交给原 Grok 会话做同会话复核。
6. 只有两位视觉复核者无 P0/P1、全工程回归通过、清单绑定当前提交后，才能写 `docs/acceptance/report-a.md`、完成 Task 5.5、提交 `test: accept complete report A vertical slice` 并停在 Phase 6 前。

## 不要做

- 不要复用旧 `a-complete` 产物、旧截图或修改前 `.artifacts/a-fresh-source` 冒充当前验收。
- 不要进入 B/C 或 PDF、HTML-PPT、PPTX 实施。
- 不要删除旧工程。
- 不要把网络/技术访问失败解释成“无证据”。
