"""原生 PDF 文本提取的边界用例：进程边界用假实现，真实进程用例单独标注。"""
from __future__ import annotations

import re
import shutil
import subprocess

import pytest

from ciw2.sources import pdf_text

PDF = b'%PDF-1.7\nsynthetic bytes'
BINARY = '/synthetic/bin/pdftotext'
VERSION = b'pdftotext version 26.08.0\n'


class FakeParser:
    """替代唯一进程边界 _invoke；记录 argv、stdin 和超时，不启动真实进程。"""

    def __init__(self, *, stdout: bytes = b'', stderr: bytes = b'', returncode: int = 0,
                 version: bytes = VERSION, version_returncode: int = 0,
                 error: BaseException | None = None) -> None:
        self.stdout, self.stderr, self.returncode = stdout, stderr, returncode
        self.version, self.version_returncode, self.error = version, version_returncode, error
        self.calls: list[tuple[list[str], bytes | None, float]] = []

    def __call__(self, argv: list[str], input_bytes: bytes | None, timeout_s: float) -> subprocess.CompletedProcess:
        self.calls.append((list(argv), input_bytes, timeout_s))
        if argv[1:] == ['-v']:
            return subprocess.CompletedProcess(argv, self.version_returncode, b'', self.version)
        if self.error is not None:
            raise self.error
        return subprocess.CompletedProcess(argv, self.returncode, self.stdout, self.stderr)

    def extraction(self) -> tuple[list[str], bytes | None, float]:
        calls = [call for call in self.calls if call[0][1:] != ['-v']]
        assert len(calls) == 1
        return calls[0]


@pytest.fixture
def parser(monkeypatch: pytest.MonkeyPatch) -> FakeParser:
    fake = FakeParser()
    monkeypatch.setattr(pdf_text, '_binary', lambda: BINARY)
    monkeypatch.setattr(pdf_text, '_invoke', fake)
    return fake


def test_parser_identity_binds_version_module_bytes_and_options(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pdf_text, '_binary', lambda: BINARY)
    monkeypatch.setattr(pdf_text, '_invoke', FakeParser())
    monkeypatch.setattr(pdf_text, '_module_bytes', lambda: b'module-A')
    base = pdf_text.parser_identity()
    assert re.fullmatch(r'pdftotext:[0-9a-f]{64}', base)
    assert pdf_text.parser_identity() == base
    assert BINARY not in base
    monkeypatch.setattr(pdf_text, '_invoke', FakeParser(version=b'pdftotext version 99.01.0\n'))
    assert pdf_text.parser_identity() != base
    monkeypatch.setattr(pdf_text, '_invoke', FakeParser())
    monkeypatch.setattr(pdf_text, '_module_bytes', lambda: b'module-B')
    assert pdf_text.parser_identity() != base
    monkeypatch.setattr(pdf_text, '_module_bytes', lambda: b'module-A')
    monkeypatch.setattr(pdf_text, 'EXTRACT_OPTIONS', ('-raw', '-enc', 'UTF-8', '-', '-'))
    assert pdf_text.parser_identity() != base


def test_missing_executable_is_a_distinct_safe_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pdf_text.shutil, 'which', lambda name: None)
    with pytest.raises(pdf_text.PDFTextError) as caught:
        pdf_text.parse_pdf(PDF)
    assert caught.value.reason == 'parser_missing'
    assert 'installed' in str(caught.value) and '/' not in str(caught.value)
    with pytest.raises(pdf_text.PDFTextError) as identity:
        pdf_text.parser_identity()
    assert identity.value.reason == 'parser_missing'


@pytest.mark.parametrize('version_returncode, version', [(2, b''), (0, b'not a version line\n'),
                                                        (0, b'pdftotext version /private/bin/pdftotext\n')])
def test_version_probe_failure_is_distinct(parser: FakeParser, version_returncode: int, version: bytes) -> None:
    parser.version, parser.version_returncode = version, version_returncode
    with pytest.raises(pdf_text.PDFTextError) as caught:
        pdf_text.parser_identity()
    assert caught.value.reason == 'version_failed'
    assert '/private' not in str(caught.value)


def test_non_pdf_is_rejected_before_any_process(monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable() -> str:
        raise AssertionError('non-PDF bytes must not resolve the parser')

    monkeypatch.setattr(pdf_text, '_binary', unavailable)
    for content in (b'', b'<html>not a pdf</html>', b'\x00' * 2048):
        with pytest.raises(pdf_text.PDFTextError) as caught:
            pdf_text.parse_pdf(content)
        assert caught.value.reason == 'not_pdf'


def test_pdf_magic_is_recognized_only_within_first_1024_bytes(parser: FakeParser) -> None:
    parser.stdout = b'Body\f'
    assert pdf_text.parse_pdf(b'x' * 1019 + b'%PDF-').pages[0]['page'] == 1
    with pytest.raises(pdf_text.PDFTextError) as caught:
        pdf_text.parse_pdf(b'x' * 1020 + b'%PDF-')
    assert caught.value.reason == 'not_pdf'
    assert len(parser.calls) == 2  # 一次成功提取 + 一次版本探测；被拒的字节没有启动提取。


@pytest.mark.parametrize('bad', [0, -1, 90.5, float('nan'), float('inf'), 'x', None])
def test_timeout_outside_bounds_is_rejected_before_spawning(parser: FakeParser, bad: object) -> None:
    with pytest.raises(pdf_text.PDFTextError) as caught:
        pdf_text.parse_pdf(PDF, timeout_s=bad)  # type: ignore[arg-type]
    assert caught.value.reason == 'invalid_timeout'
    assert parser.calls == []


def test_extraction_uses_fixed_options_stdin_bytes_and_bounded_timeout(parser: FakeParser) -> None:
    parser.stdout = b'Body\f'
    pdf_text.parse_pdf(PDF, timeout_s=90)
    argv, stdin, timeout = parser.extraction()
    assert argv == [BINARY, '-layout', '-enc', 'UTF-8', '-', '-']
    assert stdin == PDF and timeout == 90
    version_call = [call for call in parser.calls if call[0][1:] == ['-v']]
    assert version_call == [([BINARY, '-v'], None, pdf_text.VERSION_TIMEOUT_S)]


def test_timeout_has_its_own_reason(parser: FakeParser) -> None:
    parser.error = subprocess.TimeoutExpired([BINARY], 1.0)
    with pytest.raises(pdf_text.PDFTextError) as caught:
        pdf_text.parse_pdf(PDF, timeout_s=1.0)
    assert caught.value.reason == 'timeout'
    assert '/synthetic' not in str(caught.value)


def test_parser_failure_keeps_stderr_and_document_text_out_of_the_error(parser: FakeParser) -> None:
    parser.returncode, parser.stderr = 1, b'Syntax Error: /private/records/source.pdf'
    parser.stdout = b'%PDF-1.7 leaked binary'
    with pytest.raises(pdf_text.PDFTextError) as caught:
        pdf_text.parse_pdf(PDF)
    assert caught.value.reason == 'parser_failed' and 'exit status 1' in str(caught.value)
    assert '/private/records/source.pdf' not in str(caught.value)
    assert 'leaked binary' not in str(caught.value)


def test_exec_oserror_is_a_safe_parser_failure(parser: FakeParser) -> None:
    parser.error = PermissionError(13, 'denied', '/private/bin/pdftotext')
    with pytest.raises(pdf_text.PDFTextError) as caught:
        pdf_text.parse_pdf(PDF)
    assert caught.value.reason == 'parser_failed'
    assert '/private' not in str(caught.value)


def test_binary_stdout_is_never_decoded_as_text(parser: FakeParser) -> None:
    parser.stdout = b'%PDF-1.7\x00\x01binary'
    with pytest.raises(pdf_text.PDFTextError) as caught:
        pdf_text.parse_pdf(PDF)
    assert caught.value.reason == 'parser_failed'


def test_invalid_utf8_has_its_own_reason(parser: FakeParser) -> None:
    parser.stdout = b'valid prefix \xff\xfe'
    with pytest.raises(pdf_text.PDFTextError) as caught:
        pdf_text.parse_pdf(PDF)
    assert caught.value.reason == 'invalid_utf8' and 'valid prefix' not in str(caught.value)


@pytest.mark.parametrize('stdout', [b'', b'\f', b' \n\t\f'])
def test_empty_and_image_only_extraction_fails_instead_of_returning_nothing(parser: FakeParser,
                                                                            stdout: bytes) -> None:
    parser.stdout = stdout
    with pytest.raises(pdf_text.PDFTextError) as caught:
        pdf_text.parse_pdf(PDF)
    assert caught.value.reason == 'empty_text'


def test_multi_page_offsets_keep_blank_middle_page_and_unmodified_text(parser: FakeParser) -> None:
    parser.stdout = b'Alpha\n\f\fGamma\n\f'
    result = pdf_text.parse_pdf(PDF)
    assert result.text == 'Alpha\n\f\fGamma\n\f'
    assert result.pages == [{'page': 1, 'start': 0, 'end': 6}, {'page': 2, 'start': 7, 'end': 7},
                            {'page': 3, 'start': 8, 'end': 14}]
    assert [result.text[page['start']:page['end']] for page in result.pages] == ['Alpha\n', '', 'Gamma\n']
    assert result.text.count('\f') == 3


def test_single_page_trailing_formfeed_drops_only_the_phantom_page(parser: FakeParser) -> None:
    parser.stdout = b'Solo\n\f'
    result = pdf_text.parse_pdf(PDF)
    assert result.text == 'Solo\n\f'
    assert result.pages == [{'page': 1, 'start': 0, 'end': 5}]


def test_output_without_trailing_formfeed_keeps_every_page(parser: FakeParser) -> None:
    parser.stdout = b'One\fTwo'
    assert pdf_text.parse_pdf(PDF).pages == [{'page': 1, 'start': 0, 'end': 3},
                                             {'page': 2, 'start': 4, 'end': 7}]


def test_result_binds_parser_identity_and_version(parser: FakeParser) -> None:
    parser.stdout = b'Body\f'
    result = pdf_text.parse_pdf(PDF)
    assert result.parser_version == '26.08.0'
    assert result.parser_id == pdf_text.parser_identity()


def _synthetic_pdf(pages: list[str]) -> bytes:
    """最小合法 PDF：每页一个文本流；空字符串页没有内容流对象。"""
    objects: dict[int, bytes] = {
        1: b'<< /Type /Catalog /Pages 2 0 R >>',
        2: f'<< /Type /Pages /Kids [{" ".join(f"{3 + 2 * i} 0 R" for i in range(len(pages)))}] '
           f'/Count {len(pages)} >>'.encode(),
        7: b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    }
    for index, body_text in enumerate(pages):
        page_number, content_number = 3 + 2 * index, 4 + 2 * index
        stream = f'BT /F1 18 Tf 72 720 Td ({body_text}) Tj ET'.encode() if body_text else b''
        objects[page_number] = (f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {content_number} 0 R '
                                f'/Resources << /Font << /F1 7 0 R >> >> >>').encode()
        objects[content_number] = (b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream
                                   + b'\nendstream')
    out = bytearray(b'%PDF-1.4\n')
    offsets: dict[int, int] = {}
    for number in sorted(objects):
        offsets[number] = len(out)
        out += f'{number} 0 obj\n'.encode() + objects[number] + b'\nendobj\n'
    xref, size = len(out), max(objects) + 1
    out += f'xref\n0 {size}\n'.encode() + b'0000000000 65535 f \n'
    for number in range(1, size):
        out += f'{offsets[number]:010d} 00000 n \n'.encode()
    out += f'trailer\n<< /Size {size} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode()
    return bytes(out)


@pytest.mark.skipif(shutil.which('pdftotext') is None, reason='native pdftotext not installed')
def test_native_pdftotext_reads_synthetic_two_page_pdf() -> None:
    """真实进程用例（非假实现）：合成两页，第 2 页为空；无网络、无真实文档。"""
    result = pdf_text.parse_pdf(_synthetic_pdf(['Native page one', '']))
    assert result.text.startswith('Native page one')
    assert len(result.pages) == 2
    assert result.pages[0] == {'page': 1, 'start': 0, 'end': result.text.index('\f')}
    assert result.text[result.pages[1]['start']:result.pages[1]['end']].strip() == ''
    assert re.fullmatch(r'[0-9][0-9A-Za-z._+-]*', result.parser_version)
    assert result.parser_id == pdf_text.parser_identity()
