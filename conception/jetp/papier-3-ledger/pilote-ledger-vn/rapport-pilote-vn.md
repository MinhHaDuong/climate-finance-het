<!-- Atterri depuis ~/CNRS/projets/actifs/jetp/papier-3-ledger/pilote-ledger-vn/rapport-pilote-vn.md (ticket 0712, 2026-09-11).
     Contenu inchangé par rapport à la source, hors ce bandeau.
     Matériau de conception pour les papiers JETP (tracker 0708) —
     pas encore câblé dans un livrable. -->
# Rapport du pilote JETP ledger Vietnam — run 1 (10 août 2026)

Premier run du socle empirique (voie 3 de la roadmap envoyée à C. Cassen) :
recensement documentaire, collecte avec provenance, tirages IATI et OECD
CRS, brouillon de vérité terrain. 11 agents, ~22 minutes, aucun échec
d'agent. Pas d'extraction IA de contenu dans ce run — c'était le périmètre
convenu.

## Ce que le run a produit

| Livrable | Fichier | Contenu |
|---|---|---|
| Census | `census.md` | 82 documents recensés en 4 classes, priorisés 1-3 |
| Collecte | `docs/` + `manifest.csv` | 54 fichiers téléchargés, 66 lignes de provenance (statut, code HTTP, sha256, taille) |
| IATI | `iati-crs/codeforiati_*`, `registry_*` | 485 activités énergie Vietnam ; sous-ensembles bailleurs IPG (184) et mentions JETP (2) |
| OECD CRS | `iati-crs/crs_*` | Tirage complet Vietnam (167 Mo brut, compressé), énergie 2022-2024 nettoyée par bailleur × instrument |
| Vérité terrain | `verite-terrain-brouillon.csv` | 46 lignes pré-codées, à ratifier (colonne `ratifie` vide, à cocher) |

## Trouvailles de fond, déjà

1. **La dérive de l'enveloppe est visible dans la vérité terrain.** Les
   documents officiels donnent successivement 15,5 Md$ (déclaration 2022),
   15,8 Md$ (RMP, décembre 2023 : 8,08 IPG + 7,75 GFANZ), puis 15,0 Md$
   dans les restatements UK/UE de mai 2025 — après le retrait américain,
   sans annonce de révision. Le pré-codeur a codé les trois lignes avec le
   conflit signalé : c'est exactement le type de résultat que le ledger
   doit produire (inflation puis déflation silencieuse des promesses).
2. **Le JETP est quasi invisible dans IATI.** Sur 485 activités énergie
   Vietnam du Datastore, **2** seulement mentionnent « JETP » ou « Just
   Energy Transition » dans leur texte. La traçabilité déclarative de
   l'instrument est à peu près nulle — première mesure de la carte
   d'opacité, publiable telle quelle.
3. **La décision du plan révisé est identifiée** : Quyết định
   458/QĐ-TTg, signée le 23 mars 2026 par le Vice-Premier ministre Bùi
   Thanh Sơn (confirmé sur moit.gov.vn) — ~47 % d'ENR dans le mix 2030,
   plafond charbon 30,2-31 GW, fermeture des centrales de plus de 40 ans.
   La note de conseil disait « plan révisé approuvé mars 2026 » sans
   référence ; le numéro et la date exacte sont maintenant sourcés.
4. **Le secrétariat JETP vietnamien est rattaché au MOIT** (portail
   `jetp.moit.gov.vn`), pas au MONRE comme le supposait le brief.

## Les trous, nommés

- **Le RMP intégral (~200+ pages) n'a pas été obtenu.** Aucune URL PDF
  directe fonctionnelle trouvée ; le portail `jetp.moit.gov.vn` a une
  rubrique « Kế hoạch huy động nguồn lực » mais le lien de téléchargement
  exige une navigation interactive. C'est LA pièce maîtresse du registre —
  priorité absolue du run 2 (pistes : navigation directe du portail MOIT,
  energytransitionpartnership.org, climate-laws.org).
- **Tout le domaine adb.org est bloqué** (403 anti-bot, 5/5 URLs, y
  compris l'Energy Transition Mechanism — un canal majeur). Idem BII.
  Alternatives run 2 : IATI de l'ADB (publiant), archives web, ou
  téléchargement manuel ponctuel.
- **4 documents sans URL confirmée** ont été volontairement non collectés
  plutôt qu'inventés (dont le texte intégral des Quyết định 458 et 1009 —
  la base `vanban.chinhphu.vn` est la piste).
- IATI officiel (`api.iatistandard.org`) exige une clé d'abonnement
  (gratuite sur inscription) — le run est passé par le Datastore Classic
  de Code for IATI. Prendre une clé officielle serait plus propre.

## Ce qui t'attend (ratification, ~1-2 h)

`verite-terrain-brouillon.csv` : 46 lignes, chacune localisée dans un
document de `docs/` (fichier + page/section). Ouvrir le CSV, vérifier
chaque ligne contre le document indiqué, cocher `ratifie` (oui/non/corrigé).
Les conflits de chiffres sont codés en lignes multiples avec note — ne pas
les fusionner : le conflit est la donnée.

## Run 2 proposé (après ta ratification)

1. Récupérer le RMP intégral et les textes des Quyết định (navigation
   ciblée + vanban.chinhphu.vn), compléter ADB via son flux IATI.
2. Extraction IA sur le corpus validé (méthode benchmarkée AEDIST), mesure
   rappel/précision contre la vérité terrain ratifiée.
3. Croisement registre ↔ CRS/IATI : parts dons/prêts par bailleur, écarts
   annonces/déclaré — le premier tableau comptable du ledger.

## Coût du run

11 agents, ~940 k tokens de sous-agents, 248 appels d'outils, 22 minutes.
La collecte brute (docs + IATI + CRS) pèse ~350 Mo sur disque, dont
l'essentiel en tirages bruts compressables ou re-téléchargeables.
