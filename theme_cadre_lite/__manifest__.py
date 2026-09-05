# -*- coding: utf-8 -*-
{
    'name': 'Thème Cadre — Agence immobilière et gestion (gratuit)',
    'summary': "Bleu nuit, laiton et beaucoup de blanc. Bandeau à deux colonnes avec indicateur, grille de biens cerclée, quatre engagements : la page d'accueil d'une agence sérieuse.",
    'description': """

Thème Cadre — version gratuite
==============================

Système de design pour une agence immobilière, un cabinet de gestion locative
ou une étude notariale : bleu nuit et laiton, titrage géométrique resserré,
angles courts, cartes cerclées plutôt qu'ombrées, deux palettes livrées.

Quatre blocs manipulables dans l'éditeur de site Odoo : bandeau à deux colonnes
avec indicateur chiffré, grille de biens, quatre engagements, appel à estimation.

Contenu de démonstration entièrement fictif. Images générées par programme :
aucune photographie tierce, aucune marque tierce.

""",
    'category': 'Theme/Corporate',
    'version': '19.0.1.0.0',
    'author': 'DYONYSOS',
    'website': 'https://dyonysos.fr',
    'support': 'welcome@dyonysos.fr',
    'license': 'LGPL-3',
    'depends': ['website'],
    'data': [
        'views/layout.xml',
        'views/snippets/s_cadre_hero.xml',
        'views/snippets/s_cadre_biens.xml',
        'views/snippets/s_cadre_methode.xml',
        'views/snippets/s_cadre_appel.xml',
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
            'theme_cadre_lite/static/src/scss/primary_variables.scss',
        ],
        'web.assets_frontend': [
            'theme_cadre_lite/static/src/scss/theme.scss',
        ],
    },
    'images': ['images/main_screenshot.png'],
    'installable': True,
    'application': False,
}
