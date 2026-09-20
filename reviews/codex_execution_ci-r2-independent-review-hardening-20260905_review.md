# Codex Execution Review: ci-r2-independent-review-hardening-20260905

## Verdict

ACCEPTED_WITH_CODEX_INTEGRATION. 四个 worker 的输出均作为实现输入接受；没有
任何 worker 自行取得最终验收权。Codex 已逐文件合并、解决跨 worker 合同，
并补做运行级信任链、A/B/C 对称性、有效期和多次 resume 验收。

## Worker Outputs

- `worker_01`：接受真实 `review issue` 签发入口、外部进程证据、receipt 与
  issuance record 双向绑定；扩展为 A/B/C，并接入运行时晋级。
- `worker_02`：接受 post-format 门户字节绑定、B/C 受控 resume 和不可回退；
  追加生产上下文不可覆盖、签发记录核验与晋级时有效期。
- `worker_03`：接受 A 两阶段状态机和摄取时间确定性修复；未整文件复制其
  大面积格式化差异，只提取并重放语义变更，再补真实 issuance 正向测试。
- `worker_04`：接受 bundle import closure、required content 和 retained
  compatibility smoke 精确措辞；另将 `review_issuer.py` 纳入最终必需内容，
  同步 package CLI catalog/schema。

## Manager Assessment

本路线未配置 execution manager，由 Codex 直接评估四个隔离 worker。一次性
`gpt-6-astra:high` 阶段审阅与独立 CodeBuddy 会商均判定原状态需修复；共同
P1 已落实：回执正式签发路径、format 后晋级、门户字节重验、A 类对称、
多次 resume、bundle 闭包。截图实际字节验收留在 R4，`expected_run_id` 绑定
留在 R6；PKI、中央签名、OS attestation、nonce registry 与第二回执体系按
YAGNI 和既定本地威胁模型拒绝。

## Boundary

本次只改当前新工程的 R2 运行时、测试、bundle 合同和 canonical 文档；没有
访问或判断遗留工作区，没有 reset/checkout/clean，没有触碰受保护 Codex
session/database，也没有执行真实宿主发布或 RC 冻结。worker_03 的越界候选
修改由 Codex 重新验证后仅以一行确定性修复追认，未直接采纳其整文件格式化。

## Hermes

本执行路由由全局 guard 选择 ZCode 四 worker，未声明 Hermes worker，故
Hermes 未参与本次 artifact production。Hermes 的真实宿主签发与安装一致性
仍属于 R5/R6 三宿主矩阵，不以本轮缺席冒充通过或失败。

## Codex Independent Verification

- `bash tools/gate.sh`：Ruff 通过；strict mypy 205 files；v1 active 913 passed /
  20 deselected；retained compatibility smoke 20 passed；layer audit 7 passed；
  legacy reference scanner 通过；`GATE_OK status=quality-only steps=6`。
- `pytest tests/integration -q`：438 passed。
- R2 聚焦集合：91 passed，覆盖 A/B/C 真实签发、伪回执、门户漂移、同身份/
  同会话、未来/过期、重复 resume 和隔离 bundle import closure。
- C fresh-package 运行已实际完成 `rendered_unreviewed → review issue →
  scientifically_reviewed_rendered_candidate`。
- `python -m ci_workflow package verify --root .`：`PACKAGE_OK`。
- 候选 bundle：320 files，SHA-256
  `e77e87ebfb3007a052707f4237de81fcd7c5351e9208bda7b0dff2af9ae3282a`；
  `verify_bundle --require-final-content` 返回 `BUNDLE_OK`。
- `audit-execution`：4/4 role 输出、runner stdout 与 route identity 全部闭合，
  无 warning/error。

未主张：三宿主真实签发、R4 全物理页面截图字节、24 门户、clean RC、
fresh-install 和 RC freeze；这些仍按 R4-R6 完成。三个旧外部 A/B/C 验收项目
继续因旧 `package_digest` 被正确拒绝，留待 R5/R6 当前候选再生。

## Cleanup Decision

验收记录落盘并通过 review gate 后，删除四个已完成 APFS 隔离克隆和本次
临时 bundle 目录；保留 prompts、runner 输出、stdout、review、metrics、
canonical 文档和测试。不会触碰 Codex session/数据库或项目外受保护状态。
