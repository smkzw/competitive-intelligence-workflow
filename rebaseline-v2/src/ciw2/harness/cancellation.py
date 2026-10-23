"""单进程合作式运行控制。

取消是用户意图，不是模型或工具失败：`RunCancelled` 不继承 `LLMError`，因此不会触发
备用路由，也不会被工具边界吞成 `tool_failed`。持有 `RunContext` 的普通多来源循环应在
每个单元/来源之间调用 `rc.check_cancelled()`；正在进行的网络请求可以完成，本模块不杀线程。
每个运行一个 `RunControl`，没有全局注册表；这是单进程控制，不是多进程调度或租约。
"""
from __future__ import annotations

import threading


class RunCancelled(BaseException):
    """用户请求停止；已完成资料和同 run 缓存保留，可稍后继续。

    继承 `BaseException`（同 `asyncio.CancelledError`）：既有的多来源/抽取循环用
    `except Exception` 隔离单条失败，不能把停止意图改写成 `unit_failed` 或继续跑下一单元。
    """


class RunControl:
    def __init__(self) -> None:
        self._stop = threading.Event()

    def request_stop(self) -> bool:
        """记录停止意图；重复请求无副作用。"""
        if self._stop.is_set():
            return False
        self._stop.set()
        return True

    @property
    def stopping(self) -> bool:
        return self._stop.is_set()

    def check_cancelled(self) -> None:
        if self._stop.is_set():
            raise RunCancelled('用户请求停止；已在安全边界停止，已完成资料保留，可稍后继续')
