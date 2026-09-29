# Revue Astra — protocole de moissonnage REL

*28 septembre 2026. Revue critique du [protocole](rel-audit-finalisation-corpus.md) et du [plan de recherche](rel-plan-de-recherche.md). L'avis original est conservé ci-dessous ; les précisions de l'auteur et corrections ultérieures sont consignées en fin de note.*

**Avis général : révisions nécessaires avant la collecte finale.** Les voies proposées sont pertinentes, mais leur clôture n'est pas encore vérifiable ; deux descriptions du pipeline doivent être corrigées.

## Constats prioritaires

1. **Un grand sweep peut rester incomplet tout en étant enregistré comme terminé.** Le protocole ne précise ni le mode du rerun ni sa preuve de complétude ([audit, ligne 15](rel-audit-finalisation-corpus.md)). Or DVC lance OpenAlex avec `--resume` ([dvc.yaml](../dvc.yaml)) : la reprise interroge les notices créées depuis une date mémorisée, ignore les identifiants déjà dans le pool et, lorsqu'un budget est épuisé pendant une requête, date quand même celle-ci comme achevée ([openalex_pool.py](../scripts/openalex_pool.py)). Un reliquat peut ainsi être sauté. **Révision demandée :** journal par requête avec pagination achevée, nombre attendu/reçu, interruptions et reprise sans avancer la date avant achèvement ; distinguer l'ajout de notices du rafraîchissement des anciennes. Le `dvc.lock` seul ne démontre pas la complétude du passage.

2. **Les critères de pertinence ne permettent pas encore une sélection cohérente.** « Recherche sur la finance climat » ne tranche pas les cas frontières : tarification carbone générale, finance verte sans objet climatique, ingénierie énergétique, textes institutionnels, enseignement ([audit, ligne 9](rel-audit-finalisation-corpus.md)). Le filtre protège certaines notices multibase, citées ou institutionnelles même si elles sont signalées hors thème ([filter_flags.py](../scripts/filter_flags.py)). **Révision demandée :** quelques règles d'inclusion et d'exclusion avec exemples limites, types documentaires admis, distinction corpus cartographié/documents de contexte et calibration humaine sur les cas ambigus. Une protection technique ne vaut pas décision scientifique.

3. **Une notice retrouvée peut être éliminée plus tard.** Une notice sans résumé peut être écartée faute de mot « sûr » dans son titre ([filter_flags.py](../scripts/filter_flags.py)). Ajouter des requêtes russes ou indonésiennes ne suffit donc pas. De plus, l'affirmation de l'audit selon laquelle les niveaux 3–4 exigent des groupes de mots dans le résumé est **fausse à l'extraction actuelle** : `default_min = 0` désactive ce contrôle ([catalog_openalex.py](../scripts/harvest/catalog_openalex.py)). **Révision demandée :** corriger la description et suivre les articles sentinelles jusqu'au corpus final ; auditer les exclusions par langue, source, résumé absent et protection. Toute inclusion humaine doit disposer d'une voie d'application vérifiable.

4. **Le contrôle des sommaires manque d'univers et de budget définis.** « Revues économiques classées » sur toute la fenêtre 1990–2024 représente potentiellement un volume considérable ([audit, ligne 19](rel-audit-finalisation-corpus.md)). **Révision demandée :** figer un manifeste des revues/ISSN, les années et les lacunes ; contrôle exhaustif sur une sélection motivée, échantillon stratifié explicite ailleurs. Examiner les sommaires indépendamment des seuls mots-clés qui ont produit le corpus. Rapporter les absences parmi les articles pertinents effectivement examinés, sans prétention à une couverture mondiale. La distinction déjà faite entre Crossref et un sommaire complet est bonne.

5. **Versions, dates et comptes PRISMA demandent une unité de compte explicite.** « Fusionner les versions » ne dit pas quelle date rend admissible un working paper de 2024 devenu article en 2025 ([audit, ligne 48](rel-audit-finalisation-corpus.md)). La fusion courante garde séparés les DOI distincts et ne dédoublonne par titre+année que les notices sans DOI ([catalog_merge.py](../scripts/harvest/catalog_merge.py)). **Révision demandée :** distinguer identifiants de notice, version et œuvre ; fixer date d'admissibilité, version analysée, règles pour traductions et résultats modifiés. Réconcilier séparément résultats de recherche, notices uniques, versions, œuvres admises et textes lus. Le paragraphe final devra rendre compte du corpus cumulatif plutôt que laisser entendre une collecte unique.

## Constats de priorité moyenne

6. **Les voies EconLit, Sud et hors DAG ne sont pas encore assez spécifiées.** Les quatre controverses promises à REL figurent dans le plan, mais n'ont pas chacune une recherche minimale explicite. EconLit nécessite une adaptation des champs, descripteurs/JEL, syntaxe et exports ; les sources régionales, langues et répertoires de working papers restent à nommer. **Révision demandée :** matrice thème × base × langue × articles sentinelles, avec voies autonomes pour les quatre controverses, l'adaptation, la justice et les approches critiques ; préciser validation des formulations locales et traitement des affiliations multiples ou inconnues.

7. **Les regroupements d'arcs et les sondages ne sont pas reproductibles.** Les nombres de cooccurrences n'ont ni révision du corpus, ni chaînes exactes, ni liste de notices associée ([audit, ligne 30](rel-audit-finalisation-corpus.md)). **Révision demandée :** correspondance arc → famille → requêtes → études/sentinelles → statut, en séparant études du mécanisme financier, littérature auxiliaire sur une relation physique et identité comptable. Une arête médiateur–résultat peut appeler une recherche sans terme financier, dont les résultats resteront distincts du corpus REL.

8. **La section « Points d'arrêt » n'en fixe aucun.** Elle mentionne sentinelles et rendement marginal sans définir la clôture des voies, la résolution des cas pendants ou les tours de chaînage ([audit, ligne 48](rel-audit-finalisation-corpus.md)). **Révision demandée :** clore lorsque toutes les voies prévues sont exécutées ou explicitement déclarées impossibles, chaque référence externe reçoit une décision, les sentinelles manquées sont expliquées, les recherches interrompues reprises et les comptes réconciliés. Fixer à l'avance ce qui déclenche un tour de chaînage supplémentaire.

## Appréciation et décisions

Points solides : distinction entre date de collecte et fenêtre analytique ; DAG employé comme heuristique ; séparation pays étudié/affiliation/langue ; rangs des revues conservés dans leur liste d'origine ; prudence sur les cooccurrences et l'exhaustivité.

Décisions à fixer avec l'auteur avant exécution : conserver 1990–2024 ou étendre la fenêtre REL ; frontières thématiques et documentaires ; profondeur faisable du contrôle des sommaires ; date et version admissibles pour une même œuvre. Le plan retient déjà 1990–2024 alors que l'audit laisse l'extension ouverte : les harmoniser.

*Constats techniques fondés sur le code local. Cette revue n'a pas recalculé les effectifs du corpus ni actualisé les sources externes.*

## Précision de l'auteur après lecture — sommaires

L'auteur précise que le contrôle doit être **intégral**, mais dans un ensemble de revues préalablement délimité par le classement : généralistes « blue ribbon » et première catégorie des champs connexes. Le protocole a été corrigé en ce sens. Le point 4 d'Astra est donc résolu sur le **mode de contrôle** (aucun échantillonnage des numéros de cet ensemble) ; il reste à figer le manifeste nominatif avec ISSN, classement, année et changements de titre, puis à documenter les numéros éventuellement introuvables. Les autres constats de la revue restent ouverts.

## Précision de l'auteur après lecture — frontière documentaire

L'auteur fixe le sujet à la **finance climat internationale**, en excluant la finance verte dépourvue d'objet climatique. Les documents institutionnels sont inclus dans la recherche documentaire et la collecte, mais exclus des œuvres de recherche comptées dans la revue de littérature. Le protocole et le plan ont été précisés en ce sens. Le point 2 d'Astra est résolu sur cette frontière de principe ; il reste à calibrer les cas limites et à appliquer la règle explicitement au corpus analytique, puisque les protections techniques du pipeline ne sont pas des décisions d'inclusion.

## Suite donnée — adaptation, forêt et description du filtre

L'auteur retient les travaux sur l'adaptation et la forêt quand ils portent sur l'ICF ; la profondeur de leur synthèse dépendra des résultats, sans deux revues sectorielles supplémentaires. La description erronée du filtre de niveaux 3–4 dans l'audit a été corrigée ; la vérification de son comportement dans le pipeline et l'audit des exclusions restent à faire.

## Précision de l'auteur après lecture — années et instruments

L'auteur décide de moissonner jusqu'à la date finale de recherche, d'inclure 2025 dans le lot REL et d'y admettre les working papers de 2026. Le protocole distingue désormais les séries annuelles complètes arrêtées en 2025 de l'année partielle 2026 ; les autres travaux de recherche pertinents disponibles en 2026 suivent la même règle d'inclusion. La même frontière ICF s'applique aux marchés carbone et à la finance privée : mécanisme international à objet climatique explicite. Le point 5 d'Astra reste ouvert sur la mise en œuvre et la réconciliation des versions, même si la règle de dates de la revue est maintenant fixée.

## Consultation complémentaire — couverture du Sud (29 septembre 2026)

*Avis de `gpt-6-astra` (effort élevé), demandé par l’auteur après lecture du manifeste de 61 revues. Contexte fourni : uniquement le protocole et le manifeste, copiés dans un répertoire isolé ; ni dépôt ni accès web. Tous les titres et caractéristiques ci-dessous viennent de sa mémoire : **non vérifiés** (existence, activité, DOI, accès, rendement ICF). Texte reproduit tel quel ; les titres de section sont abaissés d’un niveau.*

### Couverture du Sud : insuffisamment garantie

**1. Priorité : corriger la sélection.** Les 61 titres ne garantissent aucune représentativité mondiale. CNRS/top five privilégient l’économie académique internationalisée ; les bibliométries Scopus reproduisent les contraintes d’indexation, de langue et de citations. Leurs seuils éliminent les petites sources ; leur finance climat large favorise aussi la finance domestique. Ces biais se cumulent.

Le complément améliore la couverture : *Economic and Political Weekly* est déjà présent. Des chercheurs du Sud publient dans les revues internationales. Impossible donc de quantifier le déficit à partir des seuls titres, ou de confondre éditeur septentrional et production septentrionale. Mais aucune couverture systématique non anglophone n’est garantie.

La voie « Sud et langues » est une bonne intention insuffisamment opérationnelle : sources, langues, responsabilités et effort minimal restent indéterminés. Elle doit devenir une strate obligatoire, avec sentinelles indépendantes du corpus existant, recherche sans résumé et lecture des textes ambigus.

**2. Sources manquantes.** **E** = sommaires exhaustifs ; **Q** = requêtes. Caractéristiques indicatives ; **UNVERIFIED** concerne partout l’activité actuelle, la complétude des archives et l’accès. DOI absent ne signifie jamais exclusion.

| Revues absentes | Couverture, langue ; faisabilité proposée |
|---|---|
| 气候变化研究进展 | Chine, politiques climatiques ; chinois. **E**, DOI et métadonnées bilingues possibles ; archives éditeur à contrôler. |
| *Current Science* | Inde, sciences/politiques ; anglais. **Q** : vaste volume, archives ouvertes, DOI variables historiquement. |
| *Revista Brasileira de Política Internacional* ; *Ambiente & Sociedade* | Brésil, relations internationales/environnement ; portugais, anglais, autres langues selon période. **E**, SciELO, métadonnées structurées, DOI, accès ouvert. |
| *Development Southern Africa* | Afrique australe, développement ; anglais. **E**, sommaires/DOI structurés ; texte parfois payant. |
| *Africa Development / Afrique et développement* | CODESRIA, Dakar, développement et économie politique ; anglais/français. **E**, archives ouvertes ; anciens DOI/métadonnées inégaux. |
| *Revista Angolana de Sociologia* | Angola/Afrique lusophone, sciences sociales ; portugais. **Q**, archives et continuité **UNVERIFIED**, DOI/couverture à inventorier. |
| *Мировая экономика и международные отношения* | Russie, économie mondiale et relations internationales ; russe. **Q**, DOI récents, métadonnées bilingues ; accès variable. |
| *Jurnal Ekonomi dan Pembangunan* | Indonésie, développement ; indonésien/anglais. **Q**, archives ouvertes, DOI variables ; identifier précisément éditeur/ISSN. |
| *Revista CEPAL* | Amérique latine, économie du développement ; espagnol, édition anglaise. **E**, archives ouvertes structurées ; DOI variables, traductions à dédoublonner. |
| *The Journal of Pacific Studies* | Pacifique insulaire, développement/gouvernance ; anglais. **E**, archives universitaires ; DOI et continuité à contrôler. |

**Dépôts et index : Q dans tous les cas**, sans prétendre épuiser chaque base :

- **SciELO, Redalyc** : Amérique latine notamment, espagnol/portugais/anglais ; accès ouvert, métadonnées structurées, DOI variables.
- **CNKI, Wanfang** : Chine, chinois ; métadonnées riches mais export/texte souvent sous abonnement, DOI inégaux.
- **AJOL** : revues africaines, surtout anglais/français ; métadonnées hétérogènes, accès mixte, DOI variables ; couverture lusophone limitée.
- **GARUDA** : Indonésie, indonésien/anglais ; notices et liens éditeurs, qualité/DOI variables.
- **eLIBRARY.ru/RSCI** : Russie, russe ; accès/export contraints, DOI variables.
- **CLACSO** : recherche latino-américaine, espagnol/portugais ; dépôt ouvert, PDF et métadonnées variables, DOI non systématiques.
- **Shodhganga** : thèses indiennes, anglais/langues indiennes ; accès ouvert, identifiants de dépôt, métadonnées variables.
- **Dépôts University of the West Indies et University of the South Pacific** : Caraïbes/Pacifique, surtout anglais ; thèses/recherche locale, identifiants institutionnels, métadonnées variables.

**Séries : Q**, puis inventaire complet des collections climatiques identifiées : Ipea, *Texto para Discussão* (Brésil, portugais) ; ERSA, *Working Papers* (Afrique australe, anglais) ; South Centre, *Research Papers* (coopération Sud, anglais surtout) ; ADB, *Economics Working Paper Series* (Asie, anglais). PDF généralement ouverts ; numéros stables plus fiables que DOI. Ajouter les catalogues CEEW (Inde) et CPD (Bangladesh), anglais : rapports de recherche, métadonnées hétérogènes, DOI souvent absents.

**3. Borner l’effort.** Ajouter les sept titres E ; rechercher les autres par lexiques locaux et instruments ICF. Appliquer 1990–date finale, inclure anciens titres et articles sans numéro. Prévoir deux tours de chaînage ; troisième uniquement si nouvelles œuvres admissibles au second. Clôture après exécution des requêtes prévues, décisions sur toutes les sentinelles, rapprochement des versions et résolution/documentation des lacunes. Une limite budgétaire laisse une strate « incomplète », jamais « saturée ».

**4. Corriger les catégories.** Conserver séparément pays étudiés, rôles financiers, affiliations multiples à publication et langues intégrales ; anglais ≠ Nord, affiliation ≠ nationalité. Définir le Sud indépendamment des BRICS. Garder BRICS-5 comme strate fixe, dater les adhésions, distinguer membres/partenaires ; vérifier notamment le statut saoudien derrière les « onze ». Clarifier l’exclusion institutionnelle : admettre les recherches selon question, méthode et preuves, y compris rapports collectifs sans signature individuelle.

**Ce que je n’ai pas pu vérifier.** Aucun contrôle externe, conformément à la consigne : activité actuelle, accès, DOI, rendement ICF des sources proposées et composition actuelle des BRICS restent **UNVERIFIED**.
