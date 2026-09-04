# -*- coding: utf-8 -*-
{
    'name': 'Thème Voyage — Carnet de voyage et tourisme (gratuit)',
    'summary': "Thème chaleureux et aéré pour agences, carnets de voyage et offices "
               "de tourisme : bandeau d'accueil, grille de destinations, récit en deux colonnes.",
    'description': """
Thème Voyage — version gratuite
===============================

Système de design complet — palette sable, terracotta et bleu profond, titres en
Poppins, texte en Inter, cartes à coins arrondis et ombres douces — avec les
quatre blocs indispensables à une page d'accueil de site de voyage : bandeau
pleine hauteur, grille de destinations, récit en deux colonnes texte/image et
appel à l'action.
""",
    'category': 'Theme/Creative',
    'version': '19.0.1.0.0',
    'author': 'DYONYSOS',
    'website': 'https://dyonysos.fr',
    'support': 'welcome@dyonysos.fr',
    'license': 'LGPL-3',
    'depends': ['website'],
    'data': [
        'views/snippets/s_voyage_hero.xml',
        'views/snippets/s_voyage_destinations.xml',
        'views/snippets/s_voyage_recit.xml',
        'views/snippets/s_voyage_appel.xml',
        'views/snippets/snippets.xml',
        'data/pages.xml',
    ],
    'assets': {
        # Le fichier de variables est AJOUTÉ APRÈS celui de website : il consomme
        # $o-theme-font-configs et $o-color-palettes, qui n'existent pas encore
        # si on le place en 'prepend'.
        'web._assets_primary_variables': [
            'theme_voyage_lite/static/src/scss/primary_variables.scss',
        ],
        'web.assets_frontend': [
            'theme_voyage_lite/static/src/scss/theme.scss',
        ],
    },
    'images': ['images/main_screenshot.png'],
    'installable': True,
    'application': False,
}
