# Phase 2 独立科学数据验收（Follow-up）

## 结论

FAIL。P0=0，P1=8，P2=0。

父会话提供的 59/186 全量机械证据、Ruff、strict mypy、package verify 及官方 API 结果与当前实现不冲突；但本次独立反例仍发现可执行的 Phase 2 科学数据合同绕过，因此不能放行。

## 运行与当前 diff 核对

指定命令因隔离环境无可写临时目录，在 pytest 捕获阶段退出，未收集测试：

```text
FileNotFoundError: No usable temporary directory found
```

使用同一测试集合、禁用 cache 并增加 `-s` 后，测试体实际结果：

```text
38 passed in 0.15s
```

`git diff --check` 通过。未修改任何文件，也未进行安全测试。

录制 fixture 的新增测试已断言 276、两组背景糠酸莫米松、`-0.45/-1.34`、133/143、2019-07-25、PMID 31543428，以及两个身份片段和来源—事实—声明链。父会话提供的官方 API 实时结果与这些断言一致。

## CE1–CE8 复核

| 反例 | 当前结果 |
|---|---|
| CE1 技术失败标记 `route_completed` | 已闭合，`network_error` 被拒绝 |
| CE1b 单次 `not_found` 后直接 `route_completed` | 仍可通过 |
| CE1c `route_not_applicable` 只提交一个单元、遗漏另一个必查单元 | 仍可通过 |
| CE1d `route_access_blocked` 只提交一个单元、遗漏另一个必查单元 | 仍可通过 |
| CE2 无恢复回执 | 已闭合，模型拒绝 |
| CE2b 仅用伪造的 `RecoveredSourceVersion(id,digest)` 证明取得内容 | 仍可通过 |
| CE3 无回执的饱和轮次 | 已闭合 |
| CE3b 两轮 `network_error`、无信息增益即可宣称饱和 | 仍可通过，输出 `True` |
| CE4 缺失公众号身份、非微信链接、定位不在正文 | 已闭合 |
| CE4b `locator.url` 指向其他网址、定位只取正文一个字符 | 仍可通过 |
| CE5 Registry/Web/PDF 伪造摘要 | 已闭合，三类快照均拒绝 |
| CE6 跨试验差异声明 | 已闭合，拒绝 |
| CE6b 工厂引用未注册事实 | 已闭合，拒绝 |
| CE6c 直接构造 `ClaimVersion` 引用未注册事实 | 仍可通过 |
| CE8 空的已重开片段集合 | 已闭合 |
| CE8b 调用方自行提供同名 fake fragment ID，或边界审查回执使用未注册片段 | 仍可通过 |

## 新发现缺陷

1. P1：非成功路线状态没有覆盖全部政策必查单元，也没有绑定恢复穷尽条件。
   最小复现：一个 `not_found` 回执即可 `route_completed`；`route_not_applicable` 或 `route_access_blocked` 只提交 `s1`，同时存在未处理的必查 `s2`，仍可完成。`RouteProgress` 的 `attempts` 也没有与审计回执绑定。
   位置：[receipts.py:85](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/sources/receipts.py:85>)、[planner.py:44](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/sources/planner.py:44>)。

2. P1：技术失败回执可以组成“双轮饱和”。
   两个不同策略、两个 `network_error` 回执、空 `InformationGain`，`RecoveryHistory.can_declare_information_saturated` 返回 `True`。
   位置：[retries.py:174](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/sources/retries.py:174>)、[retries.py:185](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/sources/retries.py:185>)。

3. P1：恢复/替代路径只绑定摘要型 `RecoveredSourceVersion`，不绑定真实 `SourceVersionRecord` 或已登记正文。
   最小复现：构造两个 `content_acquired` 回执，分别指向 `fake-version-1/a*64` 和 `fake-version-2/b*64`，再提供同值的 `RecoveredSourceVersion`，`minimum_distinct_alternatives_met` 返回 `True`。
   位置：[retries.py:95](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/sources/retries.py:95>)、[retries.py:273](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/sources/retries.py:273>)。

4. P1：公众号正文与精确定位的来源链接未绑定。
   最小复现：`source_url="https://mp.weixin.qq.com/s/real"`，但 `locator.url="https://evil.invalid"`、`locator.paragraph="正"`，模型仍接受。
   位置：[authoritative_wechat.py:120](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/sources/connectors/authoritative_wechat.py:120>)。

5. P1：直接构造 `ClaimVersion` 仍可引用未注册事实。
   `create_direct_evidence_claim()` 会通过注册表拒绝，但直接 `ClaimVersion.model_validate()` 使用 `fact_version_id="unregistered-fact"` 可接受；注册表约束没有成为声明模型本身的不可绕过边界。
   位置：[resolution.py:123](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/capabilities/resolution.py:123>)。

6. P1：宇宙闭合只验证调用方提供的字符串 ID，不验证真实注册表；边界审查回执的证据 ID也未检查。
   最小复现：`verified_fragment_ids=frozenset({"fake-fragment"})` 配合同名 `ComponentEligibility` 即可闭合；边界审查回执使用 `unregistered-review-fragment` 也不阻止闭合。
   位置：[ontology_universe.py:272](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/capabilities/ontology_universe.py:272>)、[identity.py:106](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/ingestion/identity.py:106>)。

7. P1：中国注册/监管记录模型仍可接受非官方 URL，且临床试验版本没有正文摘要字段。
   最小复现：`ChinaDrugTrialVersion(source_url="https://evil.invalid", raw_record_json='{"forged":true}')` 可接受；`ChinaRegulatoryRecordVersion` 同样接受非官方 URL。首次披露日期字段本身已补齐，但来源真实性绑定仍不足。
   位置：[china_registries.py:58](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/sources/connectors/china_registries.py:58>)、[china_registries.py:194](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/sources/connectors/china_registries.py:194>)。

8. P1：运行时 `SourceVersionRecord` 未强制内容寻址路径与摘要一致。
   最小复现：`content_sha256="a"*64`、`content_relative_path="not-a-content-addressed-path"` 可直接构造并进入回执绑定；JSON Schema 虽有路径正则，但 Pydantic 运行时边界未执行。
   位置：[evidence.py:133](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/domain/evidence.py:133>)、[schemas/source-version.schema.json](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/schemas/source-version.schema.json)。

## 已确认闭合项

- 技术失败不得伪装为 `route_completed`。
- 无恢复回执不得创建替代路径或恢复轮次。
- Registry/Web/PDF 快照直接构造时会校验正文摘要。
- 首次披露 `calendar_day` 在截止日内会保守阻断。
- 跨试验、同组别或指标不一致的差异声明会被拒绝。
- 通过正规工厂生成声明时，未注册事实会被拒绝。
- 传统背景治疗与创新药身份片段在 fixture 中均可重开，糠酸莫米松未进入竞品成员。

## Phase 3 前必须完成的动作

1. 将所有路线终态统一绑定完整政策单元、实际恢复审计和同一实体/缺口/声明域。
2. 饱和轮次必须排除技术失败，且绑定真实来源版本注册表和内容结果。
3. 公众号定位必须强制校验 `locator.url == source_url`、账号角色和完整定位结构。
4. 禁止直接构造未经过 lineage registry 的声明进入下游。
5. 宇宙和身份索引必须接收真实证据注册表，而不是可调用方伪造的字符串集合。
6. 中国来源必须校验官方域名、正文摘要和 SourceVersionRecord 一致性。
7. 将 `SourceVersionRecord` 的内容寻址路径规则同步到运行时模型。
8. 补充上述 8 个反例的回归测试；在这些反例全部失败后，再重新进行 Phase 2 退出验收。
