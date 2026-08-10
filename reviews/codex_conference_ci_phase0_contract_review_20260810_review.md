# Codex Conference Review: ci_phase0_contract_review_20260810

Date: 2026-08-10

## Verdict

`PASS WITH OPEN USER DECISION`：Task 0.1 与 Task 0.2 在吸收独立审查发现后通过；Task 0.3 的对账材料通过，但两份康哲设计源文件仍未获用户授权修改，因此 Phase 0 尚未完成，也不得进入 Task 0.4。

## Boundary Compliance

- 两名参与者均为只读审查角色，没有修改新仓源文件，也没有修改或复制两份康哲候选文件。
- Pi 实际生效路由为北京日间替换后的 `cms-smk/cms-model`；健康探针超时仅作诊断，真实路由随后成功，未发生 fallback。
- Grok Build 使用原生 `grok-build/grok-4.5`。首次可审计轮次以 `stop_reason=cancelled` 结束，只含进度句，未作为证据；同一 session 的恢复轮次以 `stop_reason=end_turn` 交付完整报告。
- Hermes 工作流 guard 只负责路由、记录与 review gate；Codex 保留文件修改、实测复核和最终接受权。
- 本轮未进入视觉、浏览器、PPT、PDF 或临床结论验收；这些表面不属于 Phase 0 Task 0.1–0.3 的完成条件。

## Participant Outputs Reviewed

- `general_pi_qwen38`：完整实证审查。独立复现规格摘要、迁移扫描、依赖冻结、两份康哲候选的稳定双读、共同正文锚点、唯一单词差异及假设修正摘要。其三个 P1 中，迁移清单合同测试和批准规格摘要钉住测试已实现；康哲封装摘要守卫保留到用户确认后的 Task 0.3 封装步骤。
- `general_grok45`：只采纳其完成轮次中有静态文件锚点的意见。其“真实仓库未被测试扫描”“相对旧路径可漏检”“`uv lock --check` 未纳入合同测试”三项均由 Codex 复现并修复。因该参与者的终端调用被宿主取消，其关于 Task 0.3 未复现的结论只描述该 session 的证据边界，不否定 Pi 与 Codex 的独立实测。
- 被取消且只有流程性文字的 Grok 输出明确拒绝，不计作会议完成或验证证据。

## Conference Panel Review

审查识别并关闭了四类会制造假绿的缺口：迁移清单未被 schema 与目标摘要联合约束；批准规格副本摘要未被测试钉住；真实仓库未纳入旧运行时依赖扫描且相对路径可漏检；依赖合同测试未机械执行 `uv lock --check`。修复均限制在新仓内部，没有扩大产品范围或开展安全专项。

康哲合同的剩余风险不是技术未知，而是授权边界：当前两份共同正文只有一处文字差异，`经验法则` 对 `经验阈值`。推荐将共享版改为 `经验阈值`，但用户确认前不能写源文件、不能生成合同包、不能把预测摘要称为实测摘要。

## Main-Venue Codex Review

Codex 对所有被采纳的 P1 逐项读取实现并运行了对应合同测试。修复后：

- 旧工程引用扫描同时覆盖绝对路径、相对路径、真实仓库和外部运行时符号链接；历史材料必须逐行带 `historical:` 标记。
- `legacy_manifest.jsonl` 的每条记录均按 schema 校验，已复制目标的摘要与实际文件绑定。
- 批准规格副本 SHA-256 固定为 `f96be175464d06f4a4b2075f020016148e3ac864d07b7ffe05a27db476ca465f`。
- 依赖名称、版本、许可证元数据、用途、来源、锁文件版本与 `uv lock --check` 由同一合同测试守卫。

Task 0.3 的决策记录如实保留“等待用户确认”状态；未把参与者建议、预测摘要或现存候选文件误标为已批准合同。

## Codex Independent Verification

当前工作树的确定性验证结果：

```text
uv run ruff check tools tests
All checks passed!

uv run mypy tools/check_no_legacy_refs.py tests/migration tests/contract
Success: no issues found in 5 source files

uv run pytest -q
6 passed in 0.26s

uv run python tools/check_no_legacy_refs.py
LEGACY_REF_OK ... scanned_without_runtime_dependency=true

uv lock --check
Resolved 40 packages in 3ms

uv sync --all-extras --frozen
Checked 38 packages in 0.49ms
```

康哲候选由 Codex 与 Pi 分别稳定双读，复现当前完整文件摘要 `069f18d5...` / `efa4324a...`、共同正文唯一差异、共享版假设修正摘要 `5318be3c...`，以及修正后共同正文收敛到 `470a769f...`。上述修正仍只在内存中演算，未落盘。

## Final Decision

- 接受 Task 0.1、Task 0.2 的当前实现与加固。
- 接受 Task 0.3 的对账结论和推荐措辞，状态保持“等待用户确认”。
- 用户确认后才执行单词级修改、重新稳定双读、以实测摘要封装两份 v2.1 康哲合同，并新增封装摘要合同测试。
- 用户确认前，Phase 0 不得标记完成，不得开始 Task 0.4。
