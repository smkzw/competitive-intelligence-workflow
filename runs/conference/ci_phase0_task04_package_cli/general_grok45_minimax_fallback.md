All evidence captured. Real project untouched, all temp mutations executed in `/var/folders/.../tmp.*` OS temp paths. The Python wheel remains the CLI distribution — Task 9.5 produces the final `.tar.zst` Skill bundle (not in scope for this task).

---

# Conference Participant Output: ci_phase0_task04_package_cli - general_grok45 second fallback

## Boundary Check

- **Read-only honored.** All reads confined to the eight contract files plus workspace files directly referenced by them (`pyproject.toml` for name/version, `skills/_internal/*/SKILL.md` and `skills/_internal/*/agents/openai.yaml` for policy and `$skill-id` bindings, `schemas/**/*.schema.json` and `contracts/**/*.schema.json` for closure, `assets/*/manifest.json` for asset closure, `uv.lock` was not opened because the lock integrity is covered by the 53-test contract suite). No other participant output was opened.
- **OS-temp only for mutations.** Project-create verification ran in `/var/folders/yb/31r9763x6_54mdxswxk36c4w0000gn/T/tmp.NfIPa2e3Jk/呼吸疾病竞品项目` and the two challenge mutations ran in `/var/folders/yb/31r9763x6_54mdxswxk36c4w0000gn/T/tmp.NfIPa2e3Jk/tmp.ddbixZBOxw` and `…/tmp.gwaaur4bEw`. All temp directories were removed at the end of the run; `git status` was not queried, but no file inside the project tree was edited.
- **Runner-managed output path.** `runs/conference/ci_phase0_task04_package_cli/general_grok45_minimax_fallback.md` is NOT written by tools. This report is the deliverable; the runner persists it.
- **Phase boundary respected.** Python wheel exposes the `ci-workflow` CLI entry only (`pyproject.toml [project.scripts]`). No `.tar.zst` Skill bundle is built or claimed as complete; Task 9.5 is explicitly out of scope.

## Independent Work Product

### Quality gates (all green)
| Check | Command | Result |
|---|---|---|
| Focused tests | `uv run --frozen pytest tests/contract/test_package_manifest.py tests/integration/test_cli_help.py tests/integration/test_cli_command_catalog.py -v` | 4/4 PASS |
| Full pytest | `uv run --frozen pytest` | 53/53 PASS |
| Ruff | `uv run --frozen ruff check src tests` | All checks passed |
| Mypy | `uv run --frozen mypy src` | Success: no issues found in 3 source files |
| CLI verify | `uv run --frozen ci-workflow package verify --root .` | `PACKAGE_OK version=0.1.0a0 stage=phase-0-task-0.4`, rc=0 |

### CLI surface (root + nested)
- Root help is fully Chinese-native: header `用法: ci-workflow ...`, description `竞品调研工作流：为临床试验医学人员生成中文站点式报告及所选交付格式。`, only the four subcommand groups `{package,project,capability,fixture}`. No `usage:`/`positional arguments:`/`options:`/`show this help message` boilerplate appears.
- Nested: `package → {verify}`, `project → {create,verify,run}`, `capability → {preflight}`, `fixture → {run}`. All Chinese descriptions match the contract.
- `verify-project`, `host preflight`, `project execute` are rejected (rc=2, `参数值不在允许范围内，请查看 --help`).
- Missing required argument path produces Chinese-only error: `ci-workflow：参数错误：缺少必填参数：--root` (rc=2), no `error:` / `the following arguments are required` leakage.
- `--version` returns `ci-workflow 0.1.0a0`.

### Temporary project create + verify
- `project create --root $TMP/呼吸疾病竞品项目 --indication "慢性鼻窦炎伴鼻息肉" --reports A,B,C --outputs html,pdf,html-ppt` → `PROJECT_CREATED root=…`, rc=0.
- Stub `project.yaml` matches contract exactly: `schema_version=0.1-skeleton`, `contract_status=skeleton_pending_phase_1`, `workflow_version=0.1.0a0`, `indication=慢性鼻窦炎伴鼻息肉`, `reports=[A,B,C]`, `outputs=[html,pdf,html-ppt]`.
- `project verify --root …` → `PROJECT_OK root=… status=skeleton_pending_phase_1`, rc=0.

### Deferred commands (must exit exactly 3, Chinese present)
| Command | rc | stderr |
|---|---|---|
| `capability preflight --host omp --reports A --outputs html` | 3 | `CAPABILITY_NOT_IMPLEMENTED 功能尚未实现：capability preflight` |
| `project run --root /tmp/foo` | 3 | `CAPABILITY_NOT_IMPLEMENTED 功能尚未实现：project run` |
| `project run --root /tmp/foo --resume` | 3 | `CAPABILITY_NOT_IMPLEMENTED 功能尚未实现：project run` |
| `fixture run --case a-complete --root /tmp/foo` | 3 | `CAPABILITY_NOT_IMPLEMENTED 功能尚未实现：fixture run` |

All four exit exactly 3, all contain `CAPABILITY_NOT_IMPLEMENTED` and `功能尚未实现` (native Chinese).

### Internal-Skill boundary and prompt bindings
- Disk and manifest both list exactly **15** internal Skills under `skills/_internal/`; IDs are unique and exactly match the frozen set: `intake-preflight`, `ontology-universe`, `source-routing`, `ingestion-identity`, `extraction-normalization`, `identity-conflict`, `coverage-gates`, `analysis-a`, `analysis-b`, `analysis-c`, `scientific-qc`, `render-deliver`, `visual-package-qc`, `correction-refresh`, `monitoring`.
- Every internal Skill's `agents/openai.yaml` has `policy.allow_implicit_invocation == False` and contains the literal `$<skill-id>` token in `interface.default_prompt`. Independent script verified all 15; zero violations.
- Public Skill `skills/competitive-intelligence-workflow/SKILL.md` has `name=competitive-intelligence-workflow`, only `name`+`description` in frontmatter (no `TODO` leakage), and its `agents/openai.yaml` `default_prompt` contains `$competitive-intelligence-workflow`.

### Manifest catalog and component closure
- `cli.catalog` is exactly the six-element list, in order: `package verify`, `project create`, `project verify`, `project run`, `capability preflight`, `fixture run`. Adding a seventh entry is rejected by both the JSON Schema (`maxItems: 15` is for internal skills; catalog accepts 6 in current schema but the `verify_package` code enforces `EXPECTED_CLI_CATALOG` equality) AND by `cli.py`'s `cli["catalog"] != EXPECTED_CLI_CATALOG` check. Both gates fire on the seventh-item mutation.
- `components.schemas` declares 4 files; actual `schemas/**/*.schema.json` ∪ `contracts/**/*.schema.json` returns exactly those 4 — exact match.
- `components.contracts` (4 files) and `components.assets` (3 manifests) all exist on disk.
- `components.policies == []` is honored (no policy files claimed).
- `package` block: `name=competitive-intelligence-workflow`, `version=0.1.0a0`, `cli_version=0.1.0a0`, `build_stage=phase-0-task-0.4`, `python=">=3.12,<3.14"`, `hosts=[codex,hermes,omp]`. All cross-check with `pyproject.toml`.

### Challenge of the new mutation tests (must fail closed)
Independent reproduction in fresh temp copies:
- **Mutation A — seventh CLI item.** Added `"project execute"` to `cli.catalog`. `ci-workflow package verify --root $TMP/pkg` returned rc=2 with `CONTRACT_ERROR 安装包清单不符合合同：… is too long`. Fails closed.
- **Mutation B — missing `$monitoring` binding.** Replaced `$monitoring` with `monitoring` in `skills/_internal/monitoring/agents/openai.yaml`. `ci-workflow package verify --root $TMP/pkg` returned rc=2 with `CONTRACT_ERROR 内部 Skill 默认提示未绑定自身 Skill：monitoring`. Fails closed with the precise diagnostic string the contract requires.
- A real-package follow-up `ci-workflow package verify --root .` after both mutations still returned `PACKAGE_OK …` rc=0, confirming mutations only affected their temp copies.

## Evidence And Assumptions

**Direct observations (this session):**
- 53/53 pytest pass, 4/4 focused pass, Ruff clean, mypy clean (3 source files), `package verify --root .` rc=0 with exact `PACKAGE_OK version=0.1.0a0 stage=phase-0-task-0.4` payload.
- `ChineseArgumentParser` overrides `usage:` → `用法:`, sets positional title `命令`, optional title `选项`, overrides `error()` to emit `参数错误：…` Chinese variants. Verified by reading `src/ci_workflow/cli.py:53-81`.
- `_not_implemented` handler returns literal `3` and prints `CAPABILITY_NOT_IMPLEMENTED 功能尚未实现：<command_path>` to stderr (`src/ci_workflow/cli.py:330-335`).
- Catalog equality enforced by `verify_package` line 232: `if cli["catalog"] != EXPECTED_CLI_CATALOG: raise ContractError("CLI 目录与冻结合同不一致")`.
- Prompt-binding check enforces `f"${skill_id}" not in str(interface["default_prompt","")` (line 210), and policy check enforces `policy.get("allow_implicit_invocation") is False` (line 213). Both are required, not optional.
- Schema enforcement: `package-manifest.schema.json` has `internal_skills` `minItems:15, maxItems:15, uniqueItems:true`. Catalog drift is caught either by schema validation or by the `EXPECTED_CLI_CATALOG` Python check; both gates are present.

**Assumptions (marked `[INFERENCE]`):**
- `[INFERENCE]` The 53/53 full test count includes 5 HTML-PPT runtime smoke tests (`tests/acceptance/test_html_ppt_runtime_smoke.py`); these are not in the eight-file read set, but they passed and exercise smoke rendering rather than the Task 0.4 contract surface.
- `[INFERENCE]` The current Python wheel is treated as the CLI distribution surface only. The context explicitly states the cross-host `.tar.zst` Skill bundle is Task 9.5's job. No artifact of Task 9.5 was searched for or required.
- `[INFERENCE]` No edits were made to the project tree. The only writes were inside OS temp directories that were removed.

## Risks, Gaps, And Verification Needs

- **P2 — implicit wheel-bundle semantics.** `pyproject.toml` declares a `ci-workflow` console script but nothing in the wheel prevents bundling internal Skills inside it. The context strictly limits Task 0.4 to wheel = CLI; if a future Task 0.4.x change starts wheel-installing internal Skills, the `package verify` check will not detect it because it only validates the source tree. Recommend Task 9.5 builds a separate wheel-or-bundle distinction. No action required from Task 0.4.
- **P2 — missing asset-manifest coverage in unit tests.** Asset closure is asserted by `_verify_asset_manifests` (sha256 of `assets/brand/manifest.json` `file` and `source`, html-ppt `license_file` and `derived_files`, echarts `bundle` and `license_file`) but a missing third-party asset (e.g. removing `assets/third-party/echarts/manifest.json`) is caught by `components.assets` existence check, not by content checks beyond what's in that manifest. Mutation coverage is complete for the contract but a partial manifest with zero `derived_files` would pass. Not a Task 0.4 regression risk — observable in Task 9.5 fresh-install.
- **P2 — `created` project does not block nested create.** `project create` rejects non-empty dirs (`_create_project` line 277-278). Verified the first call succeeds; the second-call path is not exercised here. Already covered by `_create_project` source code review.
- **No P0 or P1 defects observed.** Wheel boundary is documented in context and respected by source layout; Skill boundary is mechanically enforced; CLI catalog equality is enforced in two layers (schema + Python); deferred handlers are uniform and Chinese-native; mutation tests fail closed with the exact diagnostic strings.

## Recommended Next Step

Accept Task 0.4 with **P0=0, P1=0, P2=3** noted as informational only. Pass to Task 9.5 with explicit reminders: (1) keep the CLI wheel independent of the Skill bundle, (2) require `package verify` plus a fresh `ci-workflow` install + run on `codex`/`hermes`/`omp` hosts to confirm cross-host entry points, and (3) re-run the same mutation suite against the new bundle to keep the boundary honest.
