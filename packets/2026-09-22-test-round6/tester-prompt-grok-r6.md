# 独立对抗复测 round-6（grok-4.7 xhigh）

复测 round-5 你的 F10–F15 修复（提交 515500f）。产物重跑。

## 要求
1. 重跑你 round-5 探针集（runs/test-round5-grok/），F10–F14 对应用例应转 pass；F15 概念字面残留复扫（Python 匹配路径应仅剩 catalog/legacy 定义与展示标签字典）
2. 新增边界用例 ≥5 个（crosswalk 词元包含边界、composite_ae 片段判定、Period N 期别）
3. 渲染抽查：abc-v101 matrix.html TEAE 轴气泡数值是否为派生发生率；安全表事件列类目可区分
4. 写 runs/test-round6-grok/findings.json（overall/probes/findings/assumptions）

## 执行纪律
立即执行，不提问；完成退出码 0。
