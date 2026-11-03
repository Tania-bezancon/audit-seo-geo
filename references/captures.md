# Les captures de preuve

Chaque constat « vérifié » a sa capture ou son lien. Les captures sont réelles, prises le jour de la mesure, jamais retouchées : seuls des cadres rouges montrent le défaut.

## Où et comment les ranger

- Dossier : `<marque>/4 Suivi/captures-audit/AAAA-MM-JJ/`, avec un sous-dossier `site/` pour les captures des pages du site.
- Noms : `NN-sujet.jpg` pour les outils et les IA (numéros fixes, voir `outils.md` et `panel-geo.md`), `site-NN-sujet.jpg` pour les pages du site. Le numéro reste le même d'un audit à l'autre.
- Le dossier HTML et le PowerPoint retrouvent une capture par le début de son nom (`"06"`, `"site-03"`) : deux fichiers ne doivent pas commencer pareil.

## Les captures du site à prendre à chaque audit

| N° | Page | Ce qu'on montre |
|---|---|---|
| site-01 | Accueil, au premier affichage | Le bandeau cookies. Relever en même temps les requêtes réseau (`read_network_requests`) : si Google Analytics, LinkedIn ou d'autres partent avant le clic, c'est un constat |
| site-02 | Accueil, bloc des preuves | Logos, chiffres, témoignages : avec ou sans contexte |
| site-03 | À propos | Les faits (année, éditeur, adresse) à comparer avec le title, les balises de partage et le référentiel |
| site-04 | Une page produit ou cas d'usage | Fautes ou mots collés, encadrés |
| site-05 | Contact ou demande de démo | Champs obligatoires, captcha, promesse de délai |
| site-06 | Une page d'une autre langue | Traduction absente, titre dans une autre langue |
| site-07 | Le blog, la page la plus ancienne | Dates, images génériques |
| site-08, 09 | Accueil en 375 px | Écran vide, puis contenu affiché (préréglage `mobile` de `resize_window`, puis revenir à `desktop`) |

On en ajoute autant que nécessaire (site-10…), toujours une capture par constat.

## Pièges connus

- La première capture du navigateur intégré sort souvent vide ou en fondu : en prendre une à `scale: 0.1`, puis la vraie.
- Préréglage desktop : fenêtre de 1024 px, image de 800 px. Les coordonnées de la page se multiplient par 0,78125 pour placer un cadre.
- Vérifier chaque cadre rouge sur une planche contact : un cadre mal placé décrédibilise le constat.
- Un bandeau cookies refusé reste refusé dans le profil du navigateur intégré : pour site-01, ouvrir l'accueil dans un nouvel onglet en navigation sans historique si le bandeau ne s'affiche plus, ou le noter.
- Ne jamais capturer un espace connecté de production (l'application des clients, un intranet) : noms de collègues et fichiers internes.
- Les captures des IA montrent les noms des concurrents : le dossier complet reste à usage interne. Le deck pour la direction les anonymise (A, B, C…).
