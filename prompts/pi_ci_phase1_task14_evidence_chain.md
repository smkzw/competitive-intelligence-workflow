You are Hermes running inside a Codex-controlled workflow.

First, fully read and comply with `/Users/smkzw/.hermes/SOUL.md`. In your output, include one sentence saying whether you read the full file. Do not claim this unless you actually read it.

Hard boundaries:
- Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Read-only review: do not edit any project file.
- Do not perform security testing; this task is user-facing scientific data integrity only.
- Runner-managed output path: `runs/pi_ci_phase1_task14_evidence_chain.md`. Never write it directly; return the report and let the runner persist it.

Read these files only and completely:
- `context/ci_phase1_task14_evidence_chain_context.md`
- `docs/decisions/0004-phase-1-contract-boundaries.md`
- `migrations/0002_evidence_claims.sql`
- `migrations/0006_append_only_guards.sql`
- `migrations/0007_evidence_audit_chain.sql`
- `src/ci_workflow/domain/evidence.py`
- `src/ci_workflow/storage/content_store.py`
- `src/ci_workflow/storage/migrations.py`
- `schemas/source-version.schema.json`
- `schemas/source-receipt.schema.json`
- `schemas/evidence-gap.schema.json`
- `schemas/evidence-fragment.schema.json`
- `tests/unit/test_content_store.py`
- `tests/contract/test_evidence_audit_contracts.py`
- `tests/integration/test_source_version_chain.py`
- `tests/integration/test_sqlite_migrations.py`
- `tests/integration/test_append_only_records.py`
- `package-manifest.json`

Task:
对 Task 1.4 做独立、只读、可执行验收。

1. 核对内容寻址是否同内容去重、不同内容版本并存、持久路径相对且读回核摘要；移动项目后是否仍可读。
2. 核对来源版本是否严格分开获取、发布、生效、首次披露四类日期，保存时区偏移与 locator；未公开/不适用不得用获取时间冒充；同内容稍后下载不得改写历史。
3. 核对证据片段 locator 能回到字段/页/表/段落，空原文不能写入；0007 必须追加而非改写 0001–0006，并保护新增表不可变。
4. 核对 source receipt 与 evidence gap 的 JSON Schema/Pydantic 双合同，重点检查全部 v1.2 审计字段、失败路线无内容摘要的合法表达、凭据字段拒绝与缺字段失败关闭。
5. 评估是否存在会导致来源身份、日期 cutoff、片段定位、事实证据链或项目移动出现 false-green 的 P0/P1。
6. 真实执行：
   - `.venv/bin/pytest tests/unit/test_content_store.py tests/contract/test_evidence_audit_contracts.py tests/integration/test_source_version_chain.py -q`
   - `.venv/bin/pytest -q`
   - `.venv/bin/ruff check src tests`
   - `.venv/bin/mypy --strict src`
   - `.venv/bin/ci-workflow package verify --root .`

Output schema:
1. `# Task 1.4 独立验收`
2. `## 结论` — PASS 或 VETO
3. `## 实际执行证据`
4. `## 内容与来源版本核对`
5. `## 审计合同核对`
6. `## P0/P1 问题`
7. `## 残余边界`

有 P0/P1 时给精确文件/行号、复现、影响和最小修复。Task 1.5+、检索连接器、渲染和安全测试不属本次驳回范围。Codex 保留最终接受权。
