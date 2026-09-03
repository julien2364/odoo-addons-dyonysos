# -*- coding: utf-8 -*-
from odoo import fields, models


class AmazonMarketplaceCommunity(models.Model):
    _name = "amazon.marketplace.community"
    _description = "Place de marché Amazon"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=False)
    sequence = fields.Integer(default=10)
    country_code = fields.Char(
        string="Code pays", required=True, size=2,
        help="Code ISO du pays de la place de marché (FR, DE, ...)")
    marketplace_id = fields.Char(
        string="Marketplace ID", required=True,
        help="Identifiant Amazon de la place de marché, par exemple A13V1IB3VIYZZH pour la France.")
    currency_id = fields.Many2one("res.currency", string="Devise")
    domain_name = fields.Char(string="Domaine")
    active = fields.Boolean(default=True)

    _amazon_marketplace_uniq = models.Constraint(
        "UNIQUE(marketplace_id)",
        "Cette place de marché Amazon existe déjà.",
    )

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = "%s (%s)" % (rec.name, rec.country_code or "")
