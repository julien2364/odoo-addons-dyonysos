# -*- coding: utf-8 -*-
"""Génère les fiches static/description/index.html des six thèmes."""
import os

HEAD = """<section class="oe_container">
    <div class="oe_row oe_spaced">
        <div class="oe_span12">
            <h2 class="oe_slogan" style="margin-bottom:0;">{title}</h2>
            <h3 class="oe_slogan" style="color:#6B7280;font-weight:400;margin-top:6px;">{tagline}</h3>
        </div>
        <div class="oe_span12 text-center">
            <img src="mockup_home.png" alt="Page d'accueil du thème" style="max-width:100%;"/>
        </div>
    </div>
</section>
"""

INTRO = """<section class="oe_container oe_dark">
    <div class="oe_row oe_spaced">
        <div class="oe_span12">
            <h3 class="oe_slogan">{h}</h3>
        </div>
        {cols}
    </div>
</section>
"""

SHOT = """<section class="oe_container">
    <div class="oe_row oe_spaced">
        <div class="oe_span12">
            <h3 class="oe_slogan">{h}</h3>
            <p class="oe_mt32" style="text-align:center;color:#4B5563;">{p}</p>
        </div>
        <div class="oe_span12 text-center">
            <img src="{img}" alt="{alt}" style="max-width:100%;"/>
        </div>
    </div>
</section>
"""

LIST = """<section class="oe_container {cls}">
    <div class="oe_row oe_spaced">
        <div class="oe_span12">
            <h3 class="oe_slogan">{h}</h3>
        </div>
        {cols}
    </div>
</section>
"""

TECH = """<section class="oe_container oe_dark">
    <div class="oe_row oe_spaced">
        <div class="oe_span12">
            <h3 class="oe_slogan">Ce qu'il faut savoir avant d'installer</h3>
            <ul style="max-width:760px;margin:0 auto;color:#374151;line-height:1.7;">
                {items}
            </ul>
        </div>
    </div>
</section>
"""

CONTACT = """<section class="oe_container">
    <div class="oe_row oe_spaced">
        <div class="oe_span12 text-center">
            <h3 class="oe_slogan">DYONYSOS</h3>
            <p style="color:#4B5563;line-height:1.7;">
                Édité par DYONYSOS — conseil et développement Odoo.<br/>
                Support et questions avant achat :
                <a href="mailto:welcome@dyonysos.fr">welcome@dyonysos.fr</a><br/>
                <a href="https://dyonysos.fr">https://dyonysos.fr</a>
            </p>
            <p style="color:#6B7280;font-size:13px;line-height:1.7;">
                Toutes les images de démonstration sont générées par programme (dégradés, formes
                géométriques, compositions typographiques) : aucune photographie ni illustration
                tierce n'est incluse. Les contenus de démonstration sont fictifs.
            </p>
        </div>
    </div>
</section>
"""


def cols(items, span=4):
    out = []
    for t, p in items:
        out.append(
            '<div class="oe_span%d">\n'
            '            <h4 style="margin-bottom:6px;">%s</h4>\n'
            '            <p style="color:#4B5563;line-height:1.65;">%s</p>\n'
            '        </div>' % (span, t, p))
    return "\n        ".join(out)


def li(items):
    return "\n                ".join("<li>%s</li>" % i for i in items)


COMMON_TECH = [
    "Odoo 19 Community ou Enterprise. Aucun module payant tiers n'est nécessaire.",
    "Le thème s'applique depuis <em>Site web → Configuration → Thème</em>. "
    "Les pages de démonstration sont créées à ce moment-là, pas à l'installation du module.",
    "Palette et polices sont modifiables dans l'éditeur de site : le thème fournit un point de "
    "départ, il ne verrouille rien.",
    "Contrastes texte/fond vérifiés au niveau AA de la WCAG 2.1 sur les couples fournis par défaut.",
]

MODULES = {}

# ------------------------------------------------------------------ PRESSE
MODULES["theme_presse_lite"] = dict(
    title="Thème Presse — version gratuite",
    tagline="Un système de design éditorial pour les sites Odoo qui publient beaucoup.",
    intro_h="Ce que fait la version gratuite",
    intro=[
        ("Système de design éditorial",
         "Titres en serif contrastée (Playfair Display), texte en Inter, échelle typographique "
         "marquée, filets de séparation fins et palette sobre : noir anthracite, rouge éditorial "
         "en accent, fond crème alternatif."),
        ("Gabarit d'article",
         "Chapô, intertitres, citations, légendes d'image et temps de lecture calculé "
         "automatiquement. La largeur de lecture est limitée à 68 caractères, la mesure qui rend "
         "un long article réellement lisible sur grand écran."),
        ("Blocs de page d'accueil",
         "Bloc « une », grille d'articles et bloc « à lire aussi », glissables depuis la "
         "catégorie « Presse » du panneau de blocs."),
    ],
    shots=[("mockup_article.png", "Le gabarit d'article",
            "Chapô, intertitres, citation et légende. Le temps de lecture est estimé à partir du "
            "contenu réel de l'article, sans champ supplémentaire à remplir.")],
    list_h="Intégration du blog Odoo",
    list_items=[
        ("Les vues sont habillées, pas remplacées",
         "Le thème style les vues de <em>website_blog</em> et n'ajoute qu'une seule information "
         "éditoriale : la rubrique et le temps de lecture. Vos personnalisations de blog restent en place."),
        ("Contenu de démonstration",
         "Trois rubriques et douze articles fictifs sont créés à l'installation pour que le site "
         "ressemble à quelque chose dès la première minute. Ils sont supprimables sans effet sur le thème."),
        ("Et ensuite",
         "La version pro ajoute la une multi-niveaux, le fil d'actualité, la grille par rubrique "
         "avec filtres, le dossier, l'encadré auteur, la chronologie, le bandeau newsletter, "
         "deux pages prêtes à l'emploi, le sommaire automatique et le mode lecture."),
    ],
    tech=COMMON_TECH + [
        "Dépend de <em>website</em> et <em>website_blog</em> : le module Blog doit être installé.",
        "Les douze articles de démonstration sont créés à l'installation du module (et non à "
        "l'application du thème). Sur une base de production, supprimez-les après avoir pris vos repères.",
    ],
)

MODULES["theme_presse"] = dict(
    title="Thème Presse — version pro",
    tagline="Les blocs dont un média a besoin quand il publie plusieurs articles par jour.",
    intro_h="Ce que la version pro ajoute",
    intro=[
        ("Une multi-niveaux",
         "Un article principal et quatre secondaires, avec la hiérarchie typographique qui va "
         "avec. C'est le bloc qui fait qu'une page d'accueil ressemble à un journal."),
        ("Fil d'actualité",
         "Une colonne d'entrées horodatées, à poser en page d'accueil ou sur une page dédiée "
         "au direct."),
        ("Grille par rubrique avec filtres",
         "Des boutons de rubrique filtrent la grille sans rechargement de page. Aucune "
         "configuration : la rubrique est un attribut de la carte."),
        ("Dossier ou série d'articles",
         "Une liste numérotée pour présenter une enquête en plusieurs épisodes."),
        ("Encadré auteur",
         "Le bloc de signature à placer en fin d'article ou en tête de page auteur."),
        ("Chronologie d'événement",
         "Une frise date/contenu pour reprendre le fil d'une affaire ou d'un projet."),
        ("Bandeau newsletter",
         "Un gabarit d'inscription à relier au module Newsletter d'Odoo ou à votre outil d'envoi."),
        ("Sommaire automatique",
         "Le sommaire des intertitres se construit dans le navigateur à partir des h2 et h3 "
         "réellement présents. Rien à saisir."),
        ("Mode lecture",
         "Un bouton qui élargit l'interligne, réduit la mesure et masque la colonne latérale."),
    ],
    shots=[("mockup_blocs.png", "Trois des sept blocs supplémentaires",
            "Fil d'actualité, chronologie et dossier. Tous se glissent depuis la catégorie "
            "« Presse » du panneau de blocs."),
           ("mockup_article.png", "Article avec sommaire et mode lecture",
            "Le sommaire à gauche et le bouton de mode lecture sont ajoutés aux articles du blog "
            "sans remplacer la vue d'Odoo.")],
    list_h="Deux pages prêtes à l'emploi",
    list_items=[
        ("Page rubrique", "En-tête de rubrique, grille filtrable et bandeau newsletter, "
                          "créée à l'application du thème sur <em>/rubrique-economie</em>."),
        ("Page auteur", "Encadré auteur et liste des derniers articles, sur "
                        "<em>/auteur-camille-ferrand</em>."),
        ("Palette supplémentaire", "Une troisième palette à fond crème dominant s'ajoute aux deux "
                                   "palettes de la version gratuite."),
    ],
    tech=COMMON_TECH + [
        "Dépend de <em>theme_presse_lite</em>, qui doit être installé (il est gratuit).",
        "Les filtres, le sommaire et le mode lecture sont écrits en JavaScript sans dépendance "
        "et restent inertes dans l'éditeur de site.",
    ],
)

# ------------------------------------------------------------------ VOYAGE
MODULES["theme_voyage_lite"] = dict(
    title="Thème Voyage — version gratuite",
    tagline="Chaleureux et aéré : grandes images, sable, terracotta et bleu profond.",
    intro_h="Ce que fait la version gratuite",
    intro=[
        ("Système de design",
         "Palette sable, terracotta et bleu profond, titres en Poppins, texte en Inter, cartes "
         "à coins arrondis et ombres douces. Deux palettes livrées, modifiables dans l'éditeur."),
        ("Bandeau d'accueil pleine hauteur",
         "Image de fond, dégradé de lisibilité et deux appels à l'action. Le contraste du texte "
         "sur l'image est garanti par le voile, pas par la chance."),
        ("Grille de destinations et récit",
         "Une grille de cartes destination et un bloc récit en deux colonnes texte/image, plus "
         "un bloc d'appel à l'action."),
    ],
    shots=[],
    list_h="Bon à savoir",
    list_items=[
        ("Une page de démonstration",
         "La page <em>/nos-voyages</em> est créée à l'application du thème avec les quatre blocs "
         "déjà en place, éditables directement."),
        ("Aucun module métier requis",
         "Le thème ne dépend que de <em>website</em> : il fonctionne sur une installation Odoo "
         "minimale."),
        ("Et ensuite",
         "La version pro ajoute la carte d'itinéraire par étapes, la galerie mosaïque avec "
         "lightbox, la fiche destination, les témoignages, le calendrier de départs, la demande "
         "de devis, le carnet de bord et deux pages prêtes à l'emploi."),
    ],
    tech=COMMON_TECH,
)

MODULES["theme_voyage"] = dict(
    title="Thème Voyage — version pro",
    tagline="De quoi vendre un séjour, pas seulement le décrire.",
    intro_h="Ce que la version pro ajoute",
    intro=[
        ("Carte d'itinéraire par étapes",
         "Une liste d'étapes numérotées avec distance, dénivelé et contenu libre, accompagnée "
         "d'un tracé illustratif."),
        ("Galerie mosaïque avec lightbox",
         "Une mosaïque à tuiles larges et hautes ; le clic ouvre la photo en grand, avec "
         "fermeture à l'Échap et au clic sur le fond."),
        ("Fiche destination",
         "Durée, budget, saison et difficulté en quatre cartouches, avec un indicateur de niveau "
         "sur quatre crans."),
        ("Témoignages de voyageurs",
         "Trois citations en cartes, avec avatar et contexte du séjour."),
        ("Calendrier de départs",
         "Un tableau dates / itinéraire / places / prix, avec pastilles d'état (places, dernières "
         "places, complet)."),
        ("Demande de devis",
         "Un gabarit de formulaire à relier au module Formulaires d'Odoo ou à votre outil de "
         "gestion des demandes."),
        ("Carnet de bord",
         "Une chronologie jour par jour, avec images intercalées."),
    ],
    shots=[("mockup_blocs.png", "Quatre des sept blocs supplémentaires",
            "Galerie mosaïque, fiche destination et calendrier de départs."),
           ("mockup_itineraire.png", "La page itinéraire",
            "Étapes numérotées, tracé illustratif et informations de distance et de dénivelé.")],
    list_h="Deux pages prêtes à l'emploi",
    list_items=[
        ("Page destination", "Fiche, galerie, témoignages et devis sur "
                             "<em>/destination-vantour</em>."),
        ("Page itinéraire", "Étapes, calendrier de départs et carnet de bord sur "
                            "<em>/itineraire-cretes-de-vantour</em>."),
        ("Palette supplémentaire", "Une palette sombre s'ajoute aux deux palettes de la version "
                                   "gratuite."),
    ],
    tech=COMMON_TECH + [
        "Dépend de <em>theme_voyage_lite</em>, qui doit être installé (il est gratuit).",
        "La lightbox est écrite en JavaScript sans dépendance et reste inerte dans l'éditeur de site.",
    ],
)

# -------------------------------------------------------------- ANIMALERIE
MODULES["theme_animalerie_lite"] = dict(
    title="Thème Animalerie — version gratuite",
    tagline="Une boutique en ligne rassurante : vert naturel, terracotta, coins très arrondis.",
    intro_h="Ce que fait la version gratuite",
    intro=[
        ("Système de design",
         "Palette verte naturelle et terracotta, typographie ronde et lisible (Poppins et "
         "Nunito), coins très arrondis, ombres discrètes. Deux palettes livrées."),
        ("Page d'accueil boutique",
         "Un bandeau d'accueil et trois entrées de catégorie, plus une grille de produits mise "
         "en avant."),
        ("Boutique habillée",
         "Les vues de <em>website_sale</em> sont stylées, pas remplacées : grille de produits, "
         "fiche produit, panier et tunnel de commande. La fiche produit reçoit un encart de "
         "promesse (expédition, retour, conseil)."),
    ],
    shots=[("mockup_produit.png", "La fiche produit",
            "Visuel arrondi, sélecteur de quantité et bouton d'ajout au panier retravaillés, "
            "avec l'encart de promesse sous le bloc de détails.")],
    list_h="Bon à savoir",
    list_items=[
        ("Catalogue de démonstration",
         "Douze produits et trois catégories fictifs, avec des visuels générés, sont créés à "
         "l'installation. La marque « Trèfle &amp; Museau » est inventée."),
        ("Une page de démonstration",
         "La page <em>/notre-boutique</em> est créée à l'application du thème."),
        ("Et ensuite",
         "La version pro ajoute le sélecteur par type d'animal, le comparateur, les avis notés, "
         "le guide de tailles, l'abonnement, les blocs conseils, les promotions et la page "
         "catégorie enrichie."),
    ],
    tech=COMMON_TECH + [
        "Dépend de <em>website</em> et <em>website_sale</em> : le module eCommerce doit être installé.",
        "Les douze produits de démonstration sont créés à l'installation du module. Sur une base "
        "de production, supprimez-les ou installez le thème sur une base de test d'abord.",
    ],
)

MODULES["theme_animalerie"] = dict(
    title="Thème Animalerie — version pro",
    tagline="Les blocs qui font vendre : choisir, comparer, se rassurer, revenir.",
    intro_h="Ce que la version pro ajoute",
    intro=[
        ("Sélecteur par type d'animal",
         "Trois onglets chien / chat / petits animaux qui basculent le contenu affiché sans "
         "rechargement de page."),
        ("Comparateur de produits",
         "Un tableau de caractéristiques dont on retire une colonne en décochant un produit."),
        ("Avis clients avec notes",
         "Note moyenne, répartition par étoiles et quatre avis en cartes."),
        ("Guide de tailles",
         "Un tableau de correspondance et l'encadré « comment mesurer », le duo qui fait baisser "
         "les retours."),
        ("Abonnement et livraison récurrente",
         "Trois formules en cartes, dont une mise en avant. À relier au module Abonnements "
         "d'Odoo pour la récurrence réelle."),
        ("Blocs conseils",
         "Trois cartes de conseil éditorial, pour occuper le terrain du référencement naturel."),
        ("Mise en avant de promotions",
         "Un encadré promotion avec badge, prix barré et produits associés."),
        ("Panier et tunnel stylés",
         "L'habillage complet du panier et des étapes de commande, en cohérence avec le reste "
         "de la boutique."),
        ("Page catégorie enrichie",
         "Un en-tête de catégorie avec arguments de réassurance, suivi des blocs de conversion."),
    ],
    shots=[("mockup_blocs.png", "Quatre des sept blocs supplémentaires",
            "Sélecteur par animal, comparateur, avis notés et formules d'abonnement."),
           ("mockup_produit.png", "La fiche produit",
            "Héritée de la version gratuite, avec l'encart de promesse et les arrondis du thème.")],
    list_h="Bon à savoir",
    list_items=[
        ("Page de démonstration",
         "La page <em>/categorie-chiens</em> réunit l'en-tête enrichi et sept blocs, créée à "
         "l'application du thème."),
        ("Marque fictive",
         "« Trèfle &amp; Museau » est une marque inventée pour la démonstration : elle ne "
         "correspond à aucune entreprise réelle."),
        ("Palette supplémentaire",
         "Une palette sombre s'ajoute aux deux palettes de la version gratuite."),
    ],
    tech=COMMON_TECH + [
        "Dépend de <em>theme_animalerie_lite</em>, qui doit être installé (il est gratuit).",
        "Le sélecteur et le comparateur sont écrits en JavaScript sans dépendance et restent "
        "inertes dans l'éditeur de site.",
    ],
)


def render(mod, cfg):
    span = 4 if len(cfg["intro"]) % 3 == 0 else 6
    parts = [HEAD.format(title=cfg["title"], tagline=cfg["tagline"]),
             INTRO.format(h=cfg["intro_h"], cols=cols(cfg["intro"], span))]
    shots = list(cfg["shots"]) + [("mockup_design.png", "Le système de design",
        "Palette, échelle typographique et composants. Les ratios de contraste indiqués sont "
        "ceux mesurés sur les couples de couleurs livrés par défaut.")]
    for img, h, p in [(x[0], x[1], x[2]) for x in shots]:
        parts.append(SHOT.format(h=h, p=p, img=img, alt=h))
    parts.append(LIST.format(cls="",
                             h=cfg["list_h"], cols=cols(cfg["list_items"], 4)))
    parts.append(TECH.format(items=li(cfg["tech"])))
    parts.append(CONTACT)
    out = os.path.join("/home/claude/addons-dyonysos", mod, "static/description/index.html")
    open(out, "w", encoding="utf-8").write("\n".join(parts))
    return out


if __name__ == "__main__":
    for mod, cfg in MODULES.items():
        print("écrit", render(mod, cfg))
