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
from .skills import voice_lab


def main(argv=None):
    p = argparse.ArgumentParser(prog="viral_agent", description="Agent IA de vidéos courtes virales")
    sub = p.add_subparsers(dest="cmd", required=True)

    def video_opts(sp):
        sp.add_argument("--lang", default="fr", choices=list(VOICES))
        sp.add_argument("--duration", type=int, default=35, help="durée cible en secondes")
        sp.add_argument("--style", default="cinematic", help="|".join(VISUAL_STYLES) + " ou style libre")
        sp.add_argument("--voice", default="male", choices=["male", "female", "young"])
        sp.add_argument("--voice-name", help="voix Edge TTS précise (ex. fr-FR-VivienneMultilingualNeural)")
        sp.add_argument("--voice-profile", help="voix créée avec la commande `voice` (design / create / clone)")
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

    v = sub.add_parser("voice", help="labo de voix : créer, cloner, écouter des voix")
    vs = v.add_subparsers(dest="vcmd", required=True)
    vs.add_parser("list", help="voix créées")
    vs.add_parser("effects", help="effets audio disponibles")
    vd = vs.add_parser("design", help="créer une voix à partir d'une description")
    vd.add_argument("name"); vd.add_argument("description"); vd.add_argument("--lang", default="fr")
    vc = vs.add_parser("create", help="créer une voix avec des réglages manuels")
    vc.add_argument("name"); vc.add_argument("--lang", default="fr")
    vc.add_argument("--base", help="voix Edge de base (ex. fr-FR-HenriNeural)")
    vc.add_argument("--gender", default="male", choices=["male", "female", "young"])
    vc.add_argument("--rate", default="+8%"); vc.add_argument("--pitch", default="+0Hz")
    vc.add_argument("--volume", default="+0%"); vc.add_argument("--effects", default="", help="ex. deep,broadcast")
    vk = vs.add_parser("clone", help="cloner une voix depuis un enregistrement (10-20 s de parole)")
    vk.add_argument("name"); vk.add_argument("--sample", required=True); vk.add_argument("--lang", default="fr")
    vk.add_argument("--engine", default="chatterbox", choices=["chatterbox", "elevenlabs"])
    vk.add_argument("--effects", default="")
    vk.add_argument("--exaggeration", type=float, default=0.5, help="expressivité 0.25-1.0 (chatterbox)")
    vk.add_argument("--consent", action="store_true", help=voice_lab.CONSENT_TEXT)
    vp = vs.add_parser("preview", help="écouter une voix")
    vp.add_argument("name"); vp.add_argument("text", nargs="?")
    vp.add_argument("--out")
    vx = vs.add_parser("delete", help="supprimer une voix"); vx.add_argument("name")
    vb = vs.add_parser("catalog", help="voix de base Edge d'une langue"); vb.add_argument("--lang", default="fr")

    args = p.parse_args(argv)
    if args.cmd == "voice":
        return voice_cmd(args)
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
              caption_pos=args.captions, voice_profile=args.voice_profile)
    if args.cmd == "make":
        r = agent.make_video(args.topic, hook=args.hook, **kw)
        print(json.dumps(r, ensure_ascii=False, indent=2))
    elif args.cmd == "auto":
        rs = agent.autopilot(args.niche, args.count, **kw)
        print(json.dumps(rs, ensure_ascii=False, indent=2))


PREVIEW_TEXT = {"fr": "Tu ne vas pas croire ce que je vais te montrer. Reste jusqu'à la fin.",
                "en": "You won't believe what I'm about to show you. Stay until the end."}


def _effects(s):
    return [e.strip() for e in s.split(",") if e.strip()]


def _show(pf):
    print(f"✅ Voix « {pf['name']} » ({pf['engine']}, {pf.get('lang')})")
    if pf.get("edge"):
        e = pf["edge"]
        print(f"   base : {e['voice']}  débit {e.get('rate')}  hauteur {e.get('pitch')}  volume {e.get('volume', '+0%')}")
    if pf.get("effects"):
        print(f"   effets : {', '.join(pf['effects'])}")
    if pf.get("why"):
        print(f"   pourquoi : {pf['why']}")


def voice_cmd(args):
    cfg = Config()
    c = args.vcmd
    if c == "list":
        pfs = voice_lab.list_profiles()
        if not pfs:
            print("Aucune voix. Crée-en une : python -m viral_agent voice design ma-voix \"narrateur grave\"")
        for pf in pfs:
            print(f"- {pf['name']:<18} [{pf['engine']}] {pf.get('description', '')}")
    elif c == "effects":
        for k, (desc, _) in voice_lab.EFFECTS.items():
            print(f"- {k:<10} {desc}")
    elif c == "catalog":
        for vv in voice_lab.available_edge_voices(args.lang, cfg.ca_bundle):
            tags = ", ".join(vv.get("VoiceTag", {}).get("VoicePersonalities", []) or [])
            print(f"- {vv['ShortName']:<36} {vv.get('Gender', ''):<7} {tags}")
    elif c == "design":
        from .llm import LLM
        print("🎛️  Conception de la voix…")
        _show(voice_lab.design_profile(LLM(cfg), args.name, args.description, args.lang, cfg.ca_bundle))
        print(f"   écoute : python -m viral_agent voice preview {args.name}")
    elif c == "create":
        _show(voice_lab.create_profile(args.name, args.lang, args.base, args.gender, args.rate, args.pitch,
                                       args.volume, _effects(args.effects)))
    elif c == "clone":
        try:
            print("🧬 Préparation de l'échantillon et du modèle de clonage…")
            pf = voice_lab.clone_profile(args.name, args.sample, args.lang, args.engine, args.consent,
                                         _effects(args.effects), args.exaggeration)
        except PermissionError as e:
            print(f"⛔ {e}")
            return 2
        _show(pf)
        print(f"   référence : {pf['clone']['reference_seconds']}s de parole")
    elif c == "preview":
        pf = voice_lab.load_profile(args.name)
        text = args.text or PREVIEW_TEXT.get(pf.get("lang"), PREVIEW_TEXT["en"])
        out = args.out or str(voice_lab.voices_dir() / f"{pf['name']}-preview.mp3")
        dur, _ = voice_lab.synthesize(pf, text, out, cfg.ca_bundle)
        print(f"🔊 {out} ({dur:.1f}s)")
    elif c == "delete":
        voice_lab.delete_profile(args.name)
        print(f"🗑️  Voix « {args.name} » supprimée")


if __name__ == "__main__":
    sys.exit(main())
