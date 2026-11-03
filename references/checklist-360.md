# La checklist 360°

Tous les contrôles de l'audit, rangés par voie : **Contenu** (`C`), **Front-end** (`F`), **Back-end et infra** (`B`). Chaque ligne dit comment le vérifier, la correction type, la priorité par défaut et le critère de la grille qu'elle touche. On part de la correction type, puis on l'adapte au site : son CMS ou son framework, ses pages, ses chiffres.

Priorités : **P1** bloquant (Google ou les IA ne peuvent pas lire le site, ou la confiance est abîmée), **P2** important (fait perdre des visiteurs, des citations ou des demandes), **P3** finition. Une priorité peut monter ou descendre selon le site : une fausse 404 sur un site de 10 pages est P2, sur un site de 5 000 pages elle est P1.

Sources des preuves : `summary.json` et `checks.json` du crawl (clé entre crochets), les outils par leur numéro (`references/outils.md`), le panel IA (`panel-geo.md`), ou une capture du site.

## Contenu · ce qui se règle sans développeur

| Contrôle | Preuve | Correction type | Vérifié quand | Prio | Critère |
|---|---|---|---|---|---|
| Les mêmes faits partout (clients, année, équipe, certifications, prix) | captures site, outil 06, Q5 du panel | Une fiche de faits validée, reportée sur chaque page | la recherche « site: » n'affiche plus qu'une version | P1 | D4 |
| Titles uniques et descriptifs (50 à 60 caractères, le sujet d'abord, la marque à la fin) | [titres_doublons], [titres_longs_65] | Réécrire chaque title en défaut | le crawl ne trouve ni doublon ni title de plus de 65 caractères | P2 | D1 |
| Descriptions présentes (140 à 160 caractères, une promesse et un appel) | [sans_description] | Écrire une description par page | le crawl compte 0 page sans description | P2 | D1 |
| Aperçu de partage (titre, description, image 1200 × 630) | [sans_open_graph], outil 40 | Remplir les champs de partage du CMS | l'aperçu de l'outil 40 est complet | P3 | D1 |
| Un H1 par page, des H2 qui découpent la page | [h1_different_de_1] | Corriger les titres dans l'éditeur | le crawl compte 0 page en défaut | P2 | D2 |
| Mots collés, fautes | [mots_colles], `lt-<lang>.json` | Corriger chaque alerte relue | lt.py ne renvoie plus que des faux positifs | P2 | D4 |
| Textes alternatifs des images utiles (décoratives : alt vide) | [images_sans_alt], outil 15 | Décrire chaque image utile dans le CMS | WAVE ne signale plus d'image sans description | P2 | E5 |
| Pages qui répondent aux questions du public (pas seulement des slogans) | [pages_maigres_300_mots], lecture | Ajouter à chaque page clé les questions, les cas d'usage, les chiffres | chaque page clé dépasse 300 mots utiles | P2 | D3 |
| Blog daté, récent, sans article périmé en avant | [pages_datees], captures blog | Trier : garder, fusionner, retirer (avec redirection, voir B) | plus aucun article périmé en première page | P2 | D5 |
| Traductions complètes, sans reste d'une autre langue | [lang], captures | Traduire ou retirer la page de la langue | chaque langue n'a que des pages dans sa langue | P2 | D5 |
| Une page « à propos » qui identifie l'entreprise (nom légal, adresse, année, dirigeants, chiffres sourcés) | capture site-03 | Compléter la page | les 4 éléments sont en ligne | P1 | F3 |
| Auteurs nommés et dates sur les articles | lecture | Ajouter un auteur réel et une date à chaque article | chaque article a les deux | P3 | E4 |
| Preuves : clients, témoignages, chiffres sourcés, labels | capture site-02 | Ajouter des preuves avec leur contexte | l'accueil montre au moins 3 preuves vérifiables | P2 | E4 |
| Un appel à l'action principal sur chaque page clé | captures | Ajouter le bouton principal aux pages qui n'en ont pas | chaque page clé a son appel | P2 | E2 |
| Une offre intermédiaire (guide, grille, essai, webinaire) | lecture | Créer l'offre et la relier aux pages | l'offre est en ligne avec son formulaire | P3 | E2 |
| FAQ, guides de choix, définitions | lecture, panel IA | Écrire les pages que les IA citent à notre place | les pages sont en ligne et reliées entre elles | P2 | F4 |
| Fiche Wikidata, profils cohérents (LinkedIn, annuaires) | outil 22 | Créer ou corriger la fiche, aligner les profils | la fiche existe avec le site officiel | P3 | F3 |
| Fiche Google Business Profile (activité locale seulement) | recherche de marque | Créer ou compléter la fiche (horaires, catégorie, photos, avis) | la fiche s'affiche sur la recherche de marque | P2 | F3 |
| Liens et mentions depuis des sites sérieux | outil 41 | Viser la presse spécialisée, les partenaires, les annuaires du secteur | de nouveaux domaines renvoient vers le site | P3 | F4 |
| Faits repris par les IA justes (Q5) | panel IA | Corriger la source qu'elles citent (page, profil, Wikidata) | Q5 ne contient plus de chiffre faux à la remesure | P2 | F5 |

## Front-end · ce qui se règle dans le code des pages

| Contrôle | Preuve | Correction type | Vérifié quand | Prio | Critère |
|---|---|---|---|---|---|
| Contenu lisible sans JavaScript | [rendu_js_probable], page sans JS | Rendu côté serveur ou génération statique (SSR, SSG) pour les pages publiques | le HTML reçu contient le texte principal et les liens | P1 | A4 |
| Liens en vraies balises `<a href>` | lecture du HTML | Remplacer les liens en JavaScript (`onclick`) par des liens | chaque lien du menu a son `href` | P1 | A4 |
| Balises de tête dans le HTML reçu (title, description, canonical, hreflang, robots) | crawl | Les générer côté serveur, une fois par page | le crawl les trouve sur chaque page | P1 | A2 |
| Données structurées par type de page | outils 07 et 16, [jsonld_types] | Organization (avec `sameAs`) sur tout le site ; Product, SoftwareApplication, Service, LocalBusiness, Article, FAQPage, BreadcrumbList selon les pages | le test des résultats enrichis les détecte sans erreur | P2 | F1 |
| LCP sous 2,5 s | outils 01 et 09 | Image principale en priorité (`fetchpriority="high"`, pas de lazy), préchargée, au bon format | PageSpeed mobile ≥ 75 sur 3 passages | P2 | B1, B2 |
| INP sous 200 ms | outil 09 (données réelles) | Découper les tâches JavaScript longues, différer les scripts tiers | l'INP réel passe au vert | P2 | B1 |
| CLS sous 0,1 | outils 01 et 09 | Dimensions sur les images et les vidéos, place réservée aux bandeaux, `font-display: swap` avec polices ajustées | le CLS passe au vert | P2 | B1 |
| Images au bon format et à la bonne taille | outil 01, [html_lourd_100ko] | WebP ou AVIF, `srcset` et `sizes`, `loading="lazy"` sous la ligne de flottaison | PageSpeed ne signale plus d'image à optimiser | P2 | B3 |
| JavaScript et CSS bloquants ou inutilisés | outil 01 | Différer (`defer`), découper, retirer le code mort, CSS critique en ligne | PageSpeed ne signale plus de ressource bloquante | P2 | B4 |
| Polices | outil 01 | Auto-héberger, précharger, limiter les graisses, sous-ensembles | pas de saut de texte au chargement | P3 | B4 |
| Contenu mixte http | [contenu_mixte_http] | Passer chaque ressource en https | le crawl compte 0 page en défaut | P1 | B4 |
| Viewport et affichage à 375 px | [sans_viewport], captures site-08 et 09 | `<meta name="viewport" content="width=device-width, initial-scale=1">`, grilles qui se replient | pas de défilement horizontal à 375 px | P1 | B5 |
| Zones cliquables d'au moins 24 × 24 px | outil 01 (accessibilité) | Agrandir boutons et liens du menu mobile | Lighthouse ne signale plus de cible trop petite | P3 | B5 |
| Contrastes | outil 15 | Foncer les textes clairs (4,5:1 pour le texte courant) | WAVE ne signale plus de contraste | P2 | E5 |
| Navigation au clavier et focus visible | test à la main (Tab) | Style `:focus-visible`, ordre logique, lien « aller au contenu » | on parcourt la page au clavier sans se perdre | P2 | E5 |
| Formulaire accessible et qui confirme | capture site-05 | Étiquettes `<label>`, messages d'erreur clairs, confirmation | WAVE ne signale rien sur le formulaire | P2 | E3 |
| HTML valide et sémantique (`header`, `nav`, `main`, `footer`) | outil 10 | Corriger les erreurs du gabarit | le validateur W3C compte moins de 5 erreurs | P3 | D2 |
| Fil d'Ariane et liens entre pages proches | lecture | Fil d'Ariane, blocs « à lire aussi » | chaque page utile reçoit au moins 3 liens internes | P3 | A5 |
| Pagination et filtres | crawl | Pages de liste indexables, filtres en `noindex` ou canonical vers la liste | pas de milliers d'adresses de filtres dans le crawl | P2 | A5 |

## Back-end et infra · ce qui se règle sur le serveur

| Contrôle | Preuve | Correction type | Vérifié quand | Prio | Critère |
|---|---|---|---|---|---|
| Accès à Search Console et Bing Webmaster Tools | — | Valider le domaine (enregistrement DNS), y déclarer le sitemap | les clics et les positions sont lisibles | P1 | (limites) |
| robots.txt n'empêche rien d'utile | `robots.txt` du crawl, [robots_bloque] | Retirer les blocages de CSS, JS, images, pages utiles | le crawl ne trouve plus de blocage utile | P1 | A1 |
| Robots des IA | [robots_ia] dans `checks.json` | Autoriser au moins les robots de recherche (OAI-SearchBot, ChatGPT-User, PerplexityBot, ClaudeBot, Bingbot) ; décider en conscience pour ceux d'entraînement (GPTBot, Google-Extended, CCBot) ; vérifier aussi le pare-feu | les robots voulus sont « autorisé » et le pare-feu ne les bloque pas | P1 | F2 |
| llms.txt | [llms_txt] | Publier `/llms.txt` : une phrase sur l'entreprise et les liens vers les pages de référence | `/llms.txt` répond 200 | P3 | F2 |
| Sitemap complet et à jour | [plan_du_site], [pages_hors_plan] | Générer le sitemap automatiquement, avec `lastmod`, et le déclarer dans robots.txt | les pages utiles y sont toutes, et rien d'autre | P2 | A1 |
| Une seule adresse par page | [checks.autre_hote], [checks.http], [sans_canonical] | Redirections 301 vers la version https choisie (avec ou sans www), canonical sur chaque page | les autres versions redirigent en une seule étape | P1 | A2 |
| hreflang (sites en plusieurs langues) | crawl | Balises réciproques, `x-default` | chaque langue renvoie vers les autres | P2 | A2 |
| Vraie 404 | [checks.fausse_404] | Renvoyer le code 404 sur une adresse inconnue, avec une page utile | `checks.json` indique « vraie 404 » | P2 | A3 |
| Pas de liens cassés ni de chaînes de redirections | [codes] | Corriger les liens, rediriger en une étape | le crawl ne compte plus de 404 ni de chaîne | P2 | A3 |
| Redirections des pages retirées | tri du blog | Une 301 vers la page la plus proche, jamais vers l'accueil par défaut | chaque ancienne adresse redirige vers une page proche | P2 | A3 |
| Pas d'erreurs 5xx | [codes] | Corriger la cause côté serveur, surveiller | le crawl ne compte plus de 5xx | P1 | A3 |
| Certificat, TLS, HSTS | outils 13 et 14 | TLS 1.2 et 1.3 seulement, HSTS avec `max-age` d'au moins 6 mois | SSL Labs donne A ou A+ | P1 | C1 |
| En-têtes de sécurité | outils 02 et 08, [checks.accueil.securite] | Content-Security-Policy, X-Content-Type-Options, frame-ancestors ou X-Frame-Options, Referrer-Policy, Permissions-Policy | Security Headers donne B ou mieux | P2 | C2 |
| Version du serveur masquée | [version_serveur_affichee] | Retirer la version des en-têtes `Server` et `X-Powered-By` | aucune version n'apparaît | P3 | C2 |
| Compression | [checks.accueil.compression] | Brotli (ou gzip) sur HTML, CSS, JS, SVG | la compression n'est plus « aucune » | P2 | C3 |
| Cache des fichiers statiques | [sans_cache], outil 01 | `Cache-Control: public, max-age=31536000, immutable` sur les fichiers versionnés | PageSpeed ne signale plus de cache trop court | P2 | C3 |
| HTTP/2 ou HTTP/3, CDN | outil 14, en-têtes | Activer chez l'hébergeur ou le CDN | le test le confirme | P3 | C3 |
| Temps de réponse du serveur | [ttfb_median_ms], outil 01 | Cache de pages, CDN, requêtes en base plus légères | TTFB médian sous 800 ms | P2 | C4 |
| Aucun traceur avant consentement | outils 11 et 12, capture site-01 | Bloquer les scripts tiers jusqu'au clic, mode de consentement | Webbkoll ne voit aucune requête tierce avant accord | P1 | C5 |
| Un refus aussi simple que l'acceptation | capture site-01 | Bouton « Refuser » au même niveau que « Accepter » | le bandeau a les deux boutons | P2 | C5 |
| Mesure d'audience en place et conforme | lecture, outil 12 | Outil de mesure respectueux ou soumis au consentement, objectifs de conversion déclarés | les demandes sont comptées | P2 | (limites) |
| Sauvegardes et surveillance de disponibilité | — | Surveillance de l'accueil et du formulaire, alerte en cas de panne | une alerte de test arrive | P3 | C4 |

## Ce qui ne se coche pas

- **Une position dans Google** ou **une citation par une IA** : ce sont des résultats, pas des tâches. Ils se suivent dans le tableau de référence et à la remesure.
- **Le volume de trafic** (Similarweb) : une tendance, jamais un objectif.
