# 资料包与文件导航

工程唯一根：/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow。以下源码路径相对此根；本包内部链接可直接打开。大体积原始数据不再复制一套；应使用manifest/CAS引用并在W00核验可得性。

## 1. 权威与沿革

| 资料 | 用途与地位 |
|---|---|
| [PRD](PRD.md)、[设计](DESIGN.md)、[计划](PLAN.md)、[规范](EXECUTION_RULES.md) | 当前用户要求的整合与本轮建议执行基线 |
| [原Goal原文](evidence/goal-before-review.json) | 工具读取，状态paused；保留完整objective，不隐含恢复 |
| [专家原件](sources/CI_0922V2_review/0922V2_REVIEW.md) / [其下一阶段建议](sources/CI_0922V2_review/0922V2_AGENT_NEXT.md) / [40案例](sources/CI_0922V2_review/0922V2_ACCEPTANCE.md) | 固定700bd4c的审阅输入，10文件摘要验证通过；不直接执行其脚本 |
| [0920设计裁决](../2026-09-20-execution-pack/01_DECISIONS_AND_ARCHITECTURE.md) | 五项需求与复用设计；用户本轮明确纳入五项 |
| [0920工作包/旧验收](../2026-09-20-execution-pack/03_WORK_PACKAGES_AND_ACCEPTANCE.md) | 适用行为案例保留，顺序由本包取代 |
| [v2.0设计草案](../../docs/specs/competitive-intelligence-workflow-design-v2.0-draft.md) | 技术沿革，不将草案自动当用户批准 |
| [v1.4](../../docs/specs/competitive-intelligence-workflow-design-v1.4-review.md)、[v5](../../plans/gpt6-execution-plan-v5-20260905.md) | 原Goal所指旧完整规格/计划 |
| [v1.3](../../docs/specs/competitive-intelligence-workflow-design-v1.3.md) | 更早批准范围，不覆盖新用户要求 |
| [v102交接](../2026-09-22-v102-handoff/handoff.md) | 近期实施状态；其中下一步顺序不照搬 |
| [PNH runbook](../2026-09-11-pnh-vertical/runbook.md) | 历史事实日志，优先读追记66–70；“accepted”等需实际证据复核 |
| [Sept11 handoff](../../HANDOFF_20260911.md) | 历史接手信息，不是当前最新检查点 |

## 2. GitHub固定地址（本轮已核验）

- [仓库](https://github.com/smkzw/competitive-intelligence-workflow)
- [本轮最终观测提交](https://github.com/smkzw/competitive-intelligence-workflow/commit/2df24bb441e555f20b233ad2011b4ffd3610655b)
- [专家基线至当前差异](https://github.com/smkzw/competitive-intelligence-workflow/compare/700bd4c1fb90c49e27b6ff46fba07a5f7f296b6c...2df24bb441e555f20b233ad2011b4ffd3610655b)
- [固定源码树](https://github.com/smkzw/competitive-intelligence-workflow/tree/2df24bb441e555f20b233ad2011b4ffd3610655b/src/ci_workflow)
- [信任/摄取链](https://github.com/smkzw/competitive-intelligence-workflow/blob/2df24bb441e555f20b233ad2011b4ffd3610655b/src/ci_workflow/application/fresh_research_ingestion.py)
- [运行日志固定版本](https://github.com/smkzw/competitive-intelligence-workflow/blob/2df24bb441e555f20b233ad2011b4ffd3610655b/packets/2026-09-11-pnh-vertical/runbook.md)

使用gh读取而非依赖网页抓取：main当时与本地一致，仓库public；PR/Actions run/Release列表为空，.github无tracked文件。空列表不是通过。新包当前未提交，不在以上固定树中。

## 3. 组件导航与有界读法

| 任务/层 | 文件入口（先读完整相关定义，再沿调用链） |
|---|---|
| 用户入口 | src/ci_workflow/cli.py；application/intake.py、project_service.py、autonomous_research.py、capability_preflight.py、run_service.py |
| 可移植Skill | skills/competitive-intelligence-workflow/SKILL.md；skills/_internal；graph/typed_skills.py、executor.py、definitions/new_report.py、refresh.py |
| 来源与论文 | src/ci_workflow/sources；application/source_research_service.py、publication_manual_gate.py、yaozh_access.py；domain/publication.py；policies/sources/source-policy-v1.yaml |
| 信任与摄取 | application/research_package_submission.py、fresh_research_ingestion.py、review_issuer.py、scientific_review_transition.py；domain/research_package.py |
| 底层存储 | domain/facts.py、evidence.py、claims.py；storage/content_store.py、sqlite.py、source_derivation.py、snapshot_store.py、event_store.py；migrations/0001–0010 |
| 分母/安全 | reports/b/safety_denominator_crosswalk.py、safety_concepts.py、concept_catalog.py；PNH build_pnh_a_payload.py、build_pnh_b_audit.py |
| B完整语义 | reports/b/semantic_contract.py、semantic_grouping.py、registry_observation.py、baseline_views.py、disposition_views.py；policies/timepoints/compatibility-v1.yaml |
| C先例/实例 | reports/c/endpoint_instances.py、contracts.py、pages.py、synthesis.py、eligibility_source.py；application/fresh_c_research_package.py；PNH build_pnh_c_audit.py |
| 共同视图 | reports/common/view_state.py、page_registry.py、coverage.py、chart_specs.py；reports/common/page-catalogs/A.yaml、B.yaml、C.yaml |
| 三门户前端 | renderers/portal/report_a.py、report_b.py、report_c.py、builder.py；同目录assets及templates；根assets/portal是另一副本，先确认消费者 |
| 修订/刷新 | application/correction_service.py、refresh_service.py；graph/impact.py；storage/render_transaction.py；application/latest_delivery.py、delivered_artifacts.py |
| 安装/宿主 | application/fresh_install.py、host_smoke_runner.py、host_smoke_scenario.py、acceptance_runner.py；tools/bundle_contract.py、package-manifest.json |
| 质量 | tools/gate.sh；tests/unit、contract、integration、reports、browser；不能只读测试名称当生产行为已覆盖 |

PNH packet是垂直迁移输入，不是新通用入口。build_pnh_audit.py存在导入时/tmp读取，**禁止为了看结构直接import执行**。先阅读，参数化后才运行。批次实验所有输出显式指定新安全目录。

## 4. 当前材料与证据位置

- 现成候选：runs/pnh-vertical/abc-v106；A/B/C各自reports/<kind>/v1/html。
- run ID：run_b6d6d289715d3b558b641f47；实际页面数56/70/18。本轮没有重新生成。
- 科学verdict：该运行state/scientific_review下；runbook70记录三者veto，W00逐个绑定实际字节，不引用旧轮accepted。
- CT.gov原始CAS：构建器指向.artifacts/source-cas/ctgov-live-20260906/evidence/raw/sha256；本轮未全量重新验证其闭包，必须在W00核验，不默认本包已携带。
- 非PNH材料入口：packets/2026-09-18-ad-vertical/ad-alias-map-v1.json与build_ad_a_payload.py；是候选种子，不代表AD完成。
- 浏览器实证：[桌面](../../output/playwright/review-20260922/matrix-desktop.png)、[手机](../../output/playwright/review-20260922/matrix-mobile.png)、[初始DOM](../../output/playwright/review-20260922/matrix-initial.yml)、[差值DOM](../../output/playwright/review-20260922/matrix-difference.yml)。
- [本轮baseline与摘要](evidence/baseline.json)、[本轮检查记录](evidence/REVIEW_EVIDENCE.md)、[独立审阅](evidence/native-review.md)。

复制本包到另一机器不自动得到原始CAS或源码。应取得固定Git提交、本包、必要来源manifest/CAS；必要商业原文只在合法许可内传递。文档路径是工程接手导航，不得原样进入产品分享包。

## 5. 一手方法来源

[ClinicalTrials.gov结果阅读指南](https://clinicaltrials.gov/study-basics/how-to-read-study-results)区分受影响人数、风险集与事件表；[官方AE结果表模板](https://cdn.clinicaltrials.gov/documents/results_table_layout/DataEntryTable_FreqAEForm.pdf)为统计对象检查入口。查具体研究仍须读取其真实来源字节与上下文，不能由通用字段名推断分母适用。
[ECharts dataset](https://echarts.apache.org/handbook/en/concepts/dataset/)支持渲染数据/配置分离，不提供科学归并合法性。CT.gov数据结构网页本轮抓取仅得到JS壳，未把它称为已完整读过。

