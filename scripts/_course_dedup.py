"""Course-name deduplication: shared library helper.

Merges near-duplicate course names in the teaching-syllabi table (co-organized
MOOCs listed under several institution names) and recomputes n_courses. The
teaching-YAML builder (`build_teaching_yaml.py`) applies it, and
`analyze_syllabi.py` reuses it so both agree on the dedup definition.

It lives in a neutral flat `_`-module so the entry point can move by phase while
the shared helper stays on the flat library surface (ticket 0254; the 0250
pattern). The thresholds and function body are relocated verbatim from
`build_teaching_yaml.py` — output is byte-identical by construction.
"""

from collections import defaultdict

from utils import get_logger

log = get_logger("build_teaching_yaml")

OVERLAP_THRESHOLD = 0.8  # Course pairs sharing >80% readings are duplicates
MIN_SHARED_READINGS = 10  # Require >=10 shared readings to consider dedup


def _dedup_course_names(df):
    """Merge near-duplicate course names and recompute n_courses.

    Two courses are considered duplicates if they share >=MIN_SHARED_READINGS
    AND >OVERLAP_THRESHOLD of the smaller course's readings. This catches
    co-organized MOOCs listed under multiple institution names.
    """
    # Build course -> set of row indices
    course_rows = defaultdict(set)
    for idx, row in df.iterrows():
        for c in str(row.get("courses", "")).split(";"):
            c = c.strip()
            if c:
                course_rows[c].add(idx)

    # Find overlapping course pairs
    courses = list(course_rows.keys())
    merged = {}  # alias -> canonical
    for i, c1 in enumerate(courses):
        if c1 in merged:
            continue
        for c2 in courses[i + 1:]:
            if c2 in merged:
                continue
            s1, s2 = course_rows[c1], course_rows[c2]
            if not s1 or not s2:
                continue
            n_shared = len(s1 & s2)
            overlap = n_shared / min(len(s1), len(s2))
            if n_shared >= MIN_SHARED_READINGS and overlap > OVERLAP_THRESHOLD:
                canonical = c1 if len(c1) <= len(c2) else c2
                alias = c2 if canonical == c1 else c1
                merged[alias] = canonical

    if not merged:
        return df

    log.info("  Course dedup: merged %d duplicate course names", len(merged))

    def apply_merge(courses_str):
        parts = [c.strip() for c in str(courses_str).split(";")]
        deduped = []
        seen = set()
        for c in parts:
            canonical = merged.get(c, c)
            if canonical and canonical not in seen:
                deduped.append(canonical)
                seen.add(canonical)
        return " ; ".join(sorted(deduped))

    df = df.copy()
    df["courses"] = df["courses"].apply(apply_merge)
    df["n_courses"] = df["courses"].apply(
        lambda x: len([c for c in x.split(" ; ") if c.strip()]))
    return df
