"""Same public detail URL does not mean the same trial or source version."""
import pytest

from ciw2.domain.models import ExtractionResult
from ciw2.harness.llm import ScriptedLLM
from ciw2.pipeline.extraction import _call
from ciw2.service import Service
from ciw2.sources.http import register_text


@pytest.mark.parametrize('explicit',[True,False])
def test_same_url_sources_bind_only_explicit_version_actually_read(settings,monkeypatch,explicit):
    svc=Service(settings,llm_factory=lambda s:(ScriptedLLM([]),None))
    pid=svc.create_project('适应症',['C'])
    rc=svc.context(pid,svc.db.create_run(pid))
    ctx=rc.tool_ctx()
    url='https://www.chinadrugtrials.org.cn/clinicaltrials.searchlistdetail.dhtml'
    ids=[register_text(ctx,kind='chinadrugtrials',url=url,text=f'试验{i}原文') for i in (1,2)]
    facts=[{'entity':f'CTR2026000{i+1}','field':'design.control','value':f'试验{i+1}原文',
            'source_url':url,'quote':f'试验{i+1}原文',**({'source_id':sid} if explicit else {})} for i,sid in enumerate(ids)]
    def skill(*a):
        rc.cache['last_skill_source_ids']=ids
        return ExtractionResult.model_validate({'facts':facts})
    monkeypatch.setattr(rc,'skill',skill)
    out=_call(rc,'extract-design',{},'test:explicit')
    assert [f['source_id'] for f in out['facts']]==(ids if explicit else [None,None])


@pytest.mark.parametrize('wrong',['unread','foreign','url'])
def test_explicit_unread_or_foreign_source_never_falls_back_to_same_url(settings,monkeypatch,wrong):
    svc=Service(settings,llm_factory=lambda s:(ScriptedLLM([]),None))
    pid=svc.create_project('适应症',['C'])
    rc=svc.context(pid,svc.db.create_run(pid))
    url='https://example.org/current'
    good=register_text(rc.tool_ctx(),kind='web',url=url,text='实际读取原文')
    if wrong=='foreign':
        other=svc.create_project('另一项目',['C'])
        other_ctx=svc.context(other,svc.db.create_run(other)).tool_ctx()
    else:other_ctx=rc.tool_ctx()
    bad=register_text(other_ctx,kind='web',url=url+'/different' if wrong=='url' else url,text='另一个来源')
    def skill(*a):
        rc.cache['last_skill_source_ids']=[good,bad] if wrong=='url' else [good]
        return ExtractionResult.model_validate({'facts':[{'entity':'CTR20260001','field':'design.control',
            'value':'实际读取原文','source_id':bad,'source_url':url,'quote':'实际读取原文'}]})
    monkeypatch.setattr(rc,'skill',skill)
    assert _call(rc,'extract-design',{},'test:wrong')['facts'][0]['source_id'] is None


@pytest.mark.parametrize('explicit_wrong',[False,True])
def test_registry_detail_binding_must_match_fact_trial_even_when_both_versions_read(settings,monkeypatch,explicit_wrong):
    svc=Service(settings,llm_factory=lambda s:(ScriptedLLM([]),None))
    pid=svc.create_project('适应症',['C'])
    rc=svc.context(pid,svc.db.create_run(pid))
    url='https://www.chinadrugtrials.org.cn/clinicaltrials.searchlistdetail.dhtml'
    ids=[register_text(rc.tool_ctx(),kind='chinadrugtrials',url=url,text='两个来源共有的原文',
        raw=f'captured{i}'.encode(),meta={'request_context':{'registry':'chinadrugtrials','section':'trial_detail',
        'registry_id':f'CTR2026000{i+1}'}}) for i in range(2)]
    def skill(*a):
        rc.cache['last_skill_source_ids']=ids
        return ExtractionResult.model_validate({'facts':[{'entity':'CTR20260001','field':'design.control',
            'value':'两个来源共有的原文','source_url':url,'quote':'两个来源共有的原文',
            **({'source_id':ids[1]} if explicit_wrong else {})}]})
    monkeypatch.setattr(rc,'skill',skill)
    assert _call(rc,'extract-design',{},'test:trial-version')['facts'][0]['source_id']==(None if explicit_wrong else ids[0])


@pytest.mark.parametrize('extra',[{}, {'source_id':None}, {'source_id':'src_123456789abc'}])
def test_source_id_serialization_preserves_omitted_versus_explicit_binding(extra):
    result=ExtractionResult.model_validate({'facts':[{'entity':'CTR20260001','field':'design.control',
        'value':'原文完整对照','source_url':'https://example.org','quote':'原文完整对照',**extra}]})
    fact=result.model_dump()['facts'][0]
    assert ('source_id' in fact)==('source_id' in extra)
    if extra:assert fact['source_id']==extra['source_id']
