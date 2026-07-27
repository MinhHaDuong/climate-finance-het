"""The deposit's machine-readable descriptors (ticket 0354).

The load-bearing tests here validate the **written CSV** against the published
`datapackage.json`, not an in-memory frame. That distinction is the reason the
descriptor exists: a frame-level assertion cannot see an integer serialised as
``2026.0``, which is exactly what the first run of this gate found in the real
deposit (0288/0347 recorded the same class — 41 green tests over an in-memory
dict while the artifact was wrong).
"""

import csv
import json
import os

import pytest
from _deposit_schema import contract_for, frictionless_field, render_datapackage
from _deposit_variables import DEPOSIT_VARIABLES, check_columns, contract_names

RESOURCE = "climate_finance_corpus.csv"
RECIPE = "df[~df['is_flagged'] | df['is_protected']]"


def _valid_value(v) -> str:
    """A cell that satisfies the contract for one variable."""
    if v.enum:
        return v.enum[0]
    if v.dtype == "boolean":
        return "1"
    if v.dtype == "integer":
        return str(v.minimum if v.minimum is not None else 1)
    if v.dtype == "number":
        return "0.5"
    return "x"


def _write_csv(path: str, columns: list[str], rows: list[dict[str, str]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _conforming_row(columns: list[str]) -> dict[str, str]:
    by_name = {v.name: v for v in DEPOSIT_VARIABLES}
    return {c: _valid_value(by_name[c]) for c in columns}


def _validate(tmp_path, columns: list[str], rows: list[dict[str, str]]):
    """Emit CSV + descriptor into tmp_path and validate, as the gate does."""
    from frictionless import validate as fl_validate

    csv_path = os.path.join(tmp_path, RESOURCE)
    pkg_path = os.path.join(tmp_path, "datapackage.json")
    _write_csv(csv_path, columns, rows)
    with open(pkg_path, "w", encoding="utf-8") as f:
        json.dump(render_datapackage(columns, "test"), f)
    return fl_validate(pkg_path)


class TestContractStructure:
    """The structured contract, and the prose derived from it."""

    def test_field_order_follows_the_file_not_the_contract(self):
        """Frictionless matches fields by position, so order is the file's.

        Regression: the first emitter ordered fields by the contract, and the
        deposit writes six curation columns in a different order — so every
        one of them was validated against its neighbour's rules, reporting
        `source_count` as holding the value `source`.
        """
        shuffled = list(reversed(contract_names()))
        assert [v.name for v in contract_for(shuffled)] == shuffled

    def test_absent_optional_column_gets_no_field(self):
        present = [c for c in contract_names() if c != "in_v1"]
        assert "in_v1" not in [v.name for v in contract_for(present)]

    def test_enum_excludes_the_empty_sentinel(self):
        """`empty` is a missing value, not an enum member.

        Frictionless skips enum checks on missing cells, so listing `empty`
        would put a member in the schema that no cell can ever match; the
        column says so with `nullable` instead.
        """
        by_name = {v.name: v for v in DEPOSIT_VARIABLES}
        for name in ("abstract_provenance", "keywords_provenance",
                     "language_provenance"):
            v = by_name[name]
            assert "empty" not in v.enum
            assert v.nullable

    def test_required_is_the_negation_of_nullable(self):
        for v in DEPOSIT_VARIABLES:
            constraints = frictionless_field(v).get("constraints", {})
            assert constraints.get("required", False) is (not v.nullable), v.name

    def test_empty_meaning_a_value_is_not_read_as_missing(self):
        """`flag_reason` is empty for an unflagged work — data, not a gap.

        Without a field-level `missingValues: []` the empty cell would count as
        missing and `required` would fail on the 74% of works carrying no flag.
        """
        by_name = {v.name: v for v in DEPOSIT_VARIABLES}
        v = by_name["flag_reason"]
        assert v.empty_is_a_value and not v.nullable
        assert frictionless_field(v)["missingValues"] == []

    def test_measured_missingness_travels_with_the_schema(self):
        """What the retired prose codebook printed, now inside the descriptor."""
        pkg = render_datapackage(contract_names(), "test", {"doi": 0.1964})
        fields = {f["name"]: f for f in pkg["resources"][0]["schema"]["fields"]}
        assert fields["doi"]["missingRate"] == 0.1964
        assert "missingRate" not in fields["title"], "unmeasured column claims none"

    def test_boolean_fields_carry_no_enum(self):
        """The deposit writes 0/1 for provenance and True/False for curation.

        Frictionless accepts both token pairs for a boolean, and an enum would
        be compared against the parsed value, not the token — so declaring one
        would reject the other family.
        """
        for v in DEPOSIT_VARIABLES:
            if v.dtype == "boolean":
                assert not v.enum, f"{v.name} must not constrain by enum"

    def test_recipe_survives_the_json_descriptor(self):
        """The 0325 defect class, checked in the medium that now carries it.

        A delimiter inside payload text corrupted the recipe once already (a
        `|` cut the codebook cell in half) and again in LaTeX (a `~` inverted
        it). JSON escaping is `json.dump`'s job, but the claim is cheap to pin
        and this is where the description is published now.
        """
        pkg = json.loads(json.dumps(render_datapackage(contract_names(), "t")))
        fields = {f["name"]: f for f in pkg["resources"][0]["schema"]["fields"]}
        assert RECIPE in fields["is_flagged"]["description"]

    def test_every_variable_maps_to_a_frictionless_type(self):
        allowed = {"string", "integer", "number", "boolean"}
        for v in DEPOSIT_VARIABLES:
            assert v.dtype in allowed, f"{v.name}: {v.dtype}"


@pytest.mark.integration
class TestWrittenCsvValidates:
    """Validate the serialized artifact — the point of the descriptor."""

    def test_conforming_csv_is_valid(self, tmp_path):
        columns = contract_names()
        report = _validate(str(tmp_path), columns, [_conforming_row(columns)])
        assert report.valid, report.flatten(["fieldName", "type", "note"])

    def test_out_of_enum_value_is_rejected(self, tmp_path):
        """The gap this ticket closes: `check_columns` passes, values don't."""
        columns = contract_names()
        row = _conforming_row(columns)
        row["source"] = "wikipedia"
        assert check_columns(columns) == [], "column check must still pass"

        report = _validate(str(tmp_path), columns, [row])
        assert not report.valid
        offenders = {row[0] for row in report.flatten(["fieldName"])}
        assert "source" in offenders, offenders

    def test_float_serialized_integer_is_rejected(self, tmp_path):
        """`2026.0` for a column published as `integer`.

        The real deposit shipped this until export_deposit.py started casting
        to nullable Int64; no frame-level check could see it.
        """
        columns = contract_names()
        row = _conforming_row(columns)
        row["year"] = "2026.0"
        report = _validate(str(tmp_path), columns, [row])
        assert not report.valid

    def test_out_of_range_value_is_rejected(self, tmp_path):
        columns = contract_names()
        row = _conforming_row(columns)
        row["source_count"] = "9"
        report = _validate(str(tmp_path), columns, [row])
        assert not report.valid


class TestDepositEnvelope:
    """Provenance the descriptor publishes beyond the column schema."""

    def test_datapackage_carries_orcid_and_funder(self):
        pkg = render_datapackage(contract_names(), "test")
        roles = {c["roles"][0]: c["path"] for c in pkg["contributors"]}
        assert "0000-0001-9988-2100" in roles["author"]
        assert "ror.org" in roles["funder"]


class TestIntegerCoercion:
    """`export_deposit.coerce_integer_columns` — the fix for `2026.0`.

    The descriptor cannot police this one on its own. A malformed year that
    becomes an *empty* cell validates cleanly, because `year` is nullable by
    measurement; only the coercion step can refuse it.
    """

    def _frame(self, value):
        import pandas as pd
        return pd.DataFrame({"year": [value, "2020"]})

    def test_missing_value_does_not_become_a_float(self):
        import pandas as pd
        from figures.export_deposit import coerce_integer_columns

        df = coerce_integer_columns(pd.DataFrame({"year": [2026.0, None]}))
        assert df["year"].astype("string").tolist()[0] == "2026"

    def test_non_numeric_value_is_refused_not_emptied(self):
        """The silent path this closes: `coerce` would publish a blank year.

        A blank passes validation (`year` is nullable), so a garbage value would
        leave the deposit green while losing data. Refuse it at the write step.
        """
        from figures.export_deposit import coerce_integer_columns

        with pytest.raises((ValueError, TypeError)):
            coerce_integer_columns(self._frame("n.d."))

    def test_fractional_value_is_refused_not_truncated(self):
        from figures.export_deposit import coerce_integer_columns

        with pytest.raises((ValueError, TypeError)):
            coerce_integer_columns(self._frame("2026.4"))
