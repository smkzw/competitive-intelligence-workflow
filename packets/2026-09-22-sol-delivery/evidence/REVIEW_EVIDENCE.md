# 本轮实证与限制

日期2026-09-22；主线程Review，不修改产品代码。初始HEAD5ebbc8785143758981c0260e1600d6ff32b70b80；结束观测2df24bb441e555f20b233ad2011b4ffd3610655b。中途仅runbook70外部提交，主线程没有commit/push。关键hash/清单见baseline.json。

## 1. 专家包与远端

ZIP SHA256 57685eb33425072c9ecb84525d7a57ef61706fc3a3c06486dfa4e1979973d31e；11个常规文件安全解包，无脚本执行；checksums声明10文件全部匹配。
gh核验origin、repo/main/commits、PR全部状态列表、Actions run、Release；仓库public，remote main与结束HEAD相同，未观察到PR/Actions/Release。不视为CI通过。
git tracked文件按目录清点，src256、tests275，详见baseline。目录数量不是逐文件审核证明。未触旧中文工程。

## 2. 定向pytest一次批次

命令见ACCEPTANCE第4节。4个文件，40项：**38 passed, 1 failed, 1 error in 12.24s**。未跑全gate，不继承1054+2旧声明。
失败：
- tests/contract/test_page_catalogs.py:98，test_a_b_c_page_catalogs_freeze_every_v12_responsibility_without_top_n；C目录多evidence-limitations，与冻结expected_ids不一致。
- tests/contract/test_bundle_scientific_closure.py:151 fixture安装error，install_bundle→fresh_install._provision_runtime→_runtime_probe→verify_package→_verify_asset_manifests→_verify_digest，portal.css文件摘要不一致。不是skip，不是测试assert通过。

关键原输出：

    FAILED tests/contract/test_page_catalogs.py::test_a_b_c_page_catalogs_freeze_every_v12_responsibility_without_top_n
    Extra items in the left set: 'evidence-limitations'
    ERROR tests/contract/test_bundle_scientific_closure.py::test_isolated_install_imports_scientific_review_entry_without_source_path
    ci_workflow.application.fresh_install.FreshInstallError: 独立运行环境 metadata/资源校验失败
    ci_workflow.cli.ContractError: 文件摘要不一致：.../assets/portal/portal.css
    1 failed, 38 passed, 1 error in 12.24s

此为工具输出摘要而非另保存的完整终端日志；W00若需严谨base/head归因，应一次保留两边完整日志。不得声称本轮已完成该对照。

## 3. 浏览器一次现成候选抽查

Playwright CLI，现成abc-v106/A/v1/html/matrix.html。file协议工具限制，改用本线程只读127.0.0.1:18762临时HTTP服务，无产品服务器修改。检查结束已关闭浏览器与该监听进程。
1280桌面、390×844手机均document.scrollWidth不超innerWidth；console观察0 error/0 warning。实际看过两张截图。**仅基础排版抽查，不是四视口/两浏览器/全部页合格**。
初始真实DOM：默认45产品，绘入3，其余42“不完整公开”；原文数字：
- eculizumab NCT00867932 第12周“疗效192.5%”，安全100%，样本7；
- pozelimab NCT04888507 第16周“疗效0.0%”，安全100%，样本6；
- abp959 NCT03818607 第15周“疗效213.4%”，安全39%，样本42。
这些是**观察到的界面文字，不是本轮认定的真实药物效应值**；恰为需校正的呈现。当前JS tooltip强加%并独立选疗效/安全记录，不能以此作临床比较。
选择“治疗组与对照组差值”后URL有matrix_x=difference、轴标签变差值；上述三点aria-label数值未变，x刻度也全部加%。与无对照回退绝对值的代码相互印证，但各点原始控制组事实仍须在修复包逐项绑定验证。
桌面截图首屏主要是控件，科学图在下方，图头长英文与说明拥挤；手机无页面横溢但不证明全部图内无遮挡。
截图和两份DOM见MATERIALS，hash见baseline。选择器figures=0因该图用DOM模拟而非canvas/svg，**没有把0误报为空图**。

## 4. 独立审阅与方法

一个原生fresh-context只读节点核验F05/F06/F09，未调用旧会商runner。直接生产函数合成输入批次，未跑pytest或浏览器；总结在native-review.md。模型实际版本未由返回元数据证明，故不虚称指定astra或sol审阅；上下文独立，不宣称不同模型独立。
共享CAO检索不可用（URLError），没有写替代记忆库。使用旧只读历史仅定位目标，当前判断以源码/实际产物为准。

## 5. 本轮未做

全仓mypy/Ruff、全pytest、24门户重生成/科学验收、三宿主、完整安装修复、真实来源重新获取、全部页视觉、泄露全扫、基线配对归因、正式发布和旧根退役均未执行。本轮新文档不能充当这些证据。

