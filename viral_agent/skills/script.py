"""Skill : scénariste. Écrit le script découpé en scènes + direction visuelle."""
import json
from .playbook import VIRAL_PLAYBOOK, LANG_NAMES


SYSTEM = ("Tu es le meilleur scénariste de vidéos courtes au monde. Tes scripts ont un taux de rétention "
          "exceptionnel. " + VIRAL_PLAYBOOK)


def _schema(lang):
    return f"""JSON attendu :
{{
  "title": "titre accrocheur (≤ 60 caractères)",
  "format": "format viral utilisé",
  "scenes": [
    {{"text": "phrase(s) dites en voix off dans cette scène, en {LANG_NAMES.get(lang, lang)}",
      "visual": "description visuelle EN ANGLAIS de l'image (sujet, action, décor, cadrage, ambiance), sans texte dans l'image",
      "emphasis": "LE mot le plus fort de la scène (sera mis en valeur)"}}
  ],
  "cta": "appel à l'action final court"
}}
La 1re scène = le hook seul. 6 à 10 scènes. La dernière scène contient le CTA et boucle vers le début."""


def write_script(llm, topic, lang="fr", duration=35, tone="captivant", hook=None, fmt=None):
    words = int(duration * 2.6)
    user = f"""Sujet : {topic}
Durée cible : {duration} secondes (≈ {words} mots au total)
Ton : {tone}
{f'Hook imposé : {hook}' if hook else ''}
{f'Format : {fmt}' if fmt else ''}

{_schema(lang)}"""
    return llm.json(SYSTEM, user, temperature=0.95)


def rewrite_script(llm, script, critique, lang="fr", duration=35):
    user = f"""Voici un script et la critique d'un expert en viralité. Réécris-le pour corriger TOUS les points faibles,
en gardant le sujet. Le hook doit devenir irrésistible.

SCRIPT :
{json.dumps(script, ensure_ascii=False, indent=1)}

CRITIQUE :
{json.dumps(critique, ensure_ascii=False, indent=1)}

Durée cible : {duration} s.
{_schema(lang)}"""
    return llm.json(SYSTEM, user, temperature=0.9)


def full_text(script):
    return " ".join(s["text"].strip() for s in script.get("scenes", []))
