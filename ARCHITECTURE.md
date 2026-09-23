# 竞品调研工作流 — 架构与文件关联图谱

> 本文档说明仓库内所有目录/文件的职能与相互关系。新会话/新贡献者从本文档开始。

## 系统概述

一个公共入口支持一句话自动研究或高级 research-package 输入，自动编排独立可测试的内部 Skills，生成 **A 适应症竞品全景台**、**B 临床结果证据室**、**C 试验设计图谱**三类独立、中文原生、超高信息密度、多页面 HTML 门户。

## 权威文档链（按优先级）

| 优先级 | 文档 | 职能 |
|--------|------|------|
| **产品合同** | `packets/2026-09-22-sol-delivery/PRD.md` | 当前交付基线与用户确认范围 |
| **实施计划** | `packets/2026-09-22-sol-delivery/PLAN.md` | 当前 W00–W10 依赖、里程碑与连续实施入口 |
| **运行日志** | `packets/2026-09-11-pnh-vertical/runbook.md` | 当前权威运行日志（B/C 门户打通 + 复核环 18 轮记录） |
| **规划** | `plans/zcode-execution-plan-v6-20260911.md` | 现行执行计划 |
| **历史交接** | `context/ci-gpt6-takeover-20260905.md` | 早期交接文档（参考） |
| **会话记忆** | `~/.zcode/cli/memories/.../ci-workflow-current-authority.md` | 跨会话指针 + 非显见操作事实 |

## 目录关联图

```
competitive-intelligence-workflow/
│
├── src/ci_workflow/               # Python 源码（全部运行时逻辑）
│   ├── application/               # 应用服务层（研究/提交/运行/复核/发布）
│   │   ├── fresh_b_research_package.py   # B 类研究包模型 + GateSpec 绑定
│   │   ├── fresh_c_research_package.py   # C 类研究包模型
│   │   ├── research_package_submission.py # 提交校验（合同/身份/摘要/来源绑定）
│   │   ├── run_service.py                # 状态机引擎（universe→ingest→gate→render）
│   │   ├── review_issuer.py              # omp 独立复核签发（外部子进程验真）
│   │   ├── scientific_review_transition.py # 复核状态迁移
│   │   ├── visual_acceptance.py          # 视觉验收（三份绑定 JSON 校验）
│   │   └── acceptance_boundary.py        # 接受状态边界
│   ├── reports/                   # 报告层（A/B/C 门户数据构建）
│   │   ├── b/                     # B 专属（分类器/基线/处置/语义分组）
│   │   │   ├── registry_observation.py   # 终点族分类器（政策驱动）
│   │   │   ├── baseline.py               # 基线观察模型
│   │   │   ├── disposition.py            # 处置观察模型
│   │   │   ├── semantic_grouping.py      # 语义分组
│   │   │   └── contracts.py              # B 合同模型
│   │   ├── c/                     # C 专属（设计综合/契约）
│   │   │   ├── synthesis.py              # 设计路径综合
│   │   │   ├── contracts.py              # C 合同模型
│   │   │   └── design.py                 # 设计投影
│   │   └── common/                # 共享（页面注册等）
│   ├── renderers/portal/          # HTML 门户渲染器（A/B/C + 资产）
│   │   ├── report_a.py            # A 渲染（竞品全景台）
│   │   ├── report_b.py            # B 渲染（临床结果证据室）
│   │   ├── report_c.py            # C 渲染（试验设计图谱）
│   │   ├── assets/                # CSS/JS 资产（portal.css/charts.js 等）
│   │   └── templates/             # Jinja2 模板
│   ├── gates/                     # 门槛评估引擎（GateSpec → 逐对象逐单元评估）
│   ├── graph/                     # 影响力分析 + 视觉定稿
│   ├── ingestion/                 # 来源摄取（Publication Gate 等）
│   ├── sources/                   # 来源连接器（CT.gov API v2 等）
│   ├── storage/                   # 存储层（SQLite 渲染事务）
│   ├── qc/                        # 质控（浏览器验证/科学 QC）
│   ├── domain/                    # 领域模型（来源/事实/声明/快照）
│   ├── schemas/                   # JSON Schema（打包内嵌）
│   └── capabilities/              # 能力模型
│
├── policies/                      # 版本化政策文件
│   ├── gates/                     # GateSpec（B-v1.yaml / C-v1.yaml / A-v1.yaml）
│   ├── endpoints/                 # 终点兼容政策（compatibility-v1.yaml）
│   ├── endpoint-families/         # 终点族分类规则（registry-v7.yaml）★泛化关键
│   ├── timepoints/                # 时间点兼容政策（compatibility-v1.yaml）
│   └── sources/                   # 来源政策（source-policy-v1.yaml）
│
├── schemas/                       # JSON Schema（与 src/ci_workflow/schemas/ 同步）
│
├── tests/                         # 测试套件
│   ├── unit/                      # 单元测试
│   ├── reports/                   # B/C 报告测试
│   ├── browser/                   # 浏览器验收测试
│   ├── integration/               # 集成测试（多报告产品运行等）
│   └── contract/                  # 合同测试
│
├── packets/                       # 运行工作包（per-vertical / per-phase）
│   └── 2026-09-11-pnh-vertical/   # PNH 竖向权威运行包
│       ├── runbook.md             # 运行日志（当前权威）
│       ├── build_pnh_a_payload.py # A 载荷构建器
│       ├── build_pnh_b_audit.py   # B 载荷构建器
│       ├── build_pnh_c_audit.py   # C 载荷构建器
│       ├── build_pnh_audit.py     # 审计信封构建器
│       ├── accept_a_portal.py     # A 门户验收脚本
│       └── pnh-a-payload.json     # A 载荷数据
│
├── packets/2026-09-18-omp-visual/ # omp 独立验证工具包
│   ├── build_visual_docs.py       # 视觉策划书+呈现证据生成器
│   ├── reviewer-prompt-template.md # 科学复核 prompt 模板
│   ├── verifier-prompt-template.md # 视觉验证 prompt 模板
│   └── ad-raw/                    # AD 原始数据
│
├── packets/2026-09-18-ad-vertical/ # AD 竖向种子
│   ├── ad-alias-map-v1.json       # AD 别名表
│   └── build_ad_a_payload.py      # AD A 载荷构建器
│
├── runs/                          # 运行工作区（每迭代一个新目录）
│   └── pnh-vertical/
│       ├── abc-v23/               # ← 当前最终工作区（143 页三门户）
│       ├── abc-v22/               # 前一版本
│       └── ...                    # 历史迭代（v1-v24）
│       每个工作区含:
│       ├── project.yaml           # 项目合同
│       ├── evidence/library/      # 科学载荷（a/b/c-research-package.json）
│       ├── manifests/             # 运行清单+提交绑定
│       ├── reports/{A,B,C}/v1/html/ # 渲染门户（143 页）
│       ├── state/                 # 状态（科学复核请求/verdict/工作项）
│       └── receipts/              # 回执（科学复核签发凭据）
│
├── docs/                          # 文档
│   ├── specs/                     # 产品规格（v1.3 权威合同）
│   ├── architecture/              # 架构文档（页面目录/格式合同）
│   ├── acceptance/                # 验收证据
│   ├── governance/                # 治理
│   ├── decisions/                 # 决策记录
│   └── handoffs/                  # 交接文档
│
├── contracts/kangzhe/             # 康哲设计合同（视觉规范 v5.2.6）
│
├── context/                       # 会话上下文（跨会话传递）
├── plans/                         # 执行计划
├── reviews/                       # 审阅记录
├── tmp/                           # 临时文件（不入库）
├── logs/                          # 运行日志（.md 保留）
│
├── .trellis/                      # Trellis 任务管理
│   ├── spec/                      # 编码规范
│   ├── tasks/                     # 任务定义
│   └── workspace/                 # 工作区
│
├── skills/                        # 内部 Skill 定义
│   ├── _internal/                 # 内部 Skills（intake/render-deliver 等）
│   └── competitive-intelligence-workflow/ # 公共入口 Skill
│
├── agents/                        # Agent 配置（openai.yaml 等）
│
├── assets/portal/                 # 门户共享资产（charts.js/portal.css 等）
│
├── fixtures/                      # 测试夹具（正例/反例/验收）
│
├── policies/gates/                # GateSpec YAML（B-v1/C-v1/A-v1）
│
└── .github/                       # GitHub 配置（workflows 等）
```

## 工作流生命周期

```
1. project create          → 创建项目合同（indication + reports + cutoff）
2. capability preflight    → 能力预检（--independent-context yes）
3. CAS 来源获取            → CT.gov API 抓取 → sha256 寻址入库
4. build_*_payload/audit   → 派生科学载荷 + 审计信封
5. research submit         → 严格校验并绑定（字节不可变）
6. project run --resume    → 状态机：ingest → gate → snapshot → render
7. review issue (omp)      → 独立科学复核（外部子进程验真）
8. visual verification     → 视觉验证（策划书/呈现证据/独立审阅三份绑定 JSON）
9. project accept-visual   → 视觉验收签署 → 状态推进
10. accept-visual A/B/C    → 全部接受后进入发布流程
```

## 泛化能力

**新增适应症零 Python 代码改动**：
1. `policies/endpoint-families/registry-v7.yaml` 追加该适应症的终点族规则块
2. 提供药物别名映射表（`canonical_by_alias` JSON）
3. CT.gov API 抓取该适应症的原始数据

所有渲染器、门槛、验证管线均适应症无关。

## omp 独立复核管线

```
ci-workflow review issue
  --host omp --host-executable $(which omp)
  --review-command="-p,@prompt.md,--provider,<p>,--model,<m>,--thinking,<effort>,--no-session"
  --verdict state/scientific_review/<R>/verdict.json
```

omp 会话读取 review_request.json → 真实检查门户/包 → 写绑定 verdict → 流水线验签发回执。

**派发三要素**：`--no-session`（防会话复用）+ prompt 先生成 + 绝对路径钉定。

## 关键设计决策

| 决策 | 理由 |
|------|------|
| 提交后字节不可变 | 防止 scientific drift |
| 渲染器变更须新项目 | 渲染产物绑定后拒绝覆盖 |
| 研发企业两段式归属 | 对照药申办方 ≠ 研发企业 |
| 分类器安全域拒判 | AE/TEAE 不入疗效域 |
| 每规则 tolerance | 不同终点族可容忍不同时间偏差 |
| stats族分组 | 均值/中位数可并图，计数须分离 |
