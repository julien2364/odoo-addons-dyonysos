# -*- coding: utf-8 -*-
{
    "name": "Thème Agence B2B — services et conseil (gratuit)",
    'summary': "Votre site d'agence ressemble à celui de votre concurrent. Un système de design complet plutôt qu'un habillage.",
    "description": """
Thème Agence B2B — édition gratuite
==================================

Un thème de site web **gratuit, complet et réellement utilisable** pour les
agences, cabinets de conseil et sociétés de services B2B.

Ce qu'il apporte
----------------
* **Système de design complet** : palette bleu nuit / bleu vif / violet,
  typographie Poppins + Inter, échelle typographique maîtrisée, boutons,
  formulaires, tableaux, cartes, ombres douces, rayons de 12 px.
* **4 palettes** sélectionnables dans l'éditeur : Minuit (par défaut),
  Terracotta, Forêt et Graphite.
* **5 blocs originaux** : bandeau d'accueil, grille de services, bandeau de
  chiffres clés, section « à propos » et appel à l'action pleine largeur.
* **3 pages de démonstration** : accueil, services, contact.
* En-tête et pied de page retravaillés, rythme vertical généreux,
  contrastes conformes WCAG AA et focus clavier visible.

Aucune dépendance externe. Compatible Odoo 19 Community et Enterprise.

La version **l'édition complète** ajoute 7 blocs supplémentaires (témoignages,
tarifs, FAQ, chronologie, portfolio filtrable, équipe, logos partenaires),
4 pages de plus, des variantes d'en-tête et de pied de page sélectionnables
dans l'éditeur, ainsi qu'un mode sombre.
""",
    "version": "19.0.1.0.0",
    "category": "Theme/Corporate",
    "author": "DYONYSOS",
    "website": "https://dyonysos.fr",
    "support": "welcome@dyonysos.fr",
    "license": "LGPL-3",
    "depends": ["website"],
    "data": [
        "views/snippets/s_dyo_hero.xml",
        "views/snippets/s_dyo_services.xml",
        "views/snippets/s_dyo_stats.xml",
        "views/snippets/s_dyo_about.xml",
        "views/snippets/s_dyo_cta.xml",
        "views/snippets/snippets.xml",
        "views/layout.xml",
        "data/pages.xml",
        "data/menus.xml",
    ],
    "images": ["images/main_screenshot.png"],
    "assets": {
        "web._assets_primary_variables": [
            "theme_dyonysos_lite/static/src/scss/primary_variables.scss",
        ],
        "web.assets_frontend": [
            "theme_dyonysos_lite/static/src/scss/theme.scss",
        ],
    },
    "installable": True,
    "application": False,
}
