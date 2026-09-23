---
name: 竞品调研
description: 触发词“竞品调研”。面向临床试验医学人员，用户用一句话提供适应症即可启动自主研究；可选 A/B/C 报告类型和历史截止日，首版只交付独立的站点式 HTML 门户。
---

# 竞品调研

## 一句话启动

直接告诉我适应症，例如：“请调研特应性皮炎的竞品，重点看疗效和安全性。”

Agent 使用同一公开命令创建项目：

```bash
ci-workflow project create --root <项目目录> --request "请做特应性皮炎竞品调研" --reports B --outputs html
```

- 未指定 `--reports` 时，命令返回机器可读的 `ASK_REQUIRED`，宿主必须用原生 Ask 说明并请您选择：
  - **A 研究创新竞品、管线、作用机制及开发/监管状态**
  - **B 研究临床疗效、安全性、基线和结果差异**
  - **C 研究人群、终点、访视、入排标准和方案设计模式**
- 可以指定一个或多个报告类型，也可以提供可选的历史数据截止日。
- 如果您已有结构化研究资料，可以作为高级输入；不提供也不影响启动，我会自主检索、判断来源适用性、下载和初筛。

每个新项目最多询问一次是否具备药智网访问条件。药智网只作为可选浏览器会话辅助和交叉核验来源；没有访问条件就跳过，会话失效时提示您自行登录。账号、密码、Cookie、令牌和授权头不会写入项目或任何交付物。

## 您会得到什么

每个所选报告各自生成一个独立的中文多页面 HTML 门户，包含完整结构化数据、图表、默认折叠的完整事实表、证据下钻、筛选、搜索、网址状态和页底外部来源区。关键资料不足时不生成草稿；若核心问题仍可回答，会明确写出限制；否则给出简洁的证据不足说明和最省事的补充方式。

首版发布面只有站点式 HTML，不提供 PDF、HTML 演示稿、可编辑 PPTX、CSV/XLSX、雷达图、证据成熟度视图或定时监测。用户手动触发刷新后，来源复核、差异识别、历史快照和受影响页面重建会自动完成。

## 运行与恢复

1. 从安装包入口运行 `ci-workflow package verify --root <安装包目录>`。
2. 运行 `ci-workflow project create`，传入适应症、报告类型和 `--outputs html`。
3. 宿主用原生 Ask 询问一次药智网访问条件，并由 Agent 调用 `ci-workflow yaozh answer` 记录 `available`、`unavailable` 或 `skipped`；不向命令传递任何账号或会话内容，同一项目不重复询问。
4. 若回答为 `available`，宿主必须用自己的浏览器能力观察用户已登录的药智企业版页面；只把项目、回答摘要、观察时间、宿主/观察者、规范来源 origin、封闭技术状态和非敏感页面标记摘要写入临时 JSON，再调用 `ci-workflow yaozh observe --root <项目目录> --observation <临时 JSON>`。不得读取或保存浏览器 profile、Cookie、存储、授权头、HAR、全量 DOM 或账号截图；会话失效、验证码、权限、工具或解析失败均不阻断其他来源。相同观察幂等，回执按内容摘要不可变保存；临时 JSON 在回执核验后精确删除。
5. 运行 `ci-workflow capability preflight --host <local|codex|hermes|omp> --project <项目目录> --independent-context-probe <宿主探针可执行文件>` 检查当前宿主能力。探针必须真实启动子Agent、独立会话或兼容执行器并返回不同上下文的运行时回执；环境变量或“yes”声明不能通过。能启动空白 Chromium 不代表药智会话有效；药智路线状态以刚生成的无凭据观察回执为准。
6. 运行 `ci-workflow project run --root <项目目录> --independent-context-probe <宿主探针可执行文件>`，读取项目内生成的合并来源计划；共享来源只执行一次，所选 A/B/C 各自进入独立分析分支。这一步只建立可恢复的研究任务，不把“已启动”误报为调研完成。
7. 当前 Agent 按来源计划完成检索、Publication 判断、竞品宇宙闭包、缺口恢复和独立复核，形成 v1.3 研究审计包及所选 A/B/C 科学载荷。药智来源必须标为 `commercial_database`/`secondary`，只作线索或交叉核验。用户无需填写内部字段。
8. Agent 使用 `ci-workflow research submit` 校验并绑定审计包与科学载荷；松散 JSON、字节漂移、项目/适应症/截止日不一致或未完成闭包均会被拒绝。
9. 仅在提交成功后运行 `ci-workflow project run --root <项目目录> --resume`。一个项目选择多个报告时会逐份生成独立门户，不建立融合首页；中断后始终从同一项目恢复且只重做未完成节点。
10. 若返回“等待一次性补充关键公开资料”，只把项目中的 `logs/manual-supply-request.md` 呈现给用户；`logs/download_requests.md` 是内部状态指针，不得作为第二份用户清单。用户放入原始文件后直接再次 `--resume`，系统会核验内容、在原目录保持字节不变地规范重命名并生成重抽取任务；不得要求用户手工改名。若运行随后返回 `recovery_required`（退出码 7），由 Agent 读取 `receipts/re-extraction-jobs.jsonl`，重新抽取并把核验回执绑定进新版严格研究包，再执行 `research submit` 和 `project run --resume`；这是 Agent 的自动恢复工作，不得转交用户填写内部字段。
11. 若用户明确选择无法取得，Agent 调用 `ci-workflow publication unavailable --root <项目目录> --official-evidence sufficient --limitation <中文限制>` 带限制继续，或在官方证据也不足时改用 `--official-evidence insufficient`。同一快照只记录一次回答，禁止重复询问；其他未受影响报告继续运行。

执行期间只向您呈现启动、重要里程碑、资料请求、阻断、部分完成或全部完成；检索过程和技术诊断写入项目记录，不塞入医学报告主页面。宿主能力暂不可用时，请按中文提示恢复对应能力后继续；已完成的来源和事实不会因重试被静默覆盖。

## 宿主验收入口

仅在候选包验收任务明确要求 `host-smoke-v1` 时，使用候选安装根的 `bin/ci-workflow` 运行：

```bash
<候选安装根>/bin/ci-workflow fixture run \
  --case host-smoke-v1 --reports A --outputs html \
  --project <独立项目目录> --host-smoke-recovery
<候选安装根>/bin/ci-workflow project verify --root <独立项目目录>
```

该场景会先证明关键证据不足时不生成草稿，再在固定补件、显式重新打开后恢复并生成站点式 HTML。不要改用源码 checkout 的入口，不要省略恢复步骤，也不要手工拼接运行记录。
