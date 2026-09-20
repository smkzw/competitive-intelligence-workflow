# Task 6.10 无损检查点

记录日期：2026-08-30

## 状态

Task 6.10 与 Phase 6 已完成内部验收；Phase 7 尚未启动。旧 v9 和第一版持久化包保留为历史证据，当前接受对象以本文件末尾“最终收口”记录为准。

## 最终对象与摘要

| 对象 | 标识或 SHA-256 |
|---|---|
| 运行 | `run_eefcb9180978e68089c82b22` |
| 快照 | `report-snapshot_5574a880225e22c0d85e6d72` |
| 输入 | `eeae14ce581aeacc6c098cde5f45571e4d0f88d2cc5877cba5429654448381d1` |
| 案例 | `26c8eab4a77c26b0f6260808d339889c49b9b1f830ed8c5728a7980875164ad2` |
| 当前运行清单 | `b3bbba3ee10779cf9b2f052491cc50d406d6ec0024d0c8f8fd1244c76925cb32` |
| 项目产物清单 | `5b859fd11926a00a614f94abf16999c07af07658ae166161dccc2351f84161b1` |
| HTML 清单 | `ecd48df14c009fd2456b87c1978e4636dd4ede30c8e4927df3fd28edc177e460` |
| 首页 | `d25d10f27928d28143f5b0171499d9950268482fe5a08b572acd3d2e5d2c6402` |
| B 类样式 | `8f51e921c1e03d9da457e4fec2b36d98aa758b2068c25f7fab2e547f9120d26e` |

## 决定性证据

- `146 passed in 152.43s`。
- Chromium/WebKit × 1024/1280/1440 × 24 页：横向溢出 0，指定字号小于 16px 计数 0。
- v9 1024 截图：
  - `output/playwright/task-6.10-final/v9-1024-baseline-overview.png`
  - `output/playwright/task-6.10-final/v9-1024-disposition-overview.png`
  - `output/playwright/task-6.10-final/v9-1024-safety.png`
- Kimi Code v9 增量复核：`runs/conference/ci-phase6-task610-visual-review/visual_single_object_v9.md`，结论为未发现新的 P0/P1。

## 本次持久化确定性验收包

- 包目录：`output/acceptance/task-6.10/phase-6-acceptance-package-20260830/`
- 包清单：`output/acceptance/task-6.10/phase-6-acceptance-package-20260830/acceptance-package.json`
- `package_digest`：`1e00bb8b8d091366c25e4b2309b9dca21f6fcb1efac1c17d9a13f6cba6c87e13`
- 包状态：`pending_codex_visual_verdict`；只记录当前运行、报告快照、产物/阻断文件和确定性摘要，未执行视觉验收，不代表 Phase 6 接受。

| 案例 | run_id | snapshot_id | 实际状态 | 输出/阻断 | deterministic_digest |
|---|---|---|---|---|---|
| `b-pnh` | `run_70569970b9101bbc70c261cf` | `report-snapshot_9a5fb715c9158d58e0dbe7cb` | `completed / snapshot_locked / quality_check` | `reports/B/v-fixture-b-pnh-001/html` | `18cd8eb006494dfdfbddd4cb126b55945b60de4bf9e169bef4945f07f0ef7da2` |
| `b-d70-baseline-blocked` | `run_ad17d0e431d17232a32bd86b` | — | `evidence_blocked / evidence_blocked / not_generated` | `blockers/B/v-fixture-b-d70-001/`；缺少 `NCT04558918 / apply-treatment / 年龄` | `c87bd675a4aedd4238c15766c28d3627da3f39db4aba9e5ccedf480e1b6dca19` |
| `b-d70-baseline-recovered` | `run_3ebb46320b259609bce769bf` | `report-snapshot_d3a21323fbd4e5de041966df` | `completed / snapshot_locked / quality_check` | `reports/B/v-fixture-b-d70-002/html` | `db54d1b4a5f41680e80950c62e55745160dfa00d793eb25063210a1a34245c1a` |
| `b-d70-disposition-missing-pass` | `run_eb0c8c94578410b2a94269ca` | `report-snapshot_03ec154a227cada4a65de0de` | `completed / snapshot_locked / quality_check` | `reports/B/v-fixture-b-d70-003/html`；处置未公开不阻断 | `1b8854adb6088e1ebc30958edb4e4314328b550305a63573c2c5573dcf5c4ff7` |

### 文件名到合同映射

- 唯一注册表：`fixtures/catalog.yaml`；四个案例均声明 `inputs/report-data.json`，角色为 `report_data`。
- `fixture_runner` 按当前真实文件名复制为 `<case>/evidence/library/report-data.json`，不引用旧候选目录。
- 完成案例的当前运行清单、报告清单、HTML 门户和报告快照分别位于 `<case>/manifests/current_run.json`、`<case>/reports/B/<report_version>/html.manifest.json`、`<case>/reports/B/<report_version>/html/` 和 `<case>/snapshots/reports/B/<snapshot_id>.json`。
- 阻断案例仅产生 `<case>/blockers/B/<report_version>/audit.json` 与 `audit.md`，不产生 B HTML 或报告快照。

### 包级核验

- 四个项目目录均为本次新建的物理隔离目录；四个 `run_id`、四个 `case_digest`、四个输入路径均互异。
- 四份 `current_run.json` 通过 `validate_run_manifest`；三份报告清单通过 `ArtifactManifest` 和目录摘要核验；阻断审计 JSON 与 `gate_failures` 一致。
- 包摘要和四个案例 `deterministic_digest` 均按清单声明的规范 JSON + SHA-256 算法重算通过。
- `uv run pytest -q tests/acceptance/test_report_b.py tests/acceptance/test_visual_acceptance.py tests/integration/test_fixture_case_contracts.py`：`15 passed in 13.68s`。
- Phase 6 B 确定性集合：`518 passed in 220.38s`；A 类回归：`74 passed in 70.36s`。


## 已关闭问题

1. 安全性热图默认视野不能完整显示：通过响应式图表与表格布局关闭。
2. 疗效/安全性数值大量缺失：区分数据确实未公开、输入丢失和渲染丢失；已公开值进入图、表和数据依据，未公开值不伪装为零。
3. 基线混合不可比单位：按单位拆图。
4. 完成情况图数值拥挤：按试验拆图，仅绘已报告数值。
5. 组别显示为“组别未列示”：用试验组身份映射为治疗组/对照组/全研究人群。
6. 图表数值无法直接打开依据：增加不改变视觉的 32×32 点击目标。
7. APPLY-PNH 对照组人数错误：改为随机/接受治疗 35，完成治疗 35，完成研究 35；治疗组对应 62/62/61/62。
8. “未公开”提示 13/14px：B 类站点统一为 16px。

## 下一安全动作

下一安全动作是按实施计划启动 Phase 7 的独立 Trellis 任务；不得把本次 B 类 HTML 验收扩张为 PDF/PPT 验收，也不得复用旧候选作为当前结果。

## 清理与可恢复性

- v2—v8 已从当前验收目录移至 `archives/acceptance/task-6.10/old-candidates/`，不是删除；如需追溯可恢复。
- 执行工作包已由 workflow guard 移至 `archives/execution/ci-phase6-task610-visual-execution/`，保留 worker 报告、stdout 和清理清单。
- 任务专属临时视觉文件已移至 `archives/acceptance/task-6.10/transient-visual/`；最终 v9 截图继续保留在 `output/playwright/task-6.10-final/`。

## 最终收口（2026-08-30）

- 当前接受候选：`output/acceptance/task-6.10/phase-6-acceptance-package-20260830/b-pnh-responsive-visual-evidence-20260830/`。
- 产物摘要：`f1b37ba4745997df319485fb6e929e24ed1153d0304376f6740c45fda3800381`。
- 接受清单：`manifests/artifacts/artifact-manifest-accepted_002bad11c24551a833c5ce39.json`，状态 `accepted`，继承 `artifact-manifest_78a7377f0e927740225ba5ed`；旧原始清单保持 `quality_check`，未被改写。
- 最终包清单：`output/acceptance/task-6.10/phase-6-acceptance-package-20260830/acceptance-package-final.json`，文件 SHA-256 `af4d79e9c1ec9161a951ba736f5ecefda34d3018ab85b07024cc9535eaf98806`。
- 视觉证据：24 页 × Chromium/WebKit × 768/1024/1440，共 144 个目标、150 张截图；页面横向溢出、表格容器溢出、页面错误和控制台错误均为 0。
- 独立视觉会商第一轮检出 3 个阻断并拒绝旧摘要；修复后同一 session 第二轮七域全部接受。正式结论见 `runs/conference/ci-phase6-final-visual-review/visual_single_object.md`。
- Codex 回归：聚焦集合 `317 passed`；Phase 6 与 A 类回归合计 `612 passed`。
