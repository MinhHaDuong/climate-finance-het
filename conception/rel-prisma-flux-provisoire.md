# REL — diagramme de flux PRISMA : structure et chiffres provisoires

*29 septembre 2026. Structure PRISMA 2020 pour une revue bibliométrique, avec les chiffres mesurés à ce jour. Rien ici n'est un chiffre publiable : le pool n'est pas gelé (voir la liste en fin de note). Chaque ligne indique d'où vient son chiffre ; « dérivé » signale un calcul, « mesuré » une valeur lue dans un fichier.*

## Identification

| Case | Effectif | Source du chiffre |
|---|---:|---|
| **Catalogue fusionné v2** (pool épinglé au 29 juillet 2026) : notices identifiées | 44 174 | mesuré, `catalog_merge_report.json` (run 20260729T161924Z) |
| doublons par DOI retirés | 833 | mesuré, même fichier |
| doublons titre + année retirés | 159 | mesuré, même fichier |
| notices sans titre écartées | 3 | mesuré, même fichier |
| **Catalogue v2 : œuvres uniques** | **43 179** | mesuré ; dont 33 344 au corpus raffiné v2 |
| **Recherche REL « Sud et langues »** (OpenAlex ; passes `f` et `g`, requêtes gelées, 88 requêtes) : notices reçues | 50 235 | mesuré, registres `f` (41 958 + 6 274 + 31) et `g` (1 972) |
| doublons entre requêtes | 15 748 | dérivé : 50 235 − 34 487 |
| œuvres distinctes de la recherche | 34 487 | mesuré |
| dont déjà au corpus raffiné v2 | 4 007 | dérivé : 34 487 − 30 480 |
| dont déjà au pool brut mais écartées par les filtres v2 | ≈ 490 | mesuré (489 à 493 selon le rapprochement DOI / identifiant) |
| **œuvres nouvelles pour le pool** | **≈ 29 990** | dérivé : 30 480 − ≈ 490 |
| **Pool combiné (catalogue v2 + recherche)** | **≈ 73 170** | dérivé : 43 179 + ≈ 29 990 |
| *Voies non exécutées, cases vides* : Gavard–Schoch, EconLit, sommaires des 61 revues, autres sources du Sud (SciELO, Redalyc, AJOL, CNKI, eLIBRARY, GARUDA, CLACSO), chaînage de citations | — | à remplir avant le gel |

## Sélection sur titre et résumé (deux étapes automatiques)

Les 25 693 œuvres de la recherche absentes du corpus raffiné sont triées ; 3 752 autres l'étaient à l'heure de la rédaction (passage Qwen en cours sur 4 787). Les ≈ 42 688 œuvres du pool brut hors recherche ne sont **pas encore triées**.

| Case | Effectif | Source du chiffre |
|---|---:|---|
| **Étape 1** : œuvres triées (Haiku 4.5 pour 12 491, Qwen3.8-27B pour 13 202) | 25 693 | mesuré, `screen.jsonl` |
| exclues à l'étape 1 : hors sujet | 12 598 | mesuré (Haiku 5 965 ; Qwen 6 633) |
| exclues à l'étape 1 : proches mais non ICF | 8 303 | mesuré (Haiku 3 819 ; Qwen 4 484) ; renvoyées à l'étape 2 par la décision du 30 septembre |
| envoyées à l'étape 2 : « ICF » | 3 069 | mesuré (Haiku 2 028 ; Qwen 1 041) |
| envoyées à l'étape 2 : « incertaines » | 1 723 | mesuré (Haiku 679 ; Qwen 1 044) |
| **Étape 2** (Opus) : œuvres relues | 4 792 | mesuré (4 752 en 32 lots + 40 du pilote) |
| exclues à l'étape 2 : proches mais non ICF | 1 746 | mesuré (1 736 + 10) |
| exclues à l'étape 2 : hors sujet | 396 | mesuré (391 + 5) |
| **restées « incertaines »** | **177** | mesuré (174 + 3) ; restent dans REL, signalées (décision du 30 septembre) |
| **retenues « ICF »** | **2 473** | mesuré (2 451 + 22) |
| dont œuvres de recherche | 1 933 | mesuré (1 913 + 20) |
| dont documents institutionnels (hors décompte des œuvres) | 409 | mesuré (408 + 1) |
| dont autres types | 131 | mesuré (130 + 1) |

## Retenues

| Case | Effectif | Statut |
|---|---:|---|
| **Œuvres de recherche ICF, provisoire** | **1 933** | avant fusion des versions, avant lecture des « incertaines », avant le tri du reste du pool |
| Textes lus pour la synthèse narrative | — | à remplir |

## Validation des outils automatiques (à joindre au rapport)

- **Étape 1**, 200 œuvres contre Opus : Haiku 153 / 200 exact, aucune des 22 œuvres ICF d'Opus étiquetée « hors sujet » ; Qwen (JSON) 169 / 200, aucune étiquetée « hors sujet » mais 1 « proche » ; Qwen (format compact) 164 / 199, aucune « hors sujet » mais 3 « proche », comme six sentinelles (`rel_jev_pilot/2026-09-30/out/report_control.txt`). Depuis le 30 septembre, les « proche » de l'étape 1 passent à l'étape 2. Un seul juge, 22 positifs, très peu d'hindi, de bengali et d'arabe.
- **Étape 2** : pas encore d'audit par échantillon par Fable.
- **Sentinelles** (55 fixées ; 21 œuvres de classe « retrouvable ») : rappel de réserve 13 / 14 sur la passe `f` seule, 14 / 14 avec la requête de comblement `g` (H15 n'y est retrouvée que par `g`, ajoutée à cause des sentinelles de réglage) ; réglage 5 / 7 (échecs connus : S23 espagnol, S55 français). Dix sentinelles absentes d'OpenAlex testent les autres sources.

## Ce qu'il faut pour geler le pool

Voir la réponse du 29 septembre : voies du protocole exécutées ou déclarées impossibles ; étape d'injection dans le catalogue avec provenance et rapport de fusion par source ; tri de tout le pool ; manifeste de gel (empreintes, SHA du code, versions de modèles). La sortie des « incertaines » et l'unité de compte (la famille d'œuvres, version publiée en représentante) sont décidées depuis le 30 septembre.
