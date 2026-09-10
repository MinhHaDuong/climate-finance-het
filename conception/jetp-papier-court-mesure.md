<!-- Atterri (ticket 0709, 2026-09-10), matériau de conception pour un
     livrable futur (0711) — pas encore câblé. Composé depuis
     `jetp-cr-reunion-2026-09-08.md` et les notes empiriques du 2026-09-08 de
     ~/CNRS/projets/actifs/jetp/papier-court-mesure/ ; contenu redistribué et
     recadré sur le périmètre du papier court, pas une simple copie. -->

# Papier court — mesure et mécanisme (JETP)

Titre de travail : *Just Energy Transition Partnerships: the disbursement
gap is instrument substitution, not delay*. Second volet, avec le papier
long d'économie politique comparée (`jetp-papier-long-economie-politique.md`),
d'un papier unique reformulé le 2026-09-08 en réunion avec Christophe Cassen
(CR complet : `jetp-cr-reunion-2026-09-08.md`).

## Idée de recherche

Le fait déclencheur : à quatre ans, le JETP vietnamien a décaissé **≈ 9 %**
de sa part publique, contre une référence de **37,3 %** pour un portefeuille
comparable de prêts concessionnels énergie (mêmes pays, mêmes bailleurs,
même secteur, cohortes d'engagement 2006-2020) — facteur **5,3**. Pris seul,
ce chiffre invite la lecture réflexe : le JETP est lent.

**Ce n'est pas le résultat. Le résultat est que ce n'est pas de la
lenteur — c'est une substitution d'instrument**, mesurable et généralisable
aux quatre pays. Décomposé par modalité CRS :

- Appui budgétaire (A01/A02, décaisse contre déclencheurs de réforme, pas
  contre travaux) : **98,6 %** à un an, structurellement quasi instantané.
- Prêts type projet (C01) : **9,3 %** l'année même, 37,3 % à 4 ans.

Le cas sud-africain est le test qui sépare les deux lectures. Pris en
agrégat, il **réfute** la thèse de lenteur : les engagements énergie ont
quadruplé après le JETP, et ils décaissent plus vite que la référence. Mais
la quasi-totalité de ce décaissement rapide est de l'appui budgétaire (KfW,
93-97 % à un an ; Banque mondiale, ~98 %). Le seul vrai prêt-projet du
portefeuille, le *Eskom Just Energy Transition Project* de la Banque
mondiale (472,4 M USD), a décaissé **1,1 M USD — 0,2 %** à un an. En Indonésie,
les prêts JETP type projet (188,9 M USD) sont à **0,0 %** à un an, contre
94,5 % pour l'appui budgétaire.

**L'implication pour le lecteur.** Le chiffre agrégé « moins de 5 %
décaissé » que la presse et les ONG citent mélange les deux modalités et
laisse croire à une lenteur générale d'exécution. Décomposé, il dit autre
chose : la transformation productive promise — centrales fermées, réseaux
construits — passe par le financement de projet, et c'est précisément celui
qui ne décaisse pas. L'appui budgétaire, qui décaisse vite, ne finance pas
cette transformation ; il finance des réformes de politique.

**Where this sits relative to the long paper.** Ce résultat ne dépend pas du
mécanisme macro (solvabilité/agentivité) développé dans le papier long : il
tient sur la seule décomposition CRS. Le papier court le présente comme la
mesure centrale, avec un paragraphe (pas une section) renvoyant au mécanisme
macro pour l'explication de fond — pourquoi les bailleurs ont substitué
l'appui budgétaire au financement de projet sans le dire, à savoir que
l'appui budgétaire ne teste jamais la capacité d'absorption d'un bilan,
puisqu'il décaisse contre des conditions de politique et non contre des
tirages sur travaux.

## Plan détaillé

Structure resserrée sur une mesure, pas sur la comparaison à quatre
dimensions du papier long :

1. **Le fait** — la promesse (2,5-20 Md USD par pays selon les 4 JETP), le
   chiffre agrégé cité par la presse (« moins de 5 % décaissé »), et
   pourquoi ce chiffre seul ne dit rien sur la cause.
2. **Méthode** — construction de la courbe de référence : OCDE CRS
   microdonnées, dataflow `OECD.DCD.FSD:DSD_CRS@DF_CRS(1.6)`, secteur énergie
   (28 codes objet 230xx), 4 pays JETP (Afrique du Sud, Indonésie, Vietnam,
   Sénégal), cohortes d'engagement 2006-2020, appariement au niveau activité
   via `(DONOR, DONOR_PROJECT_ID)`.
3. **Résultat 1 — la référence existe et elle est nette** : 37,3 % pondéré à
   4 ans, très dispersée par cohorte (Q1 13,0 % · médiane 50,4 % · Q3 84,8 %).
4. **Résultat 2 — la substitution d'instrument** : décomposition par
   modalité CRS (A01/A02 vs C01), avec le cas sud-africain et indonésien
   comme démonstration a fortiori (l'agrégat réfute, la modalité confirme).
5. **Résultat 3 — le goulot vietnamien est à l'engagement, pas au
   décaissement** : effondrement des engagements ODA énergie de 393,9 M USD/an
   à 40,9 M USD/an, antérieur de 4 ans au JETP (sortie de l'éligibilité IDA en
   2018) — réserve de causalité à écrire explicitement.
6. **Réponse à l'objection du referee** (« à 4 ans sur un instrument à
   15-20 ans, moins de 5 % est peut-être normal ») — la courbe normale n'est
   pas plate, et le dénominateur des 37 % (engagement CRS signé) est déjà
   généreux pour le JETP (promesse politique) : comparaison au même stade
   impossible faute d'engagements signés en volume au Vietnam.
7. **Annexe comptable** — engagé/alloué/signé/approuvé/décaissé, par source
   et par tranche, retrait américain de mars 2025 traité au numérateur et au
   dénominateur. Réclamée par 7/7 éditeurs simulés du papier long ; portée
   ici, citée là-bas.
8. **Conclusion, un paragraphe** — renvoi au mécanisme macro du papier long
   pour l'explication structurelle, sans le redévelopper.

Longueur cible : **7 000 mots** (coupe Research Article pour Climate
Policy — voir Stratégie de publication). Une variante à 5 000 mots
(Policy Analysis) a été envisagée et écartée : elle mise tout le papier sur
une seule mesure sous un régime à relecteur unique, sans gain net de
probabilité une fois la courbe déjà construite.

## Données et analyses nécessaires

**Déjà produites** (2026-09-08, `courbe-reference-decaissement-2026-09-08.md`
+ `.csv`, scripts dans `analyse-crs/`) :

- Tirage CRS complet, 4 pays, secteur énergie, 2005-2024.
- Courbe de référence pondérée et par pays, cohortes 2006-2020.
- Décomposition par modalité CRS (A01/A02 vs C01), les cinq activités
  sud-africaines nommées avec montant et taux de décaissement à un an.
- Série des engagements ODA énergie Vietnam 2006-2024 (annuelle).

**Restant à faire avant rédaction** :

- **Annexe comptable complète** (point 7 du plan) — pas encore construite
  comme livrable séparé, seulement esquissée par pays dans le bloc I du
  papier long. Réutilisable telle quelle si construite une fois pour les
  deux papiers.
- **Vérifier le format exact accepté par Climate Policy** pour une coupe à
  7 000 mots Research Article — le plafond de 8 000 mots (Synthesis) est
  vérifié à la source, la variante Research Article à confirmer.
- **Anonymisation** : Climate Policy exige un manuscrit anonymisé identique
  au nominatif — le dépôt HAL doit sortir complètement du texte (7/7
  éditeurs simulés le demandent de toute façon, voir le papier long).
- **Vérifier qu'aucun tirage CRS équivalent n'existe déjà** ailleurs dans mes
  projets en cours avant tout nouveau tirage pour l'annexe comptable ou une
  extension à d'autres pays.

## Résultats préliminaires

Voir Idée de recherche ci-dessus pour les chiffres — ils constituent déjà le
cœur du papier, pas une collecte préparatoire. En synthèse, du plus solide au
plus fragile :

1. La référence de décaissement existe, dépasse largement 5 %, et est très
   dispersée (solide — mesure directe, grand échantillon).
2. La substitution d'instrument explique l'essentiel de l'écart apparent,
   démontrée a fortiori par le cas sud-africain qui réfute la thèse en
   agrégat (solide — mécanisme identifié et quantifié par activité nommée).
3. Le goulot vietnamien est antérieur au JETP de 4 ans (solide comme fait,
   la part imputable au JETP — son échec à l'inverser — reste à argumenter
   dans le texte, pas seulement à mesurer).
4. La thèse tient contre la tendance centrale, pas contre le pire cas : à
   l'activité, le premier quartile est à 0 % à 4 ans, trois cohortes
   vietnamiennes et un bailleur entier (JBIC, 498 M USD) sont proches de 0 % —
   concession à écrire explicitement (fragile si omise : un referee la
   trouvera).

## Stratégie de publication

**Cible : *Climate Policy* (Taylor & Francis), coupe à 7 000 mots, Research
Article.** Verdict de l'éditeur simulé (passe du 2026-09-08, sept revues) :
desk 55 %, acceptation 33 %, combiné **≈ 18 %** — et surtout, **33 jours de
première décision, le seul délai de tout le tableau à sept revues vérifié à
la source** (page de métriques de la revue), contre des délais de 3 à 6,6
mois partout ailleurs (auto-déclarés SciRev, effectifs dérisoires).

C'est le résultat qui a tranché la scission court/long : le principe posé en
séance était que **le papier court n'existe que si la courbe de référence
montre un écart net** (règle pré-enregistrée : ~40 % de référence contre
~5 % JETP → papier court justifié ; ~8 % de référence → pas de papier
court, et la mesure centrale du papier long est elle-même fragilisée). La
courbe construite le soir même a tranché dans le sens favorable — 37,3 %
contre 9 %, facteur 5,3.

Trois raisons de partir vite et indépendamment :

- **Vitesse.** 20 à 33 jours de premier retour contre plusieurs mois pour le
  papier long ; le court peut circuler en une semaine de rédaction.
- **Priorité.** Deux préprints concurrents (Do et al., avril 2026 ; Kruger
  et al., 3 septembre 2026) menacent la mesure, pas l'analyse politique.
  Publier la mesure vite protège précisément ce qui est contesté.
- **Indépendance.** Ce papier ne dépend d'aucune tierce disponibilité — la
  matière est entièrement produite et entièrement due à Minh.

Repli non nécessaire à ce stade : la variante Global Environmental Change
« courte » a été examinée et écartée — son seul format sous 8 000 mots (la
Perspective à 3 000 mots) exclut explicitement les papiers à description
méthodologique, donc exclut précisément ce papier.

**Convergences à respecter** (issues du panel à sept revues, valables même
si la cible change) : sortir toute référence au dépôt HAL du texte
(anonymisation, condition stricte chez Climate Policy) ; présenter la courbe
de référence comme le contrefactuel, pas seulement la mesure ; annexe
comptable complète par source et tranche.

## Répartition des rôles

**Minh, premier auteur, seul jusqu'à publication ou décision contraire.**
C'est la comptabilité et la courbe de référence, produites par Minh (avec
agents délégués pour le tirage et la mise en forme des données) ; le papier
ne dépend pas de la disponibilité de Christophe. Proposition actée en
séance : Christophe relit s'il le souhaite, sans obligation de calendrier ni
de contribution de fond.

À noter : Ha-Duong est déjà auteur publié en solo dans *Climate Policy*
(*Power system...*, référence exacte à vérifier dans le CR complet) — un
antécédent qui joue positivement sur cette cible.
