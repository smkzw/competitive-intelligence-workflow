# Task 10.5 设计

## 切换清单

`inventory` 接收一个显式 registry JSON 和授权根列表，只用 `lstat` 观察注册项，不递归发现额外系统路径，也不跟随符号链接。输出规范 JSON，摘要由规范字节计算。目录内容摘要仅覆盖 fixture 中显式注册或目录自身的稳定元数据，不读取敏感内容。

## 状态与门

- `inventory`：生成观察清单与摘要。
- `validate`：以清单、授权清单摘要和 recovery receipt 为输入，重新 `lstat` 并验证 path/realpath/dev/inode/type/digest 未漂移。
- `apply`：仅处理 `delete` 或 `retain` 等已登记动作；要求授权摘要精确匹配已验证清单；拒绝 symlink-follow 和根逃逸；重复执行返回相同终态。
- `absence-check`：任何已登记旧运行时、引用、影子、缓存或备份仍存在都不能称为“无残留”；即使 registry 暂时写为 `retain` 也仍失败。最终 absence 门必须使用全处置终态 registry。

所有写操作以 caller 提供的批准 fixture 根为硬边界。真实工程路径不会写入测试参数或默认值。

逐项 apply 有意不伪装成事务：某项失败时已完成项保持删除，错误统一收口为 `CutoverError`，修复阻塞项后以同一 inventory/授权幂等重放，已完成项报告 `already_absent`。registry 禁止“删除父目录、保留其子项”的结构性矛盾。叶符号链接可以指向批准根外，但只记录目标文本并 unlink 链接本身，绝不跟随或处置链接目标。

## Release receipt

每条回执用严格 schema 固定身份和证据摘要。聚合器读取 release-case catalog 与 receipt 集合，按 case id 和 owner task 精确闭合：required/applicable 只能由 `accepted` 闭合；`pending_future_owner` 保持未闭合；`not_applicable` 只允许 catalog 的 optional adapter 且项目合同显式关闭。

## 失败关闭

未知字段、重复 case、摘要格式错误、owner 不匹配、缺回执、路径逃逸、符号链接、inode/device/摘要漂移、recovery 未通过、授权摘要不匹配或残留引用都必须失败。
