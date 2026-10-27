# PLAN v2

只写目标、顺序和验收标准。当前进度只在 [STATUS.md](STATUS.md) 里维护；历史看 git log。

## 执行规则（来自 v1 / ciw2 的教训，必须遵守）

1. **一条真实端到端命令优先。** 每个里程碑都以 `ciw run indications/<slug>.yaml` 跑出真实 release 为准。组件测试通过不能代替。
2. **测试按根因成族写，最后统一跑。** 不搞“改一处、全仓测一次”。`uv run pytest` 必须在 60 秒内跑完，并在干净 clone 上全绿。
3. **不设额外的门。** 不派多模型会商，不做“资格认证”或回执签发链，不保留 24 门户矩阵。真正的核对只有两种：确定性规则，以及异构模型交叉核对（PRD §3）。
4. **缓存只按原件内容键入**，即原件 sha256 + 抽取 schema + 指令，不按代码哈希。改分析或渲染代码不能让已核对的抽取失效。
5. **STATUS 只保留当前块，整块替换。** 不新建 packets/、prompts/、reviews/、receipts/ 这类过程目录。
6. **运行产物不入库。** 包括 workspace、captures、sqlite、截图、第三方原文，`.gitignore` 已经排除。
7. **函数不超过 80 行，文件不超过 600 行**，超出就拆。渲染层、流水线里不得写适应症或药物专用逻辑，这些只放在 `indications/*.yaml`。

## 里程碑

| ID | 目标 | 验收（全部满足才算完成） |
|---|---|---|
| M0 | 仓库清理 + v2 主干 + 文档 | 两个分支完成 filter-repo；`archive/v1`、`archive/ciw2` 两个标签已建；`uv run pytest` 全绿；ARCHITECTURE、PRD、PLAN、STATUS 齐全 |
| M1 | CT.gov 全链 + A/B/C 门户 | CRSwNP 一条命令出 release 和三个门户；抽 30 个 B 数值核对原件，0 错误；门户在 1440 和 1920 宽下实看可用 |
| M2 | 工作台接入 | 工作台 `ciw_release` 适配器和托管路由合入；工作台相关测试全绿；在工作台里打开 A/B/C（需要宿主身份，见 STATUS 阻塞项） |
| M3 | 中国来源 | CDE 登记列表和详情：采集 → 解析 → 进入 A/C；补齐 MG-K10 登记；NMPA 批准（药品查询）解析为 approval 事件；药企公告、公众号文章（丁香园 Insight、医药魔方 Info）走采集收件箱 |
| M4 | 异构模型交叉核对（真实端点） | DGX 上 deepseek / qwen / glm 三家族跑通公告、公众号的 `EventItem` 和产品属性 `ProductAttrItem`；抽 20 条 dual_agreed 结果核对原文，0 错误；待核比例低于 15% |
| M5 | 论文结果补齐 | CT.gov 没有结果的关键 III 期，从 Europe PMC 开放全文或摘要补主要终点（`PublicationResultItem`，交叉核对）；B 的组间比较中标注“论文” |
| M6 | 泛化 + studio 候选池 | 只新增 `indications/pnh.yaml`，不改 Python，就能产出 PNH 的 A/B/C；工作台设计 studio 读取 release `c.rows` 作为竞品候选 |

## 不做（v1 范围之外，见 DECISIONS.md D3/D5/E6）

PPT/Excel/PDF 导出、离线分享、门户内编辑事实、个人配置、定时监测、历史截止日回放、移动端、多宿主安装包、24 门户矩阵、药智、排名/评分/Meta/NMA。
