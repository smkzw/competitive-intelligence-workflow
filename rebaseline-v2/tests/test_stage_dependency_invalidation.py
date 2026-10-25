"""Shared scientific/readout helpers participate in stage invalidation."""
import re

import pytest
from runtime_resume_helpers import plan, status

from ciw2.pipeline import stage_versions
from ciw2.pipeline.stages import Stage
from ciw2.render import eligibility


def test_loaded_regex_rule_change_changes_render_binding(settings):
    original = eligibility._PREFIX
    before = stage_versions.module_digest(eligibility.__name__)
    try:
        eligibility._PREFIX = re.compile(original.pattern + '|additional-rule', original.flags)
        assert stage_versions.module_digest(eligibility.__name__) != before
    finally:
        eligibility._PREFIX = original


@pytest.mark.parametrize('helper', ['ciw2.domain.outcomes', 'ciw2.domain.semantics',
                                    'ciw2.domain.profile_evidence', 'ciw2.pipeline.queries'])
def test_readout_helper_upgrade_reruns_analysis_and_render_only(settings, monkeypatch, helper):
    calls = []

    def stub(name):
        def run(rc):
            calls.append(name)
            return {'stage': name}
        return run

    svc = plan(settings, monkeypatch, [Stage('intake', stub('intake')),
        Stage('analysis_B', stub('analysis_B')), Stage('render', stub('render'))])
    pid = svc.create_project('共同读取规则升级', ['B'])
    rid = svc.start_run(pid, background=False)
    assert status(svc, rid) == 'succeeded'
    original = stage_versions.module_digest
    monkeypatch.setattr(stage_versions, 'module_digest',
                        lambda name: original(name) + ('-changed' if name == helper else ''))
    calls.clear()
    svc.start_run(pid, resume_run=rid, background=False)
    assert calls == ['analysis_B', 'render']
    assert status(svc, rid) == 'succeeded'
