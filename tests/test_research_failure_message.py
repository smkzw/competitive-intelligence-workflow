"""Saved job guidance uses safe failure metadata, never a provider's raw exception text."""
import pytest

from ciw.research import run_research
from ciw.verify.crosscheck import CrosscheckFailed


@pytest.mark.parametrize('status,kind,expected',[
    (429,'concurrency','繁忙'),
    (429,'context_capacity','繁忙'),
    (429,'quota','额度'),
    (401,'unclassified','鉴权'),
    (400,'unclassified','未完成'),
    (504,'unclassified','响应超时'),
])
def test_source_failure_is_actionable_without_exposing_provider_details(ws,monkeypatch,status,kind,expected):
    private='private_key_and_source_body_should_never_be_shown'
    error=CrosscheckFailed(private,calls=[dict(role='extract',family='deepseek',model='deepseek',
        error='HTTPError',http_status=status,rejection_kind=kind,unsafe_body=private)])
    def fail(*args,**kwargs):
        raise error
    monkeypatch.setattr('ciw.research._research',fail)
    with pytest.raises(CrosscheckFailed):
        run_research('CRSwNP',ws.root,report='C',log=lambda _:None)
    state=ws.read_stage('research-run')
    assert state['state']=='failed' and state['error_type']=='CrosscheckFailed'
    assert expected in state['message'] and private not in str(state)
    assert '已保存' in state['message'] or '资料可' in state['message']
