# -*- coding: utf-8 -*-
{
    'name': 'Thème Presse — Magazine et presse en ligne (gratuit)',
    'summary': "Votre site Odoo publie beaucoup. Il ne se lit pas. Le système de design éditorial qui rend un long article réellement lisible.",
    'description': """
Thème Presse — version gratuite
===============================

Système de design éditorial complet pour un site Odoo qui publie beaucoup :
titres en serif contrastée, texte en sans-serif, échelle typographique marquée,
filets fins, palette sobre avec un rouge éditorial en accent.

Contient le gabarit d'article (chapô, intertitres, citations, légendes, temps de
lecture), la grille d'articles, le bloc « une » et le bloc « à lire aussi », ainsi
que l'habillage des vues du blog Odoo.
""",
    'category': 'Theme/Creative',
    'version': '19.0.1.0.0',
    'author': 'DYONYSOS',
    'website': 'https://dyonysos.fr',
    'support': 'welcome@dyonysos.fr',
    'license': 'LGPL-3',
    'depends': ['website', 'website_blog'],
    'data': [
        'views/snippets/s_presse_une.xml',
        'views/snippets/s_presse_grille.xml',
        'views/snippets/s_presse_a_lire_aussi.xml',
        'views/snippets/s_presse_article.xml',
        'views/snippets/snippets.xml',
        'views/blog_templates.xml',
        'data/blog_demo.xml',
        'data/pages.xml',
        'data/menus.xml',
    ],
    'assets': {
        # Le fichier de variables doit être AJOUTÉ APRÈS celui de website :
        # il consomme $o-theme-font-configs et $o-color-palettes, qui n'existent
        # pas encore si on le place en 'prepend'.
        'web._assets_primary_variables': [
            'theme_presse_lite/static/src/scss/primary_variables.scss',
        ],
        'web.assets_frontend': [
            'theme_presse_lite/static/src/scss/theme.scss',
        ],
    },
    'images': ['images/main_screenshot.png'],
    'installable': True,
    'application': False,
}
