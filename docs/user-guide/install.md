# 竞品调研 Skill 安装说明

## 你需要做什么

首版只生成 A、B、C 报告的**站点式 HTML**。输入“竞品调研”即可用一句话启动自主研究；可选提供适应症、报告类型和历史截止日。未提供报告类型时，宿主原生 Ask 会先用简短中文说明 A（全景）、B（临床结果）和 C（设计比较），再让你选择。

## 1. 构建并校验候选包

在本工程根目录执行：

```bash
mkdir -p dist
uv run python tools/build_bundle.py \
  --output dist/competitive-intelligence-workflow.tar.zst
uv run python tools/verify_bundle.py \
  --bundle dist/competitive-intelligence-workflow.tar.zst
```

第二条命令必须输出 `BUNDLE_OK`。它会校验 `.tar.zst`、外部 SHA-256、逐文件清单、唯一 fixture catalog、包内 Schema、Skill、Policy、站点资产和设计合同。失败时不要继续安装；保留失败输出供排查。

## 2. 安装到隔离候选根

接收方不需要源码 checkout 或开发 venv，但需要 `uv`、`zstd` 和用于运行
bootstrap 的 Python 3.13。默认构建同时分发 `.tar.zst.installer.zip` 及其
SHA-256 sidecar。先通过可信发布渠道核对安装器 ZIP 和候选归档的摘要；
同目录的 sidecar 只能检错，不能单独证明发布者身份。安装器不能取自未验证候选包。

脱离开发环境的安装方法（以下均为临时候选路径）：

```bash
unzip competitive-intelligence-workflow.tar.zst.installer.zip -d trusted-installer
python3.13 -I -B trusted-installer/bootstrap/install.py \
  --bundle competitive-intelligence-workflow.tar.zst \
  --expected-digest '<可信发布的归档SHA-256>' \
  --root /tmp/ci-candidate
/tmp/ci-candidate/bin/ci-workflow package verify --root /tmp/ci-candidate/shared
/tmp/ci-candidate/bin/ci-workflow capability preflight \
  --host codex --reports A --outputs html --json /tmp/ci-preflight.json
```

安装器以 `uv sync --frozen --no-dev` 为每个安装根创建 `runtime/venv`，
按包内 `uv.lock` 安装依赖和项目 metadata；不借用开发 venv。
运行依赖锁定不等于整个构建工具链逐字节锁定：当前 `uv_build` 构建后端仍采用
版本范围，发布验收需另记录实际构建工具版本；不得据此宣称完全可复现构建。
已有 uv 管理的基础 Python 可只读复用，否则在候选根下载。首次安装需要依赖下载网络；这不是离线包。
默认下载缓存位于候选根；测试可用 `CI_WORKFLOW_INSTALL_CACHE` 显式指定隔离缓存。
项目 editable 路径仅绑定已安装的 `versions/<归档摘要>/src`，以保留真实资源布局。
安装时检查依赖版本、导入位置、项目 metadata 和资源，并在构建后重验发行字节。

入口相对自身定位安装根，清除 `PYTHONPATH`、`PYTHONHOME` 和旧解释器覆盖变量。
先以隔离、禁用 site 的 Python 验证 bootstrap/回执和完整发行集合，再加载项目。
加载布局和重复安装同样拒绝多余、缺失、修改或链接化的发行文件；并发安装失败关闭。
`versions` 是严格发行集合，`runtime` 是依赖与缓存，项目状态/预检回执应放在独立项目
或显式输出路径，不允许随意往发行目录写入“合法缓存”。能力缺失可返回预检退出码 5，
这不等同于安装失败或真实宿主通过。

venv **不可移动**：移动安装根后入口拒绝运行，必须从原始、已核对摘要的归档在新空根
重建运行环境；不要复制开发 venv、就地覆盖旧安装或删除历史证据。完整性锚点保护的是
发行文件，并非防御能同时修改入口、安装回执和本地解释器的账户攻击者；运行环境本身
不是逐依赖文件签名的防篡改沙箱。

开发者也可使用工程中的同一安装实现：

```bash
FRESH_ROOT="$(mktemp -d)"
uv run python tools/install_bundle.py \
  --bundle dist/competitive-intelligence-workflow.tar.zst \
  --root "$FRESH_ROOT"
"$FRESH_ROOT/bin/ci-workflow" package verify --root "$FRESH_ROOT/shared"
```

确认 `package-manifest.json`、`fixtures/catalog.yaml`、`fixtures/synthetic/host-smoke-v1/` 和包内 `schemas/host-receipt.schema.json` 均在 `$FRESH_ROOT/shared` 后，使用同一份 bundle 安装到规范候选根。安装器只新建内容寻址版本，不删除旧版本；如果目标根已有其他版本，命令会失败关闭。

```bash
SHARED_INSTALL="$HOME/.cc-switch/skills/clinical-research/competitive-intelligence-workflow"
uv run python tools/install_bundle.py \
  --bundle dist/competitive-intelligence-workflow.tar.zst \
  --root "$SHARED_INSTALL"
"$SHARED_INSTALL/bin/ci-workflow" package verify --root "$SHARED_INSTALL/shared"
test -L "$SHARED_INSTALL/omp/skills/competitive-intelligence-workflow"
```

Codex 和 Hermes 使用 `$SHARED_INSTALL/shared`；OMP 使用安装器创建的唯一明确链接 `$SHARED_INSTALL/omp/skills/competitive-intelligence-workflow`。三者必须解析到同一个内容地址版本。若宿主安装目录不同，只替换 `SHARED_INSTALL`，不要复制第二份或把源码 checkout 当成安装包。


## 3. 运行三宿主真实冒烟

每个宿主都必须从自己的真实安装入口启动独立外部进程，会话和项目目录也必须独立：

命令必须显式携带 `--allow-real-host`；缺少该开关只会返回环境阻断，不会启动宿主。


```bash
uv run python tools/run_host_smoke.py --allow-real-host \
  --install-root "$SHARED_INSTALL" --host codex --case host-smoke-v1 \
  --require-external-host-process --project-root "$SHARED_INSTALL/projects/codex" \
  --receipt "$PWD/docs/acceptance/host-smoke/codex.json"
uv run python tools/run_host_smoke.py --allow-real-host \
  --install-root "$SHARED_INSTALL" --host hermes --case host-smoke-v1 \
  --require-external-host-process --project-root "$SHARED_INSTALL/projects/hermes" \
  --receipt "$PWD/docs/acceptance/host-smoke/hermes.json"
uv run python tools/run_host_smoke.py --allow-real-host \
  --install-root "$SHARED_INSTALL" --host omp --case host-smoke-v1 \
  --require-external-host-process --project-root "$SHARED_INSTALL/projects/omp" \
  --receipt "$PWD/docs/acceptance/host-smoke/omp.json"
```

完成后运行：

```bash
uv run pytest tests/hosts/test_fresh_install.py \
  tests/hosts/test_conformance.py \
  tests/hosts/test_real_host_smoke.py -q
```

三份回执必须符合 `schemas/host-receipt.schema.json`，绑定当前候选包、`host-smoke-v1` case digest、真实宿主版本、安装入口、初始 no-draft 阻断、补件重开事件、恢复后 HTML、事件链、最终清单和真实退出码。`process/session/run` 必须互不相同；包摘要、案例摘要和最终语义状态必须一致。回执归档规则见 [`docs/acceptance/host-smoke/README.md`](../acceptance/host-smoke/README.md)。

## 4. 看懂失败提示

系统会明确区分技术故障和证据不足：

- **技术或环境问题**：宿主程序找不到或无法启动、外部进程失败、网络/浏览器/脚本运行时不可用。提示会说明“本轮遇到技术问题，尚未完成；请恢复环境后重试”。这不是“未检索到资料”，也不会改变已接受快照。
- **关键证据不足**：关键来源、字段或定位材料缺失，无法达到报告门槛。提示会说明“关键证据不足，暂不生成草稿”，并列出已完成的检索和需要补充的材料；保持 `no_draft=true`，不猜测、不补写事实。

三宿主中任一宿主发生技术故障时，其他宿主和已接受科学快照不受影响。未公开值应显示为“未公开”，不能与技术故障混写。

## 5. 首版边界

本候选包的实际交付范围只有站点式 HTML；PDF、HTML-PPT 和 PPTX 不属于首版包、入口或退出门。任何真实临床、监管、视觉和生产验收仍由独立验收者完成。

## 6. Agent 内部采集与恢复说明

普通用户仍只使用“竞品调研”入口，以下命令供 Agent 执行研究节点及排查，不要求用户手工编排。

在已初始化项目中，`ci-workflow research fetch-ctgov --root <项目目录> --condition <检索条件>`
逐页获取 CT.gov 当前公开记录。标准输出只含内容寻址回执路径、SHA-256、状态及记录数，
不输出整篇记录。回执保留逐页原始字节及逐条 NCT 记录的精确 JSON 切片派生关系。
`--page-size` 和 `--max-pages` 是资源边界，不是 Top-N 报告截断；达到边界而仍有下一页时
只能得到未完成状态。网络失败、拒绝访问、限流、坏响应与确实零条记录分别记录。

退出码 0 仅表示该查询分页及派生完成；恢复性失败返回 7，保留已取得的证据。
一次查询完成不代表全球/中国竞品宇宙闭包，不代表主要论文已获取，也不代表科学复核完成。
该接口不是历史登记版本接口：指定历史截止日时，不得把当前返回的管线/监管状态回填到过去。
登记页面更新日期保留日精度，不补造精确公开时刻。

候选宿主 runner 的新建模式要求空项目；恢复模式须显式 `--resume`，并保留与项目相邻的
`.项目目录名.host-smoke-binding.json`。它在启动宿主前绑定候选包、catalog、宿主和项目路径。
身份改变或旧项目没有该绑定时拒绝猜测恢复；下层 fixture 仍须验证项目合同、输入和运行状态。
此文件不代表报告或宿主验收通过，不应手工改写来绕过身份检查。
