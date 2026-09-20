# Conference Participant Output: ci-phase8-task86-visual-final - visual_single_object

## Boundary Check

- 同会话、只读复核；未编辑文件、未写入 runner 报告路径、未读取同侪审阅。
- 本轮按指定 10 页、Chromium/WebKit、四视口复核新原图；不作最终验收结论。

## Independent Work Product

**结论：REVISE（仅余一项 P2 展示修正；首轮 P1 均已解除）。**

### 已解除的首轮问题

- **试验数图例与柱义**：`a-06-a-clinical` 已将 KPI 明确为“试验总数 / 核心角色试验 / III期试验 / 已上市相关”，纵轴为“试验项数”，页下注释明确“柱高是试验项数；核心角色优先用于后面疗效锚定，不删除非核心试验”。计数口径和图例归属已清楚。
- **疗效轴与同期对照语义**：`b-04-b-efficacy` 纵轴已明确为“第24周应答率（%）”；APPOINT–PNH 下方明确“无同期对照”，未绘造对照柱。该展示不再依赖页脚来说明图表单位。
- **零值与未公开区分**：
  - `a-12-a-safety` 以米色格直接显示“未公开”，并在页注说明不能读成零事件；
  - `b-06-b-safety` 的 `0.0` 有独立文字说明，为“已公开为零”的突发性溶血事件，而非缺失；
  - `b-07-b-matrix` 对 APPOINT 给出“不可用”信息卡，未以零坐标或零气泡代替未披露事实。
- **终点术语与卡片身份**：`c-09-c-endpoints` 已将试验名/研究名、登记号、终点和时点分层。`EASI–75 应答；评估时点 第16周` 与页下注释一致，消除了原先 `EASI ≥ 75%改善` 的混用和中文排版问题。
- **两页路径构图**：`c-15-c-path-1` 已由大面积空白文字卡改为研究锚点条加三张“设计框架 / 治疗安排 / 人群与终点”卡；`c-16-c-path-2` 以“共同入组条件 / 共同设计 / 终点差异”三卡表达后续确证路径。两页均以现有事实构图，未为填满页面补造数据，且 Chromium/WebKit、四视口无裁切或错位。

### 剩余 P2：试验“项数”使用小数，制造无意义精度

**证据：**

以下八张原图中，纵轴和页注均界定为“试验项数”，但柱顶显示 `26.0`、`21.0`、`2.0`：

- `docs/acceptance/runs/8.6/visual-final-2-chromium/screenshots/chromium/1280x800/a-06-a-clinical.png`
- `docs/acceptance/runs/8.6/visual-final-2-chromium/screenshots/chromium/1920x1080/a-06-a-clinical.png`
- `docs/acceptance/runs/8.6/visual-final-2-chromium/screenshots/chromium/2048x1024/a-06-a-clinical.png`
- `docs/acceptance/runs/8.6/visual-final-2-chromium/screenshots/chromium/1280x720/a-06-a-clinical.png`
- `docs/acceptance/runs/8.6/visual-final-2-webkit/screenshots/webkit/1280x800/a-06-a-clinical.png`
- `docs/acceptance/runs/8.6/visual-final-2-webkit/screenshots/webkit/1920x1080/a-06-a-clinical.png`
- `docs/acceptance/runs/8.6/visual-final-2-webkit/screenshots/webkit/2048x1024/a-06-a-clinical.png`
- `docs/acceptance/runs/8.6/visual-final-2-webkit/screenshots/webkit/1280x720/a-06-a-clinical.png`

**判断：**

“项数”是离散计数。`.0` 不增加可读性，反而暗示不必要的测量精度；这与页面已经明确的计数语义冲突。不是医学数据问题，也不是空白填充问题。

**有界修复：**

仅将柱顶标签渲染为整数 `26`、`21`、`2`；保持柱高、纵轴、KPI `49`、`25`、`26`、`0` 和现有注释不变。

## Evidence And Assumptions

- 使用指定目录的浏览器原图进行复核：
  - `docs/acceptance/runs/8.6/visual-final-2-chromium/screenshots/chromium/`
  - `docs/acceptance/runs/8.6/visual-final-2-webkit/screenshots/webkit/`
- 适用设计判断依据：
  - `contracts/kangzhe/design_specs/project_profile.md`：中文原生、图表直接标注、不可将未公开值读作零、不得用虚构数据填充版面；
  - `contracts/kangzhe/design_specs/track_htmlppt.md`：固定逻辑画布、原图多视口人工审阅、路径/关系页面须有有效视觉结构。
- P2 之外，所指定页面未见剩余的标签裁切、跨浏览器换行漂移、图例丢失、零值替代未公开值、终点卡身份混淆或路径页死带。

## Risks, Gaps, And Verification Needs

- P2 改动后只需重拍 `a-06-a-clinical` 的八张受影响原图，核对整数标签未改变柱义或与 KPI 总数冲突。
- 本轮结论仅覆盖指定十页及八种浏览器/视口组合；未替代 Codex 对整套候选产物的最终视觉与交互验收。
- `b-04` 的“无同期对照”已可见；后续如调整文案，必须继续保持其独立于“对照组”图例的可比性提示，不能改成零对照值。

## Recommended Next Step

1. 将 `a-06-a-clinical` 的三个柱顶离散计数改为整数格式。
2. 重渲染该页八张原图并复核。
3. 若标签格式修复后无回归，本独立审阅范围可给出 **PASS advisory**；最终是否接受仍由 Codex 决定。
