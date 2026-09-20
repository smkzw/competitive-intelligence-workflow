# Task 10.3 实施步骤

- [x] F01：冻结 HTML-only 范围、当前 catalog/candidate 摘要、空项目证明和回执根。
- [x] F02：RED/GREEN catalog 真值与输入摘要验证；拒绝 CLI 覆盖和非 HTML 格式。
- [x] F03：RED/GREEN 当前运行顺序、三个 HTML artifact/浏览器 verdict 绑定与失败关闭。
- [x] F04：RED/GREEN required-v12 full-matrix case 预演及未来责任不得误关单。
- [x] F05：接入候选安装根三宿主真实 smoke，验证不同 process/session/run 与同包摘要。
- [x] F06：在全新 acceptance 根运行 pre-RC 全矩阵并完成 A/B/C 全路由实际浏览器检查。
- [x] F07：独立用户视角/视觉复核、治理审计、检查点和可恢复收口。R13k 完成 57 路由四宽度 ego(lite) 检查、A/B/C 交互、两份独立 R13k 视觉更正、同号正式视觉会商、review-gate 与 audit-execution；ZCode 旧会话续接失败被如实保留且未计为通过票。

## 精确节点

1. `tests/acceptance/test_full_matrix.py::test_runner_requires_html_only_catalog_truth_and_hashed_inputs`
2. `tests/acceptance/test_full_matrix.py::test_runner_orders_project_render_browser_hosts_and_project_verify`
3. `tests/acceptance/test_full_matrix.py::test_current_run_manifest_binds_three_html_artifacts_and_browser_verdicts`
4. `tests/acceptance/test_full_matrix.py::test_runner_fails_closed_on_any_missing_artifact_failed_verifier_or_nonzero_command`
5. `tests/acceptance/test_full_matrix.py::test_suite_full_rehearses_current_scope_without_closing_future_owner_receipts`

## 回滚点

任一实现试图恢复 PDF/PPT、复用 Task 10.2/Phase 8 旧输出、把 rehearsal 写成 release accepted、伪造宿主或浏览器回执、或在失败后输出通过时，撤销 Task 10.3 未接受产物，保留 Task 10.2 R12 与候选安装包不变。
