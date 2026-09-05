# -*- coding: utf-8 -*-
{
    'name': 'Thème Pulse — Salle de sport et studio (gratuit)',
    'summary': "Sombre par défaut, titrage condensé, accent lime. Bandeau plein écran, quatre points de méthode, trois formules d'abonnement : la page d'accueil d'un studio.",
    'description': """

Thème Pulse — version gratuite
==============================

Système de design sombre pour une salle de sport, un studio de force ou un
coach indépendant : fond charbon, accent lime électrique, titrage condensé en
capitales, angles généreux, cartes plates cerclées. Deux palettes livrées
(charbon/lime et charbon/ambre).

Quatre blocs manipulables dans l'éditeur de site Odoo : bandeau plein écran,
quatre points de méthode, trois formules d'abonnement comparables, appel à
séance d'essai.

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
        'views/snippets/s_pulse_hero.xml',
        'views/snippets/s_pulse_formules.xml',
        'views/snippets/s_pulse_atouts.xml',
        'views/snippets/s_pulse_essai.xml',
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
            'theme_pulse_lite/static/src/scss/primary_variables.scss',
        ],
        'web.assets_frontend': [
            'theme_pulse_lite/static/src/scss/theme.scss',
        ],
    },
    'images': ['images/main_screenshot.png'],
    'installable': True,
    'application': False,
}
