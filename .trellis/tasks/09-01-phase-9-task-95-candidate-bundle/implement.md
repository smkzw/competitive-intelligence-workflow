# Task 9.5 实施步骤

- [x] PK01：构建 allowlist、staging、逐文件 manifest、`.tar.zst` 与外部 SHA-256。
- [x] PK02：bundle 校验器及缺失/额外/摘要漂移/路径异常反例。
- [x] PK03：隔离 fresh-install、共享规范根和 OMP 单一明确链接，不覆盖旧入口。
- [x] PK04：三宿主真实外部进程 runner 与三份 `path_resolved` 回执。
- [x] PK05：fresh-install/conformance/real-host 测试和 `BUNDLE_OK`。
- [x] PK06：中文安装说明、阻断说明与验收证据归档。
- [x] 独立执行、会商、三宿主真实验收和治理审计通过后收口。

## 回滚点

若 bundle 混入缓存/旧输出/凭据、覆盖旧入口、三宿主解析到不同包摘要、同进程伪造回执、关键证据不足仍生成草稿，立即撤销候选安装并停在本任务。
