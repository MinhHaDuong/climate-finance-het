-- JETP ledger DDL: the one declaration of the ledger's common tables.
--
-- Contract: docs/jetp-ledger-storage.md, sections 1 and 3 (ticket 0871).
-- CSV in git is the system of record; this file is its schema. CSV headers
-- are generated from it (scripts/jetp/_ledger_headers.py) and, at build time,
-- the CSVs load into a SQLite file under data/derived/jetp/ where the keys,
-- foreign keys and checks below act as the validator
-- (scripts/jetp/build_ledger.py).
--
-- Conventions the tooling reads:
--   * A table named foo_bar is stored as data/jetp/foo-bar.csv, or chunked as
--     data/jetp/foo-bar.d/<CODE>-<year>.csv when one file would exceed the
--     pre-commit file ceiling. The .d suffix keeps a chunk directory apart
--     from any directory named after a table: data/jetp/documents/ is the
--     snapshot store. Ontology tables live under data/jetp/ontology/.
--   * Columns are declared in the CSV column order of the contract.
--   * Rules SQLite can hold per row are CHECK, NOT NULL, UNIQUE and FOREIGN
--     KEY constraints. Rules that span rows or tables are named validation
--     queries: every view whose name starts with violation_ must be empty,
--     and each row it returns is one named failure (column `detail`).
--   * A column whose values come from a closed list never enumerates that
--     list here. It is checked against the terms in force (view
--     terms_in_force), under the list name given in violation_closed_list.
--     No list of values exists outside the `terms` table
--     (data/jetp/ontology/terms.csv, ticket 0880). The only exception is the
--     terms table's own kind, status and mapping_relation, which are terms
--     too but are checked by tests/test_jetp_ontology_tables.py rather than
--     here, so that a fixture can start from a single term row.
--   * Per-document field tables (line-fields/<document_id>.csv) are not
--     declared here: each is declared by its row in line_field_specs and the
--     builder compares the file header to that row.
--   * `dry-searches.csv` and `decisions.md` stay as today and are not ledger
--     tables of this DDL.

-- ---------------------------------------------------------------------------
-- Ontology (docs/jetp-ontology.md section 5; ticket 0880)
--
-- Five tables under data/jetp/ontology/, revised by supersession and never
-- edited in place. Each row carries recorded_at, decided_by, status and
-- supersedes; a row is in force when it is the accepted terminal row of its
-- chain (views *_in_force). The chain key is the set of columns successive
-- revisions of one entry share: (list, term_id) for terms, since a value's
-- term_id is unique within its list only; (publisher_id, own_status) and
-- (publisher_id, own_sector) for the crosswalks, where publisher_id is the
-- party whose vocabulary the row maps; perimeter_id; and
-- (donor_party_id, marker, score, year) for marker coefficients. A change of
-- meaning mints a new chain key and the old one stays in force.
-- Rows: `terms` in ticket 0880, the crosswalks in 0876, perimeters in 0877,
-- marker coefficients in 0885.
-- ---------------------------------------------------------------------------

CREATE TABLE terms (
    term_row_id TEXT PRIMARY KEY,
    term_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    list TEXT,
    label TEXT NOT NULL,
    definition TEXT NOT NULL CHECK (length(trim(definition)) > 0),
    scope_note TEXT,
    domain TEXT,
    range TEXT,
    external_scheme TEXT,
    external_uri TEXT,
    mapping_relation TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    decided_by TEXT NOT NULL,
    status TEXT NOT NULL,
    supersedes TEXT UNIQUE REFERENCES terms (term_row_id),
    notes TEXT
);

CREATE TABLE status_crosswalk (
    crosswalk_row_id TEXT PRIMARY KEY,
    publisher_id TEXT NOT NULL REFERENCES parties (party_id),
    own_status TEXT NOT NULL,
    axis TEXT NOT NULL,
    shared_status TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    decided_by TEXT NOT NULL,
    status TEXT NOT NULL,
    supersedes TEXT UNIQUE REFERENCES status_crosswalk (crosswalk_row_id),
    notes TEXT
);

CREATE TABLE sector_crosswalk (
    crosswalk_row_id TEXT PRIMARY KEY,
    publisher_id TEXT NOT NULL REFERENCES parties (party_id),
    own_sector TEXT NOT NULL,
    -- A five-digit OECD DAC CRS purpose code. The purpose list is an external
    -- enumeration of some 200 codes that the ledger cites, not a closed list
    -- of its own, so its shape is checked here and a code is not a term.
    purpose_code TEXT NOT NULL CHECK (purpose_code GLOB '[0-9][0-9][0-9][0-9][0-9]'),
    recorded_at TEXT NOT NULL,
    decided_by TEXT NOT NULL,
    status TEXT NOT NULL,
    supersedes TEXT UNIQUE REFERENCES sector_crosswalk (crosswalk_row_id),
    notes TEXT
);

CREATE TABLE perimeters (
    perimeter_row_id TEXT PRIMARY KEY,
    perimeter_id TEXT NOT NULL,
    country TEXT,
    name TEXT NOT NULL,
    scope TEXT,
    definition TEXT NOT NULL CHECK (length(trim(definition)) > 0),
    recorded_at TEXT NOT NULL,
    decided_by TEXT NOT NULL,
    status TEXT NOT NULL,
    supersedes TEXT UNIQUE REFERENCES perimeters (perimeter_row_id),
    notes TEXT
);

CREATE TABLE marker_coefficients (
    coefficient_row_id TEXT PRIMARY KEY,
    donor_party_id TEXT NOT NULL REFERENCES parties (party_id),
    marker TEXT NOT NULL,
    score TEXT NOT NULL,
    year INTEGER NOT NULL,
    coefficient REAL NOT NULL CHECK (coefficient BETWEEN 0 AND 1),
    -- The line that states the donor's coefficient: a rule is sourced.
    line_id TEXT REFERENCES lines (line_id),
    recorded_at TEXT NOT NULL,
    decided_by TEXT NOT NULL,
    status TEXT NOT NULL,
    supersedes TEXT UNIQUE REFERENCES marker_coefficients (coefficient_row_id)
);

-- ---------------------------------------------------------------------------
-- Parties and their names (authority control, decided 2026-09-23)
--
-- One organisation table. A publisher is a party in a publishing role
-- (document_publishers); a funder, a channel or an operator is the same party
-- in another role. A party's names are rows of party_names, one per form as
-- printed, with exactly one preferred form in force; the party row carries
-- no name of its own.
-- ---------------------------------------------------------------------------

CREATE TABLE parties (
    party_id TEXT PRIMARY KEY,
    authority_category TEXT,
    country TEXT,
    notes TEXT
);

CREATE TABLE party_names (
    name_row_id TEXT PRIMARY KEY,
    party_id TEXT NOT NULL REFERENCES parties (party_id),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    form_type TEXT NOT NULL,
    language TEXT,
    -- The justification: the document or the line the form was read from.
    document_id TEXT REFERENCES documents (document_id),
    line_id TEXT REFERENCES lines (line_id),
    recorded_at TEXT NOT NULL,
    decided_by TEXT NOT NULL,
    status TEXT NOT NULL,
    supersedes TEXT UNIQUE REFERENCES party_names (name_row_id),
    notes TEXT,
    CHECK (document_id IS NOT NULL OR line_id IS NOT NULL)
);

-- ---------------------------------------------------------------------------
-- Documents, publications, retrievals, snapshots
-- ---------------------------------------------------------------------------

CREATE TABLE documents (
    document_id TEXT PRIMARY KEY,
    country TEXT,
    document_type TEXT,
    language TEXT,
    title TEXT NOT NULL,
    url TEXT,
    published_date TEXT,
    edition_of TEXT REFERENCES documents (document_id),
    active TEXT,
    notes TEXT
);

-- A joint publication is one row per party. name_row_id is the form of the
-- party's name this document prints, which is what a page shows beside it.
CREATE TABLE document_publishers (
    document_id TEXT NOT NULL REFERENCES documents (document_id),
    party_id TEXT NOT NULL REFERENCES parties (party_id),
    role TEXT,
    name_row_id TEXT REFERENCES party_names (name_row_id),
    PRIMARY KEY (document_id, party_id)
);

CREATE TABLE snapshots (
    sha256 TEXT PRIMARY KEY CHECK (length(sha256) = 64),
    storage_path TEXT NOT NULL,
    size_bytes INTEGER CHECK (size_bytes >= 0),
    content_type TEXT
);

CREATE TABLE retrievals (
    retrieval_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents (document_id),
    retrieved_at TEXT NOT NULL,
    status TEXT NOT NULL,
    http_status INTEGER,
    content_type TEXT,
    etag TEXT,
    last_modified TEXT,
    final_url TEXT,
    error TEXT,
    sha256 TEXT REFERENCES snapshots (sha256)
);

-- ---------------------------------------------------------------------------
-- Lines
-- ---------------------------------------------------------------------------

CREATE TABLE lines (
    line_id TEXT PRIMARY KEY,
    country TEXT NOT NULL,
    sha256 TEXT NOT NULL REFERENCES snapshots (sha256),
    locator TEXT NOT NULL,
    ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
    label TEXT,
    classification TEXT NOT NULL,
    own_status TEXT,
    own_status_axis TEXT,
    own_sector TEXT,
    -- Direction of `groups` (heading to member, or member to heading) is set
    -- by the first extraction that writes it (ticket 0873); no key yet.
    groups TEXT,
    recorded_at TEXT NOT NULL,
    notes TEXT,
    -- No two lines claim the same place in the same bytes.
    UNIQUE (sha256, locator)
);

CREATE TABLE line_field_specs (
    document_id TEXT PRIMARY KEY REFERENCES documents (document_id),
    -- The document's own column names, in order, as a JSON array of strings:
    -- the header of line-fields/<document_id>.csv after its `line_id`.
    columns TEXT NOT NULL CHECK (json_valid(columns) AND json_type(columns) = 'array')
);

-- ---------------------------------------------------------------------------
-- Identities (minted only by a line_referents row)
-- ---------------------------------------------------------------------------

CREATE TABLE projects (
    project_id TEXT PRIMARY KEY,
    country TEXT NOT NULL,
    canonical_name TEXT NOT NULL,
    aliases TEXT,
    classification TEXT,
    classified_at TEXT,
    sector TEXT,
    notes TEXT
);

CREATE TABLE assets (
    asset_id TEXT PRIMARY KEY,
    country TEXT NOT NULL,
    name TEXT NOT NULL,
    technology TEXT,
    location TEXT,
    operator_party_id TEXT REFERENCES parties (party_id),
    part_of TEXT REFERENCES assets (asset_id),
    notes TEXT
);

CREATE TABLE agreements (
    agreement_id TEXT PRIMARY KEY,
    country TEXT NOT NULL,
    instrument TEXT,
    modality TEXT,
    sector TEXT,
    currency TEXT,
    tranche_of TEXT REFERENCES agreements (agreement_id),
    notes TEXT
);

-- ---------------------------------------------------------------------------
-- Decisions (defeasible: a row is never edited, a later row supersedes it)
-- ---------------------------------------------------------------------------

CREATE TABLE line_referents (
    referent_row_id TEXT PRIMARY KEY,
    line_id TEXT NOT NULL REFERENCES lines (line_id),
    referent_kind TEXT NOT NULL,
    referent_id TEXT NOT NULL,
    status TEXT NOT NULL,
    method TEXT NOT NULL,
    method_version TEXT,
    confidence REAL CHECK (confidence BETWEEN 0 AND 1),
    justification_line_ids TEXT,
    decided_at TEXT NOT NULL,
    decided_by TEXT NOT NULL,
    -- UNIQUE: a row is superseded by at most one row (linear chain).
    supersedes TEXT UNIQUE REFERENCES line_referents (referent_row_id),
    notes TEXT
);

CREATE TABLE relations (
    relation_id TEXT PRIMARY KEY,
    from_kind TEXT NOT NULL,
    from_id TEXT NOT NULL,
    relation TEXT NOT NULL,
    to_kind TEXT NOT NULL,
    to_id TEXT NOT NULL,
    role TEXT,
    valid_from TEXT,
    valid_to TEXT,
    status TEXT NOT NULL,
    method TEXT NOT NULL,
    method_version TEXT,
    confidence REAL CHECK (confidence BETWEEN 0 AND 1),
    decided_at TEXT NOT NULL,
    decided_by TEXT NOT NULL,
    supersedes TEXT UNIQUE REFERENCES relations (relation_id),
    line_id TEXT REFERENCES lines (line_id),
    CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_from <= valid_to)
);

-- ---------------------------------------------------------------------------
-- Observations and timings
-- ---------------------------------------------------------------------------

CREATE TABLE observations (
    observation_id TEXT PRIMARY KEY,
    subject_kind TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    axis TEXT,
    measure TEXT NOT NULL,
    flow_type TEXT,
    basis TEXT,
    value REAL,
    value_low REAL,
    value_high REAL,
    unit TEXT,
    currency TEXT,
    own_status TEXT,
    indicator_code TEXT,
    -- An observation cites exactly one line.
    line_id TEXT NOT NULL REFERENCES lines (line_id),
    method TEXT NOT NULL,
    method_version TEXT,
    recorded_at TEXT NOT NULL,
    status TEXT NOT NULL,
    supersedes TEXT UNIQUE REFERENCES observations (observation_id),
    notes TEXT,
    CHECK (value_low IS NULL OR value_high IS NULL OR value_low <= value_high)
);

CREATE TABLE timings (
    timing_id TEXT PRIMARY KEY,
    observation_id TEXT NOT NULL REFERENCES observations (observation_id),
    date_role TEXT NOT NULL,
    date TEXT,
    date_precision TEXT,
    lower_bound TEXT,
    upper_bound TEXT,
    line_id TEXT REFERENCES lines (line_id),
    recorded_at TEXT NOT NULL,
    CHECK (lower_bound IS NULL OR upper_bound IS NULL OR lower_bound <= upper_bound)
);

CREATE TABLE external_ids (
    scheme TEXT NOT NULL,
    external_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    id TEXT NOT NULL,
    line_id TEXT REFERENCES lines (line_id),
    recorded_at TEXT NOT NULL,
    PRIMARY KEY (scheme, external_id)
);

-- ---------------------------------------------------------------------------
-- Adjudications
-- ---------------------------------------------------------------------------

CREATE TABLE adjudications (
    adjudication_id TEXT PRIMARY KEY,
    decision_type TEXT NOT NULL,
    subject_kind TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    verdict TEXT NOT NULL,
    status TEXT NOT NULL,
    decided_at TEXT NOT NULL,
    decided_by TEXT NOT NULL,
    supersedes TEXT UNIQUE REFERENCES adjudications (adjudication_id),
    notes TEXT
);

CREATE TABLE adjudication_members (
    adjudication_id TEXT NOT NULL REFERENCES adjudications (adjudication_id),
    kind TEXT NOT NULL,
    id TEXT NOT NULL,
    role TEXT,
    PRIMARY KEY (adjudication_id, kind, id)
);

-- ---------------------------------------------------------------------------
-- Rates and deflators (a script never carries a rate)
-- ---------------------------------------------------------------------------

CREATE TABLE rates (
    currency TEXT NOT NULL,
    date TEXT NOT NULL,
    basis TEXT NOT NULL,
    rate_to_usd REAL NOT NULL CHECK (rate_to_usd > 0),
    line_id TEXT REFERENCES lines (line_id),
    recorded_at TEXT NOT NULL,
    PRIMARY KEY (currency, date, basis)
);

CREATE TABLE deflators (
    series TEXT NOT NULL,
    year INTEGER NOT NULL,
    value REAL NOT NULL,
    line_id TEXT REFERENCES lines (line_id),
    recorded_at TEXT NOT NULL,
    PRIMARY KEY (series, year)
);

-- ---------------------------------------------------------------------------
-- Routes and coverage
-- ---------------------------------------------------------------------------

CREATE TABLE routes (
    old_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    new_id TEXT NOT NULL
);

CREATE TABLE coverage (
    referent_kind TEXT NOT NULL,
    referent_id TEXT NOT NULL,
    review_status TEXT,
    checked_at TEXT,
    route TEXT,
    document_ids TEXT,
    notes TEXT,
    PRIMARY KEY (referent_kind, referent_id)
);

-- ===========================================================================
-- Named validation queries. Each view returns one row per failure.
-- ===========================================================================

-- An ontology row is in force when it is the terminal row of its
-- supersession chain and its status is `accepted` (storage contract,
-- section 1; ontology section 5). scripts/jetp/_ontology.py applies the same
-- rule at a knowledge cutoff.
CREATE VIEW terms_in_force AS
SELECT t.*
FROM terms AS t
WHERE t.status = 'accepted'
  AND NOT EXISTS (SELECT 1 FROM terms AS s WHERE s.supersedes = t.term_row_id);

CREATE VIEW status_crosswalk_in_force AS
SELECT c.*
FROM status_crosswalk AS c
WHERE c.status = 'accepted'
  AND NOT EXISTS (SELECT 1 FROM status_crosswalk AS s WHERE s.supersedes = c.crosswalk_row_id);

CREATE VIEW sector_crosswalk_in_force AS
SELECT c.*
FROM sector_crosswalk AS c
WHERE c.status = 'accepted'
  AND NOT EXISTS (SELECT 1 FROM sector_crosswalk AS s WHERE s.supersedes = c.crosswalk_row_id);

CREATE VIEW perimeters_in_force AS
SELECT p.*
FROM perimeters AS p
WHERE p.status = 'accepted'
  AND NOT EXISTS (SELECT 1 FROM perimeters AS s WHERE s.supersedes = p.perimeter_row_id);

CREATE VIEW marker_coefficients_in_force AS
SELECT m.*
FROM marker_coefficients AS m
WHERE m.status = 'accepted'
  AND NOT EXISTS (SELECT 1 FROM marker_coefficients AS s
                  WHERE s.supersedes = m.coefficient_row_id);

-- Every ontology row with its chain key, for the chain rules below.
CREATE VIEW ontology_chains AS
          SELECT 'terms' AS tbl, term_row_id AS row_id,
                 coalesce(list, '') || '/' || term_id AS chain, recorded_at, supersedes
            FROM terms
UNION ALL SELECT 'status_crosswalk', crosswalk_row_id, publisher_id || '/' || own_status,
                 recorded_at, supersedes FROM status_crosswalk
UNION ALL SELECT 'sector_crosswalk', crosswalk_row_id, publisher_id || '/' || own_sector,
                 recorded_at, supersedes FROM sector_crosswalk
UNION ALL SELECT 'perimeters', perimeter_row_id, perimeter_id, recorded_at, supersedes
            FROM perimeters
UNION ALL SELECT 'marker_coefficients', coefficient_row_id,
                 donor_party_id || '/' || marker || '/' || score || '/' || year,
                 recorded_at, supersedes FROM marker_coefficients;

CREATE VIEW ontology_in_force AS
          SELECT 'terms' AS tbl, term_row_id AS row_id FROM terms_in_force
UNION ALL SELECT 'status_crosswalk', crosswalk_row_id FROM status_crosswalk_in_force
UNION ALL SELECT 'sector_crosswalk', crosswalk_row_id FROM sector_crosswalk_in_force
UNION ALL SELECT 'perimeters', perimeter_row_id FROM perimeters_in_force
UNION ALL SELECT 'marker_coefficients', coefficient_row_id FROM marker_coefficients_in_force;

-- Every identifier a typed reference (kind, id) may point to. A publisher is
-- a party that publishes at least one document.
CREATE VIEW ledger_identities AS
          SELECT 'publisher' AS kind, party_id AS id FROM document_publishers
UNION ALL SELECT 'document', document_id FROM documents
UNION ALL SELECT 'retrieval', retrieval_id FROM retrievals
UNION ALL SELECT 'snapshot', sha256 FROM snapshots
UNION ALL SELECT 'line', line_id FROM lines
UNION ALL SELECT 'project', project_id FROM projects
UNION ALL SELECT 'asset', asset_id FROM assets
UNION ALL SELECT 'agreement', agreement_id FROM agreements
UNION ALL SELECT 'party', party_id FROM parties
UNION ALL SELECT 'perimeter', perimeter_id FROM perimeters
UNION ALL SELECT 'observation', observation_id FROM observations;

-- The kinds that have a table in this DDL. A typed reference to one of them
-- must resolve; a kind without a table (a country) is not checked here.
CREATE VIEW identity_kinds (kind) AS
VALUES ('publisher'), ('document'), ('retrieval'), ('snapshot'), ('line'),
       ('project'), ('asset'), ('agreement'), ('party'), ('perimeter'),
       ('observation');

-- Closed lists: each value must be a term in force of the named list.
CREATE VIEW violation_closed_list AS
WITH ref (tbl, col, list, value) AS (
              SELECT 'parties', 'authority_category', 'authority_category', authority_category FROM parties
    UNION ALL SELECT 'party_names', 'form_type', 'form_type', form_type FROM party_names
    UNION ALL SELECT 'party_names', 'status', 'decision_status', status FROM party_names
    UNION ALL SELECT 'documents', 'document_type', 'document_type', document_type FROM documents
    UNION ALL SELECT 'document_publishers', 'role', 'role', role FROM document_publishers
    UNION ALL SELECT 'retrievals', 'status', 'retrieval_status', status FROM retrievals
    UNION ALL SELECT 'lines', 'classification', 'line_classification', classification FROM lines
    UNION ALL SELECT 'lines', 'own_status_axis', 'axis', own_status_axis FROM lines
    UNION ALL SELECT 'projects', 'classification', 'project_classification', classification FROM projects
    UNION ALL SELECT 'agreements', 'modality', 'modality', modality FROM agreements
    UNION ALL SELECT 'line_referents', 'referent_kind', 'class', referent_kind FROM line_referents
    UNION ALL SELECT 'line_referents', 'status', 'decision_status', status FROM line_referents
    UNION ALL SELECT 'relations', 'from_kind', 'class', from_kind FROM relations
    UNION ALL SELECT 'relations', 'relation', 'relation', relation FROM relations
    UNION ALL SELECT 'relations', 'to_kind', 'class', to_kind FROM relations
    UNION ALL SELECT 'relations', 'role', 'role', role FROM relations
    UNION ALL SELECT 'relations', 'status', 'decision_status', status FROM relations
    UNION ALL SELECT 'observations', 'subject_kind', 'class', subject_kind FROM observations
    UNION ALL SELECT 'observations', 'axis', 'axis', axis FROM observations
    UNION ALL SELECT 'observations', 'measure', 'measure', measure FROM observations
    UNION ALL SELECT 'observations', 'flow_type', 'flow_type', flow_type FROM observations
    UNION ALL SELECT 'observations', 'basis', 'basis', basis FROM observations
    UNION ALL SELECT 'observations', 'status', 'decision_status', status FROM observations
    UNION ALL SELECT 'timings', 'date_role', 'date_role', date_role FROM timings
    UNION ALL SELECT 'timings', 'date_precision', 'date_precision', date_precision FROM timings
    UNION ALL SELECT 'external_ids', 'kind', 'class', kind FROM external_ids
    UNION ALL SELECT 'adjudications', 'decision_type', 'decision_type', decision_type FROM adjudications
    UNION ALL SELECT 'adjudications', 'subject_kind', 'class', subject_kind FROM adjudications
    UNION ALL SELECT 'adjudications', 'status', 'decision_status', status FROM adjudications
    UNION ALL SELECT 'adjudication_members', 'kind', 'class', kind FROM adjudication_members
    UNION ALL SELECT 'routes', 'kind', 'class', kind FROM routes
    UNION ALL SELECT 'coverage', 'referent_kind', 'class', referent_kind FROM coverage
    UNION ALL SELECT 'status_crosswalk', 'axis', 'axis', axis FROM status_crosswalk
    UNION ALL SELECT 'status_crosswalk', 'status', 'decision_status', status FROM status_crosswalk
    UNION ALL SELECT 'sector_crosswalk', 'status', 'decision_status', status FROM sector_crosswalk
    UNION ALL SELECT 'perimeters', 'status', 'decision_status', status FROM perimeters
    UNION ALL SELECT 'marker_coefficients', 'marker', 'marker', marker FROM marker_coefficients
    UNION ALL SELECT 'marker_coefficients', 'score', 'marker_score', score FROM marker_coefficients
    UNION ALL SELECT 'marker_coefficients', 'status', 'decision_status', status FROM marker_coefficients
)
SELECT tbl || '.' || col || ' = ''' || value || ''' is not a term in force of list '''
       || list || '''' AS detail
FROM ref
WHERE value IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM terms_in_force AS t WHERE t.list = ref.list AND t.term_id = ref.value
  );

-- Typed references resolve to an existing row of their kind.
CREATE VIEW violation_typed_reference AS
WITH ref (tbl, key, kind, id) AS (
              SELECT 'observations', observation_id, subject_kind, subject_id FROM observations
    UNION ALL SELECT 'line_referents', referent_row_id, referent_kind, referent_id FROM line_referents
    UNION ALL SELECT 'relations', relation_id, from_kind, from_id FROM relations
    UNION ALL SELECT 'relations', relation_id, to_kind, to_id FROM relations
    UNION ALL SELECT 'external_ids', scheme || ':' || external_id, kind, id FROM external_ids
    UNION ALL SELECT 'adjudications', adjudication_id, subject_kind, subject_id FROM adjudications
    UNION ALL SELECT 'adjudication_members', adjudication_id, kind, id FROM adjudication_members
    UNION ALL SELECT 'routes', old_id, kind, new_id FROM routes
    UNION ALL SELECT 'coverage', referent_kind || ':' || referent_id, referent_kind, referent_id FROM coverage
)
SELECT tbl || ' ' || key || ': ' || kind || ' ''' || id || ''' does not exist' AS detail
FROM ref
WHERE kind IN (SELECT kind FROM identity_kinds)
  AND NOT EXISTS (SELECT 1 FROM ledger_identities AS i WHERE i.kind = ref.kind AND i.id = ref.id);

-- A line's snapshot is yielded by at least one retrieval.
CREATE VIEW violation_line_snapshot_retrieved AS
SELECT 'lines ' || l.line_id || ': snapshot ' || l.sha256 || ' is yielded by no retrieval' AS detail
FROM lines AS l
WHERE NOT EXISTS (SELECT 1 FROM retrievals AS r WHERE r.sha256 = l.sha256);

-- A flow carries period_start and period_end, or one event timing.
CREATE VIEW violation_flow_timing AS
SELECT 'observations ' || o.observation_id
       || ': a flow needs period_start and period_end, or one event timing' AS detail
FROM observations AS o
WHERE o.measure = 'flow'
  AND NOT (
      (SELECT count(*) FROM timings AS t
        WHERE t.observation_id = o.observation_id AND t.date_role = 'event') = 1
      OR (EXISTS (SELECT 1 FROM timings AS t
                   WHERE t.observation_id = o.observation_id AND t.date_role = 'period_start')
          AND EXISTS (SELECT 1 FROM timings AS t
                       WHERE t.observation_id = o.observation_id AND t.date_role = 'period_end'))
  );

-- A crosswalk maps a publisher's word onto a value of the axis it names: an
-- axis's term_id is the name of the list its values belong to.
CREATE VIEW violation_crosswalk_shared_status AS
SELECT 'status_crosswalk ' || c.crosswalk_row_id || ': shared_status = '''
       || c.shared_status || ''' is not a term in force of axis ''' || c.axis || ''''
       AS detail
FROM status_crosswalk AS c
WHERE NOT EXISTS (
    SELECT 1 FROM terms_in_force AS t WHERE t.list = c.axis AND t.term_id = c.shared_status
);

-- Ontology chains: a revision keeps its chain key and is not recorded before
-- the row it supersedes, and a chain key has at most one row in force.
CREATE VIEW violation_ontology_chain AS
SELECT r.tbl || ' ' || r.row_id || ': supersedes ' || p.row_id
       || ' of another chain (' || p.chain || ', not ' || r.chain || ')' AS detail
FROM ontology_chains AS r
JOIN ontology_chains AS p ON p.tbl = r.tbl AND p.row_id = r.supersedes
WHERE p.chain <> r.chain
UNION ALL
SELECT r.tbl || ' ' || r.row_id || ': recorded_at ' || r.recorded_at
       || ' is before that of the row it supersedes, ' || p.row_id
FROM ontology_chains AS r
JOIN ontology_chains AS p ON p.tbl = r.tbl AND p.row_id = r.supersedes
WHERE r.recorded_at < p.recorded_at
UNION ALL
SELECT c.tbl || ' ' || c.chain || ': more than one row in force ('
       || group_concat(c.row_id, ', ') || ')'
FROM ontology_chains AS c
JOIN ontology_in_force AS f ON f.tbl = c.tbl AND f.row_id = c.row_id
GROUP BY c.tbl, c.chain
HAVING count(*) > 1;

-- A value belongs to a list; a relation states its domain and range; a
-- mapping other than `local` names its scheme and the concept's URI or code.
CREATE VIEW violation_term_shape AS
SELECT 'terms ' || term_row_id || ': a value term names its list' AS detail
FROM terms WHERE kind = 'value' AND list IS NULL
UNION ALL
SELECT 'terms ' || term_row_id || ': a relation term states its domain and range'
FROM terms WHERE kind = 'relation' AND (domain IS NULL OR range IS NULL)
UNION ALL
SELECT 'terms ' || term_row_id || ': mapping ' || mapping_relation
       || ' names no external scheme or URI'
FROM terms
WHERE mapping_relation <> 'local' AND (external_scheme IS NULL OR external_uri IS NULL);

-- A party's name forms are revised by supersession; a form is in force when
-- it is the accepted terminal row of its chain.
CREATE VIEW party_names_in_force AS
SELECT n.*
FROM party_names AS n
WHERE n.status = 'accepted'
  AND NOT EXISTS (SELECT 1 FROM party_names AS s WHERE s.supersedes = n.name_row_id);

-- Exactly one preferred name form in force per party.
CREATE VIEW violation_party_preferred_name AS
SELECT 'parties ' || p.party_id || ': ' || count(n.name_row_id)
       || ' preferred name forms in force, expected exactly one' AS detail
FROM parties AS p
LEFT JOIN party_names_in_force AS n
       ON n.party_id = p.party_id AND n.form_type = 'preferred'
GROUP BY p.party_id
HAVING count(n.name_row_id) <> 1;

-- The name form a publication shows is a form of that publication's party.
CREATE VIEW violation_publication_name_form AS
SELECT 'document_publishers ' || d.document_id || ' / ' || d.party_id
       || ': name form ' || d.name_row_id || ' belongs to party ' || n.party_id AS detail
FROM document_publishers AS d
JOIN party_names AS n ON n.name_row_id = d.name_row_id
WHERE n.party_id <> d.party_id;
