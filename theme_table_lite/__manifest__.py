# -*- coding: utf-8 -*-
{
    'name': 'Thème La Table — Restaurant et bistrot (gratuit)',
    'summary': "Un thème de restaurant qui ressemble à un restaurant. Terre cuite, crème et olive sombre, titrage serif, quatre blocs pour monter une page d'accueil crédible.",
    'description': """

Thème La Table — version gratuite
=================================

Système de design complet pour un restaurant, un bistrot ou un traiteur :
palette terre cuite, crème et olive sombre, titrage serif à fort contraste,
texte en sans-serif humaniste, angles courts et ombres basses.

Quatre blocs manipulables dans l'éditeur de site Odoo :
bandeau de salle plein écran, vitrine de trois assiettes, présentation de la
maison en deux colonnes, et appel à réservation.

Contenu de démonstration entièrement fictif. Images générées par programme :
aucune photographie tierce, aucune marque tierce.

""",
    'category': 'Theme/Creative',
    'version': '19.0.1.0.0',
    'author': 'DYONYSOS',
    'website': 'https://dyonysos.fr',
    'support': 'welcome@dyonysos.fr',
    'license': 'LGPL-3',
    'depends': ['website'],
    'data': [
        'views/layout.xml',
        'views/snippets/s_table_hero.xml',
        'views/snippets/s_table_plats.xml',
        'views/snippets/s_table_maison.xml',
        'views/snippets/s_table_reserver.xml',
        'views/snippets/snippets.xml',
        'data/pages.xml',
    ],
    'assets': {
        # Placé APRÈS les variables de website : ce fichier consomme
        # $o-theme-font-configs et $o-color-palettes, qui n'existent pas
        # encore si on l'ajoute en 'prepend'.
        #
        # PIÈGE ODOO 19 — website/models/ir_asset.py::_get_active_addons_list
        # écarte TOUS les modules de thème sauf celui appliqué au site. Un thème
        # payant qui « depends » d'un thème gratuit N'HÉRITE DONC PAS de son
        # SCSS : les fichiers du gratuit sont redéclarés ici, dans l'ordre.
        'web._assets_primary_variables': [
            'theme_table_lite/static/src/scss/primary_variables.scss',
        ],
        'web.assets_frontend': [
            'theme_table_lite/static/src/scss/theme.scss',
        ],
    },
    'images': ['images/main_screenshot.png'],
    'installable': True,
    'application': False,
}
