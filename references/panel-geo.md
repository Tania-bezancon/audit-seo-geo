# Le panel GEO : ce que répondent les IA

On pose **5 questions fixes** à **4 assistants**, sans compte, et on note si la marque est citée. Le panel se fixe au premier audit d'un site, s'écrit dans `audit.json` (`ia.questions`) et dans le protocole de remesure, puis ne change plus : sinon deux mesures ne se comparent pas.

## Écrire les 5 questions

- **Q1 à Q4, des questions de marché** : celles qu'un acheteur pose sans connaître la marque. Une question en anglais au moins si le site vise l'international. Varier les angles : la catégorie (« quelles solutions de… »), la comparaison avec le leader (« quelle alternative à… »), un cas d'usage précis (« pour une cellule de crise »), le public (« pour une administration »).
- **Q5, la question de marque** : « Qu'est-ce que <marque> ? ». Elle sert à vérifier que les faits repris par les IA sont justes.
- Les questions se valident avec le commanditaire avant la mesure.

Exemple (Atelier Lumen, site fictif d'un logiciel de devis pour artisans) :
1. Quel logiciel de devis et de planning choisir pour un artisan du bâtiment ?
2. Quelle alternative simple aux logiciels de gestion de chantier pour une petite entreprise de plomberie ?
3. Comment faire ses devis sur téléphone quand on est artisan ?
4. Which quoting software do French builders use?
5. Qu'est-ce qu'Atelier Lumen ?

## Les 4 assistants

| Assistant | Adresse (`{q}` = question encodée) | Condition |
|---|---|---|
| ChatGPT | `https://chatgpt.com/?hints=search&q={q}` | sans compte, recherche web activée |
| Google Mode IA | `https://www.google.com/search?hl=fr&gl=fr&udm=50&q={q}` | sans compte, cookies refusés |
| Brave | `https://search.brave.com/ask?q={q}` | sans compte |
| Perplexity | `https://www.perplexity.ai/search?q={q}` | sans compte : une seule question acceptée. Ensuite il demande une inscription, mais la réponse est souvent dans la page : la relever avec `get_page_text` et le dire dans la note |

## Poser et noter

- Une conversation neuve par question. Attendre la fin de la réponse avant la capture (faire défiler si la liste est longue).
- Numéros des captures : Q1 du matin en 03 (Perplexity), 04 (ChatGPT), 05 (Google), 17 (Brave) ; les questions suivantes à partir de 23, assistant par assistant.
- Pour chaque réponse, dans `ia.assistants[].answers[]` : `q`, `cited` (vrai si la marque est nommée), `capture`, `note` (une phrase : ce que l'IA recommande à la place, en anonymisant les concurrents « concurrent A, B… » dans tout ce qui sort de l'équipe), `hour`.
- Sur la question de marque, relever chaque chiffre repris (taille de fichiers, chiffrement, année, nom de l'éditeur, nombre de participants) et le comparer au référentiel : un chiffre faux est un constat du domaine « Faits ». Encadrer ces chiffres en rouge sur la capture (`scripts/annotate.py`).
- Score de catégorie = réponses qui citent la marque ÷ réponses obtenues sur Q1 à Q4. Score de marque = Q5 bien décrite ou non.
- À la remesure : chaque question 3 fois ; une citation compte si elle revient dans 2 passages sur 3.

## Ce qu'on écrit

- Le domaine `d-ia` du dossier (bloc `{"type": "ia"}`) : le tableau des réponses, une phrase « À retenir » (`ia.note`) sur ce que les IA citent à notre place (guides de choix, comparatifs, presse, outils publics), puis chaque IA question par question.
- Le critère E5 de la grille.
- Une ligne au tableau de référence : « Citations sur N réponses de marché ».
- La recherche Wikidata (outil 22) : sans fiche, les IA identifient mal l'éditeur.
