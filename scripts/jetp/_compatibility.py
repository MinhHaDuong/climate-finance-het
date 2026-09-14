"""Versioned read boundary over the authoritative, unmigrated MVP CSV readers.

The version is negotiated outside the payload so existing renderers and downloads
retain their exact contract. This adapter has no publication or ownership writes;
reconciled data can only replace the legacy authority in a later migration.
"""

from collections.abc import Collection
from pathlib import Path
from typing import Any

import yaml

from jetp import build_observatory as legacy

MVP_SCHEMA_VERSION = 'mvp/1'
SUPPORTED_MVP_SCHEMA_VERSIONS = frozenset({MVP_SCHEMA_VERSION})
MVP_VIEWS = frozenset({'overview', 'comparison', 'ZAF', 'IDN', 'VNM', 'SEN'})


def read_mvp_view(
    root: Path,
    view: str,
    *,
    supported_versions: Collection[str],
    schema_version: str = MVP_SCHEMA_VERSION,
) -> dict[str, Any]:
    """Read an unchanged MVP payload after explicit consumer version negotiation.

    Args:
        root: Repository checkout containing authoritative CSVs and configuration.
        view: Existing public download name, without the JSON extension.
        supported_versions: Schema versions the calling consumer understands.
        schema_version: Requested output contract; unsupported versions fail closed.

    """
    if schema_version not in SUPPORTED_MVP_SCHEMA_VERSIONS:
        raise ValueError(f'Unsupported MVP schema: {schema_version}')
    if schema_version not in supported_versions:
        raise ValueError(f'Consumer does not support MVP schema: {schema_version}')
    if view not in MVP_VIEWS:
        raise ValueError(f'Unknown MVP view: {view}')
    config = yaml.safe_load((root / 'config/jetp_observatory.yaml').read_text())
    tables = legacy.read_inputs(root)
    if view == 'overview':
        return legacy.overview(root, config, tables)
    if view == 'comparison':
        return legacy.comparison_data(root, config)
    return legacy.country_data(root, view, config, tables)
