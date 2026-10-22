# 临床试验竞品调研平台 v2（重基线）

医学经理工作台的竞品调研子系统：**单用户 Web 服务 + 内嵌最小 Skill Harness（DSH）**。
输入适应症与需求 → 自动检索（中国优先全面、全球尽量充分）→ 原文核验 → 平台内展示 A/B/C 报告（康哲设计 + ECharts）。

## 快速开始
```bash
cd rebaseline-v2
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
bash scripts/fetch_assets.sh          # ECharts 6.1.0，固定SHA256验证（Apache-2.0，不入库）
pytest -q                             # 当前验证范围和结果见 docs/STATUS.md
cp .env.example .env && $EDITOR .env  # 填 LLM / 搜索密钥
set -a && . ./.env && set +a
ciw2 skills                           # 校验 Skill 与工具
ciw2 serve                            # http://127.0.0.1:8765
# 或命令行：ciw2 run --indication 特应性皮炎 --reports A,C
```

常规执行处理全部候选、完整来源页和匹配研究。`--max-drugs N`仅限制本批执行量；未完清单与已完成单元保留，可在项目页从失败处继续，命令退出码不会把未完成写成成功。
长设计原文按需完整读取，模型任务按完整研究分批，原始资料不截断。恢复复用同一运行的既有来源版本；重新调研应创建新运行。

## 目录
```
docs/        00_REVIEW 01_PRD 02_ARCHITECTURE 03_PLAN 04_AGENT_RULES 05_PORTING_MAP 06_START_PROMPT STATUS
skills/      9 个 SKILL.md（判断类工作）
src/ciw2/    config store domain verify harness sources pipeline render web service cli
tests/       离线测试 + 小夹具
scripts/     fetch_assets.sh、smoke_live.py、run_live.py、replay_design_sources.py
```

## 报告
- **A 竞争格局**：药物 × 靶点 × 中国/全球最高阶段 × 企业/MAH，含纳排理由与发现路线。
- **B 疗效与安全性**：只用已核实数据作图；不同终点/时间点/统计形式分开；SAE/死亡按组、比例仅在分母明确时计算。
- **C 试验设计先例**：期别、样本量、随机/设盲、分组、主要终点与时间点、年龄、中国站点。

开发规则见 `docs/04_AGENT_RULES.md`；当前状态见 `docs/STATUS.md`。

开发者可使用 `python scripts/smoke_live.py --complete-ctgov "Atopic Dermatitis" NEW_OUTPUT_DIR` 隔离核对完整登记分页及官方总数，保留来源哈希与回执，不调用模型或改动已有报告。输出目录必须是新的；该检查不代替报告验收。
已有冻结来源的隔离副本可用 `python scripts/run_live.py --indication 特应性皮炎 --project PREPARED_PROJECT_ID --only-stage analysis_C` 验证同一生产分析及渲染阶段。须将CIW_DATA_DIR指向副本；回执会明确单阶段，不作为完整研究或发布通过。
