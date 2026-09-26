# 2026-09-27 无损暂停交接｜0924V1 R24-62 后

这份文档是下一位 Agent 的**接手入口**，不是 RC 或医学批准。请先核对 Git HEAD、工作树和本页所引的文件；下文有些数字来自不同日期/不同候选，不能相加或互相替代。当前用户要求是完成手头工作、留下记录并推送 GitHub，随后暂停；因此本次没有再发起新一轮长程会商或继续扩研究范围。

## 1. 三分钟接手要点

1. 唯一授权工程是 GitHub 仓库 `smkzw/competitive-intelligence-workflow` 对应的**英文工程根**。默认终端工作目录可能是另一个旧中文项目；旧项目必须零接触，不读、不列、不改、不删。每条命令显式使用英文工程根的 `workdir`。不对当前脏树使用 `reset`、`checkout`、`clean`、`git add .`；历史证据和既有用户更改均保留。
2. 唯一当前台账是 [STATUS.md](STATUS.md)。正式产品合同在 [PRD.md](PRD.md)、[DESIGN.md](DESIGN.md)、[PLAN.md](PLAN.md)、[EXECUTION_RULES.md](EXECUTION_RULES.md)、[ACCEPTANCE.md](ACCEPTANCE.md)；[工作包索引](work_packages/README.md)为 W00–W10 的执行分解。0922/0923/0924 审阅 ZIP、旧 Skill、模型回执均为待验证证据，不是新的权限或当前产品权威。
3. 本次冻结前的源码基线 `bae2771b430a887ce251ad4a61ffae0cc8ac9553`，当时本地 `main` 比远端 `f629155e59ede3a1d8fbd8034820ce556b6ec828` **领先 13 提交，远端无独有提交**。本轮受控源码/测试提交为 `864e4f00754a7b574dccf8da938efc78778b74bf`；文档/回执/交接另行提交，因此接手者仍须 `git rev-parse HEAD` 与远端 `main` 核对，不能把源码提交或更早基线误当最终交接 HEAD。Goal 工具在 2026-09-27 读取到 `paused`；目标未完成，**不得标 complete**。
4. R24-57 安全来源旧开发页经独立会商判 **FAIL**；R24-62 已修其中两类呈现错误及测量 class 根因，但 197 条重分类仍待独立医学复核，Ego Lite 当前页面因本地页控制被拒而 **NOT_RUN**。R24-60 只完成两个研究的 C 来源原子，R24-61 只完成“清除数值”刷新比较的局部合同。**真实来源宇宙、三独立门户全链、三宿主、24 门户和发布门均未完成**。
5. 忽略目录 `.artifacts/r24-62-safety-semantic-20260926/` 保存修正前后 A 载荷、推导与新 A/B 安全页面共约 15 MiB，摘要在 [R24-62 回执](evidence/0924V1-r24/r24-62-safety-class-semantic-development.json)。这是本机恢复资料，**不在 GitHub 包内**；如换机，须用固定 CAS 与相同源码重建，不能仅凭报告中的 SHA 假定文件可取得。

## 2. 任务目的与裁决沿革

原始目的不是生成一张静态图，而是把新药适应症竞品研究做成可安装、可验证、可持续更新的多 Skill 工作流。A 为适应症竞品全景，B 为临床结果证据室，C 为试验设计先例库，三者独立、多页、中文、图表加原位完整表、证据可回溯且超高信息密度。一个公共入口支持一句话研究与高级 `research-package`，内部 Skill 类型化编排；跨宿主 Codex/Hermes/OMP，独立上下文复核，真实来源与不可变快照、人工触发刷新及事实级差异。

关键变更按时间先后：早期曾计划 PDF/PPT、手机和定时监测，后来被用户明确退出首版；首版 **HTML-only、仅桌面 1440/1600/1920/2560 CSS px**，不做 CSV/XLSX、雷达图、证据成熟度排名、默认竞品总排名或 Meta/NMA。0922 用户又正式纳入五项：B 保留全部相关研究并分面、实际事实修订应同步所有真实依赖的 A/B/C、C 是可检索可横比的方案先例库、个人配置复用与自包含离线分享、A/B/C 同等优先。0923 不再用 305/320/390/1024 竖屏记录作为发布门，历史 FAIL 不改写。0924 强调来源原子、科学语义、派生与消费者绑定分层，不猜分母/组别、不按总行数判完整、不用假零填缺失，并约束过度设计与“改一处测一次”。

用户另外明确：论文结果可复用，动态管线/监管状态每次核查，缓存只加速；指定历史截止日还原当时公开的证据和状态；药智已登录会话在同一运行中短期复用，访问失败即重检，不向仓库/日志写凭据。必需主要/延长期/关键安全论文缺失须先走补件与一次性无法取得分级；来源无法回答核心问题时只能给证据不足页。此前的旧中文工程退役需另获用户批准，绝不因本轮续建自动触碰。

当前 Goal 在工具中的原文：

> 基于0924V1 新的、全面的、细节化的任务计划、任务执行规范、资料包（或文件指向链接）、PRD文档、Plan文档，以及分步骤的任务执行包、验收包等等，进行实际的、不间断地任务实现，直至完全交付。 注意对过度设计、构建过程（而非构建完成后）的测试要进行约束，避免出现“改了1处测试1次”的情况

2026-09-27 用户随后要求**完成手头工作后无损暂停、记录复盘并递交 GitHub**；这是最新执行方向，暂停不代表原 Goal 完成。更早详细原 Goal 原文与演变可追 [历史目标证据](evidence/goal-before-review.json)、[REVIEW.md](REVIEW.md) 和仓库根 `HANDOFF.md` 的时间序列；不要把旧的暂停/在途字句重新解释为当前事实。

## 3. 架构地图：组件、输入、输出与责任

| 层 | 主要文件/出口 | 现状及不可越线 |
|---|---|---|
| 入口与研究 | `src/ci_workflow/application/source_research_service.py`、`tools/build_a_payload.py`、W02/W07 | 固定 CT.gov CAS 的小到全池开发切片，别名/arm–intervention/零值/未知有局部守卫；当前单源候选不等于全球/中国/文献/监管宇宙闭包或本日核查。 |
| C 原始设计 | `src/ci_workflow/application/ctgov_design_atoms.py` | R24-60 新增两研究原子及原始 JSON 路径/摘录；未形成正式可检索 C 事实/消费者。 |
| 科学事实与消费绑定 | `src/ci_workflow/storage/snapshot_store.py`、`src/ci_workflow/application/portal_consumer_registry.py`、`.../portal_consumer_binding_recovery.py` | 来源事实科学版本与 A/B/C 展示行 ID 分开；可验证合法 A+B 样本，旧快照保持只读；不能用旧 row ID 或产品名猜同事实。 |
| 用户修订/刷新 | `src/ci_workflow/application/refresh_service.py`、`tools/audit_current_a_refresh_bridge.py` | 省略/设置/明确清除、原始来源保留、undo、开发假设 A+B 扇出有局部证据；真实旧 current 的 base/user/new-source 事务、冲突选择、失败不切与 C 实际依赖尚未完整验。 |
| A/B/C 门户 | `src/ci_workflow/renderers/portal/report_a.py`、`report_b.py`、`report_c.py`、`templates/{a,b,c}` | 三独立门户，B 全相关研究而非只画可比点；图/表/来源同查询、分页/深链与桌面密度已有多个开发切片；全物理页视觉和来源科学门尚未过。 |
| 浏览器资源 | `src/ci_workflow/renderers/portal/assets/` 为唯一作者源，`assets/portal/` 是镜像，`assets/portal/manifest.json` 钉摘要 | R24-62 已同步 `report-b.js` 与清单，禁止双作者分叉。Ego Lite 本轮控制拒绝本地页面；不得借换浏览器、起本地 HTTP、CDP 等路径绕过。 |
| 分享/安装 | `src/ci_workflow/application/share_export.py`、W06/W08 | A-only/B-only/A+B 的 committed-current ZIP 静态自包含切片通过，C 与新浏览器离线尚未过；分享包与 Skill 安装包不同，不能带商业全文、凭据或开发路径。 |
| 测试与发布 | `tools/gate.sh`、W09/W10 | gate 只对 Ruff、strict-mypy、活跃单元/合同、保留兼容子集、分层和旧路径检查给**开发质量**结论；不能代表真实医学/浏览器/安装/恢复或 RC。 |

## 4. 本次做完的事与确切证据

| 项目 | 完成边界 | 有力回执与未完成 |
|---|---|---|
| R24-57 独立会商 | `codebuddy-cli/deepseek-v4.1-flash:max` 按实际回执返回，无 fallback，guard 合法；Codex 在锁定来源上自行核实 414 未知归属行和 15 百分比/12 Events 统计类型。 | [主线程审阅](../../reviews/codex_conference_ci-0924-r24-57-safety-unit-review-20260926_review.md)判冻结旧候选 FAIL；会商模型无 Bash/SQLite 权限，一次越界只读探测被拒，未作为核验依据。 |
| R24-60 C 方案原子 | `zcode/GLM-5.3-Flash:max` 终态，主线程读新代码/测试并复核两研究来源 SHA，19 新＋30 邻接共 **49 passed/93.05s**，Ruff/mypy 通过。 | [机器回执](evidence/0924V1-r24/r24-60-c-protocol-source-atom-development.json)、[集成审阅](../../reviews/codex_execution_ci-0924-r24-60-c-protocol-source-slice-20260926_review.md)。未交 C 报告/绑定；空数组完整性表述被收窄。 |
| R24-61 明确清除刷新比较 | 显式 null 不再被当成“用户没有修改”；同源保留 user_modified，新源变化产生 CONFLICT，定向 **4 passed**。 | [回执](evidence/0924V1-r24/r24-61-explicit-clear-refresh-comparison-development.json)。旧 current 实际刷新/失败回滚仍 NOT_RUN。 |
| R24-62 安全测量语义 | 514 行同 ID 同原值，197 行重分类，12 行事件次数基数纠正；严重/重度/相关/停药等保留 class，B 比例标签与未知产品侧栏修正。生产函数先 **14 RED**，整族＋邻接 **69 passed/127.89s**。 | [回执](evidence/0924V1-r24/r24-62-safety-class-semantic-development.json)。独立医学/本轮浏览器仍 PENDING/NOT_RUN，24 个 lab/ECG class 归属仍需重审。 |

R24-62 普通入口重建 A **56** 页、B **205** 页；安全页本机摘要 A `dc9727bc99449594c4fbc5dca0a3c50498a6320d37518064b6d430fb4ba582d4`、B `360537c86771e47f4a828c82bab16cecb45097c77abae80f833c81608d444f28`。B 安全 514 行虽可达，但该直渲染**未使用另一个已部分验证的逐行 `safety_views` 来源输入**；因此不能把旧 R24-57 的 514/514 定位回执嫁接给新 B 页面。414 行组别—产品未知应继续不可绘为产品点、不可误链产品；历史 9 月 6 日来源不能称 9 月 27 日实时核查。锁定 SQLite SHA `a1434296bff630e187a4fe1357a44708ba60ffe3101512e452cbe46a99699c12` 未改。

## 5. W00–W10 现况：未完成不代表从零开始

| 工作包 | 可复用进展 | 发布/验收剩余门 |
|---|---|---|
| W00 基线 | 受控仓库、source-set 和开发 gate 已有；大量未跟踪历史运行资料保留。 | 最终干净发包清单、候选 identity；勿全量追认脏树。 |
| W01 证据/快照 | 精确来源、不可变快照、恢复 sidecar 有受限实证。 | 全源逐事实信任闭包与独立签发。 |
| W02 通用入口 | 固定 CAS PNH 单源普通 A/B 候选、基础研究关系；部分真实输入。 | 一句话/高级入口跨适应症与 A/B/C 真实产物合同。 |
| W03 科学合同 | 零/缺失、分母/arm 资格、比较上下文与本次安全 class 局部守卫。 | 197 重分类独立复核、其余域全语义/统计资格。 |
| W04 修订 | 明确清除、undo、A+B 合法共源开发演练。 | 真实来源变化的旧 current 三方事务、冲突/回滚、合法 C 依赖。 |
| W05A/B/C 门户 | 三报告都有正常渲染入口与桌面局部；B 大集分页/搜索；C 固定样本检索。 | 各物理页四宽×四状态实际视觉/键盘/跨浏览器，C 真实先例库。 |
| W06 个人复用/分享 | A/B 已提交版本的单份/联合静态 ZIP 有证据。 | 同一个真实 A/B/C 项目三单包＋联合包、新浏览器/断网/移目录互动。 |
| W07 真实研究/刷新 | 历史 PNH 单源 50 研究 4412 结果原子；不同阶段的小批逐事实定位与当前源只读差异。 | 多源全球/中国/论文/监管完整性、Publication/药智条件路线、动态复核、正式刷新。 |
| W08 安装/宿主/恢复 | 早期包/恢复框架存在。 | 当前 HTML-only 包、fresh-install、Codex/Hermes/OMP 实宿主、可信恢复复验。 |
| W09 八适应症×三报告 | 历史运行与开发候选不等于最终 24 门户。 | 特应性皮炎、重度哮喘、类风湿关节炎、溃疡性结肠炎、CRSwNP、结节性痒疹、IgAN、PNH 各 A/B/C 真实科学＋视觉验收。 |
| W10 RC | 无 RC 冻结条件满足。 | P0/P1 为零、P2 处理、唯一源/包/快照身份、恢复与三宿主/24 门户门全过后才可 `RC_FROZEN`。 |

## 6. 尚未通过、为什么会停与踩过的坑

- **本次暂停原因是用户指令，不是工作完成。** Goal 是 paused，旧真实 current 未更新。不可因 49/69/开发 gate 通过宣布科学、视觉或产品验收。
- 用户可见的安全性科学歧义最关键：一个父标题下按 class 列“严重/重度/停药”不能全部当总体 TEAE；`Events` 是事件次数，不能自动除以人数；`Percentage of participants` 与 `participant_proportion` 不能落成“事件发生率”。修复引发 197 行分类变化，必须独立挑战真实类别与 UI，不是用模型自信关闭。
- 组别—产品归属未知的 414 行本来在表格守界，却在 B 证据侧栏漏守卫，导致假产品链接；现代码修，但浏览器当前候选未查。逐事实来源和产品归属是两个门：有原文不等于可绑定产品或可编辑。
- 固定来源的 B `514/514` 精确定位和本次直接重建 B 页是**两条不同链**。后者未挂来源视图；不能用两个各自 PASS 拼出不存在的最终 PASS。源日期也不能混称今天的新鲜状态。
- 本轮 Ego Lite 对本地页返回拒绝控制；主线程没有改走其他自动浏览器、文件协议替代或本地服务器。受影响的交互/审美/离线门保持 NOT_RUN。历史旧版本 Ego Lite 截图仍可作为历史局部证据，但不能顶替新 SHA 的实测。
- 派发模型能发现问题，但会商的 Bash/SQLite 工具权限不足；主线程必须用只读实际来源复核，且不能采信未授权的递归派发结果。C 执行者说“空列表都记缺失路径”超出已覆盖两研究，已缩小结论。
- 历史工程多次将局部 gate 或页面截图表述得过宽，造成返工。这里实行根因一族 RED→最小完整修复→相关 GREEN，**仅里程碑跑一次全仓开发 gate**；视觉、医学、来源、安装分别有自己的证据。前期积累的 7000 余项未跟踪文件主要是旧原始站点/日志，不能因方便提交全量 `git add .` 或不加辨别地清理。

## 7. 下一位 Agent 的安全起步与步骤

1. 读取全局 AGENTS.md 与此英文工程的 AGENTS.md、PRD/DESIGN/PLAN/EXECUTION_RULES/ACCEPTANCE/STATUS，以及本页；不盲信已安装的旧竞品 Skill。查 `git rev-parse HEAD`、`git status --short`、`git ls-remote origin refs/heads/main`，确认本轮提交和源/资产 SHA；读取会商/执行 review 与 R24-60/61/62 回执，不重跑旧 PNH v107 的逐症状全页循环。
2. **先冻结同一候选**：R24-62 的 197 条分类迁移按“原文 class/父结局/数值形式/原单位/上下文/展示位置”抽样加异常全查，尤其 24 条 lab/ECG、严重 TEAE、重度 TEAE、停药及 12 个 Events；独立临床会商挑战后由 Codex 决定。若有改动，另立候选，不改旧回执 SHA。将合法 `safety_views` 精确来源真正接入新 B 普通资料包/当前版，不能只依靠两套独立测试。
3. 在合规 Ego Lite 本地页面控制可用时，先查 B 侧栏 414 未知归属无假产品链接、比例/事件次数标签、A 安全图表与原位完整表、Esc 回焦；再按四宽×稀疏/密集/筛后稀疏/来源侧栏覆盖 A/B/C 各物理页。若工具仍拒绝，留 NOT_RUN 并推进非浏览器分支，不能绕过。
4. 并行推进 W07 来源闭包与 W05C：从 R24-60 两研究 C 原子接正式设计观察/来源版本/消费者和关键词/研究列/原条款横比；空数组与缺失路径单独反例。真实来源新鲜度按来源性质管理；扩全球、中国、论文/监管及可选药智，Publication 缺件门和独立竞品宇宙复核要实跑。A/B/C 同优先，不让 A 的全量美化阻塞 B/C 结构。
5. W04/W06 做**一条真实操作链**：在已逐源合法绑定的隔离当前项目，普通/估计值编辑、明确清除/恢复/undo、A+B 与 C 仅真实引用时扇出，失败保持旧 current、幂等重试，随后从 committed current 出 A/B/C 单份及联合离线分享；新浏览器、断网、移目录查当前值/原文/配置。旧项目 current 迁移先在副本验证，不把开发假设值当医学订正。
6. 保持包与验收层次：W08 三宿主/fresh-install/恢复，W09 24 个真实门户，W10 唯一 RC；每包记录完整输入/输出 SHA、PASS/FAIL/NOT_RUN、真实模型身份与浏览器来源。范围变化需按用户原生 Ask 选择题询问；纯实现细节可自主完成。

## 8. 恢复证据、质量门、清理与递交

- 本机可恢复输入：`.artifacts/r24-pnh-auto-binding-full-20260926/inputs/report-a-r24-22-bound.json` SHA `9a13e4b867e0f27341a616409bdd179851d8467cf7b6cf411a04d54f5b39b45d`；本轮 compact 目录四文件摘要见 R24-62 回执。两研究 C 固定 CAS SHA `5d35c3ce835ebea73cc28e53cc6216773247fb77e0b1053b45eb83036ce6b3be`。来源资产若未随 Git 走，重建前需按现有受控 CAS/manifest 找回；不伪称 GitHub 自包含所有原始论文/页面。
- 代码最小回归：`uv run pytest -q tests/integration/test_r24_safety_class_context.py tests/integration/test_w03_safety_numeric_contract.py tests/integration/test_w07_ctgov_capture_bridge.py tests/integration/test_r24_full_b_safety_source_view_projection.py tests/integration/reports/test_b_report_portal.py` 为本次 69 项；C 原子 `tests/integration/test_r24_c_ctgov_protocol_atoms.py` 加邻接 `test_w07_ctgov_capture_bridge.py` 为 49 项。代码/规则变化时按受影响族重跑，不机械每行重跑全仓。
- 开发门 `bash tools/gate.sh` 本轮一次实跑为 **GATE_OK quality-only/6 步**：Ruff 全 `src/tests/tools`、strict mypy 全 `src/tools` 252 文件、活跃 unit/contract 1067、retained 兼容子集 20、分层 7、旧路径检查均过；见 [R24-63 门与清理回执](evidence/0924V1-r24/r24-63-pause-quality-and-recovery.json)。它不跑所有 integration/browser，更非医学/发布门。
- 原 221 MiB A/B 临时完整站点在系统临时目录，本轮只保留约 15 MiB 紧凑证据；清理只针对**本轮明确创建且已校验的临时目录**，不删固定 CAS、旧页、快照、会商报告、Codex session 或不明未跟踪文件。清理后完整站点需按当前生成代码/输入重建；候选身份与本地恢复目录写在机器回执。
- 本轮 GitHub 递交只纳入有意修改的英文仓库源码、必要测试、规范状态、精简机器回执和主线程执行审阅；原始模型会商输出和本机 route/context 留在本地恢复面，不作为公开仓库文件。不追认 7000+ 未跟踪日志/原始站点，不提交凭据/会话/商业全文。推送后核远端 `main` 等于本地提交；若远端先前进，停止推送并记录差异，禁止强推。

## 9. 给用户的非工程化复盘

做了：把部分安全性结果“看着像同一类、其实不是”的错误拆开修正，也堵住了一个可能把归属未确认的研究组误连到产品的入口；补上“用户明确清除数值”在刷新时的判断；对两项试验的设计原文建立了可追溯的初步资料。关键结果与恢复资料都留下了。

没做：没有证明所有竞品资料齐全、没有完成三个报告的全程验收，也没有在这次受限的浏览器环境里确认新页面外观/交互；更没有完成三宿主、24 份报告和正式发布。

踩坑：原文的大标题和子类不能混为一谈；有原文不代表能确定产品归属；通过代码测试和看过旧版页面都不能代表新版实际可用。下一步先让独立人员挑战这批医学重分类，恢复合规页面检验，再把 C 方案来源和完整多源研究接入现有事实/报告链。
