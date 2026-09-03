# -*- coding: utf-8 -*-
{
    "name": "MCP Server for Odoo — AI assistant connector",
    "summary": "Serveur MCP natif dans Odoo : connectez Claude, ChatGPT, Cursor ou tout client "
               "MCP à votre ERP, avec vos droits d'accès Odoo et un journal d'audit",
    "description": """
MCP Server for Odoo
===================

Expose votre Odoo aux assistants IA via le **Model Context Protocol** (MCP),
sans middleware ni serveur externe : le point de terminaison ``/mcp`` est servi
par Odoo lui-même.

Sécurité d'abord
----------------
* Authentification par **clé API Odoo native** (scope ``odoo.mcp``) — révocable,
  avec date d'expiration, liée à un utilisateur réel.
* Chaque appel s'exécute **avec les droits de cet utilisateur** : règles de
  gestion, groupes, règles d'enregistrement et multi-société d'Odoo s'appliquent.
* Liste blanche de modèles : rien n'est exposé tant que vous ne l'avez pas
  autorisé, avec lecture / écriture / création / suppression au cas par cas et
  un domaine de restriction optionnel.
* **Journal d'audit** de chaque appel : outil, modèle, enregistrements touchés,
  durée, adresse IP, erreur éventuelle.

Outils MCP fournis
------------------
``odoo_list_models``, ``odoo_model_fields``, ``odoo_search``, ``odoo_read``,
``odoo_count``, ``odoo_read_group``, ``odoo_create``, ``odoo_write``,
``odoo_unlink``, ``odoo_call_method`` (liste blanche de méthodes) et
``odoo_search_partners``. Ressources MCP : schéma de chaque modèle autorisé.

Compatible Odoo 19 Community et Enterprise. Aucune dépendance Python
supplémentaire.
""",
    "version": "19.0.1.0.0",
    "category": "Productivity",
    "author": "DYONYSOS",
    "website": "https://dyonysos.fr",
    "support": "welcome@dyonysos.fr",
    "license": "OPL-1",
    "price": 250.0,
    "currency": "EUR",
    "depends": ["base", "base_setup"],
    "data": [
        "security/mcp_security.xml",
        "security/ir.model.access.csv",
        "data/mcp_model_config_data.xml",
        "data/ir_cron_data.xml",
        "views/mcp_model_config_views.xml",
        "views/mcp_access_log_views.xml",
        "views/res_users_views.xml",
        "views/res_config_settings_views.xml",
        "views/mcp_menus.xml",
    ],
    "images": ["static/description/banner.png"],
    "installable": True,
    "application": True,
}
