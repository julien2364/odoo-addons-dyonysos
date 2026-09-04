# -*- coding: utf-8 -*-
"""Maquettes de fiche pour les six thèmes.

Chaque maquette est une reconstitution de la page, dessinée avec PIL aux vraies
couleurs et dans les vraies familles typographiques du thème. Aucune image n'est
téléchargée : tout est tracé (dégradés, formes, texte).
"""
import os, sys, math
sys.path.insert(0, "/home/claude")
from make_assets import font, placeholder, hexc
from PIL import Image, ImageDraw

W, H = 1200, 630


def new(bg):
    img = Image.new("RGB", (W, H), bg)
    return img, ImageDraw.Draw(img, "RGBA")


def rr(d, box, r, **kw):
    d.rounded_rectangle(box, radius=r, **kw)


def txt(d, xy, s, f, fill, anchor=None):
    d.text(xy, s, font=f, fill=fill, anchor=anchor)


def lines(d, x, y, widths, h, color, gap):
    for w in widths:
        rr(d, (x, y, x + w, y + h), h // 2, fill=color)
        y += gap
    return y


def paw(d, cx, cy, r, fill):
    d.ellipse((cx - r, cy - r * .85, cx + r, cy + r * .95), fill=fill)
    for a in (-58, -20, 20, 58):
        rad = math.radians(a - 90)
        px, py = cx + math.cos(rad) * r * 1.45, cy + math.sin(rad) * r * 1.45
        rr2 = r * .42
        d.ellipse((px - rr2, py - rr2, px + rr2, py + rr2), fill=fill)


def photo(box, c1, c2, motif, seed, relief=False):
    w = int(box[2] - box[0]); h = int(box[3] - box[1])
    img = placeholder((max(w, 2), max(h, 2)), c1, c2, motif=motif, seed=seed)
    if relief:
        d = ImageDraw.Draw(img, "RGBA")
        for k, a in ((0, 60), (1, 45), (2, 32)):
            y0 = h * (0.55 + k * 0.13)
            pts = [(0, h), (0, y0 + h * .1)]
            for j in range(7):
                pts.append((w * j / 6, y0 + ((-1) ** (j + k)) * h * .07))
            pts += [(w, y0 + h * .1), (w, h)]
            d.polygon(pts, fill=(255, 255, 255, a))
    return img


# ============================================================ THÈME PRESSE
INK, RED, CREAM, GREY = "#1F2933", "#B3121D", "#FBF8F3", "#7A828B"


def presse_home(path):
    img, d = new("#FFFFFF")
    # bandeau supérieur
    d.rectangle((0, 0, W, 78), fill=INK)
    txt(d, (48, 39), "LE FIL DES RIVES", font("serif", "bold", 30), "#FFFFFF", "lm")
    x = 470
    for it in ("ACTUALITÉS", "ÉCONOMIE", "CULTURE", "TERRITOIRES", "ENQUÊTES"):
        txt(d, (x, 40), it, font("sans", "bold", 15), "#D7DBDF", "lm")
        x += d.textlength(it, font=font("sans", "bold", 15)) + 34
    rr(d, (1064, 26, 1152, 52), 3, fill=RED)
    txt(d, (1108, 39), "S'ABONNER", font("sans", "bold", 13), "#FFFFFF", "mm")

    # rubrique + filet
    txt(d, (48, 104), "À LA UNE", font("sans", "bold", 15), INK)
    d.line([(148, 112), (1152, 112)], fill="#D8DCE0", width=1)

    # une
    img.paste(photo((48, 136, 748, 424), "#2A3540", "#0F1418", "grid", 1), (48, 136))
    d.rectangle((48, 416, 748, 424), fill=RED)
    txt(d, (48, 448), "ÉCONOMIE", font("sans", "bold", 14), RED)
    txt(d, (48, 472), "Les ateliers de la vallée", font("serif", "bold", 40), INK)
    txt(d, (48, 518), "misent sur la réparation", font("serif", "bold", 40), INK)
    txt(d, (48, 578), "Par Camille Ferrand · 12 mars · 6 min de lecture",
        font("sans", "regular", 16), GREY)

    # colonne latérale
    y = 136
    for kicker, t1, t2 in (("CULTURE", "Le festival des Rives", "ouvre sa billetterie"),
                           ("TERRITOIRES", "Ligne 7 : le tracé", "définitif enfin arrêté"),
                           ("SCIENCES", "Un capteur pour suivre", "la nappe phréatique")):
        txt(d, (788, y), kicker, font("sans", "bold", 13), RED)
        txt(d, (788, y + 22), t1, font("serif", "bold", 23), INK)
        txt(d, (788, y + 50), t2, font("serif", "bold", 23), INK)
        txt(d, (788, y + 84), "4 min de lecture", font("sans", "regular", 14), GREY)
        y += 116
        if y < 470:
            d.line([(788, y - 22), (1152, y - 22)], fill="#E2E6EA", width=1)
    d.line([(768, 136), (768, 470)], fill="#E2E6EA", width=1)
    img.save(path)


def presse_article(path):
    img, d = new(CREAM)
    d.rectangle((0, 0, W, 66), fill=INK)
    txt(d, (48, 33), "LE FIL DES RIVES", font("serif", "bold", 24), "#FFFFFF", "lm")
    left = 300
    txt(d, (left, 104), "ENQUÊTE", font("sans", "bold", 15), RED)
    txt(d, (left, 132), "Ce que l'atelier partagé a", font("serif", "bold", 46), INK)
    txt(d, (left, 186), "changé dans le quartier", font("serif", "bold", 46), INK)
    txt(d, (left, 248), "Par Camille Ferrand · 8 min de lecture", font("sans", "regular", 16), GREY)
    d.line([(left, 284), (900, 284)], fill="#C9CDD2", width=2)
    txt(d, (left, 306), "Ouvert il y a dix-huit mois dans une ancienne", font("sans", "regular", 21), "#39424D")
    txt(d, (left, 336), "halle, l'atelier accueille aujourd'hui près de", font("sans", "regular", 21), "#39424D")
    txt(d, (left, 366), "deux cents visiteurs par semaine.", font("sans", "regular", 21), "#39424D")
    lines(d, left, 412, [600, 600, 560, 600, 470], 7, "#B9BFC5", 22)
    # citation
    d.rectangle((left, 534, left + 4, 604), fill=RED)
    txt(d, (left + 22, 540), "« En un an, nous avons évité que", font("serif", "italic", 25), INK)
    txt(d, (left + 22, 574), "trois tonnes partent en déchetterie. »", font("serif", "italic", 25), INK)
    # sommaire à gauche
    d.rectangle((48, 104, 52, 300), fill="#D8DCE0")
    txt(d, (68, 104), "DANS CET ARTICLE", font("sans", "bold", 13), GREY)
    lines(d, 68, 136, [180, 150, 168, 130], 7, "#B9BFC5", 26)
    txt(d, (68, 258), "MODE LECTURE", font("sans", "bold", 13), INK)
    rr(d, (64, 252, 200, 282), 3, outline="#C9CDD2", width=2)
    img.save(path)


def presse_blocs(path):
    img, d = new("#FFFFFF")
    txt(d, (48, 44), "LES BLOCS DE LA VERSION PRO", font("sans", "bold", 17), RED)
    txt(d, (48, 72), "Sept blocs éditoriaux prêts à glisser", font("serif", "bold", 38), INK)
    # fil
    rr(d, (48, 150, 380, 582), 4, fill=CREAM)
    txt(d, (72, 174), "LE FIL", font("sans", "bold", 14), RED)
    for i in range(6):
        y = 212 + i * 60
        d.ellipse((72, y, 86, y + 14), fill=RED)
        txt(d, (104, y - 4), "11 h 4%d" % i, font("sans", "bold", 13), RED)
        lines(d, 104, y + 18, [230, 180], 7, "#B9BFC5", 16)
    d.line([(79, 226), (79, 548)], fill="#D8DCE0", width=2)
    # chronologie
    rr(d, (404, 150, 776, 582), 4, fill=CREAM)
    txt(d, (428, 174), "CHRONOLOGIE", font("sans", "bold", 14), RED)
    for i in range(4):
        y = 216 + i * 90
        d.line([(428, y - 12), (752, y - 12)], fill="#D8DCE0", width=1)
        txt(d, (428, y), ("MARS", "SEPT.", "FÉVR.", "JANV.")[i] + " 202%d" % (4 + i),
            font("sans", "bold", 13), RED)
        lines(d, 428, y + 24, [300, 240], 7, "#B9BFC5", 16)
    # dossier
    rr(d, (800, 150, 1152, 582), 4, fill=CREAM)
    txt(d, (824, 174), "DOSSIER", font("sans", "bold", 14), RED)
    txt(d, (824, 196), "Réparer plutôt", font("serif", "bold", 26), INK)
    txt(d, (824, 228), "que remplacer", font("serif", "bold", 26), INK)
    for i in range(4):
        y = 296 + i * 68
        d.line([(824, y - 14), (1128, y - 14)], fill="#D8DCE0", width=1)
        txt(d, (824, y), "0%d" % (i + 1), font("serif", "bold", 28), RED)
        lines(d, 876, y + 6, [230, 180], 7, "#B9BFC5", 16)
    img.save(path)


# ============================================================ THÈME VOYAGE
VBLUE, VTERRA, VSAND, VINK = "#123A5E", "#A8452A", "#FAF3E8", "#0E2439"


def voyage_home(path):
    img, d = new(VSAND)
    hero = photo((0, 0, W, 400), "#1B4E77", "#0C2438", "arcs", 0, relief=True)
    img.paste(hero, (0, 0))
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle((0, 0, W, 400), fill=(14, 36, 57, 120))
    txt(d, (48, 40), "SENTIERS LENTS", font("round", "bold", 26), "#FFFFFF", "lm")
    x = 480
    for it in ("Itinéraires", "Destinations", "Carnet", "Départs"):
        txt(d, (x, 40), it, font("round", "medium", 17), "#E7EEF4", "lm")
        x += d.textlength(it, font=font("round", "medium", 17)) + 30
    rr(d, (1014, 22, 1152, 58), 18, fill=VTERRA)
    txt(d, (1083, 40), "Demander un devis", font("round", "medium", 14), "#FFFFFF", "mm")

    txt(d, (48, 150), "ITINÉRAIRES ACCOMPAGNÉS", font("round", "bold", 16), "#F3C6B4")
    txt(d, (48, 182), "Prenez le temps long,", font("round", "bold", 50), "#FFFFFF")
    txt(d, (48, 240), "du col de Vantour aux rives", font("round", "bold", 50), "#FFFFFF")
    txt(d, (48, 312), "Douze itinéraires à pied, en train et à vélo, de quatre à seize jours.",
        font("sans", "regular", 20), "#DCE7EF")

    # cartes
    for i in range(3):
        x0 = 48 + i * 372
        rr(d, (x0, 424, x0 + 336, 598), 22, fill="#FFFFFF")
        card = photo((0, 0, 336, 96), *(("#2E6E7E", "#12303B"), ("#D08A4E", "#8A4A22"),
                                        ("#3F6B4E", "#173225"))[i], motif="waves", seed=i + 2, relief=True)
        mask = Image.new("L", (336, 96), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, 336, 120), radius=22, fill=255)
        img.paste(card, (x0, 424), mask)
        d = ImageDraw.Draw(img, "RGBA")
        rr(d, (x0 + 20, 534, x0 + 96, 560), 13, fill="#F1DFD7")
        txt(d, (x0 + 58, 547), ("7 jours", "5 jours", "4 jours")[i], font("round", "medium", 13), "#8C3822", "mm")
        txt(d, (x0 + 20, 566), ("Les crêtes de Vantour", "La boucle des marais",
                                "Le littoral des cabanes")[i], font("round", "bold", 18), VINK)
    img.save(path)


def voyage_itineraire(path):
    img, d = new("#FFFFFF")
    d.rectangle((0, 0, W, 70), fill=VBLUE)
    txt(d, (48, 35), "SENTIERS LENTS", font("round", "bold", 22), "#FFFFFF", "lm")
    txt(d, (48, 106), "ITINÉRAIRE", font("round", "bold", 15), VTERRA)
    txt(d, (48, 132), "Les crêtes de Vantour,", font("round", "bold", 36), VINK)
    txt(d, (48, 178), "jour après jour", font("round", "bold", 36), VINK)
    carte = photo((0, 0, 440, 300), "#EAF1F6", "#CFDEE9", "grid", 1)
    dm = ImageDraw.Draw(carte, "RGBA")
    pts = [(50, 260), (110, 200), (170, 220), (230, 140), (300, 160), (370, 70)]
    dm.line(pts, fill=VTERRA, width=7, joint="curve")
    for (px, py) in pts:
        dm.ellipse((px - 11, py - 11, px + 11, py + 11), fill="#FFFFFF", outline=VBLUE, width=4)
    mask = Image.new("L", (440, 300), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, 440, 300), radius=22, fill=255)
    img.paste(carte, (48, 250), mask)
    d = ImageDraw.Draw(img, "RGBA")
    d.line([(576, 120), (576, 590)], fill="#D6E0E8", width=3)
    for i in range(5):
        y = 120 + i * 96
        d.ellipse((558, y, 594, y + 36), fill=VTERRA)
        txt(d, (576, y + 18), str(i + 1), font("round", "bold", 18), "#FFFFFF", "mm")
        txt(d, (628, y), "JOUR %d · %d KM · +%d M" % (i + 1, 11 + i * 2, 540 + i * 70),
            font("round", "medium", 13), VTERRA)
        txt(d, (628, y + 22), ("De la gare au hameau des Granges", "La traversée du plateau",
                               "Journée libre au refuge du Col", "Les balcons de la vallée",
                               "Vers le versant nord")[i], font("round", "bold", 21), VINK)
        lines(d, 628, y + 54, [430, 330], 7, "#C3CFD9", 16)
    img.save(path)


def voyage_blocs(path):
    img, d = new(VSAND)
    txt(d, (48, 44), "LES BLOCS DE LA VERSION PRO", font("round", "bold", 16), VTERRA)
    txt(d, (48, 72), "Sept blocs pour vendre un séjour", font("round", "bold", 36), VINK)
    # mosaïque
    rr(d, (48, 150, 560, 582), 22, fill="#FFFFFF")
    txt(d, (72, 174), "GALERIE MOSAÏQUE", font("round", "bold", 14), VTERRA)
    tiles = [(72, 208, 300, 380), (312, 208, 424, 292), (436, 208, 536, 292),
             (312, 304, 424, 380), (436, 304, 536, 380), (72, 392, 300, 558),
             (312, 392, 536, 558)]
    for i, t in enumerate(tiles):
        ph = photo(t, *(("#1B4E77", "#0C2438"), ("#2E6E7E", "#12303B"), ("#D08A4E", "#8A4A22"),
                        ("#3F6B4E", "#173225"), ("#4A5D82", "#1E2A44"), ("#C2603A", "#7E2F1B"),
                        ("#1B4E77", "#0C2438"))[i], motif="waves", seed=i, relief=True)
        m = Image.new("L", ph.size, 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, ph.size[0], ph.size[1]), radius=14, fill=255)
        img.paste(ph, (int(t[0]), int(t[1])), m)
    d = ImageDraw.Draw(img, "RGBA")
    # fiche + départs
    rr(d, (584, 150, 1152, 360), 22, fill="#FFFFFF")
    txt(d, (608, 174), "FICHE DESTINATION", font("round", "bold", 14), VTERRA)
    for i, (lab, val) in enumerate((("DURÉE", "7 jours"), ("BUDGET", "890 €"),
                                    ("SAISON", "Mai–oct."), ("DIFFICULTÉ", "Soutenue"))):
        x0 = 608 + i * 134
        rr(d, (x0, 206, x0 + 120, 320), 16, fill=VSAND)
        txt(d, (x0 + 14, 224), lab, font("round", "medium", 11), "#7C8A96")
        txt(d, (x0 + 14, 248), val, font("round", "bold", 17), VINK)
    rr(d, (584, 384, 1152, 582), 22, fill="#FFFFFF")
    txt(d, (608, 406), "CALENDRIER DE DÉPARTS", font("round", "bold", 14), VTERRA)
    for i in range(4):
        y = 440 + i * 36
        rr(d, (608, y, 1128, y + 28), 14, fill=VSAND)
        txt(d, (624, y + 14), ("18 – 24 mai", "8 – 12 juin", "6 – 21 juillet", "14 – 19 sept.")[i],
            font("round", "medium", 13), VINK, "lm")
        col = ("#2F6B3C", VTERRA, VBLUE, "#2F6B3C")[i]
        rr(d, (900, y + 5, 990, y + 23), 9, fill=col)
        txt(d, (945, y + 14), ("7 places", "2 places", "Complet", "9 places")[i],
            font("round", "medium", 11), "#FFFFFF", "mm")
        txt(d, (1112, y + 14), ("890 €", "640 €", "1 480 €", "760 €")[i],
            font("round", "bold", 13), VINK, "rm")
    img.save(path)


# ========================================================= THÈME ANIMALERIE
AGREEN, ATERRA, AIVORY, AINK = "#2F6B3C", "#A9502F", "#FBF7F0", "#22301F"


def anim_home(path):
    img, d = new(AIVORY)
    d.rectangle((0, 0, W, 76), fill="#FFFFFF")
    d.line([(0, 76), (W, 76)], fill="#E6DFD4", width=1)
    d.ellipse((44, 22, 76, 54), fill=AGREEN)
    paw(d, 60, 38, 8, (255, 255, 255, 230))
    txt(d, (88, 38), "Trèfle & Museau", font("round", "bold", 23), AINK, "lm")
    x = 470
    for it in ("Chiens", "Chats", "Petits animaux", "Conseils"):
        txt(d, (x, 38), it, font("round", "medium", 16), "#5A6857", "lm")
        x += d.textlength(it, font=font("round", "medium", 16)) + 30
    rr(d, (1042, 22, 1152, 54), 16, fill=AGREEN)
    txt(d, (1097, 38), "Panier · 2", font("round", "medium", 14), "#FFFFFF", "mm")

    rr(d, (48, 104, 1152, 396), 26, fill="#FFFFFF")
    ph = photo((0, 0, 520, 292), "#3E8A4E", "#1E4527", "circles", 0)
    dp = ImageDraw.Draw(ph, "RGBA")
    paw(dp, 340, 110, 62, (255, 255, 255, 80))
    paw(dp, 430, 200, 40, (255, 255, 255, 60))
    m = Image.new("L", (520, 292), 0)
    ImageDraw.Draw(m).rounded_rectangle((-40, 0, 520, 292), radius=26, fill=255)
    img.paste(ph, (632, 104), m)
    d = ImageDraw.Draw(img, "RGBA")
    txt(d, (88, 148), "TRÈFLE & MUSEAU", font("round", "bold", 15), AGREEN)
    txt(d, (88, 178), "De quoi bien nourrir,", font("round", "bold", 40), AINK)
    txt(d, (88, 226), "bien coucher et bien", font("round", "bold", 40), AINK)
    txt(d, (88, 274), "occuper vos animaux", font("round", "bold", 40), AINK)
    rr(d, (88, 336, 260, 376), 20, fill=AGREEN)
    txt(d, (174, 356), "Voir la boutique", font("round", "medium", 15), "#FFFFFF", "mm")
    rr(d, (276, 336, 424, 376), 20, outline=AGREEN, width=2)
    txt(d, (350, 356), "Nos conseils", font("round", "medium", 15), AGREEN, "mm")

    for i in range(4):
        x0 = 48 + i * 282
        rr(d, (x0, 424, x0 + 258, 596), 24, fill="#FFFFFF")
        ph = photo((0, 0, 258, 100), *(("#4E8C7A", "#22453C"), ("#C2703F", "#7E3F1F"),
                                       ("#8C9E4B", "#455028"), ("#B0663F", "#5E3320"))[i],
                   motif="circles", seed=i + 1)
        dp = ImageDraw.Draw(ph, "RGBA")
        paw(dp, 129, 52, 26, (255, 255, 255, 200))
        m = Image.new("L", (258, 100), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, 258, 130), radius=24, fill=255)
        img.paste(ph, (x0, 424), m)
        d = ImageDraw.Draw(img, "RGBA")
        rr(d, (x0 + 16, 532, x0 + 90, 554), 11, fill="#E1EDE2")
        txt(d, (x0 + 53, 543), ("Chiens", "Chats", "Rongeurs", "Promo")[i],
            font("round", "medium", 12), "#24552F", "mm")
        txt(d, (x0 + 16, 558), ("Gamelle en grès", "Griffoir sisal",
                                "Cage rongeur", "Croquettes 8 kg")[i],
            font("round", "medium", 14), "#3B4739")
        txt(d, (x0 + 16, 576), ("24,90 €", "36,00 €", "74,00 €", "42,00 €")[i],
            font("round", "bold", 18), AINK)
    img.save(path)


def anim_produit(path):
    img, d = new("#FFFFFF")
    d.rectangle((0, 0, W, 70), fill="#FFFFFF")
    d.line([(0, 70), (W, 70)], fill="#E6DFD4", width=1)
    d.ellipse((44, 20, 72, 48), fill=AGREEN)
    txt(d, (84, 35), "Trèfle & Museau", font("round", "bold", 21), AINK, "lm")
    ph = photo((0, 0, 480, 440), "#4E8C7A", "#22453C", "circles", 2)
    dp = ImageDraw.Draw(ph, "RGBA")
    dp.rounded_rectangle((120, 180, 360, 380), radius=50, fill=(255, 255, 255, 210))
    dp.ellipse((150, 200, 330, 300), fill=(0, 0, 0, 40))
    m = Image.new("L", (480, 440), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, 480, 440), radius=24, fill=255)
    img.paste(ph, (48, 116), m)
    d = ImageDraw.Draw(img, "RGBA")
    txt(d, (576, 124), "CHIENS", font("round", "bold", 14), AGREEN)
    txt(d, (576, 150), "Panier matelassé lavable", font("round", "bold", 34), AINK)
    txt(d, (576, 202), "59,00 €", font("round", "bold", 34), AGREEN)
    lines(d, 576, 258, [520, 480, 400], 7, "#C7CEC4", 22)
    rr(d, (576, 340, 700, 384), 22, outline="#D5DBD2", width=2)
    txt(d, (638, 362), "–   1   +", font("round", "medium", 16), AINK, "mm")
    rr(d, (716, 340, 940, 384), 22, fill=AGREEN)
    txt(d, (828, 362), "Ajouter au panier", font("round", "medium", 16), "#FFFFFF", "mm")
    rr(d, (576, 410, 1152, 566), 24, fill=AIVORY)
    for i, s in enumerate(("Expédié sous 24 h ouvrées depuis notre entrepôt",
                           "Retour accepté 30 jours, emballage ouvert compris",
                           "Un conseil avant d'acheter ? Écrivez-nous, on répond")):
        txt(d, (604, 438 + i * 40), "✓", font("round", "bold", 18), AGREEN)
        txt(d, (634, 438 + i * 40), s, font("sans", "regular", 18), "#3B4739")
    img.save(path)


def anim_blocs(path):
    img, d = new(AIVORY)
    txt(d, (48, 44), "LES BLOCS DE LA VERSION PRO", font("round", "bold", 16), AGREEN)
    txt(d, (48, 72), "Sept blocs e-commerce prêts à l'emploi", font("round", "bold", 34), AINK)
    # sélecteur
    rr(d, (48, 146, 560, 360), 24, fill="#FFFFFF")
    txt(d, (72, 168), "SÉLECTEUR PAR ANIMAL", font("round", "bold", 14), AGREEN)
    for i, lab in enumerate(("Chien", "Chat", "Petits animaux")):
        x0 = 72 + i * 152
        rr(d, (x0, 200, x0 + 140, 240), 20, fill="#E1EDE2" if i == 0 else "#FFFFFF",
           outline=AGREEN if i == 0 else "#DDE4DA", width=2)
        d.ellipse((x0 + 8, 206, x0 + 36, 234), fill=("#3E8A4E", "#C2703F", "#8C9E4B")[i])
        txt(d, (x0 + 46, 220), lab, font("round", "medium", 13), AINK, "lm")
    for i in range(3):
        x0 = 72 + i * 152
        rr(d, (x0, 258, x0 + 140, 336), 16, fill=AIVORY)
    # comparateur
    rr(d, (584, 146, 1152, 360), 24, fill="#FFFFFF")
    txt(d, (608, 168), "COMPARATEUR", font("round", "bold", 14), AGREEN)
    rr(d, (608, 196, 1128, 226), 12, fill="#E9F0E9")
    for r in range(4):
        for c in range(4):
            rr(d, (620 + c * 130, 240 + r * 26, 620 + c * 130 + (90 if c == 0 else 66),
                   248 + r * 26), 4, fill=AINK if c == 0 else "#9BA697")
    # avis
    rr(d, (48, 384, 560, 582), 24, fill="#FFFFFF")
    txt(d, (72, 406), "AVIS CLIENTS", font("round", "bold", 14), AGREEN)
    txt(d, (72, 430), "4,6", font("round", "bold", 44), AINK)
    txt(d, (150, 448), "★★★★★", font("sans", "bold", 22), "#C98A2E")
    for i in range(4):
        y = 500 + i * 20
        rr(d, (72, y, 96, y + 8), 4, fill="#9BA697")
        rr(d, (108, y, 470, y + 8), 4, fill="#E3E9E1")
        rr(d, (108, y, 108 + (330 - i * 90), y + 8), 4, fill=AGREEN)
    # abonnement
    rr(d, (584, 384, 1152, 582), 24, fill="#FFFFFF")
    txt(d, (608, 406), "ABONNEMENT", font("round", "bold", 14), AGREEN)
    for i in range(3):
        x0 = 608 + i * 178
        rr(d, (x0, 434, x0 + 160, 558), 18, fill=AIVORY,
           outline=AGREEN if i == 1 else None, width=3)
        txt(d, (x0 + 16, 450), ("2 mois", "1 mois", "2 semaines")[i], font("round", "medium", 14), AINK)
        txt(d, (x0 + 16, 472), ("-5 %", "-10 %", "-12 %")[i], font("round", "bold", 26), AGREEN)
        rr(d, (x0 + 16, 518, x0 + 144, 544), 13, fill=AGREEN if i == 1 else "#DDE7DC")
    img.save(path)


# ================================================== SYSTÈME DE DESIGN (commun)
def design_system(path, cfg):
    """Planche du système de design : palette, échelle typographique, boutons."""
    img, d = new(cfg["bg"])
    hf, bf = cfg["hfam"], cfg["bfam"]
    txt(d, (48, 42), cfg["eyebrow"], font(hf, "bold", 16), cfg["accent"])
    txt(d, (48, 68), "Le système de design du thème", font(hf, "bold", 34), cfg["ink"])

    # palette
    txt(d, (48, 142), "PALETTE", font(bf, "bold", 13), cfg["muted"])
    for i, (name, col, on) in enumerate(cfg["swatches"]):
        x0 = 48 + i * 148
        r, g, b = hexc(col)
        light = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255 > 0.82
        rr(d, (x0, 168, x0 + 132, 268), cfg["radius"], fill=col,
           outline="#CFC8BC" if light else None, width=1)
        txt(d, (x0 + 14, 236), col.upper(), font(bf, "bold", 13), on)
        txt(d, (x0, 280), name, font(bf, "regular", 14), cfg["ink"])
        txt(d, (x0, 300), cfg["ratios"][i], font(bf, "regular", 12), cfg["muted"])

    # typographie
    txt(d, (48, 348), "TYPOGRAPHIE", font(bf, "bold", 13), cfg["muted"])
    txt(d, (48, 372), cfg["h1"], font(hf, "bold", 46), cfg["ink"])
    txt(d, (48, 432), cfg["h2"], font(hf, "bold", 30), cfg["ink"])
    txt(d, (48, 476), cfg["body"], font(bf, "regular", 19), cfg["muted"])
    txt(d, (48, 506), cfg["body2"], font(bf, "regular", 19), cfg["muted"])
    txt(d, (48, 548), cfg["fonts"], font(bf, "bold", 14), cfg["accent"])

    # boutons et composants
    txt(d, (760, 348), "COMPOSANTS", font(bf, "bold", 13), cfg["muted"])
    rr(d, (760, 372, 940, 416), cfg["btn_radius"], fill=cfg["accent"])
    txt(d, (850, 394), "Bouton principal", font(hf, "medium", 15), "#FFFFFF", "mm")
    rr(d, (956, 372, 1136, 416), cfg["btn_radius"], outline=cfg["accent"], width=2)
    txt(d, (1046, 394), "Bouton secondaire", font(hf, "medium", 15), cfg["accent"], "mm")
    rr(d, (760, 434, 1136, 520), cfg["radius"], fill=cfg["card"], outline="#E3DED4", width=1)
    txt(d, (782, 454), cfg["card_kicker"], font(bf, "bold", 12), cfg["accent"])
    txt(d, (782, 474), cfg["card_title"], font(hf, "bold", 20), cfg["ink"])
    lines(d, 782, 504, [300, 240], 6, cfg["rule"], 14)
    rr(d, (760, 540, 1136, 590), cfg["radius"], fill=cfg["card"], outline="#E3DED4", width=1)
    txt(d, (782, 556), cfg["note"], font(bf, "regular", 14), cfg["muted"])
    img.save(path)


DS = {
  "presse": dict(
    bg="#FFFFFF", ink=INK, muted=GREY, accent=RED, card=CREAM, rule="#C9CDD2",
    hfam="serif", bfam="sans", radius=3, btn_radius=3,
    eyebrow="THÈME PRESSE",
    swatches=[("Rouge éditorial", RED, "#FFFFFF"), ("Anthracite", INK, "#FFFFFF"),
              ("Crème", CREAM, INK), ("Blanc", "#FFFFFF", INK), ("Noir", "#111417", "#FFFFFF")],
    ratios=["6,95:1 sur blanc", "14,8:1 sur blanc", "fond alterné", "fond principal", "pied de page"],
    h1="Titres en Playfair Display",
    h2="Intertitres à échelle marquée",
    body="Texte courant en Inter, interligne 1,65, mesure limitée",
    body2="à 68 caractères sur les articles.",
    fonts="Playfair Display · Inter",
    card_kicker="ÉCONOMIE", card_title="Carte d'article", 
    note="Angles quasi droits (2 px), filets fins, aucun effet d'ombre."),
  "voyage": dict(
    bg=VSAND, ink=VINK, muted="#7C8A96", accent=VTERRA, card="#FFFFFF", rule="#C3CFD9",
    hfam="round", bfam="sans", radius=20, btn_radius=22,
    eyebrow="THÈME VOYAGE",
    swatches=[("Terracotta", VTERRA, "#FFFFFF"), ("Bleu profond", VBLUE, "#FFFFFF"),
              ("Sable", VSAND, VINK), ("Blanc", "#FFFFFF", VINK), ("Encre", "#0E2439", "#FFFFFF")],
    ratios=["5,92:1 sur blanc", "11,7:1 sur blanc", "fond alterné", "cartes", "pied de page"],
    h1="Titres en Poppins",
    h2="Sous-titres généreux",
    body="Texte courant en Inter, interligne 1,7, pour des pages",
    body2="qui respirent autour de grandes images.",
    fonts="Poppins · Inter",
    card_kicker="7 JOURS", card_title="Carte destination",
    note="Coins arrondis 1,25 rem, ombres douces, boutons en pilule."),
  "animalerie": dict(
    bg=AIVORY, ink=AINK, muted="#7C8A76", accent=AGREEN, card="#FFFFFF", rule="#C7CEC4",
    hfam="round", bfam="sans", radius=22, btn_radius=22,
    eyebrow="THÈME ANIMALERIE",
    swatches=[("Vert naturel", AGREEN, "#FFFFFF"), ("Terracotta", ATERRA, "#FFFFFF"),
              ("Ivoire", AIVORY, AINK), ("Blanc", "#FFFFFF", AINK), ("Encre", AINK, "#FFFFFF")],
    ratios=["6,38:1 sur blanc", "5,42:1 sur blanc", "fond alterné", "cartes", "pied de page"],
    h1="Titres en Poppins",
    h2="Sous-titres lisibles",
    body="Texte courant en Nunito, interligne 1,7, arrondi partout",
    body2="pour une lecture rassurante.",
    fonts="Poppins · Nunito",
    card_kicker="CHIENS", card_title="Carte produit",
    note="Coins arrondis 1,5 rem, boutons en pilule, ombres discrètes."),
}


BUILD = {
    "theme_presse_lite": [("home", presse_home), ("article", presse_article),
                          ("design", lambda p: design_system(p, DS["presse"]))],
    "theme_presse": [("home", presse_home), ("article", presse_article), ("blocs", presse_blocs),
                     ("design", lambda p: design_system(p, DS["presse"]))],
    "theme_voyage_lite": [("home", voyage_home), ("itineraire", voyage_itineraire),
                          ("design", lambda p: design_system(p, DS["voyage"]))],
    "theme_voyage": [("home", voyage_home), ("itineraire", voyage_itineraire), ("blocs", voyage_blocs),
                     ("design", lambda p: design_system(p, DS["voyage"]))],
    "theme_animalerie_lite": [("home", anim_home), ("produit", anim_produit),
                              ("design", lambda p: design_system(p, DS["animalerie"]))],
    "theme_animalerie": [("home", anim_home), ("produit", anim_produit), ("blocs", anim_blocs),
                         ("design", lambda p: design_system(p, DS["animalerie"]))],
}

if __name__ == "__main__":
    root = "/home/claude/addons-dyonysos"
    for mod, jobs in BUILD.items():
        desc = os.path.join(root, mod, "static/description")
        os.makedirs(desc, exist_ok=True)
        for name, fn in jobs:
            fn(os.path.join(desc, "mockup_%s.png" % name))
        # la maquette d'accueil sert de capture principale de la fiche
        Image.open(os.path.join(desc, "mockup_home.png")).save(
            os.path.join(root, mod, "images/main_screenshot.png"))
        print(mod, "→", len(jobs), "maquettes")
