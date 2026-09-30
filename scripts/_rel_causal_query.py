"""Query-string helpers shared by the REL causal-map lane (ticket 1652).

A neutral private module (the 0250/0254 pattern): the search entry point and
the yield script both expand ``{BLOCK}`` templates and split boolean strings
into their top-level AND groups, so neither imports the other.
"""

import re

_BLOCK = re.compile(r"\{([A-Z_]+)\}")


def expand_blocks(template, blocks):
    """The template with every ``{NAME}`` replaced by ``blocks[NAME]``."""
    def sub(m):
        if m.group(1) not in blocks:
            raise KeyError(f"unknown block {{{m.group(1)}}}")
        return blocks[m.group(1)]
    return _BLOCK.sub(sub, template)


def split_and_groups(query):
    """Top-level AND groups of a query, outer parentheses removed."""
    groups, depth, quoted, start, i = [], 0, False, 0, 0
    while i < len(query):
        c = query[i]
        if c == '"':
            quoted = not quoted
        elif not quoted and c == "(":
            depth += 1
        elif not quoted and c == ")":
            depth -= 1
        elif not quoted and depth == 0 and query.startswith(" AND ", i):
            groups.append(query[start:i])
            start = i + 5
            i += 5
            continue
        i += 1
    groups.append(query[start:])
    out = []
    for g in groups:
        g = g.strip()
        if g.startswith("(") and g.endswith(")"):
            g = g[1:-1].strip()
        out.append(g)
    return out
