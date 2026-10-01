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
| classées à l'étape 1 : proches mais non ICF | 8 303 | mesuré (Haiku 3 819 ; Qwen 4 484) ; ne sortent plus (décision du 30 septembre) |
| **en attente d'étape 2** : « proches » de l'étape 1 | 9 906 | mesuré, `rel_view.csv` du 30 septembre (statut `pending_stage2`, étiquette d'étape 1 « aux », runs `t1530-*`) ; inclut les 1 686 du passage Qwen en cours, hors des 25 693 |
| envoyées à l'étape 2 : « ICF » | 3 069 | mesuré (Haiku 2 028 ; Qwen 1 041) |
| envoyées à l'étape 2 : « incertaines » | 1 723 | mesuré (Haiku 679 ; Qwen 1 044) |
| **Étape 2** (Opus), avant relecture des 8 303 : œuvres relues | 4 792 | mesuré (4 752 en 32 lots + 40 du pilote) |
| exclues à l'étape 2 : proches mais non ICF | 1 746 | mesuré (1 736 + 10) |
| exclues à l'étape 2 : hors sujet | 396 | mesuré (391 + 5) |
| **restées « incertaines »** | **177** | mesuré (174 + 3) ; restent dans REL, signalées (décision du 30 septembre) |
| **retenues « ICF »** | **2 473** | mesuré (2 451 + 22) |
| dont œuvres de recherche | 1 933 | mesuré (1 913 + 20) |
| dont documents institutionnels (hors décompte des œuvres) | 409 | mesuré (408 + 1) |
| dont autres types | 131 | mesuré (130 + 1) |

## Exclusions par motif : sérieux, ICF, discipline (vue REL du 1er octobre 2026)

*Provisoire.* Chiffres mesurés dans `data/rel_pool/rel_counts.json` (bloc `reasons`), produit par `make rel-view` le 1er octobre 2026 sur padme (ticket 1843) ; deux passes donnent les mêmes octets. Les tableaux des sections précédentes datent du 29 septembre et d'une autre table d'étiquettes ; ceux-ci portent sur le pool et la table `icf_screen` que `main` épingle au 1er octobre, qui comprend les 92 845 étiquettes Qwen de l'étape 1 importées ce jour-là. Empreintes des entrées, relevées dans le bloc `inputs`, et du fichier lui-même :

```text
pool.csv             sha256 3e07852be556a58e0006c6a76770c64432fae39c63d3359c861867c5b2627353
icf_screen.csv       sha256 3550e6dfb062969cdaaf82860f1b86263cf5dc2c5b3e6c0c4e46cea7dc8433ef
                     data/rel_screen.dvc md5 1eb9cfeded429aadd5c451dffea6b01d.dir
rel_dimensions.csv   absente (aucune passe de discipline encore écrite)
rel_work_venues.csv  sha256 34bffd3c14eae13e0e7ed3173f413d8d4f4792e8e0da8b281814d1c1e2b707d2
rel_counts.json      sha256 c0aba081ff104962e743c9b97647237d158541f16c40968bda23d28d185dd5cc
```

Le modèle est celui du protocole (ensemble flou coupé à α = 0,5). Les facettes sont évaluées dans l'ordre sérieux → ICF → discipline, du moins coûteux au plus coûteux, et chaque œuvre n'est comptée qu'une fois, à la facette qui atteint son minimum. La table de discipline n'existe pas encore : le rattrapage (ticket 1842) n'a pas tourné et aucun lot d'étape 2 en version 2 n'est écrit. Toutes les œuvres qui passent le sérieux et l'ICF sont donc « en attente de discipline », et les cases « exclues pour la discipline » et « retenues » restent à zéro par construction, non par mesure.

| Case | Œuvres | Familles | Source du chiffre |
|---|---:|---:|---|
| **Pool** | 389 291 | 389 261 | mesuré, `pool_works`, `families.families` |
| exclues pour le sérieux | 39 115 | 39 114 | mesuré, `reasons.works.seriousness_excluded` : rang C 39 113, revue détournée 2 |
| exclues par l'ICF | 125 192 | 125 191 | mesuré : hors sujet à l'étape 1 123 604, proches à l'étape 2 1 214, hors sujet à l'étape 2 374 |
| en attente de l'ICF | 222 992 | 222 964 | mesuré : non triées 160 780, en attente d'étape 2 62 212 |
| **exclues pour la discipline** | 0 | 0 | provisoire : aucune réponse de discipline encore écrite |
| **en attente de discipline** | **1 992** | **1 992** | mesuré ; rang A 1 220, B 370, lieu inconnu 402 ; μ provisoire 1 pour 1 543, 0,5 pour 449 (lieu inconnu ou ICF « incertaine ») |
| **retenues** | 0 | 0 | provisoire |

Des 2 615 œuvres que l'ICF retient, 623 tombent au sérieux, toutes de rang C : 518 par la règle des dépôts, 104 par la règle résiduelle « autre », 1 page non scientifique d'un site institutionnel. Parmi les 1 992 en attente de discipline, les œuvres de recherche de la fenêtre (années complètes, disposition « include ») sont 1 382, dont 308 à μ = 0,5 (`reasons.included_research_in_window`).

**Ce que l'étape 2 peut sauter** (`stage2_skip`). Parmi les 83 681 œuvres en attente d'étape 2, 21 469 sont de rang C, de sérieux nul : l'étape 2 n'a pas à les relire, et 62 212 restent à trier (rang A 48 501, B 7 944, lieu inconnu 5 767). Parmi les 160 896 œuvres non triées, 116 sont de rang C.

**Sens des biais.** *Discipline* : sur l'ensemble de contrôle de 1840, Opus en version 2 exclut 4 des 59 œuvres que la lecture humaine retient, dont 3 en finance appliquée posant une question de politique (certification des obligations vertes W3122424672, spéculation sur le SEQE-UE W4399863925, W7212372846), contre 3 inclusions en trop. Le compte des exclusions pour la discipline penchera donc vers la sur-exclusion de la finance appliquée ; il se lit comme une borne haute (`reasons.discipline_note`). *Sérieux* : certains articles de revue que seuls des agrégateurs donnent à voir (DOAJ, Dialnet, ORBi) sont classés au rang C comme simples dépôts faute de résoudre la revue, environ 5 sur 20 dans un échantillon relu (ticket 1841). Le compte des exclusions pour le sérieux est donc surestimé, et l'ensemble retenu sous-estimé d'autant (`reasons.seriousness_note`).

**Sensibilité du sérieux** (`data/rel_pool/rel_sensitivity.csv`, même passe, sha256 `ad8679c0e446b83fe78f67b24e408e1409a0f72ee401404dedca3737b5e921aa`). Chaque ligne réévalue toutes les œuvres sous un réglage, les autres à leur valeur décidée le 1er octobre. Faute de réponses de discipline, l'ensemble retenu est vide ; la dernière colonne donne les œuvres à qui ne manque que la discipline, borne haute provisoire de l'ensemble retenu.

| Réglage | Retenues | En attente de discipline |
|---|---:|---:|
| décidé : rangs A et B (lieu inconnu à 0,5), exclusion des seules revues détournées, MDPI, Frontiers et Hindawi gardés, ONG au rang B, contenus non scientifiques au rang C | 0 | 1 992 |
| MDPI, Frontiers et Hindawi écartés | 0 | 1 941 |
| MDPI seul écarté | 0 | 1 955 |
| Frontiers seul écarté | 0 | 1 984 |
| Hindawi seul écarté | 0 | 1 986 |
| rang A seul (le lieu inconnu reste à 0,5) | 0 | 1 622 |
| (a') niveau X du Kanalregisteret exclusif | 0 | 1 990 |
| (a) Scopus « discontinued » et retraits du DOAJ exclusifs aussi | 0 | 1 917 |
| (b) recherche des ONG hors du rang B | 0 | 1 992 |
| (c) œuvres sans lieu identifié exclues | 0 | 1 590 |
| (d) contenus non scientifiques gardés à leur rang | 0 | 1 993 |

## Retenues

| Case | Effectif | Statut |
|---|---:|---|
| **Œuvres de recherche ICF, provisoire** | **1 933** | série « ICF » seule, sans les 177 « incertaines » gardées et signalées ; avant comptage par familles, avant relecture des « proches », avant le tri du reste du pool |
| Textes lus pour la synthèse narrative | — | à remplir |

## Validation des outils automatiques (à joindre au rapport)

- **Étape 1**, 200 œuvres contre Opus : Haiku 153 / 200 exact, aucune des 22 œuvres ICF d'Opus étiquetée « hors sujet » ; Qwen (JSON) 169 / 200, aucune étiquetée « hors sujet » mais 1 « proche » ; Qwen (format compact) 164 / 199, aucune « hors sujet » mais 3 « proche », comme six sentinelles (`rel_jev_pilot/2026-09-30/out/report_control.txt`). Depuis le 30 septembre, les « proche » de l'étape 1 passent à l'étape 2. Un seul juge, 22 positifs, très peu d'hindi, de bengali et d'arabe.
- **Étape 2** : pas encore d'audit par échantillon par Fable.
- **Sentinelles** (55 fixées ; 21 œuvres de classe « retrouvable ») : rappel de réserve 13 / 14 sur la passe `f` seule, 14 / 14 avec la requête de comblement `g` (H15 n'y est retrouvée que par `g`, ajoutée à cause des sentinelles de réglage) ; réglage 5 / 7 (échecs connus : S23 espagnol, S55 français). Dix sentinelles absentes d'OpenAlex testent les autres sources.

## Ce qu'il faut pour geler le pool

Voir la réponse du 29 septembre : voies du protocole exécutées ou déclarées impossibles ; étape d'injection dans le catalogue avec provenance et rapport de fusion par source ; tri de tout le pool ; manifeste de gel (empreintes, SHA du code, versions de modèles). La sortie des « incertaines » et l'unité de compte (la famille d'œuvres, version publiée en représentante) sont décidées depuis le 30 septembre.
