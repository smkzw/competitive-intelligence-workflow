PASS

- 指定测试：`32 passed`。
- Manifest 使用规范化 UTF-8 JSON 摘要；修改任意 manifest 字段并复用旧 verdict 会被拒绝。
- `pre_run_state` 仅允许显式 `exists:false` 或完整既有文件身份；`null`、mtime 改写及相同内容均失败。
- Claim 仅可引用 `audience_fact`，且值、单位、分母必须匹配；`999` 脱链和页码伪装均失败。
- Notes 要求受控 claim span、原文存在、规范值一致；追加未绑定 `999` 会失败。

本次仅验收合同、Schema 与 validator，未生成或接受任何报告实产物。