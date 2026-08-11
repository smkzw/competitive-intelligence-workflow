# Codex Review: ci_phase2_task21_ontology

Date: 2026-08-11
Delegated-agent output: `runs/pi_ci_phase2_task21_ontology.md`

## Verdict

PASS。Task 2.1 可以接受；Task 2.2 及后续能力未提前接受。

## Boundary Check

- 独立 Hermes reviewer 使用当前夜间有效路由 `Pi/opencode-go/deepseek-v4-flash:max`，session `019ff137-3e4c-7000-ad67-8caaa88f2de1`，无 fallback。
- Reviewer 只读，隔离 RED 复现目录已删除；runner 仅写其管理的报告和原始输出。旧工程和外部资料未修改。

## Codex Verification

- 四个批准 exact node 均分别取得 `1 failed`（目标模块不存在）和 `1 passed`。
- Task 2.1：4 passed；含包合同：5 passed；全库：Codex 137 passed，reviewer 137 passed。
- `ruff check src tests`、strict mypy、`package verify --root .` 和 `git diff --check` 通过。
- 生产代码确实从 `innovation-therapy-v1.yaml` 解析规则；未知中文名、宣传词和未命中英文模态均保持 `review_pending`，不进行名称相似度猜测。
- 创新组件+传统背景治疗仅计创新组件；纯传统组合排除；任一 pending 使 `universe_closed=false` 且下游节点为空。
- 独立审查回执要求 reviewer、决定、理由、规则版本、至少一条证据片段和带时区时间；模型冻结且禁止额外字段。
- 安装包清单恰好登记当前本体策略，并补登记 Phase 1 迁移 0008；包合同和实际文件一致。

## Delegated-Agent Output Review

Reviewer 给出 PASS，P0=0、P1=0。其三个 P3 中，`ruff check .`/`mypy .` 对 Trellis、宿主钩子和历史测试的噪声不属于项目既定质量门；生产调用接线明确属于 Task 2.2；边界项保留原 `review-unmatched-boundary` 规则并由审查回执记录最终决定，符合审计语义。没有需要修订的 Task 2.1 缺口。

## Residual Risk

- 当前本体规则是用户批准的产品范围，不是对所有药物创新性的通用监管裁决；边界项必须继续人工/独立审查。
- Task 2.2 必须确保所有组件和所有方案都进入同一闭合检查，不能绕过 pending 项。
