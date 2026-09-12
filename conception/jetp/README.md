# Matériau de conception JETP

Atterri depuis `~/CNRS/projets/actifs/jetp/` le 2026-09-11 (ticket 0712,
tracker 0708). Chaque fichier porte un bandeau de provenance ; le contenu est
inchangé par rapport à la source.

**Ce dossier n'est pas un livrable.** C'est du matériau de recherche orphelin
mais réutilisable, au même titre que `conception/clustering-comparison.md`. Le
câblage en fragments de livrable LaTeX est le ticket 0711, qui suppose des
choix de rédaction non encore faits. Ranger n'attend pas ces choix.

## Contenu

| Chemin | Quoi |
|---|---|
| `papier-court-mesure/bloc1-absorbabilite-2026-09-08.{md,csv}` | bloc 1, absorbabilité |
| `papier-court-mesure/courbe-reference-decaissement-2026-09-08.{md,csv}` | courbe de référence du décaissement, sortie de la chaîne `analyse-crs` |
| `papier-long-economie-politique/ancrage-litterature-developpement-2026-09-08.md` | ancrage dans la littérature du développement |
| `papier-long-economie-politique/cible-revue-2026-09-08.md`, `cible-revue-complement-2026-09-08.md` | classement de revues cibles |
| `papier-long-economie-politique/saturation-angle-absorption-2026-09-08.md` + `-logs/` | saturation bibliographique, angle absorption (10 finders, juge, critique) |
| `papier-long-economie-politique/saturation-biblio-2026-08-10.md` + `-logs/` | saturation bibliographique, première passe |
| `papier-long-economie-politique/handover-biblio-saturation-2026-08-10.md` | passation de la passe d'août |
| `papier-3-ledger/imagine-jetp-ledger-2026-08-10.md` | note d'idéation du ledger |
| `papier-3-ledger/pilote-ledger-vn/` | pilote Viêt Nam : recensement, arbitrage, rapport, manifeste, vérité terrain, verdicts |

Les trois notes recadrées par papier et le compte-rendu de la réunion du
2026-09-08 sont à la racine de `conception/` et dans `conception/reunions/`,
atterris plus tôt par le ticket 0709. Ils ne sont pas dupliqués ici.

## Ce qui n'a pas migré, et pourquoi

| Reste dans `~/CNRS/projets/actifs/jetp/` | Raison |
|---|---|
| `papier-court-mesure/analyse-crs/` (scripts, `data/`, `out/`) | **ticket 0713** — portage sous DVC dans `scripts/jetp/` et `data/jetp/`, pas une simple copie |
| `papier-3-ledger/pilote-ledger-vn/iati-crs/` (312 Mo) et `docs/` (10 Mo) | tirages bruts et sources HTML du pilote ; hors périmètre de 0713 §Invariants tant que le papier 3 n'existe pas |
| `aside-afd-senelec/` | **hors périmètre** du tracker 0708, dossier en pause (chiffre central 670 M€ non vérifié) |
| `docs/` (PDF Kruger et al. 2026 + `.ris`) | staging bibliographique — discipline EDM, destination Zotero, pas ce dépôt |
| `figures/` (2023–2024, dont `world map/JETPs_map.*`) | figures du **papier 1**, rangé le 2026-09-10 dans `~/CNRS/papiers/published/Reports/JETP at two/` — orphelines depuis ce déplacement, à rapatrier avec lui |
| `pour-christophe-2026-09-10/` | copies de livraison des PDF de `conception/`, identiques octet pour octet — trace d'envoi, pas une source |

## Une fois cette branche fusionnée

Les fichiers de la colonne « Contenu » ci-dessus existent en double : ici, et
dans `~/CNRS/projets/actifs/jetp/`. Cette copie-ci fait autorité. La
suppression des originaux appartient à l'auteur, comme pour l'ancien
emplacement `~/CNRS/papiers/actif/JETP at two/` (tracker 0708 §Invariants).
