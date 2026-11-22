"""Skill : voix off. Edge TTS (gratuit, voix neuronales) avec timing mot par mot pour les sous-titres."""
import asyncio
import ssl
import subprocess

import edge_tts
import edge_tts.communicate as _comm

from .playbook import VOICES


def _patch_ssl(ca_bundle):
    if ca_bundle:
        _comm._SSL_CTX = ssl.create_default_context(cafile=ca_bundle)


def pick_voice(lang="fr", style="male", voice=None):
    if voice:
        return voice
    return VOICES.get(lang, VOICES["en"]).get(style, VOICES.get(lang, VOICES["en"])["male"])


async def _tts(text, voice, rate, pitch, out_path, volume="+0%"):
    words = []
    com = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, volume=volume, boundary="WordBoundary")
    with open(out_path, "wb") as f:
        async for ch in com.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                start = ch["offset"] / 1e7
                words.append({"word": ch["text"], "start": start, "end": start + ch["duration"] / 1e7})
    return words


def audio_duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True)
    return float(out.stdout.strip())


def synthesize(text, out_path, voice, rate="+8%", pitch="+0Hz", ca_bundle=None, retries=3, volume="+0%"):
    """Retourne (durée, [{word,start,end}])."""
    _patch_ssl(ca_bundle)
    err = None
    for _ in range(retries):
        try:
            words = asyncio.run(_tts(text, voice, rate, pitch, str(out_path), volume))
            return audio_duration(out_path), words
        except Exception as e:
            err = e
    raise RuntimeError(f"Synthèse vocale impossible : {err}")
