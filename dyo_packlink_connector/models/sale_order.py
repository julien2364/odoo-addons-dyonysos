# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    packlink_shipment_ref = fields.Char(
        string="Expédition Packlink", compute="_compute_packlink_shipment_ref")

    def _compute_packlink_shipment_ref(self):
        for order in self:
            refs = order.picking_ids.filtered("packlink_shipment_ref").mapped(
                "packlink_shipment_ref")
            order.packlink_shipment_ref = ", ".join(refs) if refs else False
