---
name: audit-seo-geo
description: Audit SEO et GEO à 360° de n'importe quel site, avec 23 examinateurs externes gratuits (19 outils et 4 assistants IA) et leurs captures, un relevé automatique des pages (contenus, front-end, serveur, robots des IA, llms.txt), le panel des IA (ChatGPT, Google Mode IA, Brave, Perplexity), une grille fixe de 30 critères notée sur 10, trois to-do sans dates (contenu, front-end, back-end) priorisées de P1 à P3 et exportées en Markdown et CSV, et un protocole de remesure. Produit le dossier « Comment se porte le site » (HTML, PDF, page unique) et son PowerPoint aux couleurs de la marque. À utiliser dès qu'on demande un audit, une analyse, une note ou un bilan SEO, GEO, référencement, performance, visibilité Google ou visibilité dans les IA d'un site, une liste des corrections front et back d'un site, de refaire un audit pour mesurer les progrès, ou de refaire le dossier, le PowerPoint ou le PDF d'un audit. Also for "SEO audit", "GEO audit", "AI visibility audit", "technical SEO checklist" requests.
---

# Audit SEO / GEO à 360°

Le même audit, toujours de la même façon, pour que les notes d'un site à l'autre et d'un mois à l'autre soient comparables. On l'appelle avec une URL : `/audit-seo-geo https://www.exemple.fr`.

360°, c'est cinq regards sur le même site : **ce que Google peut lire** (exploration, indexation), **ce que vit le visiteur** (vitesse, accessibilité, conversion), **ce que fait le serveur** (codes, cache, sécurité, vie privée), **ce que disent les textes** (contenus, faits, fraîcheur) et **ce que répondent les IA** (GEO, autorité). Chaque problème trouvé devient une tâche, rangée dans l'une des trois to-do : contenu, front-end, back-end.

L'exemple complet est l'audit fictif d'Atelier Lumen : `assets/exemple/audit.json` et ses captures factices dans `assets/exemple/captures/`. En cas de doute sur le niveau de détail attendu, s'y reporter. `scripts/selftest.sh` fabrique tout l'exemple et vérifie que rien n'est cassé.

Une journée de travail en tout : environ 3 h de mesures, 2 h de notation et de rédaction, 1 h de fabrication et de contrôle. Annoncer la durée au commanditaire (la personne qui demande l'audit) au début et le tenir au courant à chaque étape.

## Ce que contient le skill

| Fichier | Rôle |
|---|---|
| `references/checklist-360.md` | Tous les contrôles, voie par voie (contenu, front-end, back-end), avec la preuve attendue, la correction type, la priorité et le critère touché |
| `references/outils.md` | Les 19 outils (les 4 IA sont dans `panel-geo.md`) : adresse exacte, réglage, ce qu'on relève, numéro de capture, seuils des feux |
| `references/panel-geo.md` | Les 5 questions et les 4 assistants IA : écrire, poser, noter |
| `references/captures.md` | Où ranger les captures, les captures du site à prendre, les pièges |
| `references/donnees.md` | Le format de `audit.json`, le seul fichier à écrire |
| `assets/sites.json` | Les sites déjà connus : activité, public, zone, objectif, thème, validateur, dossier |
| `assets/defaults.json` | Le contenu commun : grille, voies, priorités, outils et leur rôle, assistants, lexique, règles de remesure, domaines |
| `assets/themes.json`, `logos/`, `fonts/` | Couleurs, police et logo par marque : `signature` (par défaut), `neutre`, et ceux qu'on ajoute |
| `assets/exemple/` | L'audit fictif complet, à copier pour un nouvel audit |
| `scripts/crawl.py` | Relevé automatique et prudent de toutes les pages, du serveur et des robots des IA |
| `scripts/lt.py` | Fautes avec LanguageTool sur les titres, descriptions, H1 et H2, page par page |
| `scripts/annotate.py` | Cadres rouges sur une capture |
| `scripts/build_dossier.py` | `audit.json` → dossier HTML, PDF (`--pdf`), page unique (`--single`), to-do en Markdown et CSV, après contrôle de cohérence et des notes |
| `scripts/build_pptx.js` | `audit.json` → PowerPoint (`npm install` une fois dans `scripts/`) |
| `scripts/render_pptx_pdf.sh` | PowerPoint → PDF et planches de contrôle (Microsoft PowerPoint sur Mac, sinon LibreOffice) |
| `scripts/selftest.sh` | Fabrique l'exemple de bout en bout et vérifie chaque sortie |

## 1. Le contexte du site

Si le site est dans `assets/sites.json`, on ne pose aucune question. Sinon, on demande seulement ce qui manque parmi : l'activité, le public cible, la zone et les langues, l'objectif (demandes de contact, ventes, inscriptions, notoriété), la marque (pour le thème), le validateur des faits et le dossier où ranger l'audit, puis on ajoute le site à `sites.json` pour les prochaines fois.

On demande aussi, une fois, ce qui changerait la mesure : un accès à Search Console, à Bing Webmaster Tools ou à la mesure d'audience (sinon ces critères sont NV), le CMS ou le framework du site (WordPress, Webflow, Next.js…, pour écrire des corrections que l'équipe peut appliquer), et si l'activité est locale (alors on regarde aussi la fiche Google Business Profile).

Avant de commencer, on lit ce que le dossier du site contient déjà (un CLAUDE.md, un référentiel de faits, de claims et de concurrents) et le dernier audit du site, pour mesurer l'écart. Un site sans thème prend `signature` ; pour une nouvelle marque, on ajoute un thème dans `themes.json` (couleurs, police sous licence libre dans `fonts/`, logo dans `logos/`).

## 2. Les règles de preuve

- On examine au minimum : l'accueil, chaque page produit ou offre, la page contact, la page « à propos », le blog et 3 articles, et toutes les adresses du plan du site pour les contrôles automatiques. On note les pages étudiées, la date et les limites.
- Chaque constat est rangé dans l'une de trois catégories : **vérifié** (avec preuve), **hypothèse** ou **non vérifiable** (sans Search Console, Analytics, etc.).
- On n'invente aucune statistique, aucune position Google, aucun résultat de test. Une bonne structure GEO ne garantit pas d'être cité par une IA.
- Les captures sont réelles, prises dans le navigateur, avec l'URL visible ou notée (`references/captures.md`). Pour un problème de texte ou de code, on donne un avant/après. Une préférence de style n'est pas une faute.
- On revérifie en direct tout constat surprenant avant de l'écrire (une page vide, une date fausse, un chiffre contradictoire, un robot bloqué).
- On ne nomme pas les concurrents dans ce qui peut sortir de l'équipe : A, B, C… Les noms restent dans les documents internes.
- On ne modifie jamais le site audité, on ne remplit aucun formulaire réel, on ne coche jamais une case « je suis humain ».

## 3. Les mesures, dans cet ordre

1. **Relevé automatique**, en arrière-plan dès le début : `python3 scripts/crawl.py <url> <dossier>/crawl --delay 3`. Il relève chaque page (codes, temps de réponse, cache, title, description, Hn, alt, JSON-LD, Open Graph, viewport, scripts, indice de rendu par JavaScript) et le site entier (`checks.json` : robots des IA, llms.txt, compression, en-têtes de sécurité, fausse 404, www, http). Un serveur peut bloquer une adresse au-delà d'une centaine de requêtes rapides : garder 3 s entre deux pages, et relancer avec `--jina` en cas de blocage. Puis `python3 scripts/lt.py <dossier>/crawl --lang fr --prefix <url>` (une langue à la fois), et relire chaque alerte à la main.
2. **Le rendu sans JavaScript** : si `summary.json` signale `rendu_js_probable`, ouvrir la page avec JavaScript désactivé (ou lire `crawl.jsonl`) et le confirmer par une capture. Une page vide sans JavaScript est invisible pour la plupart des robots d'IA : c'est un constat P1.
3. **Les 19 outils** de `references/outils.md`, chacun avec sa capture numérotée.
4. **Le panel des IA** : 5 questions × 4 assistants (`references/panel-geo.md`), puis la recherche Wikidata et, si on le veut, les liens entrants.
5. **Les captures du site** (`site-01` et suivantes, `references/captures.md`), encadrées en rouge avec `scripts/annotate.py`. Contrôler les cadres sur une planche.
6. **Le parcours** : la checklist de `references/checklist-360.md`, voie par voie. Tout ce qu'un outil n'a pas couvert se regarde là (formulaire, navigation au clavier, aperçu de partage, pages légales, données structurées par type de page).
7. **Les concurrents** (facultatif, interne) : PageSpeed téléphone, Security Headers, Mozilla Observatory et la lisibilité par les agents sur leur page d'accueil, le même jour, et le nombre de fois où les IA les citent sur Q1 à Q4.
8. Noter tout de suite chaque résultat dans `audit.json` (`resultats`, `fiches`, `ia`, `captures`).

## 4. La grille fixe (ne pas la modifier d'un audit à l'autre)

Il y a 6 catégories de 5 critères. Chaque critère est noté **0** (absent ou faux), **1** (partiel) ou **2** (correct). Chaque catégorie est donc notée sur 10.
Un critère non vérifiable ou sans objet est noté **NV** et retiré du calcul : la note de la catégorie = points obtenus ÷ (2 × critères vérifiés) × 10. On le signale à côté de la note.
**Note globale = moyenne des 6 notes de catégorie (chacune arrondie à une décimale), arrondie à une décimale.** `build_dossier.py` refait le calcul à partir de `criteres` et s'arrête si `note` ne correspond pas. On écrit toujours « x,x / 10 », jamais sur 100.

**A. Exploration et indexation**
1. L'accès des robots : robots.txt n'empêche rien d'utile (CSS, JS, images compris), le sitemap est complet, à jour et déclaré, pas de noindex par erreur.
2. Une seule version du site : http vers https, www ou sans www, canonicals cohérentes, hreflang réciproques si le site a plusieurs langues.
3. Les codes HTTP : pas de liens cassés, pas de fausses 404, pas de chaînes de redirections, pas d'erreurs 5xx.
4. Le rendu : le contenu principal, les liens et les balises sont dans le HTML reçu, sans attendre JavaScript.
5. L'architecture : chaque page utile est à 3 clics au plus de l'accueil et reçoit des liens internes ; aucune page orpheline.

**B. Performance et front-end**
1. Les Core Web Vitals des vrais visiteurs (LCP < 2,5 s, INP < 200 ms, CLS < 0,1). Sans données réelles, NV.
2. La performance mesurée sur téléphone (PageSpeed mobile, valeur du milieu sur 3 passages).
3. Les images : formats modernes (WebP, AVIF), dimensions déclarées, tailles adaptées à l'écran, chargement différé sous la ligne de flottaison.
4. Le code : pas de JavaScript ni de CSS bloquants inutiles, polices chargées sans saut de texte, pas de contenu mixte http.
5. Le mobile : affichage à 375 px sans défilement horizontal, viewport déclaré, zones cliquables assez grandes.

**C. Serveur, sécurité et vie privée**
1. Le chiffrement : certificat valide, TLS 1.2 ou plus, HSTS.
2. Les en-têtes de sécurité : CSP, X-Content-Type-Options, X-Frame-Options ou frame-ancestors, Referrer-Policy, Permissions-Policy ; version du serveur non affichée.
3. Le transport : compression (Brotli ou gzip), cache des fichiers statiques, HTTP/2 ou plus, CDN si le public est loin du serveur.
4. Le temps de réponse : TTFB médian sous 800 ms, pas de lenteur sur les pages dynamiques.
5. La vie privée : aucun traceur ni cookie tiers avant le consentement, un refus aussi simple que l'acceptation, une politique de confidentialité à jour.

**D. Contenus et SEO éditorial**
1. Titles et descriptions uniques, descriptifs et à la bonne longueur, en comptant les pages en défaut ; aperçu de partage (Open Graph) complet.
2. La structure : un seul H1 par page, des Hn logiques, du HTML sémantique, pas de mots collés.
3. La profondeur : des pages qui répondent aux questions et aux intentions de recherche du public, et pas seulement des slogans.
4. La justesse : orthographe, grammaire, et les mêmes faits partout (chiffres, dates, certifications). Chaque contradiction est listée pour validation par le validateur du site (`site.validateur`).
5. La fraîcheur et les langues : blog et actualités datés et récents, traductions complètes et fidèles, rien de périmé en avant.

**E. Expérience, accessibilité et conversion**
1. En 5 secondes sur l'accueil, on comprend ce que c'est, pour qui, et pourquoi c'est mieux.
2. Un appel à l'action principal clair, visible sur chaque page clé, et une offre intermédiaire pour qui n'est pas prêt (guide, essai, webinaire).
3. Un formulaire court qui fonctionne, avec une confirmation, et des étiquettes lisibles par un lecteur d'écran.
4. Des preuves et de la confiance : clients, chiffres sourcés, témoignages, auteurs nommés, mentions légales, contact réel (E-E-A-T).
5. L'accessibilité : contrastes, textes alternatifs, navigation au clavier, focus visible (WCAG 2.2 AA, note AIM de WAVE).

**F. GEO et autorité**
1. Données structurées : Organization (avec `sameAs`), plus Product, SoftwareApplication, Service, LocalBusiness, Article ou FAQPage selon les pages.
2. L'accès des IA : les robots des IA ne sont pas bloqués sans raison, un llms.txt est présent ou prévu.
3. L'entité : une page « à propos » avec l'identité, l'adresse, l'année, les dirigeants ; une fiche Wikidata ou des profils cohérents (LinkedIn, annuaires, Google Business Profile si l'activité est locale).
4. Les contenus citables et l'autorité : FAQ, guides de choix, définitions, chiffres sourcés ; des liens et des mentions depuis des sites sérieux.
5. Présence dans les réponses : le panel fixe de 5 questions (`references/panel-geo.md`). Si rien n'a pu être testé, le critère est NV.

Si l'audit précédent utilisait une autre grille, le premier audit avec celle-ci sert de nouveau point de départ : on le dit, sans comparer les notes directement. Les constats, eux, se comparent (`evolution`).

## 5. Les 9 domaines et les tâches

Le dossier range les constats en 9 domaines, toujours les mêmes : faits et cohérence, propreté des pages, blog, vitesse et front-end, serveur et rendu, sécurité et vie privée, ce que Google comprend, expérience et conversion, présence dans les IA. Un site sans blog retire le domaine avec `domain_order`. Chaque domaine a : une phrase qui dit ce que c'est, pourquoi ça compte, un verdict avec un feu, un chiffre clé, ses constats avec captures, ses outils, ses tâches.

Les tâches :
- **Trois to-do**, une par voie, et la première lettre du code dit la voie :
  - **Contenu** (`C1`, `C2`…) : tout ce qui se règle dans l'administration du site ou hors du site, sans développeur (textes, chiffres, fautes, titles, descriptions, images et leurs textes alternatifs, articles, pages, FAQ, Wikidata, profils, annuaires) ;
  - **Front-end** (`F1`…) : ce qui se règle dans le code des pages (gabarits, HTML sémantique, balises, données structurées, images responsives, JavaScript et CSS, polices, accessibilité, formulaires, rendu côté serveur) ;
  - **Back-end et infra** (`B1`…) : ce qui se règle sur le serveur (redirections, codes HTTP, robots.txt, sitemap, en-têtes, cache, compression, CDN, certificat, temps de réponse, cookies et consentement, accès à Search Console et à la mesure).
  Une tâche appartient à une seule voie. Si elle demande deux métiers, on la coupe en deux tâches liées (« après F4 »).
- **Une priorité, jamais une date** : `prio` vaut 1 (P1, bloquant : empêche Google ou les IA de lire le site, ou abîme la confiance), 2 (P2, important : fait perdre des visiteurs, des citations ou des demandes) ou 3 (P3, finition). Aucun délai, aucun effort en jours : une to-do, pas un calendrier.
- Chaque tâche dit la correction précise, adaptée au CMS ou au framework du site quand on le connaît, et « Vérifié quand… » : un contrôle que n'importe qui peut refaire (un outil, une commande, une page).
- `references/checklist-360.md` donne la correction type et la priorité par défaut de chaque contrôle : partir de là, puis adapter au site.
- Les validations : le validateur du site valide les faits et les claims, la personne responsable de la communication valide les nouvelles pages et contenus avant publication.
- On sépare ce que l'équipe maîtrise (les corrections) de ce qui reste incertain (la visibilité). Aucune promesse de classement.

## 6. Les livrables

Tout part de `audit.json` (`references/donnees.md`), rangé avec les sources de l'audit. Dans le dossier du site (indiqué dans `sites.json`) :

1. **Le rapport** `AAAA-MM-JJ Audit SEO GEO - <domaine>.md` : notes, les 30 critères avec leur preuve, constats, panel GEO, annexes.
2. **Le protocole de remesure** `AAAA-MM-JJ Protocole de remesure SEO GEO.md` : adresses exactes, réglages, questions, recherches suivies, seuils de bruit (`remesure` dans `defaults.json`), dates des remesures (le seul endroit où il y a des dates).
3. **Le dossier complet**, figé dans `AAAA-MM-JJ Audit complet/` :
   ```bash
   python3 scripts/build_dossier.py audit.json "<dossier>/AAAA-MM-JJ Audit complet" --captures "<captures>" --pdf --single
   node scripts/build_pptx.js audit.json "<dossier>/AAAA-MM-JJ Audit complet/captures" "<dossier>/AAAA-MM-JJ Audit complet/AAAA-MM-JJ Audit complet - <domaine>.pptx"
   scripts/render_pptx_pdf.sh "<…>.pptx" "<…> - slides.pdf" "<dossier temporaire>/planches"
   ```
   On y obtient `index.html` avec `captures/`, le PDF A4, la page unique (un seul fichier, captures et police intégrées, à envoyer), **la to-do en Markdown** (à cocher, à coller dans un ticket ou un wiki) **et en CSV** (à importer dans Notion, Jira, Linear, Trello ou GitHub Projects), le PowerPoint (90 à 110 slides 16:9) et son PDF. On y copie `audit.json` dans `source/`, avec un LISEZ-MOI.
4. **Une page web** du dossier si l'outil le permet (un artifact Claude, par exemple), privée jusqu'à ce que le commanditaire la partage. Elle reste à usage interne si des concurrents apparaissent dans les captures.
5. **Le bulletin pour la direction** si on le demande : un deck court (12 à 15 slides), concurrents anonymisés, une slide par message, les objectifs en badges sans dates.
6. **La trace** : si le dossier est suivi par git, un commit qui décrit le travail ; jamais de push sans accord.

## 7. Avant de livrer

- `build_dossier.py` s'arrête si `audit.json` est incohérent (tâche citée mais absente, tâche jamais citée, tâche d'une voie inconnue, priorité inconnue, outil sans fiche, critère manquant) ou si une note ne correspond pas aux 30 critères, et signale les noms de concurrents restés dans le texte (`competitors_regex`).
- Les notes du dossier et du PowerPoint sont exactement celles du rapport (même arrondi, même échelle).
- Chaque constat « vérifié » a sa capture ou son lien ; chaque cadre rouge est à la bonne place.
- Chaque P1 est vraiment bloquant ; s'il y a plus de 8 P1, on les relit : une to-do où tout est urgent ne dit plus rien.
- Rendu du dossier dans Chrome à 1280 px et à 375 px (en mode headless, Chrome ne descend pas sous 500 px : mesurer `scrollWidth` plutôt que se fier à la capture).
- Le PowerPoint : planches de `render_pptx_pdf.sh` regardées une à une (texte coupé, débordement, chevauchement). Si la police de la marque n'est pas installée sur la machine, PowerPoint la remplace : le rendu final dépend du poste qui l'ouvre ; le dire au commanditaire.
- Aucun point final dans les titres, aucun champ resté vide, aucune date dans la to-do.

## 8. Pièges connus

- Chrome headless ne produit rien sans `--user-data-dir=<dossier>` ; le script l'ajoute. `build_dossier.py --pdf` cherche Chrome à son emplacement habituel ; sinon, donner son chemin dans la variable `CHROME`.
- Sans PowerPoint, `render_pptx_pdf.sh` passe par LibreOffice (rendu moins fidèle, suffisant pour repérer un débordement).
- PowerPoint sur Mac : il faut ouvrir une copie au nom unique et non cachée (sinon il réexporte l'ancienne version ou renvoie l'erreur -9074). Un export de 100 slides dépasse le délai AppleScript par défaut (le script le porte à 15 min). Si PowerPoint renvoie -9074 sur tous les fichiers, une fenêtre de dialogue l'attend : demander à l'utilisateur de la fermer. Ne jamais fermer ses présentations ouvertes.
- pptxgenjs écrit le fichier sans compression : le script le recompresse.
- Le navigateur intégré de l'application Claude ne lit ni `file://` ni `localhost` : contrôler les pages produites avec Chrome headless, ou les publier en artifact.
- `crawl.py` ne lance pas JavaScript : c'est voulu, il voit le site comme la plupart des robots d'IA. Pour la vitesse vécue, se fier à PageSpeed, pas au crawl.
- Un hébergeur peut répondre « autorisé » dans robots.txt et bloquer quand même les robots des IA au niveau du pare-feu (Cloudflare, par exemple) : si le site est absent des réponses des IA malgré un robots.txt ouvert, le noter comme hypothèse et demander au développeur de vérifier les règles du pare-feu.
- Pour vérifier qu'aucune forme ne sort d'une slide, `python-pptx` suffit si le `validate.py` du skill pptx ne tourne pas.
