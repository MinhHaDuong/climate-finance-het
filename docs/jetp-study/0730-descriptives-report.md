# 0730 — Descriptifs JETP à partir du snapshot gelé

## Résultat préliminaire

Le snapshot conserve 1,740 assertions atomiques : 7 événements, 1,729 positions et 4 assertions de couverture. Il ne produit pas une cohorte commune opérationnelle A/B/C : le nombre d'assertions atomiques explicitement codées sur les trois dimensions est 0.

C'est un résultat de couverture documentaire, non une absence de fonctions, de finance ou d'histoire dans les JETP.

## Couverture des trois dimensions

| Dimension | Assertions documentées | Assertions non codées/inconnues | Sens |
| --- | ---: | ---: | --- |
| Fonction | 1,399 | 341 | Portfolio and technology labels are retained as source labels, not harmonised just-transition functions. |
| Instrument financier | 303 | 1,437 | Ownership is only source-stated wording; a funder name is not recoded into public or private ownership. |
| Histoire événementielle | 7 | 1,733 | Events are reported assertions pending independent operation identity; dates are not transition clocks. |

## Pays et journaux

| Pays | Atomiques | Événements | Positions | Couverture | Rapprochées | Non rapprochées |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ZAF | 257 | 0 | 257 | 0 | 0 | 257 |
| IDN | 1,148 | 0 | 1,148 | 0 | 0 | 1,148 |
| VNM | 325 | 7 | 318 | 0 | 14 | 311 |
| SEN | 10 | 0 | 6 | 4 | 1 | 9 |

## Interprétation financière et temporelle

297 positions monétaires sont rapportées, avec 1,443 valeurs monétaires inconnues. Les devises, objets financiers, périmètres et doublons possibles empêchent tout total de portefeuille. Les 7 assertions événementielles sont des assertions sourcées, pas des horloges de transition ; aucune durée de transition n'est calculable.

L'attribution public/privé n'est littérale dans le snapshot que pour 4 des 303 observations avec instrument : 1 publique, 2 privées et 1 mixte non ventilée. Les 299 autres restent non documentées pour la propriété : un nom de financeur ne suffit pas à l'inférer.

## Handoff 0823

Trois candidats restent ouverts : asymétrie de couverture (résultat nul du join), cycle de vie rapporté ZAF, et pedigree finance/histoire VNM. La sélection de la figure centrale doit comparer leur intérêt substantiel et leur lisibilité, sans transformer l'un en résultat causal ou en total financier.

Fichiers associés : `0730-descriptives.json`, `0730-run-manifest.json`, les tables CSV et `0730-plot-data.csv`. Tous sont régénérables via le script 0730 à partir du snapshot 0822 épinglé.
