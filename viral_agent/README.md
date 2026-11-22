# 🎬 Viral Agent : vidéos courtes générées par IA

Un agent qui part d'un sujet (ou d'une simple niche) et rend une vidéo verticale **1080×1920 prête à poster**
sur TikTok, Reels et Shorts, avec la miniature, les légendes, les hashtags et l'heure de publication.
Tout est **100 % gratuit** : FreeLLMAPI ou Pollinations pour le texte, Pollinations/Flux pour les images,
Edge TTS pour la voix, ffmpeg pour le montage.

## Les skills de l'agent

| Skill | Fichier | Rôle |
|---|---|---|
| 🔎 Chasseur d'idées | `skills/trends.py` | Trouve des sujets à fort potentiel dans une niche, chacun avec un format viral différent |
| ✍️ Scénariste | `skills/script.py` | Hook en moins de 2 s, open loop, rythme rapide, payoff, fin qui boucle, CTA |
| 🧐 Critique viralité | `skills/critic.py` | Note hook, rétention, émotion, clarté, partage, boucle et **véracité**, puis renvoie en réécriture tant que le score est sous 8/10 |
| 🎨 Directeur artistique | `skills/visuals.py` | Une image IA par scène, 7 styles (cinematic, anime, realistic, dark, 3d, comic, minimal) |
| 🎙️ Voix off | `skills/voice.py` | Voix neuronales dans 7 langues, timing mot par mot |
| 🧬 Labo de voix | `skills/voice_lab.py` | **Crée tes propres voix** : à partir d'une description, avec des réglages manuels et 14 effets, ou par **clonage** d'un enregistrement |
| 💬 Sous-titres | `skills/captions.py` | Style TikTok : gros mots qui « popent », mot courant en jaune, mots-clés en vert |
| ✂️ Monteur | `skills/editor.py` | Ken Burns varié, flash entre les scènes, barre de progression, musique avec ducking, volume normalisé à -14 LUFS |
| 📈 SEO / publication | `skills/seo.py` | Légendes et hashtags par plateforme, titre Shorts, commentaire à épingler, heures de post, idées de suites |

Le savoir viral commun à toutes les skills se trouve dans `skills/playbook.py`. Modifie ce fichier pour adapter l'agent à ton style.

## Installation

```bash
pip install -r requirements.txt     # plus ffmpeg : apt install ffmpeg / brew install ffmpeg
```

### Brancher FreeLLMAPI (recommandé, nettement meilleurs scripts)

```bash
curl -fsSL https://freellmapi.co/install.sh | bash    # lance FreeLLMAPI sur http://localhost:3001
# Dans le dashboard, ajoute tes clés gratuites (Groq, Gemini, OpenRouter…) puis copie la clé unifiée
export LLM_API_KEY="freellmapi-xxxxxxxx"
export LLM_MODEL="auto"          # ou auto:smart, ou un modèle précis
```

Sans FreeLLMAPI, l'agent bascule tout seul sur Pollinations (gratuit, sans clé). Ce modèle est plus faible
et son quota anonyme est limité, donc les scripts sont moins bons et la génération plus lente.

## Utilisation

```bash
# Une vidéo à partir d'un sujet
python -m viral_agent make "Pourquoi les flamants roses sont roses" --style realistic --voice female

# Trouver des idées virales dans une niche
python -m viral_agent ideas "finance perso pour les 18-25 ans" -n 10

# Pilote automatique : l'agent choisit les 3 meilleures idées et produit les 3 vidéos
python -m viral_agent auto "faits historiques choquants" -n 3 --style dark --music musique.mp3

# Script seul, avec son score viral
python -m viral_agent script "Le secret des pyramides"
```

Options utiles : `--lang fr|en|es|de|it|pt|ar`, `--duration 35`, `--tone drôle|mystérieux|motivant`,
`--rate +15%` (voix plus rapide), `--voice-name fr-FR-VivienneMultilingualNeural`, `--captions low`.

### Ce que l'agent produit (`output/<date>-<titre>/`)

- `video.mp4` : la vidéo finale
- `cover.jpg` : la miniature avec son texte
- `POST.md` : tout ce qu'il faut copier-coller pour publier, plus 3 hooks alternatifs pour faire de l'A/B test
- `publish.json` et `script.json` : les données brutes

## 🧬 Créer une voix pour tes vidéos

Chaque voix créée devient un profil réutilisable (`voices/<nom>.json`), que tu passes à n'importe quelle vidéo
avec `--voice-profile <nom>`. C'est ce qui donne une identité sonore à ta chaîne.

### 1. Décrire la voix (gratuit, immédiat)
```bash
python -m viral_agent voice design horreur "conteuse mystérieuse et posée, ambiance pesante"
python -m viral_agent voice preview horreur            # écoute
python -m viral_agent make "La maison abandonnée de Lyon" --voice-profile horreur --style dark
```
L'IA choisit la meilleure voix de base parmi toutes les voix de la langue, puis règle le débit, la hauteur et les effets.

### 2. Régler la voix soi-même
```bash
python -m viral_agent voice catalog --lang fr          # toutes les voix de base disponibles
python -m viral_agent voice effects                    # les 14 effets
python -m viral_agent voice create narrateur --base fr-FR-HenriNeural --pitch -6Hz --rate +5% --effects deep,broadcast
```
Effets : `deep`, `deeper`, `high`, `chipmunk`, `warm`, `broadcast`, `crisp`, `radio`, `phone`, `robot`,
`whisper`, `echo`, `cave` et `demon`, plus `af:<filtre ffmpeg>` pour les experts. Les effets de hauteur ne changent
pas la durée, donc les sous-titres restent calés.

### 3. Cloner TA voix
Enregistre 10 à 20 secondes de parole claire au téléphone, dans une pièce calme, avec un ton naturel. Ensuite :
```bash
pip install -r requirements-clone.txt --extra-index-url https://download.pytorch.org/whl/cpu   # une seule fois
python -m viral_agent voice clone moi --sample ma_voix.m4a --consent
python -m viral_agent voice preview moi "Salut, c'est moi, et aujourd'hui je te montre un truc fou."
python -m viral_agent make "ton sujet" --voice-profile moi
```
- **Chatterbox** (par défaut) est gratuit, tourne en local et gère 23 langues dont le français. Le modèle (~2 Go)
  se télécharge au premier usage. Compte environ 10 s de calcul par scène sur CPU, beaucoup moins avec un GPU.
  Règle l'expressivité avec `--exaggeration 0.3` (calme) à `0.8` (très expressif).
- **ElevenLabs** donne la qualité studio : `export ELEVENLABS_API_KEY=...` puis `--engine elevenlabs`.
- L'échantillon est nettoyé automatiquement : débruitage, silences retirés, normalisation.
- Les timings mot à mot des sous-titres viennent de faster-whisper. Sans lui, ils sont estimés.
- `--consent` est obligatoire. Ne clone que ta voix ou celle d'une personne qui t'a donné son accord.
  Cloner une célébrité ou une personne réelle sans accord est illégal dans beaucoup de pays et fait bannir les comptes.
  Chatterbox ajoute aussi un watermark inaudible à l'audio généré.

## 🔊 Banque de sons et « oreilles »

| Source | Rôle |
|---|---|
| **earshot** ([Leonxlnx/earshot](https://github.com/Leonxlnx/earshot), MIT) | Génère un bruitage à partir d'une description, sur CPU, en quelques secondes : whoosh, impacts, ambiances… Libre d'utilisation sans crédit. |
| **Openverse** ([api.openverse.org](https://api.openverse.org)) | Vrais enregistrements Freesound sous licence **CC0**. Les crédits sont ajoutés automatiquement à `sounds/CREDITS.md`. |
| **Oreilles** (`listen`) | Mesure le volume (LUFS), la crête, la dynamique et les silences, et dessine un spectrogramme pour repérer une voix noyée, une saturation ou un trou dans le son. |

```bash
pip install "earshot @ git+https://github.com/Leonxlnx/earshot" "librosa>=0.10"
python -m viral_agent sound make "a deep cinematic impact boom" --out boom.wav
python -m viral_agent sound find "ocean waves" --get 0
python -m viral_agent sound listen output/wardogs-partie-01/video.mp4 --picture ears.png
```

Dans les séries, chaque scène reçoit automatiquement :
- une **ambiance** déduite de l'image (plage, désert, bureau, entrepôt, tribunal…) ;
- des **bruitages** calés sur l'action : whoosh à l'arrivée d'un bandeau, alerte si le bandeau est rouge, tiroir-caisse s'il est vert, impact ou montée de tension sur les mouvements de caméra, téléphone, coups à la porte…

Le tout est mixé sous la voix avec ducking, et le rendu final est contrôlé à l'oreille. Tu peux imposer les sons
d'une scène dans la bible avec `"sfx": ["impact", "phone"]` et `"ambience": "rain on a car roof"`.
Réglages de série : `"sound": false`, `"sound_source": "openverse"`, `"ambience_db": -17`.

## 📺 Séries (ex. 30 TikToks d'une minute)

Le mode série produit des épisodes au **style POV** : vue à la première personne avec les mains en bas de l'écran,
personnages cartoon 3D, bandeaux d'alerte qui glissent du haut, sous-titres arrondis colorés par personnage,
plusieurs voix, pastille « PARTIE 3/30 » et carte « À SUIVRE » automatique à la fin.

```bash
python -m viral_agent series series/wardogs.json --episodes 1-30 --skip-done
python -m viral_agent series series/wardogs.json --episodes 5        # un seul épisode
```

Tout est décrit dans une « bible » JSON (`series/wardogs.json`, générée depuis `series/source/`) :
- `voices` : une voix par personnage (Edge TTS ou profil du labo de voix via `"profile": "moi"`) et la couleur de ses sous-titres.
- `characters` : la description visuelle fixe de chaque personnage, ajoutée à chaque image où il apparaît.
- `episodes[].scenes[]` : `visual` (description de l'image), `chars`, `move` (`walk`, `run`, `shake`, `push`,
  `zoom_in`…), `banner` (`label`, `title`, `subtitle`, `color` : red, blue, green, black, orange ou purple),
  et `lines` (`{"s": "efraim", "t": "texte"}`).

Pour mettre **ta propre voix** sur le narrateur, clone-la (voir plus haut) puis remplace l'entrée `narrateur`
par `{"profile": "moi", "color": "#FFFFFF"}`.

> **Images.** Sans clé, Pollinations limite à 1 image toutes les 45 s, avec un modèle basique : compte environ
> 10 min par épisode et un style approximatif. Avec une clé gratuite (https://enter.pollinations.ai), mets
> `export POLLINATIONS_TOKEN=...`. Le rendu devient plus rapide, les images sont générées en parallèle et le modèle
> Flux est bien meilleur pour le style POV cartoon.

## Variables d'environnement

| Variable | Défaut | |
|---|---|---|
| `LLM_BASE_URL` | `http://localhost:3001/v1` | N'importe quel endpoint compatible OpenAI |
| `LLM_API_KEY` / `FREELLMAPI_KEY` | (vide) | Clé unifiée FreeLLMAPI |
| `LLM_MODEL` | `auto` | |
| `FALLBACK_LLM_URL` | Pollinations | Mets une valeur vide pour désactiver le fallback |
| `POLLINATIONS_TOKEN` | (vide) | Token gratuit pour des limites d'images plus hautes |
| `MIN_VIRAL_SCORE` | `8` | Score à atteindre avant de lancer le rendu |
| `MAX_REWRITES` | `2` | Nombre maximum de réécritures du script |
| `VOICES_DIR` | `voices` | Dossier des voix créées |
| `ELEVENLABS_API_KEY` | (vide) | Pour le clonage ElevenLabs |
| `WHISPER_MODEL` | `base` | Modèle d'alignement des sous-titres (tiny, base, small…) |

## Conseils pour percer

1. Poste **tous les jours** pendant 30 jours sur la même niche. L'algorithme récompense la régularité.
2. Utilise `auto` pour produire une semaine de vidéos d'un coup, puis garde les meilleures.
3. Teste les hooks alternatifs de `POST.md` : reposte la même vidéo avec un autre hook si elle ne décolle pas.
4. Réponds aux commentaires dans la première heure.
5. Mets une musique tendance **depuis l'app** (TikTok ou Instagram) au moment de poster. Ça booste la portée et évite les problèmes de droits.
