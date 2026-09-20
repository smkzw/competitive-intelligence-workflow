# 设计 — R2.5 药智可选浏览器适配与会话真值

## 当前缺口

1. `RuntimeCapabilityProbe` 对 `login_browser` 只启动无会话的 headless Chromium，可能把
   “浏览器可启动”误报为“已登录资料可访问”。
2. `YaozhRouteAccessReceipt` 仅覆盖 ready/session-expired/tool-unavailable，尚未表达验证码、
   权限与解析失败，也未绑定真实页面观察。
3. `ResearchSource` 没有 `commercial_database` 来源角色，正式研究包无法按 v1.3 原义标识
   药智来源，只能错误借用 `specified_secondary`。

## 最小架构

1. 通用 capability preflight 只判断宿主是否具备“操作登录浏览器”的工具，不声称特定
   站点已登录；默认执行器无法取得宿主会话时对 `login_browser` 失败关闭但保持非阻断。
2. 宿主在自身浏览器边界观察药智页面，仅向核心提交最小 `YaozhSessionObservation`：项目、
   回答摘要、观察时间、规范来源 origin、封闭技术状态、观察者/宿主身份和非敏感页面标记
   摘要。核心不接触浏览器 profile、Cookie、header 或 token。
3. 核心从该观察确定性生成 `YaozhRouteAccessReceipt`，绑定观察摘要；同字节幂等，跨项目、
   回答漂移、非药智域、未来时间、秘密字段和本机路径拒绝。
4. 获取到的页面内容仍通过标准 `ResearchSource`/`ExtractionCandidate` 进入研究包，来源角色
   为 `commercial_database`、类型为 secondary、URL 限制为药智域。来源政策继续决定各声明域
   最多 lead/cross-check；该角色不映射为 GateSpec 的直接证据角色。
5. 真实浏览器 smoke 由 Codex/Hermes/OMP 宿主适配层执行并只保留脱敏回执摘要；不得把
   Playwright/CDP 固化为核心依赖或复制用户浏览器资料。

## 恢复语义

- `session_expired`：提示用户自行登录后重试该辅助路线。
- `captcha_required`：提示用户在浏览器内自行完成验证，禁止自动绕过。
- `permission_denied`：提示核对企业版权限；其他来源继续。
- `tool_unavailable`：提示启用可操作已登录浏览器的宿主能力。
- `parser_error`：保留页面已访问与解析失败的区别，允许更换解析策略。

上述状态均不改写项目回答、不阻断核心研究、不伪装成“没有证据”。
