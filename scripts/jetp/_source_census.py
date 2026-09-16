"""Small, fail-closed rules for the frozen 0817 source census."""

from collections.abc import Iterable

REQUIRED_FIELDS = (
    "item_id",
    "country",
    "source_id",
    "source_version",
    "route",
    "expected_item",
    "expected_count",
    "financial_semantics",
    "date_semantics",
    "retention",
    "disposition",
    "country_owner",
)
DISPOSITIONS = {"admitted", "duplicate", "excluded", "unavailable", "lost_visibility"}
COUNTRY_OWNERS = {"ZAF": "0818", "IDN": "0819", "VNM": "0820", "SEN": "0821"}
INVENTORY_FIELDS = (
    "inventory_id",
    "country",
    "source_id",
    "edition",
    "coverage_period",
    "expected_item",
    "expected_count",
    "retrieval_status",
    "content_disposition",
    "date_rule",
    "stop_rule",
    "country_owner",
)
RETRIEVAL_STATUSES = {"raw_retained", "index_raw_retained_file_not_retained"}
CONTENT_DISPOSITIONS = {"extraction_pending", "not_extracted"}
DATE_RULE = "publication_or_cutoff_not_event_without_explicit_event_statement"


def validate_census(rows: Iterable[dict[str, str]]) -> None:
    """Reject an ambiguous finite census before country work starts.

    This validates the declared acquisition universe, not its substantive
    claims.  In particular, a route that could not be retrieved remains an
    unavailable item and can never be labeled a complete zero.
    """
    seen: set[str] = set()
    for row in rows:
        missing = [field for field in REQUIRED_FIELDS if not row.get(field, "").strip()]
        if missing:
            raise ValueError(f"missing census field: {', '.join(missing)}")
        item_id = row["item_id"]
        if item_id in seen:
            raise ValueError(f"duplicate census item: {item_id}")
        seen.add(item_id)
        if row["disposition"] not in DISPOSITIONS:
            if row["disposition"] == "complete":
                raise ValueError("unavailable items cannot be reported as complete")
            raise ValueError(f"invalid disposition: {row['disposition']}")
        if row["country"] not in COUNTRY_OWNERS:
            raise ValueError(f"unknown census country: {row['country']}")
        if row["country_owner"] != COUNTRY_OWNERS[row["country"]]:
            raise ValueError(f"country owner mismatch for {item_id}")
        try:
            expected_count = int(row["expected_count"])
        except ValueError as exc:
            raise ValueError(f"invalid expected count for {item_id}") from exc
        if expected_count < 1:
            raise ValueError(f"expected count must be positive for {item_id}")


def validate_inventory_manifest(rows: Iterable[dict[str, str]]) -> None:
    """Keep retained retrieval, extractable content, and event evidence distinct."""
    seen: set[str] = set()
    for row in rows:
        missing = [field for field in INVENTORY_FIELDS if not row.get(field, "").strip()]
        if missing:
            raise ValueError(f"missing inventory field: {', '.join(missing)}")
        inventory_id = row["inventory_id"]
        if inventory_id in seen:
            raise ValueError(f"duplicate inventory item: {inventory_id}")
        seen.add(inventory_id)
        if row["country"] not in COUNTRY_OWNERS:
            raise ValueError(f"unknown inventory country: {row['country']}")
        if row["country_owner"] != COUNTRY_OWNERS[row["country"]]:
            raise ValueError(f"country owner mismatch for {inventory_id}")
        if row["retrieval_status"] not in RETRIEVAL_STATUSES:
            raise ValueError(f"invalid retrieval status: {row['retrieval_status']}")
        if row["content_disposition"] not in CONTENT_DISPOSITIONS:
            raise ValueError(f"invalid content disposition: {row['content_disposition']}")
        if row["date_rule"] != DATE_RULE:
            raise ValueError("publication or cutoff cannot be an event date without an explicit statement")
        try:
            expected_count = int(row["expected_count"])
        except ValueError as exc:
            raise ValueError(f"invalid expected count for {inventory_id}") from exc
        if expected_count < 1:
            raise ValueError(f"expected count must be positive for {inventory_id}")
