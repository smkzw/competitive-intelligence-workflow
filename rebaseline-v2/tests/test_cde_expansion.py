from test_expansion import setup_expansion

from ciw2.pipeline.expansion import query_plan


def test_structured_cde_fields_receive_raw_entity_terms_not_a_disease_prefixed_query(settings):
    _,rc,_,_=setup_expansion(settings)
    plan=query_plan(rc)
    for query in (q for q in plan if q['registry']=='cde'):
        kind={'alias':'drug_name','company':'company','target':'target'}[query['kind']]
        assert query['arguments']['query_kind']==kind
        assert query['arguments']['query']==query['term']
    assert any(q['kind']=='company' and q['registry']=='cde' for q in plan)


def test_ctr_reverse_lookup_is_a_single_keyword_and_scope_is_adjudicated_later(settings):
    _,rc,_,_=setup_expansion(settings)
    for query in (q for q in query_plan(rc) if q['registry']=='chinadrugtrials'):
        assert query['arguments']['query']==query['term']
