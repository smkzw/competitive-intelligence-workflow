# 构建 Agent 启动提示（复制以下整段给接手的 Agent）

```text
你接手的是“竞品调研子系统 v2（ciw）”。它是医学经理工作台“证据调研与方案设计”模块的竞品事实底座，首个适应症是 CRSwNP，本品是 MG-K10。
你在自己的机器上从零开始，不依赖任何其他机器上的目录、数据或浏览器会话。

获取代码（按执行包 §0 判断用哪个来源）：
- 竞品调研：GitHub smkzw/competitive-intelligence-workflow 的 main 分支（v2 主干）。如果 main 上仍是 v1，改用附件 ciw-v2-src.tar.gz。
- 工作台接入：GitHub smkzw/protocol-v3-workbench 的 feat/ciw-release-adapter 分支。如果没有这个分支，改用附件 workbench-ciw-adapter.patch，在提交 7c1bd916 上执行 git apply。

开工前按顺序阅读：README.md → docs/STATUS.md → docs/PLAN.md（执行规则）→ docs/handoff/EXECUTION_PACK.md。
产品合同见 docs/PRD.md，用户裁决见 docs/DECISIONS.md。已裁决的事项不要重新提问。

先按执行包 §1 搭好环境，依次完成：
1. uv run pytest，预期 87 passed；
2. uv run ciw run indications/crswnp.yaml --workspace <自选目录>/crswnp，跑出第一份 release；
3. uv run ciw audit -n 40，结果为 0 错误。
然后按执行包 T1→T5 的顺序推进。每个任务都要真实跑出 release，audit 0 错误后，再更新 STATUS、提交并推送。

硬约束：
1. 只有一条真实的端到端命令能证明“完成”；组件测试通过不算交付。
2. 测试按根因成族写，一组改动做完后再统一跑 uv run pytest，不要改一处就跑一次全量。
3. 不新建过程目录（packets/prompts/reviews/receipts/evidence），不写追加式日志；STATUS 整块替换，不超过 80 行。
4. 核对只有两种：确定性规则，以及 ciw.verify.crosscheck（三个不同模型家族）。不引入多模型会商、签发或资格认证；缓存不得按代码哈希失效。
5. 渲染层只做投影；适应症之间的差异只写在 indications/*.yaml；中文药名没核实就留空。
6. 运行产物、第三方原文、key、cookie、任何机器的绝对路径一律不入库。DGX key 由用户提供，只通过环境变量 CIW_DGX_API_KEY 或 CIW_DGX_KEY_FILE 读取。
7. 需要浏览器时只用 ego-browser（先运行 `ego-browser skill`）。为本目标建一个专用 TaskSpace 并一直复用，不启动 Playwright 或其他 Chromium。执行机上没有 ego 时，中国来源采集记为阻塞，其余任务照常推进。
8. 需要用户决定的事项写进 STATUS 的“待用户决定”，同时继续推进不受影响的任务；只有真正阻塞时才停下来问。

用户使用简体中文，面向用户的输出用中文。
```
