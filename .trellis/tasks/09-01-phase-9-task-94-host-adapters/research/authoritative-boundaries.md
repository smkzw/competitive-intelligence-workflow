# Task 9.4 权威边界

- 设计 v1.2 §6.2–6.3、§18.1–18.2、§19.1 是产品语义权威。
- 重构实施计划 Task 9.4 HA01–HA10 是测试和文件边界权威。
- ADR 0013 把首版真实交付收窄为站点式 HTML；其他格式只保留选择性阻断合同。
- 当前 `capability_preflight.py`、公共 CLI、事件流和项目检查点是复用对象，不在宿主层复制业务逻辑。
- Task 9.5 才冻结并安装候选包；Task 9.4 的任何源码运行不得冒充最终 fresh-install 验收。

## 安装资源布局

uv 官方构建后端说明：wheel 默认包含模块目录；额外数据要么放在模块目录内，要么配置 wheel data。现有项目从 Phase 0 起已裁决 wheel 只承载 CLI，完整工作流由 `.tar.zst` Skill bundle 交付。因此 Task 9.5 不扩大 wheel 职责，而在完整包清单中强制纳入根清单、唯一 fixture catalog 与 `host-smoke-v1`，并用独立解包安装验证其可定位性。

- 官方依据：https://docs.astral.sh/uv/configuration/build-backend/#file-inclusion-and-exclusion
- 项目依据：`.trellis/tasks/08-10-phase-0-foundation/implement.md`
