全部交叉检查完成。无其它代码路径绕过连接器守卫；守卫标志只在连接器与测试中使用。所有机械检查与对抗探针证据齐备，撰写验收报告。

# Task 2.5 独立验收

**结论：PASS（P0=0，P1=0，P2=2）**

说明：我已完整读取 `/Users/smkzw/.hermes/SOUL.md` 全文（267 行 raw 读取至文件末尾），并按其委派合同以只读验收者身份执行：未修改任何文件，未触碰 runner 报告路径，最终报告由 runner 持久化。

## 运行与读取证据

6 项机械检查全部独立重跑，真实通过：

| 检查 | 命令 | 结果 |
|---|---|---|
| CN 组合套件 | `uv run pytest tests/integration/sources/test_china_routes.py tests/integration/sources/test_company_sources.py tests/integration/sources/test_authoritative_wechat.py -q` | **7 passed in 0.06s** |
| 全库 | `uv run pytest -q` | **173 passed in 5.59s** |
| Lint | `uv run ruff check src tests` | **All checks passed!** |
| 类型 | `uv run mypy --strict src` | **Success: no issues found in 37 source files** |
| 包校验 | `uv run ci-workflow package verify --root .` | **PACKAGE_OK version=0.1.0a0 stage=phase-0-task-0.4** |
| 差异 | `git diff --check` | **DIFF_CHECK_OK**（无冲突标记/尾随空白） |

`git status --short`：13 项未跟踪文件，全部为 Task 2.5 新增（4 连接器、3 测试、ADR 0008、context/metrics/prompts/reviews、acceptance 运行记录），无已跟踪文件被修改。构建者 green.txt 声称的 7/173 计数与本轮重跑一致（时间 6.26s vs 5.59s，同数量级）。

已逐行核对：设计 v1.2 §8、ADR 0006/0008、source-policy-v1.yaml、guideline-basis.schema.json、evidence.py（路由回执 `result_class` 与页面披露状态分层）、policy.py（8 域矩阵完整性、`SourceAuthority` 四值）、四个连接器及四个测试文件。7 个 CN 测试逐一对应 CN01–CN07 验收项。red.txt 语义真实：CN01–05/07 为对应 exact node 导入失败，CN06 首轮即通过但失败关闭由显式反例断言覆盖——与记录一致，非伪造 RED。

范围边界：CN01–CN07 连接器数据合同已验收；Task 2.6 摄取定位、2.7 事实/声明链与真实多路线编排不在本轮，不提前接受，也未因其未实现而误判。

## 国内登记与监管攻击

- **CDE 受理/审评冒充 NMPA 批准**：阻断。`_approval_flag_matches_event` 要求 `is_marketing_approval == (event_type == "marketing_approved")`，且 `marketing_approved`/`approval_withdrawn` 必须归属 NMPA。对抗探针证实：CDE + `marketing_approved` → "批准及批准撤回事项必须归属 NMPA"；CDE + `approval_withdrawn` → 同样阻断；`status_label_zh` 逐字保留"已受理/审评中"，无任何转换路径。
- **多版本稳定可追溯**：`source_record_id` 按 (authority, external_record_id)、`source_trial_id` 按规范化 CTR 号稳定；`source_version_id` 含内容 SHA-256（登记还含规范化 JSON 原文）。测试证实同记录跨版本 ID 相同、版本 ID 不同；`event_id` 含事件类型+发生日期，暂停/撤回/恢复为独立事件不覆盖历史（探针：4 事件时间线 4 个独立 ID 按时间排序）。
- **登记原文防篡改**：`ChinaDrugTrialVersion` frozen，`raw_record` 每次 `json.loads` 新解析；探针将解析字典"主要疗效"改为"被篡改"后重新提取，`original_value` 仍为"试验组 -2.1"。
- **中文字段路径/原值/URL 保留**：`_walk_leaves` 以 `sections.试验分组[0].用法用量`、`sections.主要终点[0].时间点`、`sections.试验结果摘要.严重不良事件` 形式保留精确路径，原值逐字保留，`EvidenceLocator` 含 `field_path` + URL。探针逐一确认。
- **"未公开"语义**：`result_disclosure_state` 仅由页面 `试验结果摘要` 段存在性计算（absent/空段 → `not_publicly_disclosed`），页面级事实；网络/权限/解析失败走 `SourceReceipt.result_class`（`network_error` 等 13 类），分层正确，无混淆路径。
- **丁香园不冒充官方**：dxy 固定 `secondary_drug_reference` + `may_establish_official_regulatory_status=False`；探针确认官方角色注入被拒。策略 YAML 中 dxy 无任何 DIRECT 域。
- **检索 URL**：`clinicaltrials.searchlist.dhtml?keywords=CTR…` 与 ADR 0008 官方入口一致。

## 企业与行业来源攻击

- **企业/topline/会议/管线成熟度**：`_DISCLOSURE_PROPERTIES` 六类各有中文标签与两个能力位（如 topline=主要结果初步披露、支持数字；pipeline=企业管线概览、不支持数字）。`is_peer_reviewed_publication`/`is_trial_registry_result` 默认 False 且设 True 即抛错——探针证实两类冒充均被拒。
- **公众号精确四域**：`_APPROVED_DIRECT_DOMAINS` = 疗效/安全性、中国开发与监管、企业关系与交易、专利，恰好四域；其余四域固定 CROSS_CHECK。校验要求 `set(direct_claim_domains) == _APPROVED_DIRECT_DOMAINS`（多一域、少一域都拒绝），`authorities` 与策略逐域比对。探针证实：非清单账号、账号-标签错配、第 5 域注入、策略漂移为 DIRECT 全部失败关闭。
- **策略 YAML 与连接器一致性**：五个公众号共享 YAML anchor `&authorized_cn_authorities`，`create()` 将策略 authorities 与批准范围逐域比对，漂移即抛错。公众号数字永不可标记同行评议（双重：模型校验 + 测试反例断言）。
- **文章可核验链**：`external_record_id`、标题、日期、URL、内容 SHA-256、产品/试验/事件身份、中文 locator 段落全部保留——满足 ADR 0008 "账号、标题、日期、链接、内容快照和身份都可核验才入链"。
- **未发现绕过点**：仓库级 grep 确认所有守卫标志仅在连接器与测试中出现，无摄取/报告代码路径绕过（下游属 2.6/2.7）。

## 指南谱系攻击

- **字段完整性**：`GuidelineBasis` 保存司法辖区、机构、document_id、标题、草案/正式、版本日期、人群语境、开发语境、locator（页+段+URL）、SHA-256、采集时间、废止/替代状态。CN 捕获经 `capture_cde_guideline_basis` 固定 `jurisdiction="CN", agency="CDE"`。探针证实 CN 记录 `model_dump(mode="json")` 通过 `guideline-basis.schema.json` 校验（测试仅对 FDA 项做 schema 校验，CN 项我补齐验证）。
- **草案/撤回/替代不驱动默认**：`can_drive_current_default = (final AND active)`；探针证实 draft 强置 True 被拒、withdrawn 缺撤回日期被拒、superseded 缺后继被拒。`select_current_guideline_basis` 仅选 `can_drive_current_default` 项。
- **谱系完整性**：双向替代一致性、单系列单当前版本、DFS 环检测均有效——我复现了测试的环攻击：seed 与 cycle 项内容相同故版本 ID 相同，双向检查通过后由 DFS 捕获"指南替代关系存在循环"，证实环守卫真实生效。
- **CDE/FDA 平行司法辖区**：选择按 `jurisdiction` + 人群过滤；探针证实 CN 选择只返回 CDE 2025 项、US 选择只返回 FDA 2025 项，同一人群跨辖区互不覆盖、无普遍优先级。

## 缺陷

**P0：0。P1：0。**

**P2-1（防御深度）：`ChinaRegulatoryRecordVersion` 未限制 NMPA 不得携带 CDE 专有事件类型。** 危险方向（CDE 冒充批准）已由 `_approval_flag_matches_event` 完全阻断（探针 1/2 证实），但反向——`source_system="NMPA"` + `application_accepted`/`review_in_progress` 等——被允许（探针 3 证实，`is_marketing_approval` 仍为 False，批准语义不受影响）。属录入/映射错误防御缺口，不构成误报批准。最小修复：`create()` 按 `source_system` 过滤允许事件类型，或增加镜像校验"非批准类事件只能归属 CDE"。

**P2-2（漂移风险）：`ChinaDrugReferenceVersion` 的角色表硬编码于连接器，`create()` 不核对 source-policy-v1.yaml。** 公众号连接器会与策略逐域比对（漂移失败关闭），而 dxy/nmpa/cde 参考页连接器不查策略——若策略把 dxy 改为官方或 authoritative_secondary，连接器不会失败关闭。最小修复：`create()` 增加 `policy: SourcePolicy` 参数并校验 `dxy_drug_assistant` 的策略角色仍为二次参考。

**P3/非阻断说明**：未知 `source_system` 抛 KeyError 而非 ValueError（失败关闭但错误类型不友好，纯程序员面，本任务无 UI 不泄漏）；`approval_withdrawn` 正向路径与时间线重复事件拒绝无显式测试（探针验证行为正确，仅覆盖缺口）；`_walk_leaves` 静默跳过 None 值字段（不产生虚假观测，可接受）。

## Codex 仍需确认

1. 2 项 P2 是否接受为后续任务修复（均不影响本任务批准语义与"未公开"语义正确性，PASS 判定不依赖其修复）。
2. Task 2.6–2.7（摄取定位、事实/声明链、真实多路线编排）未在本轮验收范围，需在其完成后单独验收；届时连接器守卫标志（`is_peer_reviewed_publication`、`may_establish_official_regulatory_status`、`is_marketing_approval`、`result_disclosure_state`）的下游消费方必须继续遵守本验收确认的语义。
3. 本轮为离线形态/录制 fixture 验收；live 网络行为（验证码、页面结构变化）依 ADR 0008 应进入技术失败而非"未公开"，此分层已由回执模型保证，但真实 live 诊断未在本轮执行。
4. 我未对任何当前网页/监管/临床事实做最终判断，未做视觉/PPT 验收；最终验收权归 Codex。
