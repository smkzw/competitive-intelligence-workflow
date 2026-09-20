Delegated mode. MODE=TEST. 你是只读连通性测试者，不是用户侧主代理。

Hard boundaries:
- 不得修改任何文件；不得联网检索；不得启动其他代理；不得宣称产品通过。
- Runner-managed output path: `runs/tests/r13e-connectivity/zcode.md`。不得用工具写入该路径，由 runner 持久化最终回答。

Read these files only:
- `context/ci-phase10-task102-r13e-visual-review_conference_context.md`

Create/write only this output file:
- `runs/tests/r13e-connectivity/zcode.md`（runner 管理；只返回正文，不用工具写入）

预期身份：`zcode/zcode/glm-5.3-flash:max`。

任务：
1. 明确报告实际代理、provider、model 与 effort；若无法确认，写“无法确认”。
2. 使用 `ego-browser nodejs`，创建或复用名为 `ci-r13e-connectivity-zcode` 的任务空间，打开 `http://127.0.0.1:8770/b-real/reports/B/v1/html/overview.html`，读取页面标题和 URL。
3. 在单独的最终 ego heredoc 中执行 `completeTaskSpace(taskId, {keep:false})`。
4. 返回：身份、ego(lite) 是否可调用、页面标题、页面 URL、是否完成清理、任何明确错误。
