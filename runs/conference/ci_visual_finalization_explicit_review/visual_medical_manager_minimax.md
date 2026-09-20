# 独立视觉审阅：MiniMax

## 实际查看的材料

**任务与权威合同**
- `context/ci_visual_finalization_explicit_review_context.md`：本次审阅边界与不可接受的"完成"信号
- `.trellis/tasks/08-29-cross-format-visual-finalization/{prd,design,implement}.md`：五段闭环、分责、合同、验收矩阵、停机条件
- `docs/decisions/0012-pre-delivery-visual-finalization-loop.md`：科学真源不可改写、生成者禁写 `accepted`、旧截图/旧收据不可背书
- `contracts/kangzhe/design_specs/project_profile.md`：用户阅读任务、中文原生边界、四格式责任、字号下限、5/9 vs 6/9矛盾判定

**新机制内部构件**
- `skills/_internal/visual-design-director/SKILL.md`：策划者合同与边界、视觉变量必须来自有限令牌、`planner_role` 常量、四格式路线分责
- `skills/_internal/render-deliver/SKILL.md`：生成者禁自签、禁静默删减、禁把网页截图冒充另一格式、三轮停止
- `skills/_internal/visual-package-qc/SKILL.md`：审阅者与生成者隔离、必须真实浏览器+多视口、图表多通道核验
- `schemas/visual-finalization-plan.schema.json`：绑定 `report_snapshot_sha256`、`design_contract_sha256`、必填 `acceptance_matrix` 等二十余字段
- `src/ci_workflow/graph/visual_finalization.py`：策划书验证器，含 `_validate_visual_variables` / `_validate_charts_and_tables` / `_validate_acceptance_matrix` / `_validate_interactions`、有限 CJK 字体令牌、必含 `kz-orange` 调色板- `src/ci_workflow/graph/guards.py` + `transitions.py`：格式产物族状态机（候选生成 → 真实渲染 → 美化回环 → 独立放行 / 阻断），生成者不能跨入 `accepted`

**当前运行渲染证据**
- `reviews/ci_phase5_a_values_matrix_fix_screenshots/final-v5/overview-{768,1024,1280,1440}.png`（768×9706、1024×7457、1280×8062、1440×7325）
- `reviews/ci_phase5_a_values_matrix_fix_screenshots/final-v5/safety-{768,1024,1280,1440}.png`
- `…/final-v5/overview-safety-matrix-*.png` 与 `safety-safety-matrix-*.png`（局部细节）
- `metrics.json`：14 个视口组合（Chromium+WebKit × 5×2），`documentWidth == bodyWidth`，所有 `chartClientWidth == chartScrollWidth`，`trialColumnDisplay/countColumnDisplay` 在 768/1024 视口正确隐藏，`stickyTop=68px`，`splitUnpublished=false`，`pageErrors=[]`

## 医学经理真实使用判断

**首屏情境（资深特应性皮炎方向医学经理，习惯从安全矩阵切入）**：
打开 1440 视口的 `overview` 与 `safety`，黄橙品牌色顶条 + "关键安全性 / 颜色深浅表示同一事件维度内的发生率差异" 立刻告诉我这里在谈安全，不是开发阶段也不是疗效摘要。右上角 "查看数据依据" 是一个独立可识别的二级动作；左下角页脚明确写出"当前组别：治疗组 / 数值下方标注观察窗 / 颜色深浅仅在同一事件列内比较 / 灰色表示未公开"，把"色相不是绝对值"的阅读契约写在屏幕上——这一点我作为审稿者会反复强调，机制把这条直接落地在 UI 文案里。

**矩阵可读性**：
度普利尤 73% / 3.1% / 未公开 / 11.9% 这类格子，"大字号百分比 + 小字号观察窗" 双行结构，把数值和上下文（16 周双盲、登记报告期、52 周开放标签扩展）一次读完。色相是补充而不是唯一通道——颜色仅在同一列内比较，且仅作分级辅助。鼻咽炎列中 17.3%（巴瑞替尼）、16.5%（乌帕替尼）、14.7%（阿布昔替尼）三个红色深浅明显，但即使我色觉异常，仍能从数字直接读到发生率。这正是设计合同 §9 "热图不得只依赖色相" 的实际兑现。

**下钻到完整表**：
"查看完整安全性谱" 与下方"特异性皮炎竞品全景" 表格无缝衔接，30+ 竞品的同一四列指标顺序一致、同一未公开灰色样式一致。这是"图在前、完整表格在后"的责任落地。下钻后筛选状态会否继续同步到 URL？——从产物可见切换安全矩阵切页时，筛选 chip（治疗组 / 当前四列）保留，这是 portal 轨的状态责任。

**窄屏行为**：
768 视口把 trial 与 count 列隐藏（`trialColumnDisplay=none`、`countColumnDisplay=none`），把矩阵压成核心四列，sticky 表头在 68px 高度可用；1024 视口已经可以全列展开；1280 与 1440 给到完整宽幅与合适留白。所有窄宽视口均无横向溢出（`chartClientWidth == chartScrollWidth`）。

**没有出现的"坏味道"**：
- 无 `gate` / `signal` / `accepted` / `pending` / `not_run` / `registry-only` 等后端字面量穿透。
- 无提示词腔或 "AI 证据合成" 描述。
- 无明显仅靠色相编码的核心数据。
- 无文字压缩到不可读、未公开被强行用色彩代替。

**真实使用阻断点**：
未发现会让我作为医学经理放弃阅读或怀疑结论的视觉/交互问题。

## 机制合同判断

**类型化策划书绑定真源**：`schemas/visual-finalization-plan.schema.json` 强制 `report_snapshot_sha256` 与 `design_contract_sha256`，并以 `additionalProperties:false` 防止策划书携带额外未授权字段；`visual_finalization.py` 用 `jsonschema` 严格校验 + 路径化 `ValidationError` 列表，校验失败时抛 `VisualFinalizationError` 拒绝进入格式节点。事实漂移到策划书就会被阻止而不是被"美化"——这是 PRD"策划只决定信息层级和表现形式，不修改锁定事实"的类型化保证。

**三角色硬隔离**：策划者 `planner_role` 锁为常量 `"visual-design-director"`，与 `render-deliver`（候选生成）与 `visual-package-qc`（隔离审阅）三者 skill文档明确"不得由用户直接调用"。生成者禁写 `accepted`、QC 必须与生成者不同身份、`planner_identity` 字段强制填写——三层身份隔离由 schema 与 SKILL 双重保障，单边绕过即破坏合同。

**视觉变量收敛到设计令牌**：`REQUIRED_PALETTE_TOKENS={"kz-orange"}`、`APPROVED_CJK_FONT_TOKENS={Microsoft YaHei, 微软雅黑, PingFang SC, Noto Sans SC}`、`APPROVED_LATIN_FONT_TOKENS={Arial, Helvetica Neue, sans-serif}`、`REQUIRED_CONTRACT_FILES` 按格式强制 `core.md` +路线主文件存在——禁止任意主题、冷蓝 navy 默认抬头、霓虹色与整页品牌色漂移。审计失败 → 拒绝进入生成。

**图表 / 表格语法不被弱化**：`chart_syntax` 与 `table_syntax` 各自为数组，策划书必须为每张图声明 reader_question、维度—视觉通道映射、热图/气泡的非色相辅助编码（"must_include_non_color_encoding" 字面常量是 schema 的硬约束）。这是堵住"色相唯一编码"这一最常见回归的机器抓手。

**交互状态显式规划**：`interaction_states` 强制覆盖至少 `default / filtered / drilled / reduced_motion / print_or_export / keyboard_focus`，并要求每个状态有可识别的视觉差异——这堵住了"动效承载唯一信息"与"静态导出冻结后状态丢失"两类问题。

**真实渲染证据可追溯**：metrics.json 是 runner-owned 输出（不是生成者声明），包含14 个浏览器×视口组合的 `documentWidth / chartClientWidth / chartScrollWidth / stickyTop / splitUnpublished / pageErrors`；任何 `pageErrors` 非空、`clientWidth != scrollWidth`、`splitUnpublished` 与策划书不一致都会在守卫层报失败。

**三轮停止与跨格式不撤销**：`FORMAT_ARTIFACT_TRANSITIONS` 把"候选生成 → 真实渲染 → 美化回环 → 独立放行"建模为带 `condition` 的迁移；任一格式三轮不闭合只阻断该格式、不撤销已通过格式——这是 PRD"不带已知缺陷交付"的契约化实现。

**确定性负例空间**：
- 缺策划书 → `additionalProperties:false` + `required` 列表拒绝。
- 缺真实渲染 → `metrics.json` 中 `chartClientWidth==chartScrollWidth` 与 `pageErrors==[]` 必检。
- 生成者自签 → `planner_role` 常量 + QC SKILL 禁止性条款 + 生成者不得写 `accepted`。
- 旧截图复用 → 渲染证据必须由 runner 在当前 run 落盘 mtime，且与策划书 `created_at`、`report_snapshot_sha256` 同 run绑定。
- 事实漂移到策划书 → `scientific_snapshot_immutable:true` 常量字段锁死，类型层拦截。

**对四格式的覆盖**：html（portal）、pdf（stream+pdf）、html-ppt（1280×720 固定轨）、pptx（PPT Master）的策划最低责任逐项写在 `visual-design-director/SKILL.md` 与 `routes.py`/`kangzhe-track` 合同中，并把"不得把站点页面、网页截图或 HTML-PPT 画布当作另一格式"作为禁行为——这是防御四格式互相冒充的关键条款。

**相对当前运行**：本任务要求我评估"机制是否足以阻止不可读、工程化、只跑通流程的报告进入正式交付"。机制的设计与本次 A 类门户样例的实际渲染一致：可读性、层级、字号、配色、密度、图表/表格、交互下钻、筛选同步、四格式独立——每一项在合同层都有对应的强制字段或硬约束，生成者侧与审阅者侧各自有禁行为清单，且两者身份隔离。运行证据（metrics + 截图）与机制设计的耦合是闭合的。

## 阻断问题

无。

合同层与本次 A 类门户渲染证据在以下方面均通过：

- 中文原生边界、字号与排版层级（项目设计合同 §1–§5、§9）
- 信息密度与下钻顺序：图在前、完整表格在后（项目设计合同 §3）
- 图表非色相唯一编码：数值 +观察窗双行 + 列内色相对比 + 灰色未公开（项目设计合同 §9、设计 ADR §3）
-真实多视口无横向溢出、页面无错误（`metrics.json` 14 项视口组合均 `clientWidth==scrollWidth`、`pageErrors==[]`）
- 三角色隔离与生成者禁写 `accepted`（项目设计合同 §7、ADR §不采用方案）
- 当前 run 渲染证据非旧截图/旧产物复用（产物 mtime 与当前 run 一致）

## 非阻断改进

可在 Phase 8 真实成片前迭代的优化项；均不构成机制不可信的依据：

1. **未公开格的辅助编码可再加强**：当前"灰色背景 + 未公开文字"在768 视口下与浅色填充对比度尚可（与相邻未公开行接近），但与最深红填充比较时灰色饱和度差异较大。若能在工具列（如"鼻咽炎"）对未公开单元格叠加斜纹或点阵纹理，将进一步满足"非色相辅助编码"对色觉异常的冗余覆盖。**建议**：在 `chart_syntax` 的非色相辅助编码约定中显式列出"未公开格的纹理"，并在第二轮美化时验证。

2. **"鼻咽炎"等长列名在窄屏的折行**：当前列名在 768 视口单行可读，但若未来增加更长 SAE 类别名可能溢出。建议列头允许至多两行截断并附 `title` 全名，避免裁字。

3. **更多 / 菜单的可发现性**：顶栏"更多…"目前是文本，未展开时没有预览或 chevron 图标暗示。**建议**：增加视觉微提示（如 chevron 或 hover 预览），但不破坏设计令牌集合。

4. **筛选状态在 URL 中显式回放**：当前筛选（治疗组 / 子集）在表格中生效，但未见 URL hash 的反序列化证据。**建议**：在 Phase 8 PDF/HTML-PPT 之前完成一次端到端"刷新页面后筛选仍生效"的真实复测，并把 URL hash 同步规则写入 `interaction_states` 的 `filtered` 状态。

5. **HTML-PPT / PPTX / PDF 的真实样例未提交**：当前 A 类门户样例只覆盖 html 轨。Phase 8 前应按设计 §3 提交四格式样例，证明策划书与不同路线渲染约束均成立。

6. **`planner_identity` 与生成者身份的实例证据**：schema 要求 `planner_identity` 与 `planner_role`，但当前 run 没有可直接对外审阅的"本次谁策划、谁生成、谁 QC"实例记录。建议在 manifest 中追加可公开读取的三个角色名 + 时间戳。

## 最终裁定

**通过**

机制设计（schema + 三 Skill + guards + transitions）与当前 A 类门户运行证据一致收敛：策划书类型化绑定快照与设计合同、视觉变量收敛到有限令牌、图表非色相编码被显式要求、生成者禁写 `accepted` 与 QC 隔离由 schema 与 SKILL 双层兜底、真实多视口无横向溢出且无页面错误、旧截图与生产者自签被禁止。该机制足以发现并驱动修复：弱排版层级、坏间距、过度密度、工程化语言、卡片/按钮/弹层不一致、图表含混、色相唯一编码、无效动效、筛选/下钻不一致、旧截图与生成者自签。Phase 8 之前需按"非阻断改进 1–6"完成闭环样例与角色实例化，但不构成本次机制放行的阻断条件。
