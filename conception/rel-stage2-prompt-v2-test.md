# REL — essai du prompt d'étape 2, version 2 (discipline), 2026-10-01

*Ticket 1840, enfant de 1830. Archive complète (entrées, ensemble or, sorties des juges,
arbitrage, sorties Opus, rapport, soldes, `MANIFEST.sha256`) :
`~/data/projets/climate-finance-het/rel_discipline_test/2026-10-01/` (doudou et padme ; `drift/` sur padme seulement), rapport
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
rejeu du prompt v1 : le libellé ICF reste comparable. Pour la classe `icf`, celle qui
entre dans la REL, la v2 ne perd aucune des 21 œuvres pilotes que le v1 rejoué étiquette
`icf` (0 sur 21), ni aucune des 48 sentinelles (0 sur 48). C'est une borne unilatérale :
au seuil de 95 %, le taux de perte par la v2 est inférieur à 1 − 0,05^(1/21) ≈ 13 % sur
les pilotes, 1 − 0,05^(1/48) ≈ 6 % sur les sentinelles, 1 − 0,05^(1/69) ≈ 4 % sur les
deux réunies. Cela exclut une perte systématique de la classe `icf` ; cela n'exclut pas
une perte de quelques pour cent, et ne dit rien des gains (1 `aux` et la sentinelle S30
passent `icf` en v2, 2 `aux` passent `unsure`). Un effet de direction est visible à la frontière
`aux`/`out` : le même jour, 14 des 75 `aux` du v1 passent `out` en v2, aucun dans l'autre
sens. Il ne touche pas l'inclusion REL (`aux` n'y entre pas) mais la carte
bibliométrique ; sa cause est examinée ci-dessous. Les erreurs de décision portent surtout sur
la finance appliquée à une question de politique (certification des obligations vertes,
spéculation sur le marché européen du carbone : or yes, Opus no) ; en ML, un seul cas
(prévision par forêt aléatoire de l'écart de performance des projets MDP, Opus yes).

## La dérive `aux` → `out` : bruit de rejeu, pas effet du prompt

Archive : `drift/` (`join.py`, `build_rerun.py`, `make_prompts.py`, `analyse_rerun.py`,
sorties `rerun.*.opus.txt`).

Sur les 14 œuvres, 8 étaient `out` dans l'étiquetage t1530 d'origine : c'est le rejeu v1
qui les avait passées `aux`, et la v2 revient au libellé d'origine. Contre t1530, le
rejeu v1 penche vers `aux` (13 `out`→`aux` contre 4, binomiale p = 0,05) et la v2 n'a
pas de sens net (10 `aux`→`out` contre 5, p = 0,30). Le volume de bascules `aux`/`out`
est le même dans les trois comparaisons (17, 15, 14 sur 200).

Rejeu ciblé (Opus, sous-agents, un bloc de 49 : les 14, les 9 autres bascules, 13 `aux`
et 13 `out` stables tirés au hasard ; trois enveloppes : v1, v2, et v2 sans la sortie
`na` pour `out`) :

| | v1 | v2 | v2 sans sortie `na` |
|---|---|---|---|
| les 14 (`out` / `aux`) | 8 / 6 | 9 / 5 | 7 / 7 |
| les 9 autres bascules | 5 / 4 | 0 / 9 | 0 / 9 |
| 13 `aux` stables, restés `aux` | 13 | 11 | 12 |
| 13 `out` stables, restés `out` | 11 | 11 | 11 |
| désaccords avec v1 (`out`→`aux` / `aux`→`out`) | | 6 / 4 | 7 / 2 |

Le 14 contre 0 ne se reproduit pas : avec le même prompt v1, 17 des 23 œuvres sujettes
aux bascules changent de libellé d'un jour à l'autre, et cette fois c'est la v2 qui
penche vers `aux`. Les témoins stables restent stables (69 libellés sur 78, trois enveloppes réunies).
Supprimer la sortie `na` déplace 3 œuvres de `out` à `aux` : un effet de « sortie bon
marché » au plus faible, dans le bruit. L'effet de position (10 des 14 en seconde moitié
d'un bloc de 150 ou 105, contre 24 des 58 `aux` stables, Fisher p = 0,07) n'est pas
établi. Cause retenue : instabilité de la frontière `aux`/`out` sur un sous-ensemble
identifiable (paiements pour services environnementaux domestiques, optimisation
énergétique avec marché du carbone, économie circulaire nationale), que la règle
place des deux côtés à la fois (« marché carbone domestique » en `aux`, « foresterie,
agriculture, ingénierie énergétique domestiques » en `out`).

Décision : pas de changement du prompt avant l'étape 2. La frontière `aux`/`out` ne
touche pas l'inclusion REL, et le texte ICF reste figé pour rester comparable aux
4 752 libellés t1530. Pour la carte bibliométrique, le libellé `aux`/`out` de ces
œuvres est à traiter comme bruité (environ 15 bascules sur 200 entre deux passes).
