# 第 5.2 步独立验收第 4 轮

继续原 Luna 审查会话，保持与执行者隔离。第 3 轮完整结论在 `runs/conference/ci_phase5_task52_verify/luna_verifier_round3.md`，执行修补交接在 `runs/execution/ci_phase5_task52_execution/worker_03_round4.md`。

## Hard boundaries

- 只读审查，不修改任何产品、测试、Trellis 或记录文件；runner 只保存最终报告。
- 不做模板、HTML、PDF、PPT、浏览器和安全测试。
- 不接受执行者自报或既有测试数量作为完成证据；必须对当前工作树独立复现、构造反例并运行。
- Read these files only as the initial set: `AGENTS.md`、上述两份报告、Task 5.2 当前源码与精确测试；仅沿当前验证调用链读取必要相邻文件。

Read these files only:
- `AGENTS.md`
- `runs/conference/ci_phase5_task52_verify/luna_verifier_round3.md`
- `runs/execution/ci_phase5_task52_execution/worker_03_round4.md`
- `src/ci_workflow/reports/a/`
- `src/ci_workflow/storage/snapshot_store.py`
- `src/ci_workflow/storage/project_contract_store.py`
- `src/ci_workflow/capabilities/lineage_registry.py`
- `src/ci_workflow/capabilities/extraction_normalization.py`
- `tests/unit/reports/a/test_revise_round4_closure.py`
- `tests/unit/test_project_contract_store.py`

Runner-managed report path: `runs/conference/ci_phase5_task52_verify/luna_verifier_round4.md`.

## 验收目标

逐项重新攻击第 3 轮六个缺口，并检查修复是否引入新的 false-green：

1. **证据内容摘要**：确认 manifest 摘要真正覆盖每条已验证片段和每条已接受事实的全部决策性字段，排序与序列化确定；同步修改事实、片段、片段摘要、记录显示并保留 ID/locator 时必须拒绝。尝试修改 normalized_value、numerator/denominator、population、timepoint/window、arm/cohort、review/disclosure/source role、片段 locator/source_version 等非 raw 字段。检查 `_revalidate_inputs` 后续确实使用重验证 registry。缺摘要、错摘要、旧 manifest 都应失败关闭，正向锁定/读取不漂移。
2. **权威当前合同**：不要只验证 context 内一致性。确认 `ProjectContractStore` 的根、项目身份和持久化内容不能与攻击者提供的新 store 一并替换而冒充权威。构造 context+manifest+locked snapshot+新 store+新 contract store 全部自洽的 999/2099 攻击；如果仍接受，必须 REVISE。判断当前调用边界是否有真正独立、预先绑定的权威 store 身份；若没有，给出最小可执行修复而非抽象建议。
3. **结果强类型闭合**：逐字段错配 numeric/normalized value、unit/normalized_unit、numerator、denominator、population、timepoint/time window、arm/cohort；检查疗效和安全性均拒绝，且页面不要在校验后继续消费原始伪造对象。
4. **所有 AV04–AV08 扩展 DTO 重验证**：以 `model_copy` 和 `model_construct` 攻击所有记录族和嵌套 `EvidenceField`，尤其 AV04 美国地域、value+state 并存；确认使用重验证返回对象而非原对象。
5. **中文和日期**：全角日期、非零填充日期、非法日期；中文逗号/顿号/括号展示保真；工程词 NFKC、零宽和连字符变体仍拒绝，医学英文不误伤。
6. **回归与架构**：运行本轮精确测试、A 类完整单元、相关 contract/snapshot tests、目标 Ruff、strict mypy。检查 schema 与模型必填项一致，既有 manifest 生产构造点没有漏填；新增合同 store 不允许跨项目读取或静默覆盖。

最终只给 `PASS` 或 `REVISE`。`PASS` 必须满足 P0=0、P1=0，且上述攻击与机械检查都通过；P2 只有在确属用户无影响的小问题时才能保留。每个缺口写清符号/位置、构造、实际、预期、未捕获原因和最小修复。不要修改工作树，不要提交。

Output file: `runs/conference/ci_phase5_task52_verify/luna_verifier_round4.md`
