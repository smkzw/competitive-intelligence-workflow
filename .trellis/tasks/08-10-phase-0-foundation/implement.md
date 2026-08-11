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
- [x] 追踪 2026-08-10 23:49 的预期外漂移，确认其来自用户另行授权的分轨设计演进，而非文件损坏或无来源覆盖。
- [x] 识别 2026-08-11 08:19 的第二次上游变化：双全文已变为相同入口 stub，`design_specs/` 已升级为 12 文件单一完整合同。
- [x] 运行当前包 6 项结构测试并核对集合摘要；识别 `local_map.md` 仍含旧“双全文同步”规则及 post-split 实产物验收尚未完成，未把结构 GREEN 误作冻结。
- [x] 核验 Logo、ECharts 6.1.0 和 HTML-PPT 上游运行时来源、许可证、摘要及最小离线边界；记录通用 runtime 的主题、动画、总览、逐页页码和英文讲者标签缺口。
- [x] 将已批准计划 Task 0.3 的双全文文件树、摘要合同、Skill 入口和 PM03 收据逐项映射为单一 `design_specs` 包的等价实现；确认前只记录，不创建目标文件。
- [ ] 等待上游分轨实产物验收完成并修正内部矛盾，重新稳定双读整个 `design_specs/` 后再向用户呈现一次精确确认。
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
