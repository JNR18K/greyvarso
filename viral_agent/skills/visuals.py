"""Skill : directeur artistique. Génère une image par scène (Pollinations / Flux, gratuit)."""
import random
import time
import urllib.parse

import requests
from PIL import Image, ImageDraw, ImageFilter

from .playbook import VISUAL_STYLES

NEGATIVE = "no text, no watermark, no letters, no logo"


def build_prompt(visual, style="cinematic", subject_hint=""):
    style_txt = VISUAL_STYLES.get(style, style)
    hint = f", {subject_hint}" if subject_hint else ""
    return f"{visual}{hint}, {style_txt}, vertical composition, {NEGATIVE}"


def generate_image(cfg, prompt, out_path, seed=None, retries=5, session=None):
    s = session or requests.Session()
    if cfg.ca_bundle:
        s.verify = cfg.ca_bundle
    seed = seed if seed is not None else random.randint(1, 10_000_000)
    url = cfg.image_url.format(prompt=urllib.parse.quote(prompt))
    params = {"width": cfg.width, "height": cfg.height, "seed": seed, "nologo": "true",
              "model": cfg.image_model, "enhance": "false"}
    for attempt in range(retries):
        try:
            headers = {"Authorization": f"Bearer {cfg.image_token}"} if cfg.image_token else {}
            r = s.get(url, params=params, headers=headers, timeout=180)
            if r.ok and r.headers.get("content-type", "").startswith("image"):
                with open(out_path, "wb") as f:
                    f.write(r.content)
                Image.open(out_path).convert("RGB").save(out_path, "JPEG", quality=95)
                return out_path
        except Exception:
            pass
        time.sleep(8 * (attempt + 1))
    print(f"   ⚠️  image indisponible, fond de secours utilisé pour {out_path}")
    return fallback_image(cfg, out_path, seed)


def fallback_image(cfg, out_path, seed=0):
    """Fond dégradé animé-friendly si le générateur d'images est indisponible."""
    rnd = random.Random(seed)
    c1 = tuple(rnd.randint(20, 120) for _ in range(3))
    c2 = tuple(rnd.randint(120, 255) for _ in range(3))
    img = Image.new("RGB", (cfg.width, cfg.height))
    d = ImageDraw.Draw(img)
    for y in range(cfg.height):
        t = y / cfg.height
        d.line([(0, y), (cfg.width, y)], fill=tuple(int(c1[i] * (1 - t) + c2[i] * t) for i in range(3)))
    for _ in range(12):
        x, y, r = rnd.randint(0, cfg.width), rnd.randint(0, cfg.height), rnd.randint(80, 400)
        d.ellipse([x - r, y - r, x + r, y + r], fill=tuple(rnd.randint(60, 255) for _ in range(3)))
    img.filter(ImageFilter.GaussianBlur(60)).save(out_path, "JPEG", quality=92)
    return out_path
