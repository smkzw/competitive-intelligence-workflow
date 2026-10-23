"""Literal public NMPA product records; no indication or group inference.

This parser consumes visible public record rows, not browser storage/scripts. It
does not fetch, adopt a fact, decide approval of an indication, or merge a holder
with its manufacturer/domestic responsible person. Unhandled catalogues need
their own observed schema rather than speculative compatibility.
"""
from __future__ import annotations

import base64
import binascii
import re
from typing import Any
from urllib.parse import parse_qs, urlsplit

FOREIGN='境外生产药品'
DOMESTIC='境内生产药品'
FIELDS={FOREIGN:{'registration_number':'注册证号','drug_name':'产品名称（中文）','drug_name_en':'产品名称（英文）',
    'holder_name_zh':'上市许可持有人中文名称','holder_name_en':'上市许可持有人英文名称',
    'manufacturer_name_zh':'生产厂商（中文）','manufacturer_name_en':'生产厂商（英文）',
    'domestic_responsible_person':'境内责任人名称','strength':'规格（中文）',
    'issue_date':'发证日期','valid_until':'有效期截止日'},
    DOMESTIC:{'registration_number':'批准文号','drug_name':'产品名称','drug_name_en':'英文名称',
    'holder_name_zh':'上市许可持有人','manufacturer_name_zh':'生产单位','strength':'规格',
    'approval_date':'批准日期'}}


def _url(value: Any) -> str:
    if not isinstance(value,str) or any(c.isspace() for c in value):
        raise ValueError('NMPA公开详情来源地址无效')
    try:
        url=urlsplit(value)
        if (url.scheme!='https' or url.hostname!='datasearch.nmpa.gov.cn'
                or url.port not in (None,443) or url.username or url.password
                or url.path!='/datasearch/search-info.html'):
            raise ValueError('NMPA详情来源域或路径不符')
        query=parse_qs(url.query,keep_blank_values=True,strict_parsing=True)
        if set(query)!={'nmpa'} or len(query['nmpa'])!=1:
            raise ValueError('NMPA公开详情参数不符')
        # These are the public link's two record IDs, never an authentication token.
        link=base64.b64decode(query['nmpa'][0],validate=True).decode('ascii')
        if not re.fullmatch(r'id=[0-9a-f]{32}&itemId=[0-9a-f]{32}',link):
            raise ValueError('NMPA公开记录定位格式不符')
    except (ValueError,UnicodeError,binascii.Error) as exc:
        raise ValueError('NMPA公开详情来源绑定无效') from exc
    return value


def _fields(rows: Any) -> tuple[dict[str,str],dict[str,str]]:
    if not isinstance(rows,list) or not rows:
        raise ValueError('NMPA公开字段表缺失')
    fields,locators={},{}
    for i,row in enumerate(rows):
        if not isinstance(row,list) or len(row)!=2 or not all(isinstance(v,str) for v in row):
            raise ValueError('NMPA公开字段行不是标签和值')
        label=row[0].strip()
        if not label or label in fields:
            raise ValueError('NMPA公开字段标签缺失或重复，不按顺序择一')
        fields[label]=row[1]
        locators[label]=f'$.rows[{i}][1]'
    return fields,locators


def _value(fields: dict[str,str],label: str) -> str | None:
    text=fields.get(label,'').strip()
    return None if not text or re.fullmatch(r'[-—－–]+',text) else text


def parse_detail(raw: dict[str,Any],*,registration_number: str,category: str) -> dict[str,Any]:
    if not isinstance(raw,dict) or category not in FIELDS or raw.get('category')!=category:
        raise ValueError('当前已观察合同仅支持境内或境外生产药品详情')
    if not re.fullmatch(r'国药准字[A-Z]{1,3}[0-9]{8}',registration_number):
        raise ValueError('待核对的注册证号格式不符')
    url=_url(raw.get('url'))
    fields,locators=_fields(raw.get('rows'))
    names=FIELDS[category]
    heading=raw.get('heading')
    if (not isinstance(heading,str)
            or not re.fullmatch(re.escape(category)+r'\s*——[“"]'+re.escape(registration_number)+r'[”"]基本信息',heading)
            or fields.get(names['registration_number'])!=registration_number):
        raise ValueError('NMPA详情标题、原字段与所选注册证号不一致')
    keys=set().union(*(mapping.keys() for mapping in FIELDS.values()))
    result={key:_value(fields,names[key]) if key in names else None for key in keys}
    if not (result['drug_name'] or result['drug_name_en']):
        raise ValueError('NMPA产品名称原字段缺失')
    return {**result,'registration_number':registration_number,'category':category,'url':url,
        'holder_name':result['holder_name_zh'] or result['holder_name_en'],
        'manufacturer_name':result['manufacturer_name_zh'] or result['manufacturer_name_en'],
        'raw_fields':fields,'field_locators':{key:locators.get(label) for key,label in names.items()}}
