"""Shim-resolution guard: carved symbols re-exported via their old host paths.

Ticket 0170 Move A extracts the OpenAlex convention layer into the
``openalex-corpus`` package and turns ``pipeline_io``/``pipeline_text``/
``enrich_embeddings`` into re-export shims. A typo in a re-export line would
silently break a rarely-run script rather than fail a test.

This test imports every carved symbol via its OLD path (the one existing call
sites use) and asserts it resolves to the package definition. For the four pure
passthroughs that is object identity; ``retry_get`` is a thin shim (it injects
this repo's ``MAILTO``/User-Agent), so it is deliberately *not* the package
function — behavioural parity for it is pinned separately by
``test_openalex_corpus_equivalence.py``. Here we only assert the shim exists,
is distinct from the package function, and that ``RETRY_MAX_RETRIES`` is the
package's single source of truth re-exported unchanged.

``importorskip`` keeps the suite green in an env where the package is not
installed.
"""

import pytest

pkg = pytest.importorskip("openalex_corpus")


@pytest.mark.parametrize(
    "module_path, symbol",
    [
        # pure passthroughs — old path must BE the package object
        ("pipeline_text", "normalize_doi"),
        ("pipeline_text", "reconstruct_abstract"),
        ("enrich_embeddings", "build_text"),
        ("enrich_embeddings", "is_boilerplate_abstract"),
        # utils re-export facade chains through to the same package objects.
        # (utils re-exports the pipeline_text symbols; build_text /
        # is_boilerplate_abstract are imported directly from enrich_embeddings
        # by call sites, not via the utils facade — covered above.)
        ("utils", "normalize_doi"),
        ("utils", "reconstruct_abstract"),
    ],
)
def test_pure_symbol_resolves_to_package(module_path, symbol):
    module = pytest.importorskip(module_path)
    host_obj = getattr(module, symbol)
    pkg_obj = getattr(pkg, symbol)
    assert host_obj is pkg_obj, (
        f"{module_path}.{symbol} must re-export the package definition "
        f"(openalex_corpus.{symbol}); got a distinct object — the re-export "
        f"line is broken."
    )


def test_retry_max_retries_re_exported():
    pipeline_io = pytest.importorskip("pipeline_io")
    assert pipeline_io.RETRY_MAX_RETRIES == pkg.RETRY_MAX_RETRIES


def test_retry_get_is_shim_not_package_fn():
    pipeline_io = pytest.importorskip("pipeline_io")
    utils = pytest.importorskip("utils")
    # The shim wraps the package fn (injects MAILTO/User-Agent), so it must be a
    # distinct callable, and utils must re-export that same shim.
    assert callable(pipeline_io.retry_get)
    assert pipeline_io.retry_get is not pkg.retry_get
    assert utils.retry_get is pipeline_io.retry_get
