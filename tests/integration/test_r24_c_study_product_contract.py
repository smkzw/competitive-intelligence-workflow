"""C keeps explicit absent product identity without weakening known references."""
import json
from pathlib import Path

import jsonschema
import pytest

from ci_workflow.application.ctgov_c_design_projection import CtgovCTrialBinding
from ci_workflow.renderers.portal.report_c import ReportCPortalData
from ci_workflow.reports.c.contracts import DesignObservation

ROOT = Path(__file__).resolve().parents[2]


def _payload() -> dict:
    return json.loads((ROOT / 'fixtures/acceptance/full-matrix-v1/inputs/report-c-data.json')
                      .read_bytes())


def test_observation_and_schema_allow_explicit_null_not_missing_or_empty() -> None:
    original = _payload()['observations'][0]
    schema = json.loads((ROOT / 'schemas/reports/c-design-observation.schema.json').read_bytes())
    changed = {**original, 'product_id': None}
    observation = DesignObservation.model_validate(changed)
    assert observation.product_id is None
    jsonschema.Draft202012Validator(schema).validate(observation.model_dump(mode='json'))
    for invalid in ({key: value for key, value in changed.items() if key != 'product_id'},
                    {**changed, 'product_id': ''}, {**changed, 'product_id': ' '}):
        with pytest.raises(ValueError):
            DesignObservation.model_validate(invalid)
    assert DesignObservation.model_validate(original).model_dump(mode='json')['product_id'] \
        == original['product_id']


def test_registry_binding_explicit_null_is_not_missing_trial_binding() -> None:
    binding = CtgovCTrialBinding(trial_id='nct00001999', product_id=None)
    assert binding.product_id is None and binding.model_dump()['product_id'] is None
    with pytest.raises(ValueError):
        CtgovCTrialBinding.model_validate({'trial_id': 'nct00001999'})
    with pytest.raises(ValueError):
        CtgovCTrialBinding(trial_id='nct00001999', product_id=' ')


def test_pure_study_c_catalog_retains_every_observation() -> None:
    payload = _payload()
    payload['products'] = []
    payload['trials'] = [{**row, 'product_id': None} for row in payload['trials']]
    payload['observations'] = [{**row, 'product_id': None} for row in payload['observations']]
    report = ReportCPortalData.model_validate(payload)
    assert not report.products
    assert len(report.observations) == len(payload['observations'])
    assert all(row.product_id is None for row in (*report.trials, *report.observations))
    assert set(report.trial_ids) == {row['id'] for row in payload['trials']}


def test_known_unknown_identity_drift_and_wrong_known_reference_rejected() -> None:
    payload = _payload()
    payload['observations'][0]['product_id'] = None
    with pytest.raises(ValueError, match='产品.*不一致'):
        ReportCPortalData.model_validate(payload)
    payload['observations'][0]['product_id'] = 'invented-product'
    with pytest.raises(ValueError, match='未知产品'):
        ReportCPortalData.model_validate(payload)
