"""Skill : chasseur d'idées. Génère des concepts à fort potentiel viral pour une niche."""
from .playbook import VIRAL_PLAYBOOK, LANG_NAMES


def find_ideas(llm, niche, count=5, lang="fr"):
    system = ("Tu es un stratège de contenu viral qui a fait des centaines de vidéos à plusieurs millions de vues. "
              + VIRAL_PLAYBOOK)
    user = f"""Niche : {niche}
Langue de la vidéo : {LANG_NAMES.get(lang, lang)}

Propose {count} idées de vidéos courtes très différentes les unes des autres, chacune avec un format viral différent.
Privilégie les sujets à forte curiosité, partageables, et que le public de cette niche cherche déjà.

JSON attendu :
{{"ideas": [{{"topic": "sujet précis en une phrase", "format": "format viral utilisé",
  "hook": "première phrase exacte de la vidéo", "angle": "pourquoi ça va retenir et faire partager",
  "potential": 1-10}}]}}"""
    data = llm.json(system, user)
    ideas = data.get("ideas", data if isinstance(data, list) else [])
    return sorted(ideas, key=lambda i: -float(i.get("potential", 0) or 0))
