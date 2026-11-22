"""Skill : labo de voix. Crée des voix personnalisées pour les vidéos.

Trois façons de créer une voix (sauvegardée comme profil réutilisable dans voices/<nom>.json) :
  1. design  : tu décris la voix ("narrateur grave et mystérieux"), l'IA choisit la voix de base,
               le débit, la hauteur et les effets.                              -> gratuit, immédiat
  2. create  : tu règles toi-même voix de base + débit + hauteur + effets.     -> gratuit, immédiat
  3. clone   : à partir d'un enregistrement de TA voix (ou d'une voix dont tu as l'accord),
               via Chatterbox (local, gratuit) ou ElevenLabs (clé API).
"""
import json
import os
import re
import subprocess
from pathlib import Path

from . import voice as edge_voice
from .playbook import VOICES, LANG_NAMES

# ---------------------------------------------------------------- effets audio
# Les effets de hauteur compensent le tempo : la durée ne change pas, les sous-titres restent calés.
EFFECTS = {
    "deep":      ("Voix plus grave", "asetrate=44100*0.88,aresample=44100,atempo=1/0.88"),
    "deeper":    ("Voix très grave (bande-annonce)", "asetrate=44100*0.80,aresample=44100,atempo=1/0.80"),
    "high":      ("Voix plus aiguë", "asetrate=44100*1.12,aresample=44100,atempo=1/1.12"),
    "chipmunk":  ("Voix de cartoon", "asetrate=44100*1.45,aresample=44100,atempo=1/1.45"),
    "warm":      ("Chaleur, basses rondes", "equalizer=f=140:t=q:w=1.2:g=4,equalizer=f=7000:t=q:w=1:g=-2"),
    "broadcast": ("Voix radio pro / podcast", "highpass=f=70,equalizer=f=180:t=q:w=1:g=3,equalizer=f=3500:t=q:w=1.5:g=3,acompressor=threshold=0.08:ratio=4:attack=5:release=120:makeup=2"),
    "crisp":     ("Clarté, présence", "equalizer=f=4500:t=q:w=1.5:g=4,equalizer=f=250:t=q:w=1:g=-2"),
    "radio":     ("Vieille radio", "highpass=f=350,lowpass=f=3200,acompressor=threshold=0.1:ratio=6,volume=1.6"),
    "phone":     ("Téléphone", "highpass=f=500,lowpass=f=2800,volume=1.8"),
    "robot":     ("Robot", "afftfilt=real='hypot(re,im)*sin(0)':imag='hypot(re,im)*cos(0)':win_size=512:overlap=0.75"),
    "whisper":   ("Chuchotement", "afftfilt=real='hypot(re,im)*cos((random(0)*2-1)*2*3.14)':imag='hypot(re,im)*sin((random(1)*2-1)*2*3.14)':win_size=128:overlap=0.8,volume=2"),
    "echo":      ("Écho léger", "aecho=0.8:0.85:45:0.25"),
    "cave":      ("Grande salle / caverne", "aecho=0.8:0.88:90|160:0.35|0.2"),
    "demon":     ("Monstre / démon", "asetrate=44100*0.72,aresample=44100,atempo=1/0.72,aecho=0.8:0.8:40:0.3,equalizer=f=100:t=q:w=1:g=5"),
}


def effect_chain(effects):
    chain = []
    for e in effects or []:
        if e in EFFECTS:
            chain.append(EFFECTS[e][1])
        elif e.startswith("af:"):  # filtre ffmpeg libre, pour les experts
            chain.append(e[3:])
        else:
            raise ValueError(f"Effet inconnu : {e}. Disponibles : {', '.join(EFFECTS)}")
    return ",".join(chain)


def apply_effects(in_path, out_path, effects):
    chain = effect_chain(effects)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(in_path)]
    # rééchantillonnage d'abord : les effets de hauteur supposent du 44,1 kHz
    cmd += ["-af", "aresample=44100" + ("," + chain if chain else "")]
    cmd += ["-ar", "44100", "-ac", "2", str(out_path)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("Effet audio impossible : " + p.stderr[-800:])
    return out_path


# ---------------------------------------------------------------- profils
def voices_dir():
    d = Path(os.getenv("VOICES_DIR", "voices"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _slug(name):
    s = re.sub(r"[^\w-]+", "-", name.strip().lower()).strip("-")
    if not s:
        raise ValueError("Nom de voix invalide")
    return s


def save_profile(profile):
    profile["name"] = _slug(profile["name"])
    path = voices_dir() / f"{profile['name']}.json"
    path.write_text(json.dumps(profile, ensure_ascii=False, indent=2))
    return path


def load_profile(name):
    path = voices_dir() / f"{_slug(name)}.json"
    if not path.exists():
        raise FileNotFoundError(f"Voix « {name} » introuvable dans {voices_dir()} (python -m viral_agent voice list)")
    return json.loads(path.read_text())


def list_profiles():
    out = []
    for p in sorted(voices_dir().glob("*.json")):
        try:
            out.append(json.loads(p.read_text()))
        except json.JSONDecodeError:
            pass
    return out


def delete_profile(name):
    slug = _slug(name)
    for p in [voices_dir() / f"{slug}.json"]:
        p.unlink(missing_ok=True)
    d = voices_dir() / slug
    if d.is_dir():
        for f in d.iterdir():
            f.unlink()
        d.rmdir()


def create_profile(name, lang="fr", base_voice=None, style="male", rate="+8%", pitch="+0Hz",
                   volume="+0%", effects=(), description=""):
    profile = {"name": name, "description": description, "engine": "edge", "lang": lang,
               "edge": {"voice": edge_voice.pick_voice(lang, style, base_voice), "rate": _fmt_pct(rate),
                        "pitch": _fmt_hz(pitch), "volume": _fmt_pct(volume)},
               "effects": list(effects)}
    effect_chain(profile["effects"])  # valide
    save_profile(profile)
    return profile


def _fmt_pct(v):
    v = str(v).strip()
    if not v.endswith("%"):
        v += "%"
    return v if v[0] in "+-" else "+" + v


def _fmt_hz(v):
    v = str(v).strip()
    if not v.lower().endswith("hz"):
        v += "Hz"
    v = v[:-2] + "Hz"
    return v if v[0] in "+-" else "+" + v


# ---------------------------------------------------------------- design par IA
def available_edge_voices(lang, ca_bundle=None):
    """Liste les voix Edge de la langue (avec genre et personnalité)."""
    import asyncio
    import edge_tts
    edge_voice._patch_ssl(ca_bundle)
    try:
        allv = asyncio.run(edge_tts.list_voices())
    except Exception:
        return [{"ShortName": v, "Gender": k} for k, v in VOICES.get(lang, VOICES["en"]).items()]
    return [v for v in allv if v["Locale"].lower().startswith(lang.lower())]


def design_profile(llm, name, description, lang="fr", ca_bundle=None):
    voices = available_edge_voices(lang, ca_bundle)
    catalog = [{"voice": v["ShortName"], "gender": v.get("Gender"),
                "personality": ", ".join(v.get("VoiceTag", {}).get("VoicePersonalities", []) or [])}
               for v in voices]
    system = ("Tu es directeur artistique voix pour des vidéos TikTok/Reels/Shorts. "
              "Tu transformes une description de voix en réglages techniques précis.")
    user = f"""Voix souhaitée : « {description} »
Langue : {LANG_NAMES.get(lang, lang)}

Voix de base disponibles : {json.dumps(catalog, ensure_ascii=False)}

Effets disponibles : {json.dumps({k: v[0] for k, v in EFFECTS.items()}, ensure_ascii=False)}

Choisis la voix de base la plus adaptée et les réglages. Garde une voix naturelle et intelligible :
rate entre -25% et +30%, pitch entre -20Hz et +20Hz, 0 à 3 effets (n'utilise robot/demon/chipmunk/whisper
que si la description le demande explicitement).

JSON attendu :
{{"voice": "nom exact d'une voix de base", "rate": "+10%", "pitch": "-5Hz", "volume": "+0%",
  "effects": ["..."], "why": "explication courte"}}"""
    d = llm.json(system, user, temperature=0.4)
    valid = {v["voice"] for v in catalog}
    base = d.get("voice") if d.get("voice") in valid else edge_voice.pick_voice(lang)
    effects = [e for e in d.get("effects", []) if e in EFFECTS][:3]
    profile = create_profile(name, lang, base, rate=d.get("rate", "+8%"), pitch=d.get("pitch", "+0Hz"),
                             volume=d.get("volume", "+0%"), effects=effects, description=description)
    profile["why"] = d.get("why", "")
    save_profile(profile)
    return profile


# ---------------------------------------------------------------- clonage
CONSENT_TEXT = ("Je confirme que cette voix est la mienne, ou que j'ai l'autorisation explicite de la personne "
                "pour la cloner, et que je ne l'utiliserai pas pour me faire passer pour quelqu'un.")


def prepare_sample(src, dst, max_seconds=20):
    """Nettoie l'échantillon : mono, 24 kHz, débruité, silences retirés, normalisé, ≤ 20 s."""
    af = ("highpass=f=60,afftdn=nf=-25,"
          "silenceremove=start_periods=1:start_threshold=-45dB:stop_periods=-1:stop_threshold=-45dB:stop_duration=0.6,"
          "loudnorm=I=-18:TP=-2")
    p = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-af", af, "-ac", "1",
                        "-ar", "24000", "-t", str(max_seconds), str(dst)], capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("Échantillon illisible : " + p.stderr[-500:])
    dur = edge_voice.audio_duration(dst)
    if dur < 5:
        raise ValueError(f"Échantillon trop court ({dur:.1f}s de parole). Il faut 10 à 20 s de parole claire.")
    return dst, dur


def clone_profile(name, sample, lang="fr", engine="chatterbox", consent=False, effects=(),
                  exaggeration=0.5, cfg_weight=0.5, description=""):
    if not consent:
        raise PermissionError("Clonage refusé sans consentement. Relance avec --consent si : " + CONSENT_TEXT)
    slug = _slug(name)
    folder = voices_dir() / slug
    folder.mkdir(parents=True, exist_ok=True)
    ref, dur = prepare_sample(sample, folder / "reference.wav")
    profile = {"name": slug, "description": description or f"Voix clonée depuis {Path(sample).name}",
               "engine": engine, "lang": lang, "effects": list(effects),
               "clone": {"reference": str(ref), "reference_seconds": round(dur, 1),
                         "exaggeration": exaggeration, "cfg_weight": cfg_weight},
               "consent": CONSENT_TEXT}
    effect_chain(profile["effects"])
    if engine == "elevenlabs":
        profile["elevenlabs"] = {"voice_id": _eleven_add_voice(slug, ref)}
    elif engine == "chatterbox":
        _chatterbox_model(lang)  # vérifie que c'est installé, télécharge le modèle au 1er usage
    else:
        raise ValueError("Moteur de clonage inconnu (chatterbox | elevenlabs)")
    save_profile(profile)
    return profile


# ---- Chatterbox (local, gratuit, open source MIT)
_CB = {}


def _chatterbox_model(lang):
    key = "en" if lang == "en" else "mtl"
    if key in _CB:
        return _CB[key]
    try:
        import torch
        if key == "en":
            from chatterbox.tts import ChatterboxTTS as M
        else:
            from chatterbox.mtl_tts import ChatterboxMultilingualTTS as M
    except ImportError:
        raise RuntimeError("Chatterbox n'est pas installé. Installe-le avec :\n"
                           "  pip install chatterbox-tts --extra-index-url https://download.pytorch.org/whl/cpu")
    device = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
    _CB[key] = M.from_pretrained(device=device)
    return _CB[key]


def _chatterbox_tts(profile, text, out_path):
    import torchaudio
    lang = profile.get("lang", "fr")
    model = _chatterbox_model(lang)
    c = profile["clone"]
    kw = dict(audio_prompt_path=c["reference"], exaggeration=c.get("exaggeration", 0.5),
              cfg_weight=c.get("cfg_weight", 0.5))
    if lang != "en":
        kw["language_id"] = lang
    wav = model.generate(text, **kw)
    torchaudio.save(str(out_path), wav, model.sr)
    return out_path


# ---- ElevenLabs (cloud, clé API, timings exacts)
def _eleven_key():
    k = os.getenv("ELEVENLABS_API_KEY")
    if not k:
        raise RuntimeError("Définis ELEVENLABS_API_KEY pour utiliser ElevenLabs.")
    return k


def _eleven_add_voice(name, ref):
    import requests
    with open(ref, "rb") as f:
        r = requests.post("https://api.elevenlabs.io/v1/voices/add", headers={"xi-api-key": _eleven_key()},
                          data={"name": name}, files={"files": (Path(ref).name, f, "audio/wav")}, timeout=120)
    r.raise_for_status()
    return r.json()["voice_id"]


def _eleven_tts(profile, text, out_path):
    import base64
    import requests
    vid = profile["elevenlabs"]["voice_id"]
    r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}/with-timestamps",
                      headers={"xi-api-key": _eleven_key()},
                      json={"text": text, "model_id": os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")},
                      timeout=180)
    r.raise_for_status()
    data = r.json()
    Path(out_path).write_bytes(base64.b64decode(data["audio_base64"]))
    al = data.get("alignment") or {}
    words, cur, start, end = [], "", None, None
    for ch, s, e in zip(al.get("characters", []), al.get("character_start_times_seconds", []),
                        al.get("character_end_times_seconds", [])):
        if ch.isspace():
            if cur:
                words.append({"word": cur, "start": start, "end": end})
            cur, start = "", None
            continue
        if start is None:
            start = s
        cur += ch
        end = e
    if cur:
        words.append({"word": cur, "start": start, "end": end})
    return words


# ---------------------------------------------------------------- timings mot à mot
_WHISPER = {}


def word_timings(audio_path, text, duration, lang="fr"):
    """Timings mot par mot pour les moteurs qui n'en donnent pas : faster-whisper si dispo, sinon estimation."""
    words = text.split()
    try:
        from faster_whisper import WhisperModel
        if "m" not in _WHISPER:
            _WHISPER["m"] = WhisperModel(os.getenv("WHISPER_MODEL", "base"), device="cpu", compute_type="int8")
        import numpy as np  # décodage via ffmpeg : évite les incompatibilités de PyAV
        pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(audio_path), "-ac", "1", "-ar", "16000",
                              "-f", "f32le", "-"], capture_output=True, check=True).stdout
        segs, _ = _WHISPER["m"].transcribe(np.frombuffer(pcm, np.float32), language=lang, word_timestamps=True)
        found = [w for s in segs for w in (s.words or [])]
        if found:
            # on garde l'orthographe du script (Whisper peut mal transcrire), avec les temps de Whisper
            if len(found) == len(words):
                return [{"word": t, "start": w.start, "end": w.end} for t, w in zip(words, found)]
            merged = []
            for w in found:
                t = w.word.strip()
                if merged and (t[:1] in "'’-" or merged[-1]["word"][-1:] in "'’"):
                    merged[-1]["word"] += t
                    merged[-1]["end"] = w.end
                elif t:
                    merged.append({"word": t, "start": w.start, "end": w.end})
            return merged
    except ImportError:
        pass
    except Exception as e:
        print(f"   ⚠️  alignement Whisper impossible ({str(e)[:80]}), timings estimés")
    # estimation proportionnelle au nombre de caractères
    lead, usable = 0.05, max(duration - 0.15, 0.1)
    weights = [len(w) + 2 for w in words]
    total, t, out = sum(weights), lead, []
    for w, wt in zip(words, weights):
        d = usable * wt / total
        out.append({"word": w, "start": t, "end": t + d * 0.92})
        t += d
    return out


# ---------------------------------------------------------------- synthèse unifiée
def synthesize(profile, text, out_path, ca_bundle=None):
    """Génère la voix d'un profil. Retourne (durée, [{word,start,end}])."""
    out_path = Path(out_path)
    raw = out_path.with_name(out_path.stem + "_raw" + (".mp3" if profile["engine"] in ("edge", "elevenlabs") else ".wav"))
    engine = profile["engine"]
    if engine == "edge":
        e = profile["edge"]
        _, words = edge_voice.synthesize(text, raw, e["voice"], rate=e.get("rate", "+0%"),
                                         pitch=e.get("pitch", "+0Hz"), ca_bundle=ca_bundle,
                                         volume=e.get("volume", "+0%"))
    elif engine == "elevenlabs":
        words = _eleven_tts(profile, text, raw)
    elif engine == "chatterbox":
        _chatterbox_tts(profile, text, raw)
        words = None
    else:
        raise ValueError(f"Moteur inconnu : {engine}")
    apply_effects(raw, out_path, profile.get("effects"))
    dur = edge_voice.audio_duration(out_path)
    if not words:
        words = word_timings(out_path, text, dur, profile.get("lang", "fr"))
    return dur, words
