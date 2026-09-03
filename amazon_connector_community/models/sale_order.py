# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    amazon_order_ref = fields.Char(
        string="Référence Amazon", index=True, copy=False, readonly=True,
        help="Identifiant de la commande sur Amazon (AmazonOrderId).")
    amazon_account_id = fields.Many2one(
        "amazon.account.community", string="Compte Amazon", copy=False, readonly=True)
    amazon_marketplace_id = fields.Many2one(
        "amazon.marketplace.community", string="Place de marché Amazon",
        copy=False, readonly=True)

    _amazon_order_ref_uniq = models.Constraint(
        "UNIQUE(amazon_order_ref)",
        "Cette commande Amazon a déjà été importée.",
    )


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    amazon_item_ref = fields.Char(string="Référence ligne Amazon", copy=False, readonly=True)
    is_amazon_shipping = fields.Boolean(string="Frais de port Amazon", default=False, copy=False)


class ResPartner(models.Model):
    _inherit = "res.partner"

    amazon_buyer_email = fields.Char(string="Email acheteur Amazon", index=True, copy=False)
    amazon_marketplace_id = fields.Many2one(
        "amazon.marketplace.community", string="Place de marché Amazon", copy=False)
