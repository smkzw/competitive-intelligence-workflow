"""Explicit stage/Skill/source dependency groups; no whole-package fingerprint."""
from typing import Any

_RENDER_MODULES = (
    'ciw2.domain.availability',
    'ciw2.domain.identity',
    'ciw2.domain.outcomes',
    'ciw2.domain.profile_evidence',
    'ciw2.domain.semantics',
    'ciw2.pipeline.queries',
    'ciw2.store.db',
    'ciw2.verify.assessment',
    'ciw2.render.design',
    'ciw2.render.drug_identity',
    'ciw2.render.drug_profile',
    'ciw2.render.eligibility',
    'ciw2.render.endpoint_label',
    'ciw2.render.labels',
    'ciw2.render.parameter_reading',
    'ciw2.render.portal',
    'ciw2.render.publish',
    'ciw2.render.registration',
    'ciw2.render.result_identity',
    'ciw2.render.results',
    'ciw2.render.study_catalog', 'ciw2.render.safety',
    'ciw2.render.trial_identity',
)

# Component tuples are explicit on purpose: a small, reviewable grouping for the
# current 16-stage plan instead of hashing the whole package for every stage.
_FN = 'fn'
_CONST = 'const'
_MODULE = 'module'
_MODULES = 'modules'
_ASSETS = 'assets'
_FILES = 'files'

_STAGE_CODE: dict[str, tuple[tuple[Any, ...], ...]] = {
    'intake': ((_FN, 'ciw2.pipeline.stages', 'intake'),),
    'universe_china': (
        (_FN, 'ciw2.pipeline.stages', '_universe'),
        (_FN, 'ciw2.pipeline.stages', '_persist_universe'),
        (_MODULE, 'ciw2.pipeline.queries'),
        (_CONST, 'ciw2.domain.identity', 'CODE_HASH'),
    ),
    'universe_global': (
        (_FN, 'ciw2.pipeline.stages', '_universe'),
        (_FN, 'ciw2.pipeline.stages', '_persist_universe'),
        (_MODULE, 'ciw2.pipeline.queries'),
        (_CONST, 'ciw2.domain.identity', 'CODE_HASH'),
    ),
    'candidate_triage': (
        (_FN, 'ciw2.pipeline.stages', 'coverage_review'),
        (_CONST, 'ciw2.pipeline.scope', 'CODE_HASH'),
    ),
    'universe_expand': (
        (_FN, 'ciw2.pipeline.stages', 'universe_expand'),
        (_CONST, 'ciw2.pipeline.expansion', 'CODE_HASH'),
        (_FILES, (
            'sources/china_browser.mjs',
            'sources/cde_browser.mjs',
            'sources/cde_priority.mjs',
            'sources/cde_review_browser.mjs',
        )),
    ),
    'coverage_review': (
        (_FN, 'ciw2.pipeline.stages', 'coverage_review'),
        (_CONST, 'ciw2.pipeline.scope', 'CODE_HASH'),
    ),
    'trial_evidence': (
        (_FN, 'ciw2.pipeline.stages', 'trial_evidence'),
        (_FN, 'ciw2.pipeline.stages', '_matches'),
        (_MODULE, 'ciw2.pipeline.china_evidence'),
        (_MODULE, 'ciw2.pipeline.nmpa_evidence'),
        (_MODULE, 'ciw2.pipeline.cde_evidence'),
        (_MODULE, 'ciw2.sources.cde_adoption'),
        (_MODULE, 'ciw2.pipeline.queries'),
        (_CONST, 'ciw2.domain.identity', 'CODE_HASH'),
        (_CONST, 'ciw2.pipeline.stages', 'CTGOV_CODE_HASH'),
        (_CONST, 'ciw2.sources.china_ingest', 'EXTRACTOR_VERSION'),
        (_MODULES, (
            'ciw2.sources.ctgov',
            'ciw2.sources.china_ingest',
            'ciw2.sources.china_detail',
            'ciw2.sources.china_design',
            'ciw2.sources.nmpa_ingest',
            'ciw2.sources.nmpa_detail',
            'ciw2.sources.nmpa_capture',
            'ciw2.sources.cde_priority',
            'ciw2.sources.cde_review_browser',
            'ciw2.sources.cde_capture',
            'ciw2.sources.cde_review_capture',
            'ciw2.sources.cde_browser',
            'ciw2.sources.cde_resume',
            'ciw2.sources.china_browser',
            'ciw2.sources.http',
        )),
        (_FILES, (
            'sources/china_detail.mjs',
            'sources/china_browser.mjs',
            'sources/nmpa_detail.mjs',
            'sources/cde_priority.mjs',
            'sources/cde_review_browser.mjs',
            'sources/cde_browser.mjs',
        )),
    ),
    'trial_scope_review': (
        (_FN, 'ciw2.pipeline.stages', 'trial_scope_review'),
        (_CONST, 'ciw2.pipeline.scope', 'CODE_HASH'),
    ),
    'enrich_drugs': (
        (_MODULE, 'ciw2.pipeline.profile'),
        (_CONST, 'ciw2.pipeline.extraction', 'CODE_HASH'),
        (_MODULE, 'ciw2.domain.profile_evidence'),
        (_MODULE, 'ciw2.render.drug_identity'),
    ),
    'extract_results': (
        (_FN, 'ciw2.pipeline.stages', '_extract'),
        (_FN, 'ciw2.pipeline.stages', '_results_extra'),
        (_CONST, 'ciw2.pipeline.extraction', 'CODE_HASH'),
        (_MODULE, 'ciw2.pipeline.queries'),
    ),
    'extract_design': (
        (_FN, 'ciw2.pipeline.stages', '_extract'),
        (_FN, 'ciw2.pipeline.stages', '_design_extra'),
        (_CONST, 'ciw2.pipeline.extraction', 'CODE_HASH'),
        (_MODULE, 'ciw2.pipeline.queries'),
    ),
    'verify': (
        (_FN, 'ciw2.pipeline.stages', 'verify'),
        (_FN, 'ciw2.pipeline.stages', '_entity_for'),
        (_FN, 'ciw2.pipeline.stages', 'cross_check'),
        (_MODULE, 'ciw2.pipeline.verification'),
        (_MODULE, 'ciw2.pipeline.profile'),
        (_MODULES, ('ciw2.verify.assessment', 'ciw2.verify.quote')),
        (_CONST, 'ciw2.pipeline.stages', 'CTGOV_CODE_HASH'),
    ),
    'analysis_A': (
        (_CONST, 'ciw2.pipeline.stages', 'ANALYSIS_CODE_HASH'),
        (_FN, 'ciw2.pipeline.stages', '_analysis'),
        (_MODULES, _RENDER_MODULES),
    ),
    'analysis_B': (
        (_CONST, 'ciw2.pipeline.stages', 'ANALYSIS_CODE_HASH'),
        (_FN, 'ciw2.pipeline.stages', '_analysis'),
        (_MODULES, _RENDER_MODULES),
    ),
    'analysis_C': (
        (_CONST, 'ciw2.pipeline.stages', 'ANALYSIS_CODE_HASH'),
        (_FN, 'ciw2.pipeline.stages', '_analysis'),
        (_MODULES, _RENDER_MODULES),
    ),
    'render': (
        (_FN, 'ciw2.pipeline.stages', 'render'),
        (_MODULES, _RENDER_MODULES),
        # Read-on-render bytes: CSS/JS/templates affect rendering only.
        (_ASSETS, ('templates', 'static')),
    ),
}

_STAGE_SKILLS: dict[str, tuple[str, ...]] = {
    'intake': ('intake',),
    'universe_china': ('universe-china',),
    'universe_global': ('universe-global',),
    'candidate_triage': ('coverage-review',),
    'universe_expand': ('universe-china', 'universe-global'),
    'coverage_review': ('coverage-review',),
    'trial_scope_review': ('coverage-review',),
    'enrich_drugs': ('extract-results',),
    'extract_results': ('extract-results',),
    'extract_design': ('extract-design',),
    'analysis_A': ('analysis-a',),
    'analysis_B': ('analysis-b',),
    'analysis_C': ('analysis-c',),
}

_TOOL_MODULES: dict[str, tuple[str, ...]] = {
    'china_registry_search': (
        'ciw2.sources.china_browser',
        'ciw2.sources.cde_browser',
        'ciw2.sources.cde_priority',
        'ciw2.sources.cde_review_browser',
        'ciw2.sources.http',
    ),
    'china_trial_detail': (
        'ciw2.sources.china_browser',
        'ciw2.sources.china_capture',
        'ciw2.sources.china_design',
        'ciw2.sources.http',
    ),
    'nmpa_product_detail': (
        'ciw2.sources.nmpa_capture',
        'ciw2.sources.china_browser',
        'ciw2.sources.http',
    ),
    'fetch_url': ('ciw2.sources.http', 'ciw2.sources.pdf_text'),
    'web_search': ('ciw2.sources.http',),
    'pubmed_search': ('ciw2.sources.http',),
    'pubmed_fetch': ('ciw2.sources.http',),
}

_TOOL_FILES: dict[str, tuple[str, ...]] = {
    'china_registry_search': (
        'sources/china_browser.mjs',
        'sources/cde_browser.mjs',
        'sources/cde_priority.mjs',
        'sources/cde_review_browser.mjs',
    ),
    'china_trial_detail': ('sources/china_detail.mjs', 'sources/china_browser.mjs'),
    'nmpa_product_detail': ('sources/nmpa_detail.mjs', 'sources/china_browser.mjs'),
}
