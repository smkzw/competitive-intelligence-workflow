"""Read-only CDE new-review observations, never approval or indication decisions.

The native acceptance input locates/highlights a row in an unfiltered sequence.
Exact host lookup therefore follows complete source validation, not page count.
Only observed chemical IND and biological trial-application scopes are enabled.
The biological public UI uses LCSYSQ, not the hidden chemical IND control.
"""
from __future__ import annotations

import re
from typing import Any

from ciw2.sources.cde_capture import CaptureError, _check_url, _expected_rows, _parse_pagination

COLUMNS=('序号','受理号','药品名称','进入中心时间','审评状态','药理毒理','临床','药学','统计','临床药理','合规','备注')
SCOPE={'sequence':'化药','task_type':'IND','ui_acceptance_number':''}
SCOPES={'new_review_task_chemical_ind':SCOPE,
        'new_review_task_biological_trial':{'sequence':'生物','task_type':'LCSYSQ','ui_acceptance_number':''}}


def _legend(entries: Any) -> tuple[dict[str,str], str | None]:
    if not isinstance(entries,list):
        raise CaptureError('缺少来源图例')
    labels: dict[str,str] = {}
    blank = None
    for entry in entries:
        if not isinstance(entry,dict) or not isinstance(entry.get('text'),str) or not isinstance(entry.get('images'),list):
            raise CaptureError('来源图例结构不符')
        images=entry['images']
        text=entry['text'].strip()
        if images:
            if len(images)!=1 or not isinstance(images[0],str):
                raise CaptureError('图例图形关联不唯一')
            label=text.lstrip('：:').strip()
            if not label or images[0] in labels and labels[images[0]]!=label:
                raise CaptureError('来源图例映射冲突')
            labels[images[0]]=label
        elif text.startswith('空：'):
            value=text.partition('：')[2].strip()
            if blank is not None and value!=blank:
                raise CaptureError('空白图例冲突')
            blank=value
    return labels,blank


def _row(cells: Any, page: int, ordinal: int, locator: str, labels: dict[str,str], blank: str | None) -> dict[str,Any]:
    if not isinstance(cells,list) or len(cells)!=len(COLUMNS):
        raise CaptureError('审评任务行必须为完整十二列')
    for cell in cells:
        if not isinstance(cell,dict) or not isinstance(cell.get('text'),str) or not isinstance(cell.get('images'),list):
            raise CaptureError('审评任务单元格结构不符')
        if any(not isinstance(image,str) for image in cell['images']):
            raise CaptureError('图形来源字段不符')
    if cells[0]['text'].strip()!=str(ordinal):
        raise CaptureError('来源行号重复或与页位置不符')
    acceptance=cells[1]['text'].strip()
    if not re.fullmatch('[A-Z]+[0-9]+',acceptance) or not cells[2]['text'].strip():
        raise CaptureError('受理号或药名缺失/格式不符')
    disciplines,issues={},[]
    for index,name in enumerate(COLUMNS[5:11],5):
        cell=cells[index]
        images=cell['images']
        status=None
        if len(images)==1 and images[0] in labels:
            status=labels[images[0]]
            if cell['text'].strip() and cell['text'].strip()!=status:
                issues.append({'discipline':name,'reason':'conflicting_status_signals'})
                disciplines[name]={'status_text':None,'raw_cell':cell}
                continue
        elif not images:
            status=cell['text'].strip() or blank
        if status is None:
            issues.append({'discipline':name,'reason':'unmapped_status_icon' if images else 'missing_status_legend'})
        disciplines[name]={'status_text':status,'raw_cell':cell}
    return {'acceptance_number':acceptance,'drug_name':cells[2]['text'].strip(),
        'center_entry_date_text':cells[3]['text'].strip(),'review_status_text':cells[4]['text'].strip(),
        'disciplines':disciplines,'remarks_text':cells[11]['text'],'raw_cells':cells,
        'page':page,'row_number':ordinal,'locator':locator,'issues':issues}


def _page(value: Any, index: int, filters: dict[str,str]) -> dict[str,Any]:
    if not isinstance(value,dict) or value.get('section')!='new_review_task':
        raise CaptureError('不是新报审评任务来源')
    url=_check_url(value.get('url'))
    headers=value.get('headers')
    if value.get('filters')!=filters or not isinstance(headers,list) or tuple(headers)!=COLUMNS:
        raise CaptureError('审评范围或十二列表头不符')
    pagination=value.get('pagination')
    if not isinstance(pagination,dict) or not isinstance(pagination.get('text'),str):
        raise CaptureError('来源分页缺失')
    totals=set(re.findall(r'共\s*([0-9]+)\s*条',pagination['text']))
    if len(totals)!=1:
        raise CaptureError('来源总数缺失或冲突')
    current,size,total,count=_parse_pagination({**pagination,'total_records':int(totals.pop())})
    if not total or size is None:
        raise CaptureError('当前来源尚未验证整序列空状态，不能据此解释为零')
    rows=value.get('rows')
    if not isinstance(rows,list) or len(rows)!=_expected_rows(current,size,count,total):
        raise CaptureError('来源页行数不完整')
    labels,blank=_legend(value.get('legend'))
    parsed=[_row(row,current,(current-1)*size+i+1,f'$.pages[{index}].rows[{i}]',labels,blank)
            for i,row in enumerate(rows)]
    for row in parsed:
        row.update(source_url=url,scope_filters=dict(filters),observed_at=value.get('observed_at'))
    return {'page':current,'page_size':size,'total_records':total,'total_pages':count,'url':url,'rows':parsed}


def parse_review_capture(pages: list[dict[str,Any]], *, filters: dict[str,str],
                         acceptance_number: str | None = None, allow_partial: bool = False) -> dict[str,Any]:
    if filters not in SCOPES.values():
        raise CaptureError('当前只启用已观察的化药IND/生物临床试验申请序列，不把定位框当筛选')
    if type(allow_partial) is not bool or not isinstance(pages,list) or not pages:
        raise CaptureError('来源页或未完成标记不合法')
    wanted=None
    if acceptance_number is not None:
        if not isinstance(acceptance_number,str) or not re.fullmatch('[A-Z]+[0-9]+',acceptance_number.strip()):
            raise CaptureError('精确受理号查询格式不符')
        wanted=acceptance_number.strip()
    parsed=[_page(page,index,filters) for index,page in enumerate(pages)]
    identity={(p['url'],p['page_size'],p['total_records'],p['total_pages']) for p in parsed}
    if len(identity)!=1:
        raise CaptureError('来源范围/分页总数跨页变化')
    first=parsed[0]
    numbers=[p['page'] for p in parsed]
    if len(set(numbers))!=len(numbers):
        raise CaptureError('来源页重复')
    pending=sorted(set(range(1,first['total_pages']+1))-set(numbers))
    if pending and not allow_partial:
        raise CaptureError('审评序列不完整，不能当作查询闭合')
    rows=[row for page in sorted(parsed,key=lambda p:p['page']) for row in page['rows']]
    matches=[row for row in rows if wanted is None or row['acceptance_number']==wanted]
    return {'section':'new_review_task','filters':dict(filters),'complete':not pending,
        'total_records':first['total_records'],'total_pages':first['total_pages'],
        'pages_read':sorted(numbers),'pending_pages':pending,'matched_count':len(matches),'results':matches}
