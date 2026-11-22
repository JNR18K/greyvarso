# War Dogs : l'histoire vraie (série POV, 30 × 1 min)

Série originale en 30 épisodes qui raconte, du point de vue de David, l'histoire vraie d'AEY Inc. (2005-2008) :
deux jeunes de Miami décrochent un contrat de près de 300 millions de dollars avec le Pentagone, puis tombent pour
avoir revendu des munitions chinoises réemballées. L'histoire a aussi inspiré le film *War Dogs* (2016).

- Narration, dialogues et scènes sont **écrits pour cette série**. Ce n'est pas une copie du film.
- Les personnages secondaires inventés (Léa, Klaus « le Fantôme », Arben) sont des personnages originaux.
- Les designs cartoon sont originaux : ils ne reprennent pas les acteurs du film.
- Les faits principaux suivent ce qui est public : contrat afghan d'environ 298 M$, munitions chinoises venues
  d'Albanie et réemballées, enquête du New York Times en mars 2008, 4 ans de prison pour Efraim Diveroli et
  7 mois d'assignation à résidence pour David Packouz. Le reste est dramatisé, ce qu'indique la légende de chaque post.

| Arc | Épisodes |
|---|---|
| Le masseur fauché, Efraim, les miettes du Pentagone | 1-5 |
| La livraison en Irak | 6-10 |
| Ralph, Las Vegas, le Fantôme, le contrat à 300 M$ | 11-15 |
| L'Albanie, les caisses chinoises, l'usine à cartons | 16-20 |
| La trahison, la menace, l'article, le FBI | 21-25 |
| Le procès, le bracelet, les leçons, la fin | 26-30 |

Rendu : `python -m viral_agent series series/wardogs.json --episodes 1-30 --skip-done`
Modifier les scripts : éditer `source/ep*.py` puis `cd source && python build.py ../wardogs.json ep01_10 ep11_20 ep21_30`.
