# REL — manifeste des sommaires à contrôler (figé le 30 septembre 2026)

## Gel du 30 septembre 2026 (ticket 1650)

Le manifeste est figé dans [`config/rel_toc_manifest.csv`](../config/rel_toc_manifest.csv) : **63 titres**, les 61 ci-dessous plus deux ajouts décidés par l'auteur après le pilote. *AEA Papers and Proceedings* (2574-0768) reprend depuis 2018 le numéro de mai de l'*American Economic Review*, qui a changé d'ISSN : sans lui la série de l'AER serait tronquée. *American Economic Review: Insights* (2640-205X, depuis 2019) est la revue d'articles courts du même comité. Pour chaque titre : pISSN et eISSN vérifiés dans Crossref, provenance, et **rangs dans leur échelle native**, rapprochés par ISSN : liste CNRS section 37 de juin 2020 (v5.07 ; 42 titres classés), ABDC 2025 (v3 du 21 septembre 2026 ; 49), FNEGE 2025 (26). Une case vide signifie « non classé dans cette liste ». L'AJG 2024 n'est pas transcrit : la liste n'est accessible qu'avec un compte Chartered ABS. Les titres historiques n'ont pas été recherchés titre par titre : les requêtes portent sur les ISSN, et les changements d'éditeur (par exemple *Climate Policy*, passé d'Elsevier à Earthscan puis à Taylor & Francis) sont traités par le rapprochement des DOI alias.

Décisions de l'auteur du 30 septembre, après le pilote chronométré :

- Les sommaires viennent de **Crossref et OpenAlex, sans vérification sur les pages des éditeurs**. 95 % des numéros sont derrière des blocages de robots ; ce contrôle est une limite déclarée du dépouillement, jamais une saturation.
- Les six mégarevues (*Sustainability*, *Energies*, *Environmental Science and Pollution Research*, *Journal of Cleaner Production*, *Journal of Environmental Management*, *Applied Energy* : 328 861 articles dans Crossref, 60 % du volume) ne sont **pas dépouillées** : elles sont interrogées par les requêtes thématiques anglaises de la recherche REL (`config/rel_sud_search.yaml`, T1 à T4 et requête complémentaire), restreintes à leurs ISSN.
- Les 57 autres titres sont livrés en entier. *Economic and Political Weekly* n'a pas de DOI avant 2024 : cette période ne compte que ce qu'OpenAlex en tient, et reste à contrôler par l'auteur.

**Livraison du 30 septembre 2026** (`data/rel_intake/t1650-sommaires/2026-09-30/`, DVC ; synthèse par revue dans [`docs/rel-toc-1650-summary.csv`](../docs/rel-toc-1650-summary.csv)). Registre des 57 titres dépouillés : 12 746 numéros ou groupes « en ligne sans numéro », 223 834 éléments attendus et parcourus (217 308 Crossref, 6 526 seulement dans OpenAlex). Parmi eux, 9 986 non-articles (couvertures, comités, listes de relecteurs, notices d'erratum, numéros eux-mêmes) sont écartés comme `front_matter` et 241 éléments sans titre dans Crossref comme dans OpenAlex comme `not_retrievable`. Sur les 213 607 notices livrées, 2 981 sont déjà au pool et 210 626 sont des candidates absentes du pool. 3 700 éléments OpenAlex sans DOI restent non résolus (pour l'essentiel l'AER de 1990 à 1998) ; *Economic and Political Weekly* manque avant 2024. Requêtes thématiques des six mégarevues : 1 313 œuvres retrouvées, 1 256 livrées après dédoublonnage entre requêtes, dont 972 déjà au pool et 284 candidates. Au total 214 863 notices livrées, sans tri de pertinence.

Les tableaux ci-dessous restent le texte de constitution du 28 septembre.

*28 septembre 2026. Extraction nominative pour le contrôle **intégral des sommaires**, distincte de la liste des lieux où la recherche REL peut paraître. Aucun sommaire n'a encore été dépouillé.*

## Règle de constitution

Le noyau généraliste « blue ribbon » est le **top five** usuel de l'économie, confirmé par l'[American Economic Association](https://www.aeaweb.org/research/charts/publishing-promotion-economics-top-five). Les champs connexes retenus sont développement/transition, environnement/énergie/ressources, finance, économie publique, et macroéconomie internationale/monétaire. Pour chacun, la [liste CNRS section 37, juin 2020](https://www.gate.cnrs.fr/wp-content/uploads/2021/12/categorisation37_liste_juin_2020-2.pdf) fournit **tous** les titres de catégorie 1 (ou `1g` en finance). Cela donne **29 titres**, dont cinq généralistes. S'y ajoutent **31 titres** où deux synthèses bibliométriques antérieures ont repéré des publications de finance climat et **un titre** tiré des références de recherche sur la finance climat du draft HET : **61 titres uniques** dans le manifeste provisoire.

Les ISSN ci-dessous sont ceux de la liste CNRS. Avant exécution : ajouter eISSN, années de parution, transferts et changements de titre ; rapprocher avec la [liste Hcéres SHS1](https://www.hceres.fr/sites/default/files/media/files/liste-des-revues-et-des-produits-de-la-recherche-hceres-shs1-eco-et-gestion.pdf), les versions contemporaines [ABDC 2025](https://abdc.edu.au/abdc-journal-quality-list/), [AJG 2024](https://charteredabs.org/academic-journal-guide) et, pour la gestion connexe, [FNEGE 2025](https://fnege.org/classement-des-revues-scientifiques-en-sciences-de-gestion/). Conserver **chaque rang dans son échelle native** et arbitrer les titres nouveaux ou discordants avant de figer ce manifeste. Une revue hors manifeste reste accessible par OpenAlex, EconLit, les recherches régionales et les citations ; son absence de cette liste ne vaut pas exclusion du corpus REL.

Ce complément provient de travaux sur la finance climat **au sens large**, qui incluent aussi la finance verte intérieure et le risque financier climatique. Il sert à repérer des articles, **sans présumer leur pertinence ICF** : chaque candidat passe le même filtre d'inclusion que ceux des autres voies. *Environment and Development Economics* et *Journal of Forest Economics*, par exemple, restent hors de ce dépouillement intégral mais accessibles par les recherches thématiques, régionales et citationnelles. Le rendement du manifeste ne mesure pas à lui seul la complétude du corpus.

## Généralistes « blue ribbon » — cinq titres

| Revue | ISSN |
|---|---|
| American Economic Review | 0002-8282 |
| Econometrica | 0012-9682 |
| Journal of Political Economy | 0022-3808 |
| Quarterly Journal of Economics | 0033-5533 |
| Review of Economic Studies | 0034-6527 |

## Première catégorie des champs connexes — liste CNRS 2020

| Champ CNRS | Revue | ISSN | Rang natif |
|---|---|---|---|
| Développement/transition | Economic Development and Cultural Change | 0013-0079 | 1 |
| Développement/transition | Journal of Comparative Economics | 0147-5967 | 1 |
| Développement/transition | Journal of Development Economics | 0304-3878 | 1 |
| Développement/transition | World Bank Economic Review | 0258-6770 | 1 |
| Développement/transition | World Development | 0305-750X | 1 |
| Environnement/énergie/ressources | American Journal of Agricultural Economics | 0002-9092 | 1 |
| Environnement/énergie/ressources | Ecological Economics | 0921-8009 | 1 |
| Environnement/énergie/ressources | Energy Journal | 0195-6574 | 1 |
| Environnement/énergie/ressources | Journal of Environmental Economics and Management | 0095-0696 | 1 |
| Finance | Journal of Finance | 0022-1082 | 1g |
| Finance | Journal of Financial and Quantitative Analysis | 0022-1090 | 1 |
| Finance | Journal of Financial Economics | 0304-405X | 1 |
| Finance | Review of Finance | 1572-3097 | 1 |
| Finance | Review of Financial Studies | 0893-9454 | 1 |
| Économie publique | American Economic Journal: Economic Policy | 1945-7731 | 1 |
| Économie publique | Journal of Public Economics | 0047-2727 | 1 |
| Économie publique | Public Choice | 0048-5829 | 1 |
| Économie publique | Social Choice and Welfare | 0176-1714 | 1 |
| Macroéconomie internationale/monétaire | American Economic Journal: Macroeconomics | 1945-7707 | 1 |
| Macroéconomie internationale/monétaire | Journal of Economic Dynamics and Control | 0165-1889 | 1 |
| Macroéconomie internationale/monétaire | Journal of Economic Growth | 1381-4338 | 1 |
| Macroéconomie internationale/monétaire | Journal of International Economics | 0022-1996 | 1 |
| Macroéconomie internationale/monétaire | Journal of Monetary Economics | 0304-3932 | 1 |
| Macroéconomie internationale/monétaire | Journal of Money, Credit and Banking | 0022-2879 | 1 |

## Complément fondé sur les revues de littérature antérieures — 31 titres

Deux sources primaires définissent ce complément : [Carè et Weber (2023), figure 2](https://doi.org/10.1016/j.ribaf.2023.101886) recensent les revues ayant publié **au moins quatre** des 315 articles de leur corpus Scopus (2004–2021) ; [Kouwenberg et Zheng (2023), tableaux 1 et 2](https://doi.org/10.3390/su15021255) recensent les vingt premières revues par **nombre d'articles** et par **citations**, respectivement, dans leur corpus Scopus de 1 347 articles (1991–février 2022 ; 2021 est la dernière année complète). La colonne « KZ » donne le nombre d'articles dans ce corpus, **pas** un effectif ICF ; « CW ≥ 4 » signifie que la revue apparaît dans la figure 2, sans lire un compte exact sur les barres. La liste est l'union des trois relevés, après rapprochement des noms de revues et retrait des titres déjà dans les 29 ci-dessus. Les revues du seul tableau de citations KZ entrent ici parce que ce tableau rapporte aussi leur nombre d'articles ; les revues simplement *citées par* les articles du corpus n'y entrent pas. Les effectifs du tableau et la présence dans la figure restent des transcriptions à revérifier sur les originaux avant de figer le manifeste.

| Revue (titre normalisé à vérifier avant moissonnage) | KZ : articles (tableau) | CW : figure 2 |
|---|---:|---|
| Applied Energy | 8 (T2) | — |
| Business Strategy and the Environment | 12 (T1) | — |
| Climate and Development | 16 (T1) | ≥ 4 |
| Climate Law | — | ≥ 4 |
| Climate Policy | 60 (T1) | — |
| Climatic Change | 13 (T1) | — |
| Development (Basingstoke) | — | ≥ 4 |
| Economic and Political Weekly | — | ≥ 4 |
| Energies | 16 (T1) | — |
| Energy Economics | 29 (T1) | — |
| Energy Policy | 46 (T1) | — |
| Environmental and Resource Economics | 12 (T1) | ≥ 4 |
| Environmental Politics | — | ≥ 4 |
| Environmental Science & Policy | — | ≥ 4 |
| Environmental Science and Pollution Research | 31 (T1) | — |
| Finance Research Letters | 20 (T1) | — |
| Global Environmental Change | — | ≥ 4 |
| Global Environmental Politics | — | ≥ 4 |
| Global Policy | — | ≥ 4 |
| International Environmental Agreements: Politics, Law and Economics | 14 (T1) | ≥ 4 |
| Journal of Cleaner Production | 50 (T1) | ≥ 4 |
| Journal of Environmental Management | 11 (T1) | — |
| Journal of Sustainable Finance & Investment | 44 (T1) | ≥ 4 |
| Land Use Policy | — | ≥ 4 |
| Mitigation and Adaptation Strategies for Global Change | 9 (T2) | — |
| Nature Climate Change | 7 (T2) | ≥ 4 |
| Renewable and Sustainable Energy Reviews | 11 (T1) | — |
| Resources Policy | 14 (T1) | — |
| Sustainability | 70 (T1) | ≥ 4 |
| Technological Forecasting and Social Change | 11 (T1) | — |
| Wiley Interdisciplinary Reviews: Climate Change | — | ≥ 4 |

Trois titres des relevés sont déjà dans le noyau CNRS : *Ecological Economics* (19 articles KZ, CW ≥ 4), *World Development* (CW ≥ 4) et *Review of Financial Studies* (11 articles KZ). Ils ne sont comptés qu'une fois. Le nombre de titres par revue dans ces synthèses mesure leur **champ large**, non la production sur les transferts internationaux. Avant de lancer le dépouillement, valider pour ces titres les pISSN/eISSN, variantes de titre, dates de couverture et sommaires accessibles ; conserver les revues régionales et non anglophones dans les recherches complémentaires indépendamment de cette liste.

Contrôle régional limité : la [revue bibliométrique consacrée à la finance climat en Afrique](https://doi.org/10.3390/su151713036) identifie *Climate Policy* (8 documents) et *Climate and Development* (6) comme ses deux premières sources. Les deux figurent déjà dans le complément ; ce contrôle de deux lieux n'ajoute donc pas de titre au manifeste et ne mesure pas la couverture des revues africaines ou non anglophones. La voie [Sud et langues](rel-audit-finalisation-corpus.md) vérifie cette couverture indépendamment. Le tableau des sources mêle revues et livres : ne pas transformer ces derniers en revues lors d'un éventuel élargissement.

## Contrôle des références du draft HET — un titre supplémentaire

Le [manuscrit HET](../deliverables/manuscript/manuscript.qmd) cite directement une recherche sur la finance climat publiée dans une revue absente des deux groupes ci-dessus : la [revue bibliométrique de Carè et Weber (2023)](https://doi.org/10.1016/j.ribaf.2023.101886), parue dans *Research in International Business and Finance*. Ajouter cette revue au contrôle intégral des sommaires. Les autres revues qui accueillent les études de finance climat citées dans le draft HET — notamment *Climate Policy*, *Climate and Development*, *Climatic Change*, *Energy Policy*, *Environmental Science and Pollution Research*, *International Environmental Agreements: Politics, Law and Economics*, *Sustainability*, *Wiley Interdisciplinary Reviews: Climate Change* et *World Development* — figurent déjà dans le manifeste. Les revues mobilisées uniquement pour l'histoire des sciences, la sociologie des catégories ou les méthodes ne sont pas ajoutées au titre de ce contrôle.

Le dépouillement vise tous les numéros publiés depuis 1990 jusqu'à la date finale de recherche, ainsi que les articles en ligne encore sans numéro. Pour chaque revue/année/numéro, le registre devra indiquer la source du sommaire, les articles relevés, les correspondances dans le corpus et les cas non résolus. Il ne s'agit pas de lire intégralement tous les articles : titre et métadonnées servent au repérage, puis le résumé ou le texte tranche les candidats ambigus selon la règle ICF commune.
