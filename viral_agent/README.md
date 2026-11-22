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

## Conseils pour percer

1. Poste **tous les jours** pendant 30 jours sur la même niche. L'algorithme récompense la régularité.
2. Utilise `auto` pour produire une semaine de vidéos d'un coup, puis garde les meilleures.
3. Teste les hooks alternatifs de `POST.md` : reposte la même vidéo avec un autre hook si elle ne décolle pas.
4. Réponds aux commentaires dans la première heure.
5. Mets une musique tendance **depuis l'app** (TikTok ou Instagram) au moment de poster. Ça booste la portée et évite les problèmes de droits.
