"""Name-form review data for ``build_evidence_layer.py`` (ticket 0872).

Organisations are under authority control (author's decision of 2026-09-23,
``docs/jetp-ontology.md`` decision 12). The rebuild reads a publisher text and
decides how many parties it names and what each is called; every one of those
decisions was made by a reviewer looking at one text, not computed, so they
live here as data — one dict or constant per decision — kept apart from the
reconstruction logic that applies them (``build_evidence_layer.py``), plus the
handful of pure text functions those decisions are expressed with.
"""

import re
import unicodedata

DECIDED_AT = '2026-09-23'
DECIDED_BY = 'scripts/jetp/build_evidence_layer.py'

# Copies of a document already in the registry: mirror -> original.
MIRRORS = {
    'idn-cipp-2023-cpr-mirror': 'idn-cipp-2023',
    'sen-investment-plan-l4-mirror': 'sen-investment-plan-l4',
    'sen-annex8-project-analysis': 'sen-investment-plan-annex8-official',
}

# Publishers whose documents in the registry are copies they host, not texts
# they wrote.
HOST_PUBLISHERS = frozenset({'Climate Policy Radar', 'Vie-Publique.sn'})

# Joint publications added by review: document_id -> further publisher texts.
JOINT_PUBLICATIONS = {}

# Publisher texts of sources.csv that name two or more bodies: text -> the
# parts, each either a name (the default ``author`` role of
# ``_publications``) or a ``(name, role)`` pair when review found a
# different role for that part.
JOINT_LABELS = {
    'Government of Indonesia and International Partners Group':
        ('Government of Indonesia', 'International Partners Group'),
    'Government of Viet Nam and International Partners Group':
        ('Government of Viet Nam', 'International Partners Group'),
    'JETP Indonesia Secretariat and International Energy Agency':
        ('JETP Indonesia Secretariat', 'International Energy Agency'),
}

# Second parts of ``X / Y`` publisher texts reviewed as the document's writer:
# name -> 'firm' (a party in the author role) or 'person' (document notes only).
# A slash text whose second part is absent here, and is not a JOINT_LABELS
# text either, stays one party.
WRITERS = {
    'ENERCAP': 'firm',
    'Grant Thornton': 'firm',
    'Pyramide Environmental Consultants': 'firm',
    'Fatou Ndiaye': 'person',
}

# Parties named only inside a joint text: (authority_category, country, note).
PART_ATTRIBUTES = {
    'Government of Indonesia': ('national_government', 'IDN', None),
    'International Partners Group': ('ipg', None, None),
    'International Energy Agency': (
        None, None, 'no authority category of the list fits an intergovernmental '
                    'agency that neither funds nor operates; left for review'),
}

# Pairs of forms that may name one party, listed by review for the tier-2
# candidates the acronym rule cannot see: (form, form).
NAME_VARIANT_CANDIDATES = (
    ('MEPM', 'Senegal MEPM'),
)

# Words an acronym leaves out, in the four label languages the registry uses.
ACRONYM_SKIP = frozenset({'of', 'and', 'the', 'for', 'de', 'du', 'des', 'la', 'le',
                          'pour', 'et', 'd', 'l'})

# A party of these categories speaks for the partnership's country.
NATIONAL_CATEGORIES = frozenset({'national_government', 'jetp_secretariat'})


def slug(label):
    text = unicodedata.normalize('NFKD', label).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


def name_key(form):
    """A form with case, diacritics and spacing removed: equal keys, one party."""
    text = unicodedata.normalize('NFKD', form)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return ' '.join(text.casefold().split())


def initials(form):
    words = [w for w in re.findall(r'[^\W\d_]+', form) if w.casefold() not in ACRONYM_SKIP]
    return ''.join(w[0] for w in words).upper() if len(words) >= 2 else None


def is_acronym(form):
    return re.fullmatch(r'[A-Z]{2,}', form.strip()) is not None


def split_label(label, writers):
    """``(publisher, writer, channel)`` read from one publisher text.

    ``X via Y`` gives the channel Y; ``X / Y`` gives the writer Y when Y is a
    reviewed writer. A text fitting neither is its own publisher.
    """
    publisher, channel = label, None
    if ' via ' in label:
        publisher, channel = (part.strip() for part in label.rsplit(' via ', 1))
    writer = None
    if publisher.count(' / ') == 1:
        first, second = (part.strip() for part in publisher.split(' / '))
        if second in writers:
            publisher, writer = first, second
    return publisher, writer, channel


def joint_forms(entry):
    """The name forms of one ``JOINT_LABELS`` entry, dropping any role tag."""
    return tuple(part[0] if isinstance(part, tuple) else part for part in entry)
