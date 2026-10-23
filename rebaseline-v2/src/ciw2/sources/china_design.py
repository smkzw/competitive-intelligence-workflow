"""Literal clinical-table projection; no model judgment, dose arithmetic or MAH inference."""
from __future__ import annotations

import re
from typing import Any

from ciw2.domain.tiers import tier_of
from ciw2.sources.china_detail import parse_capture

_MISSING=('登记人暂未填写该信息','暂未填写此信息','企业选择不公示')


def _absent(text: str) -> bool:
    return not text.strip() or any(word in text for word in _MISSING)


def _cells(rows: list[list[str]], prefix: str, table: dict | None = None) -> dict:
    found={}
    for i,row in enumerate(rows):
        if len(row)%2:
            raise ValueError('临床字段标签和值未配对')
        for j in range(0,len(row),2):
            label=row[j].strip()
            if label in found:
                raise ValueError('临床标量标签重复，不按顺序取首项')
            nested=[(k,n['rows']) for k,n in enumerate((table or {}).get('nested',[]))
                    if n['row']==i and n['column']==j+1]
            found[label]={'value':row[j+1],'path':f'{prefix}.rows[{i}][{j+1}]',
                          'quote':row[j]+'\t'+row[j+1],'nested':nested,'prefix':prefix}
    return found


def _fact(field: str, value: Any, node: dict, **context: Any) -> dict:
    return {'field':field,'value':value,'tier':tier_of(field),
        'status':'unknown' if value is None else 'verified','quote':node['quote'],
        'context':{'json_path':node['path'],**context},'extracted_by':'code:chinadrugtrials'}


def _table_cells(raw: dict) -> dict:
    found={}
    for i,table in enumerate(raw['tables']):
        cells=_cells(table['rows'],f'$.tables[{i}]',table)
        if found.keys() & cells.keys():
            raise ValueError('临床字段跨表重复，不按表顺序取首项')
        found.update(cells)
    return found


def _endpoints(cells: dict, facts: list, gaps: list) -> None:
    for label,field in (('主要终点指标及评价时间','design.primary_endpoint'),
                        ('次要终点指标及评价时间','design.secondary_endpoint')):
        node=cells.get(label)
        if node is None:
            gaps.append({'field':field,'reason':'source_field_absent'})
            continue
        if not node['nested']:
            gaps.append({'field':field,'reason':'not_reported' if _absent(node['value']) else 'unparsed_endpoint'})
            continue
        number,rows=node['nested'][0]
        if rows[0]!=['序号','指标','评价时间','终点指标选择']:
            raise ValueError('终点内表表头与当前来源不符')
        for i,row in enumerate(rows[1:],1):
            if len(row)==1 and _absent(row[0]):
                gaps.append({'field':field,'reason':'not_reported','json_path':node['path']})
                continue
            if len(row)!=4 or not row[1].strip():
                raise ValueError('终点内表记录不完整')
            endpoint={**node,'path':f"{node['prefix']}.nested[{number}].rows[{i}]",'quote':'\t'.join(row)}
            facts.append(_fact(field,{'measure':row[1],'time_frame':row[2] or None,'description':None},endpoint,
                timepoint=row[2] or None,registry_endpoint_class=row[3],source_ordinal=row[0]))


def _names(text: str) -> list[str]:
    names={}
    for line in text.splitlines():
        match=re.fullmatch(r'(中文通用名|英文通用名)\s*[:：](.*)',line.strip())
        if match and match[2].strip() and match[2].strip().upper() not in {'NA','N/A'}:
            names.setdefault(match[1],[]).append(match[2].strip())
    return names.get('中文通用名') or names.get('英文通用名') or []


def _arms(cells: dict, facts: list, gaps: list) -> None:
    arms=[]
    paths=[]
    quotes=[]
    for label,role in (('试验药','EXPERIMENTAL'),('对照药','COMPARATOR')):
        node=cells.get(label)
        if node is None or not node['nested']:
            gaps.append({'field':'design.arms','source_role':label,'reason':'not_reported' if node and _absent(node['value']) else 'source_field_absent'})
            continue
        number,rows=node['nested'][0]
        if rows[0]!=['序号','名称','用法']:
            raise ValueError('试验用药内表表头与当前来源不符')
        for i,row in enumerate(rows[1:],1):
            if len(row)==1 and _absent(row[0]):
                gaps.append({'field':'design.arms','source_role':label,'reason':'not_reported'})
                continue
            if len(row)!=3:
                raise ValueError('试验用药内表记录不完整')
            arms.append({'label':label+' '+row[0],'type':role,'description':row[2],
                         'interventions':_names(row[1]),'name_raw':row[1],'source_role':label,'source_ordinal':row[0]})
        paths.append(f"{node['prefix']}.nested[{number}]")
        quotes.append(node['quote'])
    if arms:
        facts.append(_fact('design.arms',arms,{'path':paths[0],'quote':'\n'.join(quotes)},source_paths=paths))


def _enrollment(cells: dict, facts: list, gaps: list) -> None:
    for label,field,kind in (('目标入组人数','design.sample_size','ESTIMATED'),
                            ('实际入组总人数','design.sample_size','ACTUAL'),
                            ('已入组人数','design.enrolled_to_date','ACTUAL')):
        node=cells.get(label)
        if node is None:
            gaps.append({'field':field,'source_label':label,'reason':'source_field_absent'})
            continue
        text=node['value']
        matches=list(re.finditer(r'(国内|国际)\s*[:：]\s*([^;；\n]*)(?:[;；]|$)',text))
        remainder=re.sub(r'(国内|国际)\s*[:：]\s*([^;；\n]*)(?:[;；]|$)','',text).strip()
        parts=[(m[1],m[2]) for m in matches] if matches and not remainder else [(None,text)]
        if len({p[0] for p in parts})!=len(parts):
            raise ValueError('入组人数地域重复，不择一或相加')
        for population,raw in parts:
            number=re.fullmatch(r'\s*([0-9]+)\s*(?:人|例)?\s*',raw)
            value=int(number[1]) if number else None
            if value is None:
                gaps.append({'field':field,'population':population,'source_label':label,
                             'reason':'not_reported' if _absent(raw) else 'unparsed_enrollment'})
            facts.append(_fact(field,value,node,enrollment_type=kind,population=population,
                               source_label=label,raw_enrollment=raw,stat_type='count_participants'))


def parse_design(raw: dict) -> dict:
    parsed=parse_capture(raw,ctr=raw['registry_id'],detail_id=raw['detail_id'])
    basic=_cells(raw['basic'],'$')
    # basic is an array, not an object with rows; keep exact captured JSON paths.
    for node in basic.values():node['path']=node['path'].replace('$.rows[','$.basic[')
    cells=_table_cells(raw)
    facts=[]
    gaps=[]
    for label,field in (('试验分期','design.phase'),('随机化','design.allocation'),
                        ('盲法','design.masking'),('性别','design.eligibility.sex'),
                        ('健康受试者','design.eligibility.healthy_volunteers'),
                        ('试验范围','design.trial_scope')):
        node=cells.get(label)
        if node:
            facts.append(_fact(field,None if _absent(node['value']) else node['value'],node))
    age=cells.get('年龄')
    if age:
        match=re.fullmatch(r'\s*(.+?)\s*[（(]最小年龄[）)]\s*至\s*(.+?)\s*[（(]最大年龄[）)]\s*',age['value'])
        value={'min':match[1],'max':match[2]} if match else None
        facts.append(_fact('design.eligibility.age',value,age))
        if value is None:
            gaps.append({'field':'design.eligibility.age','reason':'not_reported' if _absent(age['value']) else 'unparsed_age'})
    for label,field in (('申请人名称','trial.applicant'),('试验状态','status.trial')):
        node=basic[label]
        facts.append(_fact(field,None if _absent(node['value']) else node['value'],node))
    criteria=[(label,node) for label,node in cells.items() if label in {'入选标准','排除标准'}]
    text='\n'.join(label+'\n'+node['value'] for label,node in criteria)
    facts.append(_fact('design.eligibility.criteria',text,
        {'path':criteria[0][1]['path'],'quote':text},source_paths=[node['path'] for _,node in criteria]))
    _endpoints(cells,facts,gaps)
    _arms(cells,facts,gaps)
    _enrollment(cells,facts,gaps)
    drug_raw=parsed['registered_drug_name']
    parts=re.split(r'\s+曾用名\s*[:：]',drug_raw,maxsplit=1)
    drug_name=parts[0].strip() or drug_raw
    return {'facts':facts,'gaps':gaps,'attrs':{'registry':'chinadrugtrials','url':raw['url'],
        'title':parsed['title'],'conditions':[parsed['indication']],
        'registry_detail_id':parsed['detail_id'],'registry_applicant':parsed['applicant'],
        'registry_drug_name':drug_name,'registry_drug_name_raw':drug_raw,
        'registry_former_name':parts[1].strip() or None if len(parts)>1 else None}}
