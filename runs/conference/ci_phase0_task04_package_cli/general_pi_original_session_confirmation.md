Full suite: **53 passed** (was 52; the new drift test added one). No regressions. All evidence collected. Delivering the closure report.

---

# Original-session closure

## Evidence

**Focused tests + package verify (executed this pass, Python 3.13.13):**
```
uv run pytest tests/contract/test_package_manifest.py \
              tests/integration/test_cli_help.py \
              tests/integration/test_cli_command_catalog.py \
              tests/contract/test_dependency_manifest.py -v
→ 6 passed in 1.07s

uv run ci-workflow package verify --root .
→ PACKAGE_OK version=0.1.0a0 stage=phase-0-task-0.4   exit=0

uv run pytest -q   (full suite)
→ 53 passed in 3.60s
```

**Five explicit Task-0.4 checks, each run independently (not trusting the mutation tests):**

1. Exact six-command schema — `package-manifest.json` `cli.catalog` = `['package verify','project create','project verify','project run','capability preflight','fixture run']`, count 6; matches `EXPECTED_CLI_CATALOG` in `cli.py:37-44` and the contract test. ✓
2. Seventh-command rejection — mutated manifest `catalog.append('project execute')` → `CONTRACT_ERROR 安装包清单不符合合同：… is too long`, **exit 2**. ✓ (schema `minItems/maxItems:6` + runtime `cli['catalog'] != EXPECTED_CLI_CATALOG` at `cli.py:231-233` both gate this.)
3. `$skill-id` runtime rejection — stripped `$` from `monitoring` agent `default_prompt` in a copied package → `CONTRACT_ERROR 内部 Skill 默认提示未绑定自身 Skill：monitoring`, **exit 2**. ✓ (runtime check at `cli.py:210-211`; public-skill binding at `cli.py:191-194`.)
4. Deferred exit exactly 3 — all four deferred commands (`capability preflight`, `project run`, `project run --resume`, `fixture run`) return **exit 3**, stderr `CAPABILITY_NOT_IMPLEMENTED 功能尚未实现：…`. ✓ (handler `_not_implemented` `cli.py:330-335`; test tightened from `!=0` to `==3` at `test_cli_command_catalog.py:70`.)
5. Chinese-native help/error — `--help` shows `用法:`/`命令:`/`选项:`/`显示帮助并退出`/`显示版本并退出`; missing-arg error `ci-workflow project create：参数错误：缺少必填参数：--root, --indication, --reports`; grep confirms **zero** leaks of `usage:`, `positional arguments:`, `options:`, `show this help message`, `show program's version`. ✓ (`ChineseArgumentParser` `cli.py:53-81`; test asserts absence at `test_cli_help.py:30-37`.)

**Task 0.4 vs Task 9.5 bundle boundary (context line 32):** Applied. The Python wheel deliberately carries only the CLI module; the full installable `.tar.zst` bundle, fresh install, and tri-host entry acceptance belong to approved-plan **Task 9.5**. Reviewers must note the wheel boundary but must not treat 9.5 as a 0.4 pass condition. My original P0-1 (wheel omits manifest/skills/schemas/contracts/assets) is therefore **rescoped to a noted boundary**, not a Task 0.4 defect.

**Closure of original-session defects:**
| Original defect | Status this pass |
|---|---|
| P0-1 wheel omits package files | Rescoped to Task 9.5 boundary per context line 32 — **not a 0.4 blocker** |
| P2-1 `project.yaml` is JSON with `.yaml` extension | Unchanged; fail-closed; non-blocking P2 |
| P2-2 English argparse text | **Closed** — `ChineseArgumentParser`, verified no English leak |
| P2-3 skeleton strings undocumented | Unchanged; non-blocking P2 |
| (new, prior note) catalog-drift / `$skill-id` runtime blind spot | **Closed** — runtime checks + mutation test added and verified |

## Verdict

**P0 = 0, P1 = 0.**

All four focused Task 0.4 test files pass (6 functions), `package verify --root .` exits 0, and all five named acceptance checks (six-command schema, seventh-command rejection, `$skill-id` runtime rejection, deferred exit exactly 3, Chinese-native help/error) are independently confirmed by real command output. The wheel-boundary concern is explicitly assigned to Task 9.5 by the approved context and is not a Task 0.4 pass condition. Remaining P2 items (`project.yaml` extension, skeleton-string docs) are non-blocking polish.

**Recommend acceptance of Phase 0 Task 0.4**, with the Task 9.5 bundle boundary carried forward as a tracked deliverable.
