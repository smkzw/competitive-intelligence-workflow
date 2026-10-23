"""Profile enrichment reuses the extraction skill, pinned-source verifier and cache."""
from __future__ import annotations

import re
from typing import Any

from ciw2.domain.identity import name_key
from ciw2.domain.profile_evidence import FIELDS, SOURCE_CONTEXT
from ciw2.domain.profile_evidence import contains as _contains
from ciw2.pipeline.context import RunContext
from ciw2.verify.quote import normalize


def enrich(rc: RunContext) -> dict[str,Any]:
    from ciw2.pipeline.extraction import extract_drugs
    return extract_drugs(rc,'extract-results',lambda context,drug:{'mode':'identity_enrichment',
        'evidence_urls':drug['attrs'].get('evidence_urls',[])})


def context_of(proposal: dict[str,Any]) -> dict[str,Any]:
    source=proposal.get('source_context') or {}
    return {key:source[key] for key in SOURCE_CONTEXT if source.get(key) is not None}


def _names(rc: RunContext,proposal: dict[str,Any]) -> list[str]:
    from ciw2.render.drug_identity import drug_identities
    drugs=[d for d in drug_identities(rc.db,rc.project_id).values()
           if name_key(d['name'])==name_key(proposal['drug'])]
    return [n for d in drugs for n in [d['name'],*(r['name'] for r in d['name_refs'])]]


def anchored(rc: RunContext,proposal: dict[str,Any]) -> dict[str,Any]:
    """Expand only to one literal source paragraph; never infer aliases across a page."""
    if proposal['field'] not in FIELDS or proposal['field']=='status.china_mah_group':
        return proposal
    quote=proposal.get('quote')
    if not isinstance(quote,str) or not quote.strip():return proposal
    names=_names(rc,proposal)
    if any(_contains(quote,name) for name in names):return proposal
    source=rc.db.one('SELECT text_digest FROM sources WHERE project_id=? AND id=?',
                      (rc.project_id,proposal.get('source_id')))
    if not source:return proposal
    try:
        text=rc.cas.get_text(source['text_digest'])
    except (OSError,TypeError,ValueError):
        return proposal
    paragraphs={block.strip() for block in re.split(r'\n\s*\n',text) if len(block)<=2000
                and normalize(quote) in normalize(block) and any(_contains(block,name) for name in names)}
    return {**proposal,'quote':next(iter(paragraphs))} if len(paragraphs)==1 else proposal


