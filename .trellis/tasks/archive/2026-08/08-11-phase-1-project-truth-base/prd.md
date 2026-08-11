# Phase 1 项目与科学真源基座

## Goal

Task 1.1-1.6：稳定标识与状态、可移动项目、SQLite、不可变来源与证据、事件快照、选择性感知能力预检。

## Requirements

- 项目合同只要求适应症、A/B/C 多选及 PDF/HTML 演示稿/可编辑 PPTX 可选；HTML 默认启用。
- 项目、报告、格式、下载、修订及证据/路由状态使用独立枚举，不得混写。
- 项目创建时把默认或显式数据截止日按合同 IANA 时区物化为日末 ISO-8601；恢复不随日期漂移。
- 项目目录和产物路径全部相对、可移动；SQLite、来源、证据、事件、检查点和快照分层保存。
- 能力预检只检查用户所选报告、输出和适用来源路线；缺失能力只阻断相关分支。
- 只做用户功能与科学数据一致性验证，不扩大安全性测试。

## Acceptance Criteria

- [x] Task 1.1 稳定 ID、九组状态枚举和版本化项目合同通过精确 RED/GREEN。
- [x] Task 1.2 空项目创建、移动、恢复和 A/B/C×四格式路径合同通过。
- [x] Task 1.3 SQLite 迁移、状态列隔离、追加式版本和 `integrity_check=ok` 通过。
- [x] Task 1.4 内容寻址、四类日期、来源回执、证据缺口和片段 locator 通过。
- [x] Task 1.5 事件重放、幂等、检查点、快照和附录 C 产物清单通过。
- [x] Task 1.6 选择性感知能力预检 CP01–CP08 通过，CLI 输出类型化中文阻断说明。
- [x] Phase 1 正式退出命令全绿，并由独立 verifier 接受。

## Notes

- 权威来源为 `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §3、§7–10 及已批准实施计划 Phase 1。
- 每个 Task 单独提交并保存 RED/GREEN/回归/判决；不把后续能力提前标记完成。
