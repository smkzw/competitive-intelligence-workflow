# 独立对抗测试：数据不变量轨 · round-4（grok-4.7 xhigh）

你是独立对抗测试者，与生产者（GLM/ZCode）无共享会话。本轮生产侧刚按外部专家审阅落地 8 项数据不变量修复（提交 f3ba4d3），你的任务是用**自己构造的对抗用例**独立验证这些不变量，并用真实浏览器抽查渲染产物。不信任任何生产者自述。

## 工作目录
`/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`（PNH 竞品调研仓库）。

## 清洁纪律
- 你的全部工作产物只写入 `runs/test-round4-grok/`（自行创建）；不得读取 `runs/test-round4-cursor` 等其他测试者目录
- 不得引用既往测试轮（test-igan/test-uc/ipf）的 findings 作为你的证据
- 可以读仓库源码、测试、渲染产物 `runs/pnh-vertical/abc-v97/reports/`（这是本轮被测对象）

## 测试内容
### 1. 对抗用例自建（核心，≥12 个用例）
针对以下四个模块，**自己设计**边界与否定用例（仓库自带测试不构成你的验证），全部写入可执行脚本 `runs/test-round4-grok/adversarial_probes.py` 并真实运行：
- `src/ci_workflow/reports/b/safety_concepts.py::classify_safety_concept`——否定（non-serious/not serious/non-TE）、缩写边界（SAESI? AESI?）、大小写、复合句
- `src/ci_workflow/reports/b/safety_denominator_crosswalk.py::build_atrisk_crosswalk/lookup`——同期别异值冲突、跨期别同标题、人时 vs 人数、单组多值
- `src/ci_workflow/reports/b/registry_observation.py::resolve_indication_id/classify_registry_endpoint`——规范 ID/大小写/连字符/未知适应症不得解锁专属规则。**额外用非 PNH 疾病领域词汇测试泛化**（如 2 型糖尿病 HbA1c、心力衰竭 NT-proBNP、银屑病 PASI：判断它们落入共享 generic 族还是被某疾病专属规则误吞）
- `src/ci_workflow/reports/c/endpoint_instances.py::validate_endpoint_timepoint_pairs`——重复 outcome_id 异定义、孤儿时间点、部分实例缺时间点
### 2. 既有回归真实运行
`PYTHONHASHSEED=0 .venv/bin/python -m pytest tests/unit/test_v96_review_invariants.py tests/integration/test_review_r07_ingestion_invariants.py -q` 记录输出
### 3. 渲染产物抽查（真实视觉）
用 **ego lite**（ego-browser skill）打开 `runs/pnh-vertical/abc-v97/reports/A/v1/html/overview.html` 等真实页面（真实点击、滚动、筛选、截图）：安全性标签是否按新分类呈现（"不良事件（登记）"与"治疗期间不良事件"应同时存在）、试验列表是否有样本量"未公开"行、eculizumab 产品页"监管批准事实"是否独立显示"待核验"、柱状图第一个系列是否显示数值标签
### 4. 写 findings
`runs/test-round4-grok/findings.json`：overall（pass/partial/fail）、probes（用例/预期/实际/结论）、regression_output、visual_checks、findings（severity+evidence）、assumptions

## 执行纪律（最高优先级）
- 读到此提示词后**立即直接开始执行**，不创建任务、不规划、不提问、不等待
- 所有歧义自行决策并记录在 assumptions
- 完成后正常退出（退出码 0）
