import copy
import json

from ciw2.pipeline.stages import _compact


def test_observation_projection_does_not_reinsert_full_original_into_summary():
    raw='Inclusion Criteria:\nEASI >= 16 OR IGA >= 3\n'+'Full original context. '*1500
    row={'trial':'NCT00000001','sample_size':100,'eligibility_criteria':raw,
         'eligibility_thresholds':[{'rule_text':'EASI >= 16 OR IGA >= 3'}],
         'observations':{'eligibility_criteria':[{'fact_id':'criteria','status':'verified','value':raw,
             'context':{'json_path':'eligibilityModule.eligibilityCriteria'}}],
             'sample_size':[{'fact_id':'size','status':'verified','value':100,
                 'context':{'enrollment_type':'ESTIMATED'}}]}}
    before=copy.deepcopy(row)
    out=_compact(row)
    assert raw not in json.dumps(out)
    assert 'EASI >= 16 OR IGA >= 3' in json.dumps(out)
    assert out['observations']['sample_size'][0]['context']['enrollment_type']=='ESTIMATED'
    assert out['observations']['eligibility_criteria'][0]['fact_id']=='criteria'
    assert 'value' not in out['observations']['sample_size'][0]
    assert row==before


def test_competing_observations_retain_each_value_and_scientific_context():
    row={'observations':{'sample_size':[
        {'fact_id':'planned','status':'verified','value':100,'context':{'enrollment_type':'ESTIMATED'}},
        {'fact_id':'actual','status':'verified','value':90,'context':{'enrollment_type':'ACTUAL','population':'ITT'}}]}}
    assert _compact(row)==row
