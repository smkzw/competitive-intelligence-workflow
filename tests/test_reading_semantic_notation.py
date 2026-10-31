"""Equivalent source notation may differ in spelling, never in quantity, schedule or unit."""
import pytest

from ciw.verify.design_labels import _check


def checked(source, label):
    atom = dict(text=source, condition="", cohort_quote="", timeframe="")
    item = dict(clause_id="synthetic", quote=source, text_zh=label,
                condition_zh="", cohort_zh="", timeframe_zh="")
    return _check(item, {"synthetic": atom})[0]


CASES = [
    ("A biopsy within the last six months.", "过去6个月内的活检。"),
    ("Over the past decade, Forty patients were enrolled.", "过去10年，入组40例患者。"),
    ("Over the past decade, A hundred patients were enrolled.", "过去10年，入组100例患者。"),
    ("Biopsy within five years, or within one year for C3G.", "5年内活检，C3G则为1年内。"),
    ("Acthar 80 U two times per week", "Acthar 80 U，每周2次。"),
    ("Three 24-hour urine collections, once a week for 3 weeks.", "3次24小时尿液采集，每周1次，共3周。"),
    ("Rivaroxaban 10 mg once daily.", "Rivaroxaban 10 mg，每日1次。"),
    ("Infusion every 4 weeks for 100 weeks.", "每4周1次输注，共100周。"),
    ("Infusion twice a week or twice in 14 days.", "每周两次或14天内两次输注。"),
    ("* 2.Patients require a diagnostic biopsy.", "2. 患者须有诊断性活检。"),
    ("Proteinuria at least3.5g/24h or albumin <30g/l.", "蛋白尿≥3.5g/24h或白蛋白<30g/l。"),
    ("Biopsy less than 36 months before randomization.", "随机前少于36个月的活检。"),
    ("Amenorrhea for at least 12 consecutive months and contraception for 6 months.",
     "闭经至少连续12个月，避孕6个月。"),
    ("Biopsy shows fibrosis exceeding 50%.", "活检显示纤维化>50%。"),
    ("Rituximab 1 g IV on days 1 and 15.", "第1天和第15天静脉给予Rituximab 1 g。"),
    ("The proportion rose from 10.4% in 2003-2006 to 24.1% in 2011-2014.",
     "比例由2003-2006年的10.4%升至2011-2014年的24.1%。"),
    ("Proteinuria >=1 in grams per day (g/d), in one complete 24-hour collection.",
     "一次完整24小时收集，蛋白尿>=1 g/d。"),
]


@pytest.mark.parametrize("source,label", CASES)
def test_equivalent_source_spelling_and_schedule_are_readable(source, label):
    assert checked(source, label)


@pytest.mark.parametrize("source,label", [
    (CASES[0][0], "过去5个月内的活检。"),
    (CASES[1][0], "过去10年，入组4例患者。"),
    ("Biopsy within five years.", "1年内活检。"),
    (CASES[4][0], "Acthar 80 U，每周1次。"),
    (CASES[4][0], "Acthar 80 U，每月2次。"),
    (CASES[5][0], "2次24小时尿液采集，每周1次，共3周。"),
    (CASES[6][0], "Rivaroxaban 10 mg，每日2次。"),
    (CASES[7][0], "每4月1次输注，共100周。"),
    (CASES[7][0], "每4周2次输注，共100周。"),
    (CASES[8][0], "每周两次或14周内两次输注。"),
    (CASES[10][0], "蛋白尿>3.5g/24h或白蛋白<30g/l。"),
    (CASES[11][0], "随机前至多36个月的活检。"),
    (CASES[12][0], "闭经超过连续12个月，避孕6个月。"),
    (CASES[13][0], "活检显示纤维化≥50%。"),
    (CASES[14][0], "第1周和第15周静脉给予Rituximab 1 g。"),
    (CASES[15][0], "比例由2003-2007年的10.4%升至2011-2014年的24.1%。"),
    (CASES[16][0], "一次完整24小时收集，蛋白尿>=1 g/L。"),
])
def test_true_quantity_schedule_threshold_or_unit_changes_stay_rejected(source, label):
    assert not checked(source, label)


@pytest.mark.parametrize("source,label", [
    ("Proteinuria ≥4g/24h from two 24-hour urine samples within 2 weeks.",
     "蛋白尿≥4g/24h，采用2周内两次24小时尿液样本。"),
    ("At least twice in 2 weeks.", "2周内至少测量两次。"),
    ("Two proteinuria measurements >3.5g/day, with the second <50% below the first.",
     "两次蛋白尿测量>3.5g/day，第二次较第一次下降<50%。"),
    ("At least one testing of proteinuria >3.5g/24h.", "至少一次蛋白尿检测>3.5g/24h。"),
    ("Month 1, 3 and 5: 1g daily; Month 2, 4 and 6: 2mg daily.",
     "第1、3、5个月：每日1g；第2、4、6个月：每日2mg。"),
    ("If the most recent biopsy was performed >24 months before randomization.",
     "若最近一次活检在随机前>24个月进行。"),
])
def test_explicit_counts_and_shared_time_labels_do_not_turn_ordinals_into_quantities(source, label):
    assert checked(source, label)


@pytest.mark.parametrize("source,label", [
    ("The first complete 24-hour collection.", "第一次完整24小时尿液采集。"),
    ("The second complete 24-hour collection.", "第二次完整24小时尿液采集。"),
    ("The most recent complete 24-hour collection.", "最近一次完整24小时尿液采集。"),
    ("At least one of the following criteria must be met.", "以下标准须至少符合1项。"),
    ("Once every week.", "每周1次。"),
    ("Every week.", "每周1次。"),
    ("Twice every week.", "每周2次。"),
])
def test_reviewed_ordinal_explicit_choice_and_unnumbered_frequency_forms(source, label):
    assert checked(source, label)


@pytest.mark.parametrize("source,label", [
    ("At least one of the following criteria must be met.", "必须超过以下标准中的1项。"),
    ("Every week.", "每月1次。"),
    ("Once every week.", "每周2次。"),
])
def test_reviewed_choice_operator_and_unnumbered_frequency_changes_stay_rejected(source, label):
    assert not checked(source, label)


@pytest.mark.parametrize("field", ["text_zh", "condition_zh"])
def test_existing_verifier_repair_uses_field_scope_feedback_without_replacing_the_source(field):
    import json

    from ciw.verify.crosscheck import crosscheck
    from ciw.verify.design_labels import _atoms, _task
    from ciw.verify.llm import FakeBackend
    snippet = dict(text="The daily dose is 7 mg.", condition="Only if age ≥21 years.",
                   source_id="synthetic", field="eligibility",
                   context="The daily dose is 7 mg. Only if age ≥21 years and weight ≥50 kg.")
    atoms = _atoms(dict(rows=[dict(design_excerpts=[dict(snippets=[snippet])])]))
    atom = next(iter(atoms.values()))
    correct = dict(clause_id=atom["clause_id"], quote=atom["text"], text_zh="每日剂量7 mg。",
                   condition_zh="仅年龄≥21岁。", cohort_zh="", timeframe_zh="")
    wrong = {**correct, field: correct[field]+"体重≥50 kg。"}
    prompts = []
    def response(system, user):
        prompts.append(user)
        errors = user.split("确定性校验错误：", 1)
        guidance = json.loads(errors[1].split("\n", 1)[0])[0]["error"] if len(errors) == 2 else ""
        return json.dumps(dict(items=[correct if "context" in guidance else wrong]))
    result = crosscheck(_task(atoms), dict(extractor_a=FakeBackend("deepseek", "a", response),
                                          verifier=FakeBackend("glm", "b", response)))[0]
    assert result.status == "verified" and result.item == correct
    assert [call["role"] for call in result.calls] == ["extract", "verify", "verify_repair"]
    assert len(prompts) == 3 and snippet["context"].endswith("weight ≥50 kg.")
