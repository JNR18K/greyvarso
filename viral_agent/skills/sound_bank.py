"""Skill : banque de sons + oreilles.

Sources :
  - earshot  : génère un bruitage à partir d'une description (CPU, MIT, sons libres sans crédit)
               https://github.com/Leonxlnx/earshot  ->  pip install "earshot @ git+https://github.com/Leonxlnx/earshot"
  - Openverse: vrais enregistrements (Freesound…) sous licence CC0, crédits sauvegardés automatiquement
               https://api.openverse.org  (sans compte : ~20 requêtes/min, 200/jour)
Oreilles :
  - listen() : volume intégré (LUFS), crête, dynamique, silences, et une image spectrogramme + forme d'onde
               pour « voir » le son et corriger un mixage (voix noyée, saturation, trous).
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import requests

OPENVERSE = "https://api.openverse.org/v1/audio/"


def cache_dir():
    d = Path(os.getenv("SOUNDS_DIR", "sounds"))
    (d / "openverse").mkdir(parents=True, exist_ok=True)
    (d / "earshot").mkdir(parents=True, exist_ok=True)
    return d


def _key(text):
    return re.sub(r"[^\w]+", "-", text.lower()).strip("-")[:40] + "-" + hashlib.md5(text.encode()).hexdigest()[:6]


def _duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True).stdout.strip()
    try:
        return float(out)
    except ValueError:
        return 0.0


# ------------------------------------------------------------------ earshot
def earshot_available():
    return shutil.which("earshot") is not None


def earshot_make(description, dur=None, seed=1, loop=False):
    """Bruitage généré par earshot. Retourne le chemin du WAV (mis en cache) ou None."""
    if not earshot_available():
        return None
    out = cache_dir() / "earshot" / f"{_key(description + str(dur) + str(seed))}.wav"
    if out.exists():
        return out
    cmd = ["earshot", "make", description, "-o", str(out), "--seed", str(seed)]
    if dur:
        cmd += ["--dur", str(dur)]
    if not loop:
        cmd += ["--no-loop"]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if p.returncode != 0 or not out.exists():
        return None
    meta = out.with_suffix(".json")
    meta.write_text(json.dumps({"description": description, "earshot": p.stdout.strip()[-300:]}, ensure_ascii=False))
    return out


# ------------------------------------------------------------------ Openverse
def openverse_search(query, max_duration=None, page_size=10, cc0_only=True, ca_bundle=None):
    params = {"q": query, "page_size": page_size, "mature": "false"}
    params["license"] = "cc0" if cc0_only else "cc0,pdm,by"
    s = requests.Session()
    if ca_bundle:
        s.verify = ca_bundle
    r = s.get(OPENVERSE, params=params, timeout=30)
    r.raise_for_status()
    res = r.json().get("results", [])
    if max_duration:
        res = [x for x in res if x.get("duration") and x["duration"] / 1000 <= max_duration]
    return res


def openverse_get(query, max_duration=None, ca_bundle=None, pick=0):
    """Télécharge le n-ième résultat CC0 pour la requête. Retourne le chemin (mis en cache) ou None."""
    idx = cache_dir() / "openverse" / "index.json"
    index = json.loads(idx.read_text()) if idx.exists() else {}
    k = f"{query}|{max_duration}|{pick}"
    if k in index and Path(index[k]).exists():
        return Path(index[k])
    try:
        res = openverse_search(query, max_duration, ca_bundle=ca_bundle)
    except Exception:
        return None
    if len(res) <= pick:
        return None
    item = res[pick]
    ext = (item.get("filetype") or "mp3").split("/")[-1]
    out = cache_dir() / "openverse" / f"{item['id']}.{ext}"
    if not out.exists():
        try:
            s = requests.Session()
            if ca_bundle:
                s.verify = ca_bundle
            data = s.get(item["url"], timeout=60)
            data.raise_for_status()
            out.write_bytes(data.content)
        except Exception:
            return None
    credits = cache_dir() / "CREDITS.md"
    line = f"- {item.get('title')} — {item.get('creator')} ({item.get('license', '').upper()}) {item.get('foreign_landing_url')}\n"
    if not credits.exists() or line not in credits.read_text():
        with open(credits, "a") as f:
            f.write(line)
    index[k] = str(out)
    idx.write_text(json.dumps(index, ensure_ascii=False, indent=1))
    return out


def get_sound(description, query=None, dur=None, loop=False, prefer="earshot", ca_bundle=None, seed=1):
    """Trouve un son : earshot (généré) ou Openverse (enregistré), selon la préférence, avec repli sur l'autre."""
    order = ["earshot", "openverse"] if prefer == "earshot" else ["openverse", "earshot"]
    for src in order:
        if src == "earshot":
            p = earshot_make(description, dur, seed, loop)
        else:
            p = openverse_get(query or description, max_duration=None if loop else 12, ca_bundle=ca_bundle)
        if p:
            return p
    return None


# ------------------------------------------------------------------ oreilles
def listen(path, picture=None):
    """Analyse un son. Retourne un dict de mesures ; écrit une image spectrogramme + forme d'onde si demandé."""
    path = str(path)
    p = subprocess.run(["ffmpeg", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    txt = p.stderr[p.stderr.rfind("Summary:"):]

    def grab(label):
        m = re.search(label + r":\s+(-?[\d.]+|-inf)", txt)
        return float(m.group(1)) if m and m.group(1) != "-inf" else None
    report = {"duration": round(_duration(path), 2), "lufs": grab("I"), "lra": grab("LRA"), "true_peak": grab("Peak")}
    s = subprocess.run(["ffmpeg", "-nostats", "-i", path, "-af", "silencedetect=n=-40dB:d=0.6", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", s)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", s)]
    report["silences"] = [(round(a, 2), round(b, 2)) for a, b in zip(starts, ends)]
    issues = []
    if report["true_peak"] is not None and report["true_peak"] > -0.5:
        issues.append("saturation probable (crête > -0,5 dBTP)")
    if report["duration"] < 3:  # LUFS intégré non fiable sur un son court
        report["lufs"] = None
    if report["lufs"] is not None and report["lufs"] < -20:
        issues.append("trop faible pour TikTok (viser -14 LUFS)")
    if report["lufs"] is not None and report["lufs"] > -10:
        issues.append("trop fort, risque de distorsion")
    if any(b - a > 1.5 for a, b in report["silences"]):
        issues.append("trou de silence > 1,5 s (perte d'attention)")
    report["issues"] = issues
    if picture:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-filter_complex",
                        "[0:a]aformat=channel_layouts=mono,showspectrumpic=s=1200x360:legend=0:color=intensity[s];"
                        "[0:a]aformat=channel_layouts=mono,showwavespic=s=1200x200:colors=0x44DDFF[w];"
                        "[w][s]vstack", "-frames:v", "1", str(picture)], capture_output=True)
        report["picture"] = str(picture)
    if earshot_available():
        m = subprocess.run(["earshot", "measure", path], capture_output=True, text=True)
        if m.returncode == 0:
            report["earshot"] = m.stdout.strip()[-600:]
    return report


# ------------------------------------------------------------------ mixage
def mix_track(voice, cues, beds, total, out_path):
    """voice : wav ; cues : [(t, fichier, gain_dB)] ; beds : [(t0, t1, fichier, gain_dB)] (ambiances en boucle).
    La voix reste devant : les ambiances et bruitages sont compressés par la voix (ducking)."""
    inputs = ["-i", str(voice)]
    parts, labels = [], []
    k = 1
    for t0, t1, f, g in beds:
        d = max(t1 - t0, 0.1)
        inputs += ["-stream_loop", "-1", "-i", str(f)]
        parts.append(f"[{k}:a]aformat=sample_rates=44100:channel_layouts=stereo,atrim=0:{d:.3f},asetpts=PTS-STARTPTS,"
                     f"afade=t=in:d=0.4,afade=t=out:st={max(d-0.4,0):.3f}:d=0.4,volume={g}dB,"
                     f"adelay={int(t0*1000)}|{int(t0*1000)}[x{k}]")
        labels.append(f"[x{k}]")
        k += 1
    for t, f, g in cues:
        inputs += ["-i", str(f)]
        parts.append(f"[{k}:a]aformat=sample_rates=44100:channel_layouts=stereo,volume={g}dB,"
                     f"adelay={int(max(t,0)*1000)}|{int(max(t,0)*1000)}[x{k}]")
        labels.append(f"[x{k}]")
        k += 1
    if not labels:
        shutil.copy(voice, out_path)
        return out_path
    graph = ";".join(parts)
    graph += f";{''.join(labels)}amix=inputs={len(labels)}:duration=longest:normalize=0[fx]"
    graph += ";[0:a]asplit=2[v1][v2];[fx][v2]sidechaincompress=threshold=0.05:ratio=3.5:attack=20:release=350[fxd]"
    graph += f";[v1][fxd]amix=inputs=2:duration=first:normalize=0,atrim=0:{total:.3f}[out]"
    p = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", graph, "-map", "[out]",
                        "-ar", "44100", "-ac", "2", str(out_path)], capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("Mixage impossible : " + p.stderr[-800:])
    return out_path


# ------------------------------------------------------------------ choix automatique
AMBIENCES = [  # (mots-clés dans la description visuelle, requête earshot, requête Openverse)
    (("beach", "ocean", "sea"), "ocean waves on a beach", "ocean waves beach ambience"),
    (("desert", "dune", "highway", "truck"), "truck engine rumble driving", "truck interior driving engine"),
    (("night", "balcony"), "night crickets ambience", "night crickets ambience"),
    (("office", "desk"), "quiet office room tone with keyboard typing", "office ambience typing"),
    (("warehouse", "bunker"), "large empty warehouse room tone", "warehouse room tone"),
    (("factory",), "factory machinery ambience", "factory ambience machines"),
    (("airplane", "airport"), "airplane cabin hum", "airplane cabin ambience"),
    (("courtroom", "courthouse", "hearing"), "murmuring crowd in a large hall", "courtroom murmur crowd"),
    (("convention", "crowd", "party", "nightclub"), "busy crowd chatter indoors", "crowd chatter indoor"),
    (("street", "city", "boulevard", "market", "tirana", "amman"), "city street traffic ambience", "city street traffic ambience"),
    (("rain",), "rain on a car roof", "rain on car roof"),
]
CUES = {  # événement -> (requête earshot, requête Openverse, gain dB)
    "banner": ("a fast whoosh", "whoosh swoosh fast", -12),
    "alert": ("a short alarm alert beep", "alert notification beep", -16),
    "impact": ("a deep cinematic impact boom", "cinematic boom impact", -10),
    "riser": ("a short tension riser", "riser tension short", -14),
    "cash": ("a cash register cha-ching", "cash register", -12),
    "phone": ("a phone vibrating buzz", "phone vibrate", -12),
    "knock": ("loud knocking on a door", "door knock loud", -8),
    "gunshot": ("distant gunshots", "distant gunshots", -16),
    "car": ("a car engine starting and driving away", "car pass by", -14),
    "camera": ("a camera shutter click", "camera shutter", -10),
}


def auto_scene_sounds(scene):
    """Devine l'ambiance et les bruitages d'une scène à partir de sa description, de son bandeau et de son mouvement."""
    v = (scene.get("visual") or "").lower()
    amb = scene.get("ambience")
    if amb is None:
        for keys, es, ov in AMBIENCES:
            if any(k in v for k in keys):
                amb = (es, ov)
                break
    elif isinstance(amb, str):
        amb = (amb, amb)
    cues = list(scene.get("sfx", []))
    if not scene.get("sfx"):
        if scene.get("banner"):
            cues.append("banner")
            if scene["banner"].get("color") == "red":
                cues.append("alert")
            if scene["banner"].get("color") == "green":
                cues.append("cash")
        if scene.get("move") in ("shake", "push") and "impact" not in cues:
            cues.append("impact" if scene.get("move") == "push" else "riser")
        for word, cue in (("phone", "phone"), ("knock", "knock"), ("gunfire", "gunshot"), ("camera", "camera"),
                          ("cash", "cash"), ("speeding away", "car")):
            if word in v and cue not in cues:
                cues.append(cue)
    return amb, cues
