# Conference Metrics: ci-1007-pk-and-safety-source-review-v1

Date: 2026-10-10

| Role | Provider | Model | Status | Duration | API calls | Tokens | Result |
|---|---|---|---|---:|---:|---:|---|
| `evidence_single_object` | grok-build | grok-4.7/high submitted; native variant unverified | terminal exit0 | 1013.198s | native count unavailable | total1758403; input183272/cache-read1504256/output70875(reasoning47064) | REVISE |
| same-session measured_followup_v2 | grok-build | same route, variant unverified | terminal exit0 | 826.882s | unavailable | total4226522/input340861/cache3839616/output46045(reasoning29049) | Scoped REVISE |

## Timeout And Retry Evidence

Original37628 once7200s, NOTE_EXIT30534 completion only, no retries/fallback. Session
93da10df-4953-4bee-992f-e118310e56a1。同会话派发时剩余6180s hardwait，kernel82920
已收到退出事件，未周期读log或重派。原native usage/session可核；没有native单独
modelvariant/effort attestation，未知不能写成0或已核身份。

## Quality Decision

原科学REVISE支持的根因已在共同源路径修复并生成独立19candidate；同会话
只挑战修复，不是新独立模型。owner定量原源/生产回归见review，正式issuer/
新版本接受/报告链/整体发布仍开。原snapshot/16candidate/REVISE不覆写。

## 暂停终态

42788/82920已结束，不等待/重派。N$.$./TESAE匹配阻断采用；SDcoverage等剩余
待根因测试。正式issuer/current/发布均未发生，用户要求无损暂停。
