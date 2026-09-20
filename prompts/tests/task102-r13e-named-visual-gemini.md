Delegated mode. MODE=TEST. 你是独立只读测试者，不是用户侧主代理。

预期身份：`pi/google-antigravity/gemini-3.7-flash:high`。

Hard boundaries:
- 只读；遵守共享审评合同；不得修改文件、联网研究、安全测试或启动其他代理。
- Runner-managed output path: `runs/tests/r13e-named-visual/gemini.md`。不得用工具写入，由 runner 持久化最终回答。

Read these files only:
- `prompts/tests/task102-r13e-named-visual-shared.md`
- `context/ci-phase10-task102-r13e-visual-review_conference_context.md`
- `.trellis/tasks/09-01-phase-10-task-102-r13-product-rebuild/prd.md`
- `.trellis/tasks/09-01-phase-10-task-102-r13-product-rebuild/design.md`
- `runs/tests/r13-ego/r13d-a-drawer-ego.png`
- `runs/tests/r13-ego/r13d-b-baseline-ego.png`
- `runs/tests/r13-ego/r13e-b-efficacy-cross-trial-ego.png`
- `runs/tests/r13-ego/r13d-c-overview-ego.png`
- `runs/tests/r13-ego/r13d-c-drawer-ego.png`

Create/write only this output file:
- `runs/tests/r13e-named-visual/gemini.md`（runner 管理；只返回正文，不用工具写入）

独立完成共享合同中的全部真实操作，不读取其他测试者输出。
