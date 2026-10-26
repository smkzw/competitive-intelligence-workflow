"""Python 3.14 folds literal slices into co_consts; supported runtime digests must serialize them."""
from ciw2.harness.agent import _dispatch
from ciw2.pipeline.stage_versions import _literal_digest, function_digest


def test_slice_constant_digest_preserves_all_parts_and_is_deterministic():
    source = slice(None, 3000, None)
    assert _literal_digest(source) == _literal_digest(slice(None, 3000, None))
    assert _literal_digest(source) != _literal_digest(slice(0, 3000, None))
    assert _literal_digest(source) != _literal_digest(slice(None, 3000, 2))
    # Actual function hashing, not a standalone JSON substitute; keep filename irrelevant.
    def finite():
        return 1
    frozen = finite.__code__.replace(co_consts=(*finite.__code__.co_consts, source))
    finite.__code__ = frozen
    digest = function_digest(finite)
    finite.__code__ = frozen.replace(co_filename='unrelated.py', co_firstlineno=200)
    assert function_digest(finite) == digest


def test_real_harness_dispatch_digest_is_usable_on_this_interpreter():
    digest = function_digest(_dispatch)
    assert len(digest) == 64 and digest == function_digest(_dispatch)
