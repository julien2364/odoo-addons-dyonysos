# -*- coding: utf-8 -*-
{
    "name": "Amazon Connector for Odoo Community",
    "summary": "Synchronise les commandes, le stock et les prix Amazon avec Odoo Community "
               "via l'API SP-API (Selling Partner API)",
    "description": """
Amazon Connector for Odoo Community
===================================

Odoo Community ne dispose pas du connecteur Amazon natif, réservé à l'édition
Enterprise. Ce module apporte cette liaison à toute base Community — et va plus
loin, en synchronisant aussi le stock et les prix vers Amazon.

* **Import des commandes** — les commandes Amazon deviennent des commandes de
  vente Odoo, avec le client, l'adresse de livraison, les lignes rapprochées par
  SKU vendeur et les frais de port sur une ligne distincte.
* **Remontée du suivi** — dès qu'un bon de livraison est validé avec un numéro
  de suivi, l'expédition est confirmée côté Amazon.
* **Push du stock** — la quantité disponible Odoo est envoyée sur les annonces
  Amazon des produits marqués « Synchroniser avec Amazon ».
* **Push des prix** — le prix de la liste de prix choisie sur le compte est
  publié sur les mêmes annonces.
* **Journal de synchronisation** — chaque opération est tracée : compte,
  marketplace, nombre d'éléments, durée, statut et message d'erreur.

Multi-comptes, multi-marketplaces (les 10 places de marché européennes sont
pré-chargées), tâches planifiées désactivées par défaut, boutons manuels pour
chaque opération.
""",
    "version": "19.0.1.0.0",
    "category": "Sales/Sales",
    "author": "DYONYSOS",
    "website": "https://dyonysos.fr",
    "support": "welcome@dyonysos.fr",
    "license": "OPL-1",
    "price": 250.0,
    "currency": "EUR",
    "depends": ["sale_management", "stock", "delivery"],
    "external_dependencies": {"python": ["requests"]},
    "data": [
        "security/amazon_security.xml",
        "security/ir.model.access.csv",
        "data/amazon_marketplace_data.xml",
        "data/ir_cron_data.xml",
        "views/amazon_marketplace_views.xml",
        "views/amazon_sync_log_views.xml",
        "views/amazon_account_views.xml",
        "views/product_views.xml",
        "views/sale_order_views.xml",
        "views/amazon_menus.xml",
    ],
    "images": ["static/description/banner.png"],
    "installable": True,
    "application": False,
}
