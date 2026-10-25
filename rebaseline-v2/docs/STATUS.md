# STATUS

**2026-10-25｜实际Goal active｜rebaseline-v2 M1–M6未全部完成、未交付**

当前计划见03_PLAN，正式需求见01_PRD，架构见02_ARCHITECTURE。详细历史/实际模型/失败/恢复在根Trellis任务10-23-rebaseline-v2-m1/implement.md；旧STATUS/PLAN完整原文保留于Git62e6355f。此页替换更新，不把历史在途任务继续列为当前活动。

## 当前活动与安全恢复

- 已push并fresh remote确认 **874ac5d0**（表格阅读节点），前序b76d2553/f61921b0/62e6355f/0a39e40d保留。仅英文工程rebaseline-v2，v1未知工作树/根HANDOFF不动，旧中文工程零接触；不reset/clean/add-all。
- **真实摘要run_8e357c79edf6已终态FAILED**（原prj_f21d0823b44a，62e6355f冻结，隔离real-synthesis-20261025-02）；不再等待91108、不冒作运行中。实际GLM glm-5.3-flash成功事件2、备用DGX DeepSeek-V4.1-Flash-1017事件84；GLM502后按授权备用，未使用Qwen。原151/780/四科学表/runtime均未变，0新来源，最终findings0，无报告接受。
- 失败根因为第32个归并包输入9要点/62别名，step3提交5要点全部缺fact_refs，非实际外来引用；Finding旧schema默认空数组，使其在Agent内算已提交、外部再拒绝。31合格归并单元完整保留。该最小schema修复已56相关及1678全门PASS、31资格缓存迁移；复用现有4步纠正机会，不新建执行器、不重跑151批或31合格单元。公开摘要不复制原模型正文；精确失败审计在该运行failure-root-audit.json。
- 只归并原780要点，不重跑151原研究批。原780 SHA295f9be691f80c9cc414d95f99f45e9e787e51105c66cb147621d65a6b0c34a5，5212 current引用、46CAS、四科学表及151输出哈希全部资格核对；原source/事实只读不改。原0a39准备目录01从未启动，已有superseded回执，旧manifest不改。
- 旧句柄52075/旧ec32归并已获授权停止并有备份，不再等待。暂停原文/前后DB+46CAS/300缓存/303旧Qwen事件在PAUSE_HANDOFF_20261024_SYNTHESIS及ciw-data/pause-20261024-synthesis；不能把旧DB的running字段当活进程。
- 隔离归并不是最终流水线接受，失败已记录；修复/恢复后仍须摘要逐项核源，再用当前UI重渲染；新UI不回写62冻结运行。原控制器未用SIGINT停止，不改其冻结字节；此次为自然失败而非人工中断。
- Ego长期授权专用空间当前84/p1；替换空间/恢复窗口无需再Ask。不改日常登录、缓存、浏览器版本。当前A/C基础UI服务05 PID5367/58139，B当前表格02 PID4899/63747（前08暂保留）；已核实并停止本轮01/03/04/05/06/07及早期已替代预览，源/截图保留，不触碰模型任务。

## 本轮已完成的实现与实证

1. **归并根因**：空批/空正文/外来引用/拒绝层假成功/无界正文及实际失败但可读HTML均有生产反例；每短引用对应一事实，选择/未选留审计，不删科学事实。沿用原stages，不建新表/平台；拒绝层明确failed，新策略不重做研究。既有read_project_fact可解析仅本包短ID到完整值/上下文/来源，跨包/旧调用别名拒绝。
2. **Kangzhe7.1.1**：官方Logo SHA8d16d3ae…及原tokens/motion固定；单一生命周期环境光场和KPI/摘要指针光，数据面不旋转，不加装饰电影或第二框架。紧凑标题/统计/检索行、18px正文/16px辅助、全宽语义布局已接通。C1920表顶由worker719px收紧至581px，不以缩字号达密度。
3. **实际图面发现再修**：B小数和N断行、药名尾字折行及A单观察满屏已修；2RED→44相关PASS。04同候选四宽×四状态×ABC共48真实截图，数值/单词换行探针0失败，无页级横溢；glyph→真实事实行与A/C Enter/Esc回焦均实跑。它是固定源组件，不是完成全宇宙或新医学报告。
4. **开发门**：04完整v2 **1591PASS10.88s**，Ruff全src/tests/scripts/setup、5JS语法、200Python600/80过（create_app例外），257冻结输入后核未变，1既有TestClient警告。manifest352c67da5d3743807ec8a567174679d4e6e1b813ab63458771bc4c441071a8a4；生成egg-info6文件保留在旧快照但明确排除安装源集，未纳入产品包。
5. **真实动态**：03浏览器实证指针70%/70%、滚动光场-36、reduce归零/无旋转，实际返回导航后owner恢复。没有据navigationType=navigate推断一定命中BFCache。04相关函数同字节，未伪造一次新的05动态全验。
6. **04离线安装**：新建隔离venv，uv本地缓存构建/安装，0包下载/来源/模型；wheel4db992d8…、sdist2f438d0b…，全部Python/22资产/9Skill同字节，/tmp隔离启动CLI9行，显式坏路径exit2且不创建数据。不是完整M6或后续资源已变的05安装接受。

## 执行与独立审阅

- E03实际pi/cursor/default/session01a17132…/750.402s/380tools/return0，无fallback；底层具体模型未知。worker改共享UI写集，owner实屏纠正几何；报告不当视觉接受。
- C03实际批准备用pi/openai-codex/gpt-6.1-sol/high/session01a17137…/236.855s/96tools，独立47离线PASS。原REVISE保留，空正文/恢复及引用含义由owner真实反例修复，不冒作又一次独立医学PASS。
- 视觉首路Gemini缺凭据，runner备用误续不存在session而失败，0审阅；保留原拒绝回执，不修全局路由。新鲜允许备用 **pi/openai-codex/gpt-6-luna/max/session01a17159-485f-7000-beb7-163aaa5aa327** 349.432s/91tools/return0，实际看3联系表和12原图，核manifest与图hash，没有现场浏览器/医学签收。
- 独立视觉疑问已实核：C在1440/2560通过真实滚轮读到排除22、关闭始终可见、滚动不漏宿主、Esc回焦；不是裁切缺文。A所谓“液”孤行未复现，9字实际Range同y，未盲加nowrap或改列宽。B不同宽度表开合为捕获过程保留glyph展开状态，非响应式产品规则，重采默认态时要先复位。
- 采纳次级来源上下文建议：B当前图旁与C详情标题下补真实登记标识，保留药物/期别为主，不造身份或新增警示墙。7RED→33相关PASS；05新增7RED后33相关PASS，最终完整v2 1591PASS11.01s、全Ruff/5JS/200Python600-80过；256冻结文件后核未变，manifest bb8b44a47c5cdf5f26f0a2f059cdba568d21d1ba13ed0ba3dce1110bf7980e3b。05受影响实屏16图、owner实看5原图；04原48图不改作05完整矩阵PASS。不再启动第三轮全页模型审查。05当前wheel SHA14ada4667292e2712bdd9bf86ad3244f48d012ee978ae572b50ad04b8a15fddb、sdist aa1be9d552853edc5733ad80b73a162729b368ba79b626e76a53d052a235455a；真实离线新venv全部模块/22资产/9Skill同字节，/tmp隔离CLI通过、坏override exit2。安装后的DB+CAS真实备份/恢复保留19源、278当前事实（原历史510），普通A/C渲染与05HTTP逐字节一致；另以该安装版真实恢复B原源，708当前事实/668结果/70图组/全部fact ID完整，B HTML SHA85c6de1d…与05HTTP一致。0新来源/模型，不是后续CDE源码的新安装接受或完整M6。

## 当前来源增量与开发门

- 生物制品公开临床试验申请实际控件为applytypecdeNewReportSw、原值LCSYSQ；原化药控件在此范围隐藏且值空，不能当IND。生产适配/类型化输入/缓存/部分恢复均按两个实测范围分开；未启用其他类型，无新增获批/MAH/适应症事实。
- 正常来源工具真实读取生物15条/1页、化药431条/9页，精确各命中1受理号，0模型；源码运行前后相同、来源CAS保留。此为来源范围，不是AD/IgAN/PNH全集或95%召回。原观察脚本的stderr遗漏/隐藏控件失败保留，修后有3生产RED及相关回归。
- 首全门1598PASS/2旧DOM模拟器FAIL保留，实际两来源均已过；模拟器适配可见控件、原恢复断言保留并增加生物恢复。79相关PASS后，冻结02当前全v2 **1602PASS14.56s**、Ruff全/9JS/203Python600-80过，264输入不变；manifest aea8ddf059229f1731c4df59961715dd49b9038f127dc7df0057cbdea2dea5cb。新CDE源码尚无最终新wheel综合接受，不借UI05旧包宣称新版安装通过。
- 精简源/代码/安装B回执见docs/evidence/20261025-cde-biological-and-installed-b.json；两个真实来源、完整失败及恢复资料留本地ciw-data。只Raise已授权Ego窗口恢复截图；未改登录/缓存/版本或其他任务内容。

## 当前阅读与独立参照节点

- 当前B阅读08 manifest14e6ddeb01bc17cd5eec0ce09830e8393e889d38026fdd845c4595d14c426107，HTML87330c0e56f61a82d8f0d77f87c9b70fccf337e223e7753cdba99737c0ba6da9；原source50bc0483…与current事实eb4067d2…不变，只读原DB。全668结果/668图点，70→34为复合访视按阈值形成各自曲线，不删观察；逐fact old/new映射2bdd3fe4…保留。449原离散量按原SD显示，0/单侧端点及raw string不改；队列/年龄图例与表复用同一阅读路径，原组名/完整定义可展开。
- 08完整v2 **1630PASS11.81s**，Ruff全通过，实际10JS逐项语法过，206Python600/80过（create_app例外），268冻结输入复核不变。06完整1624PASS、07完整1630PASS但RuffFAIL均保留，不改历史；新冻结08是最终本组件开发门，不冒称M4完成。
- 同08真实四宽default/阈值三队列/筛后单队列/AE条形/原文SD各5态，加同图四次resize共24截图，均为实际paint后几何/末值/无页溢/18px/真实glyph→原行/原文核对通过；owner实看4当前原图（1440默认、1600原文SD、1920AE、2560筛选）。未知英文标题、长选择器与完整表年龄孤字/列密度仍待后续，不宣称全前端美学或全中文接受。公共精简证据与4样图见docs/evidence/20261025-b-reading-facets-dispersion.json。
- 原Grok4.7/high独立报告6a53b452…REVISE保留。采纳图阈值可见、SD、完整队列及拼写阈值拒绝；周/日一律拆开建议拒绝，合同保留精确7天换周、原访视与碰撞守卫。latent源比较符/GEOMETRIC_MEAN留下一根因包，非本真实blob触发。一次同会话084190aa…窄复核44085已终态：实际grok-4.7-build/high、1469.406s/11turns/return0/no fallback；冻结06有界PASS、独立38PASS0.52s，原REVISE保留全中文等后续，只审06不冒称08独立接受；无新全页循环。owner预检路径语法失败后仍dispatch是顺序失误，原prompt/事故保留，事后展开16实际路径并preflight零警告过，不伪称启动前通过。
- M2独立初稿实际grok/grok-build/grok-4.7/high/session0fac4122-bf69-441d-a7db-44dd0f0d7a91，1906.37s/69turns/return0/no fallback；AD91/IgAN41/PNH20是暂定条目，不是全集或分母。41文件7984956字节由owner逐哈希核对，manifestbef0b8ce7a44e97762d7b27a61881985dbb4d3e659bcfdaedab8843eccbf999c；中国AD仅20/464原导出，其余中国页缺失/别名未闭合，故不封存、不计算召回。
- M2 recovery01同Grok会话已终态拒绝，69149已回收：实际2758.911s/59turns/return1、max_turn_requests，无fallback；三病登记分页已落盘，独立最终报告缺失，不能接受或继续等待该句柄；仅补剩余中国公开源/范围及别名，禁止读生产候选/Skill/DB/报告。此前会话用69/128turns、1906.37/7200s，本续接限定剩59turns/5293s、同模型无备用，不重置总预算。用户永久授权替代专用空间，故允许新建一个替代研究空间，不夺回用户控制的81、不碰owner空间；不再Ask。只写reference-goldens-20261025/recovery-01，原41文件不改。首preflight缺输出路径失败后修，第二通过有1文件列表识别warning；实际明确名单/原41文件存在。原报告提及tmp外部builder，未由owner执行，续接收回允许写集并保留该限制。全部初稿仍PROVISIONAL，独立性全工具边界审计尚未完成。

## 当前引用schema恢复

- 最小生产改动仅Finding.fact_refs为必填非空数组，第三步漏引用可由现有第四步纠正；4真RED→56相关PASS/Ruff。未延长预算、不改harness/路由/来源/归并算法。新固定manifest7c5a6c3d…全v2 **1678PASS11.60s**、Ruff/10JS/208Python600-80/271输入不变。实际隔离准备run_d510975298a3（real-synthesis-20261025-03）：原780、首层76包，经精确旧签名/task/源/新schema及生产后检验31原输出保全，原source/单元不改、49CAS校验链接、0模型/来源；待32–76包。绑定Git b76d2553冻结109 src/skill文件与通过1678门的同字节候选后，唯一run_d510975298a3现已自然failed，88768已回收、不得再等待；实际4个GLM成功调用、0备用，模型先读取64短引用、step3耗8192输出tokens却只交空工具对象，step4漏全部5条bullets；未取得合格归并结果；原4步预算/780输入/31资格单元保留，不另造run。请求GLM→DGX/deepseek→DGX/qwen，实际本轮glm-5.3-flash，31资格行/科学表/运行时均未变，0新来源，未签收。首次私有控制器因DB.path为str在started之前被拒，0模型/queued未变；独立recovery01控制器作Path包装并另存activation，原失败文件不改。SIGTERM/SIGINT仅请求产品RunControl合作停止，完成当前请求后在安全边界留存，不能把发送信号当已暂停。

## 当前来源标量纠偏

- 生产族24场景初18FAIL/6PASS：比较符剥除、非有限/异常千分位、科学记数/符号、明确几何/普通均值被单位覆盖；修复后86邻接PASS。继续查LLM引文发现同一阈值被认证为确数，6符号反例真RED；旧quote正例以ALT<3作为mean3不成立。保留不等式原文测试，改用完整比较表达或结构；其他回执/恢复正例补真正ALT实测3材料，回滚/幂等/版本断言不删，另新增旧确数降级反例。相关131PASS后，邻接数字字符串绕过再12RED，补相同守卫；153相关PASS1.12s。03冻结c8844947…全v2 **1674PASS12.52s**、Ruff/10JS/207Python600-80/269输入不变。01原1661PASS/1文字断言FAIL及超600行保留，02的1662PASS不冒作已覆盖后发现的数字字符串绕过。
- parse_number仅有限精确数；parse_observation保留完整带符号原值，raw值/原文不变、不当零；proportion只来自明确参与者比例，MEAN/几何/LS明确统计优先于单位。原样“Standard Deviation”与enum映射保留。StatType、作者extract-results Skill同步，原正在运行或历史冻结Skill不热改。
- 新quote规则quote-bd77e1050adcd448已只读核原6580当前事实，均为code层，0个LLM stored-verified需重签；原780要点5212唯一引用全部仍可资格采用（0受影响），7表逻辑SHA前后相同、0回执/来源/模型写入。这非逐条医学接受。实际原CAS668结果生产parser前后相同；当前B HTML与08原浏览器字节相同87330c0e…，有绑定不另跑几何。31归并缓存仍须逐task/schema/source兼容后复用，该恢复运行另见本页新终态，不把资格审计当模型执行。精简回执见20261025-source-scalar-and-synthesis-failure.json。

## 当前B表格收口

- 表格02 manifest e33d7b662c4018160abdcc91e7c7d2dceec0f9bd289bec5939ada206785d351a，HTML57faecdb…；四宽×密集/筛后原组名共8实图，年龄token与完整单访视0断裂、18px/无页横溢、键盘展开/闭合回焦通过，owner实看1440密集/1600筛后原名/2560密集。1600所选闭合行115.78→96.59px，668事实/34组/全部图点及整个图形JSON与08完全相同。源raw/未知范围不改；未缩字或全表nowrap。
- 整族59相关PASS0.42s后一次冻结全门1689PASS10.54s、Ruff/10JS/208Python600-80/272输入无变。01保留1681PASS但实际Week破行未放行；02修访视中文和列权重。精简证据20261025-b-table-cohort-visit-reading.json；不签全M4/全中文/新版安装。

## 全局进度

| 阶段 | 已具备 | 仍未完成 |
|---|---|---|
| M0 | Web/存储/来源/9Skills骨架 | 不等于交付 |
| M1/C | 原151批/完整原设计/恢复/归并根因/阅读组件 | 实际归并输出合格、最终摘要核源、完整普通流程、真实论文修订 |
| M2中国 | 登记464CTR及部分详情、CDE受理/化药IND及生物临床试验申请、NMPA精确证书与缺页恢复 | 全应查详情/栏目、创新与适应症归属、独立参照清单和95%召回 |
| M3/A | 共同正式名/靶点/角色/有限声明及图表 | 全候选档案/MAH集团/真实阶段、三适应症可用报告 |
| M4/B | 单研究668结果/当前34组（历史70）、七域、时间折线/标值/原表与glyph | 中文临床指标/完整上下文、跨研究语义、安全图、论文及50关键事实 |
| M5 | 来源版本原子更新/缓存核查分离 | 全球扩展、历史事实版本资格；截止日守卫继续保留 |
| M6 | 下载JSON/CSV、DB+CAS备份恢复、运行/发布/安装切片 | 真实来源模型取消链、完整成本、最新CDE源码安装与综合接受 |

## 下一安全动作

- 08阅读组件开发门/相关实屏及独立06窄复核均已完成；未知英文及完整M4另有明确未完成项。准备白名单提交与push，不借旧安装包宣称08安装。05基础组件/该候选ABC安装恢复已闭合，精简回执见docs/evidence/20261025-review-remedy-install.json；白名单提交push后继续真实资料任务，不重跑未受影响页面或旧151批。仅清掉本人04测试venv及04/05可重建build-source，保留冻结源/安装包/当前05环境/全部原研究与证据；有逐项清理回执，不清未知文件。
- 原归并已失败，必填schema/31资格与提交已完成，等待88768的实际终态后核最终摘要；不轮询/重派或重做研究。M2初稿已返回而未封存；原同模型会话正补齐中国资料，详情见下节；95%未验收，其他分支继续。
- M4旧endpoint-family registry只是待核历史参考；宽泛easi score直接标“变化”等可能失真，不能机械移植成科学共轴或新字典。以完整观察语义和实际来源推进，不因UI组件改善宣布完整前端/医学/项目交付。

## 当前提交合同与参照核源

- 输出合同01 manifest1885fcde212bc0c0df43896424e22f4e2222bff559b96adb9f5db98b4bce2195；2RED/7PASS后69相关PASS、一次完整v2 1692PASS11.03s/Ruff/10JS/208Python600-80/272输入不变。仅明确usage达到上限且选中提交对象不完整时，沿用既有同模型同输入一次8192→16384输出恢复；保留tool_calls实际结束原因，合格提交不重做，不增加Agent4步或新路线。三摘要Skill明确完整字段及选择性读取。未跑真实失败包，不宣称恢复已成功。
- 三病参照原41/recovery129文件均SHA匹配，6关键词分页集合/464、97、71唯一CTR无遗漏或重复分配；1266条字面引用核对0错误、NCT China location及CTR原行标记0错误。不是完整科学身份/创新资格接受。source-type审核前两次仪器误将CTR文本按NCT JSON处理，原失败保留；准确分类后的私有receipt另存、不覆盖。
- 新C03只读身份挑战11363已preflight零警告并启动，48turn/7200s；新上下文只看独立源、不看生产候选，与原采集不是同会话续跑或重置128turn预算。主路同Grok有模型族独立性限制，实际模型/结果待终态；不进度轮询或预判PASS。
