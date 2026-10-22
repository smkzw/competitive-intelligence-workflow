from ciw2.verify.quote import check_quote

SRC = "At Week 16, IGA success: 35.6% (nemolizumab) vs 24.6% (placebo); “key” result —  p<0.001."


def test_exact_quote_with_value():
    r = check_quote(SRC, "IGA success: 35.6% (nemolizumab)", 35.6)
    assert r.ok and r.start is not None and r.end > r.start


def test_normalization():
    assert check_quote(SRC, '"key" result - p<0.001', None).ok
    assert check_quote(SRC, "iga   SUCCESS: 35.6%", 35.6).ok


def test_value_must_appear_in_quote():
    r = check_quote(SRC, "IGA success: 35.6% (nemolizumab)", 41.2)
    assert not r.ok


def test_fabricated_quote():
    assert not check_quote(SRC, "IGA success: 41.2%", 41.2).ok


def test_missing_quote():
    assert not check_quote(SRC, None, 35.6).ok


def test_number_boundary():
    assert not check_quote("rate was 135.6%", "rate was 135.6%", 35.6).ok


import pytest


@pytest.mark.parametrize(
    ("source", "value", "expected"),
    [
        ("The change was 1.5 points.", -1.5, False),
        ("The response was 10.1 percent.", 10, False),
        ("The sample size was 1,000 participants.", 1000, True),
        ("The change was -1.50 points.", -1.5, True),
        ("The concentration was 1e-3 units.", 0.001, True),
    ],
)
def test_numeric_verification_preserves_sign_precision_and_thousands(source, value, expected):
    assert check_quote(source, source, value).ok is expected
