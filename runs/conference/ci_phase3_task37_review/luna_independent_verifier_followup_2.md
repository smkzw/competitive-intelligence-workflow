FAIL; P0=1; P1=2; P2=1

# Execution Output:

## Boundary And Context Check

只读完成；未读取执行者提示词、报告、日志、评审或主代理结论，未写入文件。批准设计副本存在于 `docs/specs/competitive-intelligence-workflow-design-v1.2.md`。

## Work Performed

确认以下修补有效：

- 候选快照完整摘要进入 `ReportGateResult.result_key`；同 ID/同宇宙摘要但内容变化被拒绝。
- GateSpec 标准版本错配被拒绝。
- accepted/recoverable/exhausted 矛盾组合、裸布尔、错误 SHA、错误对象、错误穷尽记录均失败关闭。
- A/B/C 否决路径无报告快照、coverage、format job、render queue、artifact 或报告目录。
- 普通字符串 `"accepted"` 不符合科学质控节点类型。

仍发现 1 个 P0、2 个 P1 和 1 个非阻断 P2。

## Artifacts And Evidence

### P0-1：授权发行仍是公开自填入口

文件：`src/ci_workflow/graph/executor.py:294-372`；`src/ci_workflow/storage/event_store.py:50-63,146-180`；`src/ci_workflow/graph/reducer.py:378-460`。

`issue_scientific_qc_authorization()` 是公开方法，调用者可自填 verdict、候选、上下文和证据摘要；`EventStore.append()` 接受普通调用者追加形状正确的授权事件。归约层只校验字段、SHA、事件 ID 和幂等键，没有发行者权威或独立 QC 证明。

攻击结果：

```text
PUBLIC_METHOD_EVENT_TYPE= scientific_qc.authorization.issued
PUBLIC_METHOD_ACTOR= ordinary-caller
PUBLIC_METHOD_TRANSITION= graph.transition.accepted
PUBLIC_METHOD_STATE= snapshot_locked
DIRECT_APPEND_EVENT_TYPE= scientific_qc.authorization.issued
DIRECT_APPEND_TRANSITION= graph.transition.accepted
DIRECT_APPEND_STATE= snapshot_locked
REPLAY_PUBLIC_STATE= snapshot_locked
REPLAY_DIRECT_STATE= snapshot_locked
```

这直接违反“只有独立、当前科学质控接受才能锁定快照”。最小修复：将发行能力限制为不可伪造的内部边界能力；事件库拒绝普通调用者发行授权；发行时重新绑定当前 QC 输入、身份、对象、from/to 和完整证据，且迁移校验所有授权字段。

### P1-1：授权可跨恢复周期重复消费

文件：`src/ci_workflow/graph/executor.py:401-419,443-448`；`src/ci_workflow/graph/reducer.py:492-506`。

同一 recoverable 授权在 `scientific_qc -> recovering` 后，经过 `recovering -> scientific_qc`，用新的 request ID 再次消费成功：

```text
FIRST= graph.transition.accepted
REOPEN= graph.transition.accepted
SECOND_REUSE= graph.transition.accepted
FINAL_STATE= recovering
```

授权账本没有 consumed/epoch/current-context 绑定。最小修复：授权必须一次性消费，或绑定当前状态代次和最新上下文；只允许同一 request ID 的精确幂等重放。

### P1-2：语义唯一/跨数组校验未进入正式边界，且遗漏嵌套定位重复

文件：`src/ci_workflow/capabilities/scientific_qc.py:101-103`；`src/ci_workflow/qc/scientific.py:144-177,482-616`；`schemas/scientific-qc-verdict.schema.json:329-337,583-587`。

生产边界仅调用 Pydantic：

```text
_revalidate_verdict -> ScientificQcVerdict.model_validate(...)
```

`check_scientific_qc_verdict_semantics()` 只有定义和测试调用，没有生产调用。JSON Schema 的 `uniqueItems` 只能拒绝完全相同对象，不能表达语义 ID 或跨数组引用。

更严重的是，向同一 `SourceRef.locators` 添加相同 `fragment_id`、但改变定位字段后：

```text
NESTED_DUP_MODEL=accept
NESTED_DUP_SCHEMA_ERRORS=0
NESTED_DUP_SEMANTIC_ERRORS=[]
NESTED_DUP_APPLY_STATE= snapshot_locked
```

最小修复：在正式边界调用 JSON Schema 和完整语义校验；补充 `SourceRef.locators` 的语义唯一、来源片段引用和跨数组引用校验，并在发行授权前拒绝。

### P2-1：历史实施计划路径不可由仓内精确文件复核

`docs/specs/competitive-intelligence-workflow-design-v1.2.md:1-7` 正本存在；请求的两个 `2026-08-10...` 文件名不在仓内。按当前任务说明，这属于外部批准计划的路径追踪缺口，不是产品功能缺陷。建议补充仓内指针或摘要。

## Commands And Observations

- `.venv/bin/python -m pytest -q tests/integration/test_scientific_qc_gate.py tests/graph/test_scientific_qc_isolated_veto.py`  
  `6 passed in 0.57s`

- `.venv/bin/python -m pytest -q tests/unit/test_gate_evaluator.py tests/graph/test_checkpoint_replay.py tests/graph/test_graph_node_contracts.py tests/graph/test_partial_delivery.py tests/graph/test_partial_delivery_blocked.py tests/graph/test_transition_matrix.py`  
  `68 passed in 23.58s`

- `.venv/bin/python -m pytest -q`  
  `464 passed in 53.18s`

- Ruff on all affected Python files  
  `All checks passed!`

- Strict mypy on affected source  
  `Success: no issues found`

- `.venv/bin/python -m ci_workflow.cli package verify --root .`  
  `PACKAGE_OK version=0.1.0a0 stage=phase-2-accepted`

- JSON Schema validation, manifest inclusion and SHA negative case  
  `SCHEMA_CHECK=valid schema; manifest entry; valid verdict; SHA negative rejected`

- `git diff --check`  
  Exit `0`, no output.

- Plain string node output attack  
  `PLAIN_STRING_QC_OUTPUT=reject ValueError`

## Blockers Or Missing Environment

无测试或工具环境阻塞。Phase 3 尚未承诺数据库持久化身份权威，因此未将该后续能力缺失单独计为缺陷；但当前公开发行接口已经足以构成 P0。

## Rerun Requests Or Next Step

修复 P0/P1-1/P1-2 后，必须重新执行上述精确测试、全量 pytest、攻击脚本、Ruff、strict mypy、package verify、Schema validation 和 diff check。
