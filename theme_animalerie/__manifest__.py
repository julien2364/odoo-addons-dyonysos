# -*- coding: utf-8 -*-
{
    'name': 'Thème Animalerie — Boutique en ligne (pro)',
    'summary': "Sélecteur par animal, comparateur, avis notés, guide de tailles, "
               "abonnement, blocs conseils, promotions, panier et tunnel stylés, mode sombre, trois dispositions d'en-tête et deux de pied de page.",
    'description': """
Thème Animalerie — version pro
==============================

Ajoute à la version gratuite les blocs qui font vendre une animalerie en ligne :
sélecteur par type d'animal, comparateur de produits, avis clients avec notes,
guide de tailles, offre d'abonnement et de livraison récurrente, blocs conseils,
mise en avant des promotions, page catégorie enrichie, un mode sombre mémorisé, plus l'habillage
complet du panier et du tunnel de commande.

La marque « Trèfle &amp; Museau » des données de démonstration est fictive.
""",
    'category': 'Theme/eCommerce',
    'version': '19.0.1.0.0',
    'author': 'DYONYSOS',
    'website': 'https://dyonysos.fr',
    'support': 'welcome@dyonysos.fr',
    'license': 'OPL-1',
    'price': 345.00,
    'currency': 'EUR',
    'depends': ['theme_animalerie_lite'],
    'data': [
        'views/snippets/s_anim_selecteur.xml',
        'views/snippets/s_anim_comparateur.xml',
        'views/snippets/s_anim_avis.xml',
        'views/snippets/s_anim_tailles.xml',
        'views/snippets/s_anim_abonnement.xml',
        'views/snippets/s_anim_conseils.xml',
        'views/snippets/s_anim_promotions.xml',
        'views/snippets/s_anim_mode_sombre.xml',
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
            'theme_animalerie_lite/static/src/scss/primary_variables.scss',
            'theme_animalerie/static/src/scss/primary_variables.scss',
        ],
        'web.assets_frontend': [
            'theme_animalerie_lite/static/src/scss/theme.scss',
            'theme_animalerie/static/src/scss/theme.scss',
            'theme_animalerie/static/src/scss/dark_mode.scss',
            'theme_animalerie/static/src/js/anim_compare.js',
            'theme_animalerie/static/src/js/anim_dark_mode.js',
        ],
        'website.website_builder_assets': [
            'theme_animalerie/static/src/builder/anim_layout_options.xml',
            'theme_animalerie/static/src/builder/anim_footer_option_plugin.js',
        ],
    },
    'images': ['images/main_screenshot.png'],
    'installable': True,
    'application': False,
}
