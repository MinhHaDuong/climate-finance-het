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

## Exclusions par motif : sérieux, ICF, discipline (vue REL du 7 octobre 2026)

*Comptes finaux du 7 octobre 2026, après le rattrapage de discipline (ticket 1842, PR 1660, 1704, 1705, 1706).* Chiffres mesurés dans `data/rel_pool/rel_counts.json` (bloc `reasons`), produit par `make rel-view` le 7 octobre 2026 sur padme (ticket 1843), refait après la dernière écriture de `rel_dimensions.csv` ; deux passes donnent les mêmes octets (relevé des journaux des tickets 1842 et 1843 ; les empreintes de `rel_counts.json` et de `rel_view.csv` ci-dessous datent de la passe précédente et ne sont pas recopiées ici). Ils remplacent ceux du 1er octobre (« non triées 160 780 », « en attente d'étape 2 62 212 »), devenus caducs avec l'import de l'étape 2 (ticket 1995). Les tableaux des sections précédentes datent du 29 septembre et d'une autre table d'étiquettes. La table `icf_screen` est celle que `data/rel_screen.dvc` épingle au 7 octobre : elle comprend la fin de l'étape 1 en plan B et les 158 636 œuvres étiquetées à l'étape 2 (ticket 1733). Empreintes des entrées, relevées dans le bloc `inputs`, et des sorties :

```text
pool.csv             sha256 3e07852be556a58e0006c6a76770c64432fae39c63d3359c861867c5b2627353
icf_screen.csv       sha256 c6fae914ed04aed92c4f817fe47d93d289864315954976208c5af1f8d445f86b
                     data/rel_screen.dvc md5 c3a3a119ec02c96a3dcf39e60e7700ef.dir
rel_dimensions.csv   sha256 73e2b452… (11 645 œuvres ; rattrapage de discipline, enveloppe v2 sha 81598e66…)
rel_work_venues.csv  sha256 34bffd3c14eae13e0e7ed3173f413d8d4f4792e8e0da8b281814d1c1e2b707d2
rel_counts.json      sha256 0d8753c1fe432bde28da3c55bbfd0c6f45b0bcfc9e97896024e82eea0a948cd5
rel_sensitivity.csv  sha256 6e9ec37bfbb70e22c72e0449e554890ee91132d88f53e202db2b0ef27de30024
```

**Étiquettes ICF après l'étape 2** (mesuré, `status` de `rel_view.csv`). Sur les 158 636 œuvres de référence de l'étape 2 (runs `t1733-stage2-sol-*`) : icf 11 982, proches 92 261, hors sujet 49 138, incertaines 5 255, comme le relevé du ticket 1733. Sur tout le pool : icf 14 452, proches 94 060, hors sujet 49 683, incertaines 5 400, hors sujet dès l'étape 1 225 341, en attente d'étape 2 296, non triées 59.

Le modèle est celui du protocole (ensemble flou coupé à α = 0,5). Les facettes sont évaluées dans l'ordre sérieux → ICF → discipline, du moins coûteux au plus coûteux, et chaque œuvre n'est comptée qu'une fois, à la facette qui atteint son minimum. La table de discipline existe : le rattrapage (ticket 1842, Opus en version 2 de l'enveloppe, passe complète puis reprise de 152 œuvres restées sans réponse) donne une réponse de discipline à 11 645 œuvres, soit toutes les œuvres icf ou incertaines qui ont un résumé (11 507 icf, 138 incertaines ; mesuré, journal du ticket 1842). Les 8 207 œuvres icf ou incertaines sans résumé ne sont pas envoyées (dérivé : 19 852 − 11 645) ; elles restent « en attente de discipline », bibliométrie seule.

| Case | Œuvres | Familles | Source du chiffre |
|---|---:|---:|---|
| **Pool** | 389 291 | 389 261 | mesuré, `pool_works`, `families.families` |
| exclues pour le sérieux | 39 115 | 39 114 | mesuré, `reasons.works.seriousness_excluded` : rang C 39 113, revue détournée 2 |
| exclues par l'ICF | 335 652 | 335 642 | mesuré : hors sujet à l'étape 1 208 016, proches 80 569, hors sujet à l'étape 2 47 067 |
| en attente de l'ICF | 351 | 350 | mesuré : en attente d'étape 2 292, non triées 59 |
| **exclues pour la discipline** | 780 | non remesuré | mesuré (`reasons.works.discipline_excluded`) ; à lire comme une borne haute (voir *Sens des biais*) |
| **en attente de discipline** | **5 894** | non remesuré | mesuré ; toutes sans résumé (`no_abstract`), bibliométrie seule |
| **retenues** | **7 499** | non remesuré | mesuré (`reasons.works.included`) |

Les quatre lignes de motif somment au pool (dérivé : 39 115 + 335 652 + 351 + 5 894 + 780 + 7 499 = 389 291 ; 5 894 + 780 + 7 499 = 14 173, le total d'avant le rattrapage). Des 19 852 œuvres que l'ICF retient (dérivé : icf 14 452 + incertaines 5 400), 5 679 tombent au sérieux, toutes de rang C : 3 724 par la règle des dépôts, 1 899 par la règle résiduelle « autre », 56 pages non scientifiques de sites institutionnels (mesuré, `rel_view.csv` joint à `tier_rule` de `rel_work_venues.csv`). Le décompte des œuvres de recherche de la fenêtre (années complètes, disposition « include ») n'a pas été refait après le rattrapage : l'ancien chiffre (8 830 parmi les 14 173 alors en attente) est caduc.

**Œuvres sans résumé : bibliométrie seule** (décision de l'auteur du 7 octobre 2026, tickets 1733 et 1843). Une œuvre dont le résumé du pool est vide une fois les blancs retirés porte `abstract_flag` = `no_abstract` ; c'est la règle du `build` du rattrapage de discipline (ticket 1842). La facette ne change ni μ, ni le motif, ni `rel_final` : elle partage l'ensemble retenu entre `rel_use` = `synthesis` (avec résumé) et `bibliometric_only`. Mesuré avant le rattrapage (`reasons.no_abstract_by_reason_works`) : 5 894 des 14 173 œuvres alors en attente de discipline n'avaient pas de résumé (μ 1 pour 1 342, 0,5 pour 4 552) ; ce sont, après le rattrapage, toutes les œuvres encore en attente de discipline ; s'y ajoutent 7 997 exclues pour le sérieux, 143 212 exclues par l'ICF et 209 en attente de l'ICF. Le registre du 7 octobre (`rel_pool_runs/2026-10-07-no-abstract-register`, 7 422 œuvres : icf 2 281, incertaines 5 141, une seule passe d'étape 2) est entièrement inclus dans cette règle ; la règle y ajoute 785 œuvres icf ou incertaines d'autres passes (664 icf, 121 incertaines ; mesuré). Le rattrapage les laisse de côté : ces 5 894 œuvres restent en attente de discipline (`reasons.no_abstract_note`).

**Ce que l'étape 2 peut sauter** (`stage2_skip`). Parmi les 296 œuvres en attente d'étape 2, 4 sont de rang C, de sérieux nul ; 292 restent à trier (rang A 287, B 2, lieu inconnu 3). Les 59 œuvres non triées sont toutes de lieu inconnu. L'auteur a accepté le 7 octobre de laisser ces 296 sans étiquette (ticket 1733).

**Sens des biais.** *Discipline* : sur l'ensemble de contrôle de 1840, Opus en version 2 exclut 4 des 59 œuvres que la lecture humaine retient, dont 3 en finance appliquée posant une question de politique (certification des obligations vertes W3122424672, spéculation sur le SEQE-UE W4399863925, W7212372846), contre 3 inclusions en trop. Le compte des exclusions pour la discipline penchera donc vers la sur-exclusion de la finance appliquée ; il se lit comme une borne haute (`reasons.discipline_note`). *Sérieux* : certains articles de revue que seuls des agrégateurs donnent à voir (DOAJ, Dialnet, ORBi) sont classés au rang C comme simples dépôts faute de résoudre la revue, environ 5 sur 20 dans un échantillon relu (ticket 1841). Le compte des exclusions pour le sérieux est donc surestimé, et l'ensemble retenu sous-estimé d'autant (`reasons.seriousness_note`).

**Sensibilité du sérieux** (`data/rel_pool/rel_sensitivity.csv`, même passe). Chaque ligne réévalue toutes les œuvres sous un réglage, les autres à leur valeur décidée le 1er octobre. **Ce tableau date de la passe d'avant le rattrapage de discipline et n'a pas été refait** : ses colonnes (retenues 0, en attente 14 173) ne valent plus. Relancer `make rel-view` donne `rel_sensitivity.csv` à jour ; le décompte décidé est maintenant 7 499 retenues. Les écarts relatifs entre lignes restent indicatifs.

| Réglage | Retenues | En attente de discipline |
|---|---:|---:|
| décidé : rangs A et B (lieu inconnu à 0,5), exclusion des seules revues détournées, MDPI, Frontiers et Hindawi gardés, ONG au rang B, contenus non scientifiques au rang C | 0 | 14 173 |
| MDPI, Frontiers et Hindawi écartés | 0 | 13 891 |
| MDPI seul écarté | 0 | 13 943 |
| Frontiers seul écarté | 0 | 14 133 |
| Hindawi seul écarté | 0 | 14 161 |
| rang A seul (le lieu inconnu reste à 0,5) | 0 | 12 102 |
| (a') niveau X du Kanalregisteret exclusif | 0 | 14 169 |
| (a) Scopus « discontinued » et retraits du DOAJ exclusifs aussi | 0 | 13 796 |
| (b) recherche des ONG hors du rang B | 0 | 14 173 |
| (c) œuvres sans lieu identifié exclues | 0 | 11 923 |
| (d) contenus non scientifiques gardés à leur rang | 0 | 14 229 |

## Retenues

| Case | Effectif | Statut |
|---|---:|---|
| **Œuvres retenues par la vue REL** | **7 499** | mesuré (7 octobre 2026, section « Exclusions par motif »), toutes avec résumé ; remplace le chiffre du 29 septembre (1 933, série « ICF » seule, avant tri du reste du pool) ; comptes par familles non remesurés |
| Textes lus pour la synthèse narrative | — | à remplir |

## Validation des outils automatiques (à joindre au rapport)

- **Étape 1**, 200 œuvres contre Opus : Haiku 153 / 200 exact, aucune des 22 œuvres ICF d'Opus étiquetée « hors sujet » ; Qwen (JSON) 169 / 200, aucune étiquetée « hors sujet » mais 1 « proche » ; Qwen (format compact) 164 / 199, aucune « hors sujet » mais 3 « proche », comme six sentinelles (`rel_jev_pilot/2026-09-30/out/report_control.txt`). Depuis le 30 septembre, les « proche » de l'étape 1 passent à l'étape 2. Un seul juge, 22 positifs, très peu d'hindi, de bengali et d'arabe.
- **Étape 2** : pas d'audit par échantillon par Fable mesuré ; critère mis de côté par décision de l'auteur du 7 octobre 2026 (ticket 1733). Le seul accord au dossier est celui de Fable sur les étiquettes de Sol avant corrections (300 étiquettes : ICF contre non-ICF 0,81 pondéré, quatre étiquettes 0,55 pondéré), qui précède les corrections de Fable et d'Opus sur les incertaines.
- **Discipline** : validation du rattrapage sur l'ensemble de contrôle de 1840 (142 œuvres, enveloppe v2) : kappa de la contribution 0,790 non pondéré sur les 142 œuvres, 0,926 pondéré linéairement sur les 121 sans « na » (PR 1704 ; coût 0,155 USD). Passe complète facturée 11,927844 USD, reprise de 152 œuvres 0,348720 USD, plus une hausse d'usage de la clé de 0,541442 USD de cause non établie pendant qu'un lot Batch abandonné était en cours (le total peut encore monter si ce lot est facturé) (journal du ticket 1842).
- **Sentinelles** (55 fixées ; 21 œuvres de classe « retrouvable ») : rappel de réserve 13 / 14 sur la passe `f` seule, 14 / 14 avec la requête de comblement `g` (H15 n'y est retrouvée que par `g`, ajoutée à cause des sentinelles de réglage) ; réglage 5 / 7 (échecs connus : S23 espagnol, S55 français). Dix sentinelles absentes d'OpenAlex testent les autres sources.

## Ce qu'il faut pour geler le pool

Voir la réponse du 29 septembre : voies du protocole exécutées ou déclarées impossibles ; étape d'injection dans le catalogue avec provenance et rapport de fusion par source ; tri de tout le pool ; manifeste de gel (empreintes, SHA du code, versions de modèles). La sortie des « incertaines » et l'unité de compte (la famille d'œuvres, version publiée en représentante) sont décidées depuis le 30 septembre.
