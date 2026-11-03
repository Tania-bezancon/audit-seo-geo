# audit.json : le seul fichier à écrire pour un audit

Le dossier HTML, le PDF, la page unique et le PowerPoint se fabriquent tous à partir de `audit.json`. On ne retouche jamais les fichiers produits : on corrige `audit.json` et on relance les scripts.

Point de départ : copier `assets/exemple/audit.json` (l'audit fictif complet d'Atelier Lumen) et remplacer chaque valeur. Le contenu commun à tous les sites (outils, rôles, lexique, règles de remesure, catégories, domaines) est dans `assets/defaults.json` ; une clé de même nom dans `audit.json` le remplace (`lexique`, `remesure`).

## Mise en forme du texte

Dans toutes les chaînes : `**gras**`, `` `code` `` et, dans les extraits de code (`code`), `[[surligné en rouge]]` pour montrer le défaut. Aucun point final dans les titres (`title`, `headline`, `stat_label`, titres de blocs).

## Les clés

| Clé | Contenu |
|---|---|
| `site` | `domain`, `url` (page testée), `brand`, `brand_q` (recherche de marque), `theme` (`signature` par défaut, `neutre` ou un thème ajouté ; voir `assets/themes.json`), `lang`, `country`, `date` (AAAA-MM-JJ), `date_label` (« 2 novembre 2026 »), `date_long` (« lundi 2 novembre 2026 »), `perimetre` (une ligne), `pages` (nombre), `prepared_by`, `usage` (« usage interne » si des concurrents sont nommés), `validateur` (« le CTO »), `who` (facultatif, renomme les voies : `{"C": "Communication", "F": "Agence web"}`) |
| `lead`, `headline` | La phrase d'introduction du dossier, et le titre-message de la note (« Un site bien construit, mal réglé… ») |
| `note` | `global` (« 5,1 ») et `categories` (`{"A": "7,0", … "F": "2,0"}`), calculées avec la grille du SKILL.md ; `build_dossier.py` les recalcule et s'arrête si elles diffèrent |
| `bulletin` | Par domaine (`d-faits`, `d-pages`, `d-blog`, `d-vitesse`, `d-infra`, `d-securite`, `d-google`, `d-conversion`, `d-ia`) : `[feu, phrase]`, feu = `v`, `o` ou `r` |
| `good`, `bad`, `decisions` | 3 à 5 phrases chacune : ce qui va bien, ce qui bloque, les décisions demandées à la direction |
| `conditions`, `limites` | Les conditions de la mesure (`[libellé, texte]`) et ce que la mesure ne dit pas |
| `resultats` | Par outil (clé de `defaults.outils`, ou nom de l'assistant) : `[résultat en une ligne, feu]`. Un outil absent de `resultats` n'apparaît pas |
| `fiches` | Par outil capturé : `who`, `big` (la note en gros), `pills` (`[[ok|warn|bad, texte]]`), `bullets` (2 à 4 constats), `says` (« À retenir »), `capture` (nom du fichier), `caption` (légende avec date et heure) |
| `domaines` | Voir ci-dessous |
| `ia` | `questions` (`{"1": "…"}`), `brand_question` (5), `intro`, `note`, `assistants` : `[{name, how, answers: [{q, cited, capture, note, hour}]}]` (voir `panel-geo.md`) |
| `tasks` | Par code (`C1`… contenu, `F1`… front-end, `B1`… back-end et infra ; voir `voies` dans `defaults.json`) : `name`, `what` (la correction précise), `check` (« Vérifié quand… »), `prio` (1, 2 ou 3 ; 2 par défaut). Aucune date, aucun délai |
| `todo` | Facultatif : `{"C": [[groupe, [codes]]], "F": [...], "B": [...]}` pour grouper par thème. Sans cette clé, chaque to-do est rangée par priorité (P1, P2, P3) |
| `todo_intro`, `validations` | Le partage des rôles en une phrase, et qui valide quoi (« Le CTO valide… », « La direction de la communication valide… ») |
| `concurrents` | Facultatif, interne : `title`, `head` (`["Mesure", "Nous", "A", …]`), `rows`, `note`. Concurrents anonymisés A, B, C… |
| `reference` | `rows` : `[domaine, mesure, valeur du jour, objectif]` pour chaque chiffre suivi ; `missing` (ce qu'il manque pour un point de départ complet) ; `tasks` (les tâches qui relèvent ce qui manque) |
| `criteres` | Les 30 lignes de la grille : `[code, critère, note "0"/"1"/"2"/"NV", preuve]` |
| `evolution` | Facultatif : `title`, `intro`, `head`, `rows` (constats de l'audit précédent → état du jour) |
| `fautes` | `[["p", "Mots collés (…) :"], ["li", "FR : …"], ["note", "…"]]` |
| `captures` | Index : par numéro (`"01"`, `"site-03"`) : `[outil ou page, ce qu'elle montre, heure, domaine]` |
| `documents` | `[libellé, chemin ou URL]` : rapport, to-do, protocole, captures, artifacts |
| `footer_note`, `competitors_regex` | La note de bas de page (claims à valider), et une expression (« A|B|C ») : le script signale tout nom de concurrent resté dans le texte |
| `domain_order` | Facultatif : ordre ou sous-ensemble des domaines |

## Un domaine

```json
"d-faits": {
  "title": "Les mêmes faits ne disent pas la même chose d'une page à l'autre",
  "feu": "r",
  "une": "Ce que c'est, en une phrase",
  "pourquoi": "Pourquoi ça compte pour un acheteur, pour Google ou pour les IA",
  "verdict": "Le constat en une phrase",
  "stat": "6", "stat_label": "contradictions relevées, dont 3 déjà affichées par Google",
  "blocks": [ … ],
  "tools": ["06", "21"],
  "tools_label": "facultatif, remplace « Ce que disent les outils »",
  "tasks": ["C1", "C2", "B4"]
}
```

Les blocs, dans l'ordre de lecture :

| `type` | Champs | Rendu |
|---|---|---|
| `finding` | `title`, `where` (page et adresse), `paras`, `list`, `code`, `captures` (`[[préfixe, légende]]`, une ou deux), `note` | Un constat : texte à gauche, capture à droite (deux captures côte à côte pour le téléphone) |
| `table` | `title`, `head`, `rows`, `colw` (largeurs en pouces dans le PowerPoint, total 12,13) | Un tableau large (contradictions…) |
| `stats` | `title`, `head`, `rows` (2 colonnes), `role` (clé d'outil dont on affiche le rôle), `role_title` | Un relevé chiffré, avec l'encadré « À quoi sert cet outil » |
| `tri` | `title`, `head`, `rows`, `tri_title`, `tri` (`[[nombre, action, détail, feu]]`), `tri_note` | Chiffres + plan de tri (le blog) |
| `note` | `text`, `label`, `title` | Un encadré seul |
| `ia` | (rien) | Le tableau des réponses des IA et chaque IA question par question, à partir de la clé `ia` |

Le dossier écrit aussi la to-do à part, en Markdown et en CSV (`AAAA-MM-JJ To-do SEO GEO - <domaine>.md` et `.csv`).

Chaque tâche citée dans un domaine doit exister dans `tasks`, et chaque tâche de `tasks` doit apparaître dans un domaine ou dans `reference.tasks`.
