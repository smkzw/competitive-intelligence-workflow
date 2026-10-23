"""Current-project download fidelity, exact source versions and safe CSV cells."""
import csv
import io
import json

import pytest
from fastapi.testclient import TestClient

from ciw2.web.app import create_app


@pytest.fixture
def exported_project(settings):
    def no_models(_):
        raise AssertionError('Read-only export must not initialize models')

    app=create_app(settings,llm_factory=no_models,background=False)
    db=app.state.svc.db
    pid=db.create_project('原始研究资料',['B'])
    other=db.create_project('其他项目',['C'])
    entity,_=db.upsert_entity(pid,'trial','NCT00000001')
    old=db.add_source(pid,'ctgov','https://example.org/study','1'*64)
    db.add_source(pid,'ctgov','https://example.org/study','2'*64)
    foreign=db.add_source(other,'ctgov','https://example.org/other','3'*64)
    ids=[]
    for value,status in [(0,'verified'),(None,'unknown'),(False,'verified'),('', 'verified'),
                         ({'threshold':'≥16','logic':'AND'},'unverified')]:
        ids.append(db.add_fact({'project_id':pid,'entity_id':entity,'field':'result.primary.value',
            'value':value,'status':status,'tier':'critical','source_id':old,'quote':'=SUM(1,1)',
            'context':{'unit':'=not-a-formula','population':'ITT','timepoint':'Week 16','json_path':'$.results[0]'},
            'extracted_by':'code:test'}))
    invalid=db.add_fact({'project_id':pid,'entity_id':entity,'field':'design.sample_size','value':20,
        'status':'unverified','tier':'critical','source_id':foreign,'extracted_by':'code:test'})
    return app,db,pid,other,old,ids,invalid


def test_json_download_retains_all_types_and_exact_source_not_latest_url(exported_project):
    app,db,pid,_,old,ids,invalid=exported_project
    before=db.current_facts(pid)
    with TestClient(app) as client:
        response=client.get(f'/api/projects/{pid}/facts/export?format=json')
    assert response.status_code==200
    assert 'attachment;' in response.headers['content-disposition']
    assert response.headers['cache-control']=='no-store'
    payload=response.json()
    assert payload['schema_version']=='ciw2-facts-v1' and payload['project_id']==pid
    assert payload['scope']=='current_project_facts' and payload['fact_count']==6
    by_id={row['id']:row for row in payload['facts']}
    assert set(by_id)==set(ids+[invalid])
    assert [by_id[fid]['value'] for fid in ids]==[0,None,False,'',{'threshold':'≥16','logic':'AND'}]
    assert type(by_id[ids[0]]['value']) is int
    assert by_id[ids[1]]['value'] is None and by_id[ids[2]]['value'] is False
    for fid in ids:
        assert by_id[fid]['source']['id']==old and by_id[fid]['source']['digest']=='1'*64
        assert by_id[fid]['quote']=='=SUM(1,1)' and by_id[fid]['context']['timepoint']=='Week 16'
        assert by_id[fid]['entity']['name']=='NCT00000001'
    assert by_id[invalid]['source'] is None
    assert db.current_facts(pid)==before


def test_csv_download_is_type_faithful_utf8_and_formula_safe_with_explicit_escape_fields(exported_project):
    app,db,pid,_,_,ids,_=exported_project
    before=db.current_facts(pid)
    with TestClient(app) as client:
        response=client.get(f'/api/projects/{pid}/facts/export?format=csv&field_prefix=result.')
    assert response.status_code==200 and response.content.startswith(b'\xef\xbb\xbf')
    rows=list(csv.DictReader(io.StringIO(response.content.decode('utf-8-sig'))))
    assert len(rows)==5
    by_id={row['id']:row for row in rows}
    assert [json.loads(by_id[fid]['value_json']) for fid in ids]==[0,None,False,'',{'threshold':'≥16','logic':'AND'}]
    assert type(json.loads(by_id[ids[0]]['value_json'])) is int
    assert json.loads(by_id[ids[1]]['value_json']) is None and json.loads(by_id[ids[2]]['value_json']) is False
    for row in rows:
        assert row['quote']=="'=SUM(1,1)" and row['unit']=="'=not-a-formula"
        assert set(json.loads(row['csv_escaped_fields']))=={'quote','unit'}
        assert json.loads(row['context_json'])['population']=='ITT'
        assert row['source_digest']=='1'*64
    assert db.current_facts(pid)==before


@pytest.mark.parametrize('query,count',[('field_prefix=result.&status=unknown',1),('status=conflict',0)])
def test_export_filter_is_exact_without_filling_or_dropping_unknown(exported_project,query,count):
    app,_,pid,*_=exported_project
    with TestClient(app) as client:
        response=client.get(f'/api/projects/{pid}/facts/export?format=json&{query}')
    assert response.status_code==200 and response.json()['fact_count']==count


def test_export_rejects_missing_project_bad_format_and_respects_global_auth(exported_project,settings,monkeypatch):
    app,_,pid,*_=exported_project
    with TestClient(app) as client:
        assert client.get('/api/projects/prj_missing/facts/export?format=json').status_code==404
        assert client.get(f'/api/projects/{pid}/facts/export?format=html').status_code==422
    monkeypatch.setenv('CIW_ACCESS_TOKEN','local-test-token')
    with TestClient(create_app(settings,background=False)) as client:
        assert client.get(f'/api/projects/{pid}/facts/export?format=json').status_code==401
        assert client.get(f'/api/projects/{pid}/facts/export?format=json',
                          headers={'x-ciw-token':'local-test-token'}).status_code==200


def test_project_exposes_both_downloads_and_existing_facts_api_unchanged(exported_project):
    app,db,pid,*_=exported_project
    with TestClient(app) as client:
        page=client.get(f'/projects/{pid}')
        original=client.get(f'/api/projects/{pid}/facts')
    assert f'/api/projects/{pid}/facts/export?format=json' in page.text
    assert f'/api/projects/{pid}/facts/export?format=csv' in page.text
    assert original.json()==db.current_facts(pid)


@pytest.mark.parametrize('quote',['+cmd','-1+2','@SUM(A1:A2)',' \t=SUM(1,1)','\tplain'])
def test_csv_escapes_formula_prefixes_but_json_is_lossless(exported_project,quote):
    app,db,pid,_,_,ids,_=exported_project
    db.execute('UPDATE facts SET quote=? WHERE id=?',(quote,ids[0]))
    with TestClient(app) as client:
        raw=client.get(f'/api/projects/{pid}/facts/export?format=json').json()
        encoded=client.get(f'/api/projects/{pid}/facts/export?format=csv')
    assert next(r for r in raw['facts'] if r['id']==ids[0])['quote']==quote
    row=next(r for r in csv.DictReader(io.StringIO(encoded.content.decode('utf-8-sig'))) if r['id']==ids[0])
    assert row['quote']=="'"+quote and 'quote' in json.loads(row['csv_escaped_fields'])


@pytest.mark.parametrize('format',['json','csv'])
def test_nonfinite_values_fail_without_rewriting_or_false_null(exported_project,format):
    app,db,pid,_,_,ids,_=exported_project
    db.execute('UPDATE facts SET value=? WHERE id=?',('NaN',ids[0]))
    with TestClient(app) as client:
        response=client.get(f'/api/projects/{pid}/facts/export?format={format}')
    assert response.status_code==409
    assert db.one('SELECT value FROM facts WHERE id=?',(ids[0],))['value']=='NaN'


def test_historical_project_export_cannot_misrepresent_current_facts_as_asof(exported_project):
    app,db,pid,*_=exported_project
    db.execute('UPDATE projects SET cutoff_date=? WHERE id=?',('2020-01-01',pid))
    with TestClient(app) as client:
        response=client.get(f'/api/projects/{pid}/facts/export?format=json')
    assert response.status_code==409
