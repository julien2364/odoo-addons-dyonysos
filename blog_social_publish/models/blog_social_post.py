# -*- coding: utf-8 -*-
"""Publication d'un article de blog sur un canal social."""

import json
import logging
import re
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:  # pragma: no cover - dépendance déclarée au manifeste
    requests = None
    _logger.warning("Blog to Social: la bibliothèque python « requests » est absente.")

#: Chemin de l'API publique Postiz, surchargeable par paramètre système.
DEFAULT_POSTIZ_PATH = "/api/public/v1/posts"
#: Délai d'attente réseau par défaut, en secondes.
DEFAULT_TIMEOUT = 20
#: Nombre maximal de tentatives avant abandon définitif.
MAX_RETRY = 5

ELLIPSIS = "…"


class BlogSocialPost(models.Model):
    _name = "blog.social.post"
    _description = "Publication sociale d'un article de blog"
    _order = "id desc"

    post_id = fields.Many2one(
        "blog.post", string="Article", required=True, ondelete="cascade", index=True)
    channel_id = fields.Many2one(
        "blog.social.channel", string="Canal", required=True, ondelete="cascade", index=True)
    network = fields.Selection(related="channel_id.network", string="Réseau", store=True)
    blog_id = fields.Many2one(related="post_id.blog_id", string="Blog", store=True)
    state = fields.Selection(
        [
            ("draft", "Brouillon"),
            ("queued", "En file"),
            ("sent", "Envoyé"),
            ("error", "Erreur"),
            ("cancelled", "Annulé"),
        ],
        string="État", default="draft", required=True, index=True, copy=False)
    message = fields.Text(string="Message", help="Texte final envoyé au réseau.")
    image_url = fields.Char(string="Image")
    link = fields.Char(string="Lien")
    scheduled_date = fields.Datetime(string="Programmé le")
    sent_date = fields.Datetime(string="Envoyé le", readonly=True, copy=False)
    remote_id = fields.Char(string="Identifiant distant", readonly=True, copy=False)
    error = fields.Text(string="Erreur", readonly=True, copy=False)
    retry_count = fields.Integer(string="Tentatives", default=0, readonly=True, copy=False)
    company_id = fields.Many2one(
        "res.company", string="Société", default=lambda self: self.env.company)

    _post_channel_uniq = models.Constraint(
        "unique(post_id, channel_id)",
        "Cet article a déjà une publication sur ce canal.",
    )

    @api.depends("post_id.name", "channel_id.name")
    def _compute_display_name(self):
        for record in self:
            record.display_name = "%s → %s" % (
                record.post_id.name or _("Article"), record.channel_id.name or "")

    # ==================================================================
    # Composition du message
    # ==================================================================
    @api.model
    def _base_url(self):
        return (self.env["ir.config_parameter"].sudo().get_param("web.base.url") or "").rstrip("/")

    @api.model
    def _absolute_url(self, url):
        if not url:
            return False
        if url.startswith(("http://", "https://")):
            return url
        return "%s/%s" % (self._base_url(), url.lstrip("/"))

    @api.model
    def _post_image_url(self, post):
        """URL absolue de l'image de couverture de l'article, si elle existe.

        ``blog.post`` hérite de ``website.cover_properties.mixin`` : l'image est
        stockée dans le JSON ``cover_properties``, clé ``background-image``,
        sous la forme ``url('/chemin/image.jpg')``.
        """
        raw = post.cover_properties or ""
        background = ""
        try:
            background = (json.loads(raw) or {}).get("background-image") or ""
        except (ValueError, TypeError):
            background = ""
        match = re.search(r"url\(\s*['\"]?(.*?)['\"]?\s*\)", background)
        if not match:
            return False
        path = match.group(1).strip()
        if not path or path == "none":
            return False
        return self._absolute_url(path)

    @api.model
    def _post_link(self, post, channel):
        """Lien absolu de l'article, enrichi des paramètres UTM du canal."""
        url = self._absolute_url(post.website_url or "/blog")
        utm = {}
        if channel.utm_source:
            utm["utm_source"] = channel.utm_source
        if channel.utm_medium:
            utm["utm_medium"] = channel.utm_medium
        if channel.utm_campaign:
            utm["utm_campaign"] = channel.utm_campaign
        if not utm:
            return url
        parts = urlparse(url)
        query = dict(parse_qsl(parts.query))
        query.update(utm)
        return urlunparse(parts._replace(query=urlencode(query)))

    @api.model
    def _cut_on_word(self, text, budget):
        """Tronque ``text`` à ``budget`` caractères sans couper un mot."""
        text = text.strip()
        if budget <= 0:
            return ""
        if len(text) <= budget:
            return text
        cut = text[:budget]
        if " " in cut.strip():
            cut = cut[:cut.rfind(" ")]
        return cut.rstrip(" \n\t\r.,;:-–—")

    @api.model
    def _truncate_message(self, text, url, max_length):
        """Tronque proprement en préservant l'URL entière en fin de message."""
        text = (text or "").strip()
        if not max_length or len(text) <= max_length:
            return text
        if url and url in text:
            body = text.replace(url, " ")
            body = re.sub(r"[ \t]{2,}", " ", body)
            body = re.sub(r"\n{3,}", "\n\n", body).strip()
            budget = max_length - len(url) - 1 - len(ELLIPSIS)
            if budget <= 0:
                # L'URL seule dépasse déjà la limite : on la garde entière.
                return url
            return "%s%s %s" % (self._cut_on_word(body, budget), ELLIPSIS, url)
        return self._cut_on_word(text, max_length - len(ELLIPSIS)) + ELLIPSIS

    @api.model
    def _render_message(self, post, channel):
        """Rendu du gabarit du canal pour un article donné."""
        link = self._post_link(post, channel)
        hashtags = channel._formatted_hashtags()
        teaser = (post.teaser or "").strip()
        values = {
            "title": post.name or "",
            "subtitle": post.subtitle or "",
            "url": link,
            "blog": post.blog_id.name or "",
            "author": post.author_id.name or "",
            "teaser": teaser,
            "hashtags": hashtags,
        }
        template = channel.message_template or "{title}\n{url}"
        try:
            message = template.format(**values)
        except (KeyError, IndexError, ValueError):
            _logger.warning(
                "Blog to Social: gabarit invalide sur le canal %s, repli sur titre + lien.",
                channel.name)
            message = "%s\n%s" % (values["title"], link)
        if hashtags and "{hashtags}" not in template:
            message = "%s\n%s" % (message.rstrip(), hashtags)
        message = re.sub(r"\n{3,}", "\n\n", message).strip()
        return self._truncate_message(message, link, channel.max_length)

    # ==================================================================
    # Création depuis un article
    # ==================================================================
    @api.model
    def _prepare_from_post(self, post, channel):
        return {
            "post_id": post.id,
            "channel_id": channel.id,
            "message": self._render_message(post, channel),
            "image_url": self._post_image_url(post) if channel.include_image else False,
            "link": self._post_link(post, channel),
            "state": "queued",
            "company_id": (post.website_id.company_id.id if post.website_id
                           else channel.company_id.id or self.env.company.id),
        }

    @api.model
    def _create_for_post(self, post, channels=None):
        """Crée les publications manquantes pour ``post``.

        Ne recrée jamais une publication existante : dépublier puis republier un
        article ne produit donc pas de doublon.
        """
        if channels is None:
            channels = self.env["blog.social.channel"]._channels_for_post(post)
        existing = self.with_context(active_test=False).search([
            ("post_id", "=", post.id), ("channel_id", "in", channels.ids)])
        todo = channels - existing.channel_id
        created = self.browse()
        for channel in todo:
            created |= self.create(self._prepare_from_post(post, channel))
        return created

    # ==================================================================
    # Transports
    # ==================================================================
    @api.model
    def _network_timeout(self):
        param = self.env["ir.config_parameter"].sudo().get_param(
            "blog_social_publish.timeout")
        try:
            return max(1, int(param))
        except (TypeError, ValueError):
            return DEFAULT_TIMEOUT

    @api.model
    def _postiz_path(self):
        return self.env["ir.config_parameter"].sudo().get_param(
            "blog_social_publish.postiz_post_path") or DEFAULT_POSTIZ_PATH

    @api.model
    def _extract_remote_id(self, data):
        """Trouve un identifiant de publication dans une réponse JSON."""
        if isinstance(data, list):
            data = data[0] if data else None
        if isinstance(data, dict):
            for key in ("id", "postId", "post_id", "remote_id", "identifier"):
                if data.get(key):
                    return str(data[key])
            for key in ("data", "posts", "result"):
                if data.get(key):
                    found = self._extract_remote_id(data[key])
                    if found:
                        return found
        return False

    @api.model
    def _postiz_payload(self, channel, payload):
        content = {"content": payload.get("message") or ""}
        if payload.get("image_url"):
            content["image"] = [{"path": payload["image_url"]}]
        return {
            "type": "now",
            "posts": [{
                "integration": {"id": channel.sudo().postiz_integration_id or ""},
                "value": [content],
            }],
        }

    @api.model
    def _transport_send(self, channel, payload):
        """Envoie ``payload`` via le transport du canal.

        Ne lève jamais : renvoie ``{"ok": bool, "remote_id": str, "error": str}``.
        """
        if requests is None:
            return {"ok": False, "error": _(
                "La bibliothèque python « requests » n'est pas installée sur ce serveur.")}
        channel_sudo = channel.sudo()
        timeout = self._network_timeout()
        try:
            if channel_sudo.transport == "postiz":
                base = (channel_sudo.postiz_base_url or "").rstrip("/")
                if not base or not channel_sudo.postiz_api_key:
                    return {"ok": False, "error": _(
                        "Canal Postiz incomplet : URL ou clé d'API manquante.")}
                url = base + self._postiz_path()
                headers = {
                    "Authorization": channel_sudo.postiz_api_key,
                    "Content-Type": "application/json",
                }
                body = self._postiz_payload(channel_sudo, payload)
            else:
                url = channel_sudo.webhook_url
                if not url:
                    return {"ok": False, "error": _("Canal webhook incomplet : URL manquante.")}
                headers = channel_sudo._webhook_headers_dict()
                body = dict(payload)
            response = requests.post(url, json=body, headers=headers, timeout=timeout)
        except Exception as error:  # noqa: BLE001 - aucune exception ne doit remonter
            _logger.warning("Blog to Social: erreur réseau sur le canal %s: %s",
                            channel.name, error)
            return {"ok": False, "error": "%s: %s" % (type(error).__name__, error)}

        status = getattr(response, "status_code", 0) or 0
        if status >= 300 or status < 200:
            text = ""
            try:
                text = (response.text or "")[:500]
            except Exception:  # noqa: BLE001
                text = ""
            return {"ok": False, "error": _("HTTP %(status)s — %(text)s",
                                            status=status, text=text)}
        data = None
        try:
            data = response.json()
        except Exception:  # noqa: BLE001 - réponse non JSON, ce n'est pas une erreur
            data = None
        return {"ok": True, "remote_id": self._extract_remote_id(data) or False}

    def _payload(self):
        """Charge utile complète transmise au webhook."""
        self.ensure_one()
        return {
            "message": self.message or "",
            "title": self.post_id.name or "",
            "subtitle": self.post_id.subtitle or "",
            "url": self.link or "",
            "image_url": self.image_url or False,
            "network": self.channel_id.network,
            "channel": self.channel_id.name,
            "blog": self.post_id.blog_id.name or "",
            "blog_id": self.post_id.blog_id.id,
            "post_id": self.post_id.id,
            "published_date": fields.Datetime.to_string(self.post_id.post_date) or "",
            "author": self.post_id.author_id.name or "",
        }

    # ==================================================================
    # Envoi
    # ==================================================================
    def _send(self):
        """Envoie les publications de ``self``. N'échoue jamais bruyamment."""
        for record in self:
            if record.state in ("sent", "cancelled"):
                continue
            if not record.message:
                record.message = self._render_message(record.post_id, record.channel_id)
            result = self._transport_send(record.channel_id, record._payload())
            if result.get("ok"):
                record.write({
                    "state": "sent",
                    "sent_date": fields.Datetime.now(),
                    "remote_id": result.get("remote_id") or False,
                    "error": False,
                    "retry_count": record.retry_count + 1,
                })
            else:
                record.write({
                    "state": "error",
                    "error": result.get("error") or _("Erreur inconnue."),
                    "retry_count": record.retry_count + 1,
                })
        return True

    def action_send_now(self):
        for record in self:
            if record.state == "cancelled":
                raise UserError(_("Cette publication est annulée : remettez-la en file."))
        self._send()
        return True

    def action_requeue(self):
        self.write({"state": "queued", "error": False, "retry_count": 0})
        return True

    def action_cancel(self):
        self.filtered(lambda r: r.state != "sent").write({"state": "cancelled"})
        return True

    def action_view_post(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "blog.post",
            "res_id": self.post_id.id,
            "view_mode": "form",
        }

    # ==================================================================
    # Tâche planifiée
    # ==================================================================
    @api.model
    def _cron_process_queue(self, limit=100):
        """Traite la file d'attente : ``queued`` dus, puis ``error`` rejouables."""
        now = fields.Datetime.now()
        domain = [
            "&",
            "|",
            ("state", "=", "queued"),
            "&", ("state", "=", "error"), ("retry_count", "<", MAX_RETRY),
            "|", ("scheduled_date", "=", False), ("scheduled_date", "<=", now),
        ]
        records = self.search(domain, limit=limit, order="id asc")
        records = records.filtered(lambda r: r.retry_count < MAX_RETRY)
        for record in records:
            try:
                with self.env.cr.savepoint():
                    record._send()
            except Exception as error:  # noqa: BLE001
                _logger.exception("Blog to Social: échec du traitement de %s", record.id)
                record.write({"state": "error", "error": str(error)})
        return len(records)
