# Replanification d'exécution — papier court et MVP JETP

> Cadrage scientifique remplacé par le
> [cadrage adopté sur les opérations](jetp-short-paper-framing-2026-09-15.md) :
> progression, public–privé et histoire, avec figure à trois panneaux.
> Le graphe de tickets ci-dessous reste le support d'exécution.

15 septembre 2026 · autorisation de l'auteur · Phase : Plan.

## Décision

L'auteur autorise une chaîne JETP complète : choix d'un dessin publiable,
acquisition et intégration des données nécessaires, statistiques, résultat et
figure centrale, extension du MVP puis manuscrit court. Un résultat nul,
négatif ou inconclusif est acceptable.

Le dessin principal retenu est **comparatif et non causal** : dans les quatre
JETP (Afrique du Sud, Indonésie, Viêt Nam, Sénégal), quelles finances JETP
publiquement rapportées peut-on tracer à des états distincts du cycle de vie,
avec quelles couvertures de source, dénominateurs et comparabilités ? Il ne
mesure ni l'effet des JETP, ni l'additionalité, ni leur mise en oeuvre physique.

Cette décision respecte le CAUSAL DEFER de 0729 et le DEFER de 0814, visibles
dans les branches revues `t0814-country-quarter-feasibility` et
`t0736-selection-timing-audit`. Le paquet 0815 est une liste de routes
discriminantes à incorporer à l'acquisition, pas un verrou préalable.

## Invariants

- « Complet » désigne chaque élément de chaque inventaire officiel, source,
  pays et période gelés dans le protocole, avec une disposition : admis,
  doublon, exclu avec raison, indisponible ou visibilité perdue. Ce n'est pas
  « toute la finance JETP » et les lacunes ne deviennent jamais des zéros.
- Les octets originaux/hashes sont archivés dans DVC; les faits revus restent
  dans les registres canoniques; le panel, les statistiques et figures sont des
  dérivés immuables et régénérables. Aucun nouveau backend vivant n'est créé.
- Pledge, allocation, approbation, signature, décaissement et réalisation ne
  sont jamais additionnés ni substitués. Les comparateurs n'entrent pas dans le
  portefeuille public JETP.
- Toute phrase causale est interdite dans le résultat, le MVP et le manuscrit
  tant qu'un futur protocole séparé ne surmonte pas les conditions de 0814.

## Graphe d'exécution

```text
acceptation 0736 / 0729 / 0814
              |
          0816 protocole de mesure
              |
          0817 recensement de sources
              |
    +---------+---------+---------+---------+
    v         v         v         v
 0818 ZA    0819 ID   0820 VN   0821 SN       ingestion revue
    +---------+---------+---------+---------+
              |
          0822 réconciliation + snapshot gelé
            /                       \
           v                         v
  0730 statistiques -> 0823 figure   0824 MVP étendu
           |
           v
      0732 papier court
```

Le MVP dépend seulement des faits canoniques admis; il n'attend pas le papier.
Une éventuelle visualisation analytique ne peut s'ajouter qu'après 0730 et reste
clairement séparée des faits.

## Sélection du résultat central

0823 développe trois résultats candidats, puis les compare selon leur intérêt
scientifique intrinsèque, leur robustesse aux choix de définition, leur couverture
empirique et leur apport vis-à-vis de la littérature publiée. Le classement,
les résultats écartés et les éléments contraires sont conservés. Astra réalise
une revue indépendante; l'auteur choisit ensuite le résultat et la figure centraux.
