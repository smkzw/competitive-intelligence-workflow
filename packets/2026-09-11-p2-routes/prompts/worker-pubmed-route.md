Delegated mode（执行模块角色：Worker-C，有界执行）

# 硬边界

1. 唯一工作区：/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow。禁止访问路径含"竞品调研工作流"的旧中文工程。
2. 允许写入的文件（严格白名单，其他一律不碰）：
   - 新建 src/ci_workflow/sources/connectors/pubmed_fetch.py
   - 新建 tests/integration/sources/test_pubmed_fetch.py
   - 修改 src/ci_workflow/cli.py（仅新增 research fetch-pubmed 子命令，不动其他代码）
   - 新建 packets/2026-09-11-p2-routes/runs/worker-c-report.md（你的输出报告）
3. 禁止：git 任何写操作（add/commit/restore/clean）、修改本清单外任何文件、运行会写仓库的命令（uv run pytest 只允许跑你自己的新测试文件）、访问网络（测试全部用合成 transport，不真连 PubMed）。
4. 不声称最终验收；派发方持有验收。

# 任务：PubMed 真实获取路线（仿 CT.gov 模式）

先读这三个文件作为模式范本：
- src/ci_workflow/sources/connectors/ctgov_fetch.py（获取器范本：stdlib-only、禁重定向 opener、超时/限流/坏响应分类、CAS 原始字节保存、游标/预算、失败不冒充无数据）
- src/ci_workflow/sources/connectors/pubmed.py（已有的 URL 构造 :104 与 XML 解析 :125，复用它们，不要重写）
- src/ci_workflow/cli.py 中 _research_fetch_ctgov_handler（CLI 接法范本）

实现：
1. pubmed_fetch.py：`fetch_pubmed_results(query/term, ...)`，复用 pubmed.py 的 URL 构造与 XML 解析；要求：
   - stdlib only（urllib.request，自定义 opener 禁 redirect）
   - 区分超时/HTTP 错误/限流(429)/坏 XML/空结果，各自抛不同异常类型，绝不把失败当"无结果"
   - 原始响应字节写入 ContentAddressedStore（照抄 ctgov_fetch 的用法），返回带 CAS 指针的回执 dataclass
   - 回执含：query、总数、条数、原始字节 sha256、CAS 相对路径、获取时刻 UTC、`universe_closed: Literal[False]`、`temporal_scope: "current_records"`（与 ctgov 同样的诚实限制字段）
2. cli.py：`research fetch-pubmed --term <词> --root <项目或输出目录>`，行为对齐 fetch-ctgov（输出精简 JSON 指针，不回显正文）
3. tests/integration/sources/test_pubmed_fetch.py：全部合成 transport（monkeypatch urllib/opener），覆盖：正常两页分页（retstart/retmax 游标）、429 限流、超时、坏 XML、空结果集、重复游标死循环保护、CAS 字节写入与 sha 一致、CLI 入口参数校验。先写测试看它失败，再实现。

# 验证命令（只许跑你自己的）

uv run pytest tests/integration/sources/test_pubmed_fetch.py -q --tb=short
uv run ruff check src/ci_workflow/sources/connectors/pubmed_fetch.py
uv run python -m mypy --no-incremental --strict src/ci_workflow/sources/connectors/pubmed_fetch.py

# 输出报告（worker-c-report.md，Markdown）

## 结果
完成/未完成一句话。
## 变更清单
逐文件：新建/修改 + 行数 + 关键函数签名。
## 测试证据
命令 + 通过数（贴尾行）。
## 设计说明
与 ctgov_fetch 的差异点；复用了 pubmed.py 哪些函数。
## 未验证项
如实列出（如：真实网络未测）。
