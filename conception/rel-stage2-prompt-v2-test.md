# REL — essai du prompt d'étape 2, version 2 (discipline), 2026-10-01

*Ticket 1840, enfant de 1830. Archive complète (entrées, ensemble or, sorties des juges,
arbitrage, sorties Opus, rapport, soldes, `MANIFEST.sha256`) :
`~/data/projets/climate-finance-het/rel_discipline_test/2026-10-01/` (doudou), rapport
chiffré dans `report.txt` et `report.json`.*

## Ce qui est testé

Le wrapper `config/rel_stage2_prompt_v2.md` (sha256 `d380740f…`) : le texte ICF de la
version 1, mot pour mot, plus trois champs séparés, `contrib` (yes/no/unsure/na), `field`
(8 valeurs) et `ctype` (7 valeurs), définis dans le fichier du prompt. Opus en sous-agents
Claude Code (`model: opus`, un par bloc, lecture seule), comme l'étape 2 d'origine.

## Ensemble or discipline (sans l'auteur, sans Opus)

142 œuvres tirées des archives locales (catalogue du pilote Jev, échantillon routeur,
ensemble de référence, entrée `rel_sud`), hors ensemble de contrôle, stratifiées par mots
clés : apprentissage automatique (32), finance (30), gestion (26), économie et politique
(32), cas limites (22). La strate de tirage ne sert qu'à la couverture ; l'or vient des
juges. Juge 1 `openai/gpt-5.6-sol-pro` (OpenRouter), juge 2 Fable (sous-agent).
Accord des juges sur `contrib` : 135/142, kappa 0,92 (`field` 0,87, `ctype` 0,91). Les 7
litiges sont arbitrés par un panel anonymisé (relecture GPT, relecture Fable, Sonnet en
troisième modèle), à la majorité ; un cas sans majorité reste `unsure`.
Or : 59 yes, 61 no, 21 na, 1 unsure.

## Résultats

| Mesure | Valeur |
|---|---|
| `contrib`, or contre Opus v2 (4 classes, n = 142) | accord 0,90, kappa 0,84 |
| Décision REL (`contrib = yes` ou non) | accord 0,95, kappa 0,90 ; 3 inclusions en trop, 4 exclusions en trop |
| `field` / `ctype` (où les juges s'accordent, hors `out`) | kappa 0,88 / 0,90 |
| Par strate, décision REL | ML 31/32, finance 27/30, gestion 26/26, économie 30/32, limites 21/22 |
| Libellé ICF, ancien Opus t1530 contre v2 (200 pilotes) | accord 0,905, kappa 0,834 |
| Libellé ICF, ancien Opus t1530 contre v1 rejoué le même jour | accord 0,905, kappa 0,838 |
| Libellé ICF, v1 rejoué contre v2, même jour | accord 0,915, kappa 0,854 ; classe `icf` 21/21 identique |
| Rappel des sentinelles (55) | v2 49 icf (51 avec unsure) ; v1 rejoué 48 (50) |
| Échecs d'analyse | 0 ligne refusée, 0 valeur hors vocabulaire, sur 397 réponses |
| Coût OpenRouter | 0,65 USD (solde 16,54 → 15,89 USD) ; Opus, Fable, Sonnet sans coût OpenRouter |

Lecture. L'écart ICF entre l'ancien prompt et la v2 est du même ordre que le bruit d'un
rejeu du prompt v1 : le libellé ICF reste comparable, et la classe `icf`, celle qui
entre dans la REL, ne bouge pas. Un effet de direction est visible à la frontière
`aux`/`out` : le même jour, 14 des 75 `aux` du v1 passent `out` en v2, aucun dans l'autre
sens. Il ne touche pas l'inclusion REL (`aux` n'y entre pas) mais la carte
bibliométrique ; la cause n'est pas établie. Les erreurs de décision portent surtout sur
la finance appliquée à une question de politique (certification des obligations vertes,
spéculation sur le marché européen du carbone : or yes, Opus no) ; en ML, un seul cas
(prévision par forêt aléatoire de l'écart de performance des projets MDP, Opus yes).
