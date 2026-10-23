"""CAS metadata cannot escape its own content-addressed namespace."""
from pathlib import Path

import pytest

from ciw2.store.cas import CAS


@pytest.mark.parametrize('digest',['../outside','../../outside','', 'x'*64,'A'*64,None,True,[],{}])
@pytest.mark.parametrize('method',['get','exists'])
def test_invalid_digest_is_rejected_before_any_filesystem_lookup(tmp_path,monkeypatch,digest,method):
    cas=CAS(tmp_path/'cas')

    def forbidden(*args,**kwargs):
        pytest.fail('Invalid metadata reached the filesystem')

    with monkeypatch.context() as scoped:
        scoped.setattr(Path,'read_bytes',forbidden)
        scoped.setattr(Path,'exists',forbidden)
        with pytest.raises(ValueError,match='SHA-256'):
            getattr(cas,method)(digest)


def test_valid_digest_reads_exact_bytes_and_missing_valid_digest_is_not_zero(tmp_path):
    cas=CAS(tmp_path/'cas')
    digest=cas.put(b'literal source')
    assert cas.get(digest)==b'literal source' and cas.exists(digest)
    assert not cas.exists('0'*64)
    with pytest.raises(FileNotFoundError):cas.get('0'*64)
