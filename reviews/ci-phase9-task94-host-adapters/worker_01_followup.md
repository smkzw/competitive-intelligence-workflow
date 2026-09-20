# Task 9.4 HA01 合同对接修订

请沿用当前会话，只修改你拥有的宿主合同、双份 Schema、包登记和合同测试；不要改 `application/host_smoke.py`。

当前 `hosts/receipt.py` / `host-receipt.schema.json` 与 HA09 的真实入口证据不完整对接，而且 `HostRunEvidence.artifacts` 强制至少 1 个，无法表示 `host-smoke-v1` 在关键证据阻断时“无草稿、零产物”的合法回执。请读取当前 `application/host_smoke.py` 和其测试，形成一个唯一可用的 `HostReceipt` 合同：

1. blocked 终态必须允许且要求零 artifacts；complete / partially_delivered 才要求至少 1 个 HTML artifact。
2. 合同必须足以验证：当前包摘要、fixture/case/逐文件摘要、真实安装入口、宿主可执行文件和版本及 `path_resolved|explicit|unavailable` 来源、launcher PID 与外部 PID、完整 argv、开始/结束时间、真实退出码、session/project/run、事件数量与摘要、no-draft 断言、最终 manifest 路径/摘要/manifest_digest。
3. 保持内容寻址和 `model_copy` 防篡改；Python 与根/包内 Schema 字节一致；用户可见文本中文原生。
4. `catalog_summary` 若不再有独立必要性可以删除；YAGNI 优先，但不得牺牲 HA09/HA10 证据。一个真实回执布局优于两个互不对接的布局。
5. 增加反例：blocked 携带 artifact、complete 无 artifact、同进程、无退出码、无 no-draft、来源为 unavailable 却声称通过、摘要漂移。

完成后运行你的聚焦测试、worker_02 适配器测试、worker_03 host smoke 测试（后者预计在 runner 尚未适配前可能失败；请精确报告接口差异），Ruff 和目标 mypy。不要声称真实三宿主通过。
