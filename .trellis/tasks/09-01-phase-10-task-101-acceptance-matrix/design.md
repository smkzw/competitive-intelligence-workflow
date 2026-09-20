# Task 10.1 设计

## 目录结构

```text
fixtures/acceptance/
├── catalog.yaml
├── full-matrix-v1/
│   ├── inputs/
│   └── expected/
└── required-v12/
    └── <case-id>/
        ├── inputs/
        └── expected/
```

catalog 是唯一索引；目录存在不代表场景有效。每个输入文件由 catalog 的 SHA-256 绑定，case digest 由规范化场景元数据与输入摘要确定性派生。

## 场景合同

每个 case 至少包含：

- `id`、中文名称、case 族；
- `indication` 或明确 `not_applicable` 原因；
- IANA `timezone`、已物化 `data_cutoff`；
- `formats: [html]`；
- `execution_scope`：`full-matrix`、`recovery`、`legacy-cutover` 或 `conditional-extension`；
- `owner_task`；
- `inputs[]` 的相对路径、用途和 SHA-256；
- `expected`：预期终态、关键不变量和禁止结果；
- `verifiers[]`：精确 pytest node 或工具命令；
- `receipt.relative_path`、回执 Schema 和当前 owner 状态。

未到责任阶段的场景必须记为 `pending_future_owner`；只有 E1 条件扩展可以带合同摘要记 `not_applicable`。不得用 `not_applicable` 绕过恢复演练或旧根不存在证明。

## required-v12 case 族

保留批准计划列出的 18 个 case 族。涉及四格式的两项按 ADR 0013 收窄：

- `b-interaction-cross-format` 首版验证 B 基线/处置的图—表—证据抽屉、筛选和 URL 恢复，并将格式口径固定为站点式 HTML；原四格式扩展后续恢复。
- `multi-report-partial-delivery` 首版验证 A/B/C 共享证据但 Gate 和交付状态独立；一个报告阻断不影响其他已满足条件的 HTML，不模拟 PPTX 能力缺失。
- `kangzhe-and-large-project-runtime` 首版验证 Logo、导航、搜索、全页面、筛选、下钻和大项目浏览器表现，不验证 HTML-PPT presenter/逐字稿。

## 失败关闭

Schema、目录、输入摘要、case digest、时区/cutoff、owner/scope、verifier 或 receipt 任一不闭合，目录验证失败。额外 case 只有在 `requirements` 显式解释并有 owner 时允许。catalog 不能引用绝对路径、缓存、生产凭据或未脱敏材料。

## 用户可读矩阵

`docs/acceptance/matrix.md` 按“报告/场景—要证明什么—预期结果—责任阶段”呈现，不暴露程序日志标签。技术故障与证据不足分列；“未公开”不等于失败。
