from dataclasses import replace

import pytest
from test_expansion import setup_expansion

from ciw2.pipeline import expansion


@pytest.mark.parametrize('registry',['chinadrugtrials','cde'])
def test_complete_browser_source_is_accepted_and_space_change_invalidates_same_run_cache(settings,registry):
    _,rc,_,calls=setup_expansion(settings)
    query=next(q for q in expansion.query_plan(rc) if q['registry']==registry)
    original=rc.registry.get('china_registry_search').fn
    def browser(ctx,args):
        original(ctx,args)
        return {'mode':'browser','complete':True,'count':0,'results':[],'persisted':True}
    rc.registry.get('china_registry_search').fn=browser
    assert expansion._source(rc,query,True)[1]=='fetched'
    count=len(calls)
    assert expansion._source(rc,query,True)[1]=='cached' and len(calls)==count
    rc.settings=replace(rc.settings,china_ego_space_id=59)
    assert expansion._source(rc,query,True)[1]=='fetched' and len(calls)==count+1


def test_partial_browser_payload_is_never_an_accepted_empty_source(settings):
    _,rc,_,_=setup_expansion(settings)
    query=next(q for q in expansion.query_plan(rc) if q['registry']=='chinadrugtrials')
    rc.registry.get('china_registry_search').fn=lambda *a:{'mode':'browser','complete':False,'count':0,'results':[]}
    assert expansion._source(rc,query,True)[1]=='failed'


def test_structured_registry_candidates_are_not_sent_to_a_second_extraction_model(settings):
    _,rc,_,_=setup_expansion(settings)
    query=next(q for q in expansion.query_plan(rc) if q['registry']=='chinadrugtrials')
    rc.skill=lambda *a,**k:pytest.fail('deterministic registry rows were already persisted')
    source={'digest':'f'*64,'payload':{'mode':'browser','complete':True,'persisted':True,
                       'results':[{'ctr':f'CTR{20260000+i}','drug_name':f'Original label {i}'} for i in range(464)]}}
    expansion._interpret(rc,query,source,lambda res:pytest.fail('no repeated model adoption'))


def test_distinct_post_queries_at_one_public_url_keep_their_own_source_recovery(settings):
    from ciw2.sources.http import register_text

    _,rc,_,calls=setup_expansion(settings)
    queries=[q for q in expansion.query_plan(rc) if q['registry']=='chinadrugtrials'][:2]
    original=rc.registry.get('china_registry_search').fn
    def browser(ctx,args):
        original(ctx,args)
        sid=register_text(ctx,kind='chinadrugtrials',
            url='https://www.chinadrugtrials.org.cn/clinicaltrials.searchlist.dhtml',text=args.query,
            meta={'request_context':{'method':'POST','registry':'chinadrugtrials','query':args.query}})
        return {'mode':'browser','complete':True,'count':0,'results':[],'source_id':sid,'persisted':True}
    rc.registry.get('china_registry_search').fn=browser
    for query in queries:
        assert expansion._source(rc,query,True)[1]=='fetched'
    assert len(calls)==2
    assert expansion._source(rc,queries[0],True)[1]=='cached'
    assert len(calls)==2
    first_query=queries[0]['arguments']['query']
    register_text(rc.tool_ctx(),kind='chinadrugtrials',
        url='https://www.chinadrugtrials.org.cn/clinicaltrials.searchlist.dhtml',text='new source version',
        meta={'request_context':{'method':'POST','registry':'chinadrugtrials','query':first_query}})
    assert expansion._source(rc,queries[0],True)[1]=='fetched'
    assert len(calls)==3


def test_post_scope_source_lookup_is_project_scoped_and_keeps_legacy_default(settings):
    from ciw2.sources.http import register_text, source_by_url

    _,rc,_,_=setup_expansion(settings)
    ctx=rc.tool_ctx()
    url='https://www.chinadrugtrials.org.cn/clinicaltrials.searchlist.dhtml'
    scope={'method':'POST','registry':'chinadrugtrials','query':'specific'}
    first=register_text(ctx,kind='chinadrugtrials',url=url,text='first',meta={'request_context':scope})
    other_scope={**scope,'query':'other'}
    second=register_text(ctx,kind='chinadrugtrials',url=url,text='second',meta={'request_context':other_scope})
    assert source_by_url(ctx,url)['id']==second
    assert source_by_url(ctx,url,request_context=dict(reversed(list(scope.items()))))['id']==first
    ctx.project_id=ctx.db.create_project('另一项目',['C'])
    assert source_by_url(ctx,url,request_context=scope) is None
