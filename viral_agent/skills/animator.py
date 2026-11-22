"""Skill : animateur 3D. Transforme un épisode (scènes + plans "anim") en vidéo animée à 24 i/s.

Chaque scène de la bible porte un plan "anim" (décor, caméra, acteurs, accessoires) :
le moteur three.js (viral_agent/anim) le rend image par image dans Chromium headless.
La bouche des personnages suit l'enveloppe de leur voix (lip-sync).

Voix : Chatterbox (plus naturel) avec vérification à l'oreille (Whisper) et repli Edge TTS.
"""
import difflib
import json
import re
import shutil
import subprocess
import time
from pathlib import Path

import numpy as np

from . import captions, editor, overlays, sound_bank, voice, voice_lab
from .series import _sound_design, _post

ANIM_DIR = Path(__file__).resolve().parent.parent / "anim"
FPS = 24


# ------------------------------------------------------------------ voix
def _norm_words(s):
    s = s.lower().replace("’", "'")
    s = re.sub(r"[^\w' ]+", " ", s)
    return s.split()


def similarity(a, b):
    return difflib.SequenceMatcher(None, _norm_words(a), _norm_words(b)).ratio()


def _transcribe(path, lang):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None
    if "m" not in voice_lab._WHISPER:
        voice_lab._WHISPER["m"] = WhisperModel("base", device="cpu", compute_type="int8")
    pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    segs, _ = voice_lab._WHISPER["m"].transcribe(np.frombuffer(pcm, np.float32), language=lang)
    return " ".join(s.text for s in segs).strip()


def _speaker_profiles(series, speaker, refs_dir, ca_bundle):
    """Profil Chatterbox (référence générée depuis la voix Edge du personnage) + profil Edge de repli."""
    lang = series.get("lang", "fr")
    v = series["voices"].get(speaker) or series["voices"]["narrateur"]
    edge = {"name": speaker, "engine": "edge", "lang": lang, "effects": v.get("effects", []),
            "edge": {"voice": v.get("voice"), "rate": v.get("rate", "+0%"), "pitch": v.get("pitch", "+0Hz")}}
    if v.get("profile"):
        return voice_lab.load_profile(v["profile"]), edge, v.get("color", "#FFFFFF")
    if series.get("voice_engine") != "chatterbox":
        return None, edge, v.get("color", "#FFFFFF")
    ref = refs_dir / f"ref_{v.get('voice')}_{v.get('pitch', '0')}.wav"
    if not ref.exists():
        txt = v.get("ref_text") or ("Franchement, je n'aurais jamais cru vivre un truc pareil. Écoute bien, parce que "
                                    "ce que je vais te raconter, personne ne le croit au début. Et pourtant, tout est vrai.")
        raw = ref.with_suffix(".mp3")
        voice.synthesize(txt, raw, v.get("voice"), rate="+0%", pitch=v.get("pitch", "+0Hz"), ca_bundle=ca_bundle)
        voice_lab.prepare_sample(raw, ref)
    cb = {"name": speaker, "engine": "chatterbox", "lang": lang, "effects": v.get("effects", []),
          "clone": {"reference": str(ref), "exaggeration": v.get("exaggeration", 0.55), "cfg_weight": v.get("cfg", 0.45)}}
    return cb, edge, v.get("color", "#FFFFFF")


def speak(series, speaker, text, out, refs_dir, ca_bundle, log, cache):
    """Synthèse + contrôle : Whisper doit retrouver le texte, sinon on régénère (3 essais) puis repli Edge."""
    lang = series.get("lang", "fr")
    say = text
    for k, v in (series.get("say") or {}).items():
        say = re.sub(rf"\b{re.escape(k)}\b", v, say)
    if speaker not in cache:
        cache[speaker] = _speaker_profiles(series, speaker, refs_dir, ca_bundle)
    cb, edge, color = cache[speaker]
    best = None
    if cb:
        for attempt in range(3):
            tmp = Path(out).with_name(Path(out).stem + f"_try{attempt}.wav")
            try:
                dur, words = voice_lab.synthesize(cb, say, tmp, ca_bundle=ca_bundle)
            except Exception as e:
                log(f"      ⚠️ chatterbox : {str(e)[:80]}")
                break
            heard = _transcribe(tmp, lang)
            score = similarity(text, heard) if heard is not None else 1.0
            if not best or score > best[0]:
                best = (score, tmp, dur, words, heard)
            if score >= 0.82:
                break
        if best and best[0] < 0.6:
            log(f"      👂 « {best[4]} » ≠ texte ({best[0]:.2f}) → voix Edge")
            best = None
    if not best:
        dur, words = voice_lab.synthesize(edge, say, out, ca_bundle=ca_bundle)
        best = (1.0, Path(out), dur, words, None)
    elif Path(best[1]) != Path(out):
        shutil.copy(best[1], out)
    # sous-titres : orthographe du script, timings de la voix
    script_words = text.split()
    words = best[3]
    if len(words) == len(script_words):
        words = [{"word": s, "start": w["start"], "end": w["end"]} for s, w in zip(script_words, words)]
    return best[2], words, color, best[0]


def mouth_envelope(wav, fps=FPS):
    """Ouverture de bouche (0..1) par image, d'après le volume de la voix."""
    pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(wav), "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(pcm, np.float32)
    hop = 16000 // fps
    n = max(1, len(x) // hop)
    rms = np.array([np.sqrt(np.mean(x[i * hop:(i + 1) * hop] ** 2) + 1e-9) for i in range(n)])
    ref = np.percentile(rms, 95) + 1e-6
    env = np.clip((rms / ref - 0.08) * 1.3, 0, 1)
    env = np.convolve(env, [0.25, 0.5, 0.25], mode="same")
    return [round(float(v), 3) for v in env]


# ------------------------------------------------------------------ rendu
def render_episode(cfg, bible, n, out_dir="output", log=print):
    series = bible["series"]
    ep = next(e for e in bible["episodes"] if int(e["n"]) == int(n))
    total_eps = len(bible["episodes"])
    scenes = ep["scenes"]
    if not all(s.get("anim") for s in scenes):
        raise ValueError(f"L'épisode {n} n'a pas de plans animés (champ 'anim' sur chaque scène).")
    t0 = time.time()
    work = Path(out_dir) / f"{series.get('slug', 'serie')}-partie-{int(n):02d}"
    parts = work / "parts"
    parts.mkdir(parents=True, exist_ok=True)
    refs = Path(out_dir) / "voice_refs"
    refs.mkdir(parents=True, exist_ok=True)
    log(f"🎬 Partie {n}/{total_eps} — « {ep['title']} » en animation 3D 24 i/s → {work}")

    # 1. voix (vérifiées) + lip-sync
    cache, words_all, durations, scene_audio, shots, offset = {}, [], [], [], [], 0.0
    for i, sc in enumerate(scenes):
        pieces, t_scene, mouths = [], 0.0, {}
        actor_ids = {a["id"] for a in sc["anim"].get("actors", [])}
        for j, line in enumerate(sc["lines"]):
            spk = line.get("s", "narrateur")
            wav = parts / f"v_{i:02d}_{j:02d}.wav"
            dur, ws, color, score = speak(series, spk, line["t"], wav, refs, cfg.ca_bundle, log, cache)
            log(f"   🎙️  {i+1}.{j+1} {spk} ({dur:.1f}s, compréhension {score:.0%})")
            for w in ws:
                words_all.append({"word": w["word"], "start": w["start"] + offset + t_scene,
                                  "end": w["end"] + offset + t_scene, "color": color})
            if spk in actor_ids:
                start_f = int(round(t_scene * FPS))
                env = mouth_envelope(wav)
                cur = mouths.setdefault(spk, [])
                cur.extend([0.0] * (start_f - len(cur)))
                cur.extend(env)
            gap = 0.12
            pp = parts / f"vp_{i:02d}_{j:02d}.wav"
            editor.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-af", "apad", "-t", f"{dur + gap:.3f}",
                        "-ar", "44100", "-ac", "2", str(pp)])
            pieces.append(pp)
            t_scene += dur + gap
        t_scene += 0.1
        durations.append(t_scene)
        sa = editor.concat_audio(pieces, parts / f"scene_{i:02d}.wav")
        sp = parts / f"scenep_{i:02d}.wav"
        editor.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(sa), "-af", "apad", "-t", f"{t_scene:.3f}",
                    "-ar", "44100", "-ac", "2", str(sp)])
        scene_audio.append(sp)
        shot = json.loads(json.dumps(sc["anim"]))
        shot["duration"] = round(t_scene, 3)
        shot["mouths"] = mouths
        for a in shot.get("actors", []):
            a.setdefault("look", series.get("looks", {}).get(a["id"], {}))
        shots.append(shot)
        offset += t_scene
    total = offset
    voice_wav = editor.concat_audio(scene_audio, parts / "voice.wav")
    log(f"   🗣️  voix : {total:.1f}s")
    if series.get("sound", True):
        voice_wav = _sound_design(cfg, series, scenes, durations, voice_wav, total, parts, log)

    # 2. animation 3D image par image
    shots_file = parts / "shots.json"
    shots_file.write_text(json.dumps(shots))
    node = shutil.which("node") or "node"
    env_path = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    log(f"   🎞️  rendu 3D de {int(total * FPS)} images…")
    p = subprocess.run([node, str(ANIM_DIR / "render.js"), str(shots_file), str(parts)], capture_output=True, text=True,
                       env={**__import__("os").environ, "NODE_PATH": env_path})
    if p.returncode != 0:
        raise RuntimeError("Rendu 3D impossible :\n" + p.stderr[-1500:])
    for line in p.stdout.strip().splitlines():
        log("      " + line)

    # 3. habillage : pastille de série + bandeaux
    tag = overlays.make_series_tag(parts / "tag.png", f"{series.get('tag', series['title']).upper()} · PARTIE {n}/{total_eps}")
    clips = []
    for i, sc in enumerate(scenes):
        ovs = [(tag, 30, 40, "static")]
        b = sc.get("banner")
        if not b and i == len(scenes) - 1 and int(n) < total_eps:
            b = {"label": "à suivre", "title": f"Partie {int(n) + 1}", "subtitle": ep.get("teaser", ""), "color": "black"}
        if b:
            png, _ = overlays.make_banner(parts / f"banner_{i:02d}.png", b.get("title", ""), b.get("label", ""),
                                          b.get("subtitle", ""), b.get("color", "red"), 1080)
            ovs.append((png, 0, 130, "slide"))
        clips.append(overlay_video(parts / f"anim_{i:02d}.mp4", parts / f"clip_{i:02d}.mp4", ovs, durations[i]))

    # 4. sous-titres + mixage final + contrôle à l'oreille
    ass = captions.build_pov_ass(words_all, parts / "subs.ass", 1080, 1920)
    final = editor.assemble(clips, voice_wav, ass, work / "video.mp4", total, music=series.get("music"),
                            progress_bar=False, w=1080, h=1920)
    rep = sound_bank.listen(final, parts / "ears.png")
    (parts / "ears.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
    log(f"   👂 {rep['lufs']} LUFS, crête {rep['true_peak']} dBTP" + (f" ⚠️ {', '.join(rep['issues'])}" if rep["issues"] else " ✔"))
    still = parts / "cover_src.jpg"
    editor.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "1.0", "-i", str(parts / "anim_00.mp4"), "-frames:v", "1", str(still)])
    editor.make_cover(still, f"Partie {n} : {ep.get('cover', ep['title'])}", work / "cover.jpg")
    (work / "POST.md").write_text(_post(series, ep, n, total_eps, total), encoding="utf-8")
    log(f"   ✅ {final} ({total:.1f}s, 24 i/s) en {time.time() - t0:.0f}s")
    return {"episode": n, "video": str(final), "duration": total}


def overlay_video(src, out, overlays_, duration):
    inputs = ["-i", str(src)]
    graph, last = "", "0:v"
    for k, (png, x, y, mode) in enumerate(overlays_):
        inputs += ["-loop", "1", "-i", str(png)]
        ys = f"if(lt(t,0.25),-h+(t/0.25)*({y}+h),{y})" if mode == "slide" else str(y)
        graph += f"[{last}][{k+1}:v]overlay=x={x}:y='{ys}':shortest=1[o{k}];"
        last = f"o{k}"
    graph += f"[{last}]format=yuv420p[out]"
    editor.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", graph, "-map", "[out]",
                "-t", f"{duration:.3f}", "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", str(out)])
    return out
