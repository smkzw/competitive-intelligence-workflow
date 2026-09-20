所有验证完成，测试全绿（25+19+16 通过），工作树未被我改动。审计证据链完整，以下为完整报告。

# Execution Output: ci-r25-yaozh-browser-adapter-20260906 - worker_01

## Boundary And Context Check

- 已读初始读取集两份文件（execution context、execution plan）。本次为只读执行审计，未编辑任何源码、测试、计划、runs 或外部路径；未触碰旧中文工作区；未打开真实药智或浏览器会话；未做 git 写操作；未安装依赖。
- 额外读取均由 context 的 "Current implementation truth" 与 "Source Of Truth" 授权：`src/ci_workflow/application/{yaozh_access,capability_preflight,autonomous_research,run_service,research_package_submission,intake}.py`、`src/ci_workflow/domain/research_package.py`、`src/ci_workflow/sources/policy.py`、`src/ci_workflow/cli.py`、`policies/sources/source-policy-v1.yaml`、`schemas/research-package.schema.json`、`schemas/package-manifest.schema.json`、`package-manifest.json`、`tools/bundle_contract.py`、`tests/{integration,unit,contract}` 对应文件、v1.3 设计文档 §1.2/§3.2/§5.3/§7 与 roadmap 现状段。
- **重要时点说明（证据，非推断）**：审计进行中工作树被并发修改——`tests/` 于 21:04:24–21:05 落盘，`yaozh_access.py` 21:05:52、`capability_preflight.py` 21:06:12 落盘（本会话开始于 21:00 后）。我对 `yaozh_access.py` 的首次读取得到的是无 `YaozhSessionObservation` 的 205 行旧版；随后 grep 得到新版。以下全部结论以 21:10 CST 重读后的当前文件为准。推测（已标注为推断）：Codex 正按 TDD 与本执行包并行落地实现。

## Work Performed

对四个审计面逐项核对了当前实现与 v1.3 契约（§3.2 第 155–166 行、§5.3 第 276–285 行、能力段第 447 行），识别出以下缺口，每条附文件与符号证据：

**G1（应用层，中）损坏/软链接的回答记录在 run 主流程产生未类型化异常。** `load_yaozh_access_record`（`yaozh_access.py:239-247`）对损坏/软链接记录抛 `YaozhAccessError`（`ValueError` 子类，`yaozh_access.py:39`）。消费方之一 `_write_source_research_work_item`（`run_service.py:594`）在 universe 节点**内联流程**被调用（`run_service.py:3043`），不在 `_run_node` 的 `except Exception → failure event` 类型化边界内（`run_service.py:1477-1490`）；CLI main 只捕获 `ContractError/FixtureCaseError/RendererUnavailableError/EvidenceBlockedError/RunError`（`cli.py:609-625`），而 `RunError` 是 `RuntimeError`（`run_service.py:44`）。结果：数据上失败关闭（不会消费坏记录），但用户看到裸 traceback 而非封闭中文结论。对照：`yaozh answer` 命令路径已正确转换（`cli.py:515` → `ContractError`，exit 2）；preflight 节点路径经 `_run_node` 属类型化失败。**推断的建议**：在内联调用点补类型化失败（failure event 或 `ContractError`），绝不静默当作“未回答”（那会违反“失败关闭，不重复询问”）。

**G2（可读性，微）** `load_yaozh_access_record` 的 symlink 分支（`yaozh_access.py:243-244`）写法形似“读软链接”，实际经 `_read_validated_record` 抛错——失败关闭语义正确，仅分支结构误导。

**G3（核心缺口，高）会话观察/访问回执类型完备但零生产接线。** 当前 `YaozhSessionObservation`（`yaozh_access.py:91-138`：extra=forbid、origin 钉死 `https://vip.yaozh.com` 且禁 query/fragment/userinfo、时区必须存在、observer/project id 拒路径分隔符与凭据词）与 `YaozhRouteAccessReceipt`（`yaozh_access.py:51-88`：六态 `ready/session_expired/captcha_required/permission_denied/tool_unavailable/parser_error` 强映射 `result_class`、`blocks_core_research=False`、`credential_fields_allowed=False`、双摘要绑定）均符合契约；`build_yaozh_route_access_receipt`（`yaozh_access.py:250-284`）对项目身份与回答字节摘要不一致时失败关闭，且回答记录永不被改写（§5.3 “`session_expired` 不是第四种回答” ✓）。但 `rg "build_yaozh_route_access_receipt|YaozhSessionObservation" src/` 仅命中 `yaozh_access.py` 自身；`cli.py` 无观察/回执命令；`run_service`/hosts 无产生或消费点；回执无持久化、无重复观察幂等规则、无过期观察拒绝策略。会话失效目前**无法**在运行期被观察或呈现。这正是 roadmap 所记“Yaozh 浏览器抓取器和真实会话探测尚未实现”（roadmap 第 119/132 行）。worker_02 的设计目标即此生命周期。

**G4（契约差距，中）能力矩阵无法表达会话失效。** v1.3 §3.2 要求“登录会话失效……由能力矩阵给出非阻断中文提示”。当前 `_user_messages`（`capability_preflight.py:501-532`）只对 `login_browser` 能力 blocked（工具级）给提示。且重写后的探针 `login_browser` 在生产路径恒返回 `False, "宿主未提供可验证的已登录浏览器会话观察"`（`capability_preflight.py:250-251`；仅 `CI_WORKFLOW_TEST_MODE=1` 的 overrides 可置 ready，`capability_preflight.py:146-163`）——这正确消灭了“空白 Chromium 冒充已登录会话”的虚假就绪（staged 测试 `test_runtime_probe_does_not_equate_blank_chromium_with_logged_in_session` 绿），但意味着回执落地前，每个 `available` 项目的矩阵将永远携带“药智网可选路线暂不可用”，且该消息无法区分 tool_unavailable / session_expired / 从未探测。**推断的建议**：回执接入后按 `technical_state` 差异化矩阵消息。

**G5（策略执行缺口，高）`LEAD_ONLY` 在引擎内零消费，“不得作为唯一依据”无确定性执行点。** `rg "LEAD_ONLY|lead_only|authority_for" src/ci_workflow/`：定义于 `sources/policy.py:27-31,139-148`，引擎内唯一使用是 `autonomous_research.py:149` 的 DIRECT 过滤；连接器内部使用与药智无关。`policies/gates/*.yaml` 与 GateSpec 相关 schema 无 yaozh/lead_only 条目。来源政策 1.1 已正确声明（`source-policy-v1.yaml:70-83`：三域 `lead_only`、其余适用域 `cross_check`、无一 `direct`、`required_* = false`、`authoritative_secondary = false`；`tests/unit/test_source_policy.py:72-83` 绿），路线完成条件里也只有**散文**约束“不得作为关键结论的唯一依据”（`autonomous_research.py:228`）。因此研究包可在 `efficacy_safety_results` 等域仅绑定 `commercial_database` 来源而提交/门槛不拒绝。这是 worker_03 的核心设计目标（如：关键声明唯一来源为 commercial_database 时 `assert_gate_ready`/GateSpec 拒绝）。

**G6（提交边界，中）提交校验不核对项目 Yaozh 回答与包内 commercial 来源的一致性。** `research_package_submission.py:274-277` 仅校验 `source_policy_id/version` 对默认政策文件；回答为 `unavailable/skipped`（路线未启用）的项目，其研究包仍可携带 `commercial_database` 来源通过提交。引擎侧无交叉校验。

**G7（注记）** `commercial_database` 域名校验把药智硬编码为 v1 唯一商业数据库（`research_package.py:322-330`：`source_type` 必须 `secondary` 且 hostname 必须恰为 `vip.yaozh.com`；schema 枚举 `schemas/research-package.schema.json:66` 与领域 Literal `research_package.py:233-246` 已同步，无漂移）。v1 范围内一致，v2 需解耦。

**其余各面均为失败关闭且已验证**：一次回答三态、同值幂等重放字节+mtime 不变、改答/篡改/跨项目/软链接/悬空链接失败关闭（`yaozh_access.py:200-236`、`intake.py:190-253`；CLI 无凭据参数面、记录键封闭，`test_yaozh_access_cli.py:24-56,178-201`）；研究包递归拒绝凭据键/值与本机绝对路径、URL 禁 userinfo/凭据查询（`research_package.py:623-655,279-290`）；技术失败类（captcha/permission）永不变造“无证据”（`research_package.py:33-46,329-351,975-999`）；`available` 才加入 `required=false` 路线（`autonomous_research.py:217-231`、`capability_preflight.py:626-649`）；login_browser 单独缺失不阻断核心研究与 HTML（`capability_preflight.py:442-459,501-532`；`test_run_capability_execution_gate.py:95` 绿）；bundle 面干净：`package-manifest.json:122` 仅含 `yaozh answer` 动词、`tools/bundle_contract.py:412` 仅允许纯类型化 `yaozh_access.py`（无浏览器/网络/凭据代码），无 cookie/profile/session 物料。

## Artifacts And Evidence

本 worker 未创建任何文件（报告由 runner 持久化）。证据即为上节引用的当前工作区文件与符号，以及下节命令观察。关键静态证据对：
- 测试规格 vs 实现：`tests/integration/test_yaozh_access_cli.py:294-392`（`YaozhSessionObservation` 六态、外来 origin/cookie/profile_path 拒绝、回执不变式）↔ `yaozh_access.py:51-148,250-284`。
- 策略声明 vs 引擎消费缺失：`source-policy-v1.yaml:70-83` ↔ `rg LEAD_ONLY src/ci_workflow/` 仅命中定义。
- 内联异常路径：`run_service.py:3043`（内联）vs `run_service.py:1477-1490`（`_run_node` 类型化边界）vs `cli.py:609-625`（捕获清单）。

## Commands And Observations

- `rg -l -i "yaozh"`（全仓定位，60+ 文件）；`rg` 系列定位符号消费方（`LEAD_ONLY`、`authority_for`、`build_yaozh_route_access_receipt`、`load_yaozh_access_record`、`session_expired`、`commercial_database`）。
- `git status --porcelain` 定向核查：`yaozh_access.py`、`test_yaozh_access_cli.py`、`autonomous_research.py`、`research_package.py`、`schemas/research-package.schema.json`、`test_run_capability_execution_gate.py` 为未跟踪新文件；`source-policy-v1.yaml`、`capability_preflight.py`、`cli.py`、`test_capability_preflight.py`、`test_source_policy.py` 为已修改。
- `stat` 取 mtime：确认 21:04:24–21:06:12 并发落盘（见 Boundary 节）。
- 时点测试验证（`.venv/bin/python`，`PYTHONDONTWRITEBYTECODE=1` + `-p no:cacheprovider`，零工作树写入，fixture 在 /tmp）：
  - `tests/integration/test_yaozh_access_cli.py` → **25 passed**（10.28s）
  - `tests/integration/test_capability_preflight.py + test_run_capability_execution_gate.py` → **19 passed**
  - `tests/contract/test_v13_intake_package.py + tests/unit/test_source_policy.py` → **16 passed**
- 观察：staged 测试与 21:05-21:06 落地的实现一致并全绿；环境内 ambient `python3` 不可导入 `ci_workflow`（见下节）。

## Blockers Or Missing Environment

- 无阻断性缺失。环境注记：`/Users/smkzw/.local/bin/python3` 无 `ci_workflow`/项目依赖；`.venv/` 已存在且可用——后续 worker 直接用 `.venv/bin/python`，无需任何安装。
- 审计窗口内工作树被并发实现修改（时点已记录）；若 Codex 在 21:06 后继续改动，G3–G6 的“当前状态”需以更新后文件复核。

## Rerun Requests Or Next Step

无重跑请求。请 Codex 裁决三个精确问题，并按分工推进：

1. **Q1（给 worker_02/修复）**：损坏/软链接回答记录应统一为何种失败面？现状分裂——preflight 节点路径=类型化 failure event（run outcome failed），universe 内联路径（`run_service.py:3043`）=裸 `ValueError` traceback。建议统一为类型化停止 + 中文修复指引；是否同意？
2. **Q2（给 worker_02）**：回执持久化选型——append-only 事件存储 vs `state/` 下可复写的易变运行事实（类比 `capabilities/preflight.json`）？§3.2 要求能力矩阵反映会话失效，回执生命周期需与矩阵消息打通。
3. **Q3（给 Codex）**：`login_browser` 探针在非测试路径恒 blocked（仅 `CI_WORKFLOW_TEST_MODE` 可覆盖）是否即真实会话探测落地前的既定过渡姿态？若否，需为宿主定义非测试的“可操作已登录浏览器”声明通道。
4. worker_02/worker_03 应以本报告 G3（回执生命周期）、G4（矩阵消息差异化）、G5（lead_only 唯一依据的确定性门槛）、G6（提交时 commercial 来源 vs 项目回答交叉校验）为输入；后续真实宿主冒烟（vip.yaozh.com 实机会话观察）按 roadmap 独立里程碑执行，不属于本执行包。
