# -*- coding: utf-8 -*-
{
    "name": "DYONYSOS Pro — Thème agence & services B2B (édition complète)",
    "summary": "Extension professionnelle du thème DYONYSOS : 7 blocs de plus, 4 pages de plus, "
               "variantes d'en-tête et de pied de page, mode sombre",
    "description": """
DYONYSOS Pro
============

L'édition complète du thème DYONYSOS pour les agences, cabinets de conseil et
sociétés de services B2B. Elle s'installe **par-dessus DYONYSOS Lite** : vous
conservez le système de design, les palettes, les 5 blocs et les 3 pages de la
version gratuite, et vous ajoutez tout ce qui suit.

7 blocs supplémentaires
-----------------------
* **Témoignages en carrousel** — citations, auteur, fonction, navigation clavier.
* **Grille tarifaire à 3 colonnes** — offre du milieu mise en avant, liste de
  prestations incluses, bouton par offre.
* **Questions fréquentes en accordéon** — accordéon Bootstrap accessible.
* **Chronologie / étapes de projet** — quatre jalons datés, alternés.
* **Portfolio en grille filtrable** — filtres par catégorie, sans dépendance JS.
* **Équipe** — portraits, fonctions et liens de contact.
* **Logos partenaires** — bandeau de références en niveaux de gris.

4 pages supplémentaires
-----------------------
À propos, Tarifs, Portfolio et une page Blog stylée (liste d'articles).

Variantes de mise en page
-------------------------
* **3 dispositions d'en-tête** : centrée, séparée avec bandeau d'information,
  et minimale, sélectionnables dans le panneau « En-tête » de l'éditeur.
* **2 dispositions de pied de page** : étendue à quatre colonnes et compacte,
  sélectionnables dans le panneau « Pied de page ».

Mode sombre
-----------
Une inversion complète des couleurs, activable par un bouton placé dans la page
ou automatiquement selon la préférence du système. Le choix est mémorisé.

Compatible Odoo 19 Community et Enterprise. Aucune dépendance externe.
""",
    "version": "19.0.1.0.0",
    "category": "Theme/Corporate",
    "author": "DYONYSOS",
    "website": "https://dyonysos.fr",
    "support": "welcome@dyonysos.fr",
    "license": "OPL-1",
    "price": 179.10,
    "currency": "EUR",
    "depends": ["theme_dyonysos_lite"],
    "data": [
        "views/snippets/s_dyo_testimonials.xml",
        "views/snippets/s_dyo_pricing.xml",
        "views/snippets/s_dyo_faq.xml",
        "views/snippets/s_dyo_timeline.xml",
        "views/snippets/s_dyo_portfolio.xml",
        "views/snippets/s_dyo_team.xml",
        "views/snippets/s_dyo_logos.xml",
        "views/snippets/snippets.xml",
        "views/layout/headers.xml",
        "views/layout/footers.xml",
        "data/pages.xml",
        "data/menus.xml",
    ],
    "images": ["images/main_screenshot.png"],
    "assets": {
        # Odoo n'assemble que les assets du thème appliqué au site
        # (website.ir_asset._get_active_addons_list écarte les autres modules
        # de catégorie « Theme »). L'édition Pro reprend donc explicitement les
        # feuilles de style de l'édition Lite dont elle dépend.
        "web._assets_primary_variables": [
            "theme_dyonysos_lite/static/src/scss/primary_variables.scss",
            "theme_dyonysos/static/src/scss/primary_variables.scss",
        ],
        "web.assets_frontend": [
            "theme_dyonysos_lite/static/src/scss/theme.scss",
            "theme_dyonysos/static/src/scss/theme_pro.scss",
            "theme_dyonysos/static/src/scss/dark_mode.scss",
            "theme_dyonysos/static/src/js/dyo_dark_mode.js",
            "theme_dyonysos/static/src/js/dyo_portfolio_filter.js",
        ],
        "website.website_builder_assets": [
            "theme_dyonysos/static/src/builder/dyo_layout_options.xml",
            "theme_dyonysos/static/src/builder/dyo_footer_option_plugin.js",
        ],
    },
    "installable": True,
    "application": False,
}
