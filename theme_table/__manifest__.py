# -*- coding: utf-8 -*-
{
    'name': 'Thème La Table — Restaurant et bistrot (complet)',
    'summary': 'La carte tarifée, la galerie, les avis, la brigade et les horaires — onze blocs et quatre pages prêtes, dans la même direction artistique.',
    'description': """

Thème La Table — version complète
=================================

Ajoute au module gratuit les sept blocs qui font la différence entre une page
d'accueil et un site de restaurant réellement exploitable :

* carte tarifée en deux colonnes, avec groupes, notes et prix alignés
* mosaïque d'images en grille asymétrique
* trois avis clients avec portraits
* portraits de la brigade
* bloc coordonnées, accessibilité et horaires de service
* bandeau citation éditorial
* parcours de réservation en quatre étapes

Trois pages supplémentaires prêtes à l'emploi : La carte, Le lieu, Réserver.

""",
    'category': 'Theme/Creative',
    'version': '19.0.1.0.0',
    'author': 'DYONYSOS',
    'website': 'https://dyonysos.fr',
    'support': 'welcome@dyonysos.fr',
    'license': 'OPL-1',
    'depends': ['theme_table_lite'],
    'data': [
        'views/footer.xml',
        'views/snippets/s_table_carte.xml',
        'views/snippets/s_table_galerie.xml',
        'views/snippets/s_table_avis.xml',
        'views/snippets/s_table_equipe.xml',
        'views/snippets/s_table_horaires.xml',
        'views/snippets/s_table_citation.xml',
        'views/snippets/s_table_etapes.xml',
        'views/snippets/snippets.xml',
        'data/pages.xml',
        'data/menus.xml',
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
            'theme_table/static/src/scss/primary_variables.scss',
        ],
        'web.assets_frontend': [
            'theme_table_lite/static/src/scss/theme.scss',
            'theme_table/static/src/scss/theme.scss',
        ],
    },
    'images': ['images/main_screenshot.png'],
    'installable': True,
    'application': False,
}
