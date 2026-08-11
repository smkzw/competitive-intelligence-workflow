全部对抗探查通过。复核完成，撰写报告。

# Task 2.5 同 session 修复复核

**结论：PASS（P0=0，P1=0，P2=0）**

本 session 已完整读取 `/Users/smkzw/.hermes/SOUL.md` 全文（267 行），按委派合同执行只读复核：未编辑任何文件，未触碰 runner 报告路径 `runs/pi_ci_phase2_task25_china_sources_followup.md`，报告由 runner 持久化。

## 运行与读取证据

6 项机械检查本轮全部真实重跑通过：

| 检查 | 结果 |
|---|---|
| CN 组合套件（test_china_routes + test_company_sources + test_authoritative_wechat） | **7 passed in 0.06s** |
| 全库 `uv run pytest -q` | **173 passed in 5.58s** |
| `uv run ruff check src tests` | **All checks passed!** |
| `uv run mypy --strict src` | **Success: no issues found in 37 source files** |
| `uv run ci-workflow package verify --root .` | **PACKAGE_OK version=0.1.0a0 stage=phase-0-task-0.4** |
| `git diff --check` | **DIFF_CHECK_OK** |

逐行核对 `china_registries.py` 与 `test_china_routes.py` 当前状态：与上轮复核时一致，修复代码与显式反例测试均已就位（`_CDE_REGULATORY_EVENTS` 八类集合 + "CDE 专有事项不能归属 NMPA"；`ChinaDrugReferenceVersion.create` 的 `policy` 参数、`_CHINA_REFERENCE_POLICY_SOURCES` 映射、`policy_id/policy_version` 字段；测试新增 NMPA 错映射与 DXY 漂移两个反例）。git 无已跟踪文件被修改；`test_company_sources.py`、`test_authoritative_wechat.py`、`company.py`、`authoritative_wechat.py`、`source-policy-v1.yaml` 与上轮一致未变。

## 原缺陷 1：CDE/NMPA 事件职责混淆（首轮 P2-1）— 已修复

逐项探查证据（对抗脚本真实输出）：

- **NMPA + 8 类 CDE 专有事件全部拒绝（8/8）**：`application_accepted`、`review_in_progress`、`priority_review`、`breakthrough_therapy`、`clinical_trial_implied_license`、`review_suspended`、`application_withdrawn`、`review_resumed` 每项均抛 `ValueError`（pydantic 校验，"CDE 专有事项不能归属 NMPA"）。
- **CDE + 批准类事件拒绝（2/2）**：`marketing_approved`、`approval_withdrawn` 均抛 "批准及批准撤回事项必须归属 NMPA"。
- **正向不受损**：NMPA + `marketing_approved` → `is_marketing_approval=True`；CDE + `review_suspended` → `False`。测试层有显式反例（`pytest.raises(match="CDE 专有事项不能归属 NMPA")`）与本探查互相印证。

## 原缺陷 2：DXY/官方页未核对策略（首轮 P2-2）— 已修复

逐项探查证据：

- **正向**：当前策略下 DXY → `secondary_drug_reference`、`may_establish_official_regulatory_status=False`、`policy_id=source-policy-v1`、`policy_version=1.0`；`nmpa_official` → `official_marketing_authority`；`cde_official` → `official_review_authority`，均接受。
- **失败关闭**：DXY 中国监管状态漂移为 DIRECT → "来源策略未把丁香园用药助手限定为二次参考"；DXY 漂移为 `authoritative_secondary=True` → 同样拒绝；`nmpa_official`（映射 `regulator_official`）与 `cde_official`（映射 `cde`）中国监管状态漂移为非 DIRECT → "来源策略未把中国官方页面标记为直接监管来源"；官方页漂移为 `authoritative_secondary=True` → 同样拒绝。六种漂移方向全部阻断，与测试反例一致。

## 新缺陷

**未发现**（P0=0，P1=0，P2=0）。

## 剩余边界（非阻断）

1. **P3 遗留（前两轮已报，仍成立）**：`ChinaDrugReferenceVersion.create` 传入字面量外的未知 `source_system` 时在 `_CHINA_REFERENCE_ROLES` 字典查找处抛 KeyError（失败关闭，错误类型不友好）；`approval_withdrawn` 正向路径无显式测试（行为已由探查验证正确）；`_walk_leaves` 静默跳过 None 值字段（不产生虚假观测）。均纯程序员面，本任务无用户界面，不泄漏。
2. **Task 2.6–2.7 未验收**：本轮仍只验收 CN01–CN07 连接器数据合同；摄取定位、事实/声明链、真实多路线编排待后续任务单独验收，不提前接受。
3. **live 网络行为未验证**：离线录制 fixture 通过；真实页面结构变化、验证码等按 ADR 0008 应归入技术失败（由 `SourceReceipt.result_class` 承载），真实 live 诊断不在本轮范围。
4. 未对任何当前网页/监管/临床事实做最终判断；最终验收权归 Codex。
