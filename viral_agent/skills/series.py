"""Skill : showrunner. Produit une série d'épisodes (ex. 30 TikToks d'1 min) à partir d'une « bible » JSON.

Bible :
{
  "series": {"title", "lang", "style", "tag": "WAR DOGS", "hashtags": [...],
             "voices":     {"narrateur": {"voice": "fr-FR-...", "rate": "+10%", "pitch": "+0Hz",
                                          "effects": [], "color": "#FFFFFF", "profile": "nom-optionnel"}},
             "characters": {"efraim": "description visuelle EN ANGLAIS, identique dans chaque image"}},
  "episodes": [{"n": 1, "title": "...", "teaser": "...",
                "scenes": [{"visual": "...", "chars": ["efraim"], "move": "walk",
                            "banner": {"label": "...", "title": "...", "subtitle": "...", "color": "red"},
                            "lines": [{"s": "narrateur", "t": "texte dit"}]}]}]
}
"""
import json
import random
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

from . import captions, editor, overlays, visuals, voice_lab


def load_bible(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _speaker_profile(series, speaker, lang):
    v = series.get("voices", {}).get(speaker) or series.get("voices", {}).get("narrateur") or {}
    if v.get("profile"):
        pf = voice_lab.load_profile(v["profile"])
    else:
        pf = {"name": speaker, "engine": "edge", "lang": lang, "effects": v.get("effects", []),
              "edge": {"voice": v.get("voice", "fr-FR-RemyMultilingualNeural"), "rate": v.get("rate", "+10%"),
                       "pitch": v.get("pitch", "+0Hz")}}
    return pf, v.get("color", "#FFFFFF")


def _image_prompt(series, scene, style):
    chars = series.get("characters", {})
    who = [chars[c] for c in scene.get("chars", []) if c in chars]
    extra = (", featuring " + "; ".join(who)) if who else ""
    pov = series.get("pov_hint", "")
    return visuals.build_prompt(scene["visual"] + extra + (f", {pov}" if pov else ""), style)


def render_episode(cfg, bible, n, out_dir="output", log=print, seed=None):
    series = bible["series"]
    ep = next(e for e in bible["episodes"] if int(e["n"]) == int(n))
    total_eps = len(bible["episodes"])
    lang = series.get("lang", "fr")
    style = series.get("style", "pov_cartoon")
    scenes = ep["scenes"]
    t0 = time.time()
    work = Path(out_dir) / f"{series.get('slug', 'serie')}-partie-{int(n):02d}"
    parts = work / "parts"
    parts.mkdir(parents=True, exist_ok=True)
    log(f"🎬 Partie {n}/{total_eps} — « {ep['title']} » ({len(scenes)} scènes) → {work}")

    # 1. images (en parallèle avec la voix)
    seed = seed if seed is not None else int(series.get("seed", random.randint(1, 9_000_000))) + int(n) * 100
    session = requests.Session()

    def gen(i):
        out = parts / f"img_{i:02d}.jpg"
        if out.exists() and out.stat().st_size > 10_000:
            return out  # reprise après interruption
        return visuals.generate_image(cfg, _image_prompt(series, scenes[i], style), out, seed + i, session=session)

    pool = ThreadPoolExecutor(max_workers=2 if cfg.image_token else 1)
    futures = [pool.submit(gen, i) for i in range(len(scenes))]

    # 2. voix multi-personnages, ligne par ligne
    words, durations, scene_audio, offset = [], [], [], 0.0
    cache = {}
    for i, sc in enumerate(scenes):
        pieces, t_scene = [], 0.0
        for j, line in enumerate(sc["lines"]):
            spk = line.get("s", "narrateur")
            if spk not in cache:
                cache[spk] = _speaker_profile(series, spk, lang)
            pf, color = cache[spk]
            ap = parts / f"v_{i:02d}_{j:02d}.wav"
            dur, ws = voice_lab.synthesize(pf, line["t"], ap, ca_bundle=cfg.ca_bundle)
            for w in ws:
                words.append({"word": w["word"], "start": w["start"] + offset + t_scene,
                              "end": w["end"] + offset + t_scene, "color": color})
            gap = 0.10
            pp = parts / f"vp_{i:02d}_{j:02d}.wav"
            editor.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(ap), "-af", "apad",
                        "-t", f"{dur + gap:.3f}", "-ar", "44100", "-ac", "2", str(pp)])
            pieces.append(pp)
            t_scene += dur + gap
        t_scene += 0.08
        durations.append(t_scene)
        sa = editor.concat_audio(pieces, parts / f"scene_{i:02d}.wav")
        # pad final de la scène
        sp = parts / f"scenep_{i:02d}.wav"
        editor.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(sa), "-af", "apad", "-t", f"{t_scene:.3f}",
                    "-ar", "44100", "-ac", "2", str(sp)])
        scene_audio.append(sp)
        offset += t_scene
    total = offset
    voice_wav = editor.concat_audio(scene_audio, parts / "voice.wav")
    log(f"   🎙️  voix : {total:.1f}s, {len(cache)} personnage(s)")

    images = [f.result() for f in futures]
    pool.shutdown()
    log("   🎨 images prêtes")

    # 3. habillage + montage
    tag_png = overlays.make_series_tag(parts / "tag.png", f"{series.get('tag', series['title']).upper()} · PARTIE {n}/{total_eps}")
    clips = []
    for i, (img, d) in enumerate(zip(images, durations)):
        ovs = [(tag_png, 30, 40, "static")]
        b = scenes[i].get("banner")
        if not b and i == len(scenes) - 1 and int(n) < total_eps:
            b = {"label": "à suivre", "title": f"Partie {int(n) + 1}", "subtitle": ep.get("teaser", "Abonne-toi pour la suite"),
                 "color": "black"}
        if b:
            png, _ = overlays.make_banner(parts / f"banner_{i:02d}.png", b.get("title", ""), b.get("label", ""),
                                          b.get("subtitle", ""), b.get("color", "red"), cfg.width,
                                          icon=b.get("icon", True))
            ovs.append((png, 0, 130, "slide"))
        move = scenes[i].get("move") or editor.pick_moves(1, seed + i)[0]
        clips.append(editor.render_scene(img, d, parts / f"clip_{i:02d}.mp4", move, cfg.width, cfg.height,
                                         cfg.fps, flash=bool(scenes[i].get("flash", i > 0 and move in ("shake", "push"))),
                                         overlays=ovs))
    ass = captions.build_pov_ass(words, parts / "subs.ass", cfg.width, cfg.height)
    final = editor.assemble(clips, voice_wav, ass, work / "video.mp4", total, music=series.get("music"),
                            progress_bar=False, w=cfg.width, h=cfg.height)
    editor.make_cover(images[0], f"Partie {n} : {ep.get('cover', ep['title'])}", work / "cover.jpg", cfg.width, cfg.height)
    (work / "POST.md").write_text(_post(series, ep, n, total_eps, total), encoding="utf-8")
    log(f"   ✅ {final} ({total:.1f}s) en {time.time() - t0:.0f}s")
    return {"episode": n, "video": str(final), "duration": total}


def _post(series, ep, n, total_eps, dur):
    tags = " ".join(series.get("hashtags", [])) + f" #partie{n}"
    lines = [f"# {series['title']} · Partie {n}/{total_eps} : {ep['title']}", "", f"Durée : {dur:.0f}s", "",
             "## Légende (TikTok / Reels / Shorts)", "",
             f"{series['title']} — Partie {n} : {ep['title']} 😳 {ep.get('teaser', '')}".strip(), "",
             series.get("disclaimer", ""), "", tags, "",
             "## Commentaire à épingler", "", ep.get("pinned", "Tu aurais fait quoi à sa place ? 👇"), "",
             "## Script", ""]
    for i, sc in enumerate(ep["scenes"], 1):
        for line in sc["lines"]:
            lines.append(f"{i}. **{line.get('s', 'narrateur')}** : {line['t']}")
    return "\n".join(lines) + "\n"


def parse_range(spec, total):
    if not spec or spec == "all":
        return list(range(1, total + 1))
    out = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out
