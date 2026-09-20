from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from pydantic import ValidationError as PydanticValidationError

ROOT = Path(__file__).resolve().parents[2]


def _project_contract_validator(schema: dict[str, object]) -> Draft202012Validator:
    from ci_workflow.domain.contracts import project_contract_format_checker

    return Draft202012Validator(
        schema,
        format_checker=project_contract_format_checker(),
    )


def test_contract_has_version_timezone_and_optional_historical_cutoff() -> None:
    assert (ROOT / "src/ci_workflow/domain/contracts.py").is_file()
    assert (ROOT / "schemas/project-contract.schema.json").is_file()
    from ci_workflow.domain.contracts import (
        ProjectContract,
        create_project_contract,
        validate_project_contract_document,
    )

    created_at = datetime(2026, 8, 11, 9, 30, tzinfo=ZoneInfo("Asia/Shanghai"))
    contract = create_project_contract(
        indication="慢性鼻窦炎伴鼻息肉",
        reports=["A", "C"],
        outputs=["html"],
        created_at=created_at,
    )
    assert contract.schema_version == "1.0"
    assert contract.contract_version == 1
    assert contract.timezone == "Asia/Shanghai"
    assert contract.data_cutoff.isoformat() == "2026-08-11T23:59:59.999999+08:00"
    assert [item.value for item in contract.reports] == ["A", "C"]
    assert [item.value for item in contract.outputs] == ["html"]
    assert contract.cutoff_was_user_supplied is False

    historical = create_project_contract(
        indication="慢性鼻窦炎伴鼻息肉",
        reports=["B"],
        outputs=["html"],
        timezone="America/New_York",
        cutoff="2024-02-29",
        created_at=created_at,
    )
    assert historical.data_cutoff.isoformat() == "2024-02-29T23:59:59.999999-05:00"
    assert historical.cutoff_was_user_supplied is True

    schema = json.loads(
        (ROOT / "schemas/project-contract.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    _project_contract_validator(schema).validate(contract.model_dump(mode="json"))
    assert validate_project_contract_document(
        contract.model_dump(mode="json"), schema
    ) == contract

    with pytest.raises(ValueError, match="IANA"):
        create_project_contract(
            indication="慢性鼻窦炎伴鼻息肉",
            reports=["A"],
            outputs=["html"],
            timezone="Shanghai",
            created_at=created_at,
        )

    valid_payload = contract.model_dump(mode="json")
    invalid_payloads = (
        {**valid_payload, "timezone": "Shanghai"},
        {**valid_payload, "outputs": ["pdf", "html"]},
        {**valid_payload, "data_cutoff": "2026-08-11T23:59:59.999999"},
        {**valid_payload, "created_at": "2026-08-11T09:30:00"},
    )
    for payload in invalid_payloads:
        with pytest.raises(ValidationError):
            _project_contract_validator(schema).validate(payload)
        with pytest.raises(PydanticValidationError):
            ProjectContract.model_validate(payload)

    with pytest.raises(PydanticValidationError):
        contract.indication = "哮喘"


def test_default_cutoff_is_fixed_at_creation_and_resume_next_day_does_not_move_it() -> None:
    from ci_workflow.domain.contracts import (
        create_project_contract,
        refresh_project_contract,
        resume_project_contract,
    )

    zone = ZoneInfo("Asia/Shanghai")
    contract = create_project_contract(
        indication="慢性鼻窦炎伴鼻息肉",
        reports=["A", "B", "C"],
        outputs=["html"],
        created_at=datetime(2026, 8, 11, 23, 59, tzinfo=zone),
    )
    resumed = resume_project_contract(
        contract,
        resumed_at=datetime(2026, 8, 12, 9, 0, tzinfo=zone),
    )
    assert resumed is contract
    assert resumed.contract_version == 1
    assert resumed.data_cutoff.isoformat() == "2026-08-11T23:59:59.999999+08:00"

    refreshed = refresh_project_contract(
        contract,
        cutoff="2026-08-12",
        created_at=datetime(2026, 8, 12, 10, 0, tzinfo=zone),
    )
    assert refreshed.contract_version == 2
    assert refreshed.project_id == contract.project_id
    assert refreshed.data_cutoff.isoformat() == "2026-08-12T23:59:59.999999+08:00"
    assert contract.contract_version == 1
    assert contract.data_cutoff.isoformat() == "2026-08-11T23:59:59.999999+08:00"

    dst_contract = create_project_contract(
        indication="哮喘",
        reports=["B"],
        outputs=["html"],
        timezone="America/New_York",
        cutoff="2026-03-08",
        created_at=datetime(2026, 3, 8, 12, 0, tzinfo=ZoneInfo("America/New_York")),
    )
    assert dst_contract.data_cutoff.isoformat() == "2026-03-08T23:59:59.999999-04:00"

    with pytest.raises(ValueError, match="必须晚于"):
        refresh_project_contract(
            contract,
            cutoff="2026-08-11",
            created_at=datetime(2026, 8, 12, 10, 0, tzinfo=zone),
        )
