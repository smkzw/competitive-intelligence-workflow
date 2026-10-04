# R251–252｜整源对象完整性收尾与无损暂停

2026-10-04；W03/W07/W08阶段收尾，用户要求全量复盘、交接、GitHub保存并暂停。
产品仍开发候选；current/source未晋级、未RC。详见
[完整handoff](../../HANDOFF_20261004_R24_252_PAUSE.md)与
[复盘](../../RETROSPECTIVE_20261004_R24_252.md)。

## 原因与真实修复

R249同审阅者终态727.638s/39测试/REVISE，真正执行四种误通过：整primary
对象消失、干预只一臂标签、给药只一队列、身份仅studyType漏源phase。
R251生产4RED/1正例→212相关PASS28.67s；复用既有native抽取，独立枚举
原源path+literal，不以剩余observations自己定义完整集合。每个版本单独证明，
arm/dose需显式bound，原值原文不改、未知不填零、C-v1不改、无新审批。
规则c-design-source-object-coverage-v2。

原source-object RED/GREEN XML在R250工件目录，分别SHA
`8c3e75c00fa81072378d1e575894b173ce14cf9d50859bc0ed8d0c76a3287100`、
`46111953ff013378244abd7218854dcff346030ad46cc8282f466d523a9743dc`。
当前fresh_c源码SHA `204510115f9a378ca2a9371f22c62892a081efa3fed4d7188f638e743932b97f`。
冻结22manifestSHA `3290643e46b3e1dd758289bedeb39cc5b30bc21e62a029d53dcf4bddaa8c2848`。

独立same-session实际PI/openai-codex/gpt-6.1-sol/high请求，270.042s/rc0/
no fallback；22/22冻结与当前字节，21pytest8.88s＋四额外关系/阶段/跨版本探针。
ACCEPT-bounded四故障，没有新已证明误通过；不是第二独立模型或医学全部接受。
报告SHA `483dfd4ded5399d4bd32a907973dcf2e87537e927eddb273d583e899a8d80190`；
raw日志SHA `e86f87d3e66427d44169b454b06b53bff3c51cca2962d25d21a2e9d37315ed48`。
原R242/R249 REVISE留存，generic方案适格、absent/NA、临床关键角色、原关系
科学证明、finite source-set与发现闭包仍开放。无在途QA/进度轮询/延迟重派。

## 最后一次当前门、提交、包与安装

真实GATE_OK quality-only六步：Ruffsrc/tests/tools、strict272src/tools；
1117活跃125.56s/20deselected；20保留compat smoke1.01s、非全保留轨；
7分层0.30s；英文根禁止旧运行依赖。不是全integration/科学/浏览器/24/RC。
日志 `.artifacts/r24-252-phase-pause-20261004/quality-gate-v1.log` SHA
`6bc904449a0c1504306c3b2b7baeb90bfbee21dca0b415ba6c1da562879dd263`。

明确293产品/测试/资产文件已提交 `22f5bbc1b31b3c74898262bd696863b7ccf053df`。
初次staged diff --check报作者原SVG的89行CRLF，不改 normative SVG字节或hash；
用明确cr-at-eol格式规则核全部staged，其余空白检查通过。源/测试静态门真通过。
保留5项历史dirty，不push raw/private prompt/routes/context/logs，无git add .。

新392文件包SHA `5c1ba59b7f127943d3155184a5c9324c91bbe9bb8a75ca8fb18388f7062e784d`；
manifest `d7dd47b5eceba4075c1220fcf6d319a5b554fc3cbee95cbe9a0b0109616c1d66`。
verify required-v12真通过。嵌入source_commit空：不是干净RC包，外部字节清单
绑定当前工作树与源码commit，禁止继承R250安装为当前通过。

实际隔离安装393记录；-I -B安装python/安装cwd、清环境影响，当前模块SHA与
作者相等、未导入开发src。完整正例PASSED，四删减BLOCKED，无PDF/PPT交付依赖。
runtime-probe SHA `8d502d294a2baf9cbe02b7475201187863605b493e799e821ada7353ecd13839`。
accepted只是测试假设，不是原源科学采用/当前报告接受。

仅删除本次新安装可再生uv缓存1376文件183.4MiB；清后393记录与metadata
不变、layout/import成功。cleanup SHA
`a8acbe9a20adb54c825262d16f1e2e704512a0a23fddf027ca7d28637eddb88e`。
未测实际APFS物理释放量；来源/候选/失败/恢复/用户改动/会话未删。

## 保全与分层未完成

[机器检查点](r24-252-pause-checkpoint-v1.json) SHA
`5934155e1413a154231fc4c3172559cb649398e7986473ec386493a2ace0e0d6`：
293源码与Git实际相等，392包作者字节相等，10关键工件hash，5历史保护摘要。
7916 Git可见原路径全存在；本地before清单SHA
`cc690e2b3e50724db10b222730abff814574206367a6202686af0cda1ab22beb`。
 ignored大工件单独绑定，非全盘备份。文档第二受控提交和最终GitHub tip见宿主
交付核验，不在自己正文嵌入自身SHA。原未跟踪raw与私人trace留本地。

Goal实读paused；Trellis status保留in_progress，meta执行paused/未完成。
nativePeirce completed真实核验、所有声明worker/reviewer终态，无下一研究派发。
科学/产品视觉/交互/保存/分享/安装分层：安装五合同探针通过；四源漏失有界审阅
通过；当前完整医学、真实宽屏、全部物理页交互、最新current保存分享恢复、24与
三宿主全模式/RC均未完成。Ego12 NOT_FOUND及既有Ask未答，不能擅换浏览器。
