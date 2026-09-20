# Execution Metrics: ci-r24-gatespec-blocker-closure-20260905

| Role | Provider | Model | Status | Duration | Tools | Result |
|---|---|---|---|---:|---:|---|
| `worker_01` | `cursor` | `default` | completed | 211.874 s | 418 | GateSpec/逐对象绕过审计完成 |
| `worker_02` | `cursor` | `default` | completed | 247.919 s | 124 | 恢复/信息增益/遗漏复核审计完成 |
| `worker_03` | `cursor` | `default` | completed | 183.998 s | 128 | blocker/no-draft 产品链审计完成 |

三个 runner receipt 均为 v2、return code 0、单轮自然结束、无 fallback；输出 SHA-256 分别为
`b439f9f42c61d49bab743cc3e971f79eced0e73c262a67d435d0be7d22d1e2f7`、
`13bc4820d98c6db836d5944e942c226c136cd7215b615bb3cc5307dda4757695`、
`0d4ca212bd592598cd90b639af494ef69bfb7f7661f76e05d8a24238926e22c5`。
