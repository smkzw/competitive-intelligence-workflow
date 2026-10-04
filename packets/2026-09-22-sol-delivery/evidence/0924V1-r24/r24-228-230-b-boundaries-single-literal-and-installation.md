# R228–230：B 阅读边界、真实页面减重及当前开发安装包

现行 W05/W07/W08 工作，不新增产品权威。共享源码由 owner 单写；两项确定性
根因各自先成族 RED，再做最小完整修复与相关批次。两项稳定后集中一次开发
质量门及隔离安装，不每次修改/私人资料重跑全仓，不要求用户测试。

## R228：首页不能替尚未完成的研究签字

原普通 B 首页固定声称“宇宙按登记检索全闭包”“基线信息完整”“数值可回溯
登记来源”和必有同组风险分母；这些结论无法由输入载荷证明，R225 实际仍有
10 项遗漏、来源缺口。现在仅说明本资料包列示的产品/研究数量，逐条查看定位
状态，分母缺失不补算比例，相关研究保留不等于共轴或头对头比较。

四种普通入口载荷：一般、缺分母、部分来源、结果子集。首次私有测试路径
层级错误导致 FileNotFoundError，保留 red-v1，不当作产品 RED。修正路径后
red-v2 为四个实际断言失败；完整修复后与两个相关集成文件共19PASS/2.33s。
未修改来源、数值、历史候选或科学状态。

## R229：减重不能隐去记录

R225 B 首页实测34,747,014B：图表18,884,665B、来源8,460,473B、筛选/上下文
6,997,176B。1,553个组、3,811条行出现，不用固定 Top-N 截断以假装精简。
根因之一是每页重复保存 FILTER_ROWS 和同一批字段的 B_ROW_DIMENSIONS。

模板现在只嵌入一份筛选数据，在消费者加载前同步建立同字段索引；使用
null-prototype 字典，普通/特殊/中文 ID 都保留，未引入异步请求或新框架。
四例普通渲染+实际 Node 执行得到四RED；修复后两新文件与相关门户/事务
集成共23PASS/2.84s，Ruff三文件与strict-mypy一个生产文件PASS。

新私有候选由同一真实 PN 冻结输入通过普通 renderer 生成，**全部101物理页**
逐项比较 snapshot、row-set digest、filter rows、chart groups、evidence views，
均与R225相等；首页/安全页/真实试验页的索引再实际 Node 执行确认全部字段。
总大小188,445,637B→170,809,446B，减少17,636,191B（约9.36%）。原R225仍保留，
没有更新其hash或将其缺口改为PASS。新候选仍是44/54研究，**不是完整B宇宙**。

新site SHA：52af6bc7c0b7650b09a3a48262e51fa4ca46d83d4ccbe0ee5809fd2cf2a6054f。
输入：ba01c0e8137e439a6796bba8cee74f1cfd65541dd46d5f8def21f597498f7998。
生产B renderer：724543edcaa72c5953f26272faf04aad052b5fcb7404798740f2406281c37a92。
B模板：bbf4ec28cf37190ee1306d7b2346c0832c7fc7091ab7197a20ec38f28de92aee。

## R230：当前字节集中开发检查与安装，不是RC

package_v1.py 实际99100终态exit0，allowlist全部390源文件在质量门前后及
构建/安装后字节不变。Ruff src/tests/tools；strict-mypy src/tools；活跃unit/
contract1117PASS/97.56s；保留轨有界兼容20PASS/0.71s；分层7PASS/0.18s；
旧路径仅文本检查，不触碰旧中文目录。GATE_OK status=quality-only。

实际开发包e1e1d6b6c9a22737482ece3810932768876cefcdfade84c47df6fed86deca993，
390清单源文件、391安装记录（含bundle-manifest）。dirty开发源，不声称clean
RC commit或正式冻结。完整包校验、全新隔离环境metadata/import/resources及
实际旧兼容探针25检查均重跑通过，并非继承R218回执。

另用安装内Python -I/-B实际生成28页合成B，确认范围/缺分母说明及特殊ID索引；
同一安装内运行C primary/secondary×absent/empty/null六例，未知时间窗局部
未决、不丢正常观察。此项78947exit0；不等于真实浏览器或临床批准。

仅清理本次已完成安装的显式 runtime/cache，uv实际移除1376文件/183.4MiB。
391安装记录、metadata、入口仍不变；venv、原件、候选、失败、logs、会话均
未删。APFS硬链接可能共享存储，未测量实际物理回收量；cache可由锁文件重建。

| 实物 | SHA256 |
|---|---|
|R228真正RED red-v2.xml|db9f75b2f85c8fb708a679f964a37aaaa86faa469c504b7e91d5c48d1de23bc8|
|R228邻接green-v1.xml|e07970786766bc09cc813c4b2c82882f4a2b69f751a328c34bd83f13b1563983|
|R229成族RED|56be78e9e5a085932e796ee71a44f9537ab09a44eac6adab2cc27705707f4778|
|R229邻接GREEN|283b7764e4ed2c9175cecd3decc25af13b92990e33164c624615f8619aba514f|
|R229全部101页重放|3632a47cf616a8af5ae46eb6457fa60308be6bf2121ad05fb9daa9c863651221|
|R230集中quality回执|193b0ad180a6d5ae87cafdea0f4f6fcf3d6c690b657e45370a60d7f1df25767a|
|R230实际bundle回执|dd14e38ec393e35c3fbc41693ea41bf1f2932cf034ba047027bbf44d18095da5|
|R230安装及兼容回执摘要|374e02aa30f192aab55458acd589872e9889f2e88431568457b9ed46de5253ad|
|R230当前B/C安装内行为|74dfc020f27508e6ca0c1e37f8b278c230b70f849683c8a28f2d4bda7c76ce51|
|R230显式cache清理|47cffce71c27bcf0e00b7f8adbfe147ed0fee86205e7381de12bf6e82addb251|

私有实物根为 `.artifacts/r24-228-b-overview-evidence-boundaries-20261004/`、
`.artifacts/r24-229-b-filter-single-source-20261004/`、
`.artifacts/r24-230-stable-candidate-package-20261004/`。脚本已运行的输出不覆盖。

## 尚未完成与下一动作

227全PN来源资料修订仅等既有kernel12176 EXIT后收31281，再核实际原件/hash/
角色/完整集合/模型身份，不能在途QA或延迟重派。随后推进普通B/C完整相关池、
合法消费者/当前事实保存/分享与完整来源资格；不能以本次减重或安装代替产品。

真实宽屏1440/1600/1920/2560×四状态、全部页面目视/焦点/联动仍NOT_RUN；
Ego12既有Ask未决。独立医学接受、全球中国闭包/必需论文、24真实门户、三宿主
全模式、当前分享离线新浏览器与最终恢复/RC仍开放。HEAD c129a575…，无新提交、
push/current晋级或暂停，Goal持续active。
