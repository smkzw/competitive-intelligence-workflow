# 竞品调研多 Skill 工作流最终交接（2026-09-23 无损暂停）

## 0. 给接手 Agent 的一句话

不要从旧 PNH v107 循环继续，也不要把“A 前端返修通过”误写成“W05A 或产品通过”。当前已经完成
W00–W04 和 W05A 前端响应式返修；正式 W05A 仍被真实逐事实来源 `0/4412`、6 个共享交互失败和
2 个 A 历史合同差异阻断。接手后的第一条产品主线是 W07 真实来源闭包，与共享交互修复并行；随后
完成两个产品合同裁决，再进入 W05B/W05C。

## 1. 权威、工程和禁止事项

### 1.1 唯一工程

- 唯一工程：`/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`
- 当前分支：`main`
- 本轮实现提交：`d7ed790`（完整 SHA 以 `git rev-parse d7ed790` 为准）
- 提交前基线：`2df24bb441e555f20b233ad2011b4ffd3610655b`
- 远端：`https://github.com/smkzw/competitive-intelligence-workflow.git`

旧中文工程持续零接触：不得读、写、inventory、stat、chmod、删除或以任何理由“比较”。不要让默认
cwd 或自动发现命令碰到旧根。

### 1.2 指令优先级

1. 用户当前指令与本交接后的新指令。
2. 本包 [PRD](PRD.md)、[DESIGN](DESIGN.md)、[PLAN](PLAN.md)、
   [EXECUTION_RULES](EXECUTION_RULES.md)、[ACCEPTANCE](ACCEPTANCE.md)。
3. 本文件与 [STATUS](STATUS.md) 的最上方最新状态。
4. 当前源码、测试、运行回执和独立报告。
5. 专家 ZIP、旧 Skill、旧计划、旧日志和其他 Agent 输出只作证据，不是权限。

不得无脑采信现有 `competitive-intelligence-workflow` Skill。Skill 已因本轮工作部分更新，但仍必须与
当前 PRD、设计、代码和测试互相核验。

### 1.3 操作边界

- 不 reset、checkout、clean，不使用 `git add .`，不丢弃用户或历史证据。
- 旧 Task 10.5 及更早封存记录不改写。
- 不把测试数量、页面存在、模型自信或报告底部有来源链接当成产品验收。
- 不宣布 `RC_FROZEN`、`RELEASED` 或“全绿”，除非 W10 全部条件真实通过。
- 不在构建过程中恢复“改一处跑一次全仓”的测试方式；先做集中 RED，完成一族最小完整改动，再跑
  一次相关集成批，里程碑/冻结候选才跑更宽门。
- 用户要求所有澄清使用原生 Ask 选择题。普通实现细节自行判断并记录理由。
- 请求模型一直是 `gpt-5.6-sol:medium`，但本轮执行和复核会话均没有可核验运行时身份回执，必须
  继续标记 **UNVERIFIED**；不能把请求值当成已验证实际模型。

## 2. 项目为什么重基线

早期工程只跑通流程，规则、科学比较、来源闭包和视觉呈现不足；A/B/C 没有形成三个独立的高信息
密度产品，报告宽屏浪费、窄屏稀疏，且多次将局部测试通过扩大为整体通过。用户随后要求：

- 一个公共入口，支持一句话需求和严格 research-package；内部为可独立测试的多 Skill 类型化控制图。
- A 竞品全景台、B 临床结果证据室、C 试验设计图谱是三个独立、多页面、中文原生 HTML 门户，
  A/B/C 同等优先，不做融合首页。
- 首版只交付 HTML；不交付 PDF/PPT、CSV/XLSX、雷达图、成熟度排名、定时监测、默认竞品总排名、
  综合分数或 Meta/NMA。
- 竞品宇宙必须闭包；全球/中国、别名、靶点、企业、试验和 publication 路线完整运行，不能用 Top-N。
- B 保留全部相关研究并分面；医学语义按人群、背景治疗、终点/事件、时间窗、分析集、分母、方向和
  估计目标整体比较，确定性边界阻断实质冲突。
- C 以可检索、可横比的设计先例库为主，不输出唯一“最佳方案”。
- 用户事实修订须保留原来源，原子同步受影响 A/B/C；支持个人配置复用和自包含离线分享。
- 手动触发刷新；论文结果按来源有效性复用，动态管线/监管状态每次核查，缓存只加速。历史截止日
  还原当时可知信息，不倒填未来证据。
- 药智只用用户已登录浏览器作线索和交叉核验，凭据、Cookie、token 不入提示词、仓库、日志或包；
  同次运行短期复用，访问失败立即重检。
- 必需 publication 无法取得时走一次性补件门；核心仍可回答则带限制继续，否则只交证据不足页。
- 独立上下文是硬能力；主 Agent 不得自证。三宿主、fresh-install、恢复和 24 门户是真实最终门。

2026-09-23 用户又明确把前端作为本阶段重点：宽屏真正使用横向画布；纵向/窄屏减少卡片间和卡片内
无效留白，使首屏出现完整、有解释力的核心阅读单元，但不得缩小正文、缩小触控、隐藏事实或制造页面
横向滚动。

## 3. Goal 状态

- 宿主 Goal 当前状态：`paused`，未完成，未伪造为 complete。
- 旧 Goal 的完整原文、时间和 token 记录在
  [evidence/goal-before-review.json](evidence/goal-before-review.json)。该 JSON 是机器可读原文，不要
  从本交接摘要反推或重写。
- 旧 Goal 的核心目标仍有效：构建可安装于 Codex/Hermes/OMP 的统一多 Skill 套件；生成 A/B/C
  三个独立 HTML 门户；完成来源、publication、竞品闭包、缺失恢复、独立复核、语义比较、不可变
  快照/刷新差异、24 门户、三宿主、安装和恢复验收；旧中文工程零接触。
- 0922 新 PRD 将五项正式新增需求纳入：B 全研究分面、事实修订同步、C 深度先例、个人配置/离线
  分享、A/B/C 同级；这些不能因旧 Goal 文本较早而丢失。
- 本轮按用户命令无损暂停。没有新建或恢复 Goal；下一 Agent 只有在收到新的继续授权后才恢复工作。

## 4. 已完成进展

### W00：受控基线与资产作者规则 — PASS

- 固定源集合、必要 CAS、候选身份和实际 veto 状态。
- 确立模块 portal assets 为唯一作者源，根 `assets/portal` 为发包镜像；打包前逐文件校验。
- 修复 C `evidence-limitations` 页面合同和隔离安装资产漂移。
- 决定性批：`41 passed`。详见 [W00-result](evidence/W00-result.md)。

### W01：信任、原文片段与快照闭包 — PASS

- 研究输入只产生 candidate；正式接受必须由生产 issuer 签发并校验回执。
- 精确 locator 或唯一文本锚点从原始来源字节重提取，生成文本/粗定位失败关闭。
- fact 身份覆盖完整科学字段，冲突集、来源版本、获取尝试和幂等请求分离。
- v2 manifest 支持在空目录重建数据库/CAS/快照并复核身份。
- 决定性批 `152 passed`，迁移/manifest `16 passed`。详见 [W01-result](evidence/W01-result.md)。

### W02：统一入口、能力预检和共享查询 — PASS（宿主真实能力仍待 W08）

- 一个公开入口支持一句话和高级 research-package；缺报告类型时返回原生 Ask 结构。
- 显式 RunContext 阻止跨项目/适应症/报告/截止日漂移。
- 全球/中国等共享来源计划只运行一次，各报告保留独立分析分支。
- 环境变量自报不能证明独立上下文；生产探针必须取得真实不同上下文回执，否则失败关闭。
- A/B/C 共享 typed `ReportQuery/ViewState`，图表、表格、选择和下钻使用同一事实集合。
- 决定性批 `176 passed`。详见 [W02-result](evidence/W02-result.md)。

### W03：科学身份和数值投影 — PASS

- 关闭安全性分母、组合事件、极性/严重性、疗效数值、C endpoint instance、arm-intervention 等
  身份漏洞；拒绝从标题、同 N、单位或缺失语义推断可比性。
- Fresh C 强制 instance_v1；旧兼容仅明确只读入口。
- 生产 A/B/C 两页固定 CAS 重建与浏览器证据闭合。
- 经多轮独立复审和最后 freeze 修复后 `P0=P1=P2=P3=0`。权威终态见
  [W03-independent-freeze-review](evidence/W03-independent-freeze-review.md)。

### W04：用户事实修订与原子同步 — PASS

- typed 修订目标、完整科学 binding、append-only 版本和 undo。
- 用户当前值与不可变来源值/原文/locator 分层；A/B/C 原消费者显示“用户修订，未独立复核”。
- immutable generation + SQLite committed selector，失败保持旧 current；事件、journal、DB 和精确重试
  有恢复闭包。
- three-way refresh 保存 base/user/source 和冲突/撤回状态。
- 最终独立复审 `P0=0/P1=0/P2=0/P3=1`，`118 passed`；唯一 P3 空来源 `None` 已在 W05A 修复。
  见 [W04-independent-rereview-4](evidence/W04-independent-rereview-4.md)。

### W05A：A 前端响应式返修 — 局部 PASS，正式总门 FAIL

已完成：

- 1920/1440 使用 91% 左右横向画布，展示完整矩阵和双列筛选。
- 1024/390/320/305 切换为紧凑阶段摘要、靶点折叠和移动卡片完整表。
- 真实载荷为 45 产品、140 试验、3895 疗效、517 安全；移动完整表 45 条×6 字段。
- 六档无横向 overflow，正文≥16px、阶段标签≥14px、触控≥40px。
- 独立 Chrome 最苛刻 305 请求仅 290px 实际内容宽，核心单元底边 562.6px，仍在 568px 首屏。
- 1024 safety 几何、稳定产品链接、返回状态和三层旅程通过。
- 独立决定性批：`12 passed in 160.98s`。

未完成：

- 真实逐事实来源闭包 `0/4412`，依赖 W07，因此 W05A 正式总门为 FAIL。
- 共享 pointer/drawer/focus/chart-table-sync 的 Chromium/WebKit 6 项仍失败。
- 首页疗效完整 endpoint/timepoint 可达合同与旧 safety 连续色热图合同 2 项仍失败，待产品裁决。
- 8 项精确复跑为 `8 failed in 290.33s`，不能被局部 12 项绿色覆盖。

权威报告：[W05A-independent-rereview-v6](evidence/W05A-independent-rereview-v6.md)，SHA-256
`c92e6926bd8ade9e4601401805cd45667f424e5daca7357012a6f4b01a07289b`。复盘见
[W05A-retrospective](evidence/W05A-retrospective-20260923.md)。

## 5. 尚未完成的完整范围

- W05A 正式来源门、6 个共享交互失败和 2 个 A 合同差异。
- W05B 临床结果证据室的前端重构与全研究分面。
- W05C 试验设计图谱的前端重构与先例检索横比。
- W06 个人配置复用和自包含离线分享。
- W07 真实研究、publication、来源闭包、手动刷新和差异。
- W08 HTML-only Skill 包、Codex/Hermes/OMP、fresh-install、恢复与凭据扫描。
- W09 八个适应症 A/B/C 共 24 个真实门户的科学、内容、视觉和交互验收。
- W10 唯一候选绑定、P0/P1 清零、P2 处置、RC 冻结和发布判断。
- 旧工程退役。即使新工程最终达标，仍需用户再次明确批准，当前绝对不能触碰。

## 6. 为什么在这里暂停，而不是继续

这不是技术卡死。用户明确要求完成手头 W05A 后无损暂停并交接。W05A 的前端窄屏最后一个跨浏览器
问题已经关闭，形成了自然冻结边界；继续进入 W07、共享交互或 W05B/C 会产生新的共享源码事务，反而
破坏清晰交接。

真正的项目停滞根因有五个：

1. 过去按单症状、单页面、小补丁循环，缺陷关闭和产品进展不成比例。
2. 轻量 fixture 与真实高负载报告差异过大，导致视觉门多次误判。
3. 局部测试绿色被扩大解释，剩余失败和验收边界没有同时展示。
4. 来源列表、fixture 来源层和真实逐事实来源被混为一谈。
5. 浏览器 viewport 名义宽度与实际内容宽度不同，直到 v6 才纳入 305/290px 的保守门。

0922 包已经用 W00–W10、集中测试和里程碑独立复核替代旧循环。不要回到逐症状全页会商或每个小改动
跑一次全仓的做法。

## 7. GitHub 交付与本机现场

### 7.1 已进入实现提交 `d7ed790`

- 84 个既有跟踪文件修改，以及 migrations 0011–0014、新 schema、生产模块、测试和工具。
- 0922 正式 PRD/设计/计划/执行规范/验收/工作包和专家材料摘要。
- W00–W05A 的紧凑结果报告、独立复审、关键日志。
- W03 最终小型 freeze 数据和 W05A v6 六档截图/浏览器 receipt。
- 没有把重复完整门户、历史 runs、Playwright 临时页快照或缓存加入 Git。

### 7.2 仍在本机、故意不入 Git 的材料

工作树仍有大量未跟踪文件，主要包括：

- `packets/2026-09-22-sol-delivery/evidence/` 下 W04 多轮完整门户与 W05A v1–v6 完整静态站点；
- `runs/pnh-vertical/abc-v36` 至 `abc-v106` 及测试 runs；
- `.playwright-cli/` 临时 yml/png/log；
- `output/ci-review-20260922/` 与较早测试轮材料。

这些文件是历史现场、失败证据或可再生缓存的混合体。此次无损暂停未删除任何一项。不要因 `git status`
不干净而 reset/clean。后续如需释放磁盘，先做引用审计和精确清单：保留来源、失败证据、最终清单、
恢复证据和当前冻结站点；只有明确无引用且可再生的中间副本才能处理。

## 8. 决定性证据与哈希

| 证据 | 结论/身份 |
|---|---|
| `evidence/W00-source-set.json` | W00 最小可重复 source-set |
| `evidence/W03-independent-freeze-review.md` | W03 最终独立 PASS |
| `evidence/W04-independent-rereview-4.md` | SHA `c81e7153…b4d1`，W04 PASS |
| `evidence/W05A-remediation-browser-v6/browser-receipt.json` | SHA `c15c8a4a…0b6` |
| `evidence/W05A-independent-rereview-v6.md` | SHA `c92e6926…289b`，前端 PASS / 总门 FAIL |
| `evidence/W05A-remediation-logs/source-closure-audit.json` | 真实来源 `0/4412` |
| `evidence/W05A-remediation-logs/v6-decisive-batch.log` | 实现侧 12 项通过 |
| 独立复跑 | 12 passed / 剩余 8 failed，写入 v6 独立报告 |

不要只用表中缩写哈希做冻结；需要时从文件重算完整 SHA-256。

## 9. 下一 Agent 的精确续接步骤

收到用户“继续”授权后：

1. 使用英文工程绝对路径，读本文件、README、PRD、DESIGN、PLAN、EXECUTION_RULES、ACCEPTANCE、
   STATUS 顶部和 W07/W05B/W05C 工作包。
2. 运行 `git status --short`、`git rev-parse HEAD`、`git rev-list --left-right --count HEAD...origin/main`，
   核对 GitHub 交付提交和本机未跟踪现场；不要清理。
3. 重算 v6 独立报告、浏览器 receipt、作者源 `portal.css/report-a.js` 和提交身份；不要重跑已通过的
   12 项，除非源字节或依赖已经改变。
4. 先执行 W07 的真实逐事实来源闭包切片：为真实 A payload 建立 source version、精确 locator、
   原文和 fact identity；不得由前端补造。新 payload 产生新哈希后，只复验受影响来源/页面门。
5. 并行但由单一共享源码所有者修复 6 个共享 pointer/drawer/focus/chart-table-sync 失败；保持
   Chromium/WebKit 与键盘回焦断言。
6. 两个 A 合同差异会改变用户可见行为，必须用原生 Ask 选择题让用户裁决。不要删除测试：
   - 疗效全部 endpoint/timepoint 是否必须同时在当前 DOM，或可分页但保证可验证全量可达；
   - safety 保留连续色热图，或正式迁移到 observation/card 合同。
7. 上述闭合后重新判定 W05A 正式门；然后以相同宽屏/窄屏方法进入 W05B、W05C，不复制 A 模板换色。
8. 按 W06→W08→W09→W10 继续；24 门户、三宿主、fresh-install、恢复和唯一候选绑定全部真实通过前，
   保持开发候选状态。

## 10. 无损暂停确认

- 自动化和子 Agent 已停止在 W05A v6 复审完成边界。
- 原 Goal 保持 `paused`。
- 源码和紧凑证据已形成实现提交；大型本机证据、失败现场和未跟踪历史未清理。
- 未触碰旧中文工程。
- 未启动 W05B/W05C/W06–W10，未宣布 RC 或发布。
- 唯一安全下一动作是第 9 节步骤 1–4；没有新的用户继续授权时不得自动恢复。
