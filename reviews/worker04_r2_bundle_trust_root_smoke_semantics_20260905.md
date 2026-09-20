# R2 信任根 bundle 闭合与保留轨门口径：拟议文档修订（worker_04，2026-09-05）

- 执行上下文：`ci-r2-independent-review-hardening-20260905` / `worker_04`
- 裁决依据：`reviews/codex_conference_ci-r2-review-runtime-fixture-acceptance-20260905_review.md`
  （“bundle closure 采纳；retained-format gate 修口径为有界兼容性 smoke，不重启排除格式产品轨”）；
  `runs/conference/ci-r2-stage-review-astra-20260905/reviewer.md` P1-5、P2-2 及其修订建议 4。
- 边界声明：本文是拟议修订提案与执行证据，不是规范文本本身；未改动任何
  canonical 设计/路线图/计划文档。Codex 保留最终采纳与发布验收裁决权。

## 1. 已落地代码与测试（本切片交付）

| 变更 | 文件 | 目的 |
|---|---|---|
| 默认 allowlist 补收 `src/ci_workflow/qc/review_receipt.py` | `tools/bundle_contract.py` | 修复 astra P1-5：`application/scientific_review_transition.py` 与 `application/run_service.py` 直接 import 该模块，原 allowlist 逐文件列举 `qc` 时漏收，干净安装包导入必失败 |
| 最终必需内容补科学复核信任根链 6 项 | `tools/bundle_contract.py` `FINAL_REQUIRED_CONTENT` | `application/scientific_review_transition.py`、`qc/review_receipt.py`、`qc/scientific.py`、`capabilities/scientific_qc.py`、`schemas/scientific-qc-verdict.schema.json`、`schemas/scientific-review-receipt.schema.json` |
| gate 保留轨步骤改名 `retained-compat-smoke` 并精确口径 | `tools/gate.sh` | 步骤只运行 tests/unit+tests/contract 内声明保留轨文件；usage 与 GATE_SCOPE 明确“不是全量保留轨、不算 v1 release gate、全量保留轨未随 gate 运行” |
| AST import 闭包合同 | `tests/contract/test_bundle_scientific_closure.py` | 默认 allowlist 必须覆盖包内全部第一方 `ci_workflow.*` import；漏收即失败关闭 |
| 隔离安装导入/最小调用合同 | 同上 | 默认 allowlist 构建 → `install_bundle` 隔离安装 → 过滤仓库源码 sys.path 后导入科学复核入口链、纯函数最小调用、并断言 v1 延后格式运行时（pdf_native/html_ppt/pptx_master/ppt_master_job）不可导入 |
| marker 双向精确相等审计 | `tests/contract/test_v1_test_layering.py` | 带 marker 文件集合 == 声明保留轨集合，防止活跃测试被静默移出门禁（astra P2-2） |
| gate smoke 口径合同（含精确文件集合 pin） | 同上 | gate 保留轨步骤名、目标目录、scope 声明与 usage 措辞全部失败关闭；smoke 精确文件集合变化必须显式改合同 |

## 2. 拟议 canonical 文档修订（待 Codex 采纳）

1. **设计 v1.3 §4/§6（安装与 bundle 合同）**：补一句“HTML-only 候选包的
   `DEFAULT_ALLOWLIST` 受 AST import 闭包合同约束；科学复核信任根链
   （状态迁移、真实回执、判定模型、能力层校验与 scientific 两个 schema）
   属于 `FINAL_REQUIRED_CONTENT`，缺一即 `verify_bundle --require-final-content`
   失败关闭”。摘要一致性不能替代模块闭合；安装包导入验收以“过滤源码路径
   后的隔离导入 + 最小调用”为准（三宿主完整安装矩阵仍留 R5）。
2. **设计 v1.3 §13.1 或路线图 R2（质量门口径）**：明确四层口径并使用新步骤名：
   - 工程质量门 = `tools/gate.sh`（ruff + mypy strict + 活跃层 fast + 兼容性
     smoke + 分层审计 + legacy 引用）；
   - HTML 活跃全量 = `-m "not retained_legacy_format"` 全树（当前 gate 内 910 项
     为 tests/unit+tests/contract 子集；全树活跃全量由验收轮执行）；
   - 保留轨兼容性 smoke = `retained-compat-smoke`，仅 tests/unit+tests/contract
     内 2 个声明文件（20 项断言），**不是全量保留轨、不算 v1 release gate**；
   - 非 HTML 保留轨全量 = 18 个声明文件，属被排除格式产品轨，保持不随 gate
     重启；运行与否由 Codex 按轮次单独决定，报告须分别列示。
3. **执行计划/检查点措辞**：任何“保留轨基础回归”表述改为上述精确口径，
   避免把 smoke 读成全量（CodeBuddy 裁决的原文缺口）。

## 3. 决策记录：package-manifest.json 无需变更

`package-manifest.json` 的 `components.schemas` 已登记 scientific-qc-verdict 与
scientific-review-receipt 两个 schema；该清单无 Python 模块字段，模块闭合由
`tools/bundle_contract.py` 的 allowlist/`FINAL_REQUIRED_CONTENT` 与
`tests/contract/test_bundle_scientific_closure.py` 承载。为避免双真源，不在
manifest 中新增模块清单。

## 4. 验证证据（本工作区副本，2026-09-05）

- RED→GREEN（TDD）：
  - RED：`test_default_allowlist_covers_first_party_import_closure`（唯一缺口
    `qc/review_receipt.py`，与 astra AST 结论一致）、
    `test_final_required_content_closes_scientific_review_trust_root`（6 项缺失）、
    `test_gate_labels_retained_step_as_bounded_compat_smoke_not_release_gate`
    （旧名/旧口径）、隔离安装导入测试（`ModuleNotFoundError: No module named
    'ci_workflow.qc.review_receipt'`，端到端复现 P1-5）。
  - GREEN：`tests/contract/test_bundle_scientific_closure.py` +
    `tests/contract/test_v1_test_layering.py` 10 项通过；
    `test_bundle_provenance.py`、`test_bundle_packaging.py`、
    `test_package_manifest.py`、`tests/hosts/test_fresh_install.py` 22 通过、
    1 跳过（真实宿主验收需 `CI_WORKFLOW_RUN_REAL_HOST_TESTS=1`，既有守卫）。
- `tools/gate.sh` 全量：6 步全部 OK（ruff；mypy strict src tools；v1-fast-tests
  910 通过/20 按标记排除；retained-compat-smoke 20 通过；v1-layer-audit 7 通过；
  legacy-references OK）→ `GATE_OK status=quality-only steps=6`。
- 并行说明：gate 运行时工作树含其他 worker 的并行修改；上述数字是当时快照。

## 5. 未验证与开放项

- 三宿主（Codex/Hermes/OMP）真实隔离安装矩阵：仍留 R5（astra 采纳决定）。
- 全量 18 文件保留轨本轮未运行（按裁决不重启产品轨）；如 Codex 需要当轮
  快照，可单独执行 `-m "retained_legacy_format"` 全树并归档输出。
- 真实宿主独立签发链、浏览器与视觉验收不在本切片；Codex 保留最终验收。
