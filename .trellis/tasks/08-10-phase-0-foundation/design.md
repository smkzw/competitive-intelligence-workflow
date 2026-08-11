# Phase 0 技术设计

## 写入与证据边界

- 新源码根：本仓。
- 独立验收根：`/Users/smkzw/Documents/AI Products/competitive-intelligence-acceptance`。
- 旧工程与康哲模板只读。
- 批准记录保存源路径、摘要、批准语境和“不改原文”规则；复制件必须逐字节一致。

## 基线机制

1. `migration/legacy_manifest.jsonl` 是迁移候选清单，不是运行时加载表。
2. `tools/check_no_legacy_refs.py` 检查 import、subprocess、符号链接和运行时路径；文档/fixture 仅在明确历史标记时例外。
3. `pyproject.toml` 保存直接依赖的用途与许可证元数据，`uv.lock` 固定可解析版本。
4. 康哲合同采用稳定双读：前后 path、realpath、inode、size、mtime、SHA-256 完全相同才可比较；用户确认后再封装。
5. 包、CLI、页面、筛选、格式合同在 Phase 0 以测试冻结，后续实现只能满足合同，不能另建命名或降级通道。
6. Agent 只提交已锁定声明支持的类型化 `ReportViewModel`；页面注册表、康哲壳层、交互、图表、PDF 和 HTML-PPT 由应用确定性渲染，PPTX 由 PPT Master 接收结构化来源包。退出码、文件存在或模型自述均不能单独判定完成。

## S1 根因与实施约束

- 流式路线连续四次写入参数序列化失败，目录为空却退出 0：实现必须把“非空当前产物 + 摘要 + coverage + verifier”作为完成条件。
- HTML-PPT 可打开但缺 `S` 讲者窗口，`N` 与下一页冲突，逐字稿不足且存在过小文字：固定运行时由应用提供，报告节点不得自行删减。
- HTML-PPT 的可见摘要写“5/9”，而 RACI 行和另一处列表可重算为 6/9：所有可见定量结论必须绑定同一 claim/fact/row ID，并在首页、详情、图表、逐字稿和四格式之间重算一致。
- `local_map.md` 仍描述已废止的双全文同步：上游修正且整体摘要稳定前，不能复制或冻结合同。
- 详细责任边界和后续机器合同见 `docs/decisions/0004-structured-report-rendering-boundary.md`。

## 独立验收

Codex 执行确定性检查；按全局 guard/runner 另建独立检查上下文，检查者只接收产物、验收条件和锚点，不接收实现者私有推理。
