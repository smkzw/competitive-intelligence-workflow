# Codex 会商验收：Task 0.5 报告机器合同

日期：2026-08-11 16:43 +0800

## Verdict（结论）

**通过。** 三轮均复用同一 Pi/Kimi Code 会话 `019fefda-ba97-7000-a881-db72575ff054`，未发生 fallback。首轮与第二轮的否决均落实为合同字段和精确测试，第三轮独立复现 `16 passed`、全库 `69 passed`、Ruff 通过，P0/P1 为 0。

## Boundary Compliance（边界与来源）

- 审查只读取设计书 §12–16、项目冻结的康哲设计清单、页面/筛选/格式合同及其测试；未修改产品文件。
- 用户后续明确要求“内化最新版并停止同步通用版”，因此 `contracts/kangzhe/manifest.json` 是当前视觉真源；旧版 §16.6 的双文件措辞不再驱动本任务。
- 本任务只验收机器合同，不把页面实现、真实报告或四格式产物误报为已完成。

## 否决与修复

- 第一轮否决 8 项：B 类基线、矩阵与试验完成情况筛选缺口；基线/处置证据抽屉语义缺口；默认选择规则；PDF 横竖版与书签；HTML 演示稿视口与页码；气泡图轴向与半径公式。
- 第二轮否决 4 项：完成情况默认顺序、常见不良事件默认行、基线时间定义、方案偏离计量对象；并补齐终点族并列、真实网页视觉检查、PDF 阅读/打印、演讲者视图、证据并列固定和减少动态效果。
- 第三轮逐字段复核上述项目，全部关闭；未发现新的 Task 0.5 高优先级缺陷。

## Codex 独立验证

- `uv run --frozen pytest -p no:cacheprovider tests/contract/test_page_catalogs.py tests/contract/test_filter_contracts.py tests/contract/test_format_contracts.py -q` → `16 passed`。
- `uv run --frozen pytest -p no:cacheprovider -q` → `69 passed`。
- `uv run --frozen ruff check` 对三份新增测试文件 → 通过。
- `git diff --check` → 通过。

## Hermes / Runner Evidence（编排与运行证据）

- 全局工作流 guard 生成并预检提示词；实际会商按清单由 Pi/Kimi Code 执行，不经 Hermes 伪装其他提供方。
- runner 保存同一会话三轮最终报告；7.3 MB 原始流式输出在提取路由身份、等待策略、Token 与工具调用证据后移入废纸篓，保留可恢复清理目录。

## 最终决定

接受 Task 0.5。A/B/C 页面责任、默认选择、筛选状态、证据抽屉以及 HTML/PDF/HTML 演示稿/可编辑 PPTX 的格式例外已冻结为机器合同。后续生成器必须满足这些合同，当前没有接受任何报告实产物。

阶段清理：原始 runner 输出、不适用的 Hermes 归档尝试、已完成用途的临时提示词/上下文/连通性记录已移至 `/Users/smkzw/.Trash/ci_task05_cleanup_20260811_1644`，可恢复；三轮最终报告、指标、验收结论和 Trellis 恢复锚点保留在仓内。
