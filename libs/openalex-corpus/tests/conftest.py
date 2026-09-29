"""Require test-domain ownership in the package's separate test suite."""

import pytest

DOMAIN_MARKERS = (
    "domain_literature",
    "domain_corpus",
    "domain_finance",
    "domain_jetp",
    "domain_writing",
    "domain_infrastructure",
)


def pytest_collection_modifyitems(items):
    """Reject an unmarked package test before ``-m`` can deselect it."""
    for item in items:
        if not any(item.get_closest_marker(name) for name in DOMAIN_MARKERS):
            raise pytest.UsageError(
                f"{item.nodeid} has no test-domain marker; declare pytestmark in its module "
                "or mark the test locally"
            )
