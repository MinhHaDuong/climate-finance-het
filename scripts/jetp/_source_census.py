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
