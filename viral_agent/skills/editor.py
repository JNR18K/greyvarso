"""Skill : monteur. Ken Burns sur chaque image, flash de transition, barre de progression,
sous-titres incrustés, musique de fond avec ducking automatique. Sortie 1080x1920 H.264."""
import random
import subprocess
from pathlib import Path


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("ffmpeg a échoué :\n" + p.stderr[-2500:])


MOVES = ["zoom_in", "zoom_out", "pan_up", "pan_down", "zoom_in_left", "zoom_in_right"]
SPECIAL_MOVES = ["walk", "run", "shake", "push", "static"]


def _zoompan(move, frames, w, h):
    d = frames
    z_in = f"min(1+0.18*on/{d},1.18)"
    z_out = f"max(1.18-0.18*on/{d},1.0)"
    cx, cy = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    exprs = {
        "zoom_in": (z_in, cx, cy),
        "zoom_out": (z_out, cx, cy),
        "pan_up": ("1.15", cx, f"(ih-ih/zoom)*(1-on/{d})"),
        "pan_down": ("1.15", cx, f"(ih-ih/zoom)*on/{d}"),
        "zoom_in_left": (z_in, f"(iw-iw/zoom)*0.2", cy),
        "zoom_in_right": (z_in, f"(iw-iw/zoom)*0.8", cy),
        # POV : balancement de marche / course, tremblement, poussée dramatique
        "walk": ("1.14", f"{cx}+sin(on*2*PI/16)*10", f"{cy}+abs(sin(on*2*PI/16))*-22+11"),
        "run": (f"1.16+0.04*on/{d}", f"{cx}+sin(on*2*PI/9)*16", f"{cy}+abs(sin(on*2*PI/9))*-38+19"),
        "shake": ("1.15", f"{cx}+sin(on*1.9)*14+sin(on*4.3)*7", f"{cy}+cos(on*2.3)*12+sin(on*5.1)*6"),
        "push": (f"min(1+0.35*on/{d},1.35)", cx, cy),
        "static": ("1.04", cx, cy),
    }
    z, x, y = exprs[move]
    return f"zoompan=z='{z}':x='{x}':y='{y}':d={d}:s={w}x{h}:fps=30"


def render_scene(image, duration, out_path, move, w=1080, h=1920, fps=30, flash=True, overlays=()):
    """overlays : [(png, x, y, mode)] ; mode 'slide' = descend du haut, 'static' = fixe."""
    frames = max(int(round(duration * fps)), 1)
    vf = ("crop=iw:ih*0.93:0:0,"  # retire le filigrane éventuel en bas de l'image
          f"scale={w*2}:{h*2}:force_original_aspect_ratio=increase,crop={w*2}:{h*2},"
          f"{_zoompan(move, frames, w, h)},"
          "eq=contrast=1.06:saturation=1.15,"
          "vignette=PI/5")
    if flash:  # flash blanc de 3 images = pattern interrupt
        vf += ",fade=t=in:st=0:d=0.12:color=white"
    inputs = ["-loop", "1", "-i", str(image)]
    graph = f"[0:v]{vf}[b0]"
    for k, (png, x, y, mode) in enumerate(overlays or []):
        inputs += ["-loop", "1", "-i", str(png)]
        ys = f"if(lt(t,0.25),-h+(t/0.25)*({y}+h),{y})" if mode == "slide" else str(y)
        graph += f";[b{k}][{k+1}:v]overlay=x={x}:y='{ys}':shortest=1[b{k+1}]"
    graph += f";[b{len(overlays or [])}]format=yuv420p[out]"
    run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", graph, "-map", "[out]",
         "-frames:v", str(frames), "-r", str(fps), "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "20", str(out_path)])
    return out_path


def concat_audio(parts, out_path, gap=0.0):
    lst = Path(out_path).with_suffix(".txt")
    lst.write_text("".join(f"file '{Path(p).resolve()}'\n" for p in parts))
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
         "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", str(out_path)])
    return out_path


def assemble(scene_clips, voice_audio, ass_file, out_path, total, music=None, music_volume=0.14,
             progress_bar=True, w=1080, h=1920):
    lst = Path(out_path).with_name("clips.txt")
    lst.write_text("".join(f"file '{Path(c).resolve()}'\n" for c in scene_clips))
    ass = str(Path(ass_file).resolve()).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
    fonts = str(Path(__file__).resolve().parent.parent / "assets" / "fonts").replace(":", r"\:")
    vchain = f"[0:v]subtitles='{ass}':fontsdir='{fonts}'"
    if progress_bar:
        vchain += (f",drawbox=x=0:y=0:w=iw:h=14:color=black@0.35:t=fill"
                   f",drawbox=x=0:y=0:w='iw*t/{total:.3f}':h=14:color=0xFFD000@0.95:t=fill")
    vchain += "[v]"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
           "-i", str(voice_audio)]
    if music:
        cmd += ["-stream_loop", "-1", "-i", str(music)]
        achain = (f"[2:a]volume={music_volume},afade=t=out:st={max(total-1.5,0):.2f}:d=1.5[m];"
                  f"[m][1:a]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=300[md];"
                  f"[1:a][md]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5[a]")
    else:
        achain = "[1:a]loudnorm=I=-14:TP=-1.5[a]"
    cmd += ["-filter_complex", vchain + ";" + achain, "-map", "[v]", "-map", "[a]",
            "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
            "-profile:v", "high", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
            "-ar", "44100", "-movflags", "+faststart", str(out_path)]
    run(cmd)
    return out_path


def make_cover(image, text, out_path, w=1080, h=1920, font="Inter Display"):
    """Miniature : image + gros texte."""
    from PIL import Image, ImageDraw, ImageFont, ImageEnhance
    img = Image.open(image).convert("RGB")
    img = img.crop((0, 0, img.width, int(img.height * 0.93))).resize((w, h))
    img = ImageEnhance.Brightness(img).enhance(0.7)
    d = ImageDraw.Draw(img)
    font_path = _find_font()
    words, lines, cur = text.upper().split(), [], ""
    for wd in words:
        if len(cur + " " + wd) > 12 and cur:
            lines.append(cur)
            cur = wd
        else:
            cur = (cur + " " + wd).strip()
    lines.append(cur)
    size = 150
    f = ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()
    y = h // 2 - len(lines) * size // 2
    for i, line in enumerate(lines):
        tw = d.textlength(line, font=f)
        d.text(((w - tw) / 2, y), line, font=f, fill=(255, 208, 0) if i % 2 == 0 else (255, 255, 255),
               stroke_width=10, stroke_fill=(0, 0, 0))
        y += int(size * 1.1)
    img.save(out_path, "JPEG", quality=92)
    return out_path


def _find_font():
    out = subprocess.run(["fc-match", "-f", "%{file}", "Inter Display:black"], capture_output=True, text=True)
    return out.stdout.strip() or None


def pick_moves(n, seed=None):
    rnd = random.Random(seed)
    moves, last = [], None
    for _ in range(n):
        m = rnd.choice([x for x in MOVES if x != last])
        moves.append(m)
        last = m
    return moves
