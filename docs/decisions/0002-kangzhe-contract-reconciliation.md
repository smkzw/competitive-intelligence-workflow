# ADR 0002：康哲设计合同候选核对

- 状态：等待上游单一可移植分轨包完成实产物验收并稳定，再请求用户确认；历史双全文方案已被替代
- 首次核对：2026-08-10
- 最新复核：2026-08-11
- 核对方式：差异分析前完整读取并记录元数据，差异分析后再次完整读取并复核同一组元数据

> 第 1–9 节保留 2026-08-10 两轮历史候选与当时建议的审计记录，均已被 2026-08-11 的单一 `design_specs` 架构替代，不能再用于批准或封装；当前决定以第 10–14 节为准。

## 1. v1.2 规格中的既有锚点

| 角色 | 文件 | v1.2 记录的 SHA-256 | 当时行数 |
|---|---|---|---:|
| 跨 Agent 默认合同 | `design_share_v2.md` | `113cc55f39d469ae91760da10c0cc3e28071573d35f4095b05b1d96d8cfb5c46` | 4,279 |
| 本地增强合同 | `design_v2.md` | `8d8dc9f67478caefda0fde8c3555863b49db5055739e6db8d3192e15622f4def` | 4,331 |

当时记录显示 share 第 11 行至文末与 local 第 63 行至文末逐字节一致，共同正文 SHA-256 为 `49c39fc209445a8bc679993483bf50d7b4a7566cbb55688b3448bb53f1f09ce7`。

## 2. 当前稳定候选

两份文件在差异分析前后保持完全相同；`path`、`realpath`、inode、size、mtime_ns 和 SHA-256 均未漂移。

| 角色 | inode | 字节 | 行数 | mtime | 当前 SHA-256 |
|---|---:|---:|---:|---|---|
| share | 61096016 | 316,474 | 4,416 | 2026-08-10 17:54:49 +0800 | `069f18d5cbfd9a4760f73e53d6b5f54149c44918337ad9c9ff8640389f1b203b` |
| local | 61096015 | 320,568 | 4,468 | 2026-08-10 17:54:49 +0800 | `efa4324aa4a29790da3315bf0cf1fc6d08f4ed25071e3c4f32cf67f4cdb7da2c` |

两个当前候选均标记为 v2.1，较 v1.2 规格记录的候选各增加 137 行。旧候选的字节副本未保存在可核验工作区，因此不能把当前文件与旧摘要做逐行机械 diff；本记录不虚构具体旧版删改位置。

## 3. 当前内容对本项目的实际影响

当前合同明确支持并区分五条媒介路线。本项目使用其中三条：

1. A/B/C 门户走 §14.12 站点式 HTML；不得套用 1280×720 幻灯片画布，也不得以单篇长文档冒充多页面站点。
2. HTML-PPT 走 §14.1–§14.9，使用 1280×720 固定逻辑画布、等比缩放、观众运行时、S 键讲者视图和逐页讲稿。
3. 可编辑 PPTX 走 §13，并必须通过已接入的 PPT Master 全流程；不能以网页截图或图片页代替。

跨格式共同约束包括：正式 Logo 槽、暖橙黄品牌主调、避免深蓝“科技感”压过品牌色、图表与表格的医学可读性、真实浏览器/Office 渲染、无溢出/重叠、内容和证据边界。share 版不含 `/Users/` 绝对路径，可作为跨 Agent 包内默认合同；local 版的本机资产和已验收样本只可在摘要完整性验证后启用。

## 4. 当前阻断：共同正文并非逐字节一致

当前 share 从第 8 行起、local 从第 60 行起各有 4,409 行、314,754 字节，但只有一处不同：

```diff
- share 第 242 行：经验法则：首屏蓝系像素占比……
+ local 第 294 行：经验阈值：首屏蓝系像素占比……
```

- share 正文 SHA-256：`caa235370b0653376249416e6871922b6136c54839d050bdcde657138bacb253`
- local 正文 SHA-256：`470a769fe857b558ada91a3f636e5f844a3a58abb551242765df16a0eaa53a20`

这违反 local 合同 L.5 的“两版固定数值和规则同步”要求，也不能满足 v1.2 实施计划的共同正文摘要合同。两份文件不能按当前状态直接封装。

## 5. 推荐决定

推荐以“经验阈值”为共同措辞：该句给出了可测的像素比例判定，`阈值`比`法则`更准确。只把 share 的这一处“经验法则”改为“经验阈值”，不改变任何数值、视觉要求或产品语义；预计修正后的 share 文件 SHA-256 为 `5318be3cf3bd87ac029e0249823322a85a32c3c74fdd00287db82baac6b6a36d`，两版共同正文 SHA-256 为 `470a769fe857b558ada91a3f636e5f844a3a58abb551242765df16a0eaa53a20`。

用户若批准此路线，后续按以下顺序执行：

1. 修正 share 源文件的一个词；
2. 重新执行稳定双读并核对实际摘要，不以预计摘要代替实测；
3. 将实际两个文件摘要、共同正文摘要、批准时间写入包内 manifest；
4. 原样复制两个已确认文件，再封装 Logo、ECharts 和 HTML-PPT 离线资产；
5. 运行摘要、离线资产和真实格式入口合同测试。

在用户确认前，不复制合同、不创建活动 `design.md` 映射、不封装视觉资产，也不进入 Task 0.4。

## 6. 2026-08-11 复核：候选已发生有来源的设计演进

2026-08-11 开始继续实施前，重新执行两轮完整读取。两轮的 path、realpath、inode、size、mtime_ns 和 SHA-256 一致，但与第 2 节记录不同：

| 角色 | inode | 字节 | 行数 | mtime | 当前 SHA-256 |
|---|---:|---:|---:|---|---|
| share | 61096016 | 318,353 | 4,454 | 2026-08-10 23:49:33 +0800 | `273983cf2cabe3784449953bac7ccff1fb9d613b85628a5082a07cd28ed653a4` |
| local | 61096015 | 322,690 | 4,513 | 2026-08-10 23:49:33 +0800 | `ea81c66ff1e0f3b0fa26a667af88dfd93d571ecf4125b99ddcd04c094d158e70` |

变化并非网络失败、文件损坏或无来源的并发覆盖。只读追踪确认：同目录在 23:48 新建 `design_specs/`；Grok Build 会话 `019feab3-f10a-7dc3-bd62-8cdcf6cc1186` 保存了对应文件编辑记录和用户指令。用户在该会话中明确要求继续设计验收，并评估“先判断产物类型、再精准调用对应 design spec”；任务最终采用“路由 + 共享内核 + 五轨投影包，完整双合同继续作为权威正文”。两份主文件和分轨文件的修改时间、会话编辑记录相互吻合。

没有进程继续占用两份文件；Documents 下没有第二份同名副本，也没有可用 APFS 本地快照。原文件的 WeChat 扩展属性只说明最初来源，不能解释本次编辑者；编辑记录才是本次变化的直接证据。

因此，第 5 节的“经验法则 → 经验阈值”请求现已失效：这两个词在当前两份文件中均不存在，旧预测摘要 `5318be3c...` 不得再使用。

## 7. 当前双合同关系与新增分轨加载包

share 从第 8 行起、local 从第 60 行起不再逐字节相同：

| 正文 | 行数 | 字节 | SHA-256 |
|---|---:|---:|---|
| share | 4,447 | 316,633 | `74038868557fe0b8c29c9dda91263e2c9b90d4822464ac1a0c5a38d70e8ce1c5` |
| local | 4,454 | 316,876 | `4dbc0c0b3b6dd1c0fb98aff28c8abcf5bb1596f24df03feb7895898f0a16206f` |

机械 diff 只有一个 hunk，位于 §0.0：share 以可分享的通用语言说明可选投影层；local 明确列出 `design_specs/ROUTER.md`、`core.md`、五个 `track_*.md` 和 `ARCHITECTURE.md`。这是一处有意的本地增强差异，不再适合用“单一共同正文摘要”隐藏。

当前分轨加载包共 9 个文件：

| 文件 | SHA-256 |
|---|---|
| `ARCHITECTURE.md` | `0910ddfd3dda4e387753102b3d8eb39ae046f05795763515db9ded41d1cb2987` |
| `README.md` | `959b7e35c6c30d6d8ede7d5c521fb834bf0cf65747fc711b0d363a55cec25f40` |
| `ROUTER.md` | `7eb608ecd17c4c0b0b45e10f3fd374d11bba1ce9dafd22229f194bd10b883d2f` |
| `core.md` | `744a94e598bb700f9bd516e343ae7757692e51b5d5963186f37d00b088b1e7b1` |
| `track_htmlppt.md` | `6b95de2f3f7d54fdd648341551c319df29fc183abd056c27fafb8bff24b6e8bb` |
| `track_interactive.md` | `d6dd0d14688597e753fa0e03da31cc87f591a06a39221566622f13ae7de86098` |
| `track_pptx.md` | `5c0db521b38ff77dd6304f006f2e4687ac7b258ef609db44156b76d7a1c2ddad` |
| `track_site.md` | `026d9c2e0c18fa300c3c0bae1b091f7cd12ae26b54cfa5d69a6ff7f2604431f1` |
| `track_stream.md` | `3c295755ac82f42bd51aa2a76f17fa5c3f573503125cc0e9eccdfd6ed38cc56e` |

按“相对文件名 + 制表符 + 文件摘要 + 换行”排序拼接后的集合摘要为 `96fff26fc3bab525b8a4ced6cf69dc8a0bf39ba7c6ebc7ddc1e352203f4d395e`。

## 8. 对可安装工作流的影响

当前全局 `kangzhe-ppt-design` Skill 通过 symlink 读取本机模板目录，适合本机使用，但不能直接成为“安装到任意 Agent”的新包运行依赖。尤其 `design_specs/ROUTER.md` 末尾含两个 `/Users/...` 绝对路径；原样复制后，其他机器会在读取权威正文时失败。

因此，Task 0.3 需要在不改动上游两份主合同的前提下：

1. 两份主合同按用户确认后的实际摘要原样复制；share 继续作为跨 Agent 默认完整合同，local 作为可选增强合同。
2. 把 9 个分轨文件纳入包内 `contracts/kangzhe/design_specs/`，而不是依赖宿主 symlink。
3. 仅对包内 `ROUTER.md` 的两个 SSOT 锚点生成可移植副本，改为相对路径 `../design_v2.md` 与 `../design_share_v2.md`；manifest 同时保存上游摘要与包内摘要，禁止无记录改写。
4. manifest 不再声称两版正文逐字节相同；分别保存两个正文摘要、唯一允许差异的 §0.0 hunk 摘要，以及分轨集合摘要。任何额外正文差异均失败关闭。
5. `SKILL.md` 固定执行“ROUTER → core → 对应 track → 完整合同专章”，但所有解析均以包根为基准。

这不是扩展新的视觉规则，而是把用户已经批准实施的分轨加载架构转成可移植包合同。

## 9. 最新推荐决定

建议确认采用第 6–8 节记录的最新 v2.1 组合：两份当前主合同 + 9 个分轨加载文件；允许新包仅把 `ROUTER.md` 的两个本机绝对路径改为包内相对路径，并以“两个正文摘要 + 声明的单一 §0.0 差异”替代已经失效的单一共同正文摘要。

用户确认后必须再次稳定双读；若任一主合同或分轨文件再次变化，本次确认自动失效，重新生成差异材料。在确认前仍不复制合同、不封装 Logo/ECharts/HTML-PPT 资产，也不进入 Task 0.4。

## 10. 2026-08-11 08:19 再次变化：单一可移植包取代双全文

实施前的稳定性复查再次发现摘要变化。当前两个根文件已成为完全相同的 829 字节兼容入口：

| 文件 | mtime | SHA-256 | 当前角色 |
|---|---|---|---|
| `design_share_v2.md` | 2026-08-11 08:19:51 +0800 | `e513b4c5d56ae666148f1c22d535295483447f236da02d55efead0d8d185ed18` | 指向 `design_specs/` 的入口 stub |
| `design_v2.md` | 2026-08-11 08:19:51 +0800 | `e513b4c5d56ae666148f1c22d535295483447f236da02d55efead0d8d185ed18` | 指向 `design_specs/` 的入口 stub |

当前路由文件明确宣布：`design_specs/` 是单一完整合同；读取顺序为 `ROUTER.md → core.md → 恰好一条 track`，多格式分别走完各自路线。主入口不再承载完整 MUST/NEVER，故第 8–9 节的“两份完整主合同 + 9 个投影文件”封装建议已失效，不得继续执行。

## 11. 当前候选包摘要与直接检查

当前 `design_specs/` 有 12 个文件，按“相对路径 + 制表符 + SHA-256 + 换行”排序拼接后的集合摘要为：

`f0aeed82df411b2471feeede92d8b566300eaad752d42777feb031ba15d3fc4e`

关键文件：

| 文件 | SHA-256 |
|---|---|
| `ROUTER.md` | `b67125001153dd6733b7d34f43544fdc9a01c551b45e9fc6bca19f308a09a807` |
| `core.md` | `acdd64bf0281bc0d27c7da5b8fd48127f69997403ce7cd48fc649291cf554aeb` |
| `track_htmlppt.md` | `91e9395fa3668d5fb94e8fc05422831688eafe4677387f9026205b2a5c1e14fa` |
| `track_interactive.md` | `68501e5f4fcc3ae72b3a22e858e240c5739e0133f71fed512cd504f9c8086687` |
| `track_pptx.md` | `7e7dcd0833d7e6a79d41cc0ada48efe7b5d9ffbcaf09aa2bbad9b39acd1d88f3` |
| `track_site.md` | `0baf152a342678e93d2666ca679e584848bed273678def225bc9dca79702a663` |
| `track_stream.md` | `4e1baca0b306b99272bfe4dcb437ef44ceb421eb30396fa1faa0e4c58812bc8e` |
| `assets/logo_bot.svg` | `8d16d3ae8353dd31f46a50d401e66f9e62af40be6cc42cdf5050866a4e6e1cae` |
| `tests/test_package_load.py` | `258d3650457bba70744841dd1d25879d0aed17658f1b4d95b1d08e2640c36093` |

其结构测试 6 项通过：必需文件、便携合同无 `/Users/`、Logo、单轨加载体量、核心品牌约束及路由完整性。但这只证明结构，不证明视觉产物已验收。当前另一个已授权设计任务已把 post-split 实产物连续通过计数重置为 0，并正在运行 S1；因此不能把 6 个结构测试当作设计合同冻结证据。

同时发现 `local_map.md` 的 L.5 仍保留“`design_share_v2.md` / `design_v2.md` 双全文同步”的旧规则，与当前 `ARCHITECTURE.md` 的“根文件均为 stub、单一完整合同在 design_specs”相矛盾。虽然 `local_map.md` 是可选本机增强层，不影响跨机器加载，但在候选冻结前应由其设计任务消除此误导；本项目不越权修改上游合同。

## 12. 当前建议

本项目只接受完成实产物验证并修正内部矛盾后的整个 `design_specs/` 目录，不再复制两份历史全文，也不对 `ROUTER.md` 做项目内改写。根目录两个 stub 可作为兼容入口一并保存，但不作为权威正文。

在上游 S1 验收尚未结束时，本项目继续完成 Logo、ECharts 和 HTML-PPT 运行层的只读来源核验；不复制设计包、不进入 Task 0.4。上游稳定后重新计算全部文件与集合摘要，再向用户只请求一次精确确认。

## 13. 用户确认后对已批准计划 Task 0.3 的等价适配

这不是另起一套实施计划，而是让 Task 0.3 保持原目标——“包内自包含、摘要锁定、用户确认后才启用”——同时匹配上游已经采用的单一权威结构。确认前只记录映射，不创建目标文件。

| 原计划位置 | 旧假设 | 确认后的等价实现 |
|---|---|---|
| 结构树约第 311 行 | `contracts/kangzhe/{design_share_v2.md,design_v2.md,manifest.json}` | `contracts/kangzhe/design_specs/**` 为权威包；两个 829 字节 stub 原样放在 `contracts/kangzhe/` 与 `design_specs/` 同级，使其相对链接可解析，但不参与规则加载 |
| Task 0.3 Files | 创建两份完整合同 | 原样复制用户确认时的整个 `design_specs/`；不得从五轨重新拼接一份隐藏 monorepo |
| Task 0.3 Step 2 | 两个全文摘要 + 共同正文摘要 | 记录全目录集合摘要、每个文件摘要、`ROUTER/core/各 track/Logo` 角色、批准时间；不存在“共同正文摘要” |
| Task 0.3 Step 3 | 固定两个全文摘要 | 固定确认后的集合摘要和逐文件摘要；验证路由仅加载 `core + 恰好一轨`，多格式分别加载，不把 optional `local_map` 当跨机器依赖 |
| Task 0.3 Step 4 | `design.md` 解析到 share 全文 | 公共 Skill 的康哲入口解析到包内 `design_specs/ROUTER.md`；不得把 stub 或全局 symlink 当运行权威 |
| Task 0.3 Step 5 | HTML-PPT runtime 直接放入 | 按 ADR 0003 生成有来源清单的康哲衍生运行层：保留讲者/翻页，删除主题和演示动画，修正逐页页码，中文化讲者界面 |
| Task 8.8 PM03 | 收据绑定两份设计全文 | 收据绑定确认后的 design_specs 集合摘要、实际 track 摘要、Logo 摘要及适用章节；PPTX 仍由 PPT Master 生成 |

确认后 Task 0.3 的目标文件应为：

```text
contracts/kangzhe/
├── design_share_v2.md
├── design_v2.md
├── design_specs/
│   ├── ROUTER.md
│   ├── core.md
│   ├── track_pptx.md
│   ├── track_htmlppt.md
│   ├── track_stream.md
│   ├── track_site.md
│   ├── track_interactive.md
│   ├── assets/logo_bot.svg
│   ├── README.md
│   ├── ARCHITECTURE.md
│   ├── local_map.md
│   └── tests/test_package_load.py
└── manifest.json
```

项目内新增合同测试必须至少机械验证：

1. manifest 的 collection digest 与逐文件 SHA-256 重算一致；任一文件新增、删除或漂移均失败。
2. `ROUTER → core → one track` 的全部相对链接可解析；五轨均可独立加载，多格式不能只加载一轨冒充。
3. 除 optional `local_map.md` 外，权威包不含 `/Users/`；运行时不得读取 `local_map.md` 才能合规。
4. 两个同级 compat stub 内容相同、相对链接可解析到包内路由，不承载第二份 MUST/NEVER 正文。
5. Logo 摘要、`viewBox`、ECharts 版本/许可、HTML-PPT 衍生运行层来源和离线依赖符合 ADR 0003。
6. `site`、`htmlppt`、`pptx`、`interactive` 四条本项目实际路线分别能从公共 Skill 解析到正确 track；站点不得继承 1280×720，HTML-PPT 必须继承讲者运行时，PPTX 必须继承可编辑/PPT Master 要求。

如果用户确认前上游再次改动，或 S1 视觉验收导致任何 track 修订，本节的目标树仍有效，但所有摘要必须重新计算，不能复用本节之前记录的候选值。

## 14. 报告生成时的加载边界

`design_specs` 的长合同用于构建和验证公共渲染层，不要求每次 A/B/C 报告生成都让宿主 Agent 重新解释数千行规则并自由编写最终页面。正式职责分界见 [ADR 0004](0004-structured-report-rendering-boundary.md)：医学节点提交类型化 view model；门户、PDF、HTML-PPT 与 PPT Master 来源包由确定性投影生成，并由当前产物的真实渲染记录接受。

S1 已证明结构测试或生成者自述不够：流式路线在零文件时仍退出 0；HTML-PPT 虽可打开但缺失讲者功能并违反逐字稿和最小字号合同。因此 Task 0.3 只冻结通过实产物验证的设计包，Task 0.4 以后必须让“产物存在 + 责任覆盖 + 真实渲染 + 独立接受”共同拥有完成判定。

## 15. S1 PPTX 真实成片复核：候选仍不接受

2026-08-11 对 S1 PPTX 的 12 页 LibreOffice 渲染图、PowerPoint 对象树、字号和生成源码进行只读复核。指定来源 `S1_pptx_ops_brief.md`（SHA-256 `5b1671b74efe2374e3ab0419939e9458ecce06145d47ea3cd169200a630d66de`）只声明七段结构与品牌硬约束，没有业务数字。生成脚本却硬编码并混用了其他 S1 样例中的 `11/5/4/1`、`9/3`、`15/5`，又自行得到 `10` 和 `67%`。第 4 页同时把 `9` 标为“待复核”、把 `4` 标为“待澄清”且未说明两个集合的关系，无法由指定来源重建。

真实视觉也不符合候选合同：第 11 页四张 KPI 卡的上下标签明显重叠；第 4、6、8、11 页存在 9–11.25 pt 可见文字，而 `core.md` I-03 要求 PPT 可见文字至少 12 pt。生成者的 `FRICTION.md` 明知全局最小为 9 pt，却引用历史 R9 母版将其自行解释为“辅助 hint”，并在无法查看 PNG 的情况下宣布通过；这不是合同允许的例外。

本次核对的 PPTX SHA-256 为 `6b098e37e2a72c71db6f640ed8ab6b76e2d684418302d7aa68a069ea3aa36b8b`，第 11 页渲染图 SHA-256 为 `c1ca3be714d35c7308dfafcda5cd531e674741ffac7cc32cd4de6b5fd2c07045`。`officecli issues` 报告 0 项并不能推翻真实缺陷：同一结构读取还显示 12 页全部没有标题，占位/结构检查本身并未覆盖投影可读性和内容真源。

因此 post-split S1 四轨没有形成可接受基线：流式路线零产物，HTML-PPT 功能/字号/逐字稿/语义不合格，PPTX 内容真源、字号和视觉重叠不合格；上游 `CLEAR_MATRIX.md` 也仍将四轨全部记为 `pending`。同时 `local_map.md` L.5 与 `ARCHITECTURE.md` 的双全文规则矛盾未修复。当前不向用户请求版本确认，不复制 `design_specs`，不进入 Task 0.4。
