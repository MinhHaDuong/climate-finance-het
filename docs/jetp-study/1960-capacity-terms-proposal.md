# Capacity terms from the Open Energy Ontology: proposal for sign-off (ticket 1960, item 3)

Status: proposal, 2026-10-01. Nothing below is imported until the author
signs it off (author decision 2026-10-01: narrow OEO import, verified on the
panel v1 sample first).

## Source

Open Energy Ontology v2.13.0 (release 2026-07-10, `oeo-full.owl`), read
locally; the EBI OLS4 search service does not index OEO (every query empty).
Units in OEO come from the Units of Measurement Ontology (`UO_…`).

## Proposed terms

| Term | List | OEO / UO term | IRI suffix | Note |
|---|---|---|---|---|
| electric power | quantity kind | power capacity | `OEO_00010257` | `closeMatch`: OEO's "power rating of a generator" |
| thermal power | quantity kind | none | | local; OEO has thermal energy but no thermal power class |
| apparent power | quantity kind | none | | local; no volt-ampere quantity in OEO |
| energy | quantity kind | energy | `OEO_00000150` | electrical energy `OEO_00000139` and thermal energy `OEO_00000207` as narrower |
| electric charge | quantity kind | electric charge (unit class) | `UO_0000219` | battery capacity in Ah |
| energy storage capacity | quantity kind | energy storage capacity | `OEO_00230000` | `closeMatch`; a storage rating in Wh |
| gross | basis | nameplate capacity | `OEO_00230003` | for power; for energy, gross electricity generation `OEO_00240012` |
| net | basis | declared net capacity | `OEO_00230002` | for energy, net electricity generation `OEO_00240013` |
| W | unit | watt | `UO_0000114` | kW `OEO_00390000`, MW `OEO_00390001`; GW has no class (prefix rule) |
| Wh | unit | watt-hour | `UO_0000223` | kWh `UO_0000224`, MWh `OEO_00050008`, GWh `OEO_00050011` |
| J | unit | joule | `UO_0000112` | |
| VA | unit | none | | local |
| Ah | unit | none | | local; ampere `UO_0000011` and coulomb `UO_0000220` exist |

SI prefixes (k, M, G, T) are a rule on the unit, not separate terms.
No annual energy output measure (author decision).

## Coverage on the panel v1 sample

Every value a v1 member wrote with an energy or power unit, in a field or
the "other" slot of a resolved row (`data/jetp/reference/panel-v1/rows.csv.gz`,
script `docs/jetp-study/1960-capacity-coverage.py`, output beside it): 60 distinct values.

- **Mapped to a quantity kind and a unit by the script: 60 of 60, none
  flagged.** Electric power 45 (MW 31, GW 9, W 3, kW 2), peak electric power
  7 (kWp 3, MWc 2, Wc 1, MWp 1; point 2 below), energy 6 (GWh 4, MWh 2),
  electric charge 2 (Ah: "C=3000Ah", "12V /150Ah").
- **Basis: stated for 4 of 60.** Gross 3 ("puissance installée 1960 MW"),
  net 1 ("112,354 MW nette"); unstated for 56.
- **Not seen in the sample:** thermal power, apparent power (VA), joule.
  Kept by decision, no v1 instance.

## Points for sign-off

1. **Basis needs `unknown`.** 56 of 60 values state no basis. `basis`
   already has `unknown` for money; extend it to physical quantities with
   `gross` and `net`, or the reader must guess. Recommended: extend.
2. **Peak power.** "kWp", "MWp" and the French "MWc" (crête) are a solar
   module's peak rating under test conditions, not the plant's AC capacity:
   7 of the 52 power values. OEO has no peak class. Options: a unit
   suffix `p` on W (Wp), or a quantity kind `peak electric power`.
   Recommended: the quantity kind, local, since the number is not
   comparable with AC capacity.
3. **Qualifiers are not capacity terms.** Several values carry a bound or a
   change: "below 10 MW", "không quá 30.127 MW" (not exceeding), "+0.7 GW
   year-on-year", "de 220 à 335 MW", "88 MWh par jour" (a rate per day).
   They map to kind and unit, but their meaning (upper bound, change, rate)
   is for the v2 schema (ticket 1940), not this list. Recommended: verbatim on
   the line, a qualifier slot in the v2 schema.
4. **Local terms without OEO IRIs:** thermal power, apparent power, VA, Ah
   (and peak electric power if adopted), recorded `mapping_relation: local`.
