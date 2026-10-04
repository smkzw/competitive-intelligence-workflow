# R24-249/250｜复合设计证据与当前隔离安装

2026-10-04；W03/W07/W08增量，连续实施，未暂停、未晋级current/RC。
HEAD仍c129a575；脏树、原来源及历史FAIL保留，旧中文工程零接触。

## 249 原源反例与完整最小修复

固定CT.gov NCT02264639真实源为PARALLEL/NON_RANDOMIZED/NONE、四剂量队列，
不是单组；不沿用早期错误概括，不按数组猜臂/药物关系。原生产函数五RED/
一个完整正例3.49s：年龄单值、仅allocation、缺masking、一个未接受主要定义/
时间不应满足整个复合要求。夹具accepted仅测试假设，不是来源采用回执。
RED XML SHA03d76cbefe1cf26b4546e99a64d44dce8228b8b117b4872e4ba3ffd1aa8c3277。

当前C-v2复用已有evidence_binding_qualifies和原源endpoint实例校验：人群需
完整eligibility条件；native分组需同一来源版本的allocation/model/masking并与
明确设计声明一致；全关键endpoint实例不能因一个实例未接受而从覆盖集合消失。
保留全部原观察，只剔除不合格proof bindings；现有引擎输出BLOCKED。
旧C-v1政策/历史不改；当前规则身份c-design-compound-coverage-v1。
新增两个验证例保留明确单组矛盾与整实例未接受，不冒称它们已属于原五RED。

最终整族/邻接207PASS/23.18s（此前205PASS/24.48s保留）；Ruff/strict一源PASS。
GREEN XML SHA c1a849a74cb358e5d83bb29a680989c823df36bf14a63d2a47ff20987135f133。
fresh_c源码SHA519c5131d6b9d391f82fcfec75666c0b119d6b42fc338a8fbf66ac3cf0b0ff57。
新测试SHAeda556b7ea96455b95ae9d3038c3b5228b2b6136c74a01ce5d477f3cdc562b02。
248的183PASS对应旧字节，不自动继承。

## 独立复核现场（未接受）

原R242结论REVISE保留。针对21冻结文件、实际上游类型/源/测试恢复同一位
PI/openai-codex/gpt-6.1-sol/high审阅者，会话01a1055d-8fe6-7000-b09d-990e662478d4。
同模型上下文续接不是第二独立意见；effort为请求值，非服务器独立证明。
冻结manifest SHAe41eba4b5901b525bb7eb87675ca362d83f3fb9cf3b78f3484e1ff1be76f5aad。
第一次45231/exit2因猜错manifest路径，未启动审阅者，失败报告/日志不覆盖；
纠正为已存在的evidence_single_object_route_manifest后启动_v2。
当前runner51113/PID45328、kernel24162仅NOTE_EXIT；收到EXIT后才收runner、读
报告与实际身份，不进度轮询/重派/在途QA。来源/设计复合判断仍待该复核。
有限输入枚举仍不等于全球/中国发现，run_service package-digest fallback未闭。

## 250 一次集中开发门与新包

实际11985终态GATE_OK status=quality-only steps=6：Ruff src/tests/tools；strict
src/tools272源；活跃unit/contract1117PASS/108.02s（20deselected）；保留轨
20兼容smokePASS/0.77s（1117deselected，不是全非HTML渲染）；分层7PASS/0.26s；
英文根禁止旧运行依赖扫描PASS。未要求干净树，未声明科学/渲染/最终门。
原终端输出在宿主执行记录；没有另存原始gate日志，不伪造原始日志/hash。

实际构建392文件的HTML-only包，最终内容验证BUNDLE_OK required-v12：
archive SHAfd925823a70f7b4a65eb386c68ea222593bbb55fd8596f68d83d62452902dc1c；
manifest SHA1665e2c46f9fd4649ad294de6d45f92ccfd88d3f54798cf3828ff6a5f9c36f07。
隔离fresh-install成功，私有venv/锁定依赖与入口真实探测；393安装记录含包内
manifest本身，与392发行文件计数口径不同，不以数字相同代替字节检查。

普通安装运行时以-I -B、安装根cwd、移除PYTHON/UV/PIP环境影响，实际导入
安装内fresh_c，源码摘要同上。完整三个复合单元满足、年龄单值阻断；这是测试
假设的合同证明，不是生产医学采用。安装内普通B入口生成48原源支持组件/
28面板/74页/6894197B；数值/单位/domain/metric/测量路径/版本/原文/定位逐项一致。
站点SHAcd5f0174147f28de719fd0f74d9b8b81104c2875de17ed367a5b3919e4239841。
不是完整6346报告、真实像素或三宿主运行。PDF/PPT交付依赖未安装。
runtime-probe-v1.json SHA4e84a885d5426c9046e5d06e9ace63e6bdec5c30652fa1c4c021b8c5dca4cf24。
首探针父进程未设置仓库tests导入路径，ModuleNotFoundError、未启动子进程；
恢复仅父PYTHONPATH=.，子-I且清理该环境，未用开发仓库冒充安装导入。

只清理本次新安装uv下载缓存：原du206120KiB；uv报告1376文件/183.4MiB。
393安装记录和安装元数据未变，清后安装runtime导入/layout再次实际成功。
cache-cleanup-v1.json SHA182cc0ba679a89278f5bd1ee546f30c497830ac76e8b663b002420ef1fdaf4b1。
缓存可按随包lock再生；永久移除缓存不是删除唯一证据。未测物理APFS回收量，
硬链接共享不能把du或uv大小冒充实际磁盘释放量；源、候选、日志、会话未删。

## 工件与下一步

- `.artifacts/r24-249-c-compound-current-review-20261004/frozen-v1.json`及原件。
- `.artifacts/r24-250-current-bundle-20261004/`：archive/manifest/安装/probe/缓存回执。
- 普通重放：`PYTHONPATH=. uv run python .artifacts/r24-250-current-bundle-20261004/probe_installed_v1.py`。
  脚本为独占新产物：已存在则失败，不覆盖；需另选新输出版本再重放。

独立终态后核真实发现scope和剩余干预/科学身份缺口；继续真实来源接受、
合法保存/分享、24门户与三宿主全模式，不做逐标签/逐处全仓循环。
指定Ego TaskSpace12本次真实仍NOT_FOUND；保留原Ask，不另造空间/替换浏览器。
Design6+A04规范未变；真实四宽屏/四状态实屏NOT_RUN，不能称视觉通过。
开发、组件、安装与医学/产品/最终发布分别记账，未交付条件不缩小。
