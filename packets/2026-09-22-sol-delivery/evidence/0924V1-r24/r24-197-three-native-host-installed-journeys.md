# R197：同一冻结包的三宿主真实安装后流程

HEAD c129a575a403ea39027e112c1acd80ca77b43117，脏树完整保留。
Goal active，连续实施；不是暂停点或RC。执行方式为owner调用现有生产宿主验收器，
每次使用安装解释器与独立项目。没有额外代码作者/主席，确定性回执核对不另派模型。
所有长任务只确认启动并等kernel NOTE_EXIT后读取，不进度轮询/在途QA/迟延重派。

## 固定版本与真实结果

冻结HTML-only开发包81ad355c4d32aff60fb96b2d233acf8fe8fbf23a9b2e0570714f8e04ec16058a；
390作者文件+生成manifest1，fresh-install-v3实际391记录逐字节相等，
安装内完整恢复回执回归也通过。版本/质量/重建资料见[196](r24-196-installed-receipt-resource-closure.md)。
当前开发门1117活跃、20保留smoke、7分层、strict271/Ruff/旧路径，quality-only。

实物均在.artifacts/r24-194-linked-jats-boundary-20261004/，以下相对此目录。

| 宿主 | 实际运行 | 成功回执 SHA-256 | 独立运行证据 |
|---|---|---|---|
| OMP18.4.9 | 44839 / PID58689，exit0，160.828s | 62c6ba5138361cbdbed9c8c5616fc0c47d20641c4c1f3e18afbabd1756b8b7d5 | real-host-projects-v3/omp；real-host-receipts-v3/omp.json |
| Codex0.159.0-alpha.12.1 | 78289 / PID59520，exit0 | 86a76c3b695ddc0bd5f579cec0a059d646c59fbe27b61fe3d2c5d4a4a965ff47 | real-host-projects-v3/codex-bundled；real-host-receipts-v3/codex-bundled.json |
| Hermes0.21.5+3698.g6f7a799.dirty | 57039 / PID60067，exit0 | 5ddf7cc9ae6dab07fbece62f3e6d0b11479c1a4ca61dc9fda4687a9c6108ee34 | real-host-projects-v3/hermes；real-host-receipts-v3/hermes.json |

三者各19事件，实际公共安装Skill、能力预检、缺关键证据时零草稿、同项目补件重开/
重新绑定、HTML生成/项目验证和严格生产回执深核通过。owner在同一安装环境调用
verify_host_smoke_batch，三个verified/no rejection/real_host_pass=true；会话、外部
进程、run分别独立且PATH解析，不是同进程伪造。批次实物
real-host-receipts-v3/batch-owner-verified.json，SHA
2e34e3114ab627f506770d988fcfc13f1276e247d9c2e54fd154ae0d17800875。

## 模型请求与身份边界

三次均明确请求gpt-6.1-sol/high；OMP与Hermes提供方为openai-codex，Codex为openai。
没有auto/default或暗换模型。OMP当前目录支持精确选择器，但本次没有独立的响应
模型记录，不能把请求写成实际模型认证。Codex实际child
01a103bd-914a-7d90-b6b2-a1d582e9a2c6的只读turn_context与本次codex-bundled项目
精确匹配，model=gpt-6.1-sol/effort=high。Hermes实际session
20261003_235032_1c7f8b只读原生库记录model=gpt-6.1-sol/billing_provider=openai-codex/
reasoning_config.enabled=true、effort=high。这是原生会话配置观测，不声称服务端内部证明。
原生历史库/记录不修改、不复制私有全文或凭据到资料包。

## 保留的失败与真正根因

- R195前两次真实OMP失败分别为内部合同直接塞入公开Schema、默认包漏包内Schema。
  原项目/包/hash不改，不追记PASS；修复及测试见195/196。
- Codex37357的PATH CLI0.153.4真实exit1/HTTP400拒绝请求模型，无manifest，不计通过。
  当前应用实际自带0.159.0-alpha.12.1，新缓存列出精确模型。以进程限定PATH选择
  已有bundled CLI、保持同一model/high重验后成功。没有安装更新/改全局配置/登录或换模型。
- Hermes未采用其cms-model/cms-smk默认配置，显式选择器转发到原生运行；无凭据处理。

## 本项不覆盖

这是每宿主**一个合成fixture**的真实原生安装后旅程，不是实际适应症自主研究、
三宿主全部模式/科学复核能力/刷新与快照一致性、整项目恢复、医学/视觉/24门户或RC。
当前三个宿主流程切片已经接通，不再概括为“三宿主完全未跑”，也不扩大为W08整体PASS。
Ego空间恢复和C补充论文政策仍待用户Ask，前端真实宽屏验收不绕过。
该下一步已由[198](r24-198-installed-current-share-chain.md)实际完成安装内隔离操作链
和分享静态核验；新浏览器/医学/整产品仍未验，不切用户旧current。
