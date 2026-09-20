# Worker-C 报告：PubMed 真实获取路线（仿 CT.gov 模式）

## 结果

已完成：`research fetch-pubmed` 真实获取路线（stdlib-only 传输、游标分页、异常分类、CAS 原始字节回执）与其合成传输测试全部通过，静态检查通过；真实网络、全仓回归与安装包清单未在本次边界内验证。

## 变更清单

| 文件 | 变更 | 行数 | 关键签名 |
|---|---|---|---|
| `src/ci_workflow/sources/connectors/pubmed_fetch.py` | 新建 | 424 | 见下 |
| `tests/integration/sources/test_pubmed_fetch.py` | 新建 | 384 | 45 个用例（含参数化） |
| `src/ci_workflow/cli.py` | 修改（仅新增） | +58 | `_research_fetch_pubmed_handler` + `research fetch-pubmed` 子解析器 |

`pubmed_fetch.py` 关键签名：

```python
def fetch_pubmed_results(
    project_root: Path, query: str, *,
    page_size: int = 200, max_pages: int = 1000, timeout: float = 30,
    max_page_bytes: int = 20 * 1024 * 1024, max_total_bytes: int = 128 * 1024 * 1024,
    efetch_batch_size: int = 200,
    transport: Transport | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> PubMedFetchResult
def build_pubmed_term_search_url(term: str, *, retstart: int, retmax: int) -> str
def build_pubmed_records_url(pmids: tuple[str, ...]) -> str
def _download(url: str, timeout: float, max_bytes: int) -> HttpPage          # 禁重定向 opener
def _classify_status(status: int, *, context: str) -> None                   # 非 200 分类
def _parse_search_page(body: bytes, *, offset: int) -> _SearchPage
def _parse_record_page(body: bytes) -> tuple[PubMedRecord, ...]
class HttpPage / Transport / CapturedPage / PubMedFetchResult
class PubMedFetchError, PubMedTimeoutError, PubMedNetworkError, PubMedHttpError,
      PubMedRateLimitedError, PubMedAccessDeniedError, PubMedServerError,
      PubMedMalformedResponseError, PubMedEmptyResultError
```

`cli.py` 仅新增（`src/ci_workflow/cli.py:544` 起为 handler，`:970` 起为子命令）：

```python
def _research_fetch_pubmed_handler(args: argparse.Namespace) -> int
# research fetch-pubmed --root/--project <项目目录> --term <检索式> [--page-size N] [--max-pages N]
```

回执字段：`query / status / pagination_complete / universe_closed=False / temporal_scope="current_records" / acquired_at(UTC) / total_count / records / search_pages / record_pages / diagnostic`；每个 `CapturedPage` 带 `raw_asset: ContentBlob`（sha256 + CAS 相对路径 + 字节数 + 媒体类型）、`request_url`、`acquired_at`。

## 测试证据

```
$ uv run pytest tests/integration/sources/test_pubmed_fetch.py -q --tb=short
.............................................                            [100%]
45 passed in 0.84s

$ uv run ruff check src/ci_workflow/sources/connectors/pubmed_fetch.py
All checks passed!            (exit 0)

$ uv run python -m mypy --no-incremental --strict src/ci_workflow/sources/connectors/pubmed_fetch.py
Success: no issues found in 1 source file      (exit 0)
```

先写测试后实现：测试首次运行时因 `ImportError: cannot import name 'pubmed_fetch'` 整体收集失败，实现后 45 项通过。覆盖点与任务书一一对应：两页 `retstart/retmax` 分页、efetch 分批、429 限流、超时/连接失败、坏 JSON/坏 XML/`<ERROR>` 文档、空结果集、重复游标死循环保护、游标不回显、重定向拒绝、页数与字节预算耗尽、CAS 字节与 sha256/相对路径一致性、`monkeypatch` opener 下的传输异常类型、HTTP 状态异常类型、检索式与限额校验、CLI 指针输出与参数校验。

## 设计说明

与 `ctgov_fetch.py` 的差异点：

1. **两段式获取**：CT.gov 是单端点游标分页；PubMed 必须先用 esearch（JSON，`retstart/retmax` 游标）枚举 PMID，再用 efetch（XML）取原文。因此回执拆成 `search_pages` 与 `record_pages` 两组 CAS 指针，而不是单一 `pages`。
2. **游标守卫形态不同**：CT.gov 用 `nextPageToken` 集合去重；PubMed 的游标是偏移量，因此改为三重守卫——回执 `retstart` 必须等于本次请求偏移（否则 `invalid_response`）、同一页不得返回零个新标识（否则 `incomplete` "重复分页游标"）、每轮循环必须新增标识，保证必然终止且不会把重复页当完成。
3. **异常类型分类**：CT.gov 只有状态字符串；本模块额外给出 8 个独立异常类型，每类带自己的 `status: ClassVar[FetchStatus]`。`fetch_pubmed_results` 在边界把异常映射为回执 `status`，所以「失败」既不冒充「无结果」，也保留独立类型供调用方与测试断言。
4. **空结果是独立信号**：`PubMedEmptyResultError` → `status="no_records"` 且 `pagination_complete=True`，且来源的空响应原始字节仍写入 CAS 作为证据（与「失败不落盘错误页」并不冲突：200 + 合法 JSON 才是证据）。
5. **efetch 分批**：`efetch_batch_size`（默认 200）避免长 URL，CT.gov 无此概念。
6. **媒体类型**：esearch 仅接受 `application/json`，efetch 接受 `application/xml|text/xml`；CT.gov 仅 JSON。
7. **回执类型**：用 pydantic `BaseModel`（与 `CtgovFetchResult` 一致）而非 `dataclass`，以便 CLI 直接 `model_dump`；`HttpPage`/`_SearchPage` 仍为 frozen dataclass。
8. **未移植** `derive_ctgov_records` 式的「重开原始字节再派生」二次校验；本模块只负责有界获取与回执。

复用 `pubmed.py` 的函数（未重写）：

- `build_pubmed_nct_search_url`：从它的输出用 `urlsplit` 单源派生 E-utilities 根地址与 `db/retmode` 默认参数，本模块只补 `term/retstart/retmax`；`efetch.fcgi` 由同一根地址派生。测试 `test_search_url_is_derived_from_the_canonical_pubmed_route` 断言 scheme/netloc/path/db 与规范构造一致。
- `parse_pubmed_efetch_xml`：全部记录解析（PMID、题名、摘要、出版类型）直接调用，未复制解析逻辑。
- `PubMedRecord`：回执记录模型。

CLI 对齐 `fetch-ctgov`：先 `verify_project_workspace`，失败写 `ContractError`（退出码 2）；成功后把回执 JSON 写入项目 CAS 并只打印精简指针（`capture_path/sha256/status/pagination_complete/records/total_count/universe_closed`），不回显正文；退出码 `0`（完成或无记录）／`7`（未完成或失败）／`2`（参数或项目校验失败）。

## 未验证项

1. **真实网络未测**：所有测试使用合成 transport 与 monkeypatch opener，未连接 `eutils.ncbi.nlm.nih.gov`。真实响应细节（esearch JSON 的 `retstart` 回显、efetch 的媒体类型、已删除 PMID 的返回行为、实际限流策略）未经真实验证。
2. **未跑全仓回归**：硬边界只允许运行本测试文件。已人工核对 `EXPECTED_CLI_CATALOG` 仅比对 `package-manifest.json` 的 `cli.catalog`（本次未改），`test_cli_help.py` 不枚举 `research` 子命令，故理论上不受影响，但未执行验证。
3. **`package-manifest.json` 未更新**：该文件在白名单外，`cli.catalog` 中未加入 `research fetch-pubmed`。若派发方要求 CLI 目录合同包含此命令，需另行授权。
4. **未做「重开 CAS 再派生」校验**：`records` 来自本次内存解析，未从 CAS 重读 XML 复核（CT.gov 的 `derive_ctgov_records` 有此步骤）。
5. **CLI `--root` 语义**：任务书写作「项目或输出目录」，实现按 `fetch-ctgov` 对齐要求必须是 `project create` 生成的项目目录（`verify_project_workspace`）；任意输出目录会被拒绝（退出码 2）。如需支持裸目录，请派发方确认。
6. **检索式语义未校验**：只做非空/长度/控制字符校验，不校验 PubMed 字段语法；来源侧 `ERROR` 文档由 `invalid_response` 兜底。
7. **无自动退避重试**：429 与 5xx 直接成为失败状态（与 CT.gov 一致），恢复由调用方负责。
8. **CLI 端到端仅覆盖成功、超时与参数校验**：页数/字节预算耗尽路径只有模块级测试，未走 CLI。
9. 未声称最终验收；验收与真实来源复核由派发方持有。
