"""Require local workpackage ownership in the package's separate test suite."""

import pytest

WP_MARKERS = (
    "wp_library",
    "wp_corpus",
    "wp_finance",
    "wp_jetp",
    "wp_writing",
    "wp_shared",
)


def pytest_collection_modifyitems(items):
    """Reject an unmarked package test before ``-m`` can deselect it."""
    for item in items:
        if not any(item.get_closest_marker(name) for name in WP_MARKERS):
            raise pytest.UsageError(
                f"{item.nodeid} has no WP marker; declare pytestmark in its module "
                "or mark the test locally"
            )
