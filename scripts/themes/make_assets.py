# -*- coding: utf-8 -*-
"""Boîte à outils PIL pour les visuels de fiche Odoo Apps Store (DYONYSOS).

Tout est généré ici : aucun visuel n'est téléchargé. Les polices utilisées sont
celles du système (Liberation, Carlito, Lora, Poppins), toutes sous licence
libre.
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT_DIRS = [
    "/usr/share/fonts/truetype/google-fonts",
    "/usr/share/fonts/truetype/crosextra",
    "/usr/share/fonts/truetype/liberation",
    "/usr/share/fonts/truetype/dejavu",
]
FONT_FILES = {
    ("serif", "regular"): "Lora-Variable.ttf",
    ("serif", "bold"): "Lora-Variable.ttf",
    ("serif", "italic"): "Lora-Italic-Variable.ttf",
    ("sans", "light"): "Poppins-Light.ttf",
    ("sans", "regular"): "Carlito-Regular.ttf",
    ("sans", "medium"): "Poppins-Medium.ttf",
    ("sans", "bold"): "Carlito-Bold.ttf",
    ("round", "regular"): "Poppins-Regular.ttf",
    ("round", "medium"): "Poppins-Medium.ttf",
    ("round", "bold"): "Poppins-Bold.ttf",
    ("round", "light"): "Poppins-Light.ttf",
    ("mono", "regular"): "LiberationMono-Regular.ttf",
}
_CACHE = {}


def font(family="sans", weight="regular", size=16):
    key = (family, weight, size)
    if key in _CACHE:
        return _CACHE[key]
    name = FONT_FILES.get((family, weight)) or FONT_FILES[("sans", "regular")]
    for d in FONT_DIRS:
        p = os.path.join(d, name)
        if os.path.exists(p):
            f = ImageFont.truetype(p, size)
            break
    else:
        f = ImageFont.load_default()
    if family == "serif" and weight == "bold":
        try:
            f.set_variation_by_axes([700])
        except Exception:
            pass
    _CACHE[key] = f
    return f


def hexc(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def gradient(size, c1, c2, direction="diagonal"):
    """Dégradé linéaire, sans dépendance externe."""
    w, h = size
    c1, c2 = hexc(c1), hexc(c2)
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(0, w, 4):
            if direction == "vertical":
                t = y / max(h - 1, 1)
            elif direction == "horizontal":
                t = x / max(w - 1, 1)
            else:
                t = (x / max(w - 1, 1) + y / max(h - 1, 1)) / 2
            col = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
            for dx in range(4):
                if x + dx < w:
                    px[x + dx, y] = col
    return img


def rrect(draw, box, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def shadow(img, box, radius=18, blur=14, opacity=40, offset=(0, 6)):
    """Ombre douce sous une boîte, appliquée sur l'image de fond."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    b = (box[0] + offset[0], box[1] + offset[1], box[2] + offset[0], box[3] + offset[1])
    d.rounded_rectangle(b, radius=radius, fill=(0, 0, 0, opacity))
    layer = layer.filter(ImageFilter.GaussianBlur(blur))
    img.paste(Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB"), (0, 0))


def wrap(draw, text, fnt, max_width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=fnt) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def paragraph(draw, xy, text, fnt, fill, max_width, line_height=None, max_lines=None):
    x, y = xy
    lh = line_height or int(fnt.size * 1.45)
    lines = wrap(draw, text, fnt, max_width)
    if max_lines:
        lines = lines[:max_lines]
    for ln in lines:
        draw.text((x, y), ln, font=fnt, fill=fill)
        y += lh
    return y


def placeholder(size, c1, c2, motif="waves", seed=0):
    """Image de démonstration abstraite : dégradé + formes géométriques."""
    import math
    img = gradient(size, c1, c2, "diagonal")
    d = ImageDraw.Draw(img, "RGBA")
    w, h = size
    if motif == "waves":
        for i in range(5):
            off = h * (0.35 + i * 0.14) + seed * 7
            pts = [(x, off + math.sin((x / w) * 6.28 + i + seed) * h * 0.07) for x in range(0, w + 8, 8)]
            pts += [(w, h), (0, h)]
            d.polygon(pts, fill=(255, 255, 255, 16))
    elif motif == "circles":
        for i in range(6):
            r = (0.12 + 0.07 * ((i + seed) % 4)) * min(w, h)
            cx = w * ((i * 0.23 + seed * 0.11) % 1.0)
            cy = h * ((i * 0.37 + seed * 0.19) % 1.0)
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255, 18))
    elif motif == "grid":
        step = max(w, h) // 12
        for x in range(0, w, step):
            d.line([(x, 0), (x, h)], fill=(255, 255, 255, 22), width=1)
        for y in range(0, h, step):
            d.line([(0, y), (w, y)], fill=(255, 255, 255, 22), width=1)
    elif motif == "arcs":
        for i in range(4):
            r = min(w, h) * (0.5 + i * 0.22)
            cx, cy = w * 0.15, h * 1.05
            d.arc((cx - r, cy - r, cx + r, cy + r), 200, 340, fill=(255, 255, 255, 40), width=3)
    return img


# ---------------------------------------------------------------- fiche assets
BLUE, VIOLET = "#3B82F6", "#7C3AED"
LOGO = "/home/claude/brand/logo-dyonysos-wordmark.png"


def _paste_logo(img, xy, height):
    if not os.path.exists(LOGO):
        return
    logo = Image.open(LOGO).convert("RGBA")
    ratio = height / logo.height
    logo = logo.resize((int(logo.width * ratio), height), Image.LANCZOS)
    img.paste(logo, xy, logo)


def icon(path, glyph, c1=BLUE, c2=VIOLET):
    img = gradient((140, 140), c1, c2)
    d = ImageDraw.Draw(img)
    f = font("round", "bold", 62 if len(glyph) <= 2 else 44)
    d.text((70, 68), glyph, font=f, fill="#FFFFFF", anchor="mm")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)
    return path


def banner(path, title, subtitle, bullets, c1=BLUE, c2=VIOLET):
    img = gradient((1200, 630), c1, c2)
    d = ImageDraw.Draw(img, "RGBA")
    d.text((70, 90), title, font=font("round", "bold", 58), fill="#FFFFFF")
    paragraph(d, (70, 180), subtitle, font("sans", "regular", 30), (255, 255, 255, 220), 1000)
    y = 300
    for b in bullets[:5]:
        d.ellipse((72, y + 10, 84, y + 22), fill=(255, 255, 255, 230))
        d.text((104, y), b, font=font("sans", "regular", 26), fill=(255, 255, 255, 235))
        y += 52
    _paste_logo(img, (70, 520), 44)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)
    return path


def screenshot_card(path, title, rows, footer, c1=BLUE, c2=VIOLET):
    img = gradient((1200, 630), c1, c2)
    d = ImageDraw.Draw(img, "RGBA")
    shadow(img, (80, 110, 1120, 540))
    d = ImageDraw.Draw(img, "RGBA")
    rrect(d, (80, 110, 1120, 540), 18, fill="#FFFFFF")
    d.text((120, 150), title, font=font("round", "bold", 34), fill="#111827")
    y = 220
    for label, value in rows[:6]:
        d.text((120, y), label, font=font("sans", "regular", 24), fill="#4B5563")
        d.text((1080, y), value, font=font("sans", "bold", 24), fill="#111827", anchor="ra")
        d.line([(120, y + 42), (1080, y + 42)], fill="#E5E7EB", width=1)
        y += 62
    d.text((120, 500), footer, font=font("sans", "regular", 20), fill="#6B7280")
    _paste_logo(img, (940, 486), 34)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)
    return path


def make_logo(path=LOGO):
    """Wordmark DYONYSOS, dessiné en typographie — aucune image importée."""
    img = Image.new("RGBA", (520, 96), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = font("round", "bold", 54)
    d.text((96, 48), "DYONYSOS", font=f, fill="#FFFFFF", anchor="lm")
    d.ellipse((16, 20, 72, 76), outline="#FFFFFF", width=5)
    d.line([(30, 62), (58, 34)], fill="#FFFFFF", width=5)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)
    return path


if __name__ == "__main__":
    make_logo()
    print("logo →", LOGO)
