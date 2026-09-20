# Task 9.4 实施步骤

- [x] HA01：基类权能边界与反例；补充属性截获类特殊方法的失败关闭反例。
- [x] HA02–HA04：Codex/Hermes/OMP 薄适配器最小输入、中断、恢复和产物映射。
- [x] HA05–HA08：三宿主语义一致、选择性能力阻断、环境恢复、手工收件箱和部分交付等价。
- [x] HA09：宿主回执 Schema、真实入口 runner 合同及伪造/旧回执反例；runner 与 verifier 均把案例 `rendered` 明确映射为运行清单 `completed`。
- [x] HA10：`host-smoke-v1` fixture、逐文件摘要、case digest 与 catalog 登记。
- [x] CLI：`capability preflight --host codex|hermes|omp` 与首版 HTML 选择保持语义一致。
- [x] 运行聚焦测试、共享集成回归、Ruff、mypy 和包完整性。
- [x] 对当前可用的真实宿主入口做连通性测试；不随意 fallback，不把 adapter JSON 当真实 smoke。
- [x] 独立会商审查越权边界、三宿主语义、恢复、回执真实性与中文医学经理体验；双 review-gate 与 `audit-execution --require-conference` 通过。

## Task 9.5 安装边界裁决

- 完整候选包为 `.tar.zst` Skill bundle；Python wheel 只承载 CLI 模块。
- 完整包必须包含根 `package-manifest.json`、唯一 fixture catalog、`host-smoke-v1` 输入、包内 Schema 与安装入口，并在隔离目录 fresh-install 后生成三份 `path_resolved` 回执。
- Task 9.4 的源码 checkout 真实调用只证明合同和当前入口可运行，不替代 Task 9.5 的最终包验收。

## 回滚点

若任一适配器改变科学数据库/项目合同摘要、在证据不足时生成草稿、用宿主私有状态替代规范事件/检查点、或用同一进程/静态 JSON 冒充三宿主真实回执，立即停在本任务并撤回该适配器候选。
