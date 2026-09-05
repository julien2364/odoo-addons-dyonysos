# -*- coding: utf-8 -*-
{
    'name': 'Thème Pulse — Salle de sport et studio (complet)',
    'summary': "Planning de cours, chiffres, parcours d'adhérent, avis, coachs, galerie, FAQ et coordonnées — treize blocs et quatre pages, dans la même direction artistique.",
    'description': """

Thème Pulse — version complète
==============================

Ajoute au module gratuit les neuf blocs d'un vrai site de studio :

* grille de six cours collectifs avec créneaux
* bandeau de chiffres à typographie géante
* parcours d'un nouvel adhérent en quatre étapes
* trois retours d'adhérents avec portraits
* portraits des coachs
* mosaïque du plateau en grille asymétrique
* questions fréquentes en accordéon
* présentation du lieu en deux colonnes
* coordonnées, accès et horaires
* pied de page complet aux couleurs du thème

Trois pages supplémentaires prêtes à l'emploi : Les cours, Tarifs, Le studio.

""",
    'category': 'Theme/Creative',
    'version': '19.0.1.0.0',
    'author': 'DYONYSOS',
    'website': 'https://dyonysos.fr',
    'support': 'welcome@dyonysos.fr',
    'license': 'OPL-1',
    'depends': ['theme_pulse_lite'],
    'data': [
        'views/footer.xml',
        'views/snippets/s_pulse_cours.xml',
        'views/snippets/s_pulse_chiffres.xml',
        'views/snippets/s_pulse_etapes.xml',
        'views/snippets/s_pulse_avis.xml',
        'views/snippets/s_pulse_equipe.xml',
        'views/snippets/s_pulse_galerie.xml',
        'views/snippets/s_pulse_faq.xml',
        'views/snippets/s_pulse_studio.xml',
        'views/snippets/s_pulse_contact.xml',
        'views/snippets/s_pulse_manifeste.xml',
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
            'theme_pulse_lite/static/src/scss/primary_variables.scss',
            'theme_pulse/static/src/scss/primary_variables.scss',
        ],
        'web.assets_frontend': [
            'theme_pulse_lite/static/src/scss/theme.scss',
            'theme_pulse/static/src/scss/theme.scss',
        ],
    },
    'images': ['images/main_screenshot.png'],
    'installable': True,
    'application': False,
}
