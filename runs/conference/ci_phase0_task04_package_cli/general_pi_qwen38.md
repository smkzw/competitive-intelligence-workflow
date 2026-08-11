All confirmations complete. 15 internal skill directories, 5 legacy migration records all `runtime_dependency=False`. I have a complete, independently-verified evidence base.

Here is my complete conference participant report:

---

# Conference Participant Output: ci_phase0_task04_package_cli - general_pi_qwen38

## Boundary Check

I am `general_pi_qwen38`, acting as an independent read-only acceptance peer for Phase 0 Task 0.4. I confirm:

- **Scope respected:** I executed only read-only verification — ran frozen tests, `package verify`, CLI help, temp project create/verify, deferred negatives, built a wheel/sdist into `/tmp`, and inspected contents. No source files, manifests, tests, or production paths were modified. No other participant's output was read.
- **Tools policy honored:** I did not perform final visual/PPT/browser/clinical acceptance (out of scope for this task and reserved for Codex).
- **Identity/route:** Effective route `cms-smk/cms-model` treated as authoritative per the dispatch override. No provider switch attempted.
- **Effective route note for Codex:** My assigned primary was `alibaba/qwen3.8-max`; the daytime CMS replacement is in effect. I flag one routing-process observation below (a stale-tool false positive I caught and retracted) so Codex can weigh whether the replacement route's tool-fidelity differs — it does not affect product verdicts.

## Independent Work Product

### A. Executed commands and outcomes

| Command | Outcome | Verdict |
|---|---|---|
| `uv run pytest tests/contract/test_package_manifest.py tests/integration/test_cli_help.py tests/integration/test_cli_command_catalog.py -v` | 3 passed | ✅ |
| `uv run pytest -q` (full suite) | 52 passed | ✅ |
| `uv run ci-workflow package verify --root .` | `PACKAGE_OK version=0.1.0a0 stage=phase-0-task-0.4`, exit 0 | ✅ |
| `uv run ci-workflow --help` / `--version` | Chinese description, 4 groups; `ci-workflow 0.1.0a0` | ✅ |
| `project create` + `project verify` (temp dir) | `PROJECT_CREATED` / `PROJECT_OK`, exit 0 | ✅ |
| 4 deferred commands (`capability preflight`, `project run`, `project run --resume`, `fixture run`) | All exit 3, stderr `CAPABILITY_NOT_IMPLEMENTED 功能尚未实现：…` | ✅ fail-closed |
| 3 forbidden aliases (`verify-project`, `host preflight`, `project execute`) + 4 incomplete groups | All exit 2 (argparse rejection) | ✅ no aliases |
| `uv build -o /tmp/ci_build` | wheel + sdist built | ✅ build |
| Wheel/sdist content inspection | **Only `ci_workflow/` Python module** — see Defect P0-1 | ⚠️ |

### B. Independently verified contract closures (not trusting the passing tests)

- **Public/Internal Skill boundary:** 1 public skill (`skills/competitive-intelligence-workflow/SKILL.md`, frontmatter `name: competitive-intelligence-workflow`, no `policy` block by design). **15** internal skill directories match the manifest's 15 declared ids and `EXPECTED_INTERNAL_SKILLS` in `cli.py` exactly. All 15 carry `allow_implicit_invocation: false` and a `default_prompt` binding `$<skill_id>`. Confirmed by direct grep, not by test attestation.
- **Four mandatory headings** (`## 输入合同`, `## 输出合同`, `## 禁止行为`, `## 失败与恢复`) present in all 15 internal `SKILL.md` files (independent grep).
- **CLI catalog:** exactly 6 frozen commands; `argparse` subparser structure guarantees no aliases; forbidden forms return exit 2.
- **Schema closure:** 4 declared schemas == 4 actual under `schemas/` + `contracts/`. `migration/legacy_manifest.schema.json` is correctly **excluded** (legacy evidence, `runtime_dependency=False` for all 5 records) — a deliberate, correct boundary, not a gap.
- **Kangzhe contract:** `runtime.files` lists 18 files, all present; digest verification path covers them.
- **pyproject ↔ manifest ↔ module version:** `name`, `version`, `cli_version` all `0.1.0a0` and consistent across `pyproject.toml`, `package-manifest.json`, `ci_workflow.__version__`.

### C. Defects found

#### **P0-1 — Built wheel/sdist omits the entire workflow package; installed artifact is unverifiable and unusable as a "versioned workflow package."**

- **Evidence:** Wheel `RECORD` and `zipfile -l` show only `ci_workflow/__init__.py`, `ci_workflow/__main__.py`, `ci_workflow/cli.py` + dist-info. Sdist (`tar tzf`) adds only `README.md` + `pyproject.toml`. **Absent:** `package-manifest.json`, `schemas/`, `skills/` (public + 15 internal), `contracts/`, `assets/`. No `[tool.uv.build-backend.data]` / `force-include` / `package-data` / `wheel` config exists in `pyproject.toml`; `[tool.uv.build-backend] module-name = "ci_workflow"` packages only the Python module.
- **Reproducible:**
  ```
  uv build -o /tmp/ci_build
  python3 -m zipfile -l /tmp/ci_build/competitive_intelligence_workflow-0.1.0a0-py3-none-any.whl
  # → 3 ci_workflow/*.py + dist-info only
  uv venv --python 3.13 /tmp/v && uv pip install --python /tmp/v/bin/python /tmp/ci_build/*.whl
  /tmp/v/bin/ci-workflow package verify --root <any-empty-dir>
  # → ModuleNotFoundError or CONTRACT_ERROR 缺少文件：…/package-manifest.json
  ```
- **Why it matters:** §6.1 contract is "用户安装一个版本化工作流包，调用一个公开入口 Skill。包内包含：内部领域 Skills；类型定义、JSON Schema…；包清单、组件版本、摘要和兼容范围。" `package verify` (`cli.py:127-136`) reads `package-manifest.json`, `schemas/package-manifest.schema.json`, and `pyproject.toml` from `--root`. A non-editable `pip install` of the published wheel yields a CLI that can never pass `package verify` and has no skills to invoke. The package is, **as shipped**, not the product §6.1 describes.
- **Masking:** `uv run … package verify --root .` passes because uv installs the project **editable** (`src/` layout) and `--root .` points at the source tree. The defect is invisible in the developer flow and invisible to the frozen tests (which run against `ROOT`, the repo). This is the "old-product false green" pattern the objective explicitly targets — here, "source-tree green, install-broken."
- **Severity:** For Task 0.4's *stated* deliverable ("安装包清单…唯一中文 CLI"), the manifest/CLI are correct and the frozen gates pass against the source tree — so this is a **P1 against this task's literal acceptance bars**. For the *product* (§6.1 installability), it is a **P0**: the shippable artifact is non-functional. I recommend Codex treat it as **P0** because "安装包" (installation package) is in the task title and §6.1 makes install-time self-containment mandatory.
- **Remediation (concrete):** Add data inclusion to the uv build backend, e.g.:
  ```toml
  [tool.uv.build-backend.data]
  # ship the workflow package alongside the python module
  ```
  or switch to explicit `force-include` mapping `package-manifest.json`, `schemas/`, `skills/`, `contracts/`, `assets/` into the wheel root (or a known data prefix), and make `package verify` resolve its `--root`/data dir relative to the installed package location (`importlib.resources`) when `--root` is omitted. Add a contract test that builds the wheel, installs it into an ephemeral venv, and asserts `ci-workflow package verify` succeeds against the installed data — this closes the masking hole.

#### **P2-1 — `project.yaml` is written and read as JSON but uses a `.yaml` extension (fail-closed, but contract-misleading).**

- **Evidence:** `_create_project` (`cli.py:239`) writes via `_atomic_json_write(root / "project.yaml", project)` using `json.dump`; `_verify_project` (`cli.py:246`) reads via `_load_json` (JSON parser). Reproducible: a valid YAML file (with a `# comment` or block sequence) named `project.yaml` produces `CONTRACT_ERROR 文件不是有效的 JSON：…/project.yaml（Expecting value）`, exit 2.
- **Severity:** Fail-closed (no correctness hole); but the extension implies YAML semantics a medical user might reasonably use when hand-editing. P2 (usability/contract-clarity).
- **Remediation:** Either rename to `project.json` (matches the actual format), or read via `_load_json_or_yaml` and document that both are accepted. Prefer rename for unambiguous format.

#### **P2-2 — argparse-generated CLI text is English, inconsistent with the native-Chinese user-facing-copy rule.**

- **Evidence:** `ci-workflow project create` with a missing arg prints `the following arguments are required: --indication, --reports`; `--help` shows `show this help message and exit`; bad subcommand prints `error: argument … invalid choice`. These are CPython `argparse` defaults.
- **Contract basis:** AGENTS.md:27 — "User-facing copy must be native Chinese… Do not expose… unnecessary English system terminology." Design spec §3.3/§3.4 scope Chinese-native requirements to the **report/conversation** layer, not the CLI shell — so the strongest basis is AGENTS.md, not the v1.2 spec. The frozen `test_cli_help.py` only asserts *presence* of Chinese strings, not *absence* of English, so it passes despite this (a "假绿" gap in the test, mild).
- **Severity:** P2. Remediation: either set `argparse` formatter/`gettext` locale to zh, or wrap a custom `HelpFormatter` + override `error()` to emit Chinese; strengthen `test_cli_help.py` to assert no English boilerplate leaks.

#### **P2-3 — Skeleton contract-status magic strings are undocumented.**

- **Evidence:** `_create_project`/`_verify_project` hardcode `schema_version: "0.1-skeleton"`, `contract_status: "skeleton_pending_phase_1"`. Grep of `docs/`, `plans/`, `.trellis/` finds no authoritative definition (only `task_store.py`'s unrelated PRD skeleton). Create↔verify are internally consistent, so not a correctness issue, but the values are untraceable to a contract document.
- **Severity:** P2 (traceability). Remediation: document the Phase-0 skeleton contract-status vocabulary in the plan or a short contract note.

### D. Defects I investigated and **rejected** (negative results, for audit trail)

- **RETRACTED — "playwright==1.61.0 unsatisfiable":** My first check (`pip index versions playwright` in a Python 3.9 venv) returned latest `1.60.0`, suggesting the pin was unsatisfiable. Cross-checking `uv.lock` (real wheel URLs on `files.pythonhosted.org`, upload 2026-06-29) and the **PyPI JSON API** (`/pypi/playwright/json` → `1.61.0` present, 8 files; latest is now `1.62.0`) confirmed 1.61.0 exists. The stale `pip index` view was the error, not the pin. **Process note for Codex:** this stale-index false positive is a reminder that single-tool index views can mislead; the lock file + registry API are authoritative.
- **REJECTED — "`migration/legacy_manifest.schema.json` undeclared":** Correctly out of scope; `runtime_dependency=False` for all 5 legacy records, guarded by `test_legacy_manifest_contract.py`. Deliberate boundary.
- **REJECTED — "public skill has no `policy.allow_implicit_invocation`":** By design. The public skill *is* the implicit entry; only internal skills must be non-implicit. Verifier correctly checks policy only on internal skills (`cli.py:163-166`).

## Evidence And Assumptions

- **Frozen tests:** 3/3 pass; full suite 52/52 pass (Python 3.13.13, which satisfies `>=3.12,<3.14`).
- **Real CLI outputs:** captured verbatim above (exit codes 0/2/3 as specified).
- **Wheel/sdist contents:** from `python3 -m zipfile -l` and `tar tzf` on freshly built artifacts in `/tmp/ci_build`; `RECORD` inspected.
- **Installability claim:** proven by building wheel, `uv pip install --no-deps` into a py3.13 venv, and showing site-packages contains only `ci_workflow/` (no manifest/skills/schemas).
- **playwright satisfiability:** PyPI JSON API (`https://pypi.org/pypi/playwright/json`) confirms 1.61.0 exists.
- **Assumptions / [INFERENCE]:**
  - [INFERENCE] The "installation package" acceptance bar in Task 0.4 is intended to mean the **built** artifact must be self-contained per §6.1, not merely that the source tree verifies. If Codex rules that Task 0.4 only requires the source-tree manifest to close (wheel data inclusion deferred to a later task), P0-1 downgrades to P1 and the task could pass with that scope explicitly narrowed. **This is the single decision I most need from Codex.**
  - [INFERENCE] `argparse` English text is in scope for the AGENTS.md native-Chinese rule; if Codex holds that CLI shell boilerplate is out of scope (spec §3.3/§3.4 limit Chinese-native to report/conversation), P2-2 is a style note, not a defect.

## Risks, Gaps, And Verification Needs

1. **Highest-impact risk (P0-1):** the published wheel is non-functional as a workflow package. This is exactly the class of "源码自证 / 旧产物假绿" the objective names: tests pass against the source tree while the installable artifact is broken. The masking is structural (editable install + `--root .`). Needs an install-time contract test.
2. **Test-suite blind spot:** `test_cli_command_catalog.py` asserts deferred commands return non-zero *and* emit `CAPABILITY_NOT_IMPLEMENTED` — good — but it cannot distinguish exit-3 (real `_not_implemented`) from exit-2 (argparse error) for the *deferred* path because it only checks `returncode != 0`. I verified exit 3 manually; the test would still pass if a deferred handler accidentally fell through to argparse. Minor hardening opportunity.
3. **Format ambiguity (P2-1)** is fail-closed but will surface as a confusing error for any medical user who edits `project.yaml` as YAML.
4. **Documentation traceability (P2-3):** skeleton status strings have no contract home; future phases will need a versioned vocabulary.

**Bounded questions for Codex:**
- **Q1 (blocking P0-1 severity):** Does Task 0.4's "安装包" acceptance require the **built wheel/sdist** to carry `package-manifest.json` + `schemas/` + `skills/` + `contracts/` + `assets/` (per §6.1), or is wheel-data inclusion explicitly deferred to a later task while Task 0.4 only closes the **source-tree** manifest? If the former → P0-1 blocks acceptance; if the latter → I downgrade to P1 with the scope narrowing recorded.
- **Q2 (P2-2):** Is CLI `argparse` boilerplate (help/error text) in scope for the native-Chinese rule (AGENTS.md), or is it out of scope per spec §3.3/§3.4 (report/conversation only)?

**Safe provisional path if Q1 is unanswered:** treat P0-1 as a **P0 hold** — do not recommend acceptance — because "安装包" is in the task title and §6.1 is explicit; the cost of shipping a non-verifiable wheel outweighs the cost of adding build-backend data inclusion now.

## Recommended Next Step

**Do not recommend acceptance yet.** P0-1 is open.

- **If Codex confirms §6.1 installability is in-scope for Task 0.4 (my reading):** block acceptance on P0-1. Remediation: add `[tool.uv.build-backend.data]`/`force-include` for the manifest+schemas+skills+contracts+assets, make `package verify` resolve data via `importlib.resources` when `--root` is absent, and add a **wheel-install contract test** (build → ephemeral venv install → `ci-workflow package verify` succeeds against installed data). Re-run in this same session to confirm P0=0.
- **If Codex explicitly narrows Task 0.4 to source-tree manifest closure (wheel deferred):** record the narrowing, downgrade P0-1→P1, and acceptance is then contingent only on the agreed follow-up task; the remaining P2 items are non-blocking polish.
- **Regardless:** address P2-1 (rename `project.yaml`→`project.json` or accept YAML) and P2-3 (document skeleton status) as cheap cleanup; decide P2-2 per Q2.

I remain available in this same Pi session for Codex's targeted follow-up once Q1/Q2 are answered or after remediation, to re-verify P0-1 closure.
