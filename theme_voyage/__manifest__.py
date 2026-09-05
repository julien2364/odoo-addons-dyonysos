# -*- coding: utf-8 -*-
{
    'name': 'Thème Voyage — Carnet de voyage et tourisme (pro)',
    'summary': "Décrire un séjour ne le vend pas. Le détailler, si. Itinéraire étape par étape, fiche destination chiffrée, calendrier de départs avec places restantes, demande de devis.",
    'description': """
Thème Voyage — version pro
==========================

Ajoute à la version gratuite tout ce qu'il faut pour vendre un séjour plutôt que
le décrire : carte d'itinéraire par étapes, galerie photo en mosaïque avec
lightbox, fiche destination (durée, budget, saison, difficulté), témoignages de
voyageurs, calendrier de départs, formulaire de demande de devis et carnet de
bord chronologique, un mode sombre mémorisé, plus deux pages prêtes à l'emploi
(destination et itinéraire).
""",
    'category': 'Theme/Creative',
    'version': '19.0.1.0.0',
    'author': 'DYONYSOS',
    'website': 'https://dyonysos.fr',
    'support': 'welcome@dyonysos.fr',
    'license': 'OPL-1',
    'price': 179.10,
    'currency': 'EUR',
    'depends': ['theme_voyage_lite'],
    'data': [
        'views/snippets/s_voyage_itineraire.xml',
        'views/snippets/s_voyage_galerie.xml',
        'views/snippets/s_voyage_fiche.xml',
        'views/snippets/s_voyage_temoignages.xml',
        'views/snippets/s_voyage_departs.xml',
        'views/snippets/s_voyage_devis.xml',
        'views/snippets/s_voyage_carnet.xml',
        'views/snippets/s_voyage_mode_sombre.xml',
        'views/snippets/snippets.xml',
        'views/layout/headers.xml',
        'views/layout/footers.xml',
        'data/pages.xml',
        'data/menus.xml',
    ],
    'assets': {
        # PIÈGE ODOO 19 — Odoo n'assemble que les assets du thème appliqué.
        # Un thème payant qui « depends » d'un thème gratuit N'HÉRITE PAS de son
        # SCSS : les fichiers du thème gratuit sont redéclarés ici, dans l'ordre.
        'web._assets_primary_variables': [
            'theme_voyage_lite/static/src/scss/primary_variables.scss',
            'theme_voyage/static/src/scss/primary_variables.scss',
        ],
        'web.assets_frontend': [
            'theme_voyage_lite/static/src/scss/theme.scss',
            'theme_voyage/static/src/scss/theme.scss',
            'theme_voyage/static/src/scss/dark_mode.scss',
            'theme_voyage/static/src/js/voyage_lightbox.js',
            'theme_voyage/static/src/js/voyage_dark_mode.js',
        ],
        'website.website_builder_assets': [
            'theme_voyage/static/src/builder/voyage_layout_options.xml',
            'theme_voyage/static/src/builder/voyage_footer_option_plugin.js',
        ],
    },
    'images': ['images/main_screenshot.png'],
    'installable': True,
    'application': False,
}
