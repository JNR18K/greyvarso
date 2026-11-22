"""Skill : habillage graphique. Bandeaux d'alerte, étiquette de série, carte de fin (PNG transparents)."""
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"

BANNER_COLORS = {
    "red": ((214, 32, 39), (160, 18, 24)),
    "blue": ((24, 92, 214), (14, 60, 150)),
    "green": ((22, 163, 74), (14, 110, 50)),
    "black": ((28, 28, 32), (0, 0, 0)),
    "orange": ((240, 120, 20), (180, 80, 10)),
    "purple": ((124, 58, 237), (88, 28, 180)),
}


def _font(kind, size):
    if kind == "round":
        p = FONTS_DIR / "FredokaBold.ttf"
        if p.exists():
            return ImageFont.truetype(str(p), size)
    q = {"black": "Inter Display:black", "bold": "Inter Display:bold"}.get(kind, "Inter Display:bold")
    path = subprocess.run(["fc-match", "-f", "%{file}", q], capture_output=True, text=True).stdout.strip()
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def _fit(draw, text, kind, size, max_w):
    while size > 30:
        f = _font(kind, size)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 4
    return _font(kind, size)


def _warning_icon(draw, x, y, s, color=(255, 255, 255)):
    draw.polygon([(x + s / 2, y), (x + s, y + s * 0.9), (x, y + s * 0.9)], outline=color, width=max(3, s // 9))
    draw.line([(x + s / 2, y + s * 0.32), (x + s / 2, y + s * 0.6)], fill=color, width=max(3, s // 9))
    draw.ellipse([x + s / 2 - s * 0.06, y + s * 0.68, x + s / 2 + s * 0.06, y + s * 0.8], fill=color)


def make_banner(out_path, title, label="", subtitle="", color="red", width=1080, icon=True):
    """Bandeau type « ALERTE D'URGENCE » (cf. vidéos POV). Retourne (chemin, hauteur)."""
    top, bottom = BANNER_COLORS.get(color, BANNER_COLORS["red"])
    pad, mx = 46, 0
    tmp = Image.new("RGBA", (width, 10))
    d = ImageDraw.Draw(tmp)
    f_label = _font("bold", 44)
    f_title = _fit(d, title.upper(), "black", 118, width - 2 * pad)
    f_sub = _font("round", 56)
    h = pad
    if label:
        h += 58
    h += int(f_title.size * 1.05)
    if subtitle:
        h += 74
    h += pad - 6
    img = Image.new("RGBA", (width, h + 30), (0, 0, 0, 0))
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([mx + 4, 14, width - mx - 4, h + 12], 22, fill=(0, 0, 0, 120))
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(10)))
    grad = Image.new("RGBA", (width, h))
    gd = ImageDraw.Draw(grad)
    for yy in range(h):
        t = yy / h
        gd.line([(0, yy), (width, yy)], fill=tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3)) + (255,))
    mask = Image.new("L", (width, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([mx, 0, width - mx - 1, h - 1], 22, fill=255)
    img.paste(grad, (0, 0), mask)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([mx, 0, width - mx - 1, h - 1], 22, outline=(255, 255, 255, 70), width=3)
    y = pad
    if label:
        x = pad
        if icon:
            _warning_icon(d, x, y + 2, 40)
            x += 54
        d.text((x, y), label.upper(), font=f_label, fill="white")
        y += 58
    d.text((pad, y - 8), title.upper(), font=f_title, fill="white", stroke_width=3, stroke_fill=(0, 0, 0, 90))
    y += int(f_title.size * 1.05)
    if subtitle:
        d.text((pad, y), subtitle, font=f_sub, fill="white")
    img.save(out_path)
    return out_path, img.height


def make_series_tag(out_path, text, width=1080):
    """Petite pastille « WAR DOGS · PARTIE 3/30 » en haut de l'écran."""
    f = _font("round", 40)
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    tw = int(tmp.textlength(text, font=f))
    w, h = tw + 56, 70
    img = Image.new("RGBA", (w + 20, h + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([10, 10, 10 + w, 10 + h], h // 2, fill=(0, 0, 0, 150), outline=(255, 255, 255, 90), width=2)
    d.text((10 + 28, 10 + 13), text, font=f, fill="white")
    img.save(out_path)
    return out_path
