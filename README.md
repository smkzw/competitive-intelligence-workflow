# ciw · 竞品调研子系统（v2）

医学经理工作台“证据调研与方案设计”的竞品事实底座。

输入一个适应症配置，自动完成以下几步：
1. 检索 ClinicalTrials.gov，读取 CDE 登记平台等中国来源的采集；
2. 确定性抽取与语义归一；
3. 对非结构化来源做异构模型交叉核对；
4. 产出版本化 release 和三个中文门户：**A 竞品全景 / B 临床结果 / C 设计先例**。

工作台通过 `ciw_release` 适配器读取 release，并在页内打开门户。

```bash
uv sync
uv run pytest                                            # 离线测试，几十秒
uv run ciw run indications/crswnp.yaml                   # 默认工作区 ~/Developer/ciw-workspaces/crswnp
uv run ciw status --workspace ~/Developer/ciw-workspaces/crswnp
uv run ciw capture cde indications/crswnp.yaml --space <ego TaskSpace ID>   # 采集中国登记（需要 ego lite）
uv run ciw run indications/crswnp.yaml --offline        # 只用工作区里已有的原件重跑
uv run ciw run indications/crswnp.yaml --with-models    # 启用异构模型交叉核对（需要 DGX key）
```

文档：

| 文件 | 内容 |
|---|---|
| [docs/PRD.md](docs/PRD.md) | 产品合同 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 分层、数据模型、核对、工作台接入 |
| [docs/PLAN.md](docs/PLAN.md) | 里程碑与执行规则 |
| [docs/STATUS.md](docs/STATUS.md) | 当前状态 |
| [docs/DECISIONS.md](docs/DECISIONS.md) | 用户裁决 |
| [docs/REVIEW_2026-10-27.md](docs/REVIEW_2026-10-27.md) | v1 与 ciw2 的审查结论及处置 |
| [docs/handoff/](docs/handoff/) | 构建 Agent 执行包与启动提示 |

当前v2发布分支为 `codex/ciw-v2-trunk`，GitHub `main` 仍保留旧工程。执行包提及的 `archive/v1` 与 `archive/ciw2` 标签在本轮远端核查中不存在，不据此宣称历史清理完成。
