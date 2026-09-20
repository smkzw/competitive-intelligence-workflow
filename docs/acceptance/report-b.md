# B 类报告验收记录

## 当前接受对象

- 适应症：阵发性睡眠性血红蛋白尿
- 报告版本：`v-fixture-b-pnh-001`
- 最终候选：`output/acceptance/task-6.10/phase-6-acceptance-package-20260830/b-pnh-responsive-visual-evidence-20260830/reports/B/v-fixture-b-pnh-001/html/`
- 运行标识：`run_fa24d20b3e1fdbc4252b7596`
- 报告快照：`report-snapshot_fb255c120a1da4f5aba550e7`
- 案例摘要：`26c8eab4a77c26b0f6260808d339889c49b9b1f830ed8c5728a7980875164ad2`
- HTML 目录摘要：`f1b37ba4745997df319485fb6e929e24ed1153d0304376f6740c45fda3800381`
- 接受清单摘要：`d3be39828b6eea1b6acc918cf8df5387030048248f842730be52d6f4d645dc85`

## 第一版持久化确定性验收包（历史记录）

- 包目录：`output/acceptance/task-6.10/phase-6-acceptance-package-20260830/`
- 包清单摘要：`1e00bb8b8d091366c25e4b2309b9dca21f6fcb1efac1c17d9a13f6cba6c87e13`
- 包状态：`pending_codex_visual_verdict`。本包只绑定四个当前运行及其确定性产物；未执行视觉接受，不发布 Phase 6，不启动 Phase 7。

| 案例 | 当前运行 | 快照 | 运行/格式状态 | 输出 |
|---|---|---|---|---|
| `b-pnh` | `run_70569970b9101bbc70c261cf` | `report-snapshot_9a5fb715c9158d58e0dbe7cb` | `snapshot_locked / quality_check` | `.../b-pnh/reports/B/v-fixture-b-pnh-001/html/` |
| `b-d70-baseline-blocked` | `run_ad17d0e431d17232a32bd86b` | — | `evidence_blocked / not_generated` | `.../b-d70-baseline-blocked/blockers/B/v-fixture-b-d70-001/` |
| `b-d70-baseline-recovered` | `run_3ebb46320b259609bce769bf` | `report-snapshot_d3a21323fbd4e5de041966df` | `snapshot_locked / quality_check` | `.../b-d70-baseline-recovered/reports/B/v-fixture-b-d70-002/html/` |
| `b-d70-disposition-missing-pass` | `run_eb0c8c94578410b2a94269ca` | `report-snapshot_03ec154a227cada4a65de0de` | `snapshot_locked / quality_check` | `.../b-d70-disposition-missing-pass/reports/B/v-fixture-b-d70-003/html/` |

阻断案例的确定性缺口为 `NCT04558918 / apply-treatment / 年龄`；处置未公开案例保留完整未公开状态且未阻断。四个案例的逐案摘要见包清单，分别为 `18cd8eb006494dfdfbddd4cb126b55945b60de4bf9e169bef4945f07f0ef7da2`、`c87bd675a4aedd4238c15766c28d3627da3f39db4aba9e5ccedf480e1b6dca19`、`db54d1b4a5f41680e80950c62e55745160dfa00d793eb25063210a1a34245c1a`、`1b8854adb6088e1ebc30958edb4e4314328b550305a63573c2c5573dcf5c4ff7`。

## 用户可见结果

- 24 个站点页面采用同一中文临床试验设计语言；正文不显示后端字段、流程标签或提示词。
- 首页与内容页均为图在前、完整表格在后；疗效、安全性、疗效—安全性矩阵、基线和试验完成情况均可筛选与下钻。
- 安全性热图在默认 1024 宽度内完整显示，不依赖左右拖动；不适用与未公开使用文字、纹理和颜色共同区分。
- 基线指标按“人、岁、%、g/dL”拆为同单位小多图；试验完成情况按 APPLY-PNH 与 APPOINT-PNH 分图。
- 图中未公开值不按零绘制，完整预定义字段仍保留在表格中。
- APPLY-PNH 处置显示：随机并接受治疗 62/35，完成治疗 61/35，完成研究 62/35；治疗组与对照组身份在图、表和数据依据中一致。

## 决定性检查

- 146 项 B 类门户、报告、图表同步、康哲设计合同与包清单测试通过。
- 24 页在 Chromium 与 WebKit 的 1024、1280、1440 宽度扫描：页面横向溢出均为 0；指定 B 类可见文本小于 16px 计数均为 0。
- Codex 独立查看 1024 宽度的基线、试验完成情况及安全性全页截图。
- MiniMax、Cursor Grok、CodeBuddy 均完成真实连通性测试并保留审阅记录；CodeBuddy 的视觉能力限制已明确记录，不作为视觉放行依据。
- Kimi Code 独立会商同一会话完成 v7→v8→v9 复核；v9 双内核复核未发现新的 P0/P1。

- 本次持久化包核验：四份当前运行清单、三份报告清单/目录摘要和一份阻断审计链重算通过；fresh/注册/状态链 `15 passed`，Phase 6 B 确定性集合 `518 passed`，A 类回归 `74 passed`。

## 证据边界

- 完成情况基数依据已发表 [APPLY-PNH 主报告](https://www.nejm.org/doi/full/10.1056/NEJMoa2308695) 和基于 CSR 的 [公开受试者处置表](https://www.ncbi.nlm.nih.gov/books/NBK617236/table/tr8269868382085182_ch01_t11/) 核对；没有用审阅模型猜测值补齐。
- 处置、依从性、筛败、补救治疗、禁用药和方案偏离等未公开字段允许显示“未公开”，不阻断 B 类报告。
- 本记录只接受 B 类 HTML 门户与 Task 6.10，不表示 PDF/PPT 已生成或已验收，不启动 Phase 7。

## 最终视觉接受与阶段结论

- 第一版持久化包之后，针对 768 视口表格、菜单搜索聚焦和 Escape 关闭语义补充真实双引擎 RED；修复后 16/16 通过。
- 新候选覆盖 24 页 × 2 浏览器 × 3 宽度，144 个真实渲染目标和 150 张截图；安全性矩阵和数据表在 768/1024/1440 均无需横向拖动。
- 独立视觉会商第一轮拒绝旧摘要，第二轮在同一会话对新摘要复测后七域全部接受；正式视觉签收记录为 `visual-verification-reference.json`。
- 原始候选清单保持 `quality_check`，新的接受清单以不可变继承方式写入，状态为 `accepted`；不存在把失败候选就地改成通过的情况。
- 最终包清单：`output/acceptance/task-6.10/phase-6-acceptance-package-20260830/acceptance-package-final.json`，文件 SHA-256 `af4d79e9c1ec9161a951ba736f5ecefda34d3018ab85b07024cc9535eaf98806`。
- Codex 最终回归：聚焦集合 `317 passed`，Phase 6 与 A 类回归合计 `612 passed`。Phase 6 内部验收完成；Phase 7 尚未启动。

## 关键证据路径

- 最终运行：`output/acceptance/task-6.10/phase-6-acceptance-package-20260830/b-pnh-responsive-visual-evidence-20260830/`
- 最终截图：`output/acceptance/task-6.10/phase-6-acceptance-package-20260830/b-pnh-responsive-visual-evidence-20260830/reviews/visual-finalization/screenshots/`
- 会商结论：`runs/conference/ci-phase6-final-visual-review/visual_single_object.md`
- Codex 审阅：`reviews/codex_execution_ci-phase6-task610-visual-execution_review.md`、`reviews/codex_conference_ci-phase6-task610-visual-review_review.md`
- 详细检查点：`docs/acceptance/runs/task-6.10/checkpoint.md`
