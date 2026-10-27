# 构建 Agent 执行包（v2 · 2026-10-27）

**先读 [STATUS](../STATUS.md) 和 [最近暂停交接](PAUSE_2026-10-27.md)，核对实际HEAD及用户最新恢复授权。下面是任务合同，不要求把已完成的环境、采集和模型调用从头重跑；发布分支以D15为准。**

本执行包面向**在另一台机器上从零开始**的构建 Agent。所需的一切都来自 Git 仓库或随包附件，不依赖任何其他机器上的目录、数据、浏览器会话或代理。

接手前先读仓库里的文档：`README.md` → `docs/STATUS.md` → `docs/PLAN.md`（含执行规则）→ `docs/ARCHITECTURE.md`。产品合同是 `docs/PRD.md`，用户裁决在 `docs/DECISIONS.md`。本文件只讲**怎么干**。

## 0. 获取代码

| 内容 | 来源（任选其一） |
|---|---|
| 竞品调研子系统 v2（包 `ciw`） | ① GitHub `smkzw/competitive-intelligence-workflow` 的分支 `main`，从提交说明为 “feat: v2 trunk (ciw)” 的那次提交起；② 附件 `ciw-v2-src.tar.gz`（解压后 `git init` 并自行提交） |
| 历史版本（只作移植来源，不在上面开发） | 同一仓库的标签 `archive/v1`（旧 ci_workflow）和 `archive/ciw2`（rebaseline-v2）。附件里不含这两个版本 |
| 医学经理工作台接入改动 | ① GitHub `smkzw/protocol-v3-workbench` 的分支 `feat/ciw-release-adapter`；② 附件 `workbench-ciw-adapter.patch`（在工作台提交 `7c1bd916` 上执行 `git apply`） |

**怎么判断用哪个来源：**
- 如果 GitHub 上 `competitive-intelligence-workflow` 的 `main` 仍是 v1（顶层有 `src/ci_workflow/`、`packets/`、`runs/`），说明 v2 还没推送。这时用附件，并在 STATUS 的“待用户决定”里记下“v2 尚未推送”。
- 工作台同理：GitHub 上没有 `feat/ciw-release-adapter` 分支，就用补丁。

## 1. 环境准备（在执行 Agent 所在机器上）

```bash
# 竞品调研子系统（Python ≥ 3.12，uv）
cd competitive-intelligence-workflow
uv sync
uv run pytest -o addopts="" -q          # 预期：87 passed
uv run ruff check src tests             # 预期：All checks passed
uv run ciw run indications/crswnp.yaml --workspace <你的工作区目录>/crswnp   # 会联网访问 ClinicalTrials.gov
uv run ciw audit --workspace <你的工作区目录>/crswnp -n 40                  # 预期：errors 为空
```

- **工作区目录**：存放 CAS 原件、采集结果、release 和门户，由你自己选，不入库。
  - 工作台通过环境变量 `CIW_WORKSPACE_CRSWNP` 找到它；
  - 不设时默认用 `~/Developer/ciw-workspaces/crswnp`。
- **代理**：访问 ClinicalTrials.gov 需要代理时，设置 `CIW_PROXY=http://host:port`。
- **第一次运行只有 CT.gov 数据**：CDE 一栏会显示“未采集”，这是正常的，CDE 数据在 T2 里由你自己采集。
- **工作台测试**：需要 Python ≥ 3.10，依赖见 `requirements-workbench.txt`。依赖旧 CSV 竞品库的用例，如果找不到数据会自动跳过。

  ```bash
  PYTHONPATH=services/api python -m unittest tests.test_ciw_release_adapter tests.test_evidence_package_adapters \
    tests.test_evidence_design_manifest tests.test_canonical_project_context tests.test_evidence_picos_workflow \
    tests.test_evidence_review_workflow tests.test_frontend_evidence_design_contract
  ```

## 2. 规则（违反任何一条都视为退回 v1 的老路）

1. **每个任务都要真跑一遍。** 完成后运行 `uv run ciw run indications/crswnp.yaml`（或加 `--offline`），再运行 `uv run ciw audit -n 40`，0 错误才算完成。
2. **测试按根因成族跑。** 同一根因的改动全部做完，再统一跑一次 `uv run pytest`（应在 60 秒内跑完）；不要改一行就跑一次全量。
3. **不留过程痕迹。** 不新建 packets/、prompts/、reviews/、receipts/、evidence/ 这类过程目录，不写追加式日志。`docs/STATUS.md` 每次整块替换，不超过 80 行。
4. **核对只有两种。** 一是确定性规则，二是 `ciw.verify.crosscheck`。不引入多模型会商、签发、资格认证或恢复账本。
5. **缓存按原件内容键入。** 键由原件 sha256、schema、指令组成；禁止按代码哈希让缓存失效。
6. **渲染层只做投影。** `src/ciw/render` 里不翻译、不推断组别、不做数值计算，`tests/test_layering.py` 会守住这一点。
7. **适应症差异只写在 `indications/*.yaml`。** 中文药名只填已核实的（来源为 CDE、NMPA 或企业官方）；没核实就留空，门户会显示 INN。
8. **不提交敏感或本地内容。** 运行产物、第三方原文、key、cookie、任何机器的绝对路径都不入库。
9. **需要用户决定的事不停工。** 写进 STATUS 的“待用户决定”，同时继续推进不受影响的部分。

## 3. 任务（按顺序）

### T1 · 工作台界面实机验证（M2 收尾）

**现状**
- 已实现：
  - 适配器 `services/api/app/ciw_release_adapter.py`；
  - 托管路由 `/api/projects/{id}/evidence-design/packages/{pkg}/reports/{A|B|C}/...`；
  - 前端“竞品调研报告”标签。
- 已验证：相关测试通过；门户能通过托管路由打开。
- 未验证：在工作台界面里点开门户。原因是工作台对真实项目（`proj_mgk10_crswnp`）要求宿主注入身份；本地启动时 `/api/projects/{id}/source-manifest` 返回 503 `monitoring_principal_unavailable`，前端因此显示“功能未配置”。

**做法**
- 不要绕过身份校验。按工作台自己的文档（`docs/`、`deploy/`、最新 HANDOFF）里的方式启动。
- 如果确实没有本地开发用的身份注入，在 STATUS 里列为“待用户决定”，给出两个选项：
  1. 工作台增加开发身份注入；
  2. 在 demo 项目上挂 ciw 包。

**验收**：在工作台里分别以 1440 和 1920 宽度点开 A/B/C，截图存入 `docs/screenshots/`（PNG 要小）。

### T2 · 中国来源（M3）

**1. CDE 登记（药物临床试验登记与信息公示平台）**

*采集*
- 命令：`uv run ciw capture cde indications/crswnp.yaml --workspace … --space <TaskSpace ID>`。
- 执行机上要装有 ego lite / ego-browser。先运行 `ego-browser skill` 阅读 API。
- 为这个目标建**一个**专用 TaskSpace，之后一直复用；不要接管用户自己的标签页。
- 采集期间不要在同一空间里并行操作别的页面。弹出的详情页会互相干扰，导致详情采集失败。
- 有详情失败时，重跑同一命令即可，已完成的会自动跳过。

*参考规模*（2026-10-27 在另一台机器上采集，数量变化属正常，以平台实时为准）
- 检索词“鼻息肉”59 条，“慢性鼻窦炎伴鼻息肉”33 条，“MG-K10”16 条；
- 与本适应症相关的详情约 59 份。

*本品 MG-K10*
- 当时 CDE 上没有它的 CRSwNP 登记，只有特应性皮炎、慢性自发性荨麻疹、结节性痒疹、哮喘、季节性过敏性鼻炎，这些已作为“本品其他适应症”展示。
- 如果仍然没有，等用户提供 CTR 号，不要猜。

*去重（审查遗留 V11）*
- 同一试验同时登记在 CT.gov 和 CDE 时，目前会被计两次。
- 处理办法：用 CT.gov 的 `secondaryIdInfos`（含 CTR 号）或 CDE 详情里的境外登记号做 NCT↔CTR 匹配，合并成一条，保留两个登记号。

**2. NMPA 批准**
- 移植 `archive/ciw2:rebaseline-v2/src/ciw2/sources/nmpa_detail.{py,mjs}`，新增命令 `ciw capture nmpa`。
- 解析结果写成 `Event(event_type="approval", status="registry")`。
- 首批核对：度普利尤单抗、奥马珠单抗、美泊利珠单抗、司普奇拜单抗。

**3. 药企公告和公众号**
- 用 ego 采集到工作区的 `captures/docs/`，每篇配一个 `.meta.json`，字段为 url、kind（company|wechat）、title、publisher、published_at、fetched_at。
- 公众号通过搜狗微信检索，只取丁香园 Insight 和医药魔方 Info。
- **验收**：收件箱里至少 10 篇；`ciw status` 的 coverage 中，company 和 wechat 显示 ok 或 partial。

**4. 已踩过的坑**
- `ego-browser nodejs -e` 的 console 输出在 **stderr**，不在 stdout。
- 子进程必须传 `stdin=DEVNULL`，否则在后台会挂住（`cde_registry.py` 已处理）。
- CDE 和 NMPA 首次打开会先过一道 JS 校验，需要等约 6 秒。

### T3 · 异构模型交叉核对接真实端点（M4）

**前提**
- 执行机能访问 DGX，即 `src/ciw/data/llm.yaml` 里配置的 OpenAI 兼容端点。
- key 由用户提供，通过环境变量 `CIW_DGX_API_KEY`，或 `CIW_DGX_KEY_FILE` 指向的文件传入。任何 key 都不写进仓库。

**运行**：`uv run ciw run indications/crswnp.yaml --offline --with-models`。

**验收**
- 抽 20 条 `dual_agreed` 或 `arbitrated` 事件，人工对照原文，0 错误。
- `needs_review` 占比低于 15%。超标时先改抽取指令或 schema，不要放宽比对规则。

**产品属性**
- 新增 `ProductAttrItem` 任务（schema 已有，尚未接入）。输入是 CT.gov 的干预描述和 CDE 的药物名称。
- 只补配置里为空的 target 和 modality，不覆盖已有值；`attribute_status` 记录核对状态。

**路由**
- deepseek 和 glm 在 DGX 的同一车道上互斥，qwen 走单独车道。
- 并发上限：deepseek 4，glm 1，qwen 2。

### T4 · 论文结果补齐（M5）
- **对象**：CT.gov 上没有结果、但已经发表的关键 II/III 期试验。中国企业的 III 期大多属于这一类。
- **检索**：用 Europe PMC REST，查询式为 `query=EXT_ID:NCTxxxx OR "CTRxxxx"`，取开放全文或摘要。
- **抽取**：用 `PublicationResultItem`（schema 已有）做交叉核对。结果进入 B 时标 `kind="publication"`，并显示核对标签。
- **冲突**：论文和登记的数值不一致时两条都保留，不合并。

### T4.5 · 审查遗留小项（V11）
- 比例单位：`unit` 是 0–1 小数形式时（判定条件：数值全部 ≤1，且单位里没有 percent 或 %），计算出的差值不能标成“百分点”。
- `common.js` 的 `src()`：只允许 http 和 https 链接。
- C 页搜索高亮：先在原文上匹配，再分段转义；不要对已经转义过的 HTML 做正则替换。

### T5 · 泛化与 studio 候选池（M6）
- **泛化**：新增 `indications/pnh.yaml`，不改 Python 代码，就能跑出 PNH 的 A/B/C。配置包括：
  - 概念字典：Hb、LDH、输血避免、FACIT-Fatigue、突破性溶血；
  - 产品别名：依库珠、雷夫利珠、pegcetacoplan、iptacopan、danicopan、crovalimab、本品 MY008211A 等；
  - 背景药。
- **studio 候选池**：工作台的设计 studio（`mw_core/design/competitors.py`、`rank.py`）增加一个数据源，读取 release 里的 `c.rows`。开工前先和工作台负责人确认。

## 4. 每个任务结束时
1. 运行 `uv run pytest` 和 `uv run ruff check src tests`。
2. 真跑一次 release，再运行 `ciw audit -n 40`。
3. 整块替换 `docs/STATUS.md`。
4. 提交到 `main` 并推送，只包含源码、测试、文档和小夹具。工作台的改动提交到 `feat/ciw-release-adapter`。
