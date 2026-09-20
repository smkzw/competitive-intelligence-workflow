我将按会议审阅要求只读核查机制合同与当前截图，先加载指定权威材料，再在原分辨率打开 overview/safety 三视口截图。接下来核对控制图、守卫和负例合同，并按原分辨率打开指定截图。我开始按原分辨率查看首页与安全性截图，并核对机制是否会把这类页面当作成品。# 独立视觉审阅：Grok

## 实际查看的材料

只读核对了审阅上下文与机制合同：`.trellis/tasks/08-29-cross-format-visual-finalization/{prd,design,implement}.md`、`docs/decisions/0012-pre-delivery-visual-finalization-loop.md`、`contracts/kangzhe/design_specs/project_profile.md`、`skills/_internal/{visual-design-director,render-deliver,visual-package-qc}/SKILL.md`、`schemas/visual-finalization-plan.schema.json`、`src/ci_workflow/graph/{visual_finalization,guards,transitions}.py`，以及负例测试 `tests/graph/test_visual_finalization_graph_negative.py`、`tests/contract/test_visual_finalization_negative.py`。对照了既有设计验收 schema `contracts/kangzhe/design_specs/schemas/design-verdict.schema.json` 与浏览器只读缺陷码 `src/ci_workflow/qc/browser.py`。

原分辨率打开了当前运行截图（非缩略图）：

- `reviews/ci_phase5_a_values_matrix_fix_screenshots/final-v5/overview-768.png`
- `reviews/ci_phase5_a_values_matrix_fix_screenshots/final-v5/overview-1024.png`
- `reviews/ci_phase5_a_values_matrix_fix_screenshots/final-v5/overview-1440.png`
- `reviews/ci_phase5_a_values_matrix_fix_screenshots/final-v5/safety-768.png`
- `reviews/ci_phase5_a_values_matrix_fix_screenshots/final-v5/safety-1024.png`
- `reviews/ci_phase5_a_values_matrix_fix_screenshots/final-v5/safety-1440.png`

为核对热图拆列与气泡重叠，额外查看了同目录 `overview-safety-matrix-{768,1440}.png`、`safety-safety-matrix-768.png`，并通读 `metrics.json`（Chromium/WebKit × 768/1024/1280/1440）。未打开交互运行时，未改任何文件。

## 医学经理真实使用判断

把这份 A 类门户当作明天要拿去开会的材料，结论是：**1024/1440 上可以扫格局和主要数字，但不能当作成品；768 上首页竞争格局不可用。** 文件在、测试过、没有横滑，都不能改变这一点。

1. **首屏没有一次讲清比较问题。** 合同要求首页先让人看到格局、疗效、安全性、开发状态。实际首页先铺一张很长的靶点分期矩阵，疗效柱、安全热图、气泡图都在折页之后。1440 上还能扫到矩阵；768 上首屏几乎就是挤在一起的分期标签。开会时我不会把笔记本递过去让领导自己找“谁更有效、谁更安全”。

2. **768 竞争格局是阻断级不可读。** 五列分期芯片换行、互相顶住，靶点行不再是一张表。这不是“信息多”，是结构塌了。1024/1440 恢复成网格后可读，说明窄屏没有被当成真实使用条件。

3. **疗效柱图可用，安全热图半可用。** 柱图有药名、终点、百分数，方向清楚。热图格子里有数字和“未公开”，不是纯靠色相猜深浅；768 把四维拆成两张两列表，数字仍能读。但大量灰色“未公开”铺满画面，一眼看不出谁在 SAE/AESI 上真正可比较。这在医学上诚实，在视觉上没有把“有数/无数”从“发生率高低”里分开。

4. **768 安全性完整表藏列。** `metrics.json` 写明 `trialColumnDisplay: "none"`、`countColumnDisplay: "none"`，同时 `pageErrors: []`、宽度与滚动宽度相等。我开会要用的是哪项试验、多少例；窄屏为了不横滑把这两列藏掉，等于把完整表收成摘要。合同写的是图在前、完整表在后，不以简洁删字段。

5. **疗效—安全性气泡图标签碰撞。** 768/1024/1440 底部气泡编号与图例药名叠在一起，分不清 1–6 号对应谁。气泡大小编码样本量、位置编码疗效/TEAE，通道是对的；标签不可读就把图废了。这不是装饰问题。

6. **中文主文案大体合格，工程词没有直接出现在我看到的标题/筛选/空值里。** “未公开”“查看数据依据”“登记报告期”能看懂。本批截图未见 `accepted`/`pending`/`prompt` 一类后台词。卡片、描边按钮、页眉在三宽上形态一致；弹层、筛选联动、下钻返回路径在静帧上无法验收。

7. **现有机器证据会把上述问题判绿。** `metrics.json` 只记视口、图表宽、热图事件数、表宽、粘性顶栏和 `pageErrors`。浏览器只读缺陷码停在死链、控制台、横溢、遮挡。这份样例正好是“无溢出但医学上不能用”的对照。

## 机制合同判断

五段闭环写在合同里是对的：策划 → 候选 → 真渲染 → 最多三轮定向修 → 生成者不能自签。`g_format_queued_generating` 没有绑定当前快照/格式/设计合同的策划书不能开工；`g_format_quality_check_passed` 拒绝缺渲染、缺独立审阅、生成者=审阅者、结论摘要与候选/渲染/策划书漂移、美化轮次 0 或大于 3。策划书对热图/气泡禁止 `redundant_encoding: none`，HTML/PDF 禁止用等价图表顶替完整表。这些负例测试是真的。

**它还不能可靠地抓住并逼修我刚刚在真图上看到的那类问题。** 原因不是“独立审阅者理论上应当看见”，而是机器层仍允许用布尔和横溢通过。

| 要防的失效 | 合同意图 | 实际牙齿 | 对这批截图 |
|---|---|---|---|
| 弱层级/字号/间距 | 七域含 `typography_spacing`、`hierarchy_density` | 守卫只要 `visual_*_check_passed: true`；策划书 `criteria` 可为“通过当前格式专属检查” | 768 格局塌陷不会被机器拒绝 |
| 过密、藏列 | 不缩字、不删已批字段 | `VisualRenderEvidence` 只有节点类型名，无 schema；`metrics.json` 把藏列记成成功 | 768 表藏试验/例数仍可判绿 |
| 工程/日志语言 | Skill 禁止；门户冻结页有词表测试 | 格式放行守卫不扫可见文案 | 本批截图碰巧干净，机制不保证下一轮 |
| 卡片/按钮/弹层不一致 | Skill 写入诊断清单 | 七域没有独立表面；无弹层状态证据 | 静帧看不出，机制也验不到 |
| 图表不清、标签碰撞 | 策划要声明问题与通道 | 只验策划声明，不验渲染后碰撞 | 气泡重叠会漏 |
| 只靠颜色 | 热图/气泡必须有文字/形状/纹理 | 只挡策划书；格子有数字即可过 | 本批热图有数字，过关；渲染层无复测 |
| 无用动效 | 须有 `none` 与减少动态 | 有令牌即可，无运行时证据 | 静帧无法证伪 |
| 筛选/下钻不一致 | Skill 要求门户筛、URL、图—表同步 | `_validate_interactions` 只强制 `page_load`；html 策划可无 `filter_change`/`drill_down`/`search` | 交互域可空转通过 |
| 旧截图、自签 | 摘要绑定 + 身份不等 | 自签能挡住；截图文件 SHA 未绑进守卫，`current_run` 只是布尔 | 可用旧渲染包给新布尔结论背书 |

`design-verdict.schema.json` 的 `checks` 仍是 `current_run` / `real_artifact` / `real_render` / `independent_verifier` / `receipts_current`，没有七域，也没有页/组件/视口原图定位。`acceptance` 节点声明了 `VisualRenderEvidence`、`BeautificationLoop`、`VisualVerificationReference`，仓库里没有对应 schema。负例测试用字面身份 `render-deliver` ≠ `visual-package-qc` 加七个 true 就能 `allowed is True`。这正好是“测试通过 ≠ 视觉完成”。

## 阻断问题

1. **真实渲染证据没有把约定视口原图、藏列和标签碰撞变成失败关闭。**  
   合同面：`src/ci_workflow/graph/definitions/new_report.py` 的 `VisualRenderEvidence`；`src/ci_workflow/graph/guards.py` 的 `g_format_quality_check_passed`；对照 `reviews/ci_phase5_a_values_matrix_fix_screenshots/final-v5/metrics.json` 与 `src/ci_workflow/qc/browser.py` 的 `DefectViolationCode`。  
   闭合条件：增加绑定当前 `candidate_artifact_digest` 的渲染证据 schema，必含 Chromium 与 WebKit × 768/1024/1440 的原图 SHA-256；缺任一视口则 `real_render`/`visual_format_render_check_passed` 不得为真。表格列计算样式为 `none`（本样例的 `trialColumnDisplay`/`countColumnDisplay`）、图表标签盒相交，必须写入未闭合视觉缺陷，不能只因 `documentWidth == viewport` 或 `pageErrors: []` 放行。用本目录 `overview-768.png` 竞争格局与 `overview-1440.png` 气泡图作负例：无缺陷记录时 `quality_check → passed` 必须拒绝。

2. **独立视觉结论可用七个布尔放行，且与旧设计验收 schema 不对齐。**  
   合同面：`contracts/kangzhe/design_specs/schemas/design-verdict.schema.json` 的 `checks`；`g_format_quality_check_passed` 的 `visual_copy_check_passed` 等；`schemas/visual-finalization-plan.schema.json` 的 `acceptance_matrix.criteria`。  
   闭合条件：落地 `VisualVerificationReference` schema：七域逐项 `accepted|rejected`，通过域的缺陷列表必须为空，否决域必须有 `{page_id, component_id, defect_code, screenshot_sha256}`；策划书每域 `criteria` 禁止同义套话，至少一条可观察条件（例如“768 靶点分期不错位”“气泡直接标注不碰撞”）。守卫改为校验该结论摘要，而不是七个 true。`tests/graph/test_visual_finalization_graph_negative.py` 里仅布尔齐全的 `_passed_evidence()` 必须改为失败。

3. **门户策划可以不声明筛选、下钻、搜索。**  
   合同面：`schemas/visual-finalization-plan.schema.json` 的 `interaction_states`；`src/ci_workflow/graph/visual_finalization.py` 的 `_validate_interactions`（只要求 `page_load`）；与 `skills/_internal/visual-design-director/SKILL.md` 的 html/portal 最低策划责任冲突。  
   闭合条件：`format=html` 且 `route_id=portal` 时，策划书必须包含 `filter_change`、`drill_down`、`search`、`keyboard`、`reduced_motion`；缺一则 `validate_visual_finalization_plan` 失败。`visual_interaction_check_passed` 为真时，渲染证据必须复测图、完整表、URL 使用同一筛选结果。仅有 `page_load` 的 html 策划书负例必须失败。

未闭合前，不能声称机制已能挡住不可读、只跑通流程的报告。

## 非阻断改进

- `chart_syntax`/`table_syntax` 允许空数组；html/pdf 至少应各有一条图表与一条 `completeness=complete` 且 `after_chart=true` 的表。
- 热图辅助编码只验策划字段；渲染层应核对格子内数字/“未公开”对比度，以及“有数/无数”与“发生率高低”不是同一灰色通道。
- 卡片、按钮、弹层层级应并入 `interaction_consistency` 或单独必检，并要求 `drawer_open` 证据。
- 可见层工程词扫描（`accepted`/`pending`/`prompt`/`pipeline` 等）应进入格式放行，而不是只活在冻结 HTML 测试里。
- 首页信息层级应写进策划书：首屏视口内必须同时露出格局、疗效、安全性入口，不能把后两者全部推到长滚之后。
- 气泡图修复路径应写死为拆页、直接标注或改小多图，禁止靠缩小字号挤开重叠。

## 最终裁定

**不通过**

闭环骨架、策划书绑定、自签拒绝和摘要防漂移已经立住，不能再靠“无横溢”或测试绿灯当视觉完成。但在当前合同表面上，768 格局崩溃、完整表藏列、气泡标签碰撞、未声明的筛选/下钻，都还能被七个布尔和一份宽度 metrics 送去放行。按资深医学经理的使用标准，机制尚未达到可交付防护。闭合上述三条阻断后，再用同一批 768/1024/1440 首页与安全性原图做一次独立否决—复测，才能重新提交。Codex 仍为终裁。
