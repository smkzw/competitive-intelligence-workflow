# Codex Review: ci_phase1_task16_capability_preflight

Date: 2026-08-11
Delegated-agent outputs: `runs/pi_ci_phase1_task16_capability_preflight.md`, `runs/pi_ci_phase1_task16_capability_preflight_followup.md`

## Verdict

PASS。Task 1.6 可以接受；Phase 1 完整退出仍需随后执行，来源路线恢复、报告门槛和格式生成/验收未提前接受。

## Boundary Check

- 本任务通过 Hermes workflow guard 与 session runner 初始化、提示预检和留痕；实际只读验收角色使用声明的 `Pi/cms-smk/deepseek-v4-flash:max`，首轮及修订复核均为同一 session `019ff10c-d3e2-7000-b372-d52aa2fb1d14`，无 fallback、无重派。
- 审查者只读并删除其 `.artifacts/reviewer-*` 临时文件；产品工作树没有被 reviewer 改写。旧工程、外部项目和通用康哲设计规范均未修改。
- 变更只覆盖 Task 1.6 的能力矩阵、CLI、schema、包登记和测试；未做安全测试、来源检索或重型格式生成。

## Codex Verification

- CP01–CP08 每个 exact node 均取得预期 `1 failed`（目标模块尚不存在），实现后分别 `1 passed`。
- 整套 Task 1.6：`11 passed in 0.67s`；全库：`132 passed in 5.82s`。
- Ruff 通过；strict mypy 20 个源文件无问题；包校验 `PACKAGE_OK version=0.1.0a0 stage=phase-0-task-0.4`；`git diff --check` 通过。
- 真实执行 `local` + A/B/C + HTML/PDF/HTML-PPT/PPTX：本次适用的 10 项能力全部 ready；未选择登录来源、未声明 OCR 需求，因此 `login_browser` 与 `ocr` 正确为 `not_applicable`。原独立报告一处“12/12 ready”表述不准确，Codex 以实际 JSON 口径更正，不影响结论。
- 内联选择与项目合同入口的 selection/capabilities/research/deliveries/overall state 完全一致；双入口、无入口和缺输出位置均中文失败关闭。
- 缺 PPT Master/Office 只阻断 PPTX，HTML/PDF 不受影响；两者同时缺失合并为一条中文说明。矩阵强制 12 个唯一能力及所选报告×格式完整笛卡尔积，伪总状态、重复项和无效阻断引用均失败关闭。
- 环境恢复只重排 blocked→ready 且已经解除其他阻断的下游；研究能力恢复包含 research/analyze/snapshot/render/verify，Office 仍阻断时不提前重排 PPTX。

## Delegated-Agent Output Review

首轮 reviewer 真实遇到一次 ClinicalTrials.gov 单次超时、重试即恢复，并指出 LibreOffice 语义可能过宽。Codex 没有把它们作为非阻断观察直接收口：网络探针改为最多 3 次、0.25/0.5 秒短退避；连续三次失败才以中文说明阻断，成功立即停止。Office 判定收紧为 Microsoft PowerPoint 或宿主显式指定的可执行 Office，LibreOffice/soffice 不再自动通过。原 reviewer 复用同 session 增量复核后再次 PASS，无 P0/P1。Codex随后把最终用户消息补充为“连续 3 次仍无法连接”，并以 11/132 项回归直接复核。

## Residual Risk

- 三次短退避只属于能力预检自愈；Task 2.3 仍必须实现同路径重试、适用替代来源和独立技术诊断，不能拿本任务冒充完整来源穷尽。
- `CI_WORKFLOW_OFFICE_COMMAND` 由宿主适配器明确指定，后续宿主一致性测试必须证明它指向用户实际采用的目标 Office；任意可执行文件名不能成为正式 PPTX 验收证据。
- Task 1.6 只证明能力“可调用”；HTML/PDF/HTML-PPT/PPTX 的真实内容、视觉、可编辑性和当前产物验收属于 Phase 8/10。
