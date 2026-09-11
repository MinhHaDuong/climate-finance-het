<!-- Atterri depuis ~/CNRS/projets/actifs/jetp/papier-court-mesure/bloc1-absorbabilite-2026-09-08.md (ticket 0712, 2026-09-11).
     Contenu inchangé par rapport à la source, hors ce bandeau.
     Matériau de conception pour les papiers JETP (tracker 0708) —
     pas encore câblé dans un livrable. -->
# Le test d'absorbabilité ex ante des quatre JETP

Collecte sourcée pour instrumenter la thèse : *le paquet promis n'était pas absorbable par
le bénéficiaire, et personne ne l'a vérifié avant de le promettre.* Quatre pays, quatre
volets (souverain, opérateur, change, besoin), grandeurs disponibles **à la date de
signature de la déclaration politique**, ou l'exercice le plus proche disponible à cette
date quand la donnée elle-même est publiée plus tard.

**Discipline appliquée.** Chaque chiffre porte une source publique datée avec URL et date
de consultation (2026-09-08 pour l'ensemble de la collecte, sauf mention contraire dans le
CSV joint). Aucun chiffre n'est interpolé, estimé ou moyenné. Quand deux sources divergent,
les deux valeurs sont conservées avec leur périmètre exact. Ce qui n'a pas été trouvé est
noté comme tel, avec ce qui a été cherché. Le détail exhaustif (432 lignes de données de
recherche + 3 lignes de compléments, soit 435 lignes au total) est dans
`bloc1-absorbabilite-2026-09-08.csv` ; ce document en donne la synthèse et l'analyse.

**Avertissement méthodologique général.** Un nombre de rapport (« le paquet en % de X »)
marqué **[dérivé]** est un calcul de l'auteur sur des grandeurs publiées, pas une donnée
publiée telle quelle. Un « service de la dette additionnel implicite » qui supposerait un
taux, une maturité et un profil de tirage non publiés est marqué **non calculable sans
hypothèse non sourcée** dans les quatre dossiers pays : aucune des quatre déclarations
politiques ni des documents de cadrage qui les suivent ne publie les conditions financières
de l'enveloppe agrégée au moment de la signature.

---

## 1. Afrique du Sud — paquet de 8,5 Md$, signé le 2 novembre 2021 (COP26)

### Volet souverain

| Grandeur | Valeur | Source |
|---|---|---|
| PIB nominal 2021 | 420,0 Md$ (419 986 284 375 US$) | Banque mondiale, WDI `NY.GDP.MKTP.CD` |
| Paquet en % du PIB | **2,02 %** (base USD) [dérivé] | — |
| Dette externe totale 2021 | **169,4 Md$** (WDI) — **160,5 Md$** (SARB) ⚠️ divergence 8,9 Md$ | Banque mondiale WDI ; South African Reserve Bank |
| Paquet en % de la dette externe | **5,02 %** ou **5,30 %** selon la base [dérivé] | — |
| Dette publique brute (gouvernement national, hors Eskom), 2021/22 | **69,9 %** PIB (Trésor) — **70,7 %** (FMI) | National Treasury, MTBPS 2021 ; FMI CR 22/37 |
| Plafond légal de dette | **Aucun.** Ancre = plafond nominal de dépense primaire + trajectoire de stabilisation annoncée. Le FMI recommande un plafond en 2021 ; les autorités le refusent explicitement (« prefer to introduce it once there is more certainty ») | FMI CR 22/37 §30-32 |
| Trajectoire de dette annoncée vs projetée | Trésor : pic **78,1 %** en 2025/26 puis reflux — FMI : **88 %** en 2026 **sans stabilisation** (106 % en choc combiné) | MTBPS 2021 ; FMI CR 22/37, Annexe VIII |
| Verdict FMI (Article IV le plus proche) | **CR 22/37**, mission 17 nov.–7 déc. 2021 (deux semaines après la signature), publié févr. 2022 : « *debt is projected at 88 percent of GDP by 2026 and not expected to stabilize* » ; « *leave no buffers for fiscal policy to respond to any future adverse shocks* » | FMI, Country Report 22/37, Annexe VIII |
| Test de choc de change (DSA externe) | Une dépréciation de 30 % porterait la dette externe **au-delà de 58 % du PIB** (référence ~45 %) ; la moitié seulement de la dette externe est libellée en rand | FMI CR 22/37, Annexe VI §5 |
| Service de la dette additionnel implicite | **Non calculable sans hypothèse non sourcée** (conditions financières non publiées ; JET IP renvoie à une négociation future) | JET IP §5.7.2 |
| Repère : charge d'intérêt déjà existante | R278 md = **4,6 % du PIB** en 2021/22 ; « 21 cents de chaque rand de recettes » | FMI CR 22/37 ; National Treasury MTBPS 2021 |
| Structure réelle du paquet (connue 12 mois après signature) | **3,90 %** dons/AT ; **80,72 %** générateur de dette (prêts + garanties) | JET IP nov. 2022, Table 28 |

### Volet opérateur — Eskom (exercice clos 31 mars)

| Grandeur | Valeur | Source |
|---|---|---|
| Résultat net FY2021 | **−R18,9 md** (publié août 2021, connu à la COP26) — retraité **−R25,0 md** (déc. 2022) | Eskom AFS2021 ; AFS2022 note 48 |
| Résultat net FY2022 | **−R12,3 md** | Eskom AFS2022 |
| Opinion d'audit | **« Material uncertainty relating to going concern »** — sur les deux exercices FY2021 et FY2022 | Rapports d'audit AFS2021, AFS2022 |
| Dette financière brute | R401,8 md (31/03/2021) → R396,3 md (31/03/2022) | Eskom AFS2021, AFS2022 |
| Gross debt/EBITDA | **13,98×** (FY2021) → **8,63×** (FY2022) — catégorie *investment grade* typiquement < 4× | Eskom IR2022, « Solvency ratios » |
| Debt service cover | **0,30×** (FY2021) → 0,76× (FY2022) : le cash d'exploitation couvrait 30 % du service de la dette | Eskom IR2022 |
| Cash interest cover | 0,85× (FY2021) → 1,68× (FY2022) | Eskom IR2022 |
| Tarif vs coût — **variable centrale** | Le tarif couvre les coûts d'exploitation courants mais pas le coût complet (amortissement + charges financières) : déficit de **4,5 à 13 c/kWh** selon la mesure, sur un tarif de 111–127 c/kWh (**4 à 12 % du tarif**) [dérivé, aucun *cost of supply* complet publié] | Calcul de l'auteur sur Eskom IR2021/2022 |
| Manque à gagner réglementaire | **R102 md** de manque à gagner sur MYPD4 ; **R103 md** de contentieux tarifaire total en cours | Eskom IR2021, IR2022 |
| Statut tarifaire à la signature | **Aucun sentier tarifaire approuvé au-delà du 31 mars 2022** : NERSA rejette la demande MYPD5 en septembre 2021 ; Eskom attaque en justice | Eskom IR2022 |
| Subventions/garanties | Equity support R56,0 md (FY2021), **R31,7 md** (FY2022) ; facilité de garantie R350 md, utilisée à R281,6 md (mars 2021) ; portefeuille de garanties R693,7 md (2020) → R789,8 md (2021) | Eskom AFS ; National Treasury MTBPS 2021 |
| Capacité d'endettement additionnelle | Verbatim directors' report (26/08/2021, 10 semaines avant la signature) : « *the taxpayer cannot continue to subsidise the electricity consumer* […] *the only way to achieve [sustainability] remains through cost-reflective tariff or a take-over of debt* » | Eskom AFS2021 |
| **Évolution documentée (postérieure)** | Interdiction d'emprunter faite à Eskom suite au plan de sauvetage budgétaire de **février 2023** : les bailleurs ne pouvaient plus l'utiliser comme canal de prêts concessionnels | Vanheukelom, ECDPM, 27/11/2023 |
| **Évolution documentée (postérieure)** | FMI, Article IV Afrique du Sud, CR 26/34 (février 2026) : le secteur électrique, dominé par Eskom, a un ratio de couverture des intérêts **sous le seuil de 2** (les entreprises non financières sud-africaines en moyenne : 3,5→4, confortablement au-dessus) | FMI CR 26/34, p. 9 |

### Volet change

- Contre-valeur en rands du paquet : **trois chiffres officiels différents** — R128 md (JET IP, taux 15:1), R131 md (Presidency, taux implicite 15,41), R132,0 md (taux Fed nov. 2021, 15,5313).
- ZAR/USD : nov. 2021 = **15,5313** → pic mai 2023 = 19,0322 (+22,5 %) → août 2026 = 16,1650 (**+4,08 %** cumulé depuis la signature).
- Dette d'Eskom en devises : ≈36,8-39,6 % de la dette brute, mais l'exposition nette de change est **couverte à ~100 %** par des swaps (sensibilité résiduelle : R123m/R36m sur une perte de R12,3 md). L'erreur comptable qui a fait passer la perte FY2021 de R18,9 à R25,0 md portait précisément sur la comptabilité de couverture de change.

### Volet besoin

- **L'IRP2019** (plan en vigueur à la signature) **ne chiffre pas** l'investissement total requis — c'est un plan de capacité (18 000 MW de nouvelles capacités engagées), pas un plan de financement.
- Le seul chiffrage officiel du besoin est **postérieur** d'un an : JET IP nov. 2022, **98,7 Md$** (2023-2027) → le paquet = **8,61 %** du besoin total, **12,4-18,0 %** du seul volet électricité selon le découpage retenu.
- Repère antérieur à la signature (fév. 2022, FMI CR 22/37) : les autorités elles-mêmes estimaient le besoin international pour tenir leur CDN à **30 Md$ sur 5 ans** → le paquet = **28,3 %** de ce chiffre. Divergence 30 Md$ vs 98,7 Md$ non arbitrée (périmètres différents).

---

## 2. Indonésie — paquet de 20 Md$, signé le 15 novembre 2022 (G20 Bali)

### Volet souverain

| Grandeur | Valeur | Source |
|---|---|---|
| PIB nominal 2022 | 1 319,1 Md$ | Banque mondiale WDI / FMI WEO (convergent) |
| Paquet en % du PIB | **1,52 %** (taux moyen) / 1,59 % (taux fin d'année) [dérivé] | — |
| Dette externe totale 2022 | **396,8 Md$** (Bank Indonesia) — 395,986 Md$ (Banque mondiale, écart mineur −0,20 %) | Bank Indonesia SP 25/36/DKom ; Banque mondiale IDS |
| Paquet en % de la dette externe | **5,04-5,05 %** ; **8,84 %** de la seule dette PPG (226,18 Md$) ; **26,52 %** d'une année de service de la dette externe (75,41 Md$) [dérivé] | — |
| Dette publique brute 2022 | **40,1 %** PIB (FMI, réalisé) — **42,9 %** (FMI, projection publiée en mars 2022, en vigueur *au moment de la signature*) — **39,70 %** (Kemenkeu, administration centrale seule) | FMI CR 23/221 et CR 22/84 ; Kemenkeu |
| Règle budgétaire légale | Déficit ≤ **3 %** PIB, dette ≤ **60 %** PIB (UU 17/2003, *Penjelasan* Pasal 12(3) + PP 23/2003 Pasal 4) | UU 17/2003 ; PP 23/2003 |
| Statut de la règle à la signature | Relaxation COVID du plafond de **déficit** en vigueur jusqu'à fin 2022 (Perppu 1/2020 + UU 2/2020), retour à 3 % imposé par la loi **dès 2023**. Le plafond de **dette** (60 %) n'a **jamais** été suspendu. Le réalisé 2022 repasse sous 3 % **avec un an d'avance** (2,38-2,4 %) | Perppu 1/2020 ; FMI CR 23/221 §16 |
| Verdict FMI en vigueur à la signature | **CR 22/84** (mars 2022) : « *external and public debt remain moderate and sustainable* » ; « *risks to public debt sustainability would thus remain low* » — pas de grille LIC-DSA (l'Indonésie relève du MAC-DSA) | FMI CR 22/84, Annexe VI |
| Premier verdict post-signature | **CR 23/221** (juin 2023) : SRDSF **« low » overall risk of sovereign stress** ; « *debt sustainability risks are well contained* » | FMI CR 23/221 §18, Annexe IV |
| Service de la dette additionnel implicite | **Non calculable sans hypothèse non sourcée.** Point dur disponible : jusqu'à **8,4 Md$** des fonds IPG exigent une garantie souveraine du ministère des Finances | CIPP §7.4.1.2 |
| Recettes budgétaires 2022 | 176,55 Md$ → paquet = **11,33-11,86 %** des recettes [dérivé] | FMI CR 23/221, Table 5 |

### Volet opérateur — PT PLN (Persero)

| Grandeur | Valeur | Source |
|---|---|---|
| Résultat net | 13,17 triliun IDR (2021) → **14,41 triliun IDR (2022)**, bénéfice comptable | PLN, Laporan Tahunan 2022 |
| Composition du bénéfice | Porté par **58,83** (subvention) + **63,65** (compensation) triliun IDR de soutien public, soit **27,76 %** des produits totaux [dérivé]. CIPP : « *actual return on equity has averaged just 2% over the last five years* » | PLN AR2022 ; CIPP §8.6.1 |
| Perte de change 2022 | **−19,79 triliun IDR** (2022) contre un gain de +2,68 triliun (2021) — soit **1,37 fois** le résultat net 2022 [dérivé] | PLN AR2022 |
| Debt/EBITDA | **4,5×** (2021) → **4,8×** (2022) — le réalisé se situe au plancher de la fourchette projetée par le RUPTL (4,8-6,6×) | PLN AR2022 ; RUPTL 2021-2030 §6.2 |
| DSCR projeté par le plan en vigueur | **0,91-2,27×**, descendant sous 1 sur une partie de la période 2021-2030 | RUPTL §6.2 |
| Tarif vs coût (BPP) — **variable centrale** | Couverture **77,2 %** en 2022 (écart −336 Rp/kWh) ; **81,2 %** en 2021 (écart −250 Rp/kWh) — l'écart se creuse. Tarif gelé depuis mai 2017 | Calcul de l'auteur sur PLN, Statistik PLN 2022 |
| Projection du plan en vigueur | Le RUPTL prévoit lui-même l'aggravation : couverture **78,0 %** (2021-24) → **68,8 %** projeté (2025-30), car la cible EnR 23 % en 2025 renchérit le coût [dérivé] | RUPTL §6.2 |
| Capacité d'endettement — diagnostic du plan en vigueur (RUPTL) | « *jumlah pinjaman PLN dibatasi oleh covenant* » — emprunts plafonnés par covenant ; respect du covenant dépend entièrement de compensation/subvention/PMN ; **risque de défaut croisé sur le Gouvernement** en cas de non-respect | RUPTL §6.1-6.2 |
| Capacité d'endettement — diagnostic rétrospectif (CIPP, nov. 2023) | « *highly leveraged balance sheet, low profitability, constrained self-financing capacity, cannot access the equity capital markets without a privatization mandate from the government* » | CIPP §8.6.1 |

### Volet change

- Composition du paquet identifiée par le CIPP (nov. 2023) : **dons purs = 153,8 M$ = 0,77 %** du paquet ; part publique totale identifiée = 11 561,7 M$ (vs 10 Md$ annoncés en 2022). Jusqu'à **8,4 Md$** requiert une garantie souveraine.
- Recettes de PLN : **100 % IDR** ; paquet intégralement libellé/converti en USD. Registre des risques du CIPP : « FX risk » côté « Financial », **niveau High**.
- IDR/USD : 15 nov. 2022 ≈ **15 537** → 8 sept. 2026 = **17 618** JISDOR (**+13,58 %** de dépréciation cumulée du rupiah, comparaison homogène). Renchérissement dérivé sur 20 Md$ : +41,7 triliun IDR, soit 2,9 fois le résultat net 2022 de PLN.
- Retrait des États-Unis (mars 2025) : engagement identifié 2 066,7 M$ = **17,9 %** de la part publique identifiée / 10,3 % du paquet annoncé [dérivé].

### Volet besoin

- **RUPTL PT PLN 2021-2030** (plan en vigueur à la signature) : besoin total 1 287 triliun IDR/10 ans ≈ **86,7 Md$** → paquet = **23,1-24,1 %** [dérivé].
- **CIPP** (nov. 2023, postérieur) : besoin 2023-2030 = **97,1-97,3 Md$** → paquet = **20,6 %** (« *approximately one-fifth* », formule du CIPP lui-même) ; horizon 2050 = 580,3 Md$ → 3,4 %.
- Capex PLN requis sous JETP jusqu'en 2040 (CIPP) : **220,2 Md$** (13,0 Md$/an en moyenne) contre **3,5 Md$** de capex PLN réel en 2022 — soit **plus de 5 fois** le niveau actuel.

---

## 3. Vietnam — paquet de 15,5 Md$, signé le 14 décembre 2022

### Volet souverain

| Grandeur | Valeur | Source |
|---|---|---|
| PIB nominal 2022 | **413,4 Md$** (Banque mondiale) — 408,4 Md$ (FMI, projection connue à la signature) | Banque mondiale WDI ; FMI CR 22/209 |
| Paquet en % du PIB | **3,75-3,80 %** [dérivé] | — |
| Dette externe totale 2022 (projection FMI) | **145,1 Md$** = 35,3 % PIB | FMI CR 22/209 |
| Paquet en % de la dette externe | **10,68 %** [dérivé] | — |
| Dette publique au 31/12/2022 (chiffres officiels vietnamiens) | Nợ công (dette publique) **≈38 %** PIB (plafond 60 %, alerte 55 % → marge **22 pts** ≈ 91 Md$) ; nợ Chính phủ **34,7 %** (plafond 50 %, alerte 45 % → marge 15,3 pts) ; nợ nước ngoài **36,8 %** (plafond 50 %, alerte 45 % → marge 13,2 pts) | RMP MOIT 30/11/2023, §4.2.1, citant la Résolution 23/2021/QH15 |
| Plafonds absolus, plus mordants que les plafonds en % du PIB | Pour 2021-2025 : tirage net sur prêts garantis par l'État ≤ **76 500 milliards VND** ; tirage sur rétrocession (« cho vay lại », canal vers EVN) ≤ **222 000 milliards VND** ≈ **9,4-9,7 Md$ pour 5 ans** [dérivé] — **inférieur à l'enveloppe JETP annoncée**, et couvrant tous les secteurs | Nghị quyết 23/2021/QH15, art. 2.5b |
| Le canal effectivement emprunté (2022) | Décaissement de dette extérieure du budget de l'État ≈ **5,9 Md$/an**, incurrence nette ≈ **1,4 Md$/an** [dérivé]. Le paquet (3,1-5,2 Md$/an) vaut **à lui seul l'essentiel du flux annuel de décaissement de dette extérieure de tout l'État**, et 2 à 4 fois son incurrence nette annuelle | FMI CR 22/209, Table 4a [dérivé] |
| Verdict FMI (Article IV le plus proche) | **CR 22/209** (juillet 2022, données arrêtées avril 2022, 8 mois avant signature) : PPG **39,7 % PIB** (2021) → 40,5 % (2022 proj.) → stabilise à 40,6 % ; « *risk … low to moderate* » ; « *comfortably below the government's statutory ceiling of 60 percent* » ; heat map : **low risk of debt distress** | FMI CR 22/209, Annexe VII |
| Réserves posées par le FMI lui-même | Choc de passif contingent → dette PPG à **≈54 %** PIB en 2027 ; choc macro-budgétaire combiné → **≈49 %**, « *close to the authorities' prudent debt anchor of 55 percent* » | FMI CR 22/209, Annexe VII |
| Service de la dette additionnel implicite | **Non calculable sans hypothèse non sourcée.** Plafond légal pertinent : dette directe du Gouvernement ≤ **25 % des recettes budgétaires totales** (NQ 23/2021/QH15, art. 2.6.d) | — |

### Volet opérateur — EVN

| Grandeur | Valeur | Source |
|---|---|---|
| Année de bascule bénéfice → perte | **2022** (l'année même de la signature) — EVN écrit en 2023 avoir subi sa « *deuxième année consécutive de perte* » sur l'activité électricité | EVN, Báo cáo tổng kết 2023 |
| Résultat net | **−26,77 mille milliards VND** (2023) → **+8,24 mille milliards VND** (2024, retour au bénéfice) | EVN, Annual Report 2024-2025 |
| Dette/EBITDA | **Non calculable sans hypothèse non sourcée** — EVN ne publie pas d'EBITDA | — |
| Capacité de décaissement observée | Investissement réalisé du groupe 2023 : **87 545 milliards VND ≈ 3,71 Md$/an** [dérivé]. Le paquet (3,1-5,2 Md$/an) représente **84 % à 140 %** de la totalité du programme d'investissement annuel de l'opérateur [dérivé] | EVN, Báo cáo tổng kết 2023 |
| Tarif vs coût — **variable centrale** | Tarif de détail moyen **gelé de mars 2019 à mai 2023** — un gel de plus de quatre ans qui **couvre entièrement la date de signature**. Les deux hausses de 2023 (+3 % mai, +4,5 % nov.) sont postérieures, et EVN écrit elle-même qu'elles n'ont pas suffi | EVN, Báo cáo tổng kết 2023 |
| Contraintes sur la capacité d'endettement (RMP, source gouvernementale) | Les décaissements MDB vers les infrastructures publiques exigent une garantie souveraine « *que le Gouvernement hésite à accorder en raison des contraintes de politique de dette publique* » ; la rétrocession consomme les limites sectorielles des banques domestiques ; les prêts non garantis à taux commercial « *ne sont pas attractifs pour EVN* » ; EVN est en difficulté financière « *du fait du coût des combustibles fossiles importés* » | RMP MOIT, 30/11/2023 |

### Volet change

- **100 % du paquet est libellé en devises étrangères** (USD, EUR à 1,05, CAD) — le RMP le confirme en note de tableau : aucune ligne en VND.
- Recettes d'EVN : **100 % VND**. Le RMP décrit explicitement le transfert de risque de change vers les projets (PPA jusque-là indexés USD, désormais réglés en VND sous le PDP8) et note un « *marché de swaps insuffisamment développé* ».
- Taux de change VND/USD : fin 2021 = **22 792** (FMI). Valeurs décembre 2022 / valeur la plus récente : voir CSV.

### Volet besoin — le paradoxe temporel

**Le plan que le paquet est censé cofinancer n'existait pas quand le paquet a été signé.**

- Déclaration politique JETP : **14 décembre 2022**. PDP8 (QĐ 500/QĐ-TTg) : **15 mai 2023**, soit **5 mois après**.
- Le plan en vigueur au 14/12/2022 était le **PDP7 révisé** (QĐ 428/QĐ-TTg, 2016), échu depuis deux ans sur sa période principale — chiffrage non extractible (scan sans texte).
- La déclaration elle-même écrit le besoin **au futur** : « *as will be outlined in the Viet Nam JETP Resource Mobilisation Plan* » (§19) — RMP publié le 30/11/2023, soit **11,5 mois après**.
- Circularité : le PDP8 (postérieur) conditionne ensuite ses propres cibles à l'exécution intégrale du JETP (« *với điều kiện các cam kết theo Tuyên bố chính trị … JETP … được thực hiện đầy đủ* »).

| Dénominateur | Antériorité vs signature | Montant | Paquet / besoin [dérivé] |
|---|---|---|---|
| PDP8 2021-2030 (QĐ 500) | **postérieur** (5 mois) | 134,7 Md$ | **11,51 %** |
| NDC actualisée 2022, secteur énergie | **antérieur** | 60,6 Md$ | **25,58 %** |
| NDC actualisée 2022, composante ODA+IDE | **antérieur** | 46,1 Md$ (RMP : « *presque trois fois* » le paquet) | **33,62 %** |
| Banque mondiale, CCDR juillet 2022, besoin total 2022-2040 | **antérieur** (5 mois) | 368 Md$ | **4,21 %** |
| Banque mondiale, CCDR, composante « EXTERNAL » 2022-2040 | **antérieur** | 54 Md$ | **28,70 %** |

Le RMP le concède lui-même un an après : « *impossible de déterminer quelle part des
134,7 Md$ du PDP8 relève du périmètre JETP … mais le besoin sera plusieurs fois les
15,5 Md$* ».

---

## 4. Sénégal — paquet de 2,5 Md€, signé le 22 juin 2023

### Volet souverain

| Grandeur | Valeur | Source |
|---|---|---|
| PIB nominal 2022 | 17 330,1 Mds FCFA / 27,783 Md$ | ANSD (via Cour des comptes) ; Banque mondiale WDI |
| Paquet en % du PIB | **9,46-9,75 %** (2022) ; 8,74-8,83 % (2023) [dérivé] | — |
| Dette externe totale 2022 (post-révision) | 35,581 Md$ → paquet = **7,62 %** ; PPG = 17,896 Md$ → **15,14 %** | Banque mondiale IDS |
| ⚠️ Divergence majeure sur la dette externe | Avant révision, PPG 2023 publiée à **≈17 Md$** ; après révision (2025), **22,4 Md$** — écart de **5,5 Md$ (16 % du PIB)** correspondant à la « dette cachée » | Financing Development Lab, 12/08/2025, sur comparaison de millésimes IDS |
| Dette publique **telle que connue à la signature** (FMI CR 23/250, Conseil du 26 juin 2023, 4 jours après signature) | Dette publique totale (large, y c. entreprises publiques) **76,6 %** PIB (2022) [> seuil UEMOA 70 %] ; administration centrale seule **68,2 %** [< 70 %, de justesse] ; déficit **−6,6 %** PIB (2022) [> 2× le seuil UEMOA de 3 %] | FMI CR 23/250 |
| **Critères UEMOA** | Déficit ≤ 3 % PIB ; dette publique ≤ 70 % PIB ; inflation ≤ 3 % | Acte additionnel n°01/2015/CCEG/UEMOA |
| ⚠️ **Révision majeure, ex post** — Cour des comptes, févr. 2025 | Dette de l'administration centrale reconstituée : **86,6 %** PIB (2022) / **99,7 %** (2023) — vs 68,2 % / 77,7 % déclarés en 2023. Déficit recalculé : **12,65 %** (2022) / **12,30 %** (2023) — vs 6,08 % / 4,90 % déclarés. Écart de **18,6 à 25,3 pts** sur la dette, **6,6 à 7,4 pts** sur le déficit | Cour des comptes du Sénégal, févr. 2025 |
| Verdict FMI/Banque mondiale (DSA jointe au CR 23/250) | Risque de surendettement extérieur : **modéré**. Risque global : **modéré**, « *limited space to absorb shocks* ». « *All risk indicators breach their threshold under the sensitivity analysis* ». Risque de dégradation cité : « *further depreciation of the CFA* » | FMI CR 23/250, DSA conjointe |
| Chiffres révisés (WEO courant, IMF DataMapper) | Dette publique/PIB : 2021 = **98,7 %**, 2022 = **104,7 %**, 2023 = **118,4 %**, 2024 = **132,4 %** — écart de 28 à 41 pts avec les chiffres de juillet 2023 | FMI, IMF DataMapper `GGXWDG_NGDP` |
| Service de la dette / recettes | **30,7 %** (2022) / 32,5 % projeté (2023) | FMI CR 23/250, tableau 1 |
| Paquet / recettes budgétaires | **47,6 %** (2022) / 40,7 % (2023) [dérivé] | — |
| Service de la dette additionnel implicite | **Non calculable sans hypothèse non sourcée** ; taux d'intérêt effectif moyen sur la dette PPG = **3,6 %** (2022) ; élément-don des nouveaux emprunts = **11,4 %** (2022) | FMI CR 23/250, DSA |

### Volet opérateur — Senelec

| Grandeur | Valeur | Source |
|---|---|---|
| Résultat net | **Bénéficiaire** sur 2020-2022 (36-39 Mds FCFA) — mais grâce à une **compensation tarifaire de l'État de 180 à 238 Mds FCFA/an** ; sans elle, l'exploitation serait lourdement déficitaire. **2023 : non trouvé** | CRSE, consultation nov. 2022 (bilan Senelec en annexe) |
| Dette financière | **Non trouvée** — le document de la CRSE présente le compte de résultat mais pas le bilan ; ratio dette/EBITDA non calculable | — |
| Tarif vs coût — **variable centrale** | Couverture du coût de service complet (RMA) : **87,5 %** (2020) → **80,6 %** (2020-21 cumulé) → **68,2 %** (budget 2022). L'écart passe de 62,7 à **238,3 Mds FCFA** en deux ans — **il quadruple** | Calcul de l'auteur sur CRSE, consultation nov. 2022 |
| Compensation tarifaire de l'État | 2020-2022 : **456,3 Mds FCFA** (CRSE) / 2017-2021 : 521,8 Mds FCFA (Cour des comptes) — divergence de périmètre signalée | CRSE ; Cour des comptes |
| Subventions énergie, budget 2022 | **692 Mds FCFA = 4,0 % du PIB** ; arriérés non réglés à mi-2023 : **2,2 % du PIB** | FMI CR 23/250, tableau 4 |
| Capacité d'endettement additionnelle | **Aucun audit ne la chiffre.** FMI : « *Senelec could turn its cash flow positive by 2027* » (implique un flux négatif jusque-là) ; « *shoring up Senelec's finances [is] a precondition to reduce production cost* » | FMI CR 23/250 §13 |
| Hausse tarifaire proche de la signature | **+17 %** en moyenne, janvier 2023 (seul ajustement entre la période mesurée et la signature) | FMI CR 23/250 §18 |

### Volet change — discriminant structurel

- **Le paquet est libellé à 100 % en euros** (déclaration §12, aucune tranche USD identifiée officiellement).
- **Le FCFA est arrimé à taux fixe à l'euro** (1 EUR = 655,957 FCFA) depuis 1999, avec garantie de convertibilité illimitée du Trésor français : **le service de la dette de la part euro ne porte aucun risque de change**. C'est un **discriminant structurel de la comparaison à quatre pays** — EVN (VND flottant), PLN (IDR flottant) et Eskom (ZAR flottant) portent un risque de change que Senelec ne porte pas sur sa composante euro.
- Nuance signalée par le NRGI (janv. 2026) : les **équipements** (panneaux, batteries, systèmes de contrôle) sont facturés en dollars du fait de leur approvisionnement mondial — un risque de change existe donc **côté coût des projets**, pas côté service de la dette.
- FCFA/USD (dérivé de la parité fixe et du taux EUR/USD) : juin 2023 ≈ **605,13** → sept. 2026 = **564,41** — le FCFA s'est apprécié de **6,7 %** contre le dollar, sans effet sur la part euro (100 % du paquet).

### Volet besoin

- **LPDSE 2019-2023** (plan en vigueur à la signature, antérieur) — le seul dénominateur légitime *ex ante* : volet électricité = **3,496 Md€** → paquet = **71,5 %** ; secteur énergie complet = 6,591 Md€ → 37,9 %.
- **Capacité d'absorption réellement constatée avant le JETP** : taux de mobilisation à mi-2021 = **5,9 %** ; taux d'exécution financière = **74 %** de l'engagé, soit **≈107 M€/an** effectivement exécutés sur tout le secteur énergie — très inférieur au débit implicite du JETP (**500-833 M€/an**).
- Le **PIMC**, cité par la déclaration comme référence de la cible de 40 % de renouvelables, **n'existait pas encore** en juin 2023 (l'AIE le confirme en janvier 2024 : « *le Sénégal travaille à l'élaboration d'un PIMC* »).
- Plan d'investissement JETP officiel (mai 2025, **postérieur de 23 mois**, avec 11 mois de retard sur l'échéance des 12 mois promise par la déclaration elle-même) : besoin total **9,531 Md€** (2025-2030), dont 35 % de mobilité verte urbaine (hors électricité) → paquet = **26,2 %** du total, **50,2 %** du seul cœur électrique.
- Le NRGI (janv. 2026) alerte sur un débit prévu **> 600 M€/an** en 2026-2027, un niveau qu'il juge « *likely to exceed the current absorption capacity* » des institutions nationales.
- Décaissements à ce jour (sept. 2026) : **0 rapporté** par trois observateurs indépendants et datés ; aucun état officiel publié.

---

## 5. Tableau comparatif des quatre pays

| | Afrique du Sud | Indonésie | Vietnam | Sénégal |
|---|---|---|---|---|
| Signature | 2 nov. 2021 | 15 nov. 2022 | 14 déc. 2022 | 22 juin 2023 |
| Paquet | 8,5 Md$ | 20 Md$ | 15,5 Md$ | 2,5 Md€ (≈2,71 Md$) |
| Paquet / PIB | **2,02 %** | **1,52 %** | **3,75-3,80 %** | **9,46-9,75 %** |
| Paquet / dette externe totale | 5,02-5,30 % | 5,04-5,05 % | 10,68 % | 7,62 % |
| Dette publique déclarée à la signature (gouv. central) | 69,9-70,7 % PIB | 39,7-42,9 % PIB | 34,7-38 % PIB | 68,2 % PIB |
| Écart avec la révision ultérieure la plus forte | 78,1 % (annoncé) vs 88 % (FMI, même moment) | 42,9 % (proj. signature) vs 40,1 % (réalisé) | non identifié dans cette collecte | **68,2 % (2023) vs 99,7 % (2025, Cour des comptes)** |
| Verdict FMI le plus proche | Trajectoire non stabilisée, « no buffers » | « moderate and sustainable », risques « low » | « low to moderate », « comfortably below » le plafond | « modéré », « limited space to absorb shocks » |
| Part de dons dans le paquet | **3,90 %** | **0,77 %** (dons purs) | **2,07-3,98 %** | dons du plan JETP postérieur : **4,0-6,4 %** (deux sources) |
| Résultat net opérateur, année de signature | perte (−R12,3 md FY2022) | bénéfice comptable, mais 27,8 % des produits en subvention/compensation | **bascule vers la perte en 2022** | bénéfice, mais entièrement porté par la compensation tarifaire |
| Tarif / coût, variable centrale | couvre l'exploitation courante, pas le coût complet (déficit 4-12 %) | **77,2 %** (2022) | tarif **gelé depuis mars 2019** | **68,2 %** (budget 2022) |
| Opinion d'audit / diagnostic financier de l'opérateur | *going concern* material uncertainty (FY2021 et FY2022) | « cannot access equity capital markets without a privatization mandate » (CIPP) | non trouvé formellement, mais bascule bénéfice→perte l'année même | aucun audit ne chiffre la capacité d'endettement ; FMI : cash-flow positif « seulement en 2027 » |
| Devise du paquet vs devise des recettes de l'opérateur | mixte USD/EUR vs ZAR — mais couverture de change quasi intégrale au bilan Eskom | 100 % USD (converti) vs 100 % IDR — pas de couverture généralisée | 100 % devises vs 100 % VND — marché de swaps peu développé | **100 % EUR vs FCFA arrimé fixe à l'EUR — risque de change nul sur le service de la dette** |
| Dépréciation de la monnaie locale depuis la signature | +4,08 % (ZAR/USD, moyennes mensuelles) | **+13,58 %** (IDR/USD) | voir CSV | −6,7 % (FCFA **apprécié** contre USD ; nul contre EUR par construction) |
| Besoin du plan en vigueur à la signature | **non chiffré** (IRP2019 = plan de capacité) | 86,7 Md$ (RUPTL 2021-2030) | **plan lui-même absent** (PDP7 échu, PDP8 signé 5 mois après) | 3,496 Md€ (LPDSE, volet électricité) |
| Paquet / besoin du plan en vigueur | n.d. | **23,1-24,1 %** | n.d. (paradoxe temporel) | **71,5 %** |
| Besoin déclaré ultérieurement par un document officiel dédié | 98,7 Md$ (JET IP, +1 an) → 8,6 % | 97,1-97,3 Md$ (CIPP, +1 an) → 20,6 % | 134,7 Md$ (PDP8, +5 mois) → 11,5 % | 9,531 Md€ (plan JETP, +23 mois) → 26,2 % |
| Capacité d'absorption mesurée avant le JETP | non chiffrée dans cette collecte | non chiffrée dans cette collecte | ≈3,71 Md$/an (EVN, 2023) contre 3,1-5,2 Md$/an demandés | **≈107 M€/an** (secteur énergie complet) contre 500-833 M€/an implicites |
| Décaissements rapportés à ce jour | rapports annuels officiels publiés (~657 M$ de dons sur 821 M$, cf. `conseil-publication-2026-07.md` §3.2) | ~1,1 Md$ décaissés fin 2025 (idem §3.3) | premières transactions 2024-2025 (idem §3.4) | **0 rapporté**, aucun état officiel |

---

## 6. Ce qui n'a pas été trouvé — synthèse des trous les plus gênants

| Pays | Item | Ce qui a été cherché | Verdict |
|---|---|---|---|
| Afrique du Sud | Montant total d'investissement de l'IRP2019 | Recherche exhaustive sur le texte intégral (5 624 lignes), motifs `billion`, `investment`, `capital cost`, etc. | Le document ne chiffre pas l'investissement — c'est un plan de capacité |
| Afrique du Sud | *Cost of supply* complet en c/kWh (Eskom ou NERSA) | grep sur les quatre documents Eskom/NERSA | Ni l'un ni l'autre ne le publie ; reconstitution dérivée fournie à titre indicatif |
| Afrique du Sud | Covenant chiffré de type dette/EBITDA | grep `covenant`, `debt/EBITDA` sur AFS/IR 2021-2022 | Non publié — seules des cibles de gestion internes existent |
| Afrique du Sud | Dette consolidée du secteur public incluant Eskom | Lecture intégrale MTBPS 2021, Budget Review 2022, FMI CR 22/37, SARB QB 303/304 | Aucun agrégat unique publié |
| Indonésie | Encours de dette externe de novembre 2022 (mensuel) | Pages SULNI en rendu JavaScript, PDF en 404, LPI 2022 hors limite de taille | Non trouvé ; proxy T3 2022 (394,6 Md$) non vérifié contre le primaire |
| Indonésie | Notations de crédit de PLN en 2022 (Moody's/Fitch/S&P) | Sites d'agences authentifiés | Non trouvé, budget de recherche web épuisé |
| Indonésie | Opinion de l'auditeur / continuité d'exploitation, comptes PLN 2022 | PDF audité récupéré mais illisible (table de références croisées absente) | Non trouvé |
| Indonésie | JISDOR (taux officiel Bank Indonesia) du 15 novembre 2022 exact | Formulaire historique bi.go.id (postback ASP.NET), service web BI, FRED, stooq | Non trouvé ; proxy par taux croisé BCE (≈15 537) |
| Vietnam | Dette/EBITDA d'EVN | Rapport annuel EVN | Non calculable — EVN ne publie pas d'EBITDA |
| Vietnam | Le RMP intégral (obtenu dans CE run, mais listé comme trou principal du run pilote du 10/08/2026) | Navigation ciblée `jetp.moit.gov.vn` | **Trouvé dans cette collecte** (248 p., 30/11/2023) |
| Vietnam | Chiffrage du besoin dans le PDP7 révisé (plan en vigueur à la signature) | PDF officiel `datafiles.chinhphu.vn/cpp/files/vbpq/2016/03/428.signed.pdf` | Scan sans couche texte ; pack de langue vietnamienne indisponible pour l'OCR |
| Sénégal | Résultat net Senelec 2023 | senelec.sn, crse.sn | Non trouvé — le document CRSE disponible s'arrête au budget 2022 |
| Sénégal | Dette financière de Senelec (bilan) | Document de consultation CRSE (compte de résultat seul disponible) | Non trouvée — aucun bilan public identifié |
| Sénégal | Notation de crédit de Senelec | Recherche générale | Non trouvée — aucune notation internationale identifiée |
| Sénégal | Chiffrage du PIMC | AIE *Sénégal 2023* | Le plan n'existait pas encore en juin 2023 — l'absence est le résultat |
| Tous | Service de la dette additionnel implicite en % des recettes, si le paquet était tiré intégralement en prêts | Déclarations politiques, JET IP/CIPP/RMP/plan d'investissement JETP | **Non calculable sans hypothèse non sourcée dans les quatre cas** — aucun document ne publie taux, maturité, différé ou profil de tirage de l'enveloppe agrégée à la date de signature |

---

## 7. Divergences entre sources — les plus significatives

1. **Sénégal — la plus grave de toutes.** Dette publique de l'administration centrale
   déclarée à 68,2 % du PIB au moment de la signature (FMI CR 23/250, juillet 2023) contre
   **86,6 % (2022) et 99,7 % (2023)** reconstitués ex post par la Cour des comptes du
   Sénégal (février 2025). Le verdict de risque « modéré » du FMI en juin 2023 reposait sur
   des données sous-déclarées. Écart de 18,6 à 25,3 points de PIB sur la dette, 6,6 à
   7,4 points sur le déficit.
2. **Afrique du Sud — trois projections officielles de dette en quatre mois.** MTBPS
   (11 nov. 2021, contemporain de la signature) : pic à 78,1 % du PIB en 2025/26. Budget
   Review (fév. 2022) : 75,1 % en 2024/25. FMI (mission close 2 semaines après la
   signature) : 88 % en 2026 **sans stabilisation**.
3. **Afrique du Sud — dette externe.** Banque mondiale 169,4 Md$ contre SARB 160,5 Md$
   fin 2021, écart de 8,9 Md$ (5,6 %), cause non établie.
4. **Vietnam — dérive de l'enveloppe elle-même**, déjà documentée par le run pilote du
   10 août 2026 : 15,5 Md$ (déclaration 2022) → 15,8 Md$ (RMP, déc. 2023 : 8,08 IPG +
   7,75 GFANZ) → 15,0 Md$ dans les restatements UK/UE de mai 2025, après le retrait
   américain, sans annonce de révision.
5. **Indonésie — dette publique brute 2022** : 40,1 % (FMI, réalisé, périmètre *general
   government*) contre 39,70 % (Kemenkeu, administration centrale) — périmètres distincts,
   pas un désaccord sur le même objet ; et 42,9 % (FMI, projection publiée en mars 2022,
   donc la valeur *effectivement connue à la date de signature*).
6. **Afrique du Sud — besoin de financement, 30 Md$ contre 98,7 Md$.** En février 2022,
   les autorités déclarent au FMI qu'« *about US$30 billion* » suffiraient sur 5 ans pour
   la CDN ; neuf mois plus tard le JET IP chiffre le besoin à 98,7 Md$. Le paquet représente
   28,3 % du premier chiffre et 8,6 % du second.
7. **Indonésie — composition du paquet.** Le Joint Statement de novembre 2022 annonce
   10 Md$ de finance publique IPG ; le CIPP (nov. 2023) en identifie 11 561,7 M$, dont
   2 000 M$ de garanties non décaissées.
8. **Sénégal — compensation tarifaire à Senelec.** CRSE : 218,0 Mds FCFA pour 2020-2021 ;
   Cour des comptes : 207,7 Mds FCFA pour les mêmes années (périmètres « décidée » vs
   « effectivement réglée par le FSE » non identiques).
9. **Indonésie — marge d'EBITDA de PLN en 2021** : 27,2 % (texte de la direction) contre
   24,22 % (tableau *Rasio Keuangan*) du même rapport annuel — écart non expliqué.
10. **Afrique du Sud — tarif moyen FY2021** : 111,04 c/kWh (Eskom, revenu réalisé ÷ kWh
    vendus) contre 116,15 c/kWh (NERSA, prix moyen réglementaire) — périmètres distincts,
    volumes également divergents (191 852 vs 192 658 GWh).

---

## 8. Lecture prudente

Ce test ex ante ne permet pas de trancher un verdict binaire « absorbable / non absorbable » —
ce n'est d'ailleurs la nature d'aucun des documents utilisés : les grilles FMI (MAC-DSA,
SRDSF, LIC-DSF) produisent des jugements de risque, pas des seuils de coupure. Mais les
grandeurs réunies convergent vers un constat commun aux quatre pays, avec des intensités
différentes.

**Au niveau souverain**, aucun des quatre paquets ne représentait, à la signature, une
menace *isolée* pour la soutenabilité de la dette publique mesurée par les seuls agrégats
officiels alors disponibles : les ratios se situaient sous les seuils légaux (Vietnam,
Indonésie) ou proches d'eux sans les dépasser nettement (Sénégal, au sens étroit de
l'administration centrale). C'est la **fiabilité de ces agrégats eux-mêmes** qui pose
problème dans deux des quatre cas : le Sénégal, où la révision post-2024 déplace la dette
de l'administration centrale de 68 % à près de 100 % du PIB, et l'Afrique du Sud, où la
propre trajectoire annoncée par le Trésor (78,1 %, stabilisation en 2025/26) divergeait
déjà de dix points de celle du FMI (88 %, aucune stabilisation) au moment même de la
signature. Dans les deux cas, le paquet a été promis sur la foi d'un chiffre de dette
publique qui, soit était déjà contredit par le propre bailleur multilatéral du pays
(Afrique du Sud), soit s'est révélé faux a posteriori pour des raisons non liées au JETP
mais préexistantes à lui (Sénégal). Aucune des quatre déclarations politiques ne fait
référence à un audit ou une vérification indépendante de ces chiffres au moment de la
signature.

**Au niveau opérateur**, le constat est plus uniforme et plus sévère : dans les quatre cas,
l'entreprise censée porter une partie substantielle de l'investissement était, à la date de
signature ou à l'exercice l'encadrant, soit en perte, soit bénéficiaire uniquement grâce à
un transfert public équivalant à 20-30 % de ses produits (Indonésie, Sénégal), et dans les
quatre cas le tarif ne couvrait pas le coût complet de fourniture — la variable posée comme
centrale par la question de recherche. Eskom portait une opinion d'audit *going concern*
sur les deux exercices encadrant la signature. EVN basculait en perte l'année même de la
signature, avec un tarif gelé depuis 2019. PLN affichait un covenant de dette plafonné et un
risque de défaut croisé sur l'État explicitement écrit dans le plan en vigueur à la
signature. Senelec ne dégagerait, selon le FMI lui-même, un flux de trésorerie positif
qu'en 2027. Dans trois cas sur quatre (Afrique du Sud, Indonésie, Vietnam), le document qui
énonce ces contraintes le plus explicitement — going concern, covenant, gel tarifaire — est
soit contemporain de la signature, soit antérieur de plusieurs mois, ce qui exclut qu'il
s'agisse d'une dégradation survenue après coup.

**Sur le besoin**, le paradoxe le plus net est vietnamien : le plan énergétique national
que le paquet devait cofinancer n'existait pas au moment de la signature et, une fois
publié, a conditionné ses propres cibles à l'exécution intégrale du paquet — une
circularité documentée dans le texte réglementaire lui-même. Le Sénégal présente le
paradoxe inverse mais tout aussi révélateur : le seul plan en vigueur à la signature
(LPDSE 2019-2023) donnait un besoin auquel le paquet répondait à 71,5 %, un ratio
apparemment cohérent — mais ce même document montrait un taux de mobilisation effective de
5,9 % et un débit annuel réel d'environ 107 M€, dix fois inférieur au débit implicite du
JETP. Un besoin correctement dimensionné sur le papier ne dit rien de la capacité
d'exécution — c'est précisément ce qu'observe, trois ans plus tard, le NRGI lorsqu'il
prévient que le rythme de décaissement prévu dépassera « la capacité d'absorption actuelle »
des institutions sénégalaises.

**Sur la structure de financement**, la comparaison à quatre pays isole un vrai
discriminant structurel, indépendant de la qualité de gestion de chaque opérateur : le
Sénégal est seul à bénéficier d'un régime de change qui neutralise, par construction, le
risque de change sur le service de la dette de son paquet (parité fixe FCFA/EUR, garantie
par le Trésor français), tandis que l'Afrique du Sud, l'Indonésie et le Vietnam empruntent
en devises flottantes contre des recettes d'opérateur en monnaie locale elle-même flottante
— un décalage déjà matérialisé dans les comptes 2022 de PLN (perte de change supérieure au
résultat net de l'année) et implicitement neutralisé chez Eskom par une couverture de change
qui a, elle-même, dû être retraitée pour erreur comptable. Sur les trois pays à devise
flottante, aucun signe ne suggère que cette exposition ait été anticipée ou discutée dans
les déclarations politiques elles-mêmes ; elle n'apparaît que dans les documents de cadrage
ultérieurs (JET IP, CIPP, RMP), rédigés après la signature.

**Sur la structure dons/prêts**, enfin, les quatre paquets convergent vers un même chiffre
d'ordre de grandeur : entre 0,8 % (Indonésie, dons purs) et 4-6 % (Sénégal, plan
d'investissement postérieur) de la part génératrice de dette effectivement identifiée après
la signature — jamais plus de 4 % de dons dans les trois cas où ce chiffre est
disponible à la signature elle-même (Afrique du Sud 3,90 %, Vietnam 2,07-3,98 %). Cette
proportion n'était, dans aucun des quatre cas, connue publiquement au moment où la
déclaration politique a été signée : elle n'apparaît que dans un document de cadrage publié
entre 5 mois (Vietnam) et 23 mois (Sénégal) plus tard. **Le paquet a donc été annoncé, dans
les quatre cas, avant que sa propre structure de financement — la variable qui détermine si
l'opération alourdit ou non la dette du bénéficiaire — soit rendue publique.** C'est le
point de méthode le mieux établi de cette collecte, et le plus directement testable contre
la thèse de l'article : ce n'est pas seulement que l'absorbabilité n'a pas été vérifiée
avant la promesse — c'est que l'instrument même par lequel la promesse allait être tenue
(don ou dette, souverain ou garanti, en devise ou en monnaie locale) restait, à la date de
signature, indéterminé dans les quatre cas.
