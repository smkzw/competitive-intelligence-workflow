# Phase 2 独立科学数据验收

## 结论

FAIL。P0=0，P1=9，P2=0。

Phase 2 科学数据合同不可接受。即使选定的 56 项测试在现有 `.venv` 中通过，仍存在可实际伪造路线完成、宇宙闭合、事实重开和声明链的跨层漏洞。

这不是对真实全量竞品调研质量、Phase 3 或最终报告的验收；这些内容尚未验收。

## 运行与来源核对证据

| 检查 | 实际结果 |
|---|---|
| 指定 Phase 2 测试 | `uv run` 因 `/Users/smkzw/.cache/uv` 权限失败；`.venv/bin/pytest -s ... -q`：56 passed |
| 全量测试 | `uv run` 同样失败；`.venv`：145 passed，6 failed，32 errors |
| Ruff | `uv run` 失败；`.venv/bin/ruff check src tests` 通过 |
| Mypy | `uv run` 失败；`.venv/bin/mypy --strict src` 因只读环境 SQLite cache `unable to open database file` 内部失败，未形成通过证据 |
| Package verify | fallback 通过，但输出 `stage=phase-0-task-0.4`，不能证明 Phase 2 退出 |
| Git | `git diff --check` 通过；工作区原有修改/新增文件未触碰 |

全量测试失败主要包括 Playwright 临时目录权限、`uv lock --check` 权限和 32 项临时文件/数据库初始化错误；它们不能判为科学不一致，但已经足以使 PASS 条件不成立。

官方 API [`https://clinicaltrials.gov/api/v2/studies/NCT02912468`](https://clinicaltrials.gov/api/v2/studies/NCT02912468) 未能实时访问：

- 代理路径连接 `127.0.0.1:7897` 被拒绝；
- 绕过代理后 `clinicaltrials.gov` DNS 解析失败。

因此不把 API 不可访问判为科学不一致。官方研究页可作为元数据旁证：[ClinicalTrials.gov NCT02912468](https://clinicaltrials.gov/study/NCT02912468)。

## 宇宙与来源路线攻击

基础规则本身通过：

- 传统糠酸莫米松被排除；
- 含度普利尤单抗的创新治疗方案可纳入；
- `review_pending` 正常情况下阻止宇宙闭合；
- 当前核心路径未发现 Top-N 截断。

但跨层攻击成功：

```text
CE1 route_completed + network_error                  => True
CE2 两个无回执替代策略即可满足 alternatives        => True
CE3 两个无执行证据的饱和轮次即可宣称 saturated       => True
CE8 任意 missing-fragment 也可关闭 universe          => True
```

关键问题：

- `[receipts.py:64](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/sources/receipts.py:64>)` 的 `route_completed` 未要求回执结果为 `content_acquired`，也未要求所有政策必需来源单元均被选中。
- `[retries.py:208](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/sources/retries.py:208>)` 的替代路径只验证策略对象，没有执行回执、来源快照或实际内容绑定。
- `[retries.py:124](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/sources/retries.py:124>)` 的双轮饱和只比较策略签名和 `is_saturated`，空信息增益也可通过。
- 五个指定公众号及四个批准声明域已在 source policy 中覆盖，且“公众号不标为同行评议”这一约束存在；但 `[authoritative_wechat.py:50](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/sources/connectors/authoritative_wechat.py:50>)` 允许缺失产品、试验和事件身份，也未强制真实账号、域名和内容快照。

因此，策略矩阵覆盖不等于来源路线已经不可伪造。

## 日期、定位与事实声明链攻击

已发现以下可绕过：

- `[china_registries.py:194](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/sources/connectors/china_registries.py:194>)` 的中国试验版本没有 `first_disclosed_at` 及日期精度，无法满足按首次披露日期的历史截止。
- planner 使用日期时间比较，但没有强制处理“只有自然日”的不确定边界；同日截止可能误纳或误排。
- `[locators.py:50](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/ingestion/locators.py:50>)` 和 Web 快照模型只校验摘要格式，直接构造伪造摘要仍可成功重开；`.create()` 的安全路径不能保护直接模型构造。
- `[facts.py:67](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/domain/facts.py:67>)` 和 `[claims.py:64](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/domain/claims.py:64>)` 允许通过任意 fragment/fact ID 构造事实与接受声明，绕过实际重开。
- `[resolution.py:194](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/capabilities/resolution.py:194>)` 的确定性差异声明未比较 `entity_id` 和 `arm_id`，已实测可生成跨试验、跨组差异声明。
- 冲突保留测试通过，但“先到先得”虽未在该测试中出现，声明链接仍可使用伪造的已接受事实 ID，因此冲突保护没有形成完整注册表边界。

## 录制官方 fixture 攻击

fixture SHA-256 为：

`f497d57cb1d4dacf9f52ce015d12ff33d7c9dc43b0b788d3792d03e4ca38b1b1`

内部字段核对成立：

- NCT：`NCT02912468`
- 实际样本量：276
- 试验组：度普利尤单抗 300 mg + 糠酸莫米松
- 对照组：安慰剂 + 糠酸莫米松
- 主要结果：`-0.45`、`-1.34`
- 结果首次发布：2019-07-25
- PMID：31543428
- 糠酸莫米松标为 `traditional_corticosteroid`，仅作背景治疗

但这只能证明录制 JSON 的内部一致性，不能替代本次失败的官方 API 实时重建。现有链路测试可构造一条 happy-path record→fragment→fact→claim，但没有证明：

- 两个主要结果值均被正式断言；
- 回执、适用性、缺口、完成状态绑定同一个来源版本注册表；
- 每个 fragment 真实存在且已重开；
- PMID 已完成独立来源角色核验。

## 缺陷

1. P1：技术失败回执可被标记为 `route_completed`。
2. P1：两个无来源回执的策略单元可伪造替代路线完成。
3. P1：无执行证据、无信息增益的两个轮次可伪造饱和。
4. P1：公众号文章可缺失产品/试验/事件身份，且快照来源未被强制验证。
5. P1：差异声明可跨实体、跨试验、跨 arm。
6. P1：事实和声明的直接模型构造可绕过实际重开和事实注册表。
7. P1：伪造 snapshot digest 仍可被 locator 重开。
8. P1：中国注册数据缺少首次披露日期及自然日精度，历史 cutoff 不可证明。
9. P1：`close_competitor_universe()` 只检查 `review_pending`，任意未注册 evidence ID 也可关闭宇宙。

## Phase 3 前必须完成的动作

1. 强制路线完成绑定所有政策必需来源单元、真实回执和正确结果类别；技术失败不得进入成功状态。
2. 将替代策略和饱和轮次绑定实际 attempt、receipt、snapshot、gap 和信息增益，并增加伪造反例测试。
3. 强制公众号的账号、域名、文章内容、产品/试验/事件身份和快照摘要全部可验证。
4. 建立 fragment/fact/claim 注册表边界；禁止直接构造伪造 ID 绕过重开。
5. 差异声明必须校验实体、试验、arm、群体、时间点和上下文一致性。
6. 为中国注册来源增加首次披露日期、精度和同日 cutoff 边界处理。
7. 扩展 NCT02912468 fixture 验收，正式断言样本量、组别、`-0.45/-1.34`、2019-07-25、PMID 和背景治疗排除。
8. 在具备可写 uv/temp/SQLite 环境后重新运行全部六类正式命令；必须得到全量测试、严格 mypy、package verify 的真实通过证据，且 package 状态应反映 Phase 2。