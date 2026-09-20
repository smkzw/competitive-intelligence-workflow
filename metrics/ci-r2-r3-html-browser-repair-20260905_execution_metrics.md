# Execution Metrics: ci-r2-r3-html-browser-repair-20260905

| Role | Provider | Model | Status | Duration | Tools | Result |
|---|---|---|---|---:|---:|---|
| `worker_01` | `zcode` | `GLM-5.3-Flash` | completed | 37m 11s | 94 | A 合同与浏览器修复，选择性采纳 |
| `worker_02` | `zcode` | `GLM-5.3-Flash` | completed | 90m 13s | 163 | B 与共享图表修复，选择性采纳并补一项遗漏 |
| `worker_03` | `zcode` | `GLM-5.3-Flash` | completed | 78m 08s | 216 | C 与共享抽屉修复，选择性采纳 |

三路均为单次长等待完成，无固定轮询、无重派、无 fallback。时长与工具调用数来自 runner stdout 的结构化运行记录。
