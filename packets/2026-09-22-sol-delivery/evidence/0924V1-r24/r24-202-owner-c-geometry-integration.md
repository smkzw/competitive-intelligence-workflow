# R202｜主线程接手 C 共用几何及正常入口

2026-10-04 CST，HEAD `c129a575a403ea39027e112c1acd80ca77b43117`。保护脏树；
只改共享/C 资产、复制列表、base 模板和新增回归。Ponytail 最小完整改动；Kangzhe
当前入口与16 owner已核等于本地A04。历史改动不归为本次新实现。

## 执行失败与路由声明纠正

kernel18004通知结束，52892 exit0仅传输/报告格式成功。最后报告没有实施/读取/
工件/工具检查，错误请求新Trellis授权；用户已有授权充分，不重开问题。
报告 SHA `dfb8b3d4142f14a83b38098f5871bdd7d8dfeac1bebdf1a21f68e848ef1b8d97`。

**owner先前“no fallback”声明不实**：可执行任务manifest实际含回退链，文字没有
禁用链。runner报三次同CodeBuddy session、ZCode exit1、最终PI/openai-codex/
gpt-6-luna session `01a103de-824f-7000-89ca-5a9e82f042ee`；最后报告承认回退。
不把外层agent/model当最后响应身份；实际响应身份未独立观测，不把同会话尝试
算多位意见。原route manifest SHA `e24ec8d1eac760f478cb241159a1b3b207483d223e3f158cd999b71f838a6d86`。
这是owner配置核验遗漏，已更新对应review/metrics；不修改全局路由。后续派单须
核实际可执行链，不能仅写声明。R199仍在途，其实际身份/链终态另核，不能继承声明。

## 整族修复与检查范围

四真实RED：普通C包缺charts.js、共享脚本注册第二控制器、20→2不缩、空画布300px。
RED XML `7a91327fd32b5cdb9ccc2f5a3995e3bf5d4493d2d8e97b44be8ff2072150271a`。
复用presentationPlan，C提供实际ECharts坐标/glyph数/绘制标签行数/轴边距，不造
临床数值、不按长原文撑高、不建第二框架。稀疏4/6/8列，复杂12列；密集类别不
硬裁到数值卡420px上限。空结果auto/status，不改成未公开或0。正常C先加载共享
脚本再C，共享脚本仅提供纯planner，不清空C模块/注册重复控制器。长条款仍文字
横比，完整row/source/query与A/B无design_layout分支保留。镜像仅机械同步。

首批6文件39PASS；最终12文件C/A/B/planner/不可绘/当前bundle合同67PASS/5.59s。
GREEN XML `ac9bfa3dbf43cf775dd9d2a56f206c7d54faf691533ccfc328f180efe4f4a338`。
新测试 SHA `da7ef79583bc69313b76b1e2eef83ce4de0fd164dae930508b21be3d764d8946`。
Ruff初次新测试两长行FAIL后格式修复通过，strict-mypy report_c.py一源通过。
Node生产调用/静态CSS/普通生成不是浏览器视觉验收。

## 当前字节、真实候选与安装

| 实物 | SHA-256 |
| --- | --- |
| 作者charts.js | `c3b848a280c5c8d23a596d29f1587da4e67b46915b1b256187b2e1bf3124e99f` |
| 作者report-c.js | `3b56013851872c4404f001903ea9c904699b21917506168e57ceb82329cd3fe9` |
| 作者report-c.css | `25544e1af61c4813e74c4cb34d24229284ec1304792915fb4147cd90759737c6` |
| C base.html.j2 | `dc7a51f08bd6c9b0821b1e30013477937a9e44b5cb9e35d4448cc176d48e6fda` |
| report_c.py | `71b62655ba21c0340bdfd385a3cfe19f548fccaf860fb755df69e7434944df40` |
| 镜像manifest | `e827f7c713895b4c5dc1a89f743087cebf63b21c5a641104e11c2095903c36c1` |

固定真实192输入 `944f2724e5c769cd0a7418f9dbb07c770b1debd5eded89b7effc83c5f504ba2c`
经render_report_c_site(review_candidate=True)新生成14页，原输入不变，仍待复核/
冲突保留/current不切。全部本地script可达/顺序正确/三资产等作者镜像。
实物 `.artifacts/r24-202-c-shared-geometry-20261004/owner-real-candidate-v1/html/`，
回执 `77131f202436ac76812bc96e29a21ced1b2daf681e61bdd94a3870d5e8d568cb`。
初次private replay误把review_status当数据字段，AttributeError/尚无输出；纠正
既有candidate API，非正式门放宽。一次ci-workflow install --help也调错入口exit2；
实际采用生产tools/install_bundle.py成功，不把owner命令错误当产品缺陷。

同目录stable-gate-v1.log `2cf9e7fdf0357d0b1d96919bbab2feabe0825bfac54afb1a2e6f410c09a3a3a4`，
66902 exit0：Ruff src/tests/tools、strict271、1117活跃unit/contract、20保留兼容
smoke、7分层及旧路径扫描；quality-only，不含全integration/科学/像素/发布。
201/203 PubMed和当前C源均在这个新门，不继承旧1117日志。

新HTML-only包 `bundle/ci-r24-202-development.tar.zst` SHA
`3fbafbb11d6fdc060a879b30ed2e48e28ff8912dd6fd6ad90b9640ed5bd128db`，390作者文件；
manifest `a3b5d452a67665f4de437fedc4183a40d2f42e93e4328c13c0f045c5a21b4ea4`。
真实fresh-install-v1的391记录逐hash/size相等；3安装内检查（help/package verify/
合成宿主完整阻断恢复回执）通过，回执 `4b6f8dda42c04ad99edda1b784e4091167c80a70912fb9ac5987afeb52683737`。
本地shell替身不是真实模型/三宿主全部模式。安装包不含原文/缓存/运行证据。

仅新runtime/cache用native uv离线清理；统计1350文件/192280630字节，uv报1376条目
183.4MiB，不等于物理释放量。清后391 release SHA/size/mode、metadata/入口help
均不变。缓存可重建，源码/历史来源/失败/会话不删。回执
`44b8434c0eae423f4510403736d07dff790380aa796c8b4ef7bc32c9415da35d`。

## 未验与下一步

仅R199终态后QA/真实身份核验/独立source-first会商。AD R204只是元数据，不是全文/
医学或全球中国宇宙闭包。Ego/论文当前可得见证扩展/药智/C补充策略Ask仍待答。
新14页/四档四状态/新浏览器离线分享NOT_RUN；不宣称审美接受。24门户/三宿主
全模式/Publication/科学/分享/恢复/RC未交付。Goal active，无pause/current晋级/
提交/push/旧根接触；连续实现，不人为阶段暂停。
