"""常规 PDF 原文的原生文本提取：只封装已安装的 pdftotext，不下载、不 OCR、不落临时文件。

- stdout 原样保留（含分页符 \\f），不翻译、不重排、不 strip；页码 1 起，偏移 0 起。
- 只丢弃结尾分页符后的幻影空页；中间空白页保留，start/end 精确对应返回 text。
- 解析身份绑定已安装二进制的版本、本模块字节和固定提取选项；不含路径或凭据。
- 失败抛 PDFTextError(reason)；绝不把 PDF 二进制当文本返回，也不合成零或空结果。
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

PARSER_NAME = 'pdftotext'
EXTRACT_OPTIONS: tuple[str, ...] = ('-layout', '-enc', 'UTF-8', '-', '-')
MAX_TIMEOUT_S = 90.0
VERSION_TIMEOUT_S = 10.0
# 安全失败代码：调用方只按代码分支，消息不得含路径、stdout/stderr 或文档内容。
REASONS = frozenset({'invalid_timeout', 'not_pdf', 'parser_missing', 'version_failed', 'timeout',
                     'parser_failed', 'invalid_utf8', 'empty_text'})
_VERSION_RE = re.compile(r'^pdftotext version\s+([0-9][0-9A-Za-z._+-]{0,31})\s*$', re.MULTILINE)


class PDFTextError(RuntimeError):
    """解析失败；reason 为固定代码，消息只含常量与退出状态。"""

    def __init__(self, reason: str, detail: str = '') -> None:
        self.reason = reason
        super().__init__(reason if not detail else f'{reason}: {detail}')


@dataclass(frozen=True)
class PDFText:
    text: str
    pages: list[dict[str, int]]
    parser_id: str
    parser_version: str


def _module_bytes() -> bytes:
    return Path(__file__).read_bytes()


def _identity(version: str, module_bytes: bytes, options: Sequence[str]) -> str:
    payload = json.dumps({'parser': PARSER_NAME, 'version': version, 'options': list(options),
                          'module_sha256': hashlib.sha256(module_bytes).hexdigest()},
                         sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(payload.encode('ascii')).hexdigest()


def _binary() -> str:
    path = shutil.which(PARSER_NAME)
    if not path:
        raise PDFTextError('parser_missing', f'{PARSER_NAME} not installed')
    return path


def _invoke(argv: list[str], input_bytes: bytes | None, timeout_s: float) -> subprocess.CompletedProcess[bytes]:
    """唯一的进程边界；shell=False，输入走 stdin，不写临时文件。"""
    return subprocess.run(argv, input=input_bytes, capture_output=True, timeout=timeout_s, check=False, shell=False)


def _binary_version(binary: str) -> str:
    try:
        proc = _invoke([binary, '-v'], None, VERSION_TIMEOUT_S)
    except (OSError, subprocess.SubprocessError):
        raise PDFTextError('version_failed', 'cannot query version') from None
    output = (proc.stdout or b'') + (proc.stderr or b'')
    match = _VERSION_RE.search(output.decode('utf-8', 'replace'))
    if proc.returncode != 0 or not match:
        raise PDFTextError('version_failed', f'exit status {proc.returncode}')
    return match.group(1)


def _resolve() -> tuple[str, str, str]:
    binary = _binary()
    version = _binary_version(binary)
    try:module=_module_bytes()
    except OSError:raise PDFTextError('version_failed','cannot verify parser module') from None
    return binary, version, _identity(version,module,EXTRACT_OPTIONS)


def parser_identity() -> str:
    """已安装解析器的确定性身份：版本 + 本模块字节 + 固定提取选项的 sha256。"""
    return f'{PARSER_NAME}:{_resolve()[2]}'


def _timeout(value: float) -> float:
    try:
        timeout = float(value)
    except (TypeError, ValueError):
        raise PDFTextError('invalid_timeout', 'not a number') from None
    if not math.isfinite(timeout) or timeout <= 0 or timeout > MAX_TIMEOUT_S:
        raise PDFTextError('invalid_timeout', f'outside 0..{MAX_TIMEOUT_S:g}s')
    return timeout


def _page_offsets(text: str) -> list[dict[str, int]]:
    pages: list[dict[str, int]] = []
    start = 0
    for page, part in enumerate(text.split('\f'), start=1):
        end = start + len(part)
        pages.append({'page': page, 'start': start, 'end': end})
        start = end + 1
    if text.endswith('\f'):
        pages.pop()  # 结尾分页符后的空段只是幻影页，不占页码。
    return pages


def parse_pdf(content: bytes, timeout_s: float = 90) -> PDFText:
    """用原生 pdftotext 提取文本、页偏移和解析身份；失败即抛 PDFTextError。"""
    timeout = _timeout(timeout_s)
    raw_input = bytes(content)
    if b'%PDF-' not in raw_input[:1024]:
        raise PDFTextError('not_pdf', 'no PDF header in first 1024 bytes')
    binary, version, identity = _resolve()
    try:
        proc = _invoke([binary, *EXTRACT_OPTIONS], raw_input, timeout)
    except subprocess.TimeoutExpired:
        raise PDFTextError('timeout', f'no output within {timeout:g}s') from None
    except (OSError, subprocess.SubprocessError):
        raise PDFTextError('parser_failed', f'cannot execute {PARSER_NAME}') from None
    if proc.returncode != 0:
        raise PDFTextError('parser_failed', f'exit status {proc.returncode}')
    raw = bytes(proc.stdout or b'')
    if b'\x00' in raw:
        raise PDFTextError('parser_failed', 'binary output rejected')
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError:
        raise PDFTextError('invalid_utf8', 'stdout is not UTF-8') from None
    if not text.strip():
        raise PDFTextError('empty_text', 'no extractable text; OCR not attempted')
    return PDFText(text=text, pages=_page_offsets(text), parser_id=f'{PARSER_NAME}:{identity}',
                   parser_version=version)
