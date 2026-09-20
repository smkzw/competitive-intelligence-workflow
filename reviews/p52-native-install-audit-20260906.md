# P5.2 原生只读工程审阅：有界交接

日期：2026-09-06。工作根仅 `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`。
方式：当前线程直接审阅和隔离测试，不派发、不运行旧 runner。未修改工程源文件、未提交、未创建 Goal、未访问旧中文根、未改真实宿主配置。临时产物保留；安装器自身的失败回滚由测试触发。
结论：已有可实际运行的独立安装实现，但不能据此接受 P5 全部完成；存在一个恢复入口 P1 和一个完整性 P2。没有发现已证实的 P0。本报告不是产品、医学或发布接受。

## 1. 当前实现

- fresh_install.py 全文 850 行、host_smoke_runner.py 全文 426 行及两个指定测试文件已审阅；实际 bundle 工具为 build_bundle.py、bundle_contract.py、install_bundle.py、verify_bundle.py。另读历史 source-set verifier，其明确只证明 dirty-baseline，不能当作当前 HTML-only 发布来源集。
- 每安装根通过 uv --no-config sync --frozen --no-dev 创建 runtime/venv；去除 PYTHON*/UV_*、VIRTUAL_ENV 等环境输入，项目 editable 指向已安装版本 src。实测安装环境含 26 个发行包，无 pytest、ruff、mypy；未借用开发 venv site-packages。
- 启动入口清除 PYTHONPATH/PYTHONHOME/CI_WORKFLOW_PYTHON，使用 -I -B -S，在 site/.pth 和项目导入前验证引导摘要与发行文件集合。发行普通文件的字节、大小、模式以及额外/缺失文件和目录检查已实现。
- 同摘要重装会与原归档比较发行字节和权限。入口使用 hard-link 无覆盖发布；捕获失败时仅回滚所记录的新路径。现有失败保全和竞争入口测试通过，不能外推为掉电/SIGKILL 或任意外部写入竞争下的事务保证。
- 移动后的安装被明确拒绝，并要求新空根重建；实际移动负例通过。发行包可搬运，安装好的 venv 不可移动。基础 Python 3.13 可只读复用 uv 管理安装；首次依赖下载需要网络，非离线包。
- 当前补测包共 338 个 manifest 记录，CLI catalog 15 项，包含 research fetch-ctgov。已列举的非 HTML 输出组件不在集合内；PDF 输入解析依赖保留符合正式设计。只发现通用宿主查找路径和检测 /Users/ 的测试串，未发现用户开发 checkout 绝对路径。此扫描不是凭据内容的全面审计。

## 2. 问题与最小修订

### P1：resume 在进入恢复流程前被非空目录检查拒绝

位置：src/ci_workflow/application/host_smoke_runner.py:143、252（两个共享问题点），CLI --resume 在 359 行。

复现：临时 project 写入 sentinel，传 resume=True 调用 run_installed_single_host_smoke；只替换 layout.verify_layout 为无操作以隔离前置分支，不替换恢复判断。返回 HostSmokeRunnerError「宿主项目目录必须为空」，sentinel 保留，尚未到达宿主派发。三宿主分支的同型判断由全文检查确认。

影响：已有中断项目正是非空目录，官方 runner 恢复入口无法走到下层 --resume；新装成功不代表宿主恢复成功。

最小修订：仅新建模式要求空目录；resume 模式要求已有项目并先验证其项目/case/bundle 身份，再交给下层恢复。两个入口一并处理。补成功恢复路由、身份不符拒绝及新建非空拒绝三个分支测试；无需增加编排框架。

### P2：load/启动未完整绑定引导集合和权限

位置：src/ci_workflow/application/fresh_install.py:411（引导锚点只记录 hash）、455（目录仅记录名称）、481（入口仅比较字节）、486（引导目录只查类型）；518 的 0755 检查仅在重装写入口路径执行。

真实独立安装复现（probe.py）：分别把 bootstrap/fresh_install.py、installation.json、bin/ci-workflow、versions/<digest>/src 改为 0777，每次 load 均 ACCEPTED，入口 --help 均退出 0。恢复原权限后新增 bootstrap/extra.py，load 和入口依然通过。发行普通文件模式漂移测试本身通过；缺口在引导文件、入口与目录。

影响：当前实现不能宣称覆盖完整 bootstrap 额外文件和上述权限漂移。未证明新增 bootstrap 文件获得执行，不能把本发现写成已验证任意代码执行漏洞。

最小修订：对固定 bootstrap 文件集合及入口执行统一 lstat 类型/模式/字节检查；为受保护目录定义并验证模式。安装、load、启动复用同一检查语义。依赖/cache 目录继续遵循已有独立边界，不扩展成逐依赖签名沙箱。

### P2 风险说明：构建后端未完全锁定

位置：pyproject.toml:21，fresh_install.py:349。uv_build 要求为 >=0.11.7,<0.12；uv.lock 没有 uv-build 条目。运行依赖版本和归档 hash 已锁定，但 --frozen 不能证明构建后端也逐字节固定。

最小修订：如 P5.2 的锁定声明覆盖安装构建过程，应固定并记录构建后端版本/约束及构建工具证据；否则安装文档明确限定为运行依赖锁定。未实测不同 backend 产生不同结果。

## 3. 检查结果和版本边界

- 两指定测试文件：39 passed、1 skipped、1 deselected，373.04 秒。早期 bundle 为 14 项时期的快照，不外推当前 CLI；安装实现 SHA 全程未变。
- 用户更新后重新构建 15 项 CLI 包，test_fresh_install.py：8 passed、1 skipped、1 deselected，12.71 秒。覆盖包集合、安装拒绝覆盖、package verify、no-draft、补件恢复 HTML、隔离能力声明一致性。
- 两轮 skip 均为 tests/hosts/test_fresh_install.py:643，真实宿主授权开关显式设为 0。deselected 均为 archived_real_host_receipts：主动不追溯历史归档路径，避免越出本轮隔离范围。没有任何真实 Codex/Hermes/OMP 通过结论。
- 另从新包的独立 installer ZIP，在临时目录使用 uv 管理的基础 Python 3.13 -I -B 安装成功；清除开发环境后，再投毒 PYTHONPATH/PYTHONHOME/CI_WORKFLOW_PYTHON，package verify 和 research fetch-ctgov --help 均退出 0。没有调用实际 fetch 或真实宿主。
- 单独完整性反例：4 个模式漂移和 1 个额外 bootstrap 文件均被错误接受；恢复入口反例被提前拒绝。
- 未测试：真实宿主会话/账号、生产安装、离线/全新机器无基础 Python 下载路径、Windows/Linux、掉电恢复、医学/科学接受和浏览器视觉接受。测试中的 HTML 产出检查不是视觉接受。

15 项候选归档：
`/tmp/p52-current15-7fw93jtp/candidate-bundle0/dist/competitive-intelligence-workflow.tar.zst`

归档 SHA-256：`b1a5c051ce4d65790c4f9f883ecbd017b1e435596936940271364f50955f3a19`

manifest SHA-256：`8c1548db61a3204900a07661ea446c35ed10c753aba30a3ada69b9a026457b48`

构建后检测到明确并发漂移：包内 cli.py 为 `e9d38a86c5c86084821c0049571c698c61f164c7e60f6112cc2e9e51ac6d0b43`，末次源文件为 `bd814cf915914676c1f160b264129e5cf7a8d9672c9936f9f38686e8f9a68648`。末次比较中其余 337 个 manifest 记录与源相符。因此本包仅是已测试的 15 项切片，不是最终当前源包。

审阅文件 SHA-256（开始/结束一致，除上述并发 CLI 外）：

```text
43b0119625a738f4d1e8ea13feef2be3bb1022d1ed8c8cbe0997855c60e4ec37  src/ci_workflow/application/fresh_install.py
83d22be9ed715ecc7af71d00957ef20fba3ea3c6a35a644fb27ba5d81e8cf5a8  src/ci_workflow/application/host_smoke_runner.py
92058335466d6e4ce7925fa30dd08f0220398e0e80a838df9e985e204aecace7  tools/build_bundle.py
2da3d388f563e8f1ff7b961e340cff58533dc7f68c01bdc077947cf72971efad  tools/bundle_contract.py
cddda5a3e66b75135877f86acad5be16f43a86bf68388a5dd160fbef7b214273  tools/install_bundle.py
31d6a1ddf31dc8c6fd282d3d83d6e1e71985d23a8411e32e4842aa7b45b1fc30  tools/verify_bundle.py
3609c53c4196dbc49848e236483052298b191bfabc162b74d0bb5483e470452b  tests/hosts/test_fresh_install.py
56558d22424f474f6e17cb76455bb94e0e39818e286c1e61309739e7d7db5420  tests/hosts/test_fresh_install_integrity.py
41baaba57626934ea4f816a5ca5566aab092f1ae2cdabf151e51db8b801963fe  docs/user-guide/install.md
f8195d5b7e591de4cb36398fea799bc874131c9b0860704c41f97fd8e0ef9435  pyproject.toml
21ec076831667b407c7fd57bd46e10e0c2724d2a7a439b81c361fea2e5147db8  uv.lock
facdc54cb92fba350b4e519ff7db6e7e7a3a5499d4dd74a53bd43bcfd677434d  package-manifest.json (15-item bundle)
61cd542582bee48ef3d1b656b9470e868036359be5670576534a6d21b28966c5  schemas/package-manifest.schema.json (15-item bundle)
```

## 4. 可恢复接续

主线程可继续原来源/图表工作，无需等待本审阅；本线程无未结束测试进程。由实现者处理上述恢复分支与完整性反例，再在最终源集合稳定后重新构建 bundle 和独立 installer，重验两文件和当前 CLI，记录源集合/归档/安装器摘要。真实宿主门保持未完成，按原授权范围另行执行；本报告不产生新的生产授权。

保留产物：本目录 probe.py（旧切片反例）、current15.py（15 项独立分发安装验证）、bundle/、install/、current15-trusted-installer/、current15-standalone/，以及上述两个 pytest 临时根。脚本含本轮固定路径，重放应替换为新空临时根，避免覆盖已保留的证据。
