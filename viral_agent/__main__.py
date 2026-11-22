"""CLI :
  python -m viral_agent make "sujet"            -> une vidéo complète
  python -m viral_agent ideas "niche"           -> idées virales
  python -m viral_agent auto "niche" -n 3       -> idées + 3 vidéos en pilote automatique
  python -m viral_agent script "sujet"          -> script seul (avec score viral)
"""
import argparse
import json
import sys

from .agent import ViralAgent
from .config import Config
from .skills.playbook import VISUAL_STYLES, VOICES


def main(argv=None):
    p = argparse.ArgumentParser(prog="viral_agent", description="Agent IA de vidéos courtes virales")
    sub = p.add_subparsers(dest="cmd", required=True)

    def video_opts(sp):
        sp.add_argument("--lang", default="fr", choices=list(VOICES))
        sp.add_argument("--duration", type=int, default=35, help="durée cible en secondes")
        sp.add_argument("--style", default="cinematic", help="|".join(VISUAL_STYLES) + " ou style libre")
        sp.add_argument("--voice", default="male", choices=["male", "female", "young"])
        sp.add_argument("--voice-name", help="voix Edge TTS précise (ex. fr-FR-VivienneMultilingualNeural)")
        sp.add_argument("--rate", default="+8%", help="vitesse de la voix (ex. +15%%)")
        sp.add_argument("--tone", default="captivant", help="ton : captivant, drôle, mystérieux, motivant…")
        sp.add_argument("--music", help="fichier audio de fond (libre de droits)")
        sp.add_argument("--captions", default="center", choices=["center", "low", "high"])
        sp.add_argument("--out", default="output")

    m = sub.add_parser("make", help="créer une vidéo à partir d'un sujet")
    m.add_argument("topic")
    m.add_argument("--hook")
    video_opts(m)

    a = sub.add_parser("auto", help="pilote automatique : idées + vidéos")
    a.add_argument("niche")
    a.add_argument("-n", "--count", type=int, default=3)
    video_opts(a)

    i = sub.add_parser("ideas", help="trouver des idées virales")
    i.add_argument("niche")
    i.add_argument("-n", "--count", type=int, default=8)
    i.add_argument("--lang", default="fr")

    s = sub.add_parser("script", help="écrire et noter un script")
    s.add_argument("topic")
    s.add_argument("--lang", default="fr")
    s.add_argument("--duration", type=int, default=35)
    s.add_argument("--tone", default="captivant")

    args = p.parse_args(argv)
    agent = ViralAgent(Config())

    if args.cmd == "ideas":
        for n, idea in enumerate(agent.ideas(args.niche, args.count, args.lang), 1):
            print(f"\n{n}. [{idea.get('potential')}/10] {idea.get('topic')}\n   format : {idea.get('format')}"
                  f"\n   hook   : {idea.get('hook')}\n   angle  : {idea.get('angle')}")
        return
    if args.cmd == "script":
        print(json.dumps(agent.script(args.topic, args.lang, args.duration, args.tone), ensure_ascii=False, indent=2))
        return

    kw = dict(out_dir=args.out, lang=args.lang, duration=args.duration, style=args.style, voice_style=args.voice,
              voice_name=args.voice_name, rate=args.rate, tone=args.tone, music=args.music,
              caption_pos=args.captions)
    if args.cmd == "make":
        r = agent.make_video(args.topic, hook=args.hook, **kw)
        print(json.dumps(r, ensure_ascii=False, indent=2))
    elif args.cmd == "auto":
        rs = agent.autopilot(args.niche, args.count, **kw)
        print(json.dumps(rs, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.exit(main())
