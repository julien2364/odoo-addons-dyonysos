# -*- coding: utf-8 -*-
"""Déclenchement des publications sociales depuis les articles de blog."""

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

ACTIVATION_PARAM = "blog_social_publish.activation_date"
AUTO_PUBLISH_PARAM = "blog_social_publish.auto_publish"


class BlogPost(models.Model):
    _inherit = "blog.post"

    social_post_ids = fields.One2many(
        "blog.social.post", "post_id", string="Publications sociales")
    social_post_count = fields.Integer(
        string="Publications sociales", compute="_compute_social_post_count")
    social_state = fields.Selection(
        [
            ("none", "Aucune"),
            ("queued", "En file"),
            ("sent", "Envoyé"),
            ("error", "Erreur"),
        ],
        string="État social", compute="_compute_social_post_count",
        help="Synthèse de l'état des publications sociales de cet article.")

    @api.depends("social_post_ids.state")
    def _compute_social_post_count(self):
        for post in self:
            posts = post.social_post_ids
            post.social_post_count = len(posts)
            states = set(posts.mapped("state"))
            if not states:
                post.social_state = "none"
            elif "error" in states:
                post.social_state = "error"
            elif states & {"draft", "queued"}:
                post.social_state = "queued"
            elif "sent" in states:
                post.social_state = "sent"
            else:
                post.social_state = "none"

    # ------------------------------------------------------------------
    # Garde-fous
    # ------------------------------------------------------------------
    @api.model
    def _social_activation_date(self):
        """Date à partir de laquelle un article peut être publié socialement."""
        raw = self.env["ir.config_parameter"].sudo().get_param(ACTIVATION_PARAM)
        if not raw:
            return False
        try:
            return fields.Datetime.to_datetime(raw)
        except (ValueError, TypeError):
            _logger.warning("Blog to Social: date d'activation illisible (%r).", raw)
            return False

    @api.model
    def _social_auto_publish_enabled(self):
        param = self.env["ir.config_parameter"].sudo().get_param(AUTO_PUBLISH_PARAM)
        return str(param).strip().lower() in ("1", "true", "yes", "on")

    def _social_publication_date(self):
        """Date de publication retenue pour comparer à la date d'activation."""
        self.ensure_one()
        return self.post_date or self.published_date or self.create_date

    def _social_is_recent(self):
        """L'article est-il postérieur à l'activation du module ?

        Garde-fou capital : une instance peut compter des milliers d'articles
        déjà publiés ; ils ne doivent jamais partir rétroactivement.
        """
        self.ensure_one()
        activation = self.env["blog.post"]._social_activation_date()
        if not activation:
            return True
        published = self._social_publication_date()
        if not published:
            return True
        return published >= activation

    # ------------------------------------------------------------------
    # Mise en file
    # ------------------------------------------------------------------
    def _blog_social_enqueue(self, manual=False):
        """Crée les publications sociales manquantes pour ``self``.

        En mode automatique, les deux garde-fous s'appliquent ; en mode manuel
        (bouton), l'utilisateur a explicitement demandé la publication.
        """
        social = self.env["blog.social.post"]
        created = social.browse()
        if not manual and not self._social_auto_publish_enabled():
            return created
        for post in self:
            if not post.is_published:
                continue
            if not manual and not post._social_is_recent():
                _logger.info(
                    "Blog to Social: article %s ignoré (publié avant l'activation).", post.id)
                continue
            channels = self.env["blog.social.channel"]._channels_for_post(post)
            if not channels:
                continue
            created |= social._create_for_post(post, channels)
        return created

    @api.model_create_multi
    def create(self, vals_list):
        posts = super().create(vals_list)
        published = posts.filtered("is_published")
        if published:
            published._blog_social_enqueue()
        return posts

    def write(self, vals):
        newly = self.browse()
        if "is_published" in vals and vals.get("is_published"):
            newly = self.filtered(lambda p: not p.is_published)
        result = super().write(vals)
        if newly:
            newly._blog_social_enqueue()
        return result

    # ------------------------------------------------------------------
    # Bouton d'en-tête
    # ------------------------------------------------------------------
    def action_blog_social_publish(self):
        """Publie manuellement l'article sur les réseaux configurés."""
        self.ensure_one()
        if not self.is_published:
            raise UserError(_("Publiez d'abord l'article sur le site web."))
        channels = self.env["blog.social.channel"]._channels_for_post(self)
        if not channels:
            raise UserError(_(
                "Aucun canal de publication ne correspond à ce blog. "
                "Créez-en un depuis Blog to Social › Canaux."))
        self._blog_social_enqueue(manual=True)
        return {
            "type": "ir.actions.act_window",
            "name": _("Publications sociales"),
            "res_model": "blog.social.post",
            "view_mode": "list,form",
            "domain": [("post_id", "=", self.id)],
            "context": {"default_post_id": self.id},
        }

    def action_view_social_posts(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Publications sociales"),
            "res_model": "blog.social.post",
            "view_mode": "list,form",
            "domain": [("post_id", "=", self.id)],
        }
