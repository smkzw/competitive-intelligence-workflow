# 实施计划 — R2 核心能力矩阵持久化与选择性执行门

## 顺序

- [x] I1 先补负向测试：每次重检、矩阵持久化、软链接拒绝、研究阻断、交付阻断、
  药智可选降级。
- [x] I2 在 capability 应用层实现唯一原子回执写入/读取边界。
- [x] I3 为 `RunContext` 增加显式 probe/host 注入，并令 preflight 不可复用。
- [x] I4 在报告研究与 HTML 交付边界应用 readiness，增加明确可恢复运行结局与中文状态。
- [x] I5 更新 CLI、运行合同及相邻宿主/fixture 测试，确保生产默认仍用真实探针。
- [x] I6 运行聚焦测试、integration、全仓 gate、隔离 bundle 与 fresh-install。
- [x] I7 由独立执行 worker/manager 审查合同、状态机和测试空洞；Codex 复核并写 checkpoint。

## 验证

```text
pytest tests/integration/test_capability_preflight.py tests/integration/test_selective_capability_blocking.py tests/integration/test_project_run_cli.py -q
pytest tests/integration -q
tools/gate.sh
```

打包验证沿用当前 package builder、required-v12 final-content 和 fresh-install 命令，
以本次实际 runner 生成的命令及现有 checkpoint 为准。

## 回滚点

本任务不改科学证据字节或历史事件。若实现失败，保留新增任务文档、RED 测试和
runner 回执；不 reset/checkout/clean，不删除用户脏树。
