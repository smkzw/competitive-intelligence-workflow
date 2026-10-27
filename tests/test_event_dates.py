import pytest

from ciw.verify.crosscheck import _date_in_quote


@pytest.mark.parametrize(
    "value,quote,ok",
    [
        ("2025-01-03", "Approved 3 January 2025", True),
        ("2025-01-03", "Approved January 3, 2025", True),
        ("2025-01-03", "2025年1月3日获批", True),
        ("2025-01-03", "Approved 2025-01-13", False),
        ("2025-01-03", "Approved January 2025", False),
        ("2025-13-03", "2025-13-03", False),
        ("2025-02-30", "2025-02-30", False),
        ("2025-01", "Approved January 2025", True),
    ],
)
def test_whole_event_date_must_be_supported(value, quote, ok):
    assert _date_in_quote(value, quote) is ok
