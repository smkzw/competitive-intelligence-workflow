# Task 10.2 实施步骤

- [x] R01：冻结本次 run_id、源码/候选包摘要、三项目空根证明、A/B/C 适应症与历史 cutoff。
- [x] R02：实现三个 current-run exact acceptance node 及旧项目、旧 mtime、断链、伪浏览器 verdict 的 RED。
- [x] R03：完成 A 特应性皮炎真实来源研究、门槛、HTML、Chromium/WebKit 全路由验收。
- [x] R04：完成 B PNH 真实来源研究、疗效/安全性/基线/处置门槛、HTML、双浏览器全路由验收。
- [x] R05：完成 C 特应性皮炎登记优先与补件恢复真实路径、HTML、双浏览器全路由验收。
- [x] R06：独立科学、中文、视觉/交互复核；异常结果完成根因分类与恢复。
- [x] R07：确定性测试、治理审计、检查点和可恢复清理完成后收口。

## Exact nodes

1. `tests/acceptance/test_report_a_real.py::test_real_a_acceptance_binds_current_run_snapshot_manifest_artifact_and_browser_verdicts`
2. `tests/acceptance/test_report_b_real.py::test_real_b_acceptance_binds_current_run_snapshot_manifest_artifact_and_browser_verdicts`
3. `tests/acceptance/test_report_c_real.py::test_real_c_acceptance_binds_current_run_snapshot_manifest_artifact_and_browser_verdicts`

## 回滚点

任一项目根预先存在、真实来源身份或 cutoff 不可闭合、关键证据不足仍生成草稿、旧产物被复用、报告数值异常缺失未深挖、浏览器 verdict 不属于当前文件时，保留诊断与下载清单，撤销本次未接受项目，不影响 Task 10.1 已冻结目录。
