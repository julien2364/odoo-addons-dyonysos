# -*- coding: utf-8 -*-
import logging
import time

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .packlink_api import PacklinkApiError

_logger = logging.getLogger(__name__)

# Dimensions repli quand le produit ne porte pas les siennes : un colis
# standard, plutôt que de laisser Packlink refuser la demande de tarif.
FALLBACK_PARCEL = {"weight": 1.0, "length": 30.0, "width": 20.0, "height": 15.0}


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    delivery_type = fields.Selection(
        selection_add=[("packlink", "Packlink PRO")],
        ondelete={"packlink": "set default"})
    packlink_account_id = fields.Many2one("packlink.account", string="Compte Packlink")
    packlink_service_id = fields.Char(
        string="Service imposé",
        help="Identifiant de service Packlink à utiliser systématiquement. "
             "Laisser vide pour laisser le module choisir selon le compte "
             "(le moins cher ou le plus rapide).")
    packlink_default_weight = fields.Float(
        string="Poids par défaut (kg)", default=1.0,
        help="Utilisé quand aucun produit de l'envoi ne porte de poids.")
    packlink_length = fields.Float(string="Longueur (cm)", default=30.0)
    packlink_width = fields.Float(string="Largeur (cm)", default=20.0)
    packlink_height = fields.Float(string="Hauteur (cm)", default=15.0)
    packlink_label_format = fields.Selection(
        [("pdf", "PDF")], string="Format d'étiquette", default="pdf")

    # ------------------------------------------------------------------
    # Utilitaires
    # ------------------------------------------------------------------
    def _packlink_account(self):
        self.ensure_one()
        account = self.packlink_account_id or self.env["packlink.account"]._default_account(
            self.company_id or self.env.company)
        if not account:
            raise UserError(_("Aucun compte Packlink n'est configuré pour ce mode de livraison."))
        return account

    def _packlink_log(self, operation, state, duration, message=False, picking=False,
                      shipment_ref=False):
        """Le journal ne doit jamais faire échouer l'opération qu'il trace."""
        try:
            self.env["packlink.log"].sudo().create({
                "account_id": self.packlink_account_id.id or False,
                "operation": operation,
                "state": state,
                "duration": duration,
                "message": message and str(message)[:2000] or False,
                "picking_id": picking and picking.id or False,
                "shipment_ref": shipment_ref or False,
            })
        except Exception:  # noqa: BLE001 - journal best effort
            _logger.exception("Écriture du journal Packlink impossible")

    def _packlink_address(self, partner, fallback=None):
        partner = partner or fallback
        if not partner:
            return {}
        street = " ".join(filter(None, [partner.street, partner.street2]))
        return {
            "name": partner.name or "",
            "surname": "",
            "company": partner.commercial_company_name or "",
            "street1": street or "",
            "city": partner.city or "",
            "zip": partner.zip or "",
            "country": (partner.country_id.code or "").upper(),
            "state": partner.state_id.name or "",
            "phone": partner.phone or "",
            "email": partner.email or "",
        }

    def _packlink_parcels_from_weight(self, weight):
        self.ensure_one()
        return [{
            "weight": round(weight or self.packlink_default_weight or FALLBACK_PARCEL["weight"], 3),
            "length": self.packlink_length or FALLBACK_PARCEL["length"],
            "width": self.packlink_width or FALLBACK_PARCEL["width"],
            "height": self.packlink_height or FALLBACK_PARCEL["height"],
        }]

    @staticmethod
    def _packlink_service_price(service):
        for key in ("price", "total_price", "base_price"):
            value = service.get(key)
            if isinstance(value, dict):
                value = value.get("total_price") or value.get("base_price") or value.get("value")
            if value not in (None, False, ""):
                try:
                    return float(value)
                except (TypeError, ValueError):
                    continue
        return None

    @staticmethod
    def _packlink_service_transit(service):
        for key in ("transit_time", "transit_hours", "delivery_time"):
            value = service.get(key)
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                digits = "".join(c for c in value if c.isdigit())
                if digits:
                    return float(digits)
        return 9999.0

    def _packlink_pick_service(self, services):
        """Retient le service imposé, sinon le moins cher / le plus rapide."""
        self.ensure_one()
        priced = [(s, self._packlink_service_price(s)) for s in services]
        priced = [(s, p) for s, p in priced if p is not None]
        if not priced:
            return None, None
        if self.packlink_service_id:
            for service, price in priced:
                if str(service.get("id") or service.get("service_id") or "") == \
                        str(self.packlink_service_id):
                    return service, price
            return None, None
        account = self._packlink_account()
        if account.postage_type == "fastest":
            service, price = min(priced, key=lambda sp: self._packlink_service_transit(sp[0]))
        else:
            service, price = min(priced, key=lambda sp: sp[1])
        return service, price

    @staticmethod
    def _packlink_carrier_label(service):
        return (service.get("carrier_name") or service.get("carrier")
                or service.get("name") or "Packlink")

    # ------------------------------------------------------------------
    # API transporteur Odoo
    # ------------------------------------------------------------------
    def packlink_rate_shipment(self, order):
        self.ensure_one()
        started = time.time()
        try:
            account = self._packlink_account()
            sender = account.warehouse_partner_id or \
                order.warehouse_id.partner_id or order.company_id.partner_id
            recipient = order.partner_shipping_id or order.partner_id
            weight = sum((line.product_id.weight or 0.0) * line.product_uom_qty
                         for line in order.order_line
                         if line.product_id and not line.is_delivery
                         and line.product_id.type == "consu")
            services = account._api().get_services(
                self._packlink_address(sender), self._packlink_address(recipient),
                self._packlink_parcels_from_weight(weight))
            service, price = self._packlink_pick_service(services)
        except (PacklinkApiError, UserError) as exc:
            self._packlink_log("rate", "error", time.time() - started, exc)
            return {"success": False, "price": 0.0,
                    "error_message": _("Packlink : %s") % exc, "warning_message": False}
        self._packlink_log("rate", "ok", time.time() - started,
                           _("%s service(s) proposé(s)") % len(services))
        if not service:
            return {"success": False, "price": 0.0,
                    "error_message": _("Packlink ne propose aucun service pour cette destination."),
                    "warning_message": False}
        price = self._packlink_apply_margins(price, order.currency_id, order.company_id)
        return {"success": True, "price": price, "error_message": False,
                "warning_message": False}

    def _packlink_apply_margins(self, price, currency, company):
        """Applique la marge et le change du mode de livraison Odoo."""
        self.ensure_one()
        price = float(price or 0.0)
        company = company or self.env.company
        if self.company_id and self.company_id.currency_id and currency \
                and currency != self.company_id.currency_id:
            price = self.company_id.currency_id._convert(
                price, currency, company, fields.Date.context_today(self))
        return price * (1.0 + (self.margin or 0.0) / 100.0) + (self.fixed_margin or 0.0)

    def packlink_send_shipping(self, pickings):
        return [self._packlink_send_one(picking) for picking in pickings]

    def _packlink_send_one(self, picking):
        self.ensure_one()
        started = time.time()
        account = self._packlink_account()
        api = account._api()
        order = picking.sale_id
        sender = account.warehouse_partner_id or picking.picking_type_id.warehouse_id.partner_id \
            or picking.company_id.partner_id
        recipient = picking.partner_id or (order and order.partner_shipping_id)
        parcels = self._packlink_parcels_from_weight(picking.shipping_weight or picking.weight)
        try:
            services = api.get_services(self._packlink_address(sender),
                                        self._packlink_address(recipient), parcels)
            service, price = self._packlink_pick_service(services)
            if not service:
                raise PacklinkApiError(
                    _("Aucun service Packlink disponible pour cette expédition."))
            payload = {
                "service_id": service.get("id") or service.get("service_id"),
                "from": self._packlink_address(sender),
                "to": self._packlink_address(recipient),
                "packages": parcels,
                "content": (picking.name or "")[:64],
                "contentvalue": round(picking._packlink_declared_value(), 2),
                "additional_data": {
                    "customer_reference": order.name if order else picking.name,
                },
            }
            result = api.create_shipment(payload) or {}
        except (PacklinkApiError, UserError) as exc:
            self._packlink_log("ship", "error", time.time() - started, exc, picking=picking)
            raise UserError(_("Packlink : %s") % exc)
        reference = str(result.get("reference") or result.get("shipment_id")
                        or result.get("id") or "")
        if not reference:
            self._packlink_log("ship", "error", time.time() - started,
                               _("Réponse sans référence d'expédition"), picking=picking)
            raise UserError(_("Packlink n'a pas retourné de référence d'expédition."))
        tracking = str(result.get("tracking_number") or result.get("trackingnumber") or "") \
            or reference
        picking.write({
            "packlink_shipment_ref": reference,
            "packlink_carrier_name": self._packlink_carrier_label(service),
            "packlink_service_name": service.get("name") or "",
            "carrier_tracking_ref": tracking,
        })
        self._packlink_log("ship", "ok", time.time() - started, picking=picking,
                           shipment_ref=reference)
        picking._packlink_fetch_label(api)
        picking.message_post(body=_(
            "Expédition Packlink %(ref)s créée (%(carrier)s), suivi %(tracking)s.",
            ref=reference, carrier=self._packlink_carrier_label(service), tracking=tracking))
        return {"exact_price": self._packlink_apply_margins(
            price, picking.company_id.currency_id, picking.company_id),
            "tracking_number": tracking}

    def packlink_get_tracking_link(self, picking):
        self.ensure_one()
        if picking.packlink_tracking_url:
            return picking.packlink_tracking_url
        if picking.packlink_shipment_ref:
            return "https://pro.packlink.fr/private/shipments/%s" % picking.packlink_shipment_ref
        return False

    def packlink_cancel_shipment(self, pickings):
        for picking in pickings:
            if not picking.packlink_shipment_ref:
                continue
            started = time.time()
            try:
                self._packlink_account()._api().cancel_shipment(picking.packlink_shipment_ref)
            except PacklinkApiError as exc:
                self._packlink_log("cancel", "error", time.time() - started, exc, picking=picking,
                                   shipment_ref=picking.packlink_shipment_ref)
                raise UserError(_("Annulation Packlink refusée : %s") % exc)
            self._packlink_log("cancel", "ok", time.time() - started, picking=picking,
                               shipment_ref=picking.packlink_shipment_ref)
            picking.message_post(body=_("Expédition Packlink %s annulée.",
                                        picking.packlink_shipment_ref))
            picking.write({"carrier_tracking_ref": False, "packlink_state": "cancelled"})

    @api.onchange("delivery_type")
    def _onchange_delivery_type_packlink(self):
        for carrier in self:
            if carrier.delivery_type == "packlink" and not carrier.packlink_account_id:
                carrier.packlink_account_id = self.env["packlink.account"]._default_account(
                    carrier.company_id or self.env.company)
