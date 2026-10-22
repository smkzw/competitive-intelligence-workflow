# 06 · 启动 Prompt（复制给开发 Agent）

```
你是这个仓库的开发 Agent，负责把「临床试验竞品调研平台 v2」从 M0 推进到 M1。

工作目录：rebaseline-v2/（v1 代码只作只读参考，不要修改 v1）。

开工前依次阅读：
1. rebaseline-v2/README.md
2. rebaseline-v2/docs/STATUS.md
3. rebaseline-v2/docs/04_AGENT_RULES.md（必须遵守）
4. rebaseline-v2/docs/03_PLAN.md 中的 M1
5. 需要背景时再读 docs/00_REVIEW.md、01_PRD.md、02_ARCHITECTURE.md、05_PORTING_MAP.md

环境：
- cd rebaseline-v2 && python -m venv .venv && . .venv/bin/activate && pip install -e '.[dev]'
- bash scripts/fetch_assets.sh
- pytest -q 必须先全绿（当前 31 条）；若不绿，先修复再做别的。
- 真实运行需要：CIW_LLM_API_KEY（OpenAI 兼容）、CIW_WEBSEARCH_PROVIDER + CIW_WEBSEARCH_API_KEY。
  如果缺少，在 STATUS「阻塞」写明，然后继续做离线可完成的部分（Skill 提示词、工具返回截断、C 门户聚类、测试）。

M1 目标：用真实 LLM 跑通一个适应症的 C 报告（建议先用「特应性皮炎」或用户指定的适应症）：
- ciw2 run --indication <适应症> --reports C
- 每个 Skill 在步数预算内提交；工具返回体积受控（>12k 字符分页）。
- C 门户 ≥10 个试验设计行，critical 字段均有来源；对 CT.gov 多 primary 的情况允许论文 supersedes。
- 结束时：pytest 全绿；STATUS.md 替换式更新（含真实运行的数字与截图路径）；03_PLAN 勾选 M1。

规则重点：
- 不提交 ciw-data/、运行产物、第三方全文、本机绝对路径、密钥。
- 不在渲染/流水线写任何适应症/药物/NCT 专用逻辑。
- 能用代码确定的事不交给 LLM；blocked/failed ≠ 无结果；缺失 ≠ 0；事件次数 ≠ 受试者人数。
- 不创建 packets/prompts/reviews/handoff 等过程文档。

遇到需求不清：在 STATUS「待用户决定」写选项与推荐，继续做不受影响的部分。
```
