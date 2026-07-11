"""Corpus row predicates: shared library module.

Row-level classifiers over a works DataFrame: whether a paper is non-English,
and whether it carries a Global-South affiliation. Pure functions with no I/O.
The core-set builder (`build_het_core.py`) flags rows with them, and
`analyze_multilingual.py` reuses the same predicates so both layers agree on the
definition.

It lives in a neutral flat `_`-module so the entry point can move by phase while
the shared predicates stay on the flat library surface (ticket 0254; the 0250
pattern). The keyword set and function bodies are relocated verbatim from
`build_het_core.py` — output is byte-identical by construction.
"""

GLOBAL_SOUTH_KEYWORDS = {
    "china", "india", "brazil", "indonesia", "mexico", "nigeria",
    "bangladesh", "pakistan", "vietnam", "ethiopia", "egypt",
    "philippines", "kenya", "tanzania", "colombia", "argentina",
    "south africa", "peru", "venezuela", "chile", "ecuador",
    "guatemala", "cameroon", "ghana", "senegal", "morocco",
    "tunisia", "algeria", "thailand", "malaysia", "sri lanka",
    "nepal", "myanmar", "cambodia", "laos", "mongolia",
    "fiji", "samoa", "tonga", "tuvalu", "vanuatu",
    "bolivia", "paraguay", "uruguay", "costa rica", "panama",
    "honduras", "nicaragua", "el salvador", "dominican republic",
    "jamaica", "trinidad", "barbados", "cuba", "haiti",
    "uganda", "mozambique", "zambia", "zimbabwe", "malawi",
    "madagascar", "niger", "mali", "burkina faso", "chad",
    "congo", "rwanda", "burundi", "benin", "togo",
    "sierra leone", "liberia", "guinea", "gambia",
    "jordan", "lebanon", "iraq", "iran", "afghanistan",
    "uzbekistan", "kazakhstan", "kyrgyzstan", "tajikistan",
    "beijing", "shanghai", "mumbai", "delhi", "são paulo",
    "nairobi", "dar es salaam", "lagos", "cairo", "dhaka",
    "jakarta", "manila", "hanoi", "bogota", "lima",
    "buenos aires", "santiago", "quito", "accra", "dakar",
    "addis ababa", "kampala", "lusaka", "harare", "maputo",
    "bangui", "kinshasa", "abidjan", "tunis", "rabat",
    "islamabad", "karachi", "colombo", "kathmandu",
    "flacso", "eclac", "cepal",
}


def is_non_english(row):
    """Check if paper is non-English."""
    lang = str(row.get("language", "") or "").lower().strip()
    if not lang:
        return False
    return lang not in ("en", "eng", "en_us", "english")


def is_global_south(row):
    """Detect Global South affiliation from affiliations field."""
    aff = str(row.get("affiliations", "") or "").lower()
    if not aff:
        return False
    for kw in GLOBAL_SOUTH_KEYWORDS:
        if kw in aff:
            return True
    return False
