"""All filled event claims belong to their selected literal evidence, not just the source page."""

import pytest

from ciw.verify.events import validate_event_item


def event(**changes):
    quote = "Drug-X已在中国获批用于CRSwNP，作为附加维持治疗。"
    item = dict(
        product_mention="Drug-X",
        event_type="approval",
        region="中国",
        date="",
        indication="CRSwNP",
        detail="作为附加维持治疗",
        quote=quote,
        detail_quote="作为附加维持治疗",
    )
    return item | changes


@pytest.mark.parametrize(
    "changes",
    [
        {"quote": "该适应症已在中国获批。"},
        {"quote": "Drug-X已在中国获批。"},
        {"detail": "获批作为后续维持治疗", "detail_quote": ""},
        {"detail_quote": "作为其他药物未控制患者的附加维持治疗"},
    ],
)
def test_event_cannot_borrow_names_indications_or_detail_from_outside_its_quote(changes):
    assert not validate_event_item(event(**changes))[0]


def test_target_indication_projection_does_not_assert_other_approved_indications_are_absent():
    assert validate_event_item(
        event(
            quote="Drug-X在欧盟获批用于severe asthma and CRSwNP。",
            region="欧盟",
            indication="CRSwNP",
            detail="获批用于CRSwNP",
            detail_quote="获批用于severe asthma and CRSwNP",
        )
    )[0]


def test_empty_detail_does_not_require_an_invented_detail_anchor():
    assert validate_event_item(event(detail="", detail_quote=""))[0]


@pytest.mark.parametrize(
    "quote,ok",
    [
        ("Drug-X针对CRSwNP的III期临床已启动。", False),
        ("Drug-X针对CRSwNP的III期临床已完成首例受试者入组。", True),
        ("Drug-X的CRSwNP试验计划于明年完成首例受试者入组。", False),
        ("The first patient has been enrolled in the Drug-X CRSwNP trial.", True),
        ("The first patient is expected to be enrolled in the Drug-X CRSwNP trial next year.", False),
    ],
)
def test_first_enrolment_event_needs_completed_first_participant_evidence(quote, ok):
    assert (
        validate_event_item(event(event_type="phase_start", quote=quote, region="", detail="", detail_quote=""))[0]
        == ok
    )


@pytest.mark.parametrize("include_product", [False, True])
def test_inbox_schema_and_ledger_preserve_selected_detail_evidence(cfg, resolver, ws, include_product):
    import json

    from ciw.sources.captures import extract_events
    from ciw.verify.llm import FakeBackend

    text = "MG-K10已在中国获批用于慢性鼻窦炎伴鼻息肉，作为附加维持治疗。"
    folder = ws.root / "captures/docs"
    folder.mkdir()
    (folder / "synthetic.txt").write_text(text)
    (folder / "synthetic.txt.meta.json").write_text(json.dumps({"kind": "company", "url": "https://example.org/news"}))
    item = event(
        product_mention="MG-K10",
        indication="慢性鼻窦炎伴鼻息肉",
        quote=text if include_product else text[len("MG-K10") :],
    )

    def reply(system, user):
        return json.dumps({"items": [item]})

    roles = {
        name: FakeBackend(family, family, reply) for name, family in (("extractor_a", "deepseek"), ("verifier", "glm"))
    }
    rows, issues, _ = extract_events(ws, cfg, resolver, roles)
    ledger = ws.verifications()
    if include_product:
        assert len(rows) == 1 and rows[0].status == "verified" and not issues
    else:
        assert not rows and any(issue["kind"] == "event_needs_review" for issue in issues)
        assert {record["status"] for record in ledger.values()} == {"needs_review"}
    assert next(iter(ledger.values()))["item"]["detail_quote"] == "作为附加维持治疗"


def test_verbatim_detail_is_already_its_own_anchor():
    assert validate_event_item(event(detail_quote=""))[0]


@pytest.mark.parametrize("mention", ["Drug-X2", "Other-Drug"])
def test_product_mention_needs_its_complete_source_identity(mention):
    assert not validate_event_item(event(product_mention=mention))[0]


def test_detail_numbers_must_belong_to_its_selected_anchor():
    quote = "Drug-X在中国获批用于CRSwNP，研究A应答率50%，研究B应答率90%。"
    assert not validate_event_item(event(quote=quote, detail="研究A应答率90%", detail_quote="研究A应答率50%"))[0]
    assert validate_event_item(event(quote=quote, detail="研究A应答率50%", detail_quote="研究A应答率50%"))[0]


@pytest.mark.parametrize(
    "quote",
    [
        "Drug-X尚未完成针对CRSwNP的首例患者入组。",
        "Drug-X未完成CRSwNP首例患者入组。",
        "Drug-X没有完成CRSwNP首例患者入组。",
        "No first patient has been enrolled in the Drug-X CRSwNP trial.",
        "The trial has not enrolled its first patient for Drug-X in CRSwNP.",
    ],
)
def test_negated_first_enrolment_is_not_a_completed_milestone(quote):
    assert not validate_event_item(event(event_type="phase_start", quote=quote, detail="", detail_quote=""))[0]
