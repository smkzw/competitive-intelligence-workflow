All required evidence gathered and all real execution commands run. Compiling the acceptance report.

---

# Task 1.4 独立验收

## 结论
**PASS** — 无 P0/P1。内容寻址、四类来源日期分离、可定位证据片段、审计回执/证据缺口双合同、追加式 0007 迁移与不可变保护均落实并通过全部真实执行。Codex 保留最终接受权。

## 实际执行证据

| 命令 | 结果 |
|---|---|
| `pytest tests/unit/test_content_store.py tests/contract/test_evidence_audit_contracts.py tests/integration/test_source_version_chain.py -q` | **10 passed** |
| `pytest -q` | **118 passed** |
| `ruff check src tests` | **All checks passed!** |
| `mypy --strict src` | **Success: no issues found in 15 source files** |
| `ci-workflow package verify --root .` | **PACKAGE_OK version=0.1.0a0 stage=phase-0-task-0.4** |

## 内容与来源版本核对

**1. 内容寻址与移动可读** — `ContentAddressedStore`（`src/ci_workflow/storage/content_store.py:46-123`）
- 同内容去重：`put_bytes` 按 sha256 生成 `evidence/raw/sha256/{前2位}/{full}.bin`，同内容返回相同 `ContentBlob`（测试 `test_same_content_deduplicates_and_different_versions_coexist` 断言 `duplicate == first`）。
- 不同内容并存：摘要不同 → 路径不同，两个版本共存。
- 路径相对且读回核摘要：`read_bytes` 复核 sha256 与 `byte_size`，不符抛 `ContentIntegrityError`；`resolve_relative` 拒绝绝对路径、`..`、`\`，并校验解析后仍落在项目内。
- 移动可读：`tests/integration/test_project_move_portability.py` 创建→`shutil.move` 改名移目录→`verify_project_workspace` 通过，且遍历文件断言不含任何机器绝对路径（`original_path`/`moved_path` 均不在内容中）。

**2. 四类日期严格分离** — 0007 新增 `source_date_assertions` 表（`migrations/0007_evidence_audit_chain.sql`）
- `date_role` 限定四种：`acquired_at/published_at/effective_at/first_disclosed_at`；保存 `observed_at`、`timezone`、`locator_json`。
- DB `CHECK`：`reported ⇒ observed_at NOT NULL`，`非 reported ⇒ observed_at IS NULL`——未公开/不适用不得拿获取时间冒充。
- 领域层 `DateEvidence`（`evidence.py:66-85`）同样强制 `state==reported ⇒ value 非空`、`state!=reported ⇒ value 为 None`，且 `_offset_datetime` 强制含时区偏移。
- 同内容稍后下载不改写历史：`add_source_version` 的 `version_id = stable_id(source_id, sha256)`，已存在即原样返回；测试断言 `duplicate_later_download.source_version_id == first` 且 `acquired_at` 保留原始值；内容变化（`changed`）生成新版本。

**3. 证据片段与追加式 0007** — `evidence_fragments` + `EvidenceRepository.add_fragment`
- `EvidenceLocator` 强制至少一个锚点（`field_path/page/table/paragraph/url`，`evidence.py:45-52`），测试验证 `field_path`、`page=4`、`table`、`paragraph` 均可回读。
- 空原文双层拒绝：领域 validator `_fragment_text_is_not_blank`（`evidence.py:142`）+ 0007 DB 触发器 `evidence_fragments_require_original_text`（`length(trim(content_text))=0 ⇒ ABORT`），测试对 Pydantic 与 `sqlite3.IntegrityError` 均覆盖。
- 0007 仅追加（新建 `content_blobs`、`source_date_assertions` 及触发器），不改 0001–0006；`_load_migrations`（`migrations.py:42-57`）要求版本 0001 连续、`test_migration_sequence_and_applied_digest_drift_fail_closed` 验证摘要漂移/断档失败关闭；`test_version_and_audit_tables_have_update_and_delete_guards` 断言 19 张表（含新增 `content_blobs`、`source_date_assertions`）均有 update/delete 追加守卫。

## 审计合同核对

**4. source receipt 与 evidence gap 双合同**（JSON Schema 2020-12 + Pydantic，`extra="forbid"`/`additionalProperties:false`）
- 全部 v1.2 审计字段在两种合同均 `required`（receipt 21 项、gap 12 项）；测试逐字段 pop 断言 JSON Schema 与 Pydantic 双失败关闭。
- 失败路线无内容摘要合法表达：`result_class != content_acquired` ⇒ `error_class` 必填、`content_sha256` 允许 `None`；`content_acquired` ⇒ 必须带 sha256、`error_class` 为 null。测试覆盖 `failed_route` 通过及 `content_sha256:None`/`error_class:None` 的非法组合失败。
- 凭据字段拒绝：`password` 注入被 `ValidationError`（JSON Schema）与 `PydanticValidationError` 双拒。
- 缺字段失败关闭：`attempt_index=0`、非法 digest、非法 `diagnostic_confidence`、无偏移 `started_at`、空 `alternative_paths` 均被双合同拒绝。
- 补充：contract 测试的 pop 循环跳过 `error_class`/`parent_attempt_id`（未直接断言其缺失失败），但二者在 Pydantic 中无默认值（必填）、在 JSON Schema `required` 中，故缺失仍被双合同拒绝——仅为测试覆盖缺口，非合同缺口。

## P0/P1 问题
无。

## 残余边界
- **`source_versions` 0002 中的四类日期列无格式/偏移 CHECK**：权威类型化存储为 0007 `source_date_assertions`（有 CHECK 且域名层强制偏移）。直接绕过域名层向 0002 日期列写裸字符串不受 CHECK 约束，但不对当前验收点构成 false-green；后续如需收紧可在新迁移追加列级约束（只追加，不改 0001–0006）。
- **contract 测试对 `error_class`/`parent_attempt_id` 缺失的失败未显式断言**（如上），属可选补强，不影响合同成立。
- Task 1.5+（事件/检查点/报告快照）、检索连接器、渲染与安全测试不在本次驳回范围，未评估。

---

报告正文已按结构产出，请 runner 落盘至 `runs/pi_ci_phase1_task14_evidence_chain.md`。
