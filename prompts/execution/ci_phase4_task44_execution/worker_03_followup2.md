继续同一 Worker 03 / Cursor 会话。Task 4.4 三位真实医学经理视觉试用均给出 REVISE；请在原授权范围内直接修复，并把问题固化为 Chromium/WebKit 回归。不要解释，不要提交。

仅修改 Task 4.4 浏览器资产、fixture、`tests/browser/test_chart_table_sync.py`、必要的门户资源副本/manifest/当前截图；不得修改 Python 科学合同、批准设计书/计划、Trellis、运行记录。

必须修复：
1. 筛选面板必须紧邻顶部“筛选条件”按钮可见，使用康哲设计语言的浮层/卡片，1280 与 1024 不得落到 body 末尾。选中项在顶部显示具体中文 chip，不只显示“已选 N 项”。
2. fixture 必须使用 Task 4.3 已冻结的 URL 状态合同：筛选有结果、空结果、清除、刷新、前进/后退可复现；不得另造不写 URL 的简版。无匹配时显示原生中文指导和一键清除。
3. 筛选后隐藏未命中小多图整组，不能只把柱降透明而保留空卡/旧 tooltip；匹配数与可见完整记录一致。关闭或变更筛选时清除旧 tooltip/selection。
4. `renderable=false` 的整组不绘制 340px 空坐标系；改为紧凑、明确的“该指标结果尚未公开”状态区，仍保留完整表格和 row ID，绝不映射为 0。用高对比但克制的灰/橙说明，避免像加载失败。
5. 柱图数值轴必须包含零基线，负值治疗/对照都真实可见；柱顶/柱端显示比较值。每行/图例/坐标标签明确治疗组或对照组，表格增加“组别”列。不要依赖 hover 才能看值。
6. 图点击→表高亮、表点击/Enter/ArrowUp/ArrowDown→图高亮必须分别用真实 pointer/keyboard 测通，不能程序化 API 兜底；选择态要明显但不刺眼。
7. 页面可见区域移除 hash/snapshot/fixture/backend/log 等内部文字；表中“未满足展示条件”改为医学经理可理解的“该指标结果尚未公开”（或更自然同义）。
8. 保持图在前、完整表在后；1024 无横向溢出。九类真实 ECharts smoke、离线资源、Python fixture parity 不得回归。

新增/强化真实浏览器断言：面板 bounding box 在首屏；chip 具体文字；URL query/hash 改变并刷新/前进后退恢复；过滤后不匹配 card display none；空态指导+清除；未公开组无 canvas/无大空白且表存在；负值两根柱都有非零像素高度/对应 option axis 包含0；value labels；臂别列；真实图点/表点/键盘；用户可见内部词扫描。重跑双引擎 Task4.4、Task4.3 回归、102 单元、Ruff、strict mypy、包校验，更新非重复截图。返回改动、失败根因、精确测试与残余边界。

Runner-managed output: `runs/execution/ci_phase4_task44_execution/worker_03_followup2.md`; 不得用工具写该路径。
