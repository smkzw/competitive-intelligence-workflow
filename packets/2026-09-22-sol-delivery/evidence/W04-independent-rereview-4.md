verdict: PASS

# W04 第四次 FAIL 返修后第五次独立只读复审

## model / effort

- 请求运行时：`gpt-5.6-sol:medium`。
- 核验结果：**UNVERIFIED**。本会话没有可核验的 runtime model/effort 回执；未猜测、未静默替换。
- 边界：全新上下文、单一只读复审者；只接触英文工程，唯一持久写入为本报告；未联网、未派子代理、未进入 W05，未修改产品、测试、既有证据或 STATUS，未执行 Git 破坏动作。

## 结论

第四次 FAIL 的 P1-01 与 P2-01 已关闭，且此前完整科学身份 binding、immutable generation selector、three-way、统计对象边界和 loopback/API 安全未见回归。当前可接受 **W04 工程风险闭包 PASS**。

该 PASS 只接受 W04：typed 用户事实修订、来源分层、原消费者重建、证据绑定、原子 current、故障恢复及相关安全边界。它不代表全 gate、8 适应症 × A/B/C 的 24 门户、W05 四视口、三宿主、全量真实生产资料、正式科学/医学/产品/用户或 RC 接受。

## P0–P3

| 等级 | 数量 | 结论 |
|---|---:|---|
| P0 | 0 | 未发现。 |
| P1 | 0 | 第四次 P1-01 的用户值/来源原文污染已关闭；未发现新的阻断性生产风险。 |
| P2 | 0 | 第四次 P2-01 的 builder input 证据缺口已关闭；正常及四类指定篡改均按预期。 |
| P3 | 1 | A 原表格的“依据与说明”在 base 行无 `source_text/source_field_path` 时渲染字面量 `None`（`templates/a/safety.html.j2:11`）；A 数据依据抽屉已正确显示修订状态、当前/原值和结构化 locator，且未把用户值归因成来源原文，因此不阻断 W04。建议 W05/后续小修将空值显示为“原文未提供/定位见证据链”。 |

补充代码观察：`tools/verify_w04_v6_evidence.py:100-101` 在 `resolve()` 后检查 `is_symlink()`，不能识别“仍指向工程内”的最终 symlink；但 resolved path 越界会被拒绝，且当前三份输入均为普通文件，逐字节 SHA-256、manifest 唯一成员和 binding 重算仍会拒绝任何不同字节。该实现细节不形成当前冻结证据的可利用完整性缺口，建议日后改为同时检查未 resolve 的路径各组件以与 manifest 的“no symlink”措辞完全一致。

## 第四次 FAIL 缺陷 closure

| 缺陷 | 判定 | 独立复核结论 |
|---|---|---|
| P1-01：用户修订覆盖 `source_text/original_text/locator`，并被展示为登记原文 | **关闭** | `UserEditDisclosure` 独立承载 `review_state=user_modified`、用户 provenance、当前值和原值；A/B/C projection 只改当前领域值及显示叙事，不改 base 来源字段。冻结 DB 中 accepted 与 user_modified 版本继续引用同一 fragment/source version/locator。C `source_text` 仍为原英文 EASI ≥16，locator 仍为 `protocolSection.eligibilityModule.eligibilityCriteria`；B 的 `original_definition`/来源定位未被用户 narrative 覆盖；A base source 字段原为 null，修订后仍为 null，未伪造来源原文。 |
| P1-01：原消费者/来源抽屉未披露用户修订状态和来源分层 | **关闭** | A 原热图显示 67%，抽屉显示“用户修订，未独立复核”、当前 67.0%、原值 66.2% 和结构化 locator；B 原图/展开表显示 30、24/80 及状态，抽屉显示原值 54.8% (34/62)、Table 3 locator 和原 source version；C 原表显示 EASI ≤18.0 分及状态，抽屉保留原值 ≥16 分、原英文原文和原 locator。三页冻结 DOM assertion 全为 true，console 合计 0 error/0 warning。 |
| P2-01：三份 builder input 未纳入 manifest，verifier 可假阴性 | **关闭** | v6 manifest 将 A/B/C 三份 `state/user-fact-builder-inputs/report-*-data.json` 作为独立 artifact；每个 delivery 校验 project-relative 路径边界、delivery SHA、实际 bytes、唯一 manifest 成员、receipt consumer binding 与 `original_row_sha256` 重算。正常验证 0 error；artifact、target、nontarget、arbitrary-byte 四类内存篡改分别产生 1/3/2/2 个错误。额外不落盘反例确认重复 manifest 成员、`../` 逃逸、绝对路径均失败关闭。 |

## W04 acceptance

| 验收项 | 判定 | 本次证据与边界 |
|---|---|---|
| 1. typed target、expected revision/request id、完整消费者科学身份、pre-staging fail closed | PASS | 完整 binding 含 report/collection/row、产品/药物、试验/登记、group/arm/cohort/period、endpoint/event、统计形式、对象、单位、source version/pointer、original-row digest；相关 stale/mismatch/cross-report 反例在 118 项批次中通过。 |
| 2. append-only 事实版本、旧 accepted/fragment 保留、user_modified、undo 追加 | PASS | 只读 DB 显示每个 base accepted 与 user_modified 共存，并继续引用同一原 fragment；未修改旧来源字节或旧接受状态。 |
| 3. 用户值 / review_state / provenance 与不可变来源层分离 | PASS | A/B/C `user_edits` 明确包含状态、request/revision、basis/saved_by/saved_at、fragment/source/locator、当前值与原值；C/B evidence view 的 original text/definition、locator、source version 保持 base。 |
| 4. 原 A/B/C builder、图/表/文字/索引/来源消费者真实更新 | PASS | 无 `user_fact_revision` overlay；A/B/C 原 builder 输出及 receipt 指向具体原页面和领域行。A/B/C report revision 为 1/2/3，三次事实分别只重建 A、B、C。 |
| 5. impact receipt 与完整 binding/original digest | PASS | receipt binding 与冻结 builder bytes 独立重算一致；transaction impact binding 使用同一 fact version、binding identity 和 original-row digest。 |
| 6. immutable generation + SQLite FULL committed selector、失败恢复与旁路 | PASS（本范围） | 稳定 `reports/current.json` descriptor 指向 SQLite selector；选中 generation 的文件名/字节 SHA 一致。generation/fsync/DB/event/journal/双故障和精确重试相关反例均通过；未发现生产直接读取旧 revision pointer 的旁路。 |
| 7. three-way refresh | PASS | 字段并集、base/user/source 三值、presence、lineage、conflict/converged/withdrawn 和 resolution options 持续通过并持久化；本次 refresh 对 threshold operator/value 明确保留冲突。 |
| 8. 统计对象边界 | PASS | `n<=N` 与自动重算仅适用于 `crude_rate + participants`；events count、person-time、adjusted rate、LS mean 与同数字无关事实未回归。 |
| 9. loopback/API 安全 | PASS（本范围） | 相关回归覆盖 Host/Origin/session/CSRF/JSON/64 KiB/path/symlink；`/api/import` 仍为 404，multipart save 拒绝。未做 DNS rebinding 专项渗透。 |
| 10. v6 manifest/browser/截图闭包 | PASS（W04范围） | 23 source、36 artifact、3 builder input 正常复算；DOM/console 与三张非白截图均被 manifest 绑定。长页、宽屏利用率和纵向密度属于 W05 未验，不用于否定 W04。 |

## 决定性命令与结果

### 1. W04 相关回归批

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider \
  tests/integration/test_w04_user_fact_edit.py \
  tests/integration/test_correction_service.py \
  tests/integration/test_correction_flow.py \
  tests/integration/test_incremental_refresh.py \
  tests/integration/test_latest_delivery.py \
  tests/unit/test_render_transaction.py \
  tests/integration/test_sqlite_migrations.py -q --tb=short

118 passed in 42.74s
```

### 2. v6 正常与四类指定 tamper

```text
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  tools/verify_w04_v6_evidence.py \
  --repo '/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow' \
  --manifest '/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/packets/2026-09-22-sol-delivery/evidence/W04-remediation-real-portal-v6-final-3/evidence-manifest.json'
```

正常：`checked_sources=23; checked_artifacts=36; checked_builder_inputs=3; error_count=0`。

分别追加 `--tamper-check artifact|builder-target|builder-nontarget|builder-byte`：

```text
artifact:          error_count=1; tamper_rejected=true
builder-target:    error_count=3; tamper_rejected=true
builder-nontarget: error_count=2; tamper_rejected=true
builder-byte:      error_count=2; tamper_rejected=true
```

### 3. 额外不落盘内存篡改

直接调用 `verify_builder_inputs()`，仅修改内存对象：

```text
duplicate_manifest_member_rejected=True
  builder input absent or duplicated in manifest: A/...
path_escape_rejected=True
  builder input path escapes project: A
absolute_path_rejected=True
  builder input path invalid: A
```

### 4. 来源分层与冻结状态

- A：当前 67.0%，原值 66.2%；accepted/user_modified 共用 `fragment-a-safety` 和同一 `report-a-row:*` source version。
- B：当前 30% (24/80)，原值 54.8% (34/62)；accepted/user_modified 共用 `fragment-count`、原 Table 3 locator 和 `nct04558918-safety-report-v1`。
- C：当前 `<=18 分`；原值 `≥16 分`；渲染后 `source_text` 仍为 `Eczema Area and Severity Index (EASI) score ≥16 at the baseline visit`，原 source version 与原 ClinicalTrials.gov locator 未变。
- selector：revision 3，selected generation `8c84b88e89c94f422c87b46ec4a1a292a322843c04a97a6bc3e71357b28b592c`。

## hash / identity

```text
evidence-manifest.json              f2657c431875098860544bc8c4bbed0b2063c8dc80515f10b67e89c9c2c7e814
dirty_source_digest                 96cbcf9b67800c684f7631af1ab0c9daea2d9be7cf3923d17397677df1536ded
tools/build_w04_v6_evidence.py      72b5bc66963bde08f094c8bc3ac1628144855a449c5860c1020f3cca97f2d241
tools/verify_w04_v6_evidence.py     27a931be03f4500164e6c1bb196395b2bdb188f60aa70a1ecb6a9760c5869c2c
active_fact_projection.py           348c74d0ea78036f19943475d5bb23547a766e341a719609be02378053dc329f
report_a.py                         c7555e52f285f3a32eac0d6d3d00d1a81c50664191c391219f0b50c166073e6d
report_b.py                         5d2f450ebc39e11b2569b0549bcb81a79e3c274fb5e20e7fb70dbb6fa5e9c052
report_c.py                         3690289bfe1f828f06571b9d69b2a84b2bb1e9150cdb00dcf88c5eb0169cc5ae
test_w04_user_fact_edit.py          66ec3e89cddacaa17492d5ca1eec98025db0231466023324dd8dc8925b628ded
```

四份既有 FAIL 原文 hash 仍为：

```text
W04-independent-review.md           ae71fd6ae67e4d3e12045a978a2cf0729ad5578bdefdc2671e1740f0ffd6eecd
W04-independent-rereview.md         37c7cc732d3b8b67196972e798eca7037b4496a89dba8f7dd9beb0bbcc6b2e90
W04-independent-rereview-2.md       eb846e42233001b3924b130b8ce691e1274484ecebc0aa7a8173929396dbeb98
W04-independent-rereview-3.md       fdc4e7f124452ce5246ba764528fd07c1be0f4cf0940a078ab3d442f0355bbc2
```

## 未验证范围

- runtime model/effort：**UNVERIFIED**。
- 全 gate。
- 8 适应症 × A/B/C 的 24 门户。
- W05 四视口：1440×900、1024×1366、390×844、320×568；宽屏利用率、纵向/窄屏密度、首屏信息密度。三张当前长截图只用于 W04 来源/状态与非白图核验，不作 W05 视觉接受。
- 三宿主真实安装、入口、失败恢复和语义一致。
- 全量真实生产资料 A/B/C 重建、W05/W06/W07 完整集成。
- DNS rebinding 专项渗透、正式科学/医学/产品/用户和 RC 接受。

本 PASS 不进入 W05，也不改变其他工作包或全产品状态。
