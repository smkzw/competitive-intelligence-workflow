Final output written to `runs/tests/task62/minimax.md`.

## Test verdict

**PASS**

三份指定测试（19 cases）全部通过；五项独立设计的最小探针全部确认 PRD 不可放宽要求：

1. **CDE/FDA 平行 + 草案/废止不驱动默认 + 语境差异分列** — `select_current_guidance` 返回 `[cde-ad, fda-ad]`；废止标 `已替代（历史）`，草案标 `草案`；双向谱系校验阻止单边关系。
2. **严格多数 / 最常采用、主要终点计数、支持研究排除** — EASI-75 命中 3/4 → `strict_majority`；次要终点不计入；分母 1 不显示严格多数；旁证 `test_without_strict_majority_only_highest_two_trial_family_is_most_common` 验证 most-common 回落。
3. **纵向 + 单时间点不跨窗** — 单时间点 week-12 仅 `[t-12, c-12]`，week-24 仅 `[t-24, c-24]`，无跨窗污染；纵向视图 `[12, 24]`。
4. **疗效事实不伪造兼容桶；治疗—对照并列；森林图不重算** — `forest_view_count == 0`，comparison 同时含治疗—对照；平铺字段覆盖原始观察即失败关闭。
5. **默认不排名；用户排序单桶；未知不按零；重置可逆** — 构造顺序互换默认序相同；`lower_is_better` 信号正值；未知行显式列出；跨桶 `EfficacyViewError`；`reset_efficacy_sort` 复现默认序。

PRD 验收标准逐条对照，无可复现缺陷；本测试未越界执行 Task 6.1 / A 类回归、Ruff、strict mypy、`git diff --check`，建议执行者侧补全。
