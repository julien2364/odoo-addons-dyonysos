# -*- coding: utf-8 -*-
{
    "name": "Blog to Social — publish your Odoo blog posts automatically",
    "summary": "Publie automatiquement les articles du blog Odoo sur Facebook, "
               "Instagram, LinkedIn, X, TikTok, YouTube ou Mastodon — via Postiz "
               "ou n'importe quel webhook (n8n, Make, Activepieces, Zapier)",
    "description": """
Blog to Social — vos articles de blog sur les réseaux sociaux
=============================================================

Odoo Social Marketing est réservé à l'édition Enterprise. Un site Odoo
Community qui tient un blog n'a donc aucun moyen natif de pousser ses articles
vers les réseaux sociaux : il faut recopier le titre, le lien et l'accroche à la
main, réseau par réseau, article par article.

Blog to Social apporte cette brique manquante :

* **Canaux de publication** : un canal par réseau et par blog, avec son gabarit
  de message, ses hashtags, sa longueur maximale et ses paramètres UTM.
* **Deux transports** : **Postiz** (auto-hébergé, gratuit et open source) ou un
  **webhook JSON générique** qui se branche sur n8n, Make, Activepieces ou
  Zapier — donc, indirectement, sur n'importe quel réseau.
* **Déclenchement à la publication** : dès qu'un article passe en publié, une
  publication est mise en file pour chaque canal concerné.
* **Garde-fou anti-publication rétroactive** : la date d'installation du module
  est figée ; aucun article antérieur n'est jamais republié. Sur une instance de
  plusieurs milliers d'articles, c'est la différence entre un module utile et un
  bannissement de compte.
* **Publication automatique désactivée par défaut** : tant que vous ne l'avez
  pas cochée, seul le bouton manuel « Publier sur les réseaux » agit.
* **File d'attente et tâche planifiée** : programmation à date, rejeu des
  erreurs, arrêt après 5 tentatives.

Les clés d'API et l'URL du webhook ne sont visibles que par les administrateurs
système, et les erreurs réseau ne remontent jamais en exception à l'utilisateur :
elles sont journalisées sur la publication.
""",
    "version": "19.0.1.0.0",
    "category": "Website/Website",
    "author": "DYONYSOS",
    "website": "https://dyonysos.fr",
    "support": "welcome@dyonysos.fr",
    "license": "OPL-1",
    "price": 250.0,
    "currency": "EUR",
    "depends": ["website_blog", "mail"],
    "external_dependencies": {"python": ["requests"]},
    "data": [
        "security/blog_social_publish_security.xml",
        "security/ir.model.access.csv",
        "data/blog_social_publish_data.xml",
        "views/blog_social_channel_views.xml",
        "views/blog_social_post_views.xml",
        "views/blog_post_views.xml",
        "views/res_config_settings_views.xml",
        "views/blog_social_publish_menus.xml",
    ],
    "images": ["images/main_screenshot.png"],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": True,
    "auto_install": False,
}
