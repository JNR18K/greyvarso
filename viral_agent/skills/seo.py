"""Skill : SEO / publication. Titre, description, hashtags, commentaire épinglé par plateforme."""
import json
from .playbook import LANG_NAMES


def make_metadata(llm, script, lang="fr", niche=""):
    system = ("Tu es expert en croissance sur TikTok, Instagram Reels et YouTube Shorts. Tu connais le SEO de chaque "
              "plateforme, les hashtags qui ramènent de la portée sans être génériques, et les meilleures heures de post.")
    user = f"""Script : {json.dumps(script, ensure_ascii=False)}
Niche : {niche or 'déduis-la'}
Langue : {LANG_NAMES.get(lang, lang)}

JSON attendu :
{{"tiktok": {{"caption": "...", "hashtags": ["#..."]}},
  "instagram": {{"caption": "...", "hashtags": ["#..."]}},
  "youtube": {{"title": "...", "description": "...", "tags": ["..."]}},
  "pinned_comment": "commentaire à épingler qui pousse à commenter",
  "cover_text": "texte de miniature, 2-5 mots percutants",
  "best_times": ["jour + heure conseillée", "..."],
  "series_ideas": ["idée de partie 2", "idée de partie 3"]}}
Titre YouTube : 70 caractères maximum, terminé par #shorts. Pas de lien inventé dans les descriptions.
Hashtags : 4-8 par plateforme, mélange niche précise + moyen volume."""
    meta = llm.json(system, user, temperature=0.7)
    yt = meta.get("youtube") or {}
    if yt.get("title") and "#shorts" not in yt["title"].lower():
        yt["title"] = yt["title"][:61].rstrip() + " #shorts"
    return meta
