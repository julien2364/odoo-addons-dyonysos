# -*- coding: utf-8 -*-
{
    'name': 'Thème Cadre — Agence immobilière et gestion (complet)',
    'summary': "Barèmes d'honoraires, chiffres, parcours de vente, avis, équipe, FAQ, partenaires et coordonnées — treize blocs et quatre pages, dans la même direction artistique.",
    'description': """

Thème Cadre — version complète
==============================

Ajoute au module gratuit les neuf blocs qui transforment une page d'accueil en
site d'agence réellement exploitable :

* trois barèmes d'honoraires comparables, avec formule mise en avant
* bandeau de chiffres clés
* parcours de vente en quatre étapes
* trois avis de vendeurs avec portraits
* portraits de l'équipe
* questions fréquentes en accordéon
* bandeau de partenaires (marques fictives générées)
* coordonnées, mentions professionnelles et horaires
* présentation de l'agence en deux colonnes
* pied de page complet aux couleurs du thème

Trois pages supplémentaires prêtes à l'emploi : Nos biens, Honoraires, L'agence.

""",
    'category': 'Theme/Corporate',
    'version': '19.0.1.0.0',
    'author': 'DYONYSOS',
    'website': 'https://dyonysos.fr',
    'support': 'welcome@dyonysos.fr',
    'license': 'OPL-1',
    'depends': ['theme_cadre_lite'],
    'data': [
        'views/footer.xml',
        'views/snippets/s_cadre_biens_plus.xml',
        'views/snippets/s_cadre_honoraires.xml',
        'views/snippets/s_cadre_chiffres.xml',
        'views/snippets/s_cadre_parcours.xml',
        'views/snippets/s_cadre_avis.xml',
        'views/snippets/s_cadre_equipe.xml',
        'views/snippets/s_cadre_faq.xml',
        'views/snippets/s_cadre_partenaires.xml',
        'views/snippets/s_cadre_contact.xml',
        'views/snippets/s_cadre_agence.xml',
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
            'theme_cadre_lite/static/src/scss/primary_variables.scss',
            'theme_cadre/static/src/scss/primary_variables.scss',
        ],
        'web.assets_frontend': [
            'theme_cadre_lite/static/src/scss/theme.scss',
            'theme_cadre/static/src/scss/theme.scss',
        ],
    },
    'images': ['images/main_screenshot.png'],
    'installable': True,
    'application': False,
}
