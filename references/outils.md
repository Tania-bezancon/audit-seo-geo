# Les 19 outils : adresses, réglages, ce qu'on relève

Avec les 4 assistants IA de `panel-geo.md`, ils forment les 23 examinateurs de l'audit. Le relevé automatique (`crawl.py`) couvre en plus ce qu'aucun outil public ne mesure page par page : codes, temps de réponse, cache, compression, robots des IA, llms.txt, rendu sans JavaScript.

Toujours les mêmes outils, aux mêmes adresses, dans le même ordre, pour que deux audits se comparent. Les adresses viennent de `assets/defaults.json` (clé `outils`), qui contient aussi le texte « À quoi sert cet outil » affiché dans le dossier : ne pas le réécrire d'un audit à l'autre.

Variables des adresses : `{url}` la page testée (souvent l'accueil dans la langue principale), `{url_enc}` la même encodée, `{url_noproto_enc}` sans `https://`, encodée, `{host}` le domaine (`www.` compris s'il existe), `{host_nowww}` sans `www.`, `{brand_q}` la marque encodée pour une recherche, `{lang}` et `{country}` (fr, fr).

| N° capture | Outil | Éditeur | Adresse | Réglage | Ce qu'on relève | Domaine du dossier |
|---|---|---|---|---|---|---|
| 01 | PageSpeed Insights, téléphone | Google | `https://pagespeed.web.dev/analysis?url={url_enc}&form_factor=mobile` | 3 passages, garder la valeur du milieu | Performance, LCP, accessibilité, bonnes pratiques, SEO, navigation agentique | d-vitesse |
| 09 | PageSpeed Insights, ordinateur | Google | `https://pagespeed.web.dev/analysis?url={url_enc}&form_factor=desktop` | 3 passages, valeur du milieu | Performance et données réelles des visiteurs (Core Web Vitals sur 28 jours) | d-vitesse |
| 02 | Security Headers | Snyk | `https://securityheaders.com/?q={url_enc}&followRedirects=on&hide=on` |  | Note, en-têtes absents et présents, version du serveur affichée | d-securite |
| 08 | HTTP Observatory | Mozilla | `https://developer.mozilla.org/en-US/observatory/analyze?host={host}` |  | Note, score sur 100, tests réussis | d-securite |
| 13 | SSL Server Test | Qualys SSL Labs | `https://www.ssllabs.com/ssltest/analyze.html?d={host}&hideResults=on` | attendre la fin du test (2 à 3 min) | Note, version TLS, date d'expiration du certificat | d-securite |
| 14 | Internet.nl | Internet Standards Platform | `https://internet.nl/site/{host}/` | lancer le test de site web | Score, IPv6, DNSSEC, HTTPS, HSTS | d-securite |
| 12 | Webbkoll | 5th of July Foundation | `https://webbkoll.5july.net/en/check?url={url_enc}` |  | Cookies tiers, requêtes vers d'autres sociétés, CSP | d-securite |
| 11 | Blacklight | The Markup | `https://themarkup.org/blacklight?url={url_noproto_enc}&device=desktop&location=eu` |  | Traceurs publicitaires, cookies tiers, enregistrement de session, empreinte | d-securite |
| 15 | WAVE | WebAIM | `https://wave.webaim.org/report#/{url}` |  | Note AIM, erreurs, contrastes, images sans description | d-pages |
| 10 | Nu HTML Checker | W3C | `https://validator.w3.org/nu/?doc={url_enc}` |  | Erreurs et avertissements | d-pages |
| — | LanguageTool | LanguageTooler | `https://api.languagetool.org/v2/check` | script lt.py sur les titres, descriptions, H1 et H2 du crawl | Fautes et mots collés | d-pages |
| 06 | Recherche « site: » | Google | `https://www.google.com/search?hl={lang}&gl={country}&q=site%3A{host}&num=100` | navigation privée, cookies refusés | Nombre de résultats, faits affichés par Google (titres, descriptions) | d-faits |
| 21 | Recherche de marque | Bing | `https://www.bing.com/search?q={brand_q}` |  | Position du site, description affichée, langue | d-faits |
| 40 | Aperçu de partage | OpenGraph.xyz | `https://www.opengraph.xyz/url/{url_enc}` |  | Titre, description et image affichés au partage (LinkedIn, messageries) | d-pages |
| 07 | Test des résultats enrichis | Google | `https://search.google.com/test/rich-results?url={url_enc}` |  | Types de données structurées détectés | d-google |
| 16 | Schema Markup Validator | Schema.org | `https://validator.schema.org/#url={url_enc}` |  | Éléments et erreurs | d-google |
| 18 | Similarweb | Similarweb | `https://www.similarweb.com/website/{host_nowww}/` | estimation : à lire comme une tendance | Visites sur 3 mois, tendance, pays, rebond | d-google |
| 22 | Wikidata | Wikimedia | `https://www.wikidata.org/w/index.php?search={brand_q}` | chercher aussi le nom de l'éditeur | Fiche présente ou non | d-ia |
| 41 | Vérificateur de liens entrants | Ahrefs | `https://ahrefs.com/backlink-checker` | facultatif ; il demande une case « je suis humain » : c'est à l'utilisateur de la cocher, jamais à Claude | Domaines qui renvoient vers le site, autorité estimée | d-ia |

Les 4 assistants IA (captures 03, 04, 05, 17 pour Q1, puis 23 et suivantes) sont dans `panel-geo.md`.

## Comment relever un outil

1. Ouvrir l'adresse dans le navigateur intégré (`preview_start` avec `url`), sans compte, cookies non essentiels refusés.
2. Attendre la fin du test (SSL Labs : 2 à 3 min ; PageSpeed : 3 passages, garder la valeur du milieu).
3. Capture : la première capture du panneau sort souvent vide ou en fondu. En prendre une à `scale: 0.1`, puis la vraie. Le préréglage desktop donne une fenêtre de 1024 px et une image de 800 px.
4. Copier l'image (fichier `mcp-Claude_Browser-blob-*.jpg` dans `~/.claude/projects/<projet>/tool-results/`) vers `captures-audit/AAAA-MM-JJ/NN-sujet.jpg`, avec le numéro de la colonne de gauche.
5. Noter dans `audit.json` : `resultats.NN` (le résultat en une ligne et un feu v/o/r) et `fiches.NN` (qui, la note en gros, une ou deux pastilles, 2 à 4 constats, une phrase « À retenir », la capture et sa légende avec la date et l'heure).

## Les seuils de feu

| Outil | Vert | Orange | Rouge |
|---|---|---|---|
| PageSpeed | ≥ 90 | 50 à 89 | < 50 |
| Security Headers, Mozilla Observatory | A ou B | C | D, E ou F |
| SSL Labs | A ou A+ | B | C ou moins |
| Internet.nl | ≥ 90 % | 60 à 89 % | < 60 % |
| Webbkoll, Blacklight | aucun traceur avant accord | traceurs connus (analytics, LinkedIn) | traceurs publicitaires intrusifs, enregistrement de session |
| WAVE (note AIM) | ≥ 8 | 5 à 7,9 | < 5 |
| W3C | 0 à 5 erreurs | 6 à 50 | > 50 |
| Données structurées | Organization + type métier | partiel | rien |
| Wikidata | fiche juste | fiche incomplète | aucune fiche |
| Aperçu de partage | titre, description et image | l'un des trois manque | rien |
| TTFB médian (crawl) | < 800 ms | 800 à 1 800 ms | > 1 800 ms |
| Robots des IA (crawl) | robots de recherche autorisés | un robot de recherche bloqué | tous bloqués |

## Hors de la liste

- **check-host.net** (`check-host.net/check-http?host={url}`) : le site répond-il depuis l'étranger. Utile quand le serveur bloque le bureau.
- **Search Console** et **Bing Webmaster Tools** : seuls vrais chiffres de clics et de positions. Sans accès, on l'écrit dans les limites et on en fait une tâche back-end P1.
- **Google Business Profile** : pour une activité locale, la fiche sur la recherche de marque (horaires, avis, catégorie).
