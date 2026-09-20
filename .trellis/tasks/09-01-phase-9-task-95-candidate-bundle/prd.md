# Task 9.5 产品需求

## 目标

把当前已验收代码、合同、Schema、Policy、康哲站点设计合同、资产和最小测试夹具封装为一个可移动、可校验的 `.tar.zst` Skill bundle；在隔离目录 fresh-install 后，Codex、Hermes、OMP 必须从各自真实入口发现并执行同一公共 Skill。

## 用户体验

- 用户仍只需提供 A/B/C 报告选择、适应症；首版输出固定为站点式 HTML。
- 安装过程给出中文、可复制的最短指引，不要求用户理解 Python 包、链接或摘要。
- 任一宿主不可用时明确说明是环境/技术问题，不伪装成“未检索到资料”；其他宿主与已接受科学快照不受影响。
- 关键证据不足时三个宿主均不生成草稿，并说明 AI 已完成的检索与用户需要补充的材料。

## 验收标准

1. bundle 只含新工程所需代码、公开/内部 Skills、合同、Schema、Policy、站点资产和必要 fixture；不含缓存、旧报告、测试项目或凭据。
2. bundle、逐文件 package manifest 与 SHA-256 同时产生；`verify_bundle.py` 对缺文件、额外未声明文件、摘要漂移和路径逃逸失败关闭。
3. fresh-install 在独立目录完成，不覆盖旧入口；共享规范根与 OMP 单一明确链接均可解析到同一 bundle digest。
4. 三宿主 capability preflight 的语义字段一致，首版 HTML 不因 PDF/PPT 能力缺失而阻断。
5. 三个真实宿主由独立外部进程/会话运行 `host-smoke-v1`；process/session/run 不同，package/case digest 与语义状态一致。
6. 三份回执均为 `path_resolved`，绑定真实宿主版本、安装入口、事件链、no-draft、manifest 和真实退出码；同进程伪造、旧回执和 adapter-only JSON 失败关闭。
7. 用户安装说明为中文原生、短步骤、可复制，并明确首版只有站点式 HTML。

## 非目标

- 不生成或验收 PDF、HTML-PPT、PPTX。
- 不覆盖生产/旧入口，不删除旧工程。
- 不进行安全专项测试，不扩展 LangGraph。
