"""注册中心枚举与年龄单位的中文显示适配（离线纯函数测试）。"""

import pytest

from ciw2.render.labels import EM_DASH, age_label, phase_label, registry_label

FIXED_MAPPINGS = [
    ("trial_status", "NOT_YET_RECRUITING", "尚未招募"),
    ("trial_status", "RECRUITING", "正在招募"),
    ("trial_status", "ENROLLING_BY_INVITATION", "邀请入组"),
    ("trial_status", "ACTIVE_NOT_RECRUITING", "进行中，已停止招募"),
    ("trial_status", "COMPLETED", "已完成"),
    ("trial_status", "SUSPENDED", "暂停"),
    ("trial_status", "TERMINATED", "提前终止"),
    ("trial_status", "WITHDRAWN", "未启动即撤回"),
    ("trial_status", "UNKNOWN", "状态未知"),
    ("allocation", "RANDOMIZED", "随机分组"),
    ("allocation", "NON_RANDOMIZED", "非随机分组"),
    ("allocation", "NA", "不适用"),
    ("masking", "NONE", "开放标签"),
    ("masking", "SINGLE", "单盲"),
    ("masking", "DOUBLE", "双盲"),
    ("masking", "TRIPLE", "三盲"),
    ("masking", "QUADRUPLE", "四盲"),
    ("arm_type", "EXPERIMENTAL", "试验组"),
    ("arm_type", "ACTIVE_COMPARATOR", "阳性对照组"),
    ("arm_type", "PLACEBO_COMPARATOR", "安慰剂对照组"),
    ("arm_type", "SHAM_COMPARATOR", "模拟干预对照组"),
    ("arm_type", "NO_INTERVENTION", "无干预组"),
    ("arm_type", "OTHER", "其他组"),
]

FIXED_CATEGORIES = ["trial_status", "allocation", "masking", "arm_type"]


@pytest.mark.parametrize('raw,label',[('其它 其他说明:','其他'),('其他 其他说明：生物等效性研究','其他 · 生物等效性研究'),
                                    ('来源中的其他研究阶段','来源中的其他研究阶段')])
def test_phase_form_label_does_not_replace_or_invent_a_clinical_phase(raw,label):
    assert phase_label(raw)==label


@pytest.mark.parametrize('raw,expected',[
    ('score on a scale','分'),('Participants','人'),('percent change','%变化'),
    ('nanograms per milliliters (ng/mL)','ng/mL'),
    ('liter per micrograms (L/ug)','L/ug'),('per day','1/天'),
    ('probability of participants','probability of participants'),
    ('my unknown unit','my unknown unit'),('<img src=x>','<img src=x>'),
])
def test_measurement_unit_display_preserves_scale_and_unknown_text(raw,expected):
    assert registry_label(raw,'measure_unit')==expected


@pytest.mark.parametrize(("category", "code", "expected"), FIXED_MAPPINGS)
def test_fixed_canonical_mappings_are_exact(category, code, expected):
    assert registry_label(code, category) == expected


def test_em_dash_is_the_missing_marker():
    assert EM_DASH == "\u2014"


@pytest.mark.parametrize("category", FIXED_CATEGORIES)
def test_missing_registry_value_is_em_dash(category):
    assert registry_label(None, category) == EM_DASH
    assert registry_label("", category) == EM_DASH


@pytest.mark.parametrize("category", FIXED_CATEGORIES)
@pytest.mark.parametrize(
    "code",
    [
        "PAUSED",
        "Recruiting",
        " recruiting ",
        "RECRUITING ",
        "RECRUITING.",
        "ACTIVE_NOT_RECRUITING_EXTRA",
        "未知",
    ],
)
def test_unknown_codes_are_returned_verbatim(category, code):
    assert registry_label(code, category) == code


def test_unknown_categories_are_returned_verbatim():
    assert registry_label("RECRUITING", "phase") == "RECRUITING"
    assert registry_label("RECRUITING", "TRIAL_STATUS") == "RECRUITING"
    assert registry_label("RECRUITING", "") == "RECRUITING"
    assert registry_label("<b>RECRUITING</b>", "unknown") == "<b>RECRUITING</b>"


def test_nonstring_values_stringify_without_inference():
    assert registry_label(0, "trial_status") == "0"
    assert registry_label(7, "masking") == "7"
    assert registry_label(True, "allocation") == "True"
    assert age_label(18) == "18"
    assert age_label(0) == "0"


@pytest.mark.parametrize(
    "code",
    [
        "<script>alert(1)</script>",
        "<img src=x onerror=alert(1)>",
        "{{ 7*7 }}",
        "{% include 'x' %}",
        "&amp;",
    ],
)
def test_hostile_text_stays_plain_unmodified_text(code):
    for result in (registry_label(code, "trial_status"), age_label(code)):
        assert result == code
        assert type(result) is str
        assert not hasattr(result, "__html__")


def test_html_marked_string_input_is_returned_as_plain_text():
    class Marked(str):
        def __html__(self):
            return str(self)

    for result in (registry_label(Marked("<b>RECRUITING</b>"), "trial_status"), age_label(Marked("<b>18 Years</b>"))):
        assert type(result) is str
        assert not hasattr(result, "__html__")
        assert "<b>" in result


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("18 Years", "18岁"),
        ("6 Months", "6个月"),
        ("4 Weeks", "4周"),
        ("30 Days", "30天"),
        ("12 Hours", "12小时"),
        ("90 Minutes", "90分钟"),
        ("0 Years", "0岁"),
        ("0.0 Days", "0.0天"),
        ("18.50 Years", "18.50岁"),
        ("018 Days", "018天"),
    ],
)
def test_age_units_are_localized_without_conversion(raw, expected):
    assert age_label(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "N/A",
        "Unknown",
        "Not Reported",
        "-1 Years",
        "18-65 Years",
        ">=18 Years",
        "<= 65 Years",
        "18 years",
        "1 Year",
        "18Years",
        " 18 Years",
        "18 Years ",
        "18  Years",
        "18 Years\t",
        "18.0.0 Years",
        "18 Years (adult)",
        "years",
    ],
)
def test_unrecognized_age_formats_are_preserved(raw):
    assert age_label(raw) == raw


def test_missing_age_is_em_dash():
    assert age_label(None) == EM_DASH
    assert age_label("") == EM_DASH
