# -*- coding: utf-8 -*-
"""Canal de publication vers un réseau social."""

import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

#: Longueur maximale raisonnable par réseau (caractères).
NETWORK_MAX_LENGTH = {
    "x": 280,
    "linkedin": 3000,
    "instagram": 2200,
    "facebook": 5000,
    "tiktok": 2200,
    "youtube": 5000,
    "mastodon": 500,
    "other": 1000,
}

DEFAULT_TEMPLATE = "{title}\n\n{teaser}\n\n{url}\n{hashtags}"


class BlogSocialChannel(models.Model):
    _name = "blog.social.channel"
    _description = "Canal de publication sociale"
    _order = "sequence, id"

    name = fields.Char(string="Nom", required=True)
    active = fields.Boolean(string="Actif", default=True)
    sequence = fields.Integer(string="Séquence", default=10)
    network = fields.Selection(
        [
            ("facebook", "Facebook"),
            ("instagram", "Instagram"),
            ("linkedin", "LinkedIn"),
            ("x", "X (Twitter)"),
            ("tiktok", "TikTok"),
            ("youtube", "YouTube"),
            ("mastodon", "Mastodon"),
            ("other", "Autre"),
        ],
        string="Réseau", required=True, default="linkedin",
    )
    transport = fields.Selection(
        [("postiz", "Postiz (auto-hébergé)"), ("webhook", "Webhook JSON générique")],
        string="Transport", required=True, default="webhook",
        help="Postiz : appel direct à votre instance Postiz.\n"
             "Webhook : POST JSON vers n8n, Make, Activepieces, Zapier ou tout "
             "service capable de recevoir un webhook.",
    )
    blog_ids = fields.Many2many(
        "blog.blog", "blog_social_channel_blog_rel", "channel_id", "blog_id",
        string="Blogs",
        help="Laisser vide pour publier les articles de tous les blogs.",
    )
    website_id = fields.Many2one("website", string="Site web")
    company_id = fields.Many2one(
        "res.company", string="Société", default=lambda self: self.env.company)

    # -- Postiz -------------------------------------------------------------
    postiz_base_url = fields.Char(
        string="URL de l'instance Postiz",
        help="Par exemple https://postiz.mondomaine.fr (sans barre oblique finale).")
    postiz_api_key = fields.Char(
        string="Clé d'API Postiz", groups="base.group_system",
        help="Envoyée dans l'en-tête Authorization. Réservée aux administrateurs.")
    postiz_integration_id = fields.Char(
        string="Identifiant d'intégration Postiz",
        help="Identifiant du compte social dans Postiz (« integration »).")

    # -- Webhook ------------------------------------------------------------
    webhook_url = fields.Char(
        string="URL du webhook", groups="base.group_system",
        help="Réservée aux administrateurs : une URL détournée exfiltrerait vos contenus.")
    webhook_method = fields.Selection(
        [("POST", "POST"), ("PUT", "PUT")], string="Méthode", default="POST")
    webhook_headers = fields.Text(
        string="En-têtes supplémentaires (JSON)",
        help='Objet JSON, par exemple {"X-Source": "odoo"}.')
    webhook_auth_header = fields.Char(
        string="En-tête d'authentification", groups="base.group_system",
        help="Valeur envoyée dans l'en-tête Authorization, par exemple « Bearer xxx ».")

    # -- Mise en forme ------------------------------------------------------
    message_template = fields.Text(
        string="Gabarit du message", default=DEFAULT_TEMPLATE,
        help="Variables disponibles : {title}, {subtitle}, {url}, {blog}, "
             "{author}, {teaser}, {hashtags}.")
    hashtags = fields.Char(
        string="Hashtags",
        help="Séparés par des espaces ou des virgules. Le # est ajouté si absent.")
    max_length = fields.Integer(string="Longueur maximale", default=280)
    include_image = fields.Boolean(string="Joindre l'image de couverture", default=True)
    utm_source = fields.Char(string="UTM source")
    utm_medium = fields.Char(string="UTM medium", default="social")
    utm_campaign = fields.Char(string="UTM campaign", default="blog")

    post_count = fields.Integer(string="Publications", compute="_compute_post_count")

    def _compute_post_count(self):
        data = self.env["blog.social.post"]._read_group(
            [("channel_id", "in", self.ids)], ["channel_id"], ["__count"])
        mapped = {channel.id: count for channel, count in data}
        for channel in self:
            channel.post_count = mapped.get(channel.id, 0)

    @api.onchange("network")
    def _onchange_network(self):
        for channel in self:
            if channel.network:
                channel.max_length = NETWORK_MAX_LENGTH.get(channel.network, 1000)
                if not channel.utm_source:
                    channel.utm_source = channel.network

    # ------------------------------------------------------------------
    # Sélection des canaux concernés par un article
    # ------------------------------------------------------------------
    @api.model
    def _channels_for_post(self, post):
        """Canaux actifs qui doivent recevoir ``post``."""
        domain = [
            "|", ("blog_ids", "=", False), ("blog_ids", "in", post.blog_id.ids),
        ]
        if post.website_id:
            domain = ["|", ("website_id", "=", False),
                      ("website_id", "=", post.website_id.id)] + domain
        return self.search(domain)

    # ------------------------------------------------------------------
    # Hashtags
    # ------------------------------------------------------------------
    def _formatted_hashtags(self):
        self.ensure_one()
        if not self.hashtags:
            return ""
        raw = self.hashtags.replace(",", " ").split()
        tags = []
        for tag in raw:
            tag = tag.strip()
            if not tag:
                continue
            tags.append(tag if tag.startswith("#") else "#" + tag)
        return " ".join(tags)

    # ------------------------------------------------------------------
    # En-têtes du webhook
    # ------------------------------------------------------------------
    def _webhook_headers_dict(self):
        self.ensure_one()
        channel = self.sudo()
        headers = {"Content-Type": "application/json"}
        if channel.webhook_headers:
            try:
                extra = json.loads(channel.webhook_headers)
            except (ValueError, TypeError):
                _logger.warning(
                    "Blog to Social: en-têtes JSON invalides sur le canal %s", channel.name)
                extra = None
            if isinstance(extra, dict):
                headers.update({str(k): str(v) for k, v in extra.items()})
        if channel.webhook_auth_header:
            headers["Authorization"] = channel.webhook_auth_header
        return headers

    # ------------------------------------------------------------------
    # Test du canal
    # ------------------------------------------------------------------
    def action_test_channel(self):
        """Envoie un message de test sans toucher aux articles."""
        self.ensure_one()
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url") or ""
        payload = {
            "message": _("Message de test envoyé depuis Odoo par le canal « %s ».", self.name),
            "title": _("Test Blog to Social"),
            "url": base_url,
            "image_url": False,
            "network": self.network,
            "blog": False,
            "post_id": False,
            "test": True,
        }
        result = self.env["blog.social.post"]._transport_send(self, payload)
        if result.get("ok"):
            message = _("Canal « %(name)s » : envoi réussi.%(remote)s", name=self.name,
                        remote=(_(" Identifiant distant : %s.", result["remote_id"])
                                if result.get("remote_id") else ""))
            kind = "success"
        else:
            message = _("Canal « %(name)s » : échec. %(error)s",
                        name=self.name, error=result.get("error") or "")
            kind = "danger"
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Test du canal"),
                "message": message,
                "type": kind,
                "sticky": kind == "danger",
            },
        }

    def action_view_posts(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Publications"),
            "res_model": "blog.social.post",
            "view_mode": "list,form",
            "domain": [("channel_id", "=", self.id)],
            "context": {"default_channel_id": self.id},
        }

    def _check_configured(self):
        """Vérifie qu'un canal est utilisable ; lève une UserError sinon."""
        self.ensure_one()
        channel = self.sudo()
        if channel.transport == "postiz":
            if not (channel.postiz_base_url and channel.postiz_api_key):
                raise UserError(_(
                    "Le canal « %s » n'a pas d'URL ou de clé d'API Postiz.", self.name))
        elif not channel.webhook_url:
            raise UserError(_("Le canal « %s » n'a pas d'URL de webhook.", self.name))
        return True
