"""Skill : critique viralité. Note le script comme un algorithme + un public exigeant."""
import json
from .playbook import VIRAL_PLAYBOOK


def critique(llm, script):
    system = ("Tu es un analyste impitoyable des algorithmes TikTok/Reels/Shorts. Tu notes sévèrement : "
              "un 8/10 doit être vraiment excellent. " + VIRAL_PLAYBOOK)
    user = f"""Analyse ce script de vidéo courte.

{json.dumps(script, ensure_ascii=False, indent=1)}

JSON attendu :
{{"scores": {{"hook": 1-10, "retention": 1-10, "emotion": 1-10, "clarity": 1-10, "shareability": 1-10, "loop": 1-10, "accuracy": 1-10}},
  "overall": 1-10,
  "dubious_claims": ["affirmation douteuse ou inventée", "..."],
  "weaknesses": ["problème précis 1", "..."],
  "fixes": ["correction concrète 1", "..."],
  "better_hooks": ["hook alternatif 1", "hook alternatif 2", "hook alternatif 3"]}}"""
    data = llm.json(system, user, temperature=0.3)
    try:
        data["overall"] = float(data.get("overall", 0))
    except (TypeError, ValueError):
        sc = data.get("scores", {})
        data["overall"] = sum(map(float, sc.values())) / max(len(sc), 1)
    try:  # une info douteuse = pas publiable, on force la réécriture
        if float(data.get("scores", {}).get("accuracy", 10)) < 6:
            data["overall"] = min(data["overall"], 5.0)
    except (TypeError, ValueError):
        pass
    return data
