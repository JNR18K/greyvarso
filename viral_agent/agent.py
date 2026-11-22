"""L'agent : orchestre toutes les skills de l'idée jusqu'à la vidéo publiable."""
import json
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

from .config import Config
from .llm import LLM
from .skills import trends, script as scriptwriter, critic, seo, voice, voice_lab, visuals, captions, editor


def slugify(s, n=40):
    s = re.sub(r"[^\w\s-]", "", s.lower()).strip()
    return re.sub(r"[\s_-]+", "-", s)[:n] or "video"


class ViralAgent:
    def __init__(self, cfg: Config = None, verbose=True):
        self.cfg = cfg or Config()
        self.llm = LLM(self.cfg, verbose)
        self.verbose = verbose

    def log(self, *a):
        if self.verbose:
            print(*a, flush=True)

    # ---------- Skills de haut niveau ----------
    def ideas(self, niche, count=5, lang="fr"):
        self.log(f"🔎 Recherche d'idées virales pour « {niche} »…")
        return trends.find_ideas(self.llm, niche, count, lang)

    def script(self, topic, lang="fr", duration=35, tone="captivant", hook=None, fmt=None):
        self.log("✍️  Écriture du script…")
        sc = scriptwriter.write_script(self.llm, topic, lang, duration, tone, hook, fmt)
        best, best_score = sc, -1
        for i in range(self.cfg.max_rewrites + 1):
            crit = critic.critique(self.llm, sc)
            score = crit["overall"]
            self.log(f"🧐 Score viral v{i+1} : {score:.1f}/10  " +
                     " ".join(f"{k}={v}" for k, v in crit.get("scores", {}).items()))
            if score > best_score:
                best, best_score, best_crit = sc, score, crit
            if score >= self.cfg.min_viral_score or i == self.cfg.max_rewrites:
                break
            self.log("♻️  Réécriture pour corriger : " + "; ".join(crit.get("weaknesses", [])[:3]))
            sc = scriptwriter.rewrite_script(self.llm, sc, crit, lang, duration)
        best["_critique"] = best_crit
        best["_score"] = best_score
        return best

    # ---------- Pipeline complet ----------
    def make_video(self, topic, out_dir="output", lang="fr", duration=35, style="cinematic",
                   voice_style="male", voice_name=None, rate="+8%", tone="captivant", music=None,
                   hook=None, fmt=None, niche="", script_data=None, caption_pos="center", voice_profile=None):
        t0 = time.time()
        cfg = self.cfg
        sc = script_data or self.script(topic, lang, duration, tone, hook, fmt)
        scenes = [s for s in sc.get("scenes", []) if s.get("text", "").strip()]
        if not scenes:
            raise RuntimeError("Le script ne contient aucune scène.")
        work = Path(out_dir) / f"{time.strftime('%Y%m%d-%H%M%S')}-{slugify(sc.get('title') or topic)}"
        (work / "parts").mkdir(parents=True, exist_ok=True)
        (work / "script.json").write_text(json.dumps(sc, ensure_ascii=False, indent=2))
        self.log(f"🎬 « {sc.get('title', topic)} » — {len(scenes)} scènes → {work}")

        # Images en parallèle pendant la voix
        seed = random.randint(1, 9_000_000)
        session = requests.Session()
        def gen(i):
            p = visuals.build_prompt(scenes[i].get("visual") or scenes[i]["text"], style)
            return visuals.generate_image(cfg, p, work / "parts" / f"img_{i:02d}.jpg", seed + i, session=session)
        self.log(f"🎨 Génération de {len(scenes)} images (style {style})…")
        pool = ThreadPoolExecutor(max_workers=2 if cfg.image_token else 1)
        img_futures = [pool.submit(gen, i) for i in range(len(scenes))]

        # Voix scène par scène -> timings exacts
        if voice_profile:
            profile = voice_lab.load_profile(voice_profile) if isinstance(voice_profile, str) else voice_profile
        else:
            profile = {"name": "défaut", "engine": "edge", "lang": lang, "effects": [],
                       "edge": {"voice": voice.pick_voice(lang, voice_style, voice_name), "rate": rate}}
        self.log(f"🎙️  Voix off ({profile['name']} · {profile['engine']})…")
        audio_parts, all_words, durations, offset = [], [], [], 0.0
        for i, s in enumerate(scenes):
            ap = work / "parts" / f"voice_{i:02d}.mp3"
            dur, words = voice_lab.synthesize(profile, s["text"], ap, ca_bundle=cfg.ca_bundle)
            dur += 0.12  # micro-respiration entre scènes
            for w in words:
                all_words.append({"word": w["word"], "start": w["start"] + offset, "end": w["end"] + offset})
            audio_parts.append(ap)
            durations.append(dur)
            offset += dur
        total = offset
        # pad chaque morceau à sa durée exacte, puis concat
        padded = []
        for i, (ap, d) in enumerate(zip(audio_parts, durations)):
            pp = work / "parts" / f"voicep_{i:02d}.wav"
            editor.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(ap), "-af", "apad",
                        "-t", f"{d:.3f}", "-ar", "44100", "-ac", "2", str(pp)])
            padded.append(pp)
        voice_wav = editor.concat_audio(padded, work / "parts" / "voice.wav")

        images = [f.result() for f in img_futures]
        pool.shutdown()

        self.log("✂️  Montage des scènes…")
        moves = editor.pick_moves(len(scenes), seed)
        clips = []
        for i, (img, d) in enumerate(zip(images, durations)):
            clips.append(editor.render_scene(img, d, work / "parts" / f"clip_{i:02d}.mp4", moves[i],
                                             cfg.width, cfg.height, cfg.fps, flash=i > 0))

        self.log("💬 Sous-titres animés…")
        ass = captions.build_ass(all_words, work / "parts" / "subs.ass", cfg.width, cfg.height,
                                 emphasis_words=[s.get("emphasis", "") for s in scenes], position=caption_pos)

        self.log("🎞️  Rendu final…")
        final = editor.assemble(clips, voice_wav, ass, work / "video.mp4", total, music=music,
                                w=cfg.width, h=cfg.height)

        self.log("📈 Métadonnées de publication…")
        try:
            meta = seo.make_metadata(self.llm, {k: v for k, v in sc.items() if not k.startswith("_")}, lang, niche)
        except Exception as e:
            meta = {"error": str(e)}
        (work / "publish.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
        cover_text = meta.get("cover_text") or sc.get("title", topic)
        editor.make_cover(images[0], cover_text, work / "cover.jpg", cfg.width, cfg.height)
        (work / "POST.md").write_text(_post_md(sc, meta, total))

        self.log(f"✅ Terminé en {time.time()-t0:.0f}s — {final} ({total:.1f}s)")
        return {"dir": str(work), "video": str(final), "cover": str(work / "cover.jpg"),
                "duration": total, "score": sc.get("_score"), "title": sc.get("title")}

    def autopilot(self, niche, count=3, **kw):
        """Trouve les meilleures idées d'une niche et produit `count` vidéos."""
        ideas = self.ideas(niche, max(count * 2, 5), kw.get("lang", "fr"))
        results = []
        for idea in ideas[:count]:
            self.log(f"\n━━━ {idea.get('topic')} ({idea.get('format')}, potentiel {idea.get('potential')}) ━━━")
            try:
                results.append(self.make_video(idea["topic"], hook=idea.get("hook"), fmt=idea.get("format"),
                                               niche=niche, **kw))
            except Exception as e:
                self.log(f"❌ Échec : {e}")
        return results


def _post_md(sc, meta, total):
    lines = [f"# {sc.get('title', '')}", "", f"Durée : {total:.1f}s · Score viral : {sc.get('_score', '?')}/10", ""]
    for plat in ("tiktok", "instagram"):
        m = meta.get(plat) or {}
        if m:
            lines += [f"## {plat.capitalize()}", "", m.get("caption", ""), "", " ".join(m.get("hashtags", [])), ""]
    yt = meta.get("youtube") or {}
    if yt:
        lines += ["## YouTube Shorts", "", f"**{yt.get('title', '')}**", "", yt.get("description", ""), "",
                  ", ".join(yt.get("tags", [])), ""]
    if meta.get("pinned_comment"):
        lines += ["## Commentaire à épingler", "", meta["pinned_comment"], ""]
    if meta.get("best_times"):
        lines += ["## Meilleures heures", ""] + [f"- {t}" for t in meta["best_times"]] + [""]
    if meta.get("series_ideas"):
        lines += ["## Suites possibles", ""] + [f"- {t}" for t in meta["series_ideas"]] + [""]
    lines += ["## Script", ""] + [f"{i+1}. {s['text']}" for i, s in enumerate(sc.get("scenes", []))]
    crit = sc.get("_critique") or {}
    if crit.get("better_hooks"):
        lines += ["", "## Hooks alternatifs (A/B test)", ""] + [f"- {h}" for h in crit["better_hooks"]]
    return "\n".join(lines) + "\n"
