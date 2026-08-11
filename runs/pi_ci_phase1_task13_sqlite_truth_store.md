I have all evidence. Here is the complete acceptance report.

---

# Task 1.3 独立验收

## 结论

PASS

Task 1.3 的六阶段 SQLite 迁移、科学真源核心表、状态族隔离与追加式版本记录满足 Success Criteria 的全部六项。所有命令真实执行通过：精确 6 项、全库 108 项、Ruff、strict mypy、包校验全绿。存在两个 P2 级残余观察（不影响 Task 1.3 驳回范围，见"残余边界"）。

我已完整读取 `/Users/smkzw/.hermes/SOUL.md`（共 268 行，读到 OCR And Translation 节末尾）。

## 实际执行证据

| 命令 | 结果 | 证据 |
|------|------|------|
| `.venv/bin/pytest tests/integration/test_sqlite_migrations.py tests/integration/test_append_only_records.py -q` | PASS | `6 passed in 0.14s` |
| `.venv/bin/pytest -q` | PASS | `108 passed in 5.61s` |
| `.venv/bin/ruff check src tests` | PASS | `All checks passed!` |
| `.venv/bin/mypy --strict src` | PASS | `Success: no issues found in 13 source files` |
| `.venv/bin/ci-workflow package verify --root .` | PASS | `PACKAGE_OK version=0.1.0a0 stage=phase-0-task-0.4` |

补充真实执行（只读探针，验证运行时行为而非仅静态阅读）：
- `PRAGMA user_version` → `6`；`PRAGMA foreign_keys` → `1`；`PRAGMA integrity_check` → `ok`
- 幂等重放 `apply_migrations` 二次调用 → `()`（空），`schema_migrations` 仍 6 行
- 摘要漂移探针：篡改 `0001` 内容后 `MigrationDriftError: 已应用迁移的文件名或摘要不一致：0001_project_identity.sql`
- 间隙探针：删除 `0003` 后 `MigrationSequenceError: 迁移版本必须从 0001 开始且连续`
- 追加式触发器：`sqlite_master` 中 34 个 trigger；对 `project_contract_versions`/`evidence_fragments`/`fact_versions`/`claim_versions`/`report_snapshots`/`artifact_records` 等执行 UPDATE/DELETE 均抛 `sqlite3.IntegrityError`，消息含 `append-only`
- 运行时 FK 强制：向 `source_eligibility_evaluations` 插入不存在父行 → `IntegrityError: FOREIGN KEY constraint failed`（`foreign_keys=ON` 真实生效，非仅声明）

## 迁移与数据合同核对

**1. 迁移连续、原子、幂等、记录摘要、拒绝漂移** — PASS
- `migrations.py:40-58` `_load_migrations` 按文件名排序，正则 `^[0-9]{4}_[a-z0-9_]+\.sql$` 校验，版本必须等于 `range(1, N+1)`，否则 `MigrationSequenceError`。
- `migrations.py:91-115` 每个迁移包在 `BEGIN IMMEDIATE; … COMMIT;` 中，`executescript` 失败回滚；插入 `schema_migrations (version, name, sha256, applied_at)` 并设 `PRAGMA user_version`。已应用迁移比对 `(name, sha256)`，不一致抛 `MigrationDriftError`，一致则 `continue` 跳过。幂等重放返回空 tuple。
- 0001–0006 文件名连续、摘要为 SHA-256（长度 64，测试 `test_six_ordered_migrations…` 断言）。

**2. 核心表齐全，FK/integrity/user_version 合同** — PASS
- `EXPECTED_TABLES`（24 表）与迁移产物一致，`tables >= EXPECTED_TABLES`。
- `foreign_keys=1`、`integrity_check=ok`、`user_version=6` 实测确认。
- 项目 YAML（`project.yaml`）与 DB 合同一致：`project_service.py:213-236` 校验 YAML 无绝对路径、`apply_migrations` 重放、`integrity_check`、DB 中 `contract_json` 与 `active_contract` 序列化（`ensure_ascii=False, sort_keys=True`）逐字节比对。

**3. 状态族隔离 + 接受后不可变 + 修正以 supersedes 表达** — PASS
- 九组状态族以独立 `CHECK` 约束隔离，互不串写：`project_runs.state`（0001:15-18）、`fact_versions.disclosure_state`（0002:47-51）与 `fact_versions.review_state`（0002:52-54）分离、`report_snapshots.evidence_state`（0003:16-19）、`format_jobs/artifact_records.state`（0004:5-8,35-38）、`download_requests.state`（0004:46-49）、`correction_proposals.state`（0005:4-7）。测试 `test_state_families…` 用 9 组非法跨族值断言全部抛 `IntegrityError`。
- 接受后不可改：0006 对 17 张不可变表建 `BEFORE UPDATE`/`BEFORE DELETE` 触发器。实测 UPDATE/DELETE 抛 `append-only`。`accepted` 记录无法改写。
- 修正以新版本表达：`fact_versions.supersedes_fact_version_id`（0002:56）、`claim_versions.supersedes_claim_version_id`（0002:78）、`artifact_records.supersedes_artifact_id`（0004:39）。测试 `test_accepted_records_cannot_be_rewritten…` 插入 `fact_v2` supersede `fact_v1`、`claim_v2` supersede `claim_v1`，断言各 2 行，原行保留。

**4. 迁移重放/路径相对性 false-green 风险** — 未发现 P0/P1
- 移动项目：`project_service._assert_no_absolute_values`（:138-146）递归校验 `project.yaml` 及所有 `_INITIAL_JSON_FILES` 不含绝对路径；`verify_project_workspace` 重放迁移并用 `integrity_check` 验证。
- 迁移重放：幂等返回空 tuple，摘要漂移 fail-closed，间隙 fail-closed，均真实执行确认。

## P0/P1 问题

无 P0，无 P1。

## 残余边界

以下为 P2 级观察，**不构成 Task 1.3 驳回理由**（成功标准未要求这些表的 `project_id`/`source_id` 外键；其值域完整性由应用层与后续 Task 1.4+ 证据合同约束），记录供后续任务跟踪：

1. **`report_snapshots.project_id`、`gate_evaluations.project_id`、`correction_proposals.project_id` 无 FK 约束**（`migrations/0003_gates_snapshots.sql:3,13`、`migrations/0005_corrections_idempotency.sql:3`）。实测可插入 `project_id='BOGUS_PROJECT'` 的 snapshot 而不报错。对比 `project_runs` 对 `project_contract_versions` 有组合 FK（0001:20-22）。影响：DB 层不阻止指向不存在项目的孤儿记录。`download_requests.source_id`（`0004:45`）同样无 FK，但该列允许 NULL 且语义为软引用，属合理设计。
2. 本验收范围仅 Task 1.3。Task 1.4+ 内容寻址文件库/证据合同、检索、渲染、安全测试不在本次驳回范围，未执行相关验证。

报告结束。Codex 保留最终接受权。
