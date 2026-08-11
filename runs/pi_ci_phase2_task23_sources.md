# Task 2.3 独立验收（P2-2 修复复核）

## 结论

**PASS**（P0 = 0，P1 = 0）。P2-2 已闭合（重复 `[1,1]` 与跳号 `[1,3]` 均被拒绝）；P2-1 确认仅为 Task 2.4–2.7 编排接线边界，非本任务代码缺陷。六项机械检查全部真实重跑通过。

声明：`pi` fallback `deepseek`/`deepseek-v4-flash`（effective route `opencode-go/deepseek-v4-flash`），只读复核，未编辑任何文件；Codex 为最终权威。

## 运行与读取证据

| 检查 | 命令 | 实际输出 |
|---|---|---|
| 组合套件 | `uv run pytest tests/unit/test_source_policy.py tests/contract/test_evidence_audit_contracts.py tests/integration/test_route_recovery.py tests/integration/test_historical_cutoff.py -q` | `18 passed in 0.11s` |
| 全库 | `uv run pytest -q` | `159 passed in 5.22s` |
| Lint | `uv run ruff check src tests` | `All checks passed!` |
| 类型 | `uv run mypy --strict src tests/unit/test_source_policy.py tests/contract/test_evidence_audit_contracts.py tests/integration/test_route_recovery.py tests/integration/test_historical_cutoff.py` | `Success: no issues found in 34 source files` |
| 包校验 | `uv run ci-workflow package verify --root .` | `PACKAGE_OK version=0.1.0a0 stage=phase-0-task-0.4` |
| 差异 | `git diff --check`；`git status --short` | exit 0；23 项改动，与修复范围一致 |

直接探测（独立于测试套件，`uv run python` 实测）：

```
valid [1,2]:   ACCEPTED
duplicate [1,1]: REJECTED -> Value error, 信息增益轮次必须从一开始连续递增
skip [1,3]:    REJECTED -> Value error, 信息增益轮次必须从一开始连续递增
empty:         REJECTED -> Tuple should have at least 1 item after validation, not 0
```

## P2-2 闭合核验

- **实现**：`EvidenceGap._information_gain_rounds_are_contiguous`（src/ci_workflow/domain/evidence.py:315-320）——`rounds != tuple(range(1, len(rounds) + 1))` 即拒绝，覆盖重复、跳号、非从 1 起始全部情形；模型 frozen + `extra="forbid"` 保持。
- **测试**：tests/contract/test_evidence_audit_contracts.py 新增 `invalid_rounds` 循环，对 `[1,1]` 与 `[1,3]` 断言 `PydanticValidationError` 且消息匹配 "信息增益轮次必须从一开始连续递增"。
- **RED 链**：red.txt 记录——首次验收发现账本缺口 → 先加拒绝断言取得 1 failed → 再补连续性校验；green.txt 已更新该条。与我的实测输出逐字一致。
- **闭合判定**：P2-2 闭合。唯一写入通道是 pydantic 域模型，无旁路。

## P2-1 状态

重 grep 确认：`SamePathRetryAudit`、`AlternativePathAudit`、`RecoveryHistory`、`can_declare_information_saturated`、`assess_historical_source` 在 src 内仍仅有定义、零调用点（git status 无新增 src 文件）。**P2-1 是编排接线边界**：Task 2.3 范围为 SP01–SP11 合同层，强制对象已齐备且经测试锁定；调用责任随 Task 2.4–2.7 连接器/编排器落地，届时需验收接线后不可绕过性在端到端成立。不属于本任务缺陷，不阻断 PASS。

## 缺陷

- P0：无。P1：无。
- P2-2：已闭合（见上）。
- P2-1：接线边界，后置 Task 2.4–2.7。
- 新观察（非阻断）：连续性规则仅在 pydantic 域层强制，`schemas/evidence-gap.schema.json` 未同步镜像（git status 显示该 schema 未改动，仅 source-receipt schema 有改动）。JSON Schema 本身无法原生表达"从 1 连续递增"，且所有机器 JSON 均由 pydantic 对象产出，故无实际绕过面；建议在 Codex 侧决定是否在 schema 注释/文档声明 pydantic 为准，或接受现状。

## Codex 仍需确认

1. P2-2 修复是否接受闭合（我侧证据：实现 + 测试 + 独立探测三通道一致）。
2. 新观察（schema 未镜像连续性规则）是否后置或维持现状。
3. P2-1 接线验收归属 Task 2.4–2.7 编排验收范围。
