# Phase 0 实施清单

## Task 0.1 独立仓和批准基线

- [x] 创建独立 Git 根并初始化 Trellis 0.6.14。
- [x] 复制 v1.2 规格并写批准记录、README、忽略规则和迁移清单。
- [x] 先建立旧依赖测试 RED，再实现扫描器并取得 GREEN。
- [x] 提交 `chore: bootstrap independent competitive intelligence repository`。

## Task 0.2 技术栈与依赖

- [x] 先写依赖清单合同测试并确认 RED。
- [x] 固定 Python 与运行/测试依赖，生成 `uv.lock` 和 ADR。
- [x] 冻结同步及合同测试 GREEN。
- [x] 提交 `build: lock workflow runtime and test dependencies`。

## Task 0.3 康哲合同

- [x] 两份候选文件执行稳定双读并生成差异决策材料。
- [x] 向用户呈现精确摘要、唯一差异和推荐方向。
- [ ] 等待用户确认将共享版唯一一处“经验法则”改为“经验阈值”。
- [ ] 确认后才复制合同、Logo 与离线资产，执行合同测试并提交。

## 独立验收加固

- [x] 会议复核并修复迁移清单、批准规格摘要、真实仓扫描、相对旧路径和锁文件检查的假绿缺口。
- [x] Codex 复跑 Ruff、mypy、pytest、真实仓扫描、锁文件与冻结同步；review gate 通过。
- [x] Task 0.3 仅接受对账材料，未越过用户确认边界。

## Task 0.4–0.5 包与报告机器合同

- [ ] 公共 Skill、内部能力边界、包 manifest 和唯一 CLI catalog。
- [ ] A/B/C 页面、筛选和 HTML/PDF/HTML-PPT/PPTX 格式合同。
- [ ] Phase 0 全套确定性检查和独立验收。

## 停止与回滚

康哲合同未确认、摘要漂移、依赖无法冻结、CLI 名称不唯一或存在旧运行依赖时立即停止；回滚只处理新仓，不触碰旧工程。
