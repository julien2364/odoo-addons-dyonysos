# -*- coding: utf-8 -*-
"""Hooks d'installation de Blog to Social."""

import logging

from odoo import fields

_logger = logging.getLogger(__name__)

ACTIVATION_PARAM = "blog_social_publish.activation_date"
AUTO_PUBLISH_PARAM = "blog_social_publish.auto_publish"


def post_init_hook(env):
    """Fige la date d'activation à l'installation du module.

    Garde-fou capital : une instance existante peut contenir des milliers
    d'articles déjà publiés. Aucun article publié avant cette date ne sera
    jamais poussé automatiquement vers les réseaux sociaux.
    """
    params = env["ir.config_parameter"].sudo()
    if not params.get_param(ACTIVATION_PARAM):
        params.set_param(ACTIVATION_PARAM, fields.Datetime.to_string(fields.Datetime.now()))
        _logger.info(
            "Blog to Social: date d'activation figée à %s ; "
            "les articles publiés avant cette date sont ignorés.",
            params.get_param(ACTIVATION_PARAM),
        )
    if params.get_param(AUTO_PUBLISH_PARAM) is False:
        params.set_param(AUTO_PUBLISH_PARAM, "False")
