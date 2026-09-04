# -*- coding: utf-8 -*-
from odoo import _, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    blog_social_auto_publish = fields.Boolean(
        string="Publier automatiquement les nouveaux articles",
        config_parameter="blog_social_publish.auto_publish",
        help="Décoché, rien ne part tout seul : seul le bouton « Publier sur les "
             "réseaux » de l'article agit.")
    blog_social_activation_date = fields.Char(
        string="Date d'activation", readonly=True,
        config_parameter="blog_social_publish.activation_date",
        help="Figée à l'installation. Aucun article publié avant cette date "
             "n'est jamais poussé automatiquement.")
    blog_social_timeout = fields.Integer(
        string="Délai réseau (s)", config_parameter="blog_social_publish.timeout",
        default=20)

    def action_blog_social_open_channels(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Canaux de publication"),
            "res_model": "blog.social.channel",
            "view_mode": "list,form",
        }
