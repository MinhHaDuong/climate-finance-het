<!-- Atterri depuis ~/CNRS/projets/actifs/jetp/papier-court-mesure/courbe-reference-decaissement-2026-09-08.md (ticket 0712, 2026-09-11).
     Contenu inchangé par rapport à la source, hors ce bandeau.
     Matériau de conception pour les papiers JETP (tracker 0708) —
     pas encore câblé dans un livrable. -->
# Courbe de référence du décaissement : le JETP contre le portefeuille énergie d'avant le JETP

Calcul du 8 septembre 2026. Source : OCDE CRS, **microdonnées d'activité**,
dataflow `OECD.DCD.FSD:DSD_CRS@DF_CRS(1.6)`, secteur énergie (28 codes objet
230xx), pays Afrique du Sud, Indonésie, Viêt Nam, Sénégal, années 2005-2024.
Scripts, données brutes et sorties intermédiaires : `analyse-crs/`.
Données du graphique : `courbe-reference-decaissement-2026-09-08.csv`.

---

## Verdict

**L'écart est significatif au Viêt Nam et en Indonésie, d'un facteur trois à
quatre. Il est inexistant — et même inversé — en Afrique du Sud. La thèse
d'un défaut de conception uniforme du JETP, mesurée par le seul taux de
décaissement, ne tient pas ; la même mesure, décomposée par modalité,
en fournit une version plus forte.**

Trois résultats, du plus solide au plus fragile.

### 1. La référence existe, elle est bien au-dessus de 5 %, et elle est très dispersée

Prêts concessionnels au secteur énergie, interventions de type projet,
cohortes d'engagement 2006-2020, quatre pays JETP groupés — **le contrôle
demandé : mêmes pays, mêmes bailleurs, même secteur, même capacité
d'absorption, seul l'instrument diffère**.

| horizon | 0 an | 1 an | 2 ans | 3 ans | **4 ans** |
|---|---|---|---|---|---|
| taux décaissé cumulé, pondéré | 9,3 % | 18,5 % | 26,1 % | 31,7 % | **37,3 %** |

n = 121 activités, 12 705 M$ engagés (constants 2024).

Par pays à quatre ans : Viêt Nam **47,5 %**, Sénégal **46,1 %**,
Afrique du Sud **44,2 %**, Indonésie **19,0 %**.

Dispersion entre les 15 cohortes annuelles : min 0,0 · **médiane 41,5** ·
max 80,9 · écart-type **24,7 points**.
Dispersion entre activités : Q1 **0,0 %** · **médiane 22,1 %** · Q3 68,6 %.

**Le chiffre unique serait un mensonge.** Un projet isolé à 5 % de
décaissement à quatre ans est dans le premier quartile de la référence,
c'est-à-dire banal. C'est au niveau du *portefeuille*, pondéré par les
montants, que la référence se situe à 37 % — et c'est le bon niveau, puisque
le JETP est une promesse de portefeuille.

### 2. Le Viêt Nam : écart d'un facteur quatre, et une thèse qui doit se déplacer vers l'amont

| | taux à 4 ans |
|---|---|
| Référence Viêt Nam — prêts énergie type projet, engagements 2006-2020 | **47,5 %** (45 activités, 5 350 M$) |
| Dispersion, cohortes annuelles vietnamiennes | min 0,0 · Q1 13,0 · médiane 50,4 · Q3 84,8 · max 93,5 |
| **JETP Viêt Nam** — décision 1929/QĐ-BCT du MOIT, 29 juillet 2026 : ~800 M$ mobilisés sur 8,08 Md$ de part publique | **~9 %** |

Facteur **5,3** ; le JETP se situe autour du **10ᵉ-15ᵉ centile** de la
distribution historique vietnamienne. L'écart est réel.

Mais le résultat le plus net n'est pas là. **Le goulot vietnamien est à
l'engagement, pas au décaissement.** Engagements de prêts ODA énergie
déclarés au CRS, moyenne annuelle en M$ constants 2024 :

| pays | 2006-2020 | 2022-2024 | rapport |
|---|---|---|---|
| **Viêt Nam** | 393,9 | **40,9** | **0,10** |
| Afrique du Sud | 147,9 | **593,2** | **4,01** |
| Indonésie | 317,7 | 237,4 | 0,75 |
| Sénégal | 79,7 | 32,1 | 0,40 |

Sur 2022-2024, **une seule activité de prêt ODA énergie par an** est déclarée
au Viêt Nam (92,7 M$ en 2022, 30,0 M$ en 2023, 0 en 2024), face à une promesse
de 15,8 Md$. Un taux de décaissement mesure la vitesse d'un tuyau ; au Viêt
Nam le tuyau n'a pas été ouvert.

**Réserve qui doit être écrite** : cet effondrement commence en 2018, quatre
ans *avant* le JETP, et coïncide avec la sortie du Viêt Nam de l'éligibilité
IDA (2017). Il n'est pas imputable au JETP. Ce qui l'est, c'est de ne l'avoir
pas inversé.

### 3. L'Afrique du Sud contredit la thèse — jusqu'à ce qu'on regarde la modalité

En Afrique du Sud, les engagements énergie ont **quadruplé** après le JETP,
et ils décaissent **plus vite** que la référence : cohorte 2021-2023, toutes
modalités projet, 1 503 M$, 44,9 % dès l'année d'engagement, 51,8 % à un an —
contre 16,4 % et 26,3 % pour la référence sud-africaine. Pris au pied de la
lettre, ce cas **falsifie** la thèse.

Il ne la falsifie pas, parce que ce n'est pas le même produit. La ventilation
par modalité CRS le montre sans ambiguïté :

| modalité, 4 pays groupés, 2006-2020 | h=0 | h=1 | h=2 | h=3 | h=4 |
|---|---|---|---|---|---|
| prêts ODA, **appui budgétaire** (A01/A02) | 63,9 % | **98,6 %** | 98,6 % | 98,6 % | 98,6 % |
| prêts ODA, **type projet** (C01) | 9,3 % | 18,5 % | 26,1 % | 31,7 % | 37,3 % |

Un prêt d'appui budgétaire décaisse en une ou deux tranches contre le respect
de déclencheurs de réforme : il est **structurellement instantané**. Ce que
le JETP sud-africain a effectivement décaissé relève de cette catégorie :

| activité engagée 2022-2023 | montant | modalité | décaissé à 1 an |
|---|---|---|---|
| KfW — *Policy Reform Loan to support the Just Energy Transition II* | 557,6 M$ | A02 | 97,0 % |
| KfW — *Reform-FöK zur Unterstützung der Just Energy Transition* | 356,9 M$ | A02 | 93,7 % |
| AFD — *JET Sudafricain* | 347,8 M$ | C01 | **100,0 %** |
| BM — *Sustainable and Low-Carbon Energy Transition Development Policy Loan* | 384,0 M$ | A02 | ~98 % |
| **BM — *Eskom Just Energy Transition Project*** | **472,4 M$** | **C01** | **0,2 %** |

L'AFD est codée C01 mais décaisse 100 % l'année même : opération d'appui, non
de projet. **La seule vraie opération de projet du portefeuille JETP
sud-africain, le projet Eskom de la Banque mondiale, a décaissé 1,1 M$ sur
472,4 M$ en un an — 0,2 %.** En Indonésie, les prêts JETP de type projet
(188,9 M$, 4 activités) sont à **0,0 % à un an**, tandis que les 417,3 M$
d'appui budgétaire sont à 94,5 %.

**C'est là l'argument de conception, et il est mesurable.** Le JETP n'a pas
échoué à décaisser : il a décaissé de l'appui budgétaire à la vitesse
habituelle de l'appui budgétaire, et n'a pratiquement rien décaissé en
financement de projet. La transformation productive promise passe par le
second ; le chiffre de « moins de 5 % » agrège les deux et laisse croire à une
lenteur générale là où il y a **substitution d'instrument**.

### Réponse directe à l'objection du referee

> « À quatre ans, sur des instruments à horizon quinze à vingt ans, moins de
> 5 % décaissé décrit peut-être simplement la courbe normale du prêt
> concessionnel d'infrastructure. »

Non, pas au niveau du portefeuille : le portefeuille énergie de ces quatre
mêmes pays, avec ces mêmes bailleurs, avant le JETP, décaissait **37 % de ses
engagements en quatre ans**, et **47 % au Viêt Nam**. La courbe normale n'est
pas plate.

Mais l'objection est partiellement fondée, et il faut le concéder :
au niveau de l'activité, la médiane est à 22 % et le premier quartile à 0 % ;
trois cohortes annuelles vietnamiennes (2006, 2007, 2017) et un bailleur
entier (JBIC, 498 M$) sont à ~0 % à quatre ans. **La thèse tient contre la
tendance centrale, pas contre le pire cas** ; écrire « le JETP est plus lent
que tout ce qu'on a observé » serait faux.

Enfin, un point de méthode qui joue en faveur de la thèse et qu'il faut
énoncer : le dénominateur des 37 % est un **engagement CRS**, accord signé et
contraignant ; celui des 9 % est une **promesse politique**. La comparaison
est déjà généreuse pour le JETP, puisqu'elle lui compte comme franchie
l'étape promesse → engagement. Mesuré au même stade, le JETP vietnamien n'est
pas mesurable, faute d'engagements signés en volume.

---

## Méthode

### Données et tirage

Microdonnées d'activité du CRS via l'API SDMX de l'OCDE, endpoint
`https://sdmx.oecd.org/dcd-public/rest/data/`. Les lignes `MD_DIM = DD`
portent les identifiants d'activité (`DONOR_PROJECT_ID`, `OECD_ID`), le titre
du projet, l'agence, la modalité et le type de financement. Une ligne = une
activité × année × type de flux (`C` engagement, `D` décaissement) × mesure ×
base de prix.

Prix constants base 2024 (`PRICE_BASE = Q`) : le ratio compare des montants de
millésimes différents. Les prix courants ont été testés et ne changent pas les
conclusions.

Reproduction :

```bash
cd analyse-crs
python3 pull_crs.py --outdir data --start 2005 --end 2024 --md-dim DD --pause 20
python3 cohortes.py --out-csv out/cohortes_bloc.csv --out-act out/activites.csv
python3 livrable_csv.py --out ../courbe-reference-decaissement-2026-09-08.csv
python3 final.py --out out/reference_groupee.csv          # tableau de synthèse
python3 synthese.py --act out/activites.csv --pays VNM    # dispersion détaillée
```

L'API OCDE limite le débit (HTTP 429) : `--pause 20` est nécessaire pour un
tirage complet.

### L'appariement au niveau activité a été possible

C'est le point qui décide de la qualité de tout le reste, et **aucun proxy
agrégé n'a été nécessaire**. Clé retenue : `(DONOR, DONOR_PROJECT_ID)`.

| pays | lignes | activités | part de la valeur engagée portant un `DONOR_PROJECT_ID` |
|---|---|---|---|
| Viêt Nam | 2 486 | 698 | **99,8 %** |
| Indonésie | 2 716 | 814 | **99,8 %** |
| Sénégal | 1 356 | 459 | 95,4 % |
| Afrique du Sud | 1 471 | 599 | 95,0 % |

Au Viêt Nam, 397 activités portent à la fois engagements et décaissements, et
80,3 % de la valeur engagée est appariée à au moins un décaissement. Le ratio
calculé est donc un vrai rapport décaissements/engagements **de la même
activité**, non un rapport de deux agrégats décalés dans le temps.

L'alternative `(DONOR, OECD_ID)` a été testée et rejetée : `OECD_ID` est
préfixé par l'année de déclaration et n'est stable d'une année sur l'autre que
pour 13,3 % des activités, contre 39,3 % pour `DONOR_PROJECT_ID`.

### Définitions

- **Cohorte** : année *T* du premier engagement (`FLOW_TYPE = C`) de l'activité.
- **Dénominateur** : somme des engagements de l'activité sur toute la fenêtre.
  Variante testée — engagement de la seule année *T* : **résultats identiques
  au dixième de point** pour les prêts énergie, les activités n'étant engagées
  qu'une fois.
- **Numérateur à l'horizon *h*** : décaissements cumulés des années *T* à *T+h*
  incluses. *h* = 4 recouvre donc cinq années civiles, celle de l'engagement
  comprise.
- **Instrument** : mesure CRS dominante des engagements — `11` dons ODA,
  `13` prêts ODA, `14`/`19` autres apports officiels, `30`/`60` financement
  privé.
- **Modalité** : code CRS dominant des engagements — `C01` interventions de
  type projet, `A01`/`A02` appui budgétaire général et sectoriel, `D01`/`D02`
  assistance technique, `B0x` fonds et contributions.
- **Censure à droite** : une cellule (cohorte, *h*) n'inclut que les activités
  dont *T+h* ≤ 2024, dernière année CRS disponible. Le nombre d'activités
  exclues figure dans le CSV (`activites_exclues_censure`).

### Dons contre prêts

Le comparateur les distingue, comme demandé, et le résultat est
contre-intuitif : à quatre ans, sur les quatre pays groupés et en type projet,
les **dons** décaissent 50,7 % contre 37,3 % pour les **prêts**. L'explication
est de composition : les dons énergie sont nombreux (572), petits (1,9 M$ en
moyenne) et souvent liés à de l'assistance technique achevée rapidement ; les
prêts sont peu nombreux (121), gros (105 M$) et adossés à des chantiers. Cet
écart va dans le sens de la thèse — le JETP est majoritairement du prêt — mais
il interdit d'écrire que « les prêts décaissent plus vite que les dons ».

---

## Limites — à lire avant de citer un chiffre

1. **Le chiffre JETP de 9 % n'est pas calculé ici.** Il provient de la décision
   1929/QĐ-BCT du MOIT (29 juillet 2026). Le CRS ne permet pas de le
   recalculer : le JETP n'y est pas identifiable comme instrument — le pilote
   d'août 2026 avait déjà établi que 2 activités sur 485 mentionnent « JETP »
   dans IATI. Toute comparaison JETP ↔ CRS croise deux nomenclatures qui ne se
   recouvrent pas.
2. **Les dénominateurs ne sont pas de même nature** (promesse politique contre
   engagement signé). C'est la limite la plus lourde ; elle joue en faveur de
   la thèse, et doit être énoncée plutôt que dissimulée.
3. **Effectifs faibles sur les cohortes récentes et sur certains pays.**
   Afrique du Sud : 2 activités de prêt type projet sur 2021-2023. Sénégal :
   aucune sur la cohorte JETP. Indonésie : 4. Les taux JETP par instrument
   reposent sur des poignées de projets et ne sont pas des tendances.
4. **Censure à droite.** Aucune cohorte postérieure à 2020 n'est observable à
   quatre ans dans le CRS (dernière année 2024). La cohorte JETP n'est
   observable qu'à *h* = 2 au plus. La comparaison à quatre ans repose
   entièrement sur la source vietnamienne (MOIT).
5. **Défauts de déclaration.** JBIC déclare 498 M$ d'engagements au Viêt Nam et
   0,4 % de décaissements à quatre ans : c'est très probablement une
   sous-déclaration des décaissements, non un décaissement réellement nul. Les
   cas extrêmes bas de la distribution doivent être lus « lent **ou** mal
   déclaré », ce qui affaiblit l'usage du pire cas comme borne inférieure.
6. **Codes objet énergie : pas de rupture de série sectorielle.** Vérifié
   empiriquement — une requête sur les codes hérités d'avant la refonte 2016
   (23010-23082) renvoie `NoRecordsFound` sur 2010-2014 : l'OCDE a
   rétro-appliqué la nomenclature actuelle. Il subsiste une rupture de
   *contenu* : les sous-codes solaire et éolien fins n'existaient pas avant
   2016 et les activités antérieures ont été reclassées par l'OCDE, avec
   l'incertitude que cela comporte.
7. **Activités décaissant sans engagement identifié.** 219 activités
   vietnamiennes portent des décaissements sans engagement dans la fenêtre
   (engagement antérieur à 2005, ou identifiant absent). Exclues du calcul —
   correct pour un ratio par cohorte, mais le total décaissé du secteur excède
   le numérateur utilisé ici.
8. **Restriction aux bailleurs du GPI non appliquée.** Prévue, non faite. La
   ventilation par bailleur (`analyse-crs/out/vnm_bailleurs_h4.csv`) montre que
   restreindre à JICA / KfW / AFD / BEI / UE déplacerait la référence
   vietnamienne dans une fourchette de 25 à 72 %, sans jamais l'approcher
   de 9 %.
9. **Ratios supérieurs à 100 %.** Quelques cellules dépassent 100 % (change,
   révisions d'engagement, décaissements sur tranches antérieures). Ils sont
   plafonnés à 500 % au niveau de l'activité pour les statistiques de
   dispersion, et laissés bruts dans les taux pondérés.

---

## Fichiers

| fichier | contenu |
|---|---|
| `courbe-reference-decaissement-2026-09-08.csv` | 937 lignes : pays × cohorte × périmètre × horizon, taux pondéré + médiane/Q1/Q3 inter-activités |
| `analyse-crs/pull_crs.py` | tirage SDMX des microdonnées CRS |
| `analyse-crs/cohortes.py` | reconstitution des activités et profils par cohorte |
| `analyse-crs/livrable_csv.py` | génération du CSV livrable |
| `analyse-crs/final.py` | tableau de synthèse par pays × périmètre |
| `analyse-crs/synthese.py` | dispersion par cohorte annuelle et par bailleur |
| `analyse-crs/data/` | 80 tirages bruts (4 pays × 20 ans), gzip |
| `analyse-crs/out/activites.csv` | 1 791 activités reconstituées — table d'audit |
| `analyse-crs/out/reference_groupee.csv` | référence groupée par pays et périmètre |
| `analyse-crs/out/vnm_bailleurs_h4.csv`, `out/zaf_bailleurs_h4.csv` | ventilation par bailleur |
