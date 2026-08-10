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

## 独立验收

Codex 执行确定性检查；按全局 guard/runner 另建独立检查上下文，检查者只接收产物、验收条件和锚点，不接收实现者私有推理。
