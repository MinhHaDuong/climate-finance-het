<!-- Atterri depuis ~/CNRS/projets/actifs/jetp/papier-3-ledger/imagine-jetp-ledger-2026-08-10.md (ticket 0712, 2026-09-11).
     Contenu inchangé par rapport à la source, hors ce bandeau.
     Matériau de conception pour les papiers JETP (tracker 0708) —
     pas encore câblé dans un livrable. -->
# Imagine — le registre comptable JETP comme campagne AEDIST (10 août 2026)

Note d'imagination en réponse à trois questions : garde-t-on l'idée de
publication après la passe de saturation ? comment utiliser AEDIST pour
télécharger la documentation officielle des quatre JETP et refaire la
comptabilité nous-mêmes ? comment articuler avec le corpus finance climat
(>30 000 réf., climate-finance-het) et avec le suivi automatique de la
transition énergétique (north star d'AEDIST) ?

## 1. Garde-t-on l'idée ? Oui — et la comptabilité primaire la renforce

La saturation du 10 août laisse les trois créneaux libres en peer-review.
Elle montre aussi que la concurrence arrive par preprints (Do/Burke/Jotzo
le 29 juillet, Kawiriaan & Zan « In Review ») et que toute la littérature
existante, y compris ces concurrents, travaille sur sources secondaires :
la note de conseil elle-même avoue (§8) que « les chiffres de décaissement
divergent selon les sources et les périmètres — toute version soumise devra
retourner aux sources primaires ».

Refaire la comptabilité depuis les documents primaires est précisément la
contribution que personne n'a : un registre financier JETP auditable, où
chaque cellule cite le document officiel qui la fonde. Cela transforme la
faiblesse anticipée de l'option C (« policy chronicle », dixit l'éditeur
simulé d'INEA) en colonne vertébrale empirique, et répond frontalement au
rejet ESD de 2024 (« more work is needed to substantiate the
conclusions »). L'idée est non seulement gardée : elle monte en gamme.

## 2. Le « JETP ledger » — une campagne AEDIST sur documents financiers

AEDIST n'est pas un crawler : c'est une méthode d'extraction outillée
(régimes d'information, fusion incrémentale, vérification) validée par
benchmark sur l'inventaire des centrales vietnamiennes. La campagne JETP
réutilise l'architecture telle quelle en changeant l'objet : la ligne du
master n'est plus une centrale, c'est un engagement financier.

### 2.1 Recensement de l'univers documentaire (phase harvest, hors AEDIST)

Le téléchargement est la partie facile — scripts de collecte, pas d'IA.
L'univers par pays :

- **Textes fondateurs** : 4 déclarations politiques ; plans
  d'investissement (JET-IP Afrique du Sud, CIPP Indonésie, RMP Vietnam,
  plan sénégalais quand il paraît).
- **Suivi officiel** : leaders' updates annuels IPG ; rapports annuels des
  secrétariats (JETP-SA, secrétariat indonésien puis JETP Delivery Unit,
  secrétariat vietnamien) ; listes de projets approuvés (les 17 projets
  vietnamiens de juillet 2025, le pipeline sud-africain…).
- **Documents bailleurs, projet par projet** : pages projet et notes
  d'approbation AFD, KfW, BEI, ADB, Banque mondiale, JICA, DFC, BII… —
  chaque opération a une fiche publique avec montants, instrument, dates.
- **Opérateurs** : rapports annuels Eskom, PLN, EVN, Senelec (fermetures,
  mises en service, investissements).

Deux colonnes vertébrales **déjà structurées** évitent d'extraire par IA ce
qu'une API donne : **IATI** (flux d'aide déclarés en XML, par activité) et
**OECD CRS** (notifications par ligne, avec équivalent-don). Le registre se
construit en trois couches : CRS/IATI (structuré) → tables des documents
officiels (extraction sérielle) → prose des rapports et communiqués
(extraction scalaire). L'IA ne travaille que sur les deux dernières.

Archivage selon la discipline existante : pool documentaire versionné en
DVC (le motif data/pool de climate-finance-het), provenance complète (URL,
date de collecte, checksum), rapports catalogués dans Zotero avec
`numPages` (règle EDM). Chaque document n'entre au registre de sources
qu'après le triage HITL — exactement le Source triago du masterplan
AEDIST : enregistrement et validation sont le même acte.

### 2.2 Schéma d'extraction

Une ligne par engagement financier :

| Champ | Exemple |
|---|---|
| projet / opération | « Don AFD réseau électrique Vietnam » |
| pays, JETP | Vietnam |
| financeur, guichet | AFD |
| instrument | don / prêt concessionnel / garantie / fonds propres |
| montant engagé, approuvé, décaissé | 67 M€ engagés |
| devise, date, équivalent-don | mai 2025 |
| conditionnalités déclarées | réforme tarifaire Senelec pour l'AFD 670 M€ |
| statut, source de chaque cellule | sidecar de provenance |

La taxonomie de fragments d'AEDIST se transpose sans modification :
**sériel** (annexes tabulaires des plans d'investissement, tables IPG) →
squelette du master ; **multi-scalaire** (« 17 projets validés en juillet
2025 ») → contrôle d'existence des lignes ; **scalaire** (« l'AFD a signé
67 M€ en mai 2025 ») → mise à jour d'attribut. Fusion chronologique avec
l'autorité en départage, journal de fusion, vérification trois niveaux
(concordance chaîne de caractères → adjudication LLM → HITL). Le master et
son sidecar de provenance donnent la propriété qui fait la valeur
scientifique du produit : *chaque chiffre est localisable dans un document
officiel daté* — « research-quality data isn't correct data, it's data
whose errors are locatable ».

### 2.3 Ce que la comptabilité refaite mesure

- Part de dons, part équivalent-don, ratios décaissé/engagé — par pays,
  par année, par financeur. Le registre de risques 2024 devient un tableau
  de mesures, plus un tableau de verdicts qualitatifs.
- Réconciliation trois sources : chiffres-titres IPG vs somme des fiches
  projet vs CRS/IATI. **Les écarts sont le résultat** : inflation des
  promesses, re-labellisation, double compte — le créneau 3 (littérature
  de l'aide) instrumenté.
- **La carte d'opacité est un livrable** : les notes de délibération non
  publiques (conseils d'administration des bailleurs) sont enregistrées
  comme absences. « X % des montants annoncés sont traçables jusqu'à un
  document public » quantifie l'« opacité financière » que Karg et al.
  constatent par entretiens.

## 3. Articulation avec climate-finance-het (corpus >30 000 réf.)

Les deux programmes sont complémentaires par construction : le corpus het
étudie *comment la finance climat est devenue comptable* (catégories,
métriques, cadres, 1990-2024) ; le ledger produit *les comptes* de
l'instrument le plus récent. La controverse JETP sur l'équivalent-don et
les prêts présentés comme aide est le chapitre vivant de « Counting
Climate Finance » — la recommandation du manuscrit (comptabilité
équivalent-don sous l'article 13) est une thèse de politique de la mesure
que le programme het fonde sur cinq décennies. Le pont créneau 3 se fait
dans les deux sens : la littérature de l'aide éclaire les JETP, et le cas
JETP prolonge l'histoire de la mesure.

Réutilisation pratique, sans fusion des dépôts :

- **Même infrastructure** : padme autorité des données, DVC pour le pool
  documentaire, pipeline corpus → figures → papiers, archive de
  reproductibilité Zenodo — le savoir-faire du data paper RDJ s'applique
  tel quel à un « JETP Finance Ledger » publiable en data paper.
- **Tranche de corpus vivante** : les ~60 références académiques JETP de
  la saturation d'aujourd'hui deviennent une tranche surveillée par le
  même outillage OpenAlex/Crossref que le corpus het. La cartographie de
  littérature de l'option E (WIREs) reste à jour par re-run — la passe de
  saturation devient un rafraîchissement de corpus, pas un exploit
  ponctuel.

## 4. Articulation avec le suivi automatique de la transition énergétique

Le ledger est le jumeau financier du volet physique. Auto-PyPSA ASEAN suit
les mégawatts et les centrales ; le ledger suit les dollars et les
instruments ; le Vietnam et l'Indonésie sont dans les deux périmètres.

**La jointure est le vrai prix.** Événements financiers ↔ événements
physiques, par actif : Cirebon-1 (fonds ETM réaffectés vs retraite
annulée), Komati (seule fermeture effective vs dons versés), Vung Ang II
(mise en service charbon en avril 2026 pendant que le JETP décaisse à
2 %). Personne ne publie « dollars par MW effectivement fermé » ni « délai
entre engagement et effet physique ». C'est l'observable qui tranche la
question que toute la littérature pose de biais : l'argent déplace-t-il
l'acier ?

Bénéfice retour pour AEDIST : un deuxième domaine documentaire (rapports
financiers, notes d'approbation) teste la généralisation de la méthode
au-delà des inventaires de centrales — l'évidence de transférabilité dont
le programme méthodes (Paper B) a besoin. Et la cadence de re-run
trimestrielle du ledger est le « suivi automatique » en production réelle,
plus démonstrative qu'aucun benchmark.

## 5. Séquencement réaliste

1. **Ne pas bloquer l'option E.** La proposition WIREs (2 jours) part
   maintenant avec les formulations sûres de la saturation ; le ledger y
   figure comme agenda de recherche, pas comme prérequis.
2. **Pilote Vietnam** (~1-2 semaines) : recensement documentaire complet
   d'un seul pays — notre avantage comparatif, le terrain natal d'AEDIST,
   l'univers documentaire le plus petit. Tirage CRS/IATI, extraction sur
   ~20 documents, échantillon codé à la main comme vérité terrain, mesure
   rappel/précision avant de faire confiance au reste. C'est la
   méthodologie AEDIST : on ne déploie pas une méthode non benchmarkée.
3. **Décision après pilote** : registre 4 pays → data paper (dépôt
   Zenodo, gabarit RDJ) + section empirique de l'option C, dont le plan de
   mise à jour (12-15 jours) absorbe alors la mise à jour factuelle par
   lecture directe du ledger au lieu de re-recherche web.

**Risques nommés.** Les notes de délibération des bailleurs ne sont que
partiellement publiques — le pilote établira le taux de couverture réel,
et l'absence est une donnée. Les conventions d'équivalent-don et de change
sont des choix de méthode à documenter (suivre le CRS). Le périmètre peut
enfler — le ledger est un workpackage autonome avec son propre dépôt et
ses tickets, pas une annexe du manuscrit.
