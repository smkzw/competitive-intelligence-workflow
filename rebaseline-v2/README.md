# 临床试验竞品调研平台 v2（重基线）

医学经理工作台的竞品调研子系统：**单用户 Web 服务 + 内嵌最小 Skill Harness（DSH）**。
输入适应症与需求 → 自动检索（中国优先全面、全球尽量充分）→ 原文核验 → 平台内展示 A/B/C 报告（康哲设计 + ECharts）。

## 快速开始
```bash
cd rebaseline-v2
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
bash scripts/fetch_assets.sh          # ECharts（不入库）
pytest -q                             # 31 passed
cp .env.example .env && $EDITOR .env  # 填 LLM / 搜索密钥
set -a && . ./.env && set +a
ciw2 skills                           # 校验 Skill 与工具
ciw2 serve                            # http://127.0.0.1:8765
# 或命令行：ciw2 run --indication 特应性皮炎 --reports A,C
```

## 目录
```
docs/        00_REVIEW 01_PRD 02_ARCHITECTURE 03_PLAN 04_AGENT_RULES 05_PORTING_MAP 06_START_PROMPT STATUS
skills/      9 个 SKILL.md（判断类工作）
src/ciw2/    config store domain verify harness sources pipeline render web service cli
tests/       离线测试 + 小夹具
scripts/     fetch_assets.sh
```

## 报告
- **A 竞争格局**：药物 × 靶点 × 中国/全球最高阶段 × 企业/MAH，含纳排理由与发现路线。
- **B 疗效与安全性**：只用已核实数据作图；不同终点/时间点/统计形式分开；SAE/死亡按组、比例仅在分母明确时计算。
- **C 试验设计先例**：期别、样本量、随机/设盲、分组、主要终点与时间点、年龄、中国站点。

开发规则见 `docs/04_AGENT_RULES.md`；当前状态见 `docs/STATUS.md`。
