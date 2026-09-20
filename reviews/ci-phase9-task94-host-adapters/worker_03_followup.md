# Task 9.4 HA09–HA10 统一回执修订

请沿用当前会话，读取 worker_01 最新的 `hosts/receipt.py`、双份 `host-receipt.schema.json` 和合同测试。把 `application/host_smoke.py` 从自建字典合同改为唯一 `HostReceipt` 合同，并保持当前 R01–R09 对项目实时状态的深度验证。

Codex 裁决：`package.package_digest` 定义为当前安装包内 `package-manifest.json` 原始字节的 SHA-256。开发 editable install 与 Task 9.5 fresh-install 均须从安装入口对应包根定位该文件；找不到或摘要不一致则诚实失败，不用版本号代替内容摘要。

具体要求：

1. `run_host_smoke()` 返回可直接 `model_validate` 且通过根/包内 Schema 的 `HostReceipt`（若兼容 CLI 需 JSON，再显式 `model_dump(mode="json")`），不要保留第二套 receipt_kind/receipt_digest 结构。
2. 宿主不可用时使用 `provenance="unavailable"` 证据块，不能写 `None`；`status` 由合同推导。
3. 从规范事件/manifest/站点文件构造 `state`、`no_draft`、HTML artifacts 和 `semantic_receipt_digest`。`host-smoke-v1` 预期 evidence_blocked，因此必须 blocked + no_draft=true + 零 artifacts；不得生成草稿。
4. 验证器先跑 `HostReceipt.verify_content_integrity()` 与 JSON Schema，再核对当前 package manifest、fixture、入口、宿主可执行文件、外部进程、事件链和当前 manifest；旧回执、同进程、adapter-only 继续失败关闭。
5. 在 `tests/hosts/test_real_host_smoke.py` 新增精确 HA09 节点 `test_three_receipts_bind_distinct_real_host_entries_sessions_runs_package_and_events`。允许显式测试替身证明结构和批次拒绝，但断言 `real_host_pass=False`，不得冒充真实三宿主。
6. 在 `tests/integration/test_fixture_case_contracts.py` 增加精确 HA10 节点 `test_host_smoke_v1_is_registered_hashed_and_binds_current_run_receipts`，直接验证唯一 catalog、逐文件摘要、case digest 与三宿主 current receipt 绑定；若真实入口材料尚需 Task 9.5，测试必须清楚区分 source-contract 与 fresh-install acceptance。
7. 解决 fresh-install fixture 定位：最小优先给 fixture runner / host smoke 增加显式 `--catalog` 或等价可移植入口，不扩大 CLI 目录；最终 wheel/bundle 交付仍属 Task 9.5。

完成后运行 HA09/HA10、全部 `tests/hosts`、host receipt 合同、fixture/CLI 回归、Ruff、目标 mypy、包完整性。不得声称真实三宿主通过。
