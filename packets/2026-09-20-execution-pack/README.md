# 竞品调研工作流：修订后实施包

用户决策：2026-09-20。审阅基线：`d6cb6d51e1b5a5e2abdacea485ea84b5268dc7ca`。

## 给开发 Agent

先将 `00_AGENT_MASTER.md` 作为实施指令，并让 Agent 读取同目录其他文件。不要只转发本轮聊天里的摘要而遗漏事实修订、离线分享及科学比较边界。

这是实施说明与审阅证据，不是已经改好的产品代码，不会修改仓库。当前没有完整仓库/真实研究/安装/浏览器验收通过的证明。

## 文件

| 文件 | 作用 |
|---|---|
| `00_AGENT_MASTER.md` | 可直接交给开发 Agent 的主指令 |
| `01_DECISIONS_AND_ARCHITECTURE.md` | 五项用户决策与推荐数据、交互、修订、分享实现 |
| `02_REVIEW_FINDINGS.md` | 20项问题/约束/扩展点，区分实测与静态、候选和影响边界 |
| `03_WORK_PACKAGES_AND_ACCEPTANCE.md` | 11个工作包、59项行为验收、迁移与回报要求 |
| `work_items.json` | 机器可读依赖图；A/B/C平行产品线 |
| `acceptance_cases.json` | 必须执行的测试情境，不是已通过结果 |
| `contract_examples.json` | typed修订/查询/版本合同的示例意图；不是现有API输入 |
| `probes/review_probes.py` | 8项可复现窄范围检查，可从真实checkout做AST提取 |
| `probes/source_extracts/` | 明确标识的源码函数摘录；不是完整仓库 |
| `probes/phase1/` | 第一轮抄录模型探针 |
| `evidence/` | 本轮函数探针结果、第一轮原始结果、范围及问题索引 |
| `PACKAGE_MANIFEST.json` | 本材料包逐文件SHA-256清单；非产品发布签名 |

## 本包探针

仅Python标准库即可运行本轮检查：

```bash
python3 probes/review_probes.py --output /tmp/ci-review-probes.json
```

默认执行随包抄录函数，返回0仅表示成功记录观察，并非要求的不变量均通过。在本轮基线8项检查中，7项所要求不变量未满足，1项SAE正向对照通过。

对实际代码做边界核对：

```bash
python3 probes/review_probes.py \
  --repo /实际仓库路径 \
  --output /独立证据路径/checks.json \
  --assert-fixed
```

`--assert-fixed`下：0=这些窄范围不变量通过；1=仍有不变量失败；2=无法提取/运行。均不是端到端产品发布判定。重构后函数迁移须把用例接到新公共API，不能删用例或标skip。

第一轮探针要求Pydantic；其结果原样标记为第一轮原始结果，本轮没有把它伪称为重新执行的整个仓库测试。

## 已冻结方向

B默认全相关研究+分面；无医学批注；实际事实修订并跨报告同步；C为完整设计先例检索/横比；个人使用与分享；A/B/C同等验收。按需本地编辑会话是工程推荐实现，静态离线阅读继续保留。不要恢复旧的B-first、强制C候选方案和医学批注需求。
