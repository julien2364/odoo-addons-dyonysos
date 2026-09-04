# -*- coding: utf-8 -*-
{
    "name": "Dougs Bridge — Accounting Export",
    "summary": "Envoie automatiquement factures clients, factures fournisseurs et notes de frais "
               "d'Odoo vers votre cabinet Dougs (API First, email, SFTP, dossier partagé, ZIP)",
    "description": """
Dougs Bridge — Accounting Export
================================

Un seul point de saisie : Odoo. Le pont sélectionne les pièces validées
(factures clients, avoirs, factures fournisseurs, notes de frais approuvées),
génère un lot (PDF + XML Factur-X pour les ventes + journal CSV) et le transmet
au cabinet Dougs par le canal de votre choix :

* **API First (Dougs)** — plateforme agréée de facturation électronique, REST ;
* **Email** — envoi du lot à l'adresse de collecte du cabinet ;
* **SFTP** ou **dossier partagé** (Google Drive / Nextcloud synchronisé sur le serveur) ;
* **Téléchargement** — ZIP à déposer soi-même dans Dougs.

Chaque pièce garde son statut (à envoyer / envoyée / erreur), les échecs se
rejouent, un compte-rendu est envoyé par email après chaque lot, et une tâche
planifiée peut faire tourner l'export tous les jours ou toutes les semaines.

Compatible Odoo Community et Enterprise. Fonctionne pour tout cabinet qui
accepte des pièces par email, SFTP ou dossier partagé — pas seulement Dougs.
""",
    "version": "19.0.1.0.0",
    "category": "Accounting/Accounting",
    "author": "DYONYSOS",
    "website": "https://dyonysos.fr",
    "support": "welcome@dyonysos.fr",
    "license": "OPL-1",
    "price": 250.0,
    "currency": "EUR",
    "depends": ["account", "hr_expense", "account_edi_ubl_cii", "mail"],
    "external_dependencies": {"python": ["requests"]},
    "data": [
        "security/ir.model.access.csv",
        "security/dougs_security.xml",
        "data/mail_template_data.xml",
        "data/ir_cron_data.xml",
        "views/dougs_export_views.xml",
        "views/account_move_views.xml",
        "views/hr_expense_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "images": ["images/main_screenshot.png"],
    "installable": True,
    "application": False,
}
