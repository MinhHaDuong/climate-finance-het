<!-- Atterri (ticket 0709, 2026-09-10), matériau de conception pour un
     livrable futur (0711) — pas encore câblé. Composé depuis
     `jetp-cr-reunion-2026-09-08.md` et les notes empiriques du 2026-09-08 de
     ~/CNRS/projets/actifs/jetp/papier-court-mesure/ ; contenu redistribué et
     recadré sur le périmètre du papier court, pas une simple copie. -->

# Papier court — mesure et mécanisme (JETP)

Titre de travail : *How slow is slow? Benchmarking Just Energy Transition
Partnership disbursement against comparable concessional energy lending*.

Second volet, avec le papier long d'économie politique comparée
(`jetp-papier-long-economie-politique.md`), d'un papier unique reformulé le
2026-09-08 en réunion avec Christophe Cassen (CR complet :
`jetp-cr-reunion-2026-09-08.md`).

*Titre arrêté le 2026-09-11, sur deux principes.* Le précédent (« the
disbursement gap is instrument substitution, not delay ») était construit en
ressort — un « ce n'est pas X, c'est Y » qui promeut l'explication en
manchette. **L'explication n'est pas la mesure** : la substitution
d'instrument reste dans le corps. Et la contribution est l'étalon lui-même,
qui n'existait pas — il permet de dire si un taux de décaissement est lent.
Le titre n'asserte par ailleurs aucun écart uniforme, ce que la donnée ne
permettrait pas : à horizon apparié, l'Afrique du Sud et le Sénégal décaissent
au niveau de leur propre norme (voir Résultats).

## Idée de recherche

Le fait déclencheur : à quatre ans, le JETP vietnamien a décaissé **≈ 9 %**
de sa part publique, contre une référence de **37,3 %** pour un portefeuille
comparable de prêts concessionnels énergie (mêmes pays, mêmes bailleurs,
même secteur, cohortes d'engagement 2006-2020) — facteur **5,3**. Pris seul,
ce chiffre invite la lecture réflexe : le JETP est lent.

**Ce chiffre n'est pas le résultat. Le résultat est l'étalon et la séparation
qu'il impose entre paquet annoncé, engagement signé et décaissement.** À
horizon apparié, l'écart d'exécution n'apparaît que dans deux pays sur quatre ;
le résultat commun est en amont, puisque 60 à 98 % des paquets annoncés ne
deviennent jamais des engagements signés. La décomposition par modalité CRS
teste ensuite une explication — la substitution d'instrument — sans la
confondre avec la mesure :

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

Longueur cible : **moins de 5 000 mots**, format Policy Analysis chez
Climate Policy — une courbe, une explication (voir Stratégie de
publication).

*Arbitrage révisé le 2026-09-11.* Cette note portait 7 000 mots en Research
Article et écartait la Policy Analysis au motif qu'elle « mise tout le papier
sur une seule mesure sous un régime à relecteur unique ». Le 7 000 n'était
pas la longueur du papier court : c'est celle du papier *long* comprimé pour
entrer chez Climate Policy, un scénario dont la note de ciblage dit qu'il
« ne survit pas à la coupe en tant que ce qu'il est devenu ». Quant au motif
du rejet, il valait sous l'hypothèse d'un manuscrit unique : depuis la
scission, le papier long porte les quatre affirmations, et la mono-thèse du
court cesse d'être une fragilité à couvrir.

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
- **Anonymisation** : Climate Policy exige un manuscrit anonymisé identique
  au nominatif — le dépôt HAL doit sortir complètement du texte (7/7
  éditeurs simulés le demandent de toute façon, voir le papier long).
- **Vérifier qu'aucun tirage CRS équivalent n'existe déjà** ailleurs dans mes
  projets en cours avant tout nouveau tirage pour l'annexe comptable ou une
  extension à d'autres pays.
- **La comparaison à quatre pays est faite** — figure 1 ci-dessous. Reste à
  en tirer la section d'interprétation, qui revient à Christophe.

## Résultats préliminaires

![Le décaissé du paquet annoncé, contre la norme d'exécution du
pays. Chaque panneau est lu au temps écoulé depuis la signature de son JETP, la
norme du pays y étant prise au même horizon. Deux dénominateurs : la
distribution rapporte le décaissé à l'engagement signé, la barre le rapporte au
paquet annoncé — l'écart entre les deux mesure ce qui n'a jamais quitté
l'annonce.](jetp/papier-court-mesure/figure-distribution-decaissement.pdf)

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
5. **Le goulot est à l'engagement, pas au décaissement, et cela vaut pour les
   quatre pays.** La part du paquet annoncé jamais transformée en engagement
   signé atteint 98 % au Viêt Nam, 91 % au Sénégal, 89 % en Indonésie et 60 %
   en Afrique du Sud. La note d'août ne l'établissait que pour le Viêt Nam.
6. **À horizon apparié, l'écart d'exécution ne tient qu'à moitié.** Rapporté au
   paquet annoncé et pris au temps réellement écoulé depuis chaque signature :
   Viêt Nam 1,1 % contre une norme de 25,8 % à deux ans, Indonésie 5,4 % contre
   25,5 % — écarts nets ; Afrique du Sud 26,2 % contre 30,5 % à trois ans,
   Sénégal 7,2 % contre 7,2 % à un an — au niveau de leur norme. **Le papier ne
   peut donc pas asserter un écart uniforme** (fragile si omis : la figure 1 le
   montre).
7. **Trois spécifications, trois réponses — et c'est un résultat.** Le
   chiffre-titre s'est déplacé deux fois pendant la construction, selon les
   instruments retenus (s'en tenir à l'APD excluait les prêts IBRD, donc
   l'*Eskom Just Energy Transition Project*), le dénominateur (engagement signé
   ou paquet annoncé) et l'horizon (uniforme ou apparié aux signatures). Une
   mesure aussi sensible à sa spécification justifie que le papier porte sur
   l'étalon plutôt que sur un chiffre.

## Stratégie de publication

**Cible : *Climate Policy* (Taylor & Francis), Policy Analysis, moins de
5 000 mots.** Verdict de l'éditeur simulé (passe du 2026-09-08, sept
revues) : desk 60 %, acceptation 35 %, combiné **≈ 21 %** — le meilleur des
sept revues évaluées — et surtout, **33 jours de première décision, le seul
délai de tout le tableau à sept revues vérifié à la source** (page de métriques de la revue), contre des délais de 3 à 6,6
mois partout ailleurs (auto-déclarés SciRev, effectifs dérisoires).

C'est le résultat qui a tranché la scission court/long : le principe posé en
séance était que **le papier court n'existe que si la courbe de référence
montre un écart net** (règle pré-enregistrée : ~40 % de référence contre
~5 % JETP → papier court justifié ; ~8 % de référence → pas de papier
court, et la mesure centrale du papier long est elle-même fragilisée). La
courbe construite le soir même a tranché dans le sens favorable — 37,3 %
contre 9 %, facteur 5,3.

Trois raisons de partir vite avec un calendrier borné :

- **Vitesse.** 20 à 33 jours de premier retour contre plusieurs mois pour le
  papier long ; le court peut circuler en une semaine de rédaction.
- **Priorité.** Deux préprints concurrents (Do et al., avril 2026 ; Kruger
  et al., 3 septembre 2026) menacent la mesure, pas l'analyse politique.
  Publier la mesure vite protège précisément ce qui est contesté.
- **Calendrier maîtrisable.** La matière quantitative est entièrement
  produite par Minh ; la contribution de Christophe est bornée à une section
  d'interprétation, aux *key policy insights* et à une passe de validation,
  avec une date de soumission fixée d'avance.

Repli non nécessaire à ce stade : la variante Global Environmental Change
« courte » a été examinée et écartée. Son seul format sous 8 000 mots, la
Perspective à 3 000 mots, est réservé au point de vue prospectif et
explicitement fermé aux papiers *nécessitant une description
méthodologique*. La courbe de référence est une observation empirique ; ce
qui la rend inéligible à ce format, ce n'est pas sa nature, c'est qu'elle
n'est crédible qu'accompagnée du détail de sa construction. **Les 3 000 mots
envisagés en séance n'ont donc jamais été disponibles chez GEC** — ce n'est
pas un arbitrage rendu contre la position de la réunion, c'est une option qui
n'existait pas.

Chez Climate Policy en revanche, les quatre formats sont vérifiés à la
source : Research Article 7 000, Synthesis 8 000 (réservé aux revues de
l'état des connaissances), Policy Analysis 5 000, Debate/Viewpoint 3 000 —
références exclues, figures et tableaux comptés 250 mots la demi-page et 500
la page pleine. Le format à 3 000 y est un format de commentaire, pas un
véhicule pour un résultat empirique original.

**Convergences à respecter** (issues du panel à sept revues, valables même
si la cible change) : sortir toute référence au dépôt HAL du texte
(anonymisation, condition stricte chez Climate Policy) ; présenter la courbe
de référence comme le contrefactuel, pas seulement la mesure ; annexe
comptable complète par source et tranche.

**Condition propre au format retenu** : déposer la chaîne de tirage CRS en
données supplémentaires. Sous la Policy Analysis, la seule surface d'attaque
du papier est la construction de la référence — population de prêts
concessionnels énergie, fenêtre, correction du décalage engagement-signature.
Bricolée, le relecteur unique la démolit ; déposée et ré-exécutable, elle se
défend.

## Répartition des rôles

**Minh premier auteur et corresponding ; Christophe coauteur.** Décision de
l'auteur du 2026-09-11, qui révise la proposition actée en séance (« Minh
seul, Christophe relit s'il le souhaite, sans contribution de fond »).

**Le rôle proposé n'est pas une relecture requalifiée : il est appelé par le
format et par la comparaison à quatre pays.** La Policy Analysis de Climate
Policy est définie comme une *evidence-based objective analysis of particular
policy approaches* — la couche d'analyse de politique publique est
constitutive du format, pas un ornement. Et la comparaison à quatre pays
ouvre précisément les questions auxquelles la mesure ne répond pas :
pourquoi 60 à 98 % des paquets ne sont jamais devenus des engagements signés,
pourquoi l'Indonésie décaisse cinq fois moins que sa norme quand l'Afrique du
Sud tient la sienne, et ce que la substitution vers l'appui budgétaire
dit de la pratique réelle des bailleurs. C'est le terrain de Christophe.

Proposition au standard CRediT, à valider ou corriger par lui :

| Rôle CRediT | Contributeur |
|---|---|
| Conceptualization | **Conjoint** — l'étalon et le dispositif de mesure (Minh) ; la question à laquelle l'étalon sert à répondre, et la lecture institutionnelle de l'hétérogénéité (Christophe) |
| Methodology, Software, Formal analysis, Data curation | Minh |
| **Investigation** | **Christophe** — la matière qui explique l'hétérogénéité entre pays, et qui n'est pas dans le CRS : pourquoi 60 à 98 % des paquets annoncés ne sont jamais devenus des engagements signés, ce que fait réellement l'opération AFD « JET Sudafricain » qui décaisse 348 M USD l'année même de son engagement, quelle pratique de bailleur produit la substitution vers l'appui budgétaire. Travail de terrain documentaire, pas de relecture. |
| Writing – original draft | Minh : mesure, méthode, résultats. **Christophe : la section d'interprétation** — pourquoi l'écart varie, ce qui se conclut pour la conception des plateformes-pays — **et les 3 à 5 *key policy insights*** exigés par la revue. Section nommée, pas des commentaires en marge. |
| Validation | Les deux |
| Writing – review & editing | Les deux |
| Visualization | Minh |
| Corresponding author | Minh |

Sans la section d'interprétation et l'investigation qui la nourrit, le papier
reste une note de mesure et perd son format : la Policy Analysis suppose une
analyse, pas seulement un étalon. **L'ordre des signatures se rediscute sur ce
mérite** si la contribution de Christophe s'avère à la hauteur de ce tableau ;
la proposition de départ reste Minh premier auteur.

**Le coût, énoncé plutôt que tu.** L'indépendance de calendrier était l'une
des trois raisons de partir court et vite ; un coauteur la réintroduit. La
contrepartie proposée : un périmètre borné — une section, les key policy
insights, une passe de validation — et une date de soumission fixée d'avance,
le papier partant à cette date avec ce qui est prêt.

À noter : Ha-Duong est déjà auteur publié en solo dans *Climate Policy* —
*Power system planning in the energy transition era: the case of Vietnam's
power development plan 8*, 12 septembre 2024, pp. 562-577, DOI
10.1080/14693062.2024.2401857 — un antécédent qui joue positivement sur cette
cible.
