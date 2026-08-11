# Codex Conference Review: ci_phase0_offline_assets_20260811

Date: 2026-08-11

## Verdict

**PASS** — 仅接受 Task 0.3 的项目康哲合同、Logo、ECharts 6.1.0 和中文 HTML-PPT 离线运行基础设施。P0=0，P1=0；不接受任何 A/B/C 报告实产物，也不代表 Phase 0 完成。

## Boundary Compliance

- 两名参与者均在项目根只读检查，不访问网络、不修改项目文件、不读取对方输出。
- 本会商按 guard 声明直接使用 Pi 与 Grok Build；未通过 Hermes 伪装或转发 Grok，会话身份与 runner 记录一致。
- 生产者没有为自己关闭任务；两名参与者先后独立找到同一 P1，修复后均在原 session 做负向复验并给出 PASS。
- 所有临时变异目录由参与者自行删除；Codex 只清理自己创建的 `/tmp/ci-*` 目录。
- 会商指标和最终/有效参与者报告保留；4.4 MB 原始 runner stdout、两份被取消的空壳输出和四份未使用模板已移入废纸篓，不进入项目提交。
- 没有启动安全专项、Task 0.4 或报告页面实现。

## Participant Outputs Reviewed

- `general_pi_qwen38`：日间路由实际为 `Pi/cms-smk/cms-model:high`，session `019fef9a-0c91-7000-8f29-90b7d9ccfaf1`。首轮发现 Logo manifest 来源路径悬空；同会话复验 4 类变异后 PASS。最终复验 SHA-256 `cd12b0bde76d8a175f48698501780f4046b530a9568a2ca7c2b4af25ec8e3801`。
- `general_grok45`：`Grok Build/grok-4.5`，session `4dcf868f-b0f3-4b95-bb2d-a46630ca1154`。前两次 `plan` 权限模式在首个工具动作前返回 `cancelled`，不计验收；同 session 改为只读命令自动批准后完成实测并发现相同 P1，修复后负向复验 PASS。最终复验 SHA-256 `98ac9320f4efdcbdaee3a0b5f45324c4202adc4cbe8a3bb1f3c42b68586773a8`。

## Conference Panel Review

两名参与者独立重算六个资产摘要、核对许可和 manifest，并分别运行真实浏览器与临时假绿变异。共同阻断项为 `assets/brand/manifest.json` 的 `source` 指向不存在的 `contracts/kangzhe/brand/logo/cms-logo.svg`，同时合同没有检查来源可达性。

Codex 先写 RED 合同，确认 exact node 因 `source.is_file()` 失败，再把 `source` 修正为 `contracts/kangzhe/design_specs/assets/logo_bot.svg`，增加 9,542 字节、官网地址和 2026-08-11 核验日期，并锁定来源文件存在、摘要相同、字节完全相同。两名参与者随后各自在临时副本破坏路径/字节/字段，均被新合同拒绝；原 P1 关闭。

## Main-Venue Codex Review

- 重算 Logo、ECharts bundle/许可、HTML-PPT runtime/许可摘要，与 manifest 一致。
- `node --check assets/html-ppt/runtime.js` 通过。
- Ruff 与 mypy 覆盖校验器和新增测试，均通过。
- 设计合同+离线资产+真实浏览器专项：43 passed。
- 仓内全量：49 passed。
- Chromium 与 WebKit 均在 `file://` 下验证翻页、页码、hash 深链、逐字稿、演讲者视图、计时、预览、固定画布缩放；ECharts 在两种浏览器生成本地 SVG，零 HTTP/HTTPS 请求。
- Codex 人工打开观众页、演讲者视图和 WebKit ECharts 截图；运行机制清晰可读，未见叠压或非中文界面。该样稿只验证运行层，不冒充康哲报告视觉验收。
- `uv lock --check`、`uv sync --all-extras --frozen` 与旧运行依赖扫描通过，输出 `LEGACY_REF_OK`。

## Codex Independent Verification

上述命令和截图均由 Codex 在当前工作区亲自执行。上游官网与 npm/GitHub 未在独立会商中联网重拉；其来源身份采用 ADR 0003 已记录的双重获取/完整性证据，本次验收重算包内字节与清单闭合性。PPTX/PDF 不属于本 Task，未测试。

## Final Decision

Task 0.3 接受。允许在提交本 Task 后进入 Task 0.4；后续 A/B/C 页面、PDF、HTML-PPT 报告和 PPTX 仍须分别生成、真实打开和独立验收。
