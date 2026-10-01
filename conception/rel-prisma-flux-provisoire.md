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

## Exclusions par motif : ICF, discipline, sérieux (vue REL du 1er octobre 2026)

*Provisoire.* Chiffres mesurés dans `data/rel_pool/rel_counts.json` (bloc `reasons`), produit par `make rel-view` le 1er octobre 2026 sur padme (ticket 1843) ; deux passes donnent les mêmes octets. Empreintes sha256 des entrées, relevées dans le bloc `inputs` du fichier, et du fichier lui-même :

```text
pool.csv             3e07852be556a58e0006c6a76770c64432fae39c63d3359c861867c5b2627353
icf_screen.csv       483b93a021086893356edba659bb5cc1aa6db5179eeb2a247904a0397ef0ce77
rel_dimensions.csv   absente (aucune passe de discipline encore écrite)
rel_work_venues.csv  ef12dc12466c918a00737503a25bb776552153ba2f039847c32ee9a4081bede3
rel_counts.json      da7fd4d34c4c4d3a80f878461e7856ed91c46808d135f62426390e36b3ca12cc
```

Chaque œuvre du pool n'est comptée qu'une fois, au premier motif qui s'applique dans l'ordre ICF → discipline → sérieux. La table de discipline n'existe pas encore : le rattrapage (ticket 1842) n'a pas tourné et aucun lot d'étape 2 en version 2 n'est écrit. Toutes les œuvres retenues par l'ICF sont donc « en attente de discipline », et les cases discipline et sérieux restent à zéro par construction, non par mesure. Le sérieux de ces œuvres est déjà calculé et donné à titre indicatif.

| Case | Œuvres | Familles | Source du chiffre |
|---|---:|---:|---|
| **Pool** | 389 291 | 389 261 | mesuré, `pool_works`, `families.families` |
| exclues par l'ICF | 31 993 | 31 993 | mesuré, `reasons.works.icf_excluded` : hors sujet à l'étape 1 29 721, proches à l'étape 2 1 799, hors sujet à l'étape 2 473 |
| en attente de l'ICF | 354 683 | 354 653 | mesuré : non triées 318 598, en attente d'étape 2 36 085 |
| **exclues pour la discipline** | 0 | 0 | provisoire : aucune réponse de discipline encore écrite |
| **en attente de discipline** | **2 615** | **2 615** | mesuré, dont 145 « incertaines » ICF signalées ; à titre indicatif, sérieux : passent 1 991 (dont 400 sans lieu identifié, gardées et signalées), rang C 622, Kanalregisteret niveau X 2 |
| **exclues pour le sérieux** | 0 | 0 | provisoire : le sérieux n'est compté qu'après la discipline |
| **retenues** | 0 | 0 | provisoire |

Parmi les 2 615, les œuvres de recherche de la fenêtre (années complètes, disposition « include ») sont 1 902 : 1 383 passent le sérieux, 519 sont de rang C (`reasons.included_research_in_window`). Le rang C tient surtout aux dépôts et serveurs de prépublications (518 des 622 œuvres de rang C, toutes catégories ; règle `repository` de `rel_work_venues.csv`).

**Sens des biais.** *Discipline* : sur l'ensemble de contrôle de 1840, Opus en version 2 exclut 4 des 59 œuvres que la lecture humaine retient, dont 3 en finance appliquée posant une question de politique (certification des obligations vertes W3122424672, spéculation sur le SEQE-UE W4399863925, W7212372846), contre 3 inclusions en trop. Le compte des exclusions pour la discipline penchera donc vers la sur-exclusion de la finance appliquée ; il se lit comme une borne haute (note recopiée dans `reasons.discipline_note`). *Sérieux* : certains articles de revue que seuls des agrégateurs donnent à voir (DOAJ, Dialnet, ORBi) sont classés au rang C comme simples dépôts faute de résoudre la revue, environ 5 sur 20 dans un échantillon relu (ticket 1841). Le compte des exclusions pour le sérieux est donc surestimé, et l'ensemble retenu sous-estimé d'autant.

**Sensibilité du sérieux** (`data/rel_pool/rel_sensitivity.csv`, même passe, sha256 `3690e755753139104ef45387476bfdd9f082189c8fea3549d139ac00776bd0fb`). Faute de réponses de discipline, l'ensemble retenu est vide ; la table donne donc aussi les œuvres en attente de discipline qui passeraient le sérieux selon chaque réglage, borne haute provisoire de l'ensemble retenu. ICF et discipline fixés ; une ligne par réglage, les autres à leur valeur par défaut.

| Réglage | Retenues | En attente de discipline, sérieux passé |
|---|---:|---:|
| par défaut : rangs A et B, exclusion Kanalregisteret X et revues détournées, MDPI, Frontiers et Hindawi gardés, ONG au rang B, œuvres sans lieu gardées et signalées | 0 | 1 991 |
| MDPI, Frontiers et Hindawi écartés | 0 | 1 941 |
| MDPI seul écarté | 0 | 1 955 |
| Frontiers seul écarté | 0 | 1 983 |
| Hindawi seul écarté | 0 | 1 985 |
| rang A seul | 0 | 1 618 |
| interrupteur (a) élargi : Scopus « discontinued » et retraits du DOAJ excluent aussi | 0 | 1 917 |
| interrupteur (b) inversé : recherche des ONG hors du rang B | 0 | 1 991 |
| interrupteur (c) inversé : œuvres sans lieu identifié exclues | 0 | 1 591 |

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
