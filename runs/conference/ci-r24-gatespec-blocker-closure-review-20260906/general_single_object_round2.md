所有验证已完成。正在编译差异报告。

# 会议参与者输出：ci-r24-gatespec-blocker-closure-review-20260906 - general_single_object (第2轮)

## 边界检查

- 同会话续轮（round 2），只读复核；未改任何源码/测试/任务记录/日志；未读生产路径、凭据、旧工作区、其他参与者输出。
- 本次仅读取指定文件集：`gates/evaluator.py`、`gates/exhaustion.py`、`application/run_service.py`、`gates/blocker_audit.py`、`package-manifest.json`、`tests/unit/test_gate_evaluator.py`、`tests/integration/test_double_exhaustion.py`、`tests/integration/test_fixture_case_contracts.py`；两个专用 schema 文件仅做了存在性检查与程序化字段约束抽查（未通读内容），并运行了上述三个测试文件。
- 未写 runner 报告路径 `runs/conference/.../general_single_object_round2.md`；本报告随消息返回由 runner 持久化。进程内探针只构造内存对象或写系统临时目录。
- 新鲜度按指示保持用户裁决事项；父模式无原生 Ask 控件一事未计为代码缺陷。

## 绕过探针与结果

**修复 1 — `evaluate_report` 拒绝未知单元绑定**（`evaluator.py:504-510`，RED/GREEN：`test_gate_evaluator.py:547`）
- 字节核验：`spec_units` 差集非空即 `GateEvaluationError("证据绑定引用未知门槛单元")`，置于矩阵展开之前。
- 探针 1a：跨报告单元（A 评估中绑定 `b_trial_identity_role`）→ 拒绝 ✓。
- 探针 1b：大小写改写（`A_PRODUCT_IDENTITY`）→ 拒绝 ✓（无 casefold 宽容，安全方向）。
- 探针 1c：伪单元携带 CONFLICTING 事实（压制尝试）→ 绑定模型层即拒（ValidationError）✓。
- 结论：修复成立；"有效单元+错误对象"的残余路径仍由 `assert_bindings_in_universe` + 矩阵全等覆盖，无新开口。

**修复 2 — 终态科学穷尽拒绝自由 `new_fields`/`new_source_versions`**（`exhaustion.py:597-603`，参数化 RED/GREEN：`test_double_exhaustion.py:194-216`）
- 字节核验：科学分支新增 `any(item.new_fields or item.new_source_versions ...)` 即拒；类型化身份（fragments/units/conflicts）仍由 `_information_gain_rounds_align_with_history` 逐轮精确绑定；测试先重算 reviewer inputs digest，保证拒绝确实来自新检查而非摘要错配。
- 探针 2a：双列表同时注入自由字段 + 重算摘要（真实伪造路径）→ 以"自由字段或来源版本"拒绝 ✓。
- 探针 2b：只注入内嵌 `evidence_gap.information_gain_diff` → 以全等绑定（"完全一致"）拒绝 ✓。
- 探针 2c：轮次重编号 + 自由字段 → 拒绝 ✓。
- 残余说明：独立（非终态）`EvidenceGap` 仍可携带自由字段，但所有终态/blocker 消费路径都经 `GapDoubleExhaustion`，内嵌时受全等约束——可接受。

**修复 3 — 空宇宙阻断缺证据即 raise + 移除假 NCT 链接**（`run_service.py:3457`、`:3483`）
- 字节核验：`ctx.universe_evidence is None` → `ContractConfigError("空宇宙阻断写入缺少已绑定的宇宙证据")`；`source_links=()`。
- 相邻失败模式排查：canonical `BlockerAudit.source_links` 默认空元组且注册 schema 的 `source_links` 无 minItems → 模型与 schema 双向接受空集，不会使空宇宙路径构造崩溃；publication 变体保持 `min_length=1`（其语义本就须真实论文链接）——正确的不对称。
- 实盘断言：`test_fixture_case_contracts.py:293-294` 在真实 fixture 运行中断言 `audit.source_links == ()` 且 `"NCT01234567" not in audit_json`，另断言无 `reports/A` 版本目录与占位文件 ✓。

**schema 注册与变体分发**
- `package-manifest.json` components/schemas 注册三个条目：`blocker-audit.schema.json`、`publication-blocker-audit.schema.json`、`scientific-qc-blocker-audit.schema.json`；两专用文件存在于磁盘（本轮存在性核对）。
- `validate_existing_blocker_package`（`blocker_audit.py:2190-2267`）：symlink/两文件/普通文件 → 按 `blocker_kind` 三路分发（QC 分支对内嵌 `exhaustion` strip-computed 后全模型重验证）→ `audit_digest` 重算比对 → 身份四元组校验 → publication 专属补件门文件字节 SHA/终态/响应重验 → `audit.md` 再生成字节比对。共享基线（身份、原子两文件、`no_draft`/`resume_node` 字面量、漂移拒绝、resume）对三变体统一生效；publication 变体不含 GateSpec/穷尽/失败单元字段，未伪造任何未发生的科学恢复轮次——独立机制定位正确。
- 探针 4a：canonical 载荷伪装 `blocker_kind="publication_unavailable"` → `BlockerPackageIntegrityError` ✓（变体 extra=forbid）。
- 探针 4b：**`blocker_kind="scientific_qc_exhausted"` 但缺 `exhaustion` 键 → 裸 `KeyError` 逃出** try 的 `except (OSError, ValueError, TypeError)`，也逃出 run_service 的类型化捕获——仍失败关闭（绝不接受），但 resume 会以未类型化崩溃代替中文合同错误。**新 P2**：`scientific_raw.get("exhaustion")` + 显式 ValueError（或把 KeyError 纳入 except），一行修复。
- 探针 4c：无 kind 垃圾载荷 → canonical 分支拒绝 ✓。

**回归证据**：三个指定测试文件在当前字节上 `83 passed`；Codex 侧 233 项受影响矩阵与全量门（Ruff、strict-mypy 211 文件、945 active、20 retained、7 layer、legacy-path）为 runner 记录，本轮未重跑全量。

## 剩余 P0/P1

- **P0：无。P1：无新增。** 唯一 P1 仍是新鲜度缺失——用户产品裁决事项，本轮按指示不裁、不计 Ask UI 限制为缺陷。本轮复核范围内未发现新的可造成科学假绿、候选删减、终态无机器审计或下游残留的可达缺陷。

## 首轮 P2 处置

| 首轮编号 | 内容 | 处置 |
|---|---|---|
| P2-a | 增益自由字段未绑定 | **已闭合**（修复 2，以"删除"而非"派生"方式，强于建议；探针 2a-2c 证伪失败） |
| P2-b | 遗漏复核上下文摘要调用方自报 | **开放**（本轮范围外；仍为 P2） |
| P2-c | 未知 unit_id 绑定被静默忽略 | **已闭合**（修复 1 + 探针 1a-1c + 专用测试） |
| P2-d | 空宇宙假 NCT 链接 | **已闭合**（修复 3 + fixture 实盘断言） |
| P2-e | `_drive_blocker_write` 静默 return | **已闭合**（`run_service.py:3457` 显式 raise） |
| P2-f | 专用 schema 注册/分发 | **基本闭合**：注册、存在、分发、重验、共享基线全部核实；publication §6 字面口径由"独立失败机制"定位解决。残余：专用 schema 文件内容未通读（读集限制），仅抽查 `source_links` 约束一致 |
| P2-g | 成熟度启发式对抗性误标测试 | **开放**（风险级，本轮范围外） |
| **新 P2（本轮）** | `validate_existing_blocker_package` QC 分支缺 `exhaustion` 键时裸 `KeyError` 逃出类型化错误合同（探针 4b） | 开放，一行加固 |

## 精确残余风险

1. 新鲜度模型/阈值/历史截止日语义未定（用户所有）；裁决前不得以默认语义关闭 P2。
2. `KeyError` 逃逸（新 P2）：方向失败关闭，仅错误合同破损；被篡改 `audit.json` 触发 resume 时表现为未类型化崩溃。
3. P2-b：遗漏复核独立性证明强度仍依赖恢复阶段纪律（摘要自报、仅约束不等）。
4. P2-g：监管事实误标可移动成熟度适用性边界，无对抗性负向测试锁定。
5. 本轮未重跑全量门与三变体 blocker 的实盘 resume 全链（读集与范围限制）；以代码核验、探针、83 项指定测试与 runner 记录的 233+全量门为据。

## 建议的任务状态

**R2.4 P3–P5 维持闭合，无需回开**：三项修复在字节、测试、探针三层均验证成立，且各自带真实 RED/GREEN；专用 schema 注册与变体分发达标。建议：
1. 采纳新 P2（`KeyError` 一行加固 + 一条 RED：缺 exhaustion 键的 audit.json → 类型化 `BlockerPackageIntegrityError`）。
2. P2-b、P2-g 记入任务跟踪，随 P6 治理门或后续最小修复处理，不阻断 P3–P5 状态。
3. 新鲜度三项继续走用户原生 Ask（父模式控件恢复后）；裁决前 P2 不得关闭。
4. P6 按计划推进（独立会商、分层 gate、bundle/fresh-install、checkpoint、归档）；修复后建议由 Codex 再跑一次全量门作为 P6 输入。Codex 保留最终接受权。
