# Task 3.3 原会话最终完成轮

Hard boundaries:
- 继续会话 `17ca0d78-0348-40fe-a1fe-ce2984131c0c`；不得新开会话。
- 只读验收；不得修改仓库文件，不得读取另一参与者输出。
- 临时探针只写系统临时目录，完成后清理。

Read these files only:
- `src/ci_workflow/ingestion/manual_inbox.py`
- `src/ci_workflow/application/project_service.py`
- `schemas/download-request.schema.json`
- `tests/integration/test_manual_inbox_recovery.py`
- `tests/integration/test_user_filename_auto_rename.py`
- `tests/integration/test_download_request_transitions.py`
- `policies/gates/B-v1.yaml`

Write exactly one output file: `runs/conference/ci_phase3_task33_acceptance/general_grok45_completion.md`

该文件由 runner 持久化；你不得自行写入。

前两轮都在准备调用工具时被运行时取消，没有形成验收结论。这是同一会话的最终完成轮。当前调用允许只读终端操作；请直接完成验证，不再先返回进度文字。

当前验收源摘要：

- `manual_inbox.py`: `128c9a40d32bbe0c7d7e7e27995936a46e40e19ede1be071fac153880f457481`
- `download-request.schema.json`: `b614cd119f9d44eb2d2dffd73d8cc021fd90b903dcb348d2c01a85d0bb9968c5`
- `test_manual_inbox_recovery.py`: `1ddfe481f490b02f7996da9835def2cc70f492a36f1911cb12d40b0fc0a7b369`
- `test_user_filename_auto_rename.py`: `54dea9ec3000e68237c95f6e55b99ea0f64ab360c994c8f8417e0164139063d8`
- `test_download_request_transitions.py`: `c09cbab7e50a2f0adb63e98530aa350985fbcf07f1ce81145f17616aaa1115bc`

先核对摘要，再运行三个精确测试。至少用临时目录对抗验证：大写扩展名；`matched` 中断恢复；`accepted` 后遗留副本清理且不重复事件/作业/来源；同运行歧义与跨运行隔离；英文标题必须命中至少两个非通用词；无可核对标识不发起请求；隔离说明保留多轮记录；模型与 Schema 的 accepted 字段一致。

测试计数不能替代探针。返回完整六节报告并给 P0/P1/P2。若没有 P0/P1，应明确 `PASS`。结尾严格为：

`PASS|FAIL; P0=n; P1=n; P2=n`
