# Revue d'intégration — tracker 0834 « M1a : le MVP explore les données en trois étages »

Revue adversariale menée en lecture seule sur `main` (HEAD `3231d3e0`), dans le
worktree `/home/haduong/CNRS/projets/actifs/climate-finance-het/.claude/worktrees/agent-a1bfd530a8cb85d44`.
Rien n'a été committé, poussé, ni écrit dans le dépôt principal.

Aperçu servi par `python3 -m http.server 8791 --directory deliverables/jetp-observatory`,
sur les artefacts **committés** de `main` — pas sur une reconstruction locale, afin
que la recette juge ce qui a effectivement fusionné.

---

## 1. Verdict — **NE PAS FERMER**

Les cinq enfants sont bien fermés et la recette Afrique du Sud passe de bout en
bout. Trois choses s'y opposent néanmoins, dont deux sérieuses.

**D'abord, `main` est rouge, et c'est le train qui l'a cassé.** `make check`
complet donne `3 failed, 3092 passed, 57 skipped` ; deux échecs sont
environnementaux et prouvés tels par l'entrée qui leur manque, mais le troisième —
`test_zaf_candidate_reconciles_inventory_legacy_and_current_views` — est une
régression attribuable à la PR #1436 (ticket 0839) : la vue MVP `ZAF.json` pesait
509 315 octets avant le train, soit 2 685 octets sous le plafond de publication de
512 000, et pèse 792 434 octets depuis `3231d3e0`. Le plafond qu'elle franchit
garde le déploiement public suivi par 0727. Personne ne l'a vu : pas de CI, et le
palier lent n'est passé qu'*ex post*. §4.

**Ensuite, le quatrième critère de sortie** — « Aucun étage n'agrège ni ne fusionne
les lignes d'un autre » — **échoue sur un nombre visible par le lecteur** : la page
Documents affiche « Extracted here · 514 » pour le registre JET sud-africain, soit
257 observations du ledger **plus** 257 lignes M1a qui sont *les mêmes 257 lignes
de registre lues sous deux schémas*. La première entrée de chaque moitié porte le
même identifiant source (`Unique ID ACTIP001`), la dernière de chaque moitié porte
`IDC003` : le compte double la population qu'il prétend décrire. L'application
elle-même écrit la règle violée, une page plus loin (`app.js:525`) : « They are read
separately and **never added together**: one ledger row and one inventory row can
describe the same paragraph of the same file. » Le défaut est petit et local — un
compte de `<summary>`, pas une fusion de données — mais il porte précisément sur
l'invariant que le tracker fait signer à l'auteur, et il atteint un livrable.

**Enfin**, un pas de la recette Vietnam ne passe pas tel qu'il est écrit : depuis le
registre des documents, le RMP 2023 ne s'ouvre pas à la page imprimée 139 — l'ancre
ne porte aucun fragment `#page=` et les 279 positions du dépliage pointent toutes
vers `#inventory/VNM` non filtré (VN1, §3).

Ce qui a été livré est solide : la descente et la remontée fonctionnent, la
séparation des deux produits d'étage 2 est écrite sur la page, et le côte-à-côte
vietnamien est un modèle de non-fusion. Mais on ne ferme pas un tracker dont le
critère de non-fusion est enfreint à l'écran pendant que la suite est rouge d'une
régression née dans son propre train. Je recommande : réparer le plafond ZAF,
corriger V1, trancher VN1 — puis rouvrir la revue, qui sera courte.

---

## 2. Critères de sortie de 0834

| # | Critère | Verdict | Preuve |
|---|---|---|---|
| 1 | Les cinq enfants sont fermés | **atteint** | `tickets/closed/0835…0839`, chacun avec `Closed:` non vide en ligne 5 (`autoclosed — PR #1429/#1432/#1430/#1433/#1436`). 0853, né de la revue de 0835, est fermé aussi (PR #1435). |
| 2 | La recette Afrique du Sud passe de bout en bout dans le navigateur | **atteint** | SA1/SA2/SA3 tous PASS — §3. Empreinte du snapshot servie == empreinte du registre ; 88 lignes « D. Completed » sur 257 ; descente projet → ligne de ledger → snapshot vérifiée par popup. |
| 3 | La recette Vietnam passe de bout en bout dans le navigateur | **non atteint pour VN1 ; VN3 atteint sous la lecture restreinte ; VN2 et VN4 atteints** | §3. VN1 : la page Documents n'offre aucun lien ouvrant le RMP à la page imprimée 139. |
| 4 | Aucun étage n'agrège ni ne fusionne les lignes d'un autre | **non atteint** | V1 : `Extracted here · 514` (`app.js:334-335`, données `build_observatory.py:271` + `:278`). V2, mineur : totaux M1a inter-sous-couches contredits par la note adjacente. §5. |
| 5 | La ligne M1a de 0725 et 0715 cochée par l'auteur après revue d'intégration | **non atteint, par dessin** | C'est l'objet de la présente revue ; elle conclut à ne pas cocher ce soir. |

---

## 3. Parcours des recettes, pas à pas

Marche indépendante (`scratchpad/recipe_walk.py`), qui **ne réutilise aucune
assertion** de `tests/browser/jetp_observatory.py` : chaque valeur est redérivée du
JSON servi et relue dans le DOM.

### Afrique du Sud

| Pas | Énoncé du ticket | Verdict | Observation |
|---|---|---|---|
| SA1 | Ouvrir le snapshot HTML archivé du registre depuis le registre des documents | **PASS** | `a[data-document-id="zaf-jet-investment-register-q1-2026:1"]` → `documents/objects/5b/5b5d…f4.html`, popup ouverte à cette URL ; SHA-256 des octets servis == `sha256` du registre. `SA1-documents-register-row.png`, `SA1-snapshot-opened.png` |
| SA2 | Filtrer l'inventaire M1a ZAF sur « D. Completed » → 88 lignes, chacune avec ses 21 champs source | **PASS** | Ligne de compte : `88 of 257 source rows · page 1 of 2`. 21 colonnes `raw_*` dans la charge utile **et** 21 clés `raw_*` dans le dépliage d'une ligne (32 champs au total = 11 + 21). `SA2-inventory-zaf-completed.png` |
| SA3 | Depuis un projet de la vue pays, descendre à sa ligne de registre puis au snapshot | **PASS** | `#project/zaf-register-actip001` → dépliage `data-evidence-count="1"` → lien `documents/objects/5b/…html`, popup ouverte à cette URL. `SA3a-country-zaf.png`, `SA3b-project-evidence-foldout.png` |

*Réconciliation d'un écart apparent* : le ticket dit « 258 enregistrements », le
livrable en sert 257. Ce n'est pas un défaut — c'est l'inverse. La 258ᵉ entrée est
la ligne d'agrégat du tableau de bord lui-même (`Unique ID = 248`, un `int` et non
un `str`, `Project Name` et `Portfolios` à `None`, `Total US$ 3 953 240 805,08`),
exclue délibérément et documentée en toutes lettres :
`docs/jetp-study/0818-zaf-q1-2026-report.md:26-30` et
`manifest.json → countries.ZAF.sublayers[0].excluded_source_rows`. Le pipeline
refuse d'admettre un total dans un jeu de lignes : exactement la discipline que le
critère 4 demande.

### Vietnam

| Pas | Énoncé du ticket | Verdict | Observation |
|---|---|---|---|
| VN1 | Ouvrir le PDF du RMP 2023 à la page imprimée 139 **depuis le registre des documents** | **non atteint tel qu'écrit** | Le lien « Open archived copy » porte `documents/objects/b1/b145…3c.pdf`, **sans fragment `#page=`** : il ouvre à la page 1. Le dépliage « Extracted here · 279 » liste bien les 279 positions avec leur localisateur en clair (« Annex I.1; PDF pages 155; printed pages 139; ordinal 1 »), mais **les 279 ancres pointent toutes vers `#inventory/VNM`**, non filtré et sans cible de ligne : on atterrit sur 279 lignes et il faut re-chercher. La page 139 n'est atteignable que (a) en éditant l'URL à la main pour y ajouter `#page=155`, ce que 0835 ligne 243 décrit précisément comme la vérification attendue, ou (b) par l'inventaire, où l'ordinal 1 porte bien `…pdf#page=155`. `VN1-documents-rmp-extracted.png`, `VN1b-inventory-printed-139.png` |
| VN2 | Filtrer l'inventaire M1a VNM sur l'annexe I.1 → 37 lignes ; la ligne 22 (KN Tri An Floating Solar Farm) ouvre le PDF à sa page | **PASS** | `37 of 279 source rows`, 37 lignes dans le DOM. Ligne 22 : libellé « 22 KN Tri An Floating Solar Farm Dong Nai 928 MW 2030 Decision No. 500/QD-TTg PDP8 », localisateur « Annex I.1; PDF pages 156; printed pages 140; ordinal 22 », `href = …pdf#page=156`, popup ouverte. `VN2a-inventory-vnm-annex-I1.png`, `VN2b-inventory-vnm-tri-an.png` |
| VN3 | Depuis Bac Ai dans la vue pays, remonter à ses quatre sources et ouvrir le bulletin 5 du MOIT (juillet 2025) | **passe sous la lecture restreinte VN** | La remontée fonctionne et elle est honnête : 6 cartes source (et non quatre — voir ci-dessous), chacune avec éditeur, URL et statut de collecte affiché (« Not collected » pour cinq, « collected · Retrieved 2026-09-12 » pour le bulletin). Le bulletin 5 ouvre bien l'archive locale : `a[data-archived-source="vnm-moit-newsletter-05-2025-07"]` → `documents/objects/a4/a4bb…39.pdf`, popup ouverte. Le dépliage des 3 observations du ledger affiche « No archived copy of this source » pour chacune (0 lien de descente), ce qui est la lecture restreinte, écrite sur la page et non tue. `VN3b-project-bac-ai.png`, `VN3c-bac-ai-sources-expanded.png` |
| VN4 | Constater la table initiale et les 24 enregistrements de 2025 côte à côte, sans lien fabriqué | **PASS** | `#vnm-side-by-side` : panneau gauche « RMP 2023 initial table — 279 positions listed in the annexes… », panneau droit « 2025 portfolio — 24 records: 3 named and 21 unpublished identities », et la phrase « No link between the 2023 table and the 2025 portfolio ». Aucun champ ne joint les deux objets. C'est le meilleur endroit du site sur la non-fusion. `VN4-vnm-side-by-side.png` |
| — | *Critère d'acceptation, la remontée depuis un document* | **PASS** | `vnm-rmp-2023` : `data-extracted-count="279"`, 279 `<li>` réellement rendus, `data-facts-count="0"`, et l'index confirme `facts == []`. `CLIMB-rmp-279-positions.png` |

**Vérification indépendante du localisateur, hors navigateur.** `pdftotext` sur
l'archive locale : la page PDF 155 porte les ordinaux 1 à 17 de l'annexe I
(« Long Tao Hydropower plan », « Yen Son Hydropower plan », …) et la page PDF 156
porte l'ordinal 22, « KN Tri An Floating Solar Farm », Dong Nai. Le mapping
imprimée 139 → PDF 155 et imprimée 140 → PDF 156 est donc exact dans les données :
le défaut de VN1 est de navigation, pas d'extraction.

**Deux écarts de prose du ticket, sans conséquence sur le code.** Le tracker écrit
« ses quatre sources » ; Bac Ai en porte six
(`vnm-eeas-jetp-project-progress-2025`, `vnm-eib-bac-ai-package-2025`,
`vnm-evn-cdp-bac-ai-2025`, `vnm-moit-newsletter-05-2025-07`,
`vnm-moit-project-bac-ai`, `vnm-moit-project-index-2026`), dont **une seule** figure
au registre des documents avec une empreinte. C'est la fiche qui est périmée, pas
la livraison — l'écart est consigné au journal de 0839 (`2026-09-21T22:10Z`).

**Exécution de la recette livrée.** `tests/browser/jetp_observatory.py` échoue bien
sur `main` comme annoncé, au plafond de téléchargements automatiques de Chromium :
`TimeoutError: Timeout 30000ms exceeded while waiting for event "download"` à
`download_matches(page, url, f'data/m1a/{code}.csv')` — le 9ᵉ appel de
`expect_download` de la session, après `comparison.json` et les sept vues. C'est le
défaut que le ticket 0852 traite. Relancées **une par une, chacune dans un contexte
navigateur neuf** (`scratchpad/run_checks.py`), les cinq fonctions passent :
`check_projects`, `check_documents`, `check_inventory`, `check_observations`,
`check_facts` — toutes PASS, zéro `pageerror`, zéro requête externe.

---

## 4. Classement des échecs de `make check`

`make check` complet (palier lent inclus), lancé dans ce worktree après avoir
rendu les artefacts de corpus disponibles par lien symbolique depuis le dépôt
principal (le préflux `scripts/qa_full_gate_preflight.py` refusait autrement de
démarrer : `catalogs/*` et `llm_relevance_cache.csv` absents du worktree). Rien
n'a été écrit dans le dépôt principal — `data/derived` et `data/exports` ont été
**copiés**, pas liés, précisément parce que des tests y écrivent.

**Résultat : `3 failed, 3092 passed, 57 skipped` en 583,76 s.**

| Test en échec | Classement | Preuve, par l'entrée manquante nommée |
|---|---|---|
| `tests/test_jetp_courbe_reference.py::test_chaine_portee_reproduit_la_reference` | **environnemental** | Le test nomme lui-même son entrée : `data/jetp/crs` absent, « lancer `dvc pull data/jetp/crs` avant ce test ». Le répertoire est **également absent du dépôt principal** (`ls /home/haduong/…/climate-finance-het/data/jetp/crs` → no such file) : artefact DVC jamais matérialisé sur cette machine. Aucun fichier du train ne le touche. |
| `tests/test_jetp_public_release.py::test_reviewed_evidence_records_are_distinct_non_aggregate_and_traceable` | **environnemental** | Entrée manquante : le commit `3b432ef322ed9a1bb099089b24b793f6d791842a`. `_public_release.py:180` fait `git cat-file -e 3b432ef3…^{commit}` → exit 128, « Not a valid object name ». Contrôle : la **même** commande échoue à l'identique dans le dépôt principal. C'est l'échec environnemental déjà connu, et le corps de la PR #1435 le documentait avec son propre contrôle négatif. |
| `tests/test_jetp_zaf_migration.py::test_zaf_candidate_reconciles_inventory_legacy_and_current_views` | **CAUSÉ PAR LE TRAIN** | Voir ci-dessous. Aucune entrée ne manque. |

### L'échec 3 est une régression du train, et elle est attribuable à une PR

`ValueError: Public payload needs compatible chunking before publication`, levée
par `scripts/jetp/build_zaf_positions.py:186-188`, qui refuse toute vue MVP dont
la charge utile publiée dépasse `publication_limit_bytes` —
**512 000 octets**, `config/jetp-zaf-migration.json:189`. Les vues contrôlées sont
`MVP_VIEWS = {overview, comparison, ZAF, IDN, VNM, SEN}`
(`scripts/jetp/_compatibility.py:18`) ; `documents` n'en fait pas partie, donc une
seule vue est en cause : **ZAF**.

Taille de `deliverables/jetp-observatory/data/ZAF.json`, relevée commit par commit
sur le premier parent de `main` :

| Commit | PR | ZAF.json |
|---|---|---|
| `f4673570` | avant le train | **509 315** o — 2 685 o **sous** le plafond |
| `4f9ad63f` | #1433 (0838) | 509 315 o |
| `3d442189` | #1435 (0853) | 509 315 o |
| `3231d3e0` | **#1436 (0839)** | **792 434 o** — 280 434 o **au-dessus** |

Le saut tombe exactement sur la dernière fusion du train, celle de 0839, qui ajoute
la clé `evidence` à chaque projet de la vue pays (283 119 octets pour 338
observations ZAF, ≈ 838 o par ligne). Le plafond n'avait que 0,5 % de marge avant
le train ; la dernière PR l'a franchi.

Ce n'est pas un détail de test : le plafond garde la **publication**, c'est-à-dire
exactement le déploiement public suivi par [[0727]]. `main` est rouge sur ce point
depuis `3231d3e0`, et rien ne l'a signalé — le dépôt n'a pas de CI (décision 0321)
et le palier lent n'est vérifié qu'*ex post*, à l'étape 9 de `/lair`. Cette revue
est le premier passage complet depuis la fin du train.

*Note de méthode* : le second échec environnemental attendu — le décalage
d'empreinte DVC sur `data/jetp/releases/vnm-migration-0764.json` — ne s'est pas
manifesté, parce que j'ai lié le fichier matérialisé depuis le dépôt principal
avant de lancer la suite. Il n'est donc ni infirmé ni confirmé ici.

---

## 5. Audit de fusion inter-étages (critère 4)

**Au niveau des étages : aucune fusion.** Les liens 1 → 2 → 3 sont partout de la
provenance pure (`source_id`, `sha256`, localisateur, `project_id` stocké). Rien ne
somme de montants, rien n'apparie d'identités, aucun ensemble d'étage 2 n'est
fusionné dans un ensemble d'étage 3 — le report de M1b vers 0833 est intact.
`scripts/jetp/build_observations.py`, `scripts/jetp/_m1a_document_links.py` et
`scripts/jetp/_observatory_data.py` sont propres de bout en bout : filtres,
partitions et transformations ligne à ligne, avec des `raise` là où d'autres
auraient laissé passer un vide silencieux.

**Au niveau des sous-couches : deux totaux affichés en faute.** Le critère interdit
l'agrégation « entre sous-couches » autant qu'entre étages.

### V1 — bloquant : la page Documents additionne les deux produits d'étage 2

`scripts/jetp/build_observatory.py:271` et `:278` empilent les références du ledger
et les références M1a **dans la même liste** `extracted` (chaque élément garde son
discriminant `product`, donc la donnée reste séparée — le build est défendable).
Mais `deliverables/jetp-observatory/app.js:334-335` rend cette liste par
`foldout(...)`, dont le résumé est `items.length` : un seul nombre pour deux
populations. Appelé en `app.js:342` sous le libellé « Extracted here ».

Quatre sources ont une liste `extracted` mixte dans `data/documents.json` livré :

| source | ledger | m1a | affiché |
|---|---|---|---|
| `zaf-jet-investment-register-q1-2026` | 257 | 257 | **514** |
| `idn-jetp-progress-report-2025` | 113 | 1 142 | **1 255** |
| `sen-investment-plan-annexes-mirror` | 67 | 38 | **105** |
| `sen-investment-plan-l4-mirror` | 82 | 11 | **93** |

Le cas ZAF est la preuve : relevé dans le DOM, `li[1]` est « Financial event
zaf-register-actip001 … Overall - Data, **Unique ID ACTIP001** » et `li[258]` est
« 1 Skills Research Programme … Overall - Data, **Unique ID ACTIP001** » ; `li[257]`
et `li[514]` portent tous deux `IDC003`. Les deux moitiés sont la même table de 257
lignes, lue deux fois. Capture : `FUSION-V1-zaf-extracted-514.png`.

Le test censé garder cet invariant a l'angle mort exact :
`tests/test_jetp_observatory_facts.py::test_extracted_lists_hold_the_ledger_row_and_the_m1a_row_separately`
vérifie que **la donnée** garde les deux produits distincts (`products == [("ledger", …), ("m1a", …)]`)
et son commentaire « Two lists per source, never a total across them » vise la paire
`extracted` / `facts` — pas le contenu de `extracted`. Rien ne teste le compte rendu
à l'écran. `README.md:76` reprend la formule « two lists, never a total », vraie de
la paire et fausse du premier membre.

*Réparation la moins chère* : scinder le dépliage en « Ledger rows · N » et
« M1a rows · M », ou supprimer le compte du résumé quand la liste porte plus d'un
`product`.

### V2 — mineur : totaux M1a inter-sous-couches, contredits par la note adjacente

`scripts/jetp/build_m1a_inventories.py:228` publie un `row_count` par pays à travers
ses sous-couches (IDN 1 579 = 437 + 1 142 ; SEN 49 = 38 + 11) et `:231-233` fait un
`sum()` explicite des inconnus à travers les sous-couches (IDN `field_values` 7 522
= 1 728 + 5 794). Rendus à l'écran en `app.js:232` (ligne de compte de l'inventaire,
relevée : `1579 of 1579 source rows · page 1 of 32`) et `app.js:923` (tableau de la
page Methods).

Trente pixels au-dessus de cette ligne de compte, `app.js:448` imprime : « Each
figure counts one extraction sub-layer of this country. **This page adds none of
them together**: the sub-layers overlap, count different things, and a country is
not the unit any of them measures. » Relevé dans le même DOM que le `1579 of 1579`.
`README.md:48-50` fait la même affirmation. Capture :
`FUSION-V2-idn-inventory-total.png`.

Atténuation réelle : les ensembles de lignes *sont* disjoints (437 + 1 142 = 1 579
sans recouvrement de lignes), donc le nombre est une propriété vraie de l'export
livré. Aggravation : la note dit que les sous-couches « se recouvrent », ce qui est
précisément la raison de ne pas montrer leur somme comme une population. Réparation
honnête, au choix de l'auteur : reformuler la note, ou nommer le nombre « rows in
this export » plutôt qu'une population.

### Le contre-modèle, dans le même code

`app.js:130-133` (`vietnamSideBySide`) met 279 positions d'étage 2 à côté de 24
enregistrements d'étage 3, dans deux panneaux, sans aucun champ qui les joigne, et
écrit la non-relation. C'est la forme dans laquelle V1 et V2 devraient être
ramenés. Capture : `FUSION-control-vnm-sidebyside.png`.

---

## 6. Résidu — pour la suite

**Au-dessus du plancher de sévérité (mérite un ticket) :**

0. **Le plafond de publication ZAF franchi par 0839** (§4). Bloque la publication,
   fait échouer la suite sur `main`, et relève de la voie science : un ticket, tout
   de suite, enfant de 0834 et bloquant pour 0727. Deux réparations possibles, au
   choix de l'auteur : relever `publication_limit_bytes` si le plafond de 512 ko
   est arbitraire, ou — plus conforme à l'intention du garde — servir `evidence`
   depuis les vues `observations/<CODE>.json` déjà livrées au lieu de le recopier
   dans la vue pays, puisque `test_a_fact_carries_its_evidence_rows_verbatim_and_in_order`
   établit que ce sont les mêmes lignes, mot pour mot. La seconde option supprime
   283 119 octets de duplication et rapproche l'étage 3 de la discipline de
   provenance que le reste du train applique.
1. **V1**, ci-dessus. Valeur fausse visible dans un livrable, sur l'invariant même
   que le tracker fait signer. Un ticket, enfant de 0834, bloquant pour le
   critère 4.
2. **VN1** : décision d'auteur requise. Soit une réparation bon marché — poser
   `#page=` sur l'ancre « Open archived copy » quand les lignes extraites s'accordent
   sur une page, ou faire pointer chaque `<li>` du dépliage vers *sa* ligne
   d'inventaire plutôt que vers `#inventory/VNM` non filtré — soit une reformulation
   du pas de recette. Je recommande la seconde ancre (`<li>` → ligne), qui répare
   aussi la remontée : aujourd'hui elle dépose le lecteur sur 279 lignes non
   filtrées.

**Sous le plancher (liste pour le wrap-up, pas de ticket) :**

3. **Les 21 lignes d'observation sans empreinte hors périmètre 0854.** Sur 766
   observations servies, 28 n'ont pas de `sha256` : 7 pour le Vietnam (couvertes par
   0854) et **21 autres — ZAF 2, IDN 8, SEN 11 — dont la source figure au registre
   mais dont aucune tentative n'a relevé d'empreinte**. Elles sont épinglées par
   `tests/test_jetp_observatory_observations.py::test_a_row_without_a_fingerprint_is_one_of_two_named_collection_gaps`,
   donc surveillées, mais rien ne planifie leur collecte. À signaler à l'auteur.
4. **« 1 740 » contre « 766 ».** Le tracker décrit l'étage 2 comme « les observations
   atomiques du ledger (1 740, marquées "not deployed") ». Les vues livrées en
   servent **766** (ZAF 338, IDN 158, VNM 7, SEN 263), tandis que la page Editions
   affiche toujours « 1 740 staged observations » depuis
   `reviewed-evidence.json → evidence_depth.structured_atomic_observations`
   (`status: not_deployed`, répartition tout autre : IDN 1 148, SEN 10, VNM 325,
   ZAF 257). Deux populations distinctes et correctement étiquetées, mais un lecteur
   passant d'une page à l'autre voit deux nombres pour « observations atomiques »
   sans réconciliation. Une phrase suffirait.
5. **Résidu de vocabulaire « layer »** — résidu, pas bloquant, comme demandé.
   Visible par l'utilisateur : `app.js:887` « These are distinct **layers**. They are
   not a common record total. » (le seul endroit où le modèle à trois étages est
   expliqué au lecteur, et il dit « layers ») ; `app.js:935` « Implementation
   observations are a separate **layer** » ; `data/SEN.json`, note de projet, « no sum
   across status **layers** » (troisième sens du mot). Prose de documentation :
   `STATE.md:17` « 2,164 rows, **six layers** » — la ligne de statut canonique de
   0834 ; `docs/jetp-backend-design.md:38,45` ; `docs/jetp-tracking.md:3,7,25,175,184`.
   Identifiants internes (`source_layer`, `FrozenLayer`, `layer_id`) : à laisser, sauf
   que `app.js:453-461` imprime les clés brutes dans le dépliage d'une ligne, donc
   `source_layer` fuit à l'écran — cosmétique.
6. **`countStages` (`app.js:44-48`) est du code mort** — un agrégateur défini et jamais
   appelé. À supprimer.
7. **Nommage « sources ».** Le mot désigne quatre nombres dans l'interface livrée :
   307 tentatives de collecte (page Documents), 285 identifiants distincts, 301 lignes
   de `sources.csv` (tuile d'accueil et page Methods), 301 `frozen_source_documents`.
   Tous d'étage 1, donc aucun critère enfreint, mais 301 et 307 se présentent au
   lecteur comme la même chose. Appeler « collection attempts » ce que la page
   Documents compte lèverait l'ambiguïté.
8. **Risque latent, `build_m1a_inventories.py:216-217`** : l'en-tête CSV est pris sur
   la forme de la *première* sous-couche. Inerte aujourd'hui (seul ZAF émet des
   colonnes `raw_`, et il n'a qu'une sous-couche) ; une seconde sous-couche à
   colonnes différentes sur un pays existant blanchirait silencieusement les
   colonnes manquantes. Une assertion, pas un ticket.
9. **La recette navigateur n'est pas collectée par pytest** (docstring
   `tests/browser/jetp_observatory.py:3`). Les cases « recette navigateur » des quatre
   fiches reposent sur des exécutions manuelles, et jusqu'à ce soir aucune n'avait été
   passée d'un seul tenant. Le présent rapport est la première vérification
   fonction-par-fonction complète sur `main`.

---

## 7. Ligne de journal proposée et cases recommandées

Ligne à ajouter au journal de `tickets/0834-m1a-mvp-trois-etages.erg` :

```
2026-09-22T00:00Z HDMX-coding-agent note revue d'integration sur main (3231d3e0), verdict NE PAS FERMER. Recette ZAF verte de bout en bout ; recette VNM verte sauf VN1 (depuis le registre des documents le RMP 2023 n'ouvre pas a la page imprimee 139 : ancre sans fragment #page=, et les 279 positions du depliage pointent toutes vers #inventory/VNM non filtre) ; VN3 vert sous la lecture restreinte de 0838 (Bac Ai porte six sources et non quatre, une seule archivee). Critere 4 en echec : la page Documents affiche « Extracted here · 514 » pour le registre JET ZAF, soit 257 lignes de ledger + les 257 memes lignes M1a (app.js:334-335, donnees build_observatory.py:271 et :278), ce que app.js:525 interdit explicitement ; meme defaut sur IDN 1255, SEN 105 et 93. make check complet : 3 failed, 3092 passed, 57 skipped — deux echecs environnementaux (data/jetp/crs absent, commit 3b432ef3 absent du clone, l'un et l'autre reproduits dans le depot principal) et un echec cause par le train, test_zaf_candidate_reconciles_inventory_legacy_and_current_views : la vue MVP ZAF.json passe de 509 315 o (avant le train et jusqu'a 3d442189) a 792 434 o en 3231d3e0, au-dessus du plafond de publication de 512 000 o (config/jetp-zaf-migration.json:189), par l'ajout de la cle evidence en 0839. Tracker maintenu ouvert ; plafond ZAF, V1 et VN1 a traiter avant de cocher la ligne M1a de 0725 et 0715.
```

Cases recommandées dans `## Exit criteria` :

```
- [x] Les cinq enfants sont fermés
- [x] La recette Afrique du Sud passe de bout en bout dans le navigateur
- [ ] La recette Vietnam passe de bout en bout dans le navigateur
- [ ] Aucun étage n'agrège ni ne fusionne les lignes d'un autre
- [ ] La ligne M1a de [[0725]] et de [[0715]] est cochée par l'auteur après revue d'intégration
```

Les trois cases laissées vides le sont pour une raison chacune : VN1 non atteint tel
qu'écrit, V1 en faute sur le critère 4, et la cinquième appartient à l'auteur — que
cette revue invite à ne pas cocher ce soir.

La première case reste cochée : les cinq enfants *sont* fermés, et le plafond ZAF
franchi par 0839 ne rouvre pas 0839 — il ouvre un ticket de réparation. Rien dans
ce rapport ne remet en cause la fermeture d'un enfant ; tout porte sur ce que
l'intégration révèle et qu'aucune PR prise isolément ne pouvait voir. C'est le
travail que la revue d'intégration existe pour faire, et il a rendu trois prises :
une régression de publication, une fusion affichée, un pas de recette qui ne passe
pas. Le tracker reste ouvert, ce qui est la bonne issue.

---

### Artefacts

Scripts de la revue et captures, tous dans
`/tmp/claude-1001/-home-haduong-CNRS-projets-actifs-climate-finance-het/a12625da-f40d-43cd-8b7d-fd6f422a6920/scratchpad/` :
`recipe_walk.py`, `run_checks.py`, `fusion_check.py`, `probe.py`, `probe2.py`,
`ground_truth.py`, `ground_truth2.py`, `make-check.log`, et les captures
`SA1-*`, `SA2-*`, `SA3a/b-*`, `VN1-*`, `VN1b-*`, `VN2a/b-*`, `VN3a/b/c-*`, `VN4-*`,
`CLIMB-*`, `FUSION-V1-*`, `FUSION-V2-*`, `FUSION-control-*`, `check-check_*.png`.
