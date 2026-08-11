FAIL

P0

- 文件：`tools/design_contract_validation.py:152-160`；测试 `tests/contract/test_design_acceptance_contracts.py:147-154,261-265`
- 问题：validator 信任外部传入的 `manifest_sha256`，未重算被验收 manifest 的实际摘要。
- 复现：将 manifest 的 `report_snapshot_sha256` 改为 `SHA_E`，保留 verdict 和参数摘要 `SHA_A`，仍返回 `accepted`。
- 最小修复：由 validator 基于规范化原始 manifest 字节自行计算摘要，并增加“任意 manifest 字段变异即失败”的测试。

P0

- 文件：`design-run-manifest.schema.json:70-75`；`tools/design_contract_validation.py:129-139`
- 问题：`pre_run_state: null` 未区分“运行前不存在”与“未记录”；只要改写后的 mtime 晚于 run 起始时间即可通过。
- 复现：现有有效 fixture 的 `pre_run_state` 已为 `null`；将旧产物的 mtime 改为运行后时间，validator 仍接受。
- 最小修复：用显式 `exists: false` 表示运行前不存在，未知状态拒绝；补充 null + mtime 改写负例。

P1

- 文件：`design-source-pack.schema.json:136-149`；`tools/design_contract_validation.py:59-74`
- 问题：claim 只校验引用了存在的 token，不校验声明值与 token 的原始值、单位和分母一致。
- 复现：将 claim 及所有 occurrence 改为“999”，保留 token 原值 `-1.2`，仍被接受；将事实 token 替换为结构合法的 `page_number` 也被接受。
- 最小修复：受众定量 claim 仅允许引用 `audience_fact`，并机械绑定规范化值、单位、分母；增加上述两类变异测试。

P1

- 文件：`design-source-pack.schema.json:164-177`；`tools/design_contract_validation.py:76-99`
- 问题：notes 只校验 `claim_id` 和 occurrence 元数据，未校验 notes 文本本身与同一 claim/value 一致。
- 复现：将现有 note 文本替换为与页面结论无关且含另一数值的文本，validator 仍接受。
- 最小修复：为 notes 增加受控抽取的规范化 claim/value，并与 speaker-notes occurrence 及受众表面值逐项比较；补充文本脱链负例。