"""Display native AE concepts without changing their scientific source identity."""
from __future__ import annotations


def safety_label(row: dict) -> str:
    field = row['field']
    if field == 'safety.sae.any':
        return '发生SAE的受试者'
    if field == 'safety.death.all_cause':
        return '全因死亡'
    if field == 'safety.other_ae.above_threshold':
        threshold = row.get('threshold_pct')
        return '其他AE' + (f'（报告阈值 {threshold}%）' if threshold is not None else '')
    term = row.get('term') or row.get('endpoint') or ''
    return {'safety.sae.term': 'SAE', 'safety.ae.term': '其他AE'}.get(field, '安全性记录') + (
        f' · {term}' if term else '')
