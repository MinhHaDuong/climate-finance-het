<!-- Atterri depuis ~/CNRS/projets/actifs/jetp/papier-long-economie-politique/saturation-angle-absorption-2026-09-08-logs/00-note-outillage.md (ticket 0712, 2026-09-11).
     Contenu inchangé par rapport à la source, hors ce bandeau.
     Matériau de conception pour les papiers JETP (tracker 0708) —
     pas encore câblé dans un livrable. -->
# NOTE OUTILLAGE — état mesuré le 8 septembre 2026, ~11h UTC

Testé depuis cette machine :

- **OpenAlex : HTTP 429 sur TOUTE requête**, y compris avec `&mailto=`.
  Un agent précédent a saturé le quota IP ; l'en-tête Retry-After annonçait
  ~10,5 heures. **Ne compte pas sur OpenAlex.** Si tu obtiens un 200, tant
  mieux, note-le ; sinon bascule immédiatement, ne boucle pas dessus.
- **Semantic Scholar : HTTP 429 systématique.** Inutilisable.
- **Crossref : 200 OK.** `https://api.crossref.org/works?query.bibliographic=...&rows=20`
  Filtres utiles : `&filter=from-pub-date:2026-08-01,until-pub-date:2026-09-08`,
  `&filter=from-created-date:...`. Ajoute `&mailto=haduong@centre-cired.fr`
  (pool poli). Crossref renvoie `abstract` pour une partie des éditeurs
  seulement — un abstract absent de Crossref n'est pas un abstract inexistant.
- **OpenAIRE : 200 OK.** `https://api.openaire.eu/search/publications?title=...&size=20`
  (aussi `&keywords=`). Bon substitut d'OpenAlex, agrège les dépôts.
- **DOAJ : 200 OK.** `https://doaj.org/api/search/articles/<requête%20urlencodée>?pageSize=20`
  Excellent pour les revues régionales en accès ouvert (Indonésie, Afrique).
- **HAL : 200 OK.** `https://api.archives-ouvertes.fr/search/?q=...&wt=json&rows=20&fl=title_s,authFullName_s,producedDateY_i,doiId_s,uri_s,peerReviewing_s,docType_s`
  Le champ `peerReviewing_s` est décisif pour ne pas prendre une tribune pour
  un article.
- **Europe PMC : 200 OK.** `https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=...&format=json&pageSize=20`
  Couverture surtout biomédicale, mais indexe aussi des preprints.
- **WebSearch** : budget de session limité et partagé entre tous les agents.
  Utilise-le pour la littérature grise et les canaux non indexés, pas pour ce
  qu'une API peut faire.
- **WebFetch direct** : 403 fréquents sur sciencedirect.com, tandfonline.com,
  papers.ssrn.com, thediplomat.com, researchgate.net ; 402 sur Wiley.
  Contourne par le DOI Crossref, le dépôt institutionnel, ou Unpaywall
  (`https://api.unpaywall.org/v2/<doi>?email=haduong@centre-cired.fr`).

**Règle** : un échec d'outil (403, 429, paywall) se note comme échec d'outil,
jamais comme absence de littérature. Un angle dont tous les outils ont échoué
n'a PAS de résultat nul : il a un trou de couverture, à déclarer comme tel.
