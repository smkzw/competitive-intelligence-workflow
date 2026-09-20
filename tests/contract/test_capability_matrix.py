from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]


def test_capability_matrix_schema_matches_the_typed_runtime_contract(tmp_path: Path) -> None:
    from ci_workflow.application.capability_preflight import (
        CapabilitySelection,
        StaticCapabilityProbe,
        run_capability_preflight,
    )

    matrix = run_capability_preflight(
        CapabilitySelection(
            reports=("A", "B", "C"),
            outputs=("html",),
            source_routes=("public-http", "public-browser"),
            needs_document_ingestion=True,
            needs_ocr=False,
        ),
        host="local",
        probe=StaticCapabilityProbe(),
        project_root=tmp_path,
    )
    payload = matrix.model_dump(mode="json")
    schema = json.loads(
        (ROOT / "schemas/capability-matrix.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)
    assert payload["schema_version"] == "1.0"
    assert payload["host"] == "local"
    assert payload["overall_state"] == "ready"
    assert all(message.strip() for message in payload["user_messages"])

    duplicate = deepcopy(payload)
    duplicate["capabilities"][-1] = duplicate["capabilities"][0]
    with pytest.raises(JsonSchemaValidationError):
        Draft202012Validator(schema).validate(duplicate)
    from ci_workflow.application.capability_preflight import CapabilityMatrix

    with pytest.raises(ValidationError, match="完整且唯一"):
        CapabilityMatrix.model_validate(duplicate)
