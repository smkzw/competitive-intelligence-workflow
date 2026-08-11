All verification complete. Here is the full report.

---

# Task 1.2 独立验收

我已完整阅读 `/Users/smkzw/.hermes/SOUL.md`（文件在第 268 行结束，逐行读取完毕）。

## 结论

PASS

## 实际执行证据

四条命令均在 `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow` 真实运行，输出原文如下。

1. Task 1.2 聚焦集成测试：
   ```
   .venv/bin/pytest tests/integration/test_project_workspace.py tests/integration/test_project_move_portability.py tests/integration/test_artifact_paths.py -q
   .............................                                            [100%]
   29 passed in 0.34s
   ```

2. 全量测试套件：
   ```
   .venv/bin/pytest -q
   ........................................................................ [ 70%]
   ..............................                                           [100%]
   102 passed in 4.64s
   ```

3. Ruff 静态检查：
   ```
   .venv/bin/ruff check src tests
   All checks passed!
   ```

4. Mypy 严格类型检查：
   ```
   .venv/bin/mypy --strict src
   Success: no issues found in 11 source files
   ```

## 合同核对

### 1. v1.2 项目必需目录/文件、移动后恢复、持久数据不含机器绝对路径

| 核对项 | 证据 | 结论 |
|---|---|---|
| 必需目录精确匹配 | `project_service.py:17-37` `_DIRECTORIES` 共 19 项，与 `test_project_workspace.py:31-51` `EXPECTED_DIRECTORIES` 完全一致（state/checkpoints、evidence/{raw,fragments,library,manual-inbox,quarantine}、blockers/{A,B,C}、snapshots/{evidence,reports/A,reports/B,reports/C}、reports/{A,B,C}、logs/diagnostics、corrections/inbox、monitoring/inbox） | 通过 |
| 必需文件精确匹配 | `project_service.py:39-61` 文本+JSON 文件 + `project.yaml` + `state/project.sqlite`，与 `test_project_workspace.py:53-66` `EXPECTED_FILES` 完全一致 | 通过 |
| 空目录保护 | `project_service.py:111-112` 非空目录直接拒绝 | 通过 |
| SQLite 初始化 | `project_service.py:125-127` 创建并设 `PRAGMA user_version = 0`；`test_project_workspace.py:93-94` 断言 `integrity_check = ok` | 通过 |
| 整体移动后恢复 | `verify_project_workspace` (`project_service.py:155`) 从入参 `root.expanduser().resolve()` 重新解析，不读取任何原始路径；`test_project_move_portability.py` 用 `shutil.move` 改名换目录后 `verify_project_workspace(moved)` 通过且 `contract == contract` | 通过 |
| 持久数据不含机器绝对路径 | `_assert_no_absolute_values` (`project_service.py:131-139`) 递归扫描 `project.yaml` 及全部 `_INITIAL_JSON_FILES`（line 206-208），对 `Path(value).is_absolute()` 为真的字符串抛错；移动测试 (`test_project_move_portability.py:36-41`) 对所有非 sqlite 文件做原始/目标绝对路径字节扫描，均未命中 | 通过 |

### 2. ArtifactPathService 是 A/B/C × HTML/PDF/HTML-PPT/PPTX 唯一规范路径入口

| 核对项 | 证据 | 结论 |
|---|---|---|
| 唯一入口 | grep 全 src 仅 `storage/paths.py:22` 构造 `reports/{report.value}/{version}` 路径；`application/project_service.py:31-33` 只建目录骨架，不生成产物路径 | 通过 |
| 含 report version | `artifact()` (`paths.py:24-37`) 返回 `reports/{A\|B\|C}/{version}/{html\|report.pdf\|html-ppt\|report.pptx}`，4 格式 × 3 报告全含版本层 | 通过 |
| 拒绝小写报告 | `validate_persisted_path` (`paths.py:68-71`) `ReportKind(path.parts[1])` 对 `c` 抛 `ValueError` → `ArtifactPathViolation`；测试 `reports/c/html` 命中 | 通过 |
| 拒绝省略版本 | `paths.py:66` `len(path.parts) != 4` 拦截 3 段路径；测试 `reports/A/html` 命中 | 通过 |
| 拒绝绝对路径 | `paths.py:64` `path.is_absolute()` 拦截；测试 `/tmp/reports/A/v1.0/report.pdf` 命中 | 通过 |
| 拒绝路径跳转 | `paths.py:64` `..` part 拦截；测试 `reports/A/v1.0/../report.pdf` 命中 | 通过 |
| 拒绝非规范位置 | `paths.py:74-80` 候选集成员判断拦截；测试 `reports/A/v1.0/custom.pdf`、`reports/A/v1.0/pdf/report.pdf`、`.artifacts/report-a/html` 均命中 | 通过 |
| 版本格式校验 | `_VERSION_PATTERN` (`paths.py:8`) `^v[0-9]+(?:\.[0-9]+){0,2}(?:-[a-z0-9][a-z0-9.-]*)?$`；测试覆盖 `""`/`.`/`..`/`V1`/`v 1`/`v1/other` 全部失败 | 通过 |
| 全矩阵参数化 | `test_artifact_paths.py:11-12` `parametrize(report, list(ReportKind))` × `parametrize(output, list(OutputFormat))` = 12 组合全断言 | 通过 |

### 3. `project create --timezone/--cutoff` 进入合同版本；`project verify` 用生产双重验证且不依赖原始项目路径

| 核对项 | 证据 | 结论 |
|---|---|---|
| timezone/cutoff 进入不可变合同 | `cli.py:281-296` `_create_project` 调 `create_project_contract(timezone=args.timezone, cutoff=args.cutoff)`；`contracts.py:153-194` 将 cutoff 物化为 `datetime.combine(cutoff_date, time.max, tzinfo=zone)`（即当日 23:59:59.999999 + UTC offset），写入 `ProjectContract.data_cutoff`（frozen 模型，`contracts.py:18` `ConfigDict(extra="forbid", frozen=True)`） | 通过 |
| 物化语义验证 | `test_project_create_persists_timezone_and_cutoff_without_guessing` 断言 `America/New_York` + `2024-02-29` → `data_cutoff == "2024-02-29T23:59:59.999999-05:00"`；`outputs == ["html","pdf"]`（HTML 强制首位）；`"root" not in project` 且 `str(project_root) not in json.dumps(project)` | 通过 |
| verify 用生产双重验证 | `cli.py:299-309` `_verify_project` → `verify_project_workspace(Path(args.root))`；`project_service.py:185-194` 调 `validate_project_contract_document(item, schema)`（`contracts.py:97-106`）= 同一入口先 `Draft202012Validator(format_checker=iana)` 再 `ProjectContract.model_validate` | 通过 |
| 不依赖原始项目路径 | `verify_project_workspace` (`project_service.py:154-220`) 全程仅用入参 `root` 解析出的 `project_root`，读取相对路径文件；无任何原始/创建时路径字段；移动测试改名换父目录后仍通过 | 通过 |

## P0/P1 问题

无 P0/P1 问题。四条验收命令全绿，三项合同核对逐项通过。明确不将 Task 1.3 SQLite 业务表、证据库或渲染能力作为本次驳回条件。

## 残余边界

1. `_assert_no_absolute_values`（`project_service.py:206-208`）仅扫描 `project.yaml` 与 `_INITIAL_JSON_FILES`（coverage/A,B,C + artifact_manifest 共 4 个 JSON），不扫描 `events/*.jsonl`、`receipts/*.jsonl`、`logs/*.md` 等文本文件。当前这些文件均为固定模板、不含机器路径，且移动测试对所有非 sqlite 文件做了字节级绝对路径扫描兜底——对 Task 1.2 可接受；后续业务写入 JSONL 时需复用同一绝对路径断言。
2. SQLite 仅 `PRAGMA user_version = 0` + `integrity_check`，无业务表（Task 1.3 范围）；移动测试显式跳过 `.sqlite` 字节扫描（`test_project_move_portability.py:37`），因为业务表尚未写入任何路径文本。
3. `coverage/*.json` 初始 `status="not_started"`，无渲染产物（Task 1.5 范围）。
4. `ArtifactPathService.validate_persisted_path` 候选集枚举全部 `OutputFormat`，当前 4 格式；若未来新增格式需同步更新枚举与候选集——这是设计内约束，非遗漏。

以上残余项均在 Task 1.2 明确范围之外，不构成驳回条件。最终接受权属于 Codex。
