# 0817 — Census des sources et contrat d'acquisition

Le fichier `0817-source-census.csv` est l'univers fini de cette vague : une
ligne par `source_id` déclaré dans les quatre pays, soit ZAF 61, IDN 90, VNM 34
et SEN 116 sources. Il est construit uniquement depuis les métadonnées locales
`data/jetp/sources.csv` et `data/jetp/manifest.csv`, au 15 septembre 2026. Il
ne prétend donc pas que ces sources épuisent les JETP ou leurs portefeuilles.

Chaque ligne conserve une version (empreinte locale si disponible, sinon date
publiée ou `declared-undated`), le rôle financier, la sémantique de date, une
route et une disposition. `admitted` signifie seulement que l'octet est déjà
archivé et doit encore être revu avant admission d'un fait canonique;
`unavailable` signifie que la récupération locale a échoué ou n'a pas eu lieu.
Ce n'est jamais un zéro de finance, d'activité ou de couverture.

## Contrat commun

1. Chaque ticket télécharge ou réconcilie exclusivement ses lignes, en conserve
   les octets bruts et empreintes via DVC, puis produit des candidats séparés.
2. La revue humaine décide `admitted`, `duplicate`, `excluded`, `unavailable`
   ou `lost_visibility` pour chaque item, sans changer l'identité de source.
3. Les faits canoniques n'entrent qu'après cette revue et restent liés à leur
   source, version et locator. Les coûts, engagements, signatures, paiements,
   jalons physiques et dates de publication restent des champs distincts.
4. Un rapport de fin de ticket compte toutes les dispositions; aucun item non
   résolu ne peut devenir « complet » ou un montant nul.

## Handoffs sans recouvrement

| Ticket | Autorité exclusive | Priorités de revue |
|---|---|---|
| 0818 | toutes les lignes `country=ZAF` | registres/grants, rapports trimestriels, pages sociales; états de registre ≠ signatures/paiements |
| 0819 | toutes les lignes `country=IDN` | CIPP et ses miroirs, portefeuille, Cirebon/Saguling/ISLE-1; priorité ≠ allocation ≠ approbation |
| 0820 | toutes les lignes `country=VNM` | RMP, décisions MOIT, index/profils et sources financeurs; montants mobilisés ≠ décaissements |
| 0821 | toutes les lignes `country=SEN` | plan/annexes, opérateurs et Diass/ESAREF; slots anonymes et liens proposés restent non résolus |

Les sources transnationales sont rangées selon leur `country` déclaré; aucun
ticket ne modifie les lignes ou l'admission d'un autre pays. Les huit cas 0816
servent uniquement de pistes de revue, jamais de census de portefeuille.
