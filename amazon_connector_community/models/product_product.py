# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    amazon_sync = fields.Boolean(
        string="Synchroniser avec Amazon", default=False,
        help="Envoie la quantité disponible et le prix de cet article vers Amazon.")


class ProductProduct(models.Model):
    _inherit = "product.product"

    amazon_sku = fields.Char(
        string="SKU Amazon", index=True,
        help="SKU vendeur utilisé sur Amazon. Vide, la référence interne est utilisée.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("amazon_sku") and vals.get("default_code"):
                vals["amazon_sku"] = vals["default_code"]
        return super().create(vals_list)

    def _amazon_effective_sku(self):
        """SKU réellement envoyé à Amazon."""
        self.ensure_one()
        return self.amazon_sku or self.default_code or False
