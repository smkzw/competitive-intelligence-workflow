# ciw · 竞品调研子系统（v2）

当前已按用户要求无损暂停。恢复先读 [STATUS](docs/STATUS.md) 与 [本次交接和复盘](docs/handoff/PAUSE_20261029.md)，经用户恢复授权后续接，不重跑下面的首次安装示例。

医学经理工作台“证据调研与方案设计”的竞品事实底座。

输入一个适应症配置，自动完成以下几步：
1. 检索 ClinicalTrials.gov，读取 CDE 登记平台等中国来源的采集；
2. 确定性抽取与语义归一；
3. 对非结构化来源做异构模型交叉核对；
4. 产出版本化 release 和三个中文门户：**A 竞品全景 / B 临床结果 / C 设计先例**。

工作台通过 `ciw_release` 适配器读取 release，并在页内打开门户。

环境：Python 3.12/3.13、uv；显示工具契约测试使用工作台现有的 Node.js，无需另启浏览器。

```bash
uv sync
uv run pytest                                            # 离线测试，几十秒
uv run ciw run indications/crswnp.yaml                   # 默认工作区 ~/Developer/ciw-workspaces/crswnp
uv run ciw status --workspace ~/Developer/ciw-workspaces/crswnp
uv run ciw capture cde indications/crswnp.yaml --space <ego TaskSpace ID>   # 采集中国登记（需要 ego lite）
uv run ciw capture nmpa indications/crswnp.yaml --space <ego TaskSpace ID>  # 公开药品许可列表与详情
uv run ciw capture nmpa indications/crswnp.yaml --space <ego TaskSpace ID> --resume-only  # 只补缺失详情
uv run ciw capture docs indications/crswnp.yaml --space <ego TaskSpace ID> --url <公开文章HTTPS地址> --kind company
uv run ciw run indications/crswnp.yaml --offline        # 只用工作区里已有的原件重跑
uv run ciw run indications/crswnp.yaml --with-models    # 启用异构模型交叉核对（需要 DGX key）
uv run ciw run indications/crswnp.yaml --offline --with-models --report B  # 登记原件离线复用；模型在线核对B，保留已有门户
```

采集与运行时使用同一个 `--workspace`。公众号原文使用 `--kind wechat`，发布者必须匹配适应症配置中的账号。
DGX 凭据仅通过 `CIW_DGX_API_KEY` 或 `CIW_DGX_KEY_FILE` 显式提供；cms-smk凭据只读 `CMS_SMK_API_KEY`。
现行D22恢复配置（沿用D17两角色）：DGX `deepseek`主抽取，cms-smk `glm-5.3-flash`读取完整原文和候选核对、纠错、补漏。
通过本地JSON/schema/引文/数值/日期校验后标记 `verified`；不再调用Qwen或第三模型仲裁，不宣称盲审。
各模型响应的 model/id、结束原因和用量随原有工作区核对记录保留；缓存复用不会伪造新调用。

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

## 从新适应症开始

工作台“证据调研与方案设计”提供自助入口：输入适应症、选择A/B/C并可补充研究问题，检索和生成在后台继续，返回页面可恢复进度和已完成报告。高级YAML/CLI入口同时保留。服务需显式配置并提供宿主身份；隔离开发身份默认关闭，详见工作台接入说明。

同一自然语言流程也可运行 `uv run ciw research "适应症全称" --question "研究问题" --workspace <新工作区>`。需要既有DeepSeek与cms-smk GLM凭据。登记新发现药物保留未知创新属性；中文名等不凭模型记忆填写。中国来源仍需真实采集，未采集不等于零项。

新建 `indications/<slug>.yaml`，提供名称、英文检索词与人群匹配规则、从来源核实的产品/别名，以及要比较的终点概念；结构可参照已有配置。未核实中文药名留空；未归类干预保留单列，不能把少量配置产品称为完整竞品宇宙。

运行 `uv run ciw run indications/<slug>.yaml --workspace <新工作区> --with-models` 联网生成；原件、来源覆盖与未决项保留在工作区。只在已有真实原件时用 `--offline`，不能用于从零研究。

独立查看本次产物时，可在新工作区的 `releases/<release_id>/site` 运行 `python3 -m http.server <空闲端口> --bind 127.0.0.1`，浏览器打开 `http://127.0.0.1:<端口>/A/`（或B/C）。这是CLI产物查看，不等于新适应症已接入正式工作台；后者需要相应项目和已配置的数据源。

### 按需生成报告

网页优先深入生成所选A/B/C，其他类型通过“生成”按钮复用本次资料补充。高级CLI亦可：

```sh
uv run ciw research "适应症全称" --report C --workspace <workspace>
uv run ciw research "适应症全称" --report B --reuse-research --workspace <workspace>
```

B/C不等待A的产品属性核对。高级YAML `ciw run`仍可一次生成整套A/B/C。运行时间及科学质量以真实独立测试为准。
