# ADR 0001：Phase 0 技术栈与依赖基线

- 状态：已采用
- 日期：2026-08-10
- 适用版本：`0.1.0a0`

## 决定

### Python 与类型合同

- Python 固定为 `>=3.12,<3.14`。目标宿主不依赖 macOS 自带 Python；安装器和开发环境均以 `uv.lock` 解析的解释器及环境为准。
- Pydantic 2.13.4 负责项目合同、状态和科学数据的入口校验。
- JSON Schema 4.26.0 负责跨语言、跨宿主和产物清单的机器合同。
- PyYAML 6.0.3 只读取版本化政策和报告合同，不承载运行状态真源。

### 报告渲染

- Jinja2 3.1.6 生成站点式 HTML 和格式原生模板。
- ReportLab 5.0.0 生成原生 PDF。拒绝以浏览器打印 HTML 冒充原生 PDF，因为后者无法稳定满足段落分页、页眉页脚、表格续页和高信息密度排版合同。
- pypdf 6.15.0 用于 PDF 结构与页级核验，pdfplumber 0.11.10 用于用户补充文档的抽取；两者不能取代对源文档 locator 的保存。
- Playwright 固定为 1.61.0，作为已批准实施计划的浏览器验收基线。检索时 PyPI 已出现 1.62.0，但在代表性门户回归完成前不静默升级；升级需新锁文件和浏览器验收记录。
- Apache ECharts 6.1.0 用于交互图表，采用 Apache-2.0 许可证。Task 0.3 将保存离线文件、版本、摘要和许可证，不依赖 CDN。

### 开发验证

- pytest 9.1.1 执行合同、单元、集成、浏览器和验收测试。
- Ruff 0.16.2 与 mypy 2.3.0 分别负责静态质量和严格类型检查。
- 测试重点是用户功能、科学完整性、真实渲染和可恢复性；不扩展安全专项测试。

## 外部依据

| 组件 | 官方来源 | 许可证 | 采用理由 |
|---|---|---|---|
| ReportLab 5.0.0 | `https://docs.reportlab.com/releases/notes/whats-new-50/` | BSD-3-Clause | 原生 PDF 绘制和排版 |
| Playwright 1.61.0 | `https://pypi.org/project/playwright/1.61.0/` | Apache-2.0 | Chromium/WebKit 真实运行验收 |
| Apache ECharts 6.1.0 | `https://www.npmjs.com/package/echarts/v/6.1.0` | Apache-2.0 | 高信息密度交互图表，支持离线封装 |

其余直接依赖的精确版本、许可证、用途与来源保存在 `pyproject.toml` 的 `[tool.ci-workflow.dependencies]`，并由合同测试与 `uv.lock` 双重核对。

## 回滚与升级

1. 锁文件是环境重建的唯一解析结果；不接受宿主全局环境“碰巧已安装”。
2. 单组件升级必须先更新依赖记录，再生成新锁文件，运行其直接合同和共享回归。
3. ReportLab 如无法满足某类原生排版，先修正布局或建立可测试的 renderer abstraction；不得自动降级为 HTML 打印。
4. Playwright 升级需同时固定浏览器版本并重跑 Chromium/WebKit 真实页面验收。
5. ECharts 升级需重新封装离线资产、许可证与摘要，并重跑图表—表格同步和筛选联动验收。
