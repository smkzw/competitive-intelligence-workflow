# Task 10.5 完成检查点（2026-09-02）

## 结论

Task 10.5 已完成并封存。精准切换工具、required-v12 owner-stage 发布回执 schema 与聚合验证器通过确定性检查、独立会商和同任务治理审计。P0=0、P1=0、P2=0。

本任务没有向工具提供任何真实旧工程、旧全局 Skill、归档、缓存、备份、启动器或消费者路径；没有读取其内容，也没有执行真实 inventory、validate、apply 或 absence-check。全部写入性验证仅发生在 pytest `tmp_path` 临时根。真实迁移和删除仍未获授权。

## 冻结产物

- `tools/legacy_cutover.py` — `fc6aad591723b61c4d9ffdae3ce216321a9aea1bf86b396beb735c8f6f0da49f`
- `tools/verify_release_receipts.py` — `4cf5e52e28b5697bf124f226bf7a7618bd6a7c17ef8941fdbbe61b81e83c4695`
- `schemas/release-case-receipt.schema.json` — `327e996a932ac01a71e62a66281177921b185018b4fe40ed03b9e325ddb7ecaa`
- `tests/migration/test_legacy_cutover.py` — `ec4a750cbf9c3b34f029d5362cda392138fd6915adae889328da064571667cf8`
- `tests/acceptance/test_required_receipt_closure.py` — `407260672942ea39939c31675a18b5a01b795787004706ec5f9c6dccadf330fb`
- `docs/acceptance/legacy-cutover-tooling.md` — `8be3faf7df6a13ac7a4a9c66aa570c10e4699f60eec924a40c07c2bf28ef1ad6`

两个 Python 工具是仓库内治理工具，不进入可安装运行时 bundle；发布回执 schema 是可移植合同，已进入 package manifest。

## 决定性验证

- 聚焦测试：26 passed。
- 扩展迁移、required-v12、全矩阵、fixture catalog、旧负回归、package manifest 与 bundle packaging：166 passed。
- Ruff、mypy：通过。
- `tools/check_no_legacy_refs.py --root .`：`LEGACY_REF_OK`。
- 独立会商：同一 CodeBuddy session 两轮，最终 P0=0、P1=0、P2=0，无 fallback。
- conference review-gate：通过，无 warning。
- `audit-execution --require-conference`：通过，无 warning/error。

## 后续强制依赖与安全边界

1. Task 10.6 必须实现并实际生成符合冻结消费者合同的 `recovery-package-v1` 回执：`receipt_kind/status/recovery_package_sha256/issued_at`（代码字段名以 schema/测试为准），拒绝未知字段，并完成真实恢复演练后才可进入预授权验证。
2. Task 10.7 必须建立经过人工审阅的完整多根 registry，覆盖旧工程之外的旧全局 Skill、归档副本、启动器和消费者引用；单根 `--legacy-root` metadata-only 快捷清单不能冒充全域授权。只有向用户展示完整清单和摘要后，才能请求精确授权。
3. Task 10.8 的 apply/absence-check 仍属于后续受控动作。本检查点不授予删除、替换、卸载或清理任何真实数据的权限。
4. 下一安全动作：启动 Task 10.6，仅构建最终 RC、全量验收根和恢复包；继续保持真实旧根零触碰。
