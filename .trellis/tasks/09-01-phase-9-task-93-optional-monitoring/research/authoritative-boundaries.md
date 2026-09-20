# Task 9.3 权威边界摘录

## 产品合同

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §17.3：监测只写入去重后的变更候选；不能自动接纳事实、生成正式快照或发布报告；用户决定是否启动正常刷新；移除监测不影响新建、打开、恢复或手动刷新。
- 同节最低字段：候选 ID、来源/版本/定位、发现时间、实体和声明域、变化类型、当前值与候选值、去重摘要、可能影响的报告/页面、获取/诊断状态、用户处置。
- §7：`monitoring/inbox/` 使用 §17.3 schema，不能绕过核验和批准。

## 已有实现约束

- `project_service.py` 已创建 `monitoring/inbox/`，所以本任务不改变项目工作区必需结构。
- `event_store.py` 是项目内追加式事件真源，已提供事件 ID 与幂等键冲突检测。
- `refresh_service.py` 是正常刷新与版本接受边界；监测只能生成输入交接，不能调用其接受、快照或发布动作。
- `package-manifest.json` 已登记内部 `monitoring` Skill，但尚无变更候选 schema 和运行服务。

## 实施裁决

- 不新增数据库迁移：候选当前投影使用 `monitoring/inbox/` JSON，历史使用事件流，以保持监测可卸载。
- 不实现调度器和宿主适配，不新增可见页面。
- 技术获取失败与确实无变化/未公开分开建模；只有恢复尝试达到合同要求后才可要求用户协助。
