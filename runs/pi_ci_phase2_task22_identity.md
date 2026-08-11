# Task 2.2 独立验收（第三轮复核）

## 结论

**PASS**，P0=0，P1=0，P2=0。

六类机械检查全部在本轮真实重跑通过，五个指定攻击向量逐一复现修复生效；本轮未发现任何残余缺陷。按质量门（P0=0、P1=0 且实际命令通过）建议接受。

关于 SOUL.md：本会话前两轮已通过 read 工具读取全文，工具输出尾部在 768 字符处截断显示，除截断段外均已阅读；本轮未重复读取。

## 读取与执行证据

本轮重读（当前工作树）：`src/ci_workflow/domain/entities.py`、`src/ci_workflow/ingestion/identity.py`、`tests/unit/test_entity_identity.py`、`tests/integration/test_competitor_universe.py`、`docs/acceptance/runs/task-2.2/red.txt`、`docs/acceptance/runs/task-2.2/green.txt`，另复核 `src/ci_workflow/domain/ids.py`、`src/ci_workflow/capabilities/ontology_universe.py`、`policies/ontology/innovation-therapy-v1.yaml` 及 prd/design/implement 合同（本会话前两轮读取，内容一致）。文件与上轮 PASS 复核逐字节一致，无新增改动。

实际运行输出：

| 检查 | 命令 | 结果 |
|---|---|---|
| Task 2.2 精确套件 | `uv run pytest tests/unit/test_entity_identity.py tests/integration/test_competitor_universe.py -q` | **10 passed in 0.05s** |
| 全库 | `uv run pytest -q` | **147 passed in 6.01s** |
| Ruff | `uv run ruff check src tests` | **All checks passed** |
| strict mypy | `uv run mypy --strict src tests/unit/test_entity_identity.py tests/integration/test_competitor_universe.py` | **Success: 27 source files** |
| 包校验 | `uv run ci-workflow package verify --root .` | **PACKAGE_OK version=0.1.0a0 stage=phase-0-task-0.4** |
| git | `git diff --check`（exit 0）`git status --short` | 无空白错误；未跟踪文件集与预期一致 |

**本轮测试数：Task 2.2 精确 10 项，全库 147 项**（较首轮 7/144 增加 3 个修复节点：basis 守卫、重复/缺失适格记录、待审查闭合）。green.txt 声称的 10/147、27 源文件、包版本与本次重跑完全吻合。

## 五个指定攻击向量结果

1. **重复适格记录**：`CompetitorUniverse.build` 抛 `ValueError("每个实体必须且只能有一条适格记录")`（`identity.py:115-117`）。探针：`(elig, elig)` → raised。测试：`test_competitor_universe_rejects_duplicate_or_missing_eligibility_records`。
2. **已登记但漏评的实体**：`set(by_id) - eligibility_id_set` 非空即抛同错误（`identity.py:121-122`）。探针：缺一条 → raised。同上测试。
3. **identity_basis 等于名称/别名/NCT/CTR**：`entities.py:66-72` 守卫，四种情形（名称、别名、NCT 大小写变体、CTR）全部抛 `身份依据不能直接使用名称、别名或外部登记号`。测试：`test_identity_basis_cannot_be_the_name_alias_or_external_identifier`（覆盖名称、别名、NCT 小写三种；CTR 由探针补充确认同守卫）。
4. **变更外部登记号后的身份稳定性**：NCT→CTR 与 NCT→新 NCT 均保持 `entity_id` 不变（键为 kind+type+basis 哈希，`entities.py:68`）；旧登记号仍可经 `resolve_external_identifier` 命中。测试 1 新增 `changed_registry_number.entity_id == product.entity_id` 断言。
5. **review_pending 阻断宇宙闭合**：任一 `review_pending` → `universe_closed=False`（`identity.py:123-124`）；探针确认纯 pending 与 pending+included 混合两种情形均闭合为 False，members 仅含 included。测试：`test_pending_eligibility_prevents_identity_bound_universe_closure`。

附加复核：实体身份重复、未知适格引用仍抛错；别名/外部标识符冲突保留全部候选与证据（非先到先得、不自动合并）；同一内部身份不一致内容拒绝静默覆盖；150 实体宇宙无 Top-N/排序/切片截断（`members=150` 全量保留）。

## 缺陷

**无**（P0=0、P1=0、P2=0）。

**残余 P2：无**。首轮报告的 P1-1（重复适格静默翻倍）、P1-2（漏评实体静默丢弃且闭合）与 P2-1（basis 无守卫）、P2-2（换登记号断言缺失）、P2-3（pending 路径无测试）均已由实现+测试双重重闭合，本轮未发现新缺陷。

假绿排查：三个新节点在 red.txt 均有真实 RED 失败信号（basis 守卫、重复/缺失适格、待审查闭合），非虚构；测试 1 的弱断言已由「换登记号身份不变」与守卫测试补强。未发现形式通过而行为未验证的假绿。

## 确认与 Codex 仍需直接确认

**确认：本会话未编辑任何文件**。本轮仅执行 read、grep、bash 只读命令（pytest/ruff/mypy/package verify/git diff --check/git status）与进程内 Python 探针（eval 内核，不落盘），未调用任何 write/edit 工具，工作树与进入会话时一致。

Codex 仍需直接确认（非缺陷，属后续承接）：
1. 全 excluded 宇宙为 `closed=True, members=()`，非空性由 §8.7「宇宙关闭且非空」门槛在 Task 2.3+ 求值器承接。
2. `identity_basis` 的来源派生规则需在 Task 2.3 摄取合同落地（守卫已防住名称/别名/登记号直用，但 basis 生成规范未定）。
3. implement.md 中 Task 2.2 复选框仍未勾选，接受后请更新；最终接受权在 Codex。
