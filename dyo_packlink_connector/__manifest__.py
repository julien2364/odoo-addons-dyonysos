# -*- coding: utf-8 -*-
{
    "name": "Packlink Connector for Odoo Community",
    "summary": "Transporteur Packlink PRO dans Odoo : tarifs comparés, étiquette PDF, "
               "suivi automatique et confirmation d'expédition Amazon",
    "description": """
Packlink Connector for Odoo Community
=====================================

Packlink PRO devient un **mode de livraison Odoo** à part entière : le tarif est
calculé sur le devis, l'étiquette est achetée à la validation du bon de livraison
et le suivi remonte tout seul.

* **Tarifs en direct** — au clic sur « Obtenir le tarif », le module interroge
  Packlink avec le poids et les dimensions réels du colis et retient le service
  le moins cher, ou le service que vous avez imposé sur le mode de livraison.
* **Achat de l'étiquette à la validation** — l'expédition est créée chez
  Packlink, l'étiquette PDF est jointe au bon de livraison et le numéro de suivi
  renseigné sur le transfert et la commande.
* **Suivi automatique** — une tâche planifiée rafraîchit l'état des expéditions
  en cours et note chaque étape dans le fil de discussion du transfert.
* **Annulation** — un bouton annule l'expédition côté Packlink tant qu'elle n'a
  pas été collectée.
* **Amazon** — si le connecteur Amazon Community est installé, le nom du
  transporteur Packlink et le numéro de suivi sont transmis à Amazon dans la
  confirmation d'expédition, avec la correspondance des noms attendus par
  Amazon (Chronopost, Colissimo, DHL, DPD, GLS, UPS…).
* **Journal des appels** — chaque appel API est tracé : opération, expédition,
  durée, statut, message d'erreur.

Multi-comptes et multi-sociétés. L'URL de l'API et l'en-tête d'authentification
sont paramétrables, pour suivre les évolutions de l'API sans mise à jour du
module.
""",
    "version": "19.0.1.0.0",
    "category": "Inventory/Delivery",
    "author": "DYONYSOS",
    "website": "https://dyonysos.fr",
    "support": "welcome@dyonysos.fr",
    "license": "OPL-1",
    "price": 250.0,
    "currency": "EUR",
    "depends": ["stock_delivery", "sale_management"],
    "external_dependencies": {"python": ["requests"]},
    "data": [
        "security/packlink_security.xml",
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "views/packlink_account_views.xml",
        "views/packlink_log_views.xml",
        "views/delivery_carrier_views.xml",
        "views/stock_picking_views.xml",
        "views/packlink_menus.xml",
    ],
    "images": ["images/main_screenshot.png"],
    "installable": True,
    "application": False,
}
