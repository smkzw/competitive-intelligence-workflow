# STATUS

**2026-10-23｜Goal=active，继续实施｜M1/M2进行中，未交付**

## 当前入口与范围
- 产品权威：01_PRD、02_ARCHITECTURE、03_PLAN、04_AGENT_RULES；本页替换更新，不另立规格。
- 唯一英文工程根内rebaseline-v2；单用户Web服务+内嵌9 Skills。v1多宿主包、编辑/分享、24门户不是v2发布门；未知v1工作树保留，旧中文工程零接触。
- 分支codex/rebaseline-v2-m1。来源扩展节点已提交/push并核远端exact：`ad65b790fa63917dc2a5dbdf79ef611d5f87f1c2`。当前C阅读修复待白名单提交。
- 历史恢复依据：Trellis `10-23-rebaseline-v2-m1/PAUSE_HANDOFF_20261023_0810.md`；原暂停回执/备份不改。用户已解除暂停，历史paused/旧PID不覆盖新授权。
- 模型cms-router/glm-5.3-flash → DGX/deepseek → DGX/qwen；凭据仅注册配置到必要子进程环境，不入文件/日志/提示词，不改全局路由。

## 阶段进度
| 阶段 | 实际状态 | 主要未完成门 |
|---|---|---|
| M0骨架 | 离线骨架/部分公开来源冒烟具备 | 不是产品交付 |
| M1/C | 完整终点投影、C阅读组件具备；模型阶段恢复中 | 完整流水线/论文修订/最终科学及产品接受 |
| M2中国宇宙 | 反向扩展及恢复代码已提交，真实源离线重放通过 | 中国浏览器适配/3份专家清单/≥95%召回 |
| M3/A、M4/B | 骨架与部分切片 | 对应正式科学/图表/真实项目验收 |
| M5全球/历史 | 来源版本原子采用具备 | 历史公开资格/全球来源扩充 |
| M6加固 | 未完成 | 队列/取消/成本/导出/备份 |

## 同一R4真实模型阶段：仍运行
- 句柄49763，run_a37cd8cba43b / prj_f21d0823b44a，**attempt0002**；scope=stage/analysis_C，pipeline_acceptance=NOT_RUN。脚本ciw-data/resume-r4-20261023.py。
- 冻结`2cbab03927fbe22cc2212f3fa4105862cfec0992`代码/Skills/规则/模型和原数据；恢复启动已核冻结hash、46源、DB完整性、6580事实及缓存。没有重跑bootstrap/来源/51已完成批。
- 恢复基线151任务/51合格缓存/100待做；33非空、195条分批要点仅为暂停时范围，不是最终归并结论。不定期轮询、不因等待替换运行。
- 最近同句柄等待仍pending无新输出。终态后核实际模型、151批引用、输出恢复、用量、源hash及渲染；stage成功不替代M1完整链。
- 原attempt0001 STARTED回执不改，原97920用户SIGINT终态不再等待。暂停一致性DB备份SHA e9c18f2153ac95cff0495839d38caa4bc38a7cf1c46342fe0bcb168d3af2ce3e；冻结源/WIP副本/diff在ciw-data/pause-20261023-0810。
- 冻结模型使用旧renderer，不随当前前端热更新。其产物和本轮C候选分开验收。

## C阅读组件：同源candidate03核验完成
- Ego旧53不存在；原生Ask批准替代并复用 **59/p1**。只读预览localhost49587/C3，句柄47130；不改登录/缓存/其他空间。Ego提示更新，未擅自升级。
- ciw-data/browser-m1/c-reading-r4-03/C.html：SHA `e96d5ca88c9f14db48abd2a5eecbbfb5c6eafb18de27834671d775ec84738ffc`，12,371,833字节。
- 正常生产renderer/同R4源：284研究/6580事实/580主要/2876次要终点/282样本点/5明确0；事实hash f903dc7b89a22bc4b1c83edb8696d7df96699166e3986b089700cd2828f1be53。不是创新药全集/模型最终报告。
- 1440/1600/1920/2560×1080密集、筛后单项、原文阅读共12截图全部实看。同目录dense-stable/interaction/restoration-browser JSON含实测及操作。
- 密集样本量336px/期别160px，完整期别计数不截短，对照表顶部743.98px（旧约947）；筛后两图区120px/表顶部527.98。不缩字号、删数据或伪点。
- 9462字入排从旧181px窄格改同页宽幅阅读，四宽正文806/900/1088/1463px，16px；事实依据独立列，原文不复制改写。英语仅主动打开原文层，不铺默认首页。
- 真实键盘焦点留原生dialog；原文滚动627.5px/背景0；Esc恢复原内容、触发焦点和查询。无JS/不支持dialog仍可原details读取。
- 原生键盘检索末项NCT00932074=1；无命中0且两图卡隐藏；恢复284/284、282样本点/5明确0不变。
- 候选01标签截短/504px判FAIL保留；02单项220/300px空白被owner拒收后修复。首次03截图未等ResizeObserver稳定不采用，dense-stable才采纳；不改历史FAIL或借旧图签收。
- 接受仅C来源阅读/几何/检索组件。A/B、模型全文、论文修订及最终医学/审美门未完成；不宣称完整康哲6.1.3影像/动效合规。

## 测试、协作与复盘
- 当前全v2 **364PASS/2.70s**，Ruff全src/tests/scripts、生产JS/sh语法、Python600/80尺寸门PASS；1既有TestClient警告。相关24PASS，不为文档收尾再跑宽门。
- 一次有界执行：CodeBuddy/codebuddy-cli/deepseek-v4.1-flash/max，session01a1690e-8288-7d63-a24c-f1f2424cb2d8，304.785s/36tools/return0，无fallback，输出hash核对。worker图例/数据窗/查询；owner补稀疏高度及宽幅阅读。
- 协作审计格式缺口保留：custom prompt缺解析器规定route bullet，audit-execution FAIL/prompt_route=null；真实runner身份/effort/hash另核。不改已派发prompt、不为标题重派、不伪造审计绿；下次dispatch前规范bullet。executor不是独立科学/审美review。
- Trellis implement/check在dispatch后发现seed并已改为当前PRD/规则2+2；prompt原含read set，不能冒称清单先前已修。raw证据在ciw-data，不入Git。
- 复盘：可达不等于好读，实看长原文和筛后态；少条目不能套密集卡。viewport/ResizeObserver采样时机、大范围computed-style超时与产品缺陷分开记账。

## 来源底座与已提交M2节点
- 发现→全量candidate_triage→universe_expand→最终coverage_review；复用Skill，不添平台/表/路由。别名/靶点/企业驱动中国CT.gov+三中国站点及全球路线，最多3轮；unknown保留，failed/blocked/pending不算空成功，来源/解释独立缓存。
- 真实中国CT.gov冒烟1研究/17待查/0模型；原Placebo保留，但共同身份/旧别名读取/种子排除精确控制标签。捕获源离线重放1研究、0网络0模型，原回执hash不变。节点361PASS/ad65b790已提交，不是召回通过。
- CT.gov18页/1787唯一ID=官方总数，不是创新药闭包。77容器采用46源/284研究/6580事实，2488非空次要定义补回，其他科学值/上下文0变化；151完整终点包最大23984字符，无截尾。
- 来源文档+解析器版本原子采用，失败旧current不变；独立论文不随登记刷新撤回；HTTP/缓存/导入分开。历史as-of未实施，启动/数据/HTML守卫拒绝，不删守卫冒充完成。

## 下一有界动作
1. 白名单提交本轮五个前端/测试文件、原位PRD/ARCH/PLAN/STATUS及现有Trellis记录，push核远端exact；排除v1 WIP/未知健康日志/运行证据。
2. 同句柄等模型终态后核冻结身份/来源/缓存，只恢复失效或未完单元，不重跑已完成研究。
3. 推进不依赖模型的M2中国来源接入及A/B科学消费缺口，根因族RED→完整改动→相关批，里程碑一次宽门。
4. 搜索/微信未配置、中国适配/专家清单未具备；M1完整链/论文修订及M2–M6正式门未过不宣称交付。无须新用户裁决，不设人为暂停点。
