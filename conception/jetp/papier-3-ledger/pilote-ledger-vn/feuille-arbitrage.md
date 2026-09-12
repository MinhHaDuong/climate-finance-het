<!-- Atterri depuis ~/CNRS/projets/actifs/jetp/papier-3-ledger/pilote-ledger-vn/feuille-arbitrage.md (ticket 0712, 2026-09-11).
     Contenu inchangé par rapport à la source, hors ce bandeau.
     Matériau de conception pour les papiers JETP (tracker 0708) —
     pas encore câblé dans un livrable. -->
# Feuille d'arbitrage — vérité terrain JETP Vietnam (10 août 2026)

La vérification mécanique est faite : les 46 lignes de
`verite-terrain-brouillon.csv` ont été confrontées mot à mot à leurs
documents sources locaux (8 agents, verdicts avec citation du passage).
**Résultat : 45 vérifiées, 1 partielle, 0 introuvable, 0 document
manquant.** Tu n'as donc PAS à relire les 46 lignes — il reste 6 clusters
de conflits à arbitrer, 4 questions de convention, et un sondage libre de
5 lignes. Recommandation en tête de chaque point ; coche ou corrige.

## 0. La seule ligne en échec partiel

**Ligne 10** (« restatement UK/UE 2025 ») code 15,0 Md$ ; le document dit
« $15.5 billion » en titre mais ventile « $7.5 billion public + $7.5
billion private » = 15,0 — le document est incohérent avec lui-même.
**Recommandé** : scinder en deux lignes (titre 15,5 ; somme des
composantes 15,0) avec note d'incohérence interne. C'est une donnée, pas
une erreur de codage.

- [ ] D'accord / corriger :

## 1. Cluster enveloppe globale (lignes 1-11)

La série officielle : 15,5 Md$ (déclaration 2022, 7,75+7,75) → 15,8
(RMP anglais 2023, 8,08+7,75) → 15,5 selon le gouvernement vietnamien au
même moment (7,75+7,75) → 15,5/15,0 incohérent (UK/UE mai 2025) → 15,0
(presse post-retrait US). Plus la variante américaine (ligne 4) qui
attribue les 7,75 publics à « IPG + ADB + IFC » (périmètre différent).
**Recommandé** : le ledger garde TOUTES les lignes datées — l'enveloppe
est une série temporelle, pas une valeur ; la dérive (inflation puis
déflation silencieuse des promesses) est le résultat.

- [ ] D'accord / valeur canonique à désigner :

## 2. Cluster Bac Ai (lignes 20-27)

Le même projet apparaît sous 480 M€ (MoU consortial mai 2025), 430 M€
(paquet Team Europe oct. 2025), 565 M$ (MOIT juil. 2026), 547 M€ (France+
IPG « deux projets phares »), 76 M€ (premier accord AFD signé déc. 2025),
10 M€ (AT), 21 100 Md VND (coût total), LOI CDP non chiffrée. Couches
d'annonce empilées, périmètres croisés.
**Recommandé** : identité projet unique « Bac Ai » ; chaque ligne garde sa
couche (annonce-cadre / MoU / signature / tirage) ; **on ne somme jamais
entre couches** — seules les signatures s'additionnent dans les totaux.

- [ ] D'accord / autre règle :

## 3. Cluster double valorisation EUR-USD (lignes 16-17, 18-19, 43-44)

Trois opérations codées deux fois : AFD 67 M€ = 78 M$ MOIT ; KfW 65 M€ =
79 M$ MOIT ; JICA 50 Md JPY = 320 M$ presse (avec en prime deux dates de
cérémonie divergentes, 18 vs 30 mars 2026).
**Recommandé** : la devise du document de signature est canonique (EUR,
EUR, JPY) ; les valorisations USD du MOIT/presse restent comme lignes de
recoupement marquées « conversion tierce », exclues des totaux (sinon
double compte). Conversions pour agrégats : taux annuels CRS.

- [ ] D'accord / autre convention :

## 4. Cluster périmètre JETP vs contexte (lignes 29-33, 45-46)

Cumuls historiques EIB (561→800 M€ depuis 1997), KfW-EVN (891,5 M€ depuis
2009 ; 800 M€ à venir), GET FiT (14,5 M€, non daté), crédits IDA DPF
Banque mondiale (2021 et 2023). Rien de tout ça n'est étiqueté JETP par
sa source.
**Recommandé** : périmètre à deux niveaux — « JETP strict » (le document
source dit JETP) et « IPG énergie élargi » (flux énergie post-2022 d'un
membre IPG). Ces lignes entrent en élargi, flag « contexte », hors totaux
JETP strict. Cohérent avec le constat IATI (2 activités sur 485
étiquetées JETP) : le flou du périmètre est lui-même un résultat.

- [ ] D'accord / autre périmètre :

## 5. Cluster statuts (lignes 34-39)

Pipeline de besoins (1,5 → 5,52 → 7,04 → 11 Md$) vs « mobilisé » ~800 M$
(3 projets — la source MOIT signale elle-même que 78+79+565 = 722 ≠ 800)
vs constat zéro décaissement (oct. 2024).
**Recommandé** : échelle de statuts du ledger : identifié (besoin) <
annoncé < MoU < signé < approuvé < décaissé. Les lignes « besoin » sortent
des totaux de financement (table pipeline séparée). L'écart 722/800 reste
codé tel quel, note d'incohérence source.

- [ ] D'accord / autre échelle :

## 6. Questions de convention transversales

1. **Concessionnalité** : « termes plus favorables que le marché » n'est
   pas une preuve de concessionnalité. **Recommandé** : nomenclature CRS
   (don / prêt concessionnel / prêt non concessionnel / garantie / AT) ;
   coder « concessionnalité déclarée, non vérifiée » sauf confirmation
   CRS ; équivalent-don selon la méthode CAD quand calculable.
   - [ ]
2. **Statut « engagé » du RMP** : le RMP dit « committed » pour 15,8 Md$ —
   engagement politique, pas contractuel. **Recommandé** : réserver
   « engagé » aux accords signés ; le RMP reste « annoncé (committed
   politique) ».
   - [ ]
3. **Le retrait américain** (lignes 40-41) : l'engagement US n'a jamais
   été ventilé publiquement pour le Vietnam. **Recommandé** : ligne de
   retrait non chiffrée + USAID 50 M$ marqué « sort post-retrait
   inconnu » ; ne pas inventer une part US.
   - [ ]
4. **Deux corrections mécaniques au passage** : renommer
   `evn-kfw-trian-65m-2024-06.html` → `…-2025-06.html` (le contenu date
   du 24 juin 2025) et corriger la date de la ligne 33 (GET FiT, non
   datée dans le document — laisser vide plutôt qu'estimer).
   - [ ]

## 7. Sondage libre (calibration)

Cinq lignes à ouvrir document en main, choisies pour leur variété :
**5** (RMP total, pièce centrale), **20** (Bac Ai MoU consortial),
**33** (GET FiT, la moins bien datée), **38** (le 800 M$ incohérent),
**43** (JICA en yen). Les passages exacts cités par les vérificateurs
sont dans `verif-verdicts.json` (ce dossier).

---

Une fois tes coches/corrections portées ici, la vérité terrain est
ratifiée : je répercute tes décisions dans le CSV (statuts, scissions,
flags de périmètre) et le run 2 (extraction + mesure rappel/précision)
peut partir.
