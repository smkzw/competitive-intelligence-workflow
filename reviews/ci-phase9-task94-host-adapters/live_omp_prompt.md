你正在执行 Task 9.4 OMP 真实宿主源码级冒烟，不是审查或模拟。只允许在当前仓库读取文件，并写入 `tmp/task94-live/omp-project/`；不得修改源码、合同、测试或其他目录。

1. 完整读取 `skills/competitive-intelligence-workflow/SKILL.md` 并按其入口规则执行。
2. 运行 `uv run ci-workflow package verify --root .`，必须看到 PACKAGE_OK。
3. 运行 `uv run ci-workflow fixture run --case host-smoke-v1 --reports A --outputs html --project tmp/task94-live/omp-project --catalog fixtures/catalog.yaml`。关键证据不足的预期退出码为 4；退出码 4 不是技术失败。
4. 读取 `tmp/task94-live/omp-project/manifests/current_run.json`、事件流和 reports 目录，确认 outcome=evidence_blocked、存在规范 run_id、且没有任何报告草稿文件。
5. 最终只输出一行：`HOST_SMOKE_RESULT host=omp package=ok outcome=evidence_blocked no_draft=true run_id=<真实值>`。任一步异常则输出 `HOST_SMOKE_FAILED host=omp reason=<简洁中文原因>`，不得伪造成功。
