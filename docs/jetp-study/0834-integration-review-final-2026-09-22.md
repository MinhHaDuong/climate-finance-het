# Revue d'intégration finale — tracker 0834 « M1a : le MVP explore les données en trois étages »

Revue adversariale, en lecture seule, sur `main` à `bf31b3ee34d8844b9927e98e470377e28f32894c`
(« Merge pull request #1441 from MinhHaDuong/t0854-sources-vnm »), dans le worktree
`/home/haduong/CNRS/projets/actifs/climate-finance-het/.claude/worktrees/agent-a13512b4c228f6e76`.
Aucun fichier suivi n'a été modifié, rien n'a été committé ni poussé : `git status --porcelain`
rend zéro ligne à la fin de la session.

Elle fait suite à la revue du 2026-09-22 ~00:00
(`docs/jetp-study/0834-integration-review-2026-09-22.md`, verdict NE PAS FERMER sur trois prises)
et contrôle ce que les PR #1439 (0855, 0856, 0857), #1443 (0858) et #1441 (0854) ont livré depuis.

**Préparation du worktree.** `.venv` → `/data/envs/venv/oeconomia`, `.env` copié du dépôt
principal, `dvc pull data/jetp/documents.dvc` (264 fichiers, remote padme joignable, exit 0),
`make jetp-data`, `make jetp-observatory-documents` (264 objets réfléchis sous
`deliverables/jetp-observatory/documents/`). Les artefacts de corpus du préflux
(`scripts/qa_full_gate_preflight.py:13-18`) sont liés depuis le dépôt principal, `data/derived`
et `data/exports` **copiés** — des tests y écrivent.

**Aperçu** servi par `python3 -m http.server 8771 --bind 127.0.0.1 --directory
deliverables/jetp-observatory`, sur les artefacts **committés** de `main`, pas sur une
reconstruction locale : la recette doit juger ce qui a fusionné. Le port 8765 de l'auteur n'a
jamais été touché. Serveur arrêté en fin de session.

---

## 1. Verdict — **NE PAS FERMER**, mais pour une seule raison et d'une seule ligne

Les trois prises de la revue précédente sont réparées et vérifiées à l'écran : le plafond de
publication ZAF est repassé dessous (`ZAF.json` 509 315 octets, §4), la page Documents ne somme
plus les deux produits d'étage 2 (« Ledger rows · 257 » et « M1a rows · 257 », jamais 514, §5),
et le RMP 2023 s'ouvre en un clic à la page imprimée 139 depuis le registre des documents
(`…b145af2e….pdf#page=155`, §3). Les sept sources vietnamiennes de 0854 sont collectées et
ouvrent leur document local, 7/7. **Les critères de sortie 3 et 4 peuvent être cochés** : la
recette Vietnam passe désormais de bout en bout telle qu'elle est écrite, et aucun étage ni
sous-couche n'agrège plus les lignes d'un autre, ni dans les générateurs ni à l'écran. La recette
navigateur livrée (`tests/browser/jetp_observatory.py`) passe **trois fois sur trois**, sans
aucune défaillance à son assertion finale — l'échec intermittent du lien d'évitement sur
`#country/IDN` ne s'est pas reproduit ici.

Ce qui reste s'oppose à la fermeture : **`make check` complet est rouge, et le troisième échec est
une régression du train, née de PR #1441 (0854).**
`tests/test_jetp_vnm_positions.py:168` épingle `len(result['legacy_dispositions']) == 227` ; la
valeur est 234 depuis que le commit `43b6fc4d data(0854): collecter les sept sources
vietnamiennes du ledger` a ajouté sept lignes `collected` à `data/jetp/manifest.csv` (lignes
309–315). J'ai nommé les sept dispositions ajoutées une par une (§4) : ce sont exactement les
sept, classées `acquisition_history`, `retained_legacy_authority`. Aucun autre épinglage du même
test ne bouge — j'ai recalculé les neuf, un seul a dérivé. **La réparation est une ligne**, et
c'est le même mécanisme que la fois précédente : le palier lent n'est vérifié qu'*ex post*, la
porte de 0854 était `make check-fast` + `make lint`, et rien entre les deux n'a regardé.

Le reste du dossier est propre, et solidement gardé : le harnais de rendu Node de 0856/0857/0858
compte onze tests au **palier rapide** (aucun `@pytest.mark.slow`), et je l'ai muté pour vérifier
qu'il a des dents — en rétablissant le rendu d'avant 0856 sur une copie du site dans le
scratchpad, trois de ces tests tombent, et le premier affiche `{'mixed': '514'}` contre
`{'ledger': '257', 'm1a': '257'}` : très exactement le défaut que la revue précédente avait relevé
à l'écran. Le garde n'est pas décoratif.

**Ce que l'auteur doit trancher pour le critère 5** — la ligne M1a de 0725
(`tickets/0725-jetp-observatory-and-papers.erg:37`, « M1a accepted: the MVP explores documents,
extractions and facts end to end on the SA and VN acceptance cases ») et celle de 0715
(`tickets/0715-suivi-vivant-jetp-quatre-pays.erg:79`) : la recette est verte des deux côtés et
l'invariant de non-fusion tient, donc la décision n'est plus technique. Elle porte sur deux
écarts de lecture que cette revue laisse ouverts et n'a pas autorité pour fermer : (a) la fiche
0834 dit « ses quatre sources » pour Bac Ai, la donnée en porte six dont quatre archivées — est-ce
la fiche qu'on corrige, ou la recette ? (b) le lecteur voit « 1 740 observations atomiques » sur
la page Editions et 766 dans les vues servies (§6, point 2) ; deux populations correctement
étiquetées, jamais additionnées, mais jamais réconciliées non plus par une phrase. Aucune des
deux n'empêche de cocher ; les deux méritent d'être vues avant de le faire.

Recommandation : réparer l'épinglage 227 → 234 (un enfant de 0834, une ligne, palier lent), cocher
les critères 3 et 4 maintenant, laisser le 5 à l'auteur. La revue suivante sera d'une minute.

---

## 2. Critères de sortie de 0834

| # | Critère | Verdict | Preuve |
|---|---|---|---|
| 1 | Les cinq enfants sont fermés | **atteint** | `tickets/closed/0835…0839`, `Closed:` non vide. Les quatre enfants de suite le sont aussi : `tickets/closed/0855-…erg:5`, `0856-…erg:5`, `0857-…erg:5` (« autoclosed — PR #1439 »), `0858-…erg:5` (« PR #1443 »), plus `0854-…erg:5` (« PR #1441 »). |
| 2 | La recette Afrique du Sud passe de bout en bout dans le navigateur | **atteint** | SA1/SA2/SA3 PASS, §3. Empreinte servie == `sha256` du registre ; 88 lignes « D. Completed » sur 257, 21 champs `raw_*` ; descente projet → ligne de ledger → snapshot vérifiée par popup. |
| 3 | La recette Vietnam passe de bout en bout dans le navigateur | **atteint — à cocher** | VN1 PASS (le pas qui manquait : `#page=155` en un clic depuis le registre), VN2 PASS (37 lignes annexe I.1, ligne 22 = KN Tri An → `#page=156`), VN3 PASS **sans lecture restreinte** (7/7 observations du ledger ouvrent leur document local, HTTP 200), VN4 PASS. §3. |
| 4 | Aucun étage n'agrège ni ne fusionne les lignes d'un autre | **atteint — à cocher** | À l'écran : un dépliage par produit avec son compte propre, sur les quatre documents mixtes ; aucune occurrence du littéral `514`. Dans le code : plus aucune somme ni jointure inter-étages dans les générateurs ; `by_source_id` supprimé. §5. |
| 5 | La ligne M1a de 0725 et 0715 cochée par l'auteur après revue d'intégration | **non atteint, par dessin** | Appartient à l'auteur. La revue lève ses objections techniques et lui laisse deux écarts de lecture (§1, §6). |

---

## 3. Parcours des recettes, pas à pas

Marche indépendante,
`scratchpad/recipe_walk.py`, qui **ne réutilise aucune assertion** de
`tests/browser/jetp_observatory.py` : chaque valeur est redérivée du JSON servi (les vues M1a
arrivent en `fields` + lignes positionnelles, rezippées en dictionnaires, la forme que `app.js`
hydrate) puis relue dans le DOM. Zéro `pageerror`, zéro `requestfailed` sur l'ensemble du
parcours. Journal complet : `scratchpad/walk.log`. Captures dans `scratchpad/shots/`.

### Afrique du Sud

| Pas | Énoncé du ticket | Verdict | Observation |
|---|---|---|---|
| SA1 | Ouvrir le snapshot HTML archivé du registre depuis le registre des documents | **PASS** | Ligne de compte `1 of 314 sources`. `a[data-document-id="zaf-jet-investment-register-q1-2026:1"]` → `documents/objects/5b/5b5d6442…f4.html` ; SHA-256 des octets servis == `sha256` du registre (recalculé, pas relu) ; popup ouverte, titre `Investment-Register-Dashboard - Just Energy Transition`. `shots/SA1-documents-register-row.png`, `shots/SA1-snapshot-opened.png` |
| SA2 | Filtrer l'inventaire M1a ZAF sur « D. Completed » → 88 lignes, chacune avec ses 21 champs source | **PASS** | Vérité terrain redérivée de `m1a/ZAF.json` : 88 lignes `reported_status == "D. Completed"`. Ligne de compte lue au DOM : `88 of 257 rows in this export · page 1 of 2`. 21 clés `raw_*` dans la charge utile (sur 32 champs = 11 + 21) et 65 lignes de détail dépliées dans le DOM. `shots/SA2-inventory-zaf-completed.png` |
| SA3 | Depuis un projet de la vue pays, descendre à sa ligne de registre puis au snapshot | **PASS** | `#project/zaf-register-actip001` → `details[data-evidence-count="1"]` → `documents/objects/5b/5b5d6442…f4.html`, popup ouverte à cette URL. Le dépliage est désormais construit par jointure à la lecture sur `observations/ZAF.json` (0855), pas par recopie dans la vue pays. `shots/SA3-project-evidence.png`, `shots/SA3b-snapshot-from-project.png` |

*L'écart 258 / 257 du ticket reste réconcilié comme en première revue* : la 258ᵉ entrée est la
ligne d'agrégat du tableau de bord, exclue délibérément
(`docs/jetp-study/0818-zaf-q1-2026-report.md:26-30`). Rien n'a changé de ce côté.

### Vietnam

| Pas | Énoncé du ticket | Verdict | Observation |
|---|---|---|---|
| VN1 | Ouvrir le PDF du RMP 2023 à la page imprimée 139 **depuis le registre des documents** | **PASS — la prise de la revue précédente est réparée** | L'ancre « Open archived copy » porte maintenant `documents/objects/b1/b145af2e…3c.pdf#page=155` : un clic, page imprimée 139. Le fragment n'est pas fabriqué — `extractionCell()` (`app.js:445-451`) le repose *après* la jointure, depuis `firstPdfPage()` (`app.js:393-403`), qui ne rend une page que si tous les produits qui en nomment une s'accordent sur la première. Popup ouverte (Chromium sans tête n'atteint jamais l'état `load` du visualiseur PDF, donc pas de capture de la popup — l'URL et le `href` sont la preuve). `shots/VN1-documents-rmp.png` |
| VN2 | Filtrer l'inventaire M1a VNM sur l'annexe I.1 → 37 lignes ; la ligne 22 (KN Tri An Floating Solar Farm) ouvre le PDF à sa page | **PASS** | Vérité terrain : 37 lignes portant « Annex I.1 ». DOM : `37 of 279 rows in this export`. La ligne 22 de l'export est bien `22 KN Tri An Floating Solar Farm Dong Nai 928 MW 2030 Decision No. 500/QD-TTg PDP8`, localisateur `Annex I.1; PDF pages 156; printed pages 140; ordinal 22`, lien `…pdf#page=156`. `shots/VN2a-inventory-annex-I1.png`, `shots/VN2b-inventory-tri-an.png` |
| VN2b | *La remontée que 0857 a ajoutée* | **PASS** | Depuis `#documents`, le 22ᵉ `<li>` du dépliage M1a du RMP porte deux liens : `#inventory/VNM?row=22` (sa propre ligne) et `…pdf#page=156` (sa page). `#inventory/VNM?row=22` ouvre **une seule ligne**, `data-inventory-focus="22"`, c'est KN Tri An. Le lecteur n'atterrit plus sur 279 lignes non filtrées. `shots/VN2c-inventory-row22.png`, `shots/VN2d-documents-rmp-positions.png` |
| VN3 | Depuis Bac Ai dans la vue pays, remonter à ses sources et ouvrir le bulletin 5 du MOIT (juillet 2025) | **PASS** | `#project/vnm-project-bac-ai-pumped-hydro` : **quatre** liens `data-archived-source` (`vnm-eib-bac-ai-package-2025`, `vnm-evn-cdp-bac-ai-2025`, `vnm-moit-newsletter-05-2025-07`, `vnm-moit-project-bac-ai`), contre **un** en première revue. Le bulletin 5 ouvre bien l'archive locale, popup ouverte. `shots/VN3-bac-ai.png` |
| VN3bis | *Les observations du ledger ouvrent leur propre document (0854)* | **PASS** | `observations/VNM.json` : 7 lignes, **zéro sans `sha256`** (c'était 7 sur 7 avant 0854). À l'écran, sur les trois fiches projet concernées : Bac Ai 3/3, Binh Duong–Dong Nai 2/2, Tri An 2/2 — **7/7**, chaque lien récupéré en HTTP 200, et plus aucune mention « No archived copy of this source ». `shots/VN3c-vnm-project-bac-ai-pumped-hydro.png`, `shots/VN3c-vnm-project-binh-duong-dong-nai-tran.png`, `shots/VN3c-vnm-project-tri-an-expansion.png` |
| VN4 | Constater la table initiale et les 24 enregistrements de 2025 côte à côte, sans lien fabriqué | **PASS** | `#vnm-side-by-side` : « RMP 2023 initial table — 279 positions », « 2025 portfolio — 24 records: 3 named and 21 unpublished identities », et la phrase « No link between the 2023 table and the 2025 portfolio is established here ». Aucun champ ne joint les deux objets. `shots/VN4-side-by-side.png` |

**Un écart de fiche, pas de livraison.** Le tracker écrit « ses quatre sources » ; `VNM.json`
en donne six à Bac Ai (`vnm-eeas-jetp-project-progress-2025`, `vnm-eib-bac-ai-package-2025`,
`vnm-evn-cdp-bac-ai-2025`, `vnm-moit-newsletter-05-2025-07`, `vnm-moit-project-bac-ai`,
`vnm-moit-project-index-2026`), dont quatre archivées depuis 0854. La coïncidence « quatre
archivées / quatre dans la fiche » est fortuite : ce ne sont pas les quatre mêmes. L'écart était
déjà consigné au journal de 0839 (`2026-09-21T22:10Z`). `shots/PROBE-Q2-bac-ai-sources.png`.

**Recette navigateur livrée : trois exécutions, trois succès.**
`tests/browser/jetp_observatory.py --url http://127.0.0.1:8771` rend
`Browser checks passed; 97 historical records` aux trois passages, exit 0 à chaque fois
(`scratchpad/browser-run1.log`, captures `shots/BROWSER-run1.png`, `-run2`, `-run3`). L'échec
intermittent signalé sur la dernière assertion — focus du lien d'évitement sur `#country/IDN` —
**ne s'est pas produit une seule fois**. Ce n'est pas une preuve qu'il a disparu : trois succès
ne falsifient pas une intermittence, ils bornent sa fréquence. Rien n'a été observé à signaler.

---

## 4. Classement des échecs de `make check`

`make check` complet, palier lent inclus, dans ce worktree :
**`3 failed, 3100 passed, 57 skipped` en 605,72 s** (`scratchpad/make-check.log`).
Le train en a réparé un et en a cassé un autre : `test_zaf_candidate_reconciles_inventory_legacy_and_current_views`,
l'échec causé par 0839 en première revue, **passe maintenant** (0855).

| Test en échec | Classement | Preuve, par l'entrée manquante nommée |
|---|---|---|
| `tests/test_jetp_courbe_reference.py::test_chaine_portee_reproduit_la_reference` | **environnemental** | Le test nomme son entrée : `tests/test_jetp_courbe_reference.py:68` — « `…/data/jetp/crs` absent : lancer `dvc pull data/jetp/crs` avant ce test. Pas de skip ». Contrôle : le répertoire est **également absent du dépôt principal** (`ls /home/haduong/…/climate-finance-het/data/jetp/crs` → no such file), et aucun pointeur `crs*` n'existe sous `data/jetp/`. Artefact jamais matérialisé sur cette machine ; aucun fichier du train ne le touche. |
| `tests/test_jetp_public_release.py::test_reviewed_evidence_records_are_distinct_non_aggregate_and_traceable` | **environnemental** | Entrée manquante : le commit `3b432ef322ed9a1bb099089b24b793f6d791842a`. `scripts/jetp/_public_release.py:180` fait `git cat-file -e 3b432ef3…^{commit}` → exit 128, « Not a valid object name ». **Contrôle positif** : la même commande sur `bf31b3ee…^{commit}` rend exit 0, donc la sonde voit les objets qui existent ; et `git rev-parse --git-common-dir` montre que ce worktree partage la base d'objets du dépôt principal, donc l'absence est celle du clone entier, pas du worktree. |
| `tests/test_jetp_vnm_positions.py::test_real_candidate_covers_inventory_legacy_and_all_country_views` | **CAUSÉ PAR LE TRAIN — PR #1441 (0854)** | Aucune entrée ne manque. Voir ci-dessous. |

### Le troisième échec est une régression attribuable, et sa réparation est d'une ligne

`tests/test_jetp_vnm_positions.py:168` : `assert len(result['legacy_dispositions']) == 227`,
observé `234`. Le delta est **exactement sept**, et les sept sont nommables :
`scripts/jetp/_country_migration.py:69` classe `manifest.csv` en `acquisition_history`, et
`build_migration()` rend aujourd'hui sept dispositions `acquisition_history` /
`retained_legacy_authority` de plus, portant `"path": "data/jetp/manifest.csv"` et
`"row_number"` 309 à 315 (`scratchpad/why234.py`). Ces sept lignes du registre sont les sept
collectes de 0854, horodatées `2026-09-22T06:34Z`, ajoutées par le commit
`43b6fc4d data(0854): collecter les sept sources vietnamiennes du ledger`. Le test, lui, n'a pas
été touché par 0854 : son dernier commit est `d1964d49`, sans rapport.

**Tous les autres épinglages du même test tiennent** — je les ai recalculés pour que la réparation
soit d'un seul passage et non de trois rerolls (`scratchpad/pins.py`) :

| Épinglage | Attendu | Observé |
|---|---|---|
| `inventory_positions` | 279 | 279 |
| **`legacy_dispositions`** | **227** | **234** |
| `legacy_position_candidates` | 46 | 46 |
| `legacy_unresolved` | 53 | 53 |
| `comparison.existing_project_ids` | 24 | 24 |
| `comparison.added_public_project_ids` | `[]` | `[]` |
| `selected_acquisition.retrieved_at` | `2026-09-11T20:39:00Z` | idem |
| `selected_acquisition.recorded_at` | `None` | `None` |
| `extraction.recorded_at` | `2026-09-14*` | `2026-09-14T18:12:19Z` |
| sous-chaînes `vnm-pilot-source-066`, `partial`, `7040000000`, `5520000000` | présentes | présentes |

Ce n'est pas une donnée fausse : 234 est **la valeur juste**, le registre a réellement gagné sept
acquisitions. C'est l'attente qui est périmée. Mais le résultat est que `main` échoue à
`make check`, et que rien ne l'a signalé — même mécanisme qu'il y a huit heures : pas de CI
(0321), palier lent vérifié *ex post* seulement, et la porte de 0854 était `check-fast` + `lint`.
C'est le deuxième aller-retour de suite du même piège sur le même tracker.

---

## 5. Audit du critère 4 — à l'écran et dans le code

### À l'écran : la fusion affichée a disparu

Relevé dans le DOM, sur les quatre sources que la revue précédente accusait
(`shots/C4-zaf.png`, `C4-idn.png`, `C4-sen-annexes.png`, `C4-sen-l4.png`) :

| source | dépliages rendus | ancien affichage |
|---|---|---|
| `zaf-jet-investment-register-q1-2026` | `Ledger rows · 257` + `M1a rows · 257` + `Facts relying on it · 257` | ~~514~~ |
| `idn-jetp-progress-report-2025` | `Ledger rows · 113` + `M1a rows · 1,142` + `Facts relying on it · 75` | ~~1 255~~ |
| `sen-investment-plan-annexes-mirror` | `Ledger rows · 67` + `M1a rows · 38` + `Facts relying on it · 38` | ~~105~~ |
| `sen-investment-plan-l4-mirror` | `Ledger rows · 82` + `M1a rows · 11` + `Facts relying on it · 35` | ~~93~~ |

Chaque dépliage porte son discriminant `data-extracted-product` et son propre
`data-extracted-count`. Le littéral `514` n'apparaît nulle part dans les résultats rendus. Le
libellé de colonne est devenu « Extracted here, per product · relied on by » (`app.js:519`).

**La note d'une phrase, décision de l'auteur, est bien là.** 55 sources livrées sont citées par un
fait sans qu'aucune ligne n'en ait été extraite. Sur `idn-portfolio-candi-umbul`, la cellule rend
`<p class="note" data-extracted-count="0">Nothing extracted from this source in this edition.</p>`
puis, à côté, `Facts relying on it · 1` : la note remplace **une** liste, pas les deux — exactement
ce que `app.js:370-375` documente comme décision du 2026-09-22 (PR #1439).
`shots/PROBE-Q3-facts-no-extract.png`. Et une source que rien ne cite *ni* n'extrait rend l'autre
note, `span[data-uncited]` : 41 occurrences sur la seule page ZAF.
`shots/C4-empty-notes-zaf.png`.

**La ligne de compte de l'inventaire ne ment plus, et la note au-dessus ne la contredit plus.**
Relevé sur `#inventory/IDN` : `1579 of 1579 rows in this export · page 1 of 32`, et trente pixels
au-dessus (`app.js:596`) : « Each figure counts one extraction sub-layer of this country. **The
count line under the filters is the size of this export, the sub-layers laid end to end: it says
how many rows the file holds, not how many projects the country has**, because the sub-layers
overlap and count different things, and a country is not the unit any of them measures. » La
vieille phrase « This page adds none of them together » a disparu. Le tableau de la page Methods
suit : colonne « Rows in this export » (`app.js:1114`) et note « the size of a file, not a count
of projects ». `shots/C4-idn-inventory-count.png`, `shots/C4-methods.png`.

### Dans le code : plus rien à additionner entre étages

Grep de `sum(`, `Counter(`, `.merge(`, `drop_duplicates`, `dedup`, `groupby` sur
`build_observatory.py`, `build_observations.py`, `build_m1a_inventories.py`, `_observatory_data.py`,
`_m1a_document_links.py`, `build_observatory_provenance.py` — quatre occurrences en tout :

- `build_observatory.py:149-150` — deux `Counter` sur les projets **d'un seul pays** (étage 3, `stages`, `technologies`). Pas d'inter-étage.
- `build_observatory.py:208` — `attempts = Counter()`, un **ordinal** par identifiant de source pour composer `row_key` (0853). Ce n'est pas un agrégat : il numérote, il n'additionne pas.
- `build_m1a_inventories.py:231` — le seul `sum()` inter-sous-couches qui subsiste (`unknowns.field_values`, etc.). Il est désormais **honnêtement libellé** par les deux notes ci-dessus : une propriété du fichier, pas une population.

`by_source_id` a disparu du générateur comme du livrable : `documents.json` porte **une seule clé**,
`documents`, **314 lignes**, **155 720 octets** — sous le plafond de 512 000. Ce qui restait de
`extraction_index()`, `m1a_reference()` et `ledger_reference()` n'existe plus que dans deux
commentaires qui racontent pourquoi (`build_observatory.py:182`, `app.js:333`). La remontée
document → faits est bien une jointure à la lecture, refaite dans `extractedRows()` et
`factsRelyingOn()` (`app.js:404-430`) sur les vues déjà servies.

### Mesures du §4 de la consigne

| Contrôle | Attendu | Mesuré | Verdict |
|---|---|---|---|
| `documents.json` : une seule clé | oui | `['documents']` | ✅ |
| `documents.json` : nombre de lignes | 314 | 314 | ✅ |
| `documents.json` : taille | < 512 000 o | **155 720 o** | ✅ |
| `ZAF.json` : taille | < 512 000 o | **509 315 o** (2 685 o de marge, la valeur d'avant le train) | ✅ |
| `.githooks/pre-commit` : plafond intact | 512 000, sans exemption | `.githooks/pre-commit:49` `limit=512000` ; `git diff origin/main -- .githooks/` **vide** ; dernier commit sur le fichier `7e464af9` (ticket 0610, antérieur au train) — le commit `dee039ea` de 0854 qui relevait le plafond à 1 Mo a bien été abandonné au rebase | ✅ |

### Les gardes ont des dents — vérifié par mutation

`tests/test_jetp_observatory_render.py` compte onze tests, **tous au palier rapide** (aucun
`@pytest.mark.slow`) ; avec `test_jetp_observatory_facts.py`,
`test_jetp_observatory_observations.py` et `test_jetp_zaf_migration.py`, **37 passed in 7.64s**.
Le plafond de publication est gardé au palier rapide, lu depuis la configuration
(`tests/test_jetp_observatory_facts.py:113`, `assert view.stat().st_size <= policy["publication_limit_bytes"]`),
et non plus seulement par le test lent qui avait laissé passer 0839.

Contrôle positif du garde de 0856 : j'ai copié le site dans
`scratchpad/mutant/` et y ai rétabli le rendu d'avant 0856 (un seul `foldout("Extracted here", …)`
sur la liste mixte), puis fait tourner le harnais Node contre cette copie. **Trois tests tombent**,
et le premier affiche exactement la prise de la revue précédente :

```
AssertionError: assert {'mixed': '514'} == {'ledger': '257', 'm1a': '257'}
```

`test_the_documents_page_shows_one_extracted_summary_per_product_never_a_sum`,
`test_a_document_with_one_product_gets_one_fold_out` et
`test_a_document_shows_what_it_yielded_and_what_relies_on_it_as_lists_never_a_total`. Le test est
clé sur le trait distinctif — la paire `(product, count)` — et non sur le libellé, ce que son
propre commentaire dit en toutes lettres (`:161-163`). Aucun fichier suivi n'a été muté : la
mutation vit dans le scratchpad et le test a été repointé par copie.

---

## 6. Résidu, passé au plancher de sévérité

**Au-dessus du plancher — un ticket, un seul :**

0. **L'épinglage périmé de `tests/test_jetp_vnm_positions.py:168`** (§4). Il bloque `make check`
   sur `main`, ce qui est la définition même du plancher côté voie science. Enfant de 0834,
   réparation `227` → `234`, avec en corps la raison (les sept acquisitions de 0854) pour que le
   nombre ne redevienne pas un nombre magique. Les huit autres épinglages du test sont vérifiés
   inchangés, donc le correctif n'a pas besoin d'être exploratoire.

**Sous le plancher — à signaler, pas à ficher :**

1. **Trois épinglages frères de la même classe**, tous au palier lent :
   `test_jetp_vnm_positions.py:168` (227), `test_jetp_idn_positions.py:56` (2285),
   `test_jetp_zaf_migration.py:22` (1087). Chacun compte, entre autres, les lignes
   `manifest.csv` de son pays. **Toute collecte future dans ZAF, IDN ou SEN cassera son propre
   épinglage, invisible à la porte rapide** — c'est ce qui vient de se produire pour VNM. La
   réparation durable n'est pas de remettre un nombre : c'est de dériver la part
   `acquisition_history` du registre au lieu de l'épingler. À traiter dans le ticket du point 0,
   ou à laisser tomber — mais pas à découvrir une troisième fois.
2. **« 1 740 » contre « 766 ».** La page Editions affiche toujours `1 740` observations atomiques
   depuis `reviewed-evidence.json → evidence_depth.structured_atomic_observations`
   (`status: not_deployed`, répartition IDN 1 148, SEN 10, VNM 325, ZAF 257) tandis que les vues
   servies en comptent **766** (ZAF 338, IDN 158, VNM 7, SEN 263). Deux populations distinctes,
   toutes deux correctement étiquetées, jamais additionnées — donc **aucun critère enfreint**.
   Mais un lecteur qui passe d'une page à l'autre voit deux nombres pour « observations
   atomiques » sans réconciliation. Une phrase suffirait. Reporté tel quel de la revue précédente,
   comme demandé : résidu, pas bloquant.
3. **Résidu de vocabulaire « layer », visible par l'utilisateur.** `app.js:1075` : « These are
   distinct **layers**. They are not a common record total. » — et c'est le seul endroit où le
   modèle à trois étages est expliqué au lecteur. `app.js:1123` : « Implementation observations
   are a separate **layer**. » Le vocabulaire « sub-layer » (4 occurrences) est cohérent et voulu,
   c'est bien de sous-couches qu'il s'agit ; ce sont les deux phrases ci-dessus qui emploient
   « layer » au sens que 0834 a remplacé par « étage ». `source_layer` fuit toujours à l'écran dans
   le dépliage d'une ligne d'inventaire (relevé au DOM : `source_layer / register-q1-2026`) —
   cosmétique. Résidu, comme demandé.
4. **Les 21 observations sans empreinte hors périmètre 0854.** Sur 766 observations servies, 21
   n'ont pas de `sha256` : ZAF 2, IDN 8, SEN 11 — les sept du Vietnam sont réglées (0/7 désormais).
   Elles sont surveillées par
   `tests/test_jetp_observatory_observations.py::test_a_row_without_a_fingerprint_is_one_of_two_named_collection_gaps`,
   dont le commentaire les nomme et dont la première liste est maintenant **vide, pas comptée** —
   toute nouvelle source citée sans tentative de collecte échouera avec son identifiant. Rien ne
   planifie leur collecte ; à signaler à l'auteur, pas à ficher.
5. **`countStages` (`app.js:44`) est toujours du code mort** — une seule occurrence dans le
   fichier, la définition. Signalé en première revue, non traité. À supprimer au passage suivant.
6. **Deux lignes de registre pour un même document, chacune annonçant les mêmes 279 positions.**
   `vnm-rmp-2023` porte deux tentatives (`:1` `collected`, `:2` `not_modified`, même `sha256`), et
   la page rend deux fois « M1a rows · 279 ». Ce n'est **pas** une somme — les deux nombres ne
   sont jamais additionnés, et `build_observatory.py:200-206` documente explicitement que 21
   identifiants portent plusieurs tentatives (0853). Mais un lecteur voit le même 279 deux fois
   sur deux lignes voisines. 22 lignes sur 314 sont dans ce cas (292 identifiants distincts).
   Résidu de lisibilité ; aucun critère enfreint. `shots/PROBE-Q1-rmp-two-rows.png`.

Rien dans cette liste ne remet en cause la fermeture d'un enfant.

---

## 7. Ligne de journal proposée et cases recommandées

Ligne à ajouter au journal de `tickets/0834-m1a-mvp-trois-etages.erg` (ajout seul, jamais de
réécriture sur place) :

```
2026-09-22T12:00Z HDMX-coding-agent note revue d'integration finale sur main (bf31b3ee), verdict NE PAS FERMER pour un seul motif. Les trois prises du 2026-09-22 00:05 sont reparees et verifiees a l'ecran : ZAF.json 509 315 octets sous le plafond de 512 000 (0855) ; page Documents un depliage par produit, « Ledger rows · 257 » et « M1a rows · 257 », aucune occurrence de 514, idem IDN 113/1142 et SEN 67/38 et 82/11 (0856) ; le RMP 2023 s'ouvre en un clic a la page imprimee 139 depuis le registre des documents, ancre …b145af2e….pdf#page=155, et chaque position mene a sa propre ligne via #inventory/VNM?row=N (0857) ; documents.json une clef, 314 lignes, 155 720 octets, remontee document -> faits en jointure a la lecture (0858) ; observations/VNM.json 7 lignes sans empreinte nulle, 7/7 ouvrent leur document local en HTTP 200 depuis les trois fiches projet (0854). Recettes ZAF et VNM vertes de bout en bout, telles qu'ecrites ; tests/browser/jetp_observatory.py vert 3 fois sur 3, l'echec intermittent du lien d'evitement sur #country/IDN ne s'est pas reproduit. Criteres 3 et 4 coches. Garde de 0856 verifie par mutation : retablir le rendu d'avant 0856 sur une copie du site fait tomber trois tests de rendu avec {'mixed': '514'} contre {'ledger': '257', 'm1a': '257'}. .githooks/pre-commit identique a origin/main, plafond 512 000 intact, le commit dee039ea de 0854 bien abandonne au rebase. make check complet : 3 failed, 3100 passed, 57 skipped — deux echecs environnementaux (data/jetp/crs absent du clone entier, commit 3b432ef3 absent, controle positif sur bf31b3ee a exit 0) et une regression du train, test_jetp_vnm_positions.py:168 qui epingle 227 legacy_dispositions la ou il y en a 234 : les sept lignes manifest.csv 309-315 ajoutees par 43b6fc4d (0854), classees acquisition_history. Les huit autres epinglages du test sont verifies inchanges ; la reparation est d'une ligne. Tracker maintenu ouvert sur ce seul point, plus la ligne M1a de [[0725]] et [[0715]] qui appartient a l'auteur. Rapport complet : docs/jetp-study/0834-integration-review-final-2026-09-22.md.
```

Cases recommandées dans `## Exit criteria` :

```
- [x] Les cinq enfants sont fermés
- [x] La recette Afrique du Sud passe de bout en bout dans le navigateur
- [x] La recette Vietnam passe de bout en bout dans le navigateur
- [x] Aucun étage n'agrège ni ne fusionne les lignes d'un autre
- [ ] La ligne M1a de [[0725]] et de [[0715]] est cochée par l'auteur après revue d'intégration
```

Les deux cases nouvellement cochées le sont chacune sur une preuve à l'écran et une preuve dans le
code, listées au §3 et au §5. La cinquième reste vide parce qu'elle appartient à l'auteur, et
cette revue lui recommande de la cocher **une fois l'épinglage 227 → 234 réparé** — pas avant,
non parce que le défaut touche M1a, mais parce qu'on ne fait pas signer une acceptation pendant
que la suite est rouge d'une régression née dans le train qu'on fait accepter.

La première case reste cochée. Rien dans ce rapport ne remet en cause la fermeture d'un enfant :
le point 0 du §6 ouvre un ticket de réparation, il ne rouvre pas 0854.

---

### Artefacts

Tous dans
`/tmp/claude-1001/-home-haduong-CNRS-projets-actifs-climate-finance-het/a12625da-f40d-43cd-8b7d-fd6f422a6920/scratchpad/` :

- `recipe_walk.py` — la marche indépendante des deux recettes, et `walk.log` son journal
- `probe.py` — les trois questions ouvertes (doublons de registre, sources de Bac Ai, source citée sans extraction)
- `why234.py` — le contrôle positif qui nomme les sept dispositions ajoutées
- `pins.py` — les neuf épinglages du test lent recalculés
- `mutant/`, `mutant_render_test.py` — la mutation qui prouve les dents du garde de 0856
- `make-check.log`, `browser-run1.log`, `server.log`
- `shots/` — 36 captures : `SA1-*`, `SA2-*`, `SA3-*`, `VN1-*`, `VN2a/b/c/d-*`, `VN3-*`, `VN3c-*`, `VN4-*`, `C4-*`, `PROBE-Q1/Q2/Q3-*`, `BROWSER-run1/2/3`
