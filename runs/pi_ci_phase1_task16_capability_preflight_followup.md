Temp artifact removed. Independent acceptance for Task 1.6 follow-up, re-confirmed in this same session.

---

# Task 1.6 独立验收（修订后复核，同 session 恢复）

## 修订后 PASS/FAIL

**PASS**

## 真实命令计数锚点

| 命令 | 结果 |
|---|---|
| `uv run pytest tests/contract/test_capability_matrix.py tests/integration/test_capability_preflight.py tests/integration/test_selective_capability_blocking.py -q` | **11 passed** (0.71s) |
| `uv run pytest -q` | **132 passed** (5.94s) |
| `uv run ruff check src tests` | passed (exit 0) |
| `uv run mypy --strict src` | 20 files, no issues (exit 0) |
| `uv run ci-workflow package verify --root .` | `PACKAGE_OK version=0.1.0a0 stage=phase-0-task-0.4` |
| `git diff --check` | exit 0 |
| `uv run ci-workflow capability preflight --host local --reports A,B,C --outputs html,pdf,html-ppt,pptx --json .artifacts/reviewer-preflight-v2.json` | `PREFLIGHT_COMPLETE`，overall=`ready`，exit 0 |

实机 v2 概览：12/12 能力 `ready`（`login_browser`/`ocr`=`not_applicable`，未选对应来源/无 OCR 需求）；`http_network` detail=`ClinicalTrials.gov 第 1 次检查返回 200`（首次成功即停）；矩阵通过 `capability-matrix.schema.json`（Draft 2020-12）校验。

复核的文件（`capability_preflight.py` MD5 `c3332bb0…`、`test_capability_preflight.py` MD5 `28c76a75…`）与上一轮验收时逐字节一致，无新改动；逻辑块与已验证结论相同。

## P0/P1

无

## 残留 P2/P3

1. **`http_network` 三次重试是轻量预检自愈，不是 Task 2.3 的完整来源替代路线穷尽**（`capability_preflight.py:230-245`）。实现正确只做短退避重试，未冒充多来源替代路线；符合规格 §6.2。非缺陷，仅提醒后续 Task 2.3 来源恢复为独立职责。
2. **`http_network` 阻断时 `user_messages` 用通用文案**「请确认网络可用…」，未在用户消息中提示「已做 3 次短重试」（detail 字段已含「连续 3 次…已完成短间隔重试」）。中文、含影响与下一步，符合规格；P3 表达充分性观察。

## 重点复核

**3 次网络尝试：两个短退避、成功即停、连续失败才阻断**
通过。`capability_preflight.py:230-245`：`for attempt in range(1,4)`，`urlopen(timeout=5)` 成功即 `return`（成功即停）；`except (OSError, TimeoutError)` 记 `last_error`，`attempt<3` 时 `time.sleep(0.25 * 2**(attempt-1))` → 退避 `[0.25, 0.5]`；三次全失败 `raise CapabilityProbeFailure("连续 3 次…已完成短间隔重试")`，`_failure_detail` 首分支转中文。测试（`test_capability_preflight.py:70-118`）monkeypatch `urlopen`/`time.sleep`：前两次超时第三次成功 → `available=True`、`attempts==3`、`delays==[0.25,0.5]`；持续 OSError → `available=False`、`attempts==3`、`delays==[0.25,0.5]`、detail 含「连续 3 次」。未把三次重试称为完整来源路线穷尽。

**LibreOffice/soffice 单独存在时 blocked；显式指定 Office 或 PowerPoint 才 ready**
通过。`capability_preflight.py:282-287`：`available = bool(configured and shutil.which(configured)) or Path("/Applications/Microsoft PowerPoint.app").exists()`，已移除 soffice/LibreOffice 自动判定。测试（`test_capability_preflight.py:195-207`）monkeypatch `Path.exists` 仅匹配 `LibreOffice.app`、`shutil.which("soffice")` 返索引进 → `office.available is False`。实机探针（上一轮已验证，逻辑未变）：本机 PowerPoint 与 LibreOffice 并存，默认路径 `ready` 靠 PowerPoint；LibreOffice-only（monkeypatch）→ `False`；显式 `CI_WORKFLOW_OFFICE_COMMAND=soffice` → `True`（`shutil.which` 命中 `/opt/homebrew/bin/soffice`）。

**是否引入新 P0/P1、是否保留首轮全部选择性阻断与恢复行为**
未引入。全库 132 通过，ruff/mypy/package/diffcheck 全绿；`plan_environment_recovery`（`capability_preflight.py:598-640`）未改动，「仅重排已修复能力及已解除全部阻断的下游、仍有另一能力阻断不提前重排、研究恢复含 analyze/snapshot/render/verify」行为保留；`test_selective_capability_blocking.py` 的两个 exact node（合同/内联一致、PPTX 只阻断中文指引）与 `test_capability_matrix.py`（schema 双合同失败）全部通过。

## 是否同意 Codex 接受 Task 1.6

**同意接受。** 修订后无 P0/P1，11 项精确测试与全库 132 项回归通过，ruff/strict mypy/包校验/diff-check 全绿，实机 v2 矩阵 12/12 可用且有真实探针锚点，http 重试与 office 语义经真实命令 + monkeypatch 探针验证，首轮全部选择性阻断/恢复行为保留。Codex 接受前复核（非阻断）：确认 `office_renderer` 的「PowerPoint 或显式指定 Office」口径符合康哲 PPTX 验收预期；关注 P2/P3 #2 的 `http_network` 用户消息是否需提示已重试。

**清理：** `.artifacts/reviewer-preflight-v2.json` 已删除；工作树仅含实现本体的未提交改动。

**SOUL.md 读取说明：** 本轮 session 恢复时已完整读取 `/Users/smkzw/.hermes/SOUL.md` 至末尾（共 267 行，`.md:1-267` 确认 EOF）。
