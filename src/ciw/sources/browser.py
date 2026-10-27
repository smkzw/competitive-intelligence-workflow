"""Shared bounded Ego runner; stdout/stderr receipts contain public page captures only."""

from __future__ import annotations

import json
import shutil
import subprocess
from importlib import resources
from typing import Any


def run_script(
    name: str, config: dict[str, Any], timeout: float, *, package: str, helpers: tuple[str, ...] = ()
) -> tuple[list[dict], dict]:
    exe = shutil.which("ego-browser")
    if not exe:
        raise RuntimeError("未找到 ego-browser；中国来源采集需要 ego lite")
    script = (
        "const config = "
        + json.dumps(config, ensure_ascii=False)
        + ";\n"
        + "\n".join(resources.files(package).joinpath(h).read_text(encoding="utf-8") for h in helpers)
        + "\n"
        + resources.files(package).joinpath(name).read_text(encoding="utf-8")
    )
    try:
        proc = subprocess.run(
            [exe, "nodejs", "-e", script],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        streams = (proc.stdout or "") + "\n" + (proc.stderr or "")
    except subprocess.TimeoutExpired as exc:  # 超时：保留已输出的分页，状态记为 timeout
        streams = (
            "\n".join(
                x.decode("utf-8", "replace") if isinstance(x, bytes) else (x or "") for x in (exc.stdout, exc.stderr)
            )
            + '\nCIW_CHINA_END:{"status":"timeout"}'
        )
    pages, end = [], {}
    # ego-browser 0.6 把脚本的 console 输出写到 stderr；两个流都读
    seen: set[str] = set()
    for line in streams.splitlines():
        if line in seen:  # 同一行可能同时出现在两个流里
            continue
        seen.add(line)
        if line.startswith("CIW_CHINA_PAGE:"):
            pages.append(json.loads(line.removeprefix("CIW_CHINA_PAGE:")))
        elif line.startswith("CIW_CHINA_END:"):
            end = json.loads(line.removeprefix("CIW_CHINA_END:"))
    return pages, end
