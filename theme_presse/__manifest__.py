# -*- coding: utf-8 -*-
{
    'name': 'Thème Presse — Magazine et presse en ligne (pro)',
    'summary': "Blocs éditoriaux avancés pour un vrai média : une multi-niveaux, "
               "fil d'actualité, grille par rubrique avec filtres, dossier, "
               "encadré auteur, chronologie, newsletter, sommaire, mode lecture, mode sombre, trois dispositions d'en-tête et deux de pied de page.",
    'description': """
Thème Presse — version pro
==========================

Ajoute à la version gratuite les blocs dont un média a besoin quand il publie
plusieurs articles par jour : bloc « une » multi-niveaux (1 article principal et
4 secondaires), fil d'actualité en colonne, grille par rubrique avec filtres,
dossier ou série d'articles, encadré auteur, chronologie d'événement et bandeau
newsletter, plus deux pages prêtes à l'emploi (rubrique et auteur), le sommaire
automatique des intertitres, le mode lecture et un mode sombre mémorisé.
""",
    'category': 'Theme/Creative',
    'version': '19.0.1.0.0',
    'author': 'DYONYSOS',
    'website': 'https://dyonysos.fr',
    'support': 'welcome@dyonysos.fr',
    'license': 'OPL-1',
    'price': 345.00,
    'currency': 'EUR',
    'depends': ['theme_presse_lite'],
    'data': [
        'views/snippets/s_presse_une_multi.xml',
        'views/snippets/s_presse_fil.xml',
        'views/snippets/s_presse_rubriques.xml',
        'views/snippets/s_presse_dossier.xml',
        'views/snippets/s_presse_auteur.xml',
        'views/snippets/s_presse_chronologie.xml',
        'views/snippets/s_presse_newsletter.xml',
        'views/snippets/s_presse_mode_sombre.xml',
        'views/snippets/snippets.xml',
        'views/blog_templates.xml',
        'views/layout/headers.xml',
        'views/layout/footers.xml',
        'data/pages.xml',
        'data/menus.xml',
    ],
    'assets': {
        # PIÈGE ODOO 19 — Odoo n'assemble que les assets du thème appliqué.
        # Un thème payant qui « depends » d'un thème gratuit N'HÉRITE PAS de son
        # SCSS : les fichiers du thème gratuit doivent être redéclarés ici, dans
        # le bon ordre, sinon la version pro s'affiche sans son système de design.
        'web._assets_primary_variables': [
            'theme_presse_lite/static/src/scss/primary_variables.scss',
            'theme_presse/static/src/scss/primary_variables.scss',
        ],
        'web.assets_frontend': [
            'theme_presse_lite/static/src/scss/theme.scss',
            'theme_presse/static/src/scss/theme.scss',
            'theme_presse/static/src/scss/dark_mode.scss',
            'theme_presse/static/src/js/presse_reader.js',
            'theme_presse/static/src/js/presse_dark_mode.js',
        ],
        'website.website_builder_assets': [
            'theme_presse/static/src/builder/presse_layout_options.xml',
            'theme_presse/static/src/builder/presse_footer_option_plugin.js',
        ],
    },
    'images': ['images/main_screenshot.png'],
    'installable': True,
    'application': False,
}
