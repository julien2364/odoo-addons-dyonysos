# -*- coding: utf-8 -*-
{
    'name': 'Thème Animalerie — Boutique en ligne (gratuit)',
    'summary': "Thème e-commerce rassurant pour animalerie : page d'accueil boutique, "
               "grille de produits, fiche produit retravaillée, bandeau de réassurance.",
    'description': """
Thème Animalerie — version gratuite
===================================

Système de design complet pour une boutique en ligne d'animalerie : palette verte
naturelle et terracotta, coins très arrondis, typographie ronde et lisible,
illustrations générées (silhouettes stylisées, motifs de pattes, formes
organiques).

Contient la page d'accueil boutique, la grille de produits, la fiche produit
retravaillée et le bandeau de réassurance (livraison, retours, paiement
sécurisé), avec douze produits et trois catégories de démonstration.

La marque « Trèfle & Museau » utilisée dans les données de démonstration est
fictive : elle n'existe pas et sert uniquement d'exemple.
""",
    'category': 'Theme/eCommerce',
    'version': '19.0.1.0.0',
    'author': 'DYONYSOS',
    'website': 'https://dyonysos.fr',
    'support': 'welcome@dyonysos.fr',
    'license': 'LGPL-3',
    'depends': ['website', 'website_sale'],
    'data': [
        'views/snippets/s_anim_accueil.xml',
        'views/snippets/s_anim_produits.xml',
        'views/snippets/s_anim_reassurance.xml',
        'views/snippets/snippets.xml',
        'views/shop_templates.xml',
        'data/products.xml',
        'data/pages.xml',
    ],
    'assets': {
        # Ajouté APRÈS le fichier de website : il consomme $o-theme-font-configs
        # et $o-color-palettes, qui n'existent pas encore en 'prepend'.
        'web._assets_primary_variables': [
            'theme_animalerie_lite/static/src/scss/primary_variables.scss',
        ],
        'web.assets_frontend': [
            'theme_animalerie_lite/static/src/scss/theme.scss',
        ],
    },
    'images': ['images/main_screenshot.png'],
    'installable': True,
    'application': False,
}
