"""Literal NMPA certificate projection; manufacturer/responsible person is not MAH."""
import base64
from copy import deepcopy

import pytest


def record():
    token=base64.b64encode(('id='+'a'*32+'&itemId='+'b'*32).encode()).decode()
    return {'url':'https://datasearch.nmpa.gov.cn/datasearch/search-info.html?nmpa='+token,
        'category':'境外生产药品','heading':'境外生产药品 ——“国药准字SJ20240001”基本信息',
        'rows':[['注册证号','国药准字SJ20240001'],['原注册证号','S20190001'],
            ['产品名称（中文）','药物甲注射液'],['产品名称（英文）','Drug A Injection'],
            ['上市许可持有人中文名称','————'],['上市许可持有人英文名称','Holder Legal Entity'],
            ['生产厂商（英文）','Factory Company'],['境内责任人名称','境内责任人甲公司'],
            ['发证日期','2025-02-18'],['有效期截止日','2030-01-23'],
            ['规格（中文）','300mg（2.0mL）/支'],['注','详情']]}


def parse(raw):
    from ciw2.sources.nmpa_capture import parse_detail
    return parse_detail(raw,registration_number='国药准字SJ20240001',category='境外生产药品')


def test_exact_certificate_uses_explicit_holder_not_domestic_responsible_person_or_factory():
    raw=record()
    before=deepcopy(raw)
    result=parse(raw)
    assert result['holder_name']=='Holder Legal Entity'
    assert result['holder_name_zh'] is None and result['holder_name_en']=='Holder Legal Entity'
    assert result['manufacturer_name']=='Factory Company'
    assert result['domestic_responsible_person']=='境内责任人甲公司'
    assert result['drug_name']=='药物甲注射液' and result['strength']=='300mg（2.0mL）/支'
    assert result['issue_date']=='2025-02-18' and result['valid_until']=='2030-01-23'
    assert 'first_approval_date' not in result and 'indication' not in result and 'group' not in result
    assert result['raw_fields']['原注册证号']=='S20190001'
    assert raw==before


def test_missing_holder_does_not_borrow_another_organization():
    raw=record()
    raw['rows']=[r for r in raw['rows'] if not r[0].startswith('上市许可持有人')]
    assert parse(raw)['holder_name'] is None


def test_source_chinese_holder_is_preferred_without_guessing_translation():
    raw=record()
    next(r for r in raw['rows'] if r[0]=='上市许可持有人中文名称')[1]='持有人甲法律实体'
    assert parse(raw)['holder_name']=='持有人甲法律实体'


def domestic():
    return {**record(), 'category':'境内生产药品',
        'heading':'境内生产药品 ——“国药准字S20240001”基本信息',
        'rows':[['批准文号','国药准字S20240001'],['产品名称','药物甲注射液'],
            ['英文名称','Drug A Injection'],['上市许可持有人','持有人甲法律实体'],
            ['生产单位','生产企业乙'],['批准日期','2024-09-10'],['规格','300mg（2ml）/瓶']]}


def test_domestic_explicit_holder_and_approval_date_are_not_foreign_certificate_dates():
    from ciw2.sources.nmpa_capture import parse_detail
    raw=domestic()
    before=deepcopy(raw)
    result=parse_detail(raw,registration_number='国药准字S20240001',category='境内生产药品')
    assert result['holder_name']=='持有人甲法律实体' and result['manufacturer_name']=='生产企业乙'
    assert result['approval_date']=='2024-09-10'
    assert result['issue_date'] is None and result['valid_until'] is None
    assert result['domestic_responsible_person'] is None
    assert result['field_locators']['holder_name_zh']=='$.rows[3][1]'
    assert 'indication' not in result and 'group' not in result and raw==before


def test_domestic_missing_holder_does_not_inherit_manufacturer():
    from ciw2.sources.nmpa_capture import parse_detail
    raw=domestic()
    raw['rows']=[r for r in raw['rows'] if r[0]!='上市许可持有人']
    result=parse_detail(raw,registration_number='国药准字S20240001',category='境内生产药品')
    assert result['holder_name'] is None and result['manufacturer_name']=='生产企业乙'


@pytest.mark.parametrize('change',[
    lambda r:r.update(url=r['url'].replace('https://datasearch.nmpa.gov.cn','https://example.org')),
    lambda r:r.update(url=r['url'].replace('https://','http://')),
    lambda r:r.update(url=r['url']+'&session=private'),
    lambda r:r.update(url=r['url'].replace('?nmpa=','?token=')),
    lambda r:r.update(heading=r['heading'].replace('SJ20240001','SJ20240002')),
    lambda r:r.update(category='境内生产药品'),
    lambda r:r['rows'].append(['上市许可持有人英文名称','Different Holder']),
    lambda r:r['rows'][0].__setitem__(1,'国药准字SJ20240002'),
    lambda r:r['rows'].append(['坏行']),
])
def test_unbound_foreign_duplicate_or_malformed_capture_is_not_a_certificate(change):
    raw=record()
    change(raw)
    with pytest.raises(ValueError):parse(raw)
