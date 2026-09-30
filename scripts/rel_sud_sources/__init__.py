"""Adapters for the REL "Sud et langues" sources outside OpenAlex (ticket 1653).

Each adapter module defines ``SOURCE`` (a dict: ``name``, ``region``,
``languages``, ``route``, ``endpoint``, ``terms``) and two functions:

``plan(cfg) -> list[dict]``
    Query specs, each with at least ``query_id`` and ``query_string`` (the exact
    string sent, or for a harvest-then-match route the set and the local
    lexicon that selects candidates).

``fetch(spec, delay) -> iterator``
    The protocol of ``catalog_rel_sud_search.fetch``: ``('meta', n_expected)``
    at most once, then ``('work', record)`` per record, then exactly one
    ``('end', reason)`` where ``reason`` is ``''`` when the last page was
    reached. ``record`` is a dict over ``common.RECORD_FIELDS``.

Search routes keep every record the server returned. Harvest routes (OAI-PMH
sets, ``oai-pmh``) and listing routes (a whole series or catalogue,
``listing``) have no server-side search: they yield every item read, with
``matched_terms`` set locally; the runner archives the full harvest and keeps
only matched records as candidates.
"""
