# -*- coding: utf-8 -*-
{
    "name": "Studio Lite — Customize Odoo without code",
    "summary": "Champs personnalisés, placement dans les vues, automatisations "
               "et journal réversible des personnalisations — sans écrire de XML",
    "description": """
Studio Lite — personnaliser Odoo sans code
==========================================

Odoo Studio est réservé à l'édition Enterprise. Odoo Community sait pourtant
déjà tout faire (champs personnalisés via ``ir.model.fields``, vues héritées via
``ir.ui.view``, automatisations via ``base.automation``) — mais uniquement en
mode développeur, à la main, en XML.

Studio Lite apporte l'interface qui manque et couvre les usages courants :

* **Champs personnalisés** : un assistant crée le champ ``x_...`` ET la vue
  héritée qui l'affiche, en une seule opération (14 types, options par type,
  valeurs de sélection, aide, obligatoire, suivi au chatter).
* **Placement** : après un champ existant, dans un onglet, ou en fin de
  formulaire — sans toucher au XML.
* **Retouches de vues** : masquer un champ, le rendre obligatoire ou en lecture
  seule, en un clic (vue héritée ``position="attributes"``).
* **Automatisations sans code** : « quand ... alors ... » au-dessus de
  ``base.automation`` (email, mise à jour de champ, activité, abonné).
* **Journal des personnalisations** : tout ce que le module crée est tracé,
  désactivable et supprimable proprement, dans l'ordre inverse de création.

Ce module n'est pas Odoo Studio : il ne fabrique pas de nouveaux modèles ni de
rapports, et n'offre pas d'édition glisser-déposer. Il couvre l'essentiel des
demandes de personnalisation quotidiennes.
""",
    "version": "19.0.1.0.0",
    "category": "Productivity",
    "author": "DYONYSOS",
    "website": "https://dyonysos.fr",
    "support": "welcome@dyonysos.fr",
    "license": "OPL-1",
    "price": 250.0,
    "currency": "EUR",
    "depends": ["base", "web", "mail", "base_automation"],
    "data": [
        "security/studio_lite_security.xml",
        "security/ir.model.access.csv",
        "views/studio_customization_views.xml",
        "views/studio_view_customization_views.xml",
        "wizards/studio_field_wizard_views.xml",
        "wizards/studio_automation_wizard_views.xml",
        "views/studio_lite_menus.xml",
    ],
    "images": ["static/description/banner.png"],
    "installable": True,
    "application": True,
    "auto_install": False,
}
