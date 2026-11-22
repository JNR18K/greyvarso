"""Skill : sous-titres style TikTok. Mots qui popent, mot courant surligné, mot-clé en couleur."""
import re

HIGHLIGHT = "&H0000F0FF&"   # jaune (BGR)
EMPHASIS = "&H005CFF39&"    # vert fluo
WHITE = "&H00FFFFFF&"


def _ts(t):
    t = max(t, 0)
    h, m = int(t // 3600), int(t % 3600 // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _clean(w):
    return re.sub(r"[{}\\]", "", w)


def _norm(w):
    return re.sub(r"[^\w]", "", w.lower())


def chunk_words(words, max_words=3, max_chars=14):
    chunks, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or len(" ".join(x["word"] for x in cur + [w])) > max_chars
                    or w["start"] - cur[-1]["end"] > 0.35):
            chunks.append(cur)
            cur = []
        cur.append(w)
        if re.search(r"[.!?…]$", w["word"]):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return chunks


def build_ass(words, out_path, width=1080, height=1920, emphasis_words=(), font="Inter Display",
              font_size=124, position="center"):
    emph = {_norm(e) for phrase in emphasis_words for e in (phrase or "").split() if len(_norm(e)) > 2}
    margin_v = {"center": int(height * 0.40), "low": int(height * 0.22), "high": int(height * 0.62)}[position]
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,{font},{font_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,-1,0,0,0,100,100,2,0,1,9,5,2,50,50,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for chunk in chunk_words(words):
        c_end = chunk[-1]["end"] + 0.08
        for i, w in enumerate(chunk):
            start = w["start"]
            end = chunk[i + 1]["start"] if i + 1 < len(chunk) else c_end
            parts = []
            for j, x in enumerate(chunk):
                txt = _clean(x["word"]).upper()
                is_emph = _norm(x["word"]) in emph
                if j == i:
                    col = EMPHASIS if is_emph else HIGHLIGHT
                    parts.append(r"{\c" + col + r"\fscx112\fscy112}" + txt + r"{\c" + WHITE + r"\fscx100\fscy100}")
                else:
                    parts.append(r"{\c" + (EMPHASIS if is_emph else WHITE) + "}" + txt)
            pop = r"{\fad(0,0)\t(0,60,\fscx108\fscy108)\t(60,140,\fscx100\fscy100)}" if i == 0 else ""
            lines.append(f"Dialogue: 0,{_ts(start)},{_ts(end)},Main,,0,0,0,,{pop}{' '.join(parts)}")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(lines) + "\n")
    return out_path
