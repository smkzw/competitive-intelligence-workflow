# 竞品调研工作流无损暂停锚点

暂停时间：2026-08-11 17:43（Asia/Shanghai）
项目根：`/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`
已接受基线：`1aa6309`（Task 1.2）
当前 Trellis 任务：`.trellis/tasks/08-11-phase-1-project-truth-base`

## 目标与不可变边界

- 按已批准 v1.2 设计书和实施计划顺序构建，新架构保持在独立目录，旧工程只读。
- 中文原生、临床试验医学用户导向；不做安全测试扩展。
- 关键证据不达门槛时不得生成草稿；项目数据必须可移动、追加式、可追溯。

## 已完成且已接受

- Phase 0 全部完成。
- Task 1.1：稳定 ID、九组状态、项目合同、IANA 时区和固定 cutoff，commit `fffefee`。
- Task 1.2：自包含可移动项目、唯一产物相对路径、`project create/verify`，commit `1aa6309`。

## Task 1.3 已完成但尚未接受的工作

- 新增 `migrations/0001_*.sql`–`0006_*.sql`，覆盖项目/实体、来源/事实/声明、门槛/快照/覆盖、格式/产物/下载、修订/幂等、追加式保护。
- 新增 `src/ci_workflow/storage/sqlite.py` 与 `migrations.py`：连续迁移、摘要防漂移、幂等重放、`foreign_keys=ON`。
- `project create` 现在执行迁移并将同一份不可变项目合同写入 SQLite；`project verify` 核对 YAML/DB 一致性。
- 数据库 CHECK 拒绝状态族串写、绝对产物路径和绝对下载路径；科学版本和迁移记录禁止原地更改/删除。
- 新增 `tests/integration/test_sqlite_migrations.py` 和 `test_append_only_records.py`。

## 已获得的确定性证据

- RED：两个测试文件因 `ci_workflow.storage.migrations` 不存在出现 2 个 collection errors。
- Task 1.3 精确测试：`6 passed`。
- 全库回归：`108 passed`。
- Ruff：通过。
- strict mypy：13 个源文件无问题。
- 包校验：`PACKAGE_OK`。
- `git diff --check`：通过。

## 暂停时正在运行的只读审查

- runner PID：`83455`；OMP 子进程 PID：`84016`。
- Codex unified exec session：`90504`。
- 声明路由：`Pi/cms-smk/cms-model:high`；设置 7200 秒硬等待，暂停时未 fallback、未终止。
- 输出路径：`runs/pi_ci_phase1_task13_sqlite_truth_store.md`、`runs/pi_ci_phase1_task13_sqlite_truth_store_stdout.txt`。
- 不要因 UI 会话柄失效而重派。恢复时先检查上述进程和两个输出文件；只有明确终端失败或输出缺失才按声明链处理。

## 恢复时唯一安全顺序

1. 打开本文件、`context/ci_phase1_task13_sqlite_truth_store_context.md` 和 Trellis 当前任务，确认 `git status` 与本锚点一致。
2. 检查 PID `83455`/`84016` 或上述 runner 输出。若已完成，直接评审原会话产物；不得重派。
3. 若返回 VETO，只修复精确 P0/P1，在同一会话可恢复时使用同会话复验；若 PASS，Codex 仍需复跑 6/108/Ruff/mypy/package/Trellis 并完成 review gate。
4. 写入 Task 1.3 验收锚点、会商指标和 Trellis 记录，再做可恢复日志清理。
5. 用计划精确提交信息 `feat: add canonical sqlite scientific truth store` 完成 Task 1.3，然后才进入 Task 1.4。

## 尚未完成

- 独立审查结论的 Codex 裁决。
- review gate、Task 1.3 验收目录、Trellis 完成勾选、可恢复清理、正式 Task 1.3 commit。
- Task 1.4 及之后尚未开始。
