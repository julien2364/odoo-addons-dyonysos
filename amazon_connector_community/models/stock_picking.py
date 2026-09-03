# -*- coding: utf-8 -*-
from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    amazon_tracking_sent = fields.Boolean(
        string="Suivi envoyé à Amazon", default=False, copy=False, readonly=True)
    amazon_tracking_date = fields.Datetime(
        string="Date d'envoi du suivi", copy=False, readonly=True)

    def _amazon_tracking_reference(self):
        """Numéro de suivi, quel que soit le module transporteur installé."""
        self.ensure_one()
        if "carrier_tracking_ref" in self._fields:
            return self.carrier_tracking_ref or False
        return False

    def _amazon_carrier_name(self):
        self.ensure_one()
        if "carrier_id" in self._fields and self.carrier_id:
            return self.carrier_id.name
        return "Other"

    def _amazon_shipment_payload(self):
        """Charge utile de confirmation d'expédition SP-API, ou False."""
        self.ensure_one()
        order = self.sale_id
        if not order or not order.amazon_order_ref:
            return False
        tracking = self._amazon_tracking_reference()
        if not tracking:
            return False
        items = []
        for move in self.move_ids.filtered(lambda m: m.state == "done"):
            line = move.sale_line_id
            if not line or not line.amazon_item_ref:
                continue
            items.append({
                "orderItemId": line.amazon_item_ref,
                "quantity": int(move.quantity or move.product_uom_qty or 0),
            })
        return {
            "packageDetail": {
                "packageReferenceId": self.name,
                "carrierName": self._amazon_carrier_name(),
                "trackingNumber": tracking,
                "shipDate": fields.Datetime.to_string(
                    self.date_done or fields.Datetime.now()).replace(" ", "T") + "Z",
                "orderItems": items,
            },
            "marketplaceId": order.amazon_marketplace_id.marketplace_id or "",
        }

    def button_validate(self):
        result = super().button_validate()
        pickings = self.filtered(
            lambda p: p.state == "done" and p.sale_id.amazon_order_ref
            and not p.amazon_tracking_sent)
        for picking in pickings:
            account = picking.sale_id.amazon_account_id
            if account and picking._amazon_tracking_reference():
                account._push_tracking()
        return result
