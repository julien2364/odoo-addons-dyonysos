# -*- coding: utf-8 -*-
{
    "name": "AI Invoice & Expense Digitization",
    "summary": "OCR par IA des factures fournisseurs et notes de frais (Community) — "
               "Claude, OpenAI, Mistral, Grok : facture en brouillon en quelques secondes",
    "description": """
AI Invoice & Expense Digitization
=================================

Équivalent Community de la numérisation Enterprise, sans crédits IAP :
chaque PDF ou image reçu (alias mail achats, glisser-déposer sur le journal,
pièce jointe d'une note de frais) est lu par un modèle de vision et transformé
en facture fournisseur ou note de frais en brouillon :

* fournisseur (recherche par TVA, email, nom ; création optionnelle),
* numéro, dates de facture et d'échéance, devise,
* lignes avec quantité, prix unitaire et taux de TVA (rapproché des taxes Odoo),
* contrôle des totaux et note dans le chatter si écart,
* journal des extractions (durée, jetons, statut) pour suivre le coût.

Fournisseurs IA pris en charge : Anthropic (PDF natif), OpenAI, Mistral, xAI Grok
(API compatible OpenAI). Clé API stockée dans les paramètres système.
""",
    "version": "19.0.1.0.0",
    "category": "Accounting/Accounting",
    "author": "DYONYSOS",
    "website": "https://dyonysos.fr",
    "support": "welcome@dyonysos.fr",
    "license": "OPL-1",
    "price": 250.0,
    "currency": "EUR",
    "depends": ["account", "hr_expense"],
    "external_dependencies": {"python": ["requests"]},
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/ai_extract_log_views.xml",
        "views/account_move_views.xml",
        "views/hr_expense_views.xml",
    ],
    "images": ["static/description/banner.png"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
