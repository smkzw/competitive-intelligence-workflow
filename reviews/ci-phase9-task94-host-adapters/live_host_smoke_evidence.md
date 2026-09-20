# Task 9.4 三宿主源码级真实冒烟证据

日期：2026-09-01

## 连通性

- Codex CLI `0.147.0`：返回 `CODEX_HOST_CONNECTED`。
- Hermes Agent `0.20.6`：会话 `20260901_054223_e1730a` 返回 `HERMES_HOST_CONNECTED`。
- OMP `18.0.11`：返回 `OMP_HOST_CONNECTED`。

三者均按各自真实 CLI 调用，未使用 fallback。

## 工作流实跑

三宿主分别启动真实 Agent 会话，完整读取公共 `skills/competitive-intelligence-workflow/SKILL.md`，在独立项目目录运行包校验与 `host-smoke-v1`。三者都得到关键证据阻断、退出码 4、零报告草稿；未把业务阻断误报为技术失败。

| 宿主 | 宿主会话/调用证据 | project_id | run_id | 结果 | 事件数 | reports 文件数 |
|---|---|---|---|---|---:|---:|
| Codex | Codex CLI JSON 事件流；首次 `uv` 缓存越界被沙箱拒绝，改用项目内隔离缓存后发现项目目录非空，再清空本次缓存并用 `UV_NO_CACHE=1` 成功重跑 | `project_f68ba57f9c2eaec784e3e9ad` | `run_c297ab9be64908af4d2a1424` | `evidence_blocked` | 11 | 0 |
| Hermes | `20260901_054436_559eb6` | `project_f68ba57f9c2eaec784e3e9ad` | `run_389cb5b7ec9e876a1ca0c4ee` | `evidence_blocked` | 11 | 0 |
| OMP | OMP print-mode 真实 Agent 调用 | `project_f68ba57f9c2eaec784e3e9ad` | `run_2bb1cc26308a7fffc850d91f` | `evidence_blocked` | 11 | 0 |

共同 `case_digest`：`294e8e958a8107bcbfd8bc351575b641d35232eab27242070f68638bb1bc8baf`。

## 独立文件摘要

- Codex manifest：`6ad2873e7f04d3b2399afe99b4d62a5eb199d7962cfe32413f07a9c1f05a4588`；events：`a71b5a3b6e354edd607420be80fc2688a5b59c54e450c16424c969e938965ade`。
- Hermes manifest：`6afba2f78469955581bded318fad20d26178ca5de5c1a06023894c6aa4c0fdfa`；events：`13aa3dd902cb5aec2d9dcd52adbca0713f1ae27d2bdf82a2a0263d8ed777741e`。
- OMP manifest：`cbaf8f314cd174aa74540c40138b84727fc86891eadd29ebb4e4d8c40a023ce4`；events：`c30e798040a24a4d668792204a33c309ac62e22bef155880a92801fb00e3d8d4`。

## 边界

这是当前源码 checkout 的真实宿主调用证据，不是 Task 9.5 最终候选包 fresh-install 验收。当前 HA09 自动测试使用显式替身验证回执结构与反例，明确输出 `real_host_pass=false`；只有 Task 9.5 从最终安装入口产生的三份 `path_resolved` 回执通过批次验证后，才可声明候选包的真实三宿主验收通过。
