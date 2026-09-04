# -*- coding: utf-8 -*-
import base64
import logging
import time

from odoo import _, fields, models

from .packlink_api import PacklinkApiError

_logger = logging.getLogger(__name__)

# Correspondance des noms de transporteurs attendus par Amazon dans la
# confirmation d'expédition : Amazon rejette un nom inconnu, alors que
# Packlink renvoie le nom commercial du transporteur.
AMAZON_CARRIER_MAP = {
    "chronopost": "Chronopost",
    "colissimo": "Colissimo",
    "la poste": "La Poste",
    "mondial relay": "Mondial Relay",
    "dhl": "DHL",
    "dpd": "DPD",
    "gls": "GLS",
    "ups": "UPS",
    "fedex": "FedEx",
    "tnt": "TNT",
    "seur": "SEUR",
    "correos": "Correos",
    "brt": "BRT",
    "hermes": "Hermes",
    "evri": "Evri",
    "poste italiane": "Poste Italiane",
    "nacex": "Nacex",
    "ctt": "CTT",
}


class StockPicking(models.Model):
    _inherit = "stock.picking"

    packlink_shipment_ref = fields.Char(
        string="Expédition Packlink", copy=False, readonly=True, index="btree_not_null")
    packlink_carrier_name = fields.Char(
        string="Transporteur Packlink", copy=False, readonly=True)
    packlink_service_name = fields.Char(
        string="Service Packlink", copy=False, readonly=True)
    packlink_tracking_url = fields.Char(string="Lien de suivi", copy=False, readonly=True)
    packlink_state = fields.Char(string="État Packlink", copy=False, readonly=True)
    packlink_label_id = fields.Many2one(
        "ir.attachment", string="Étiquette", copy=False, readonly=True)

    def _packlink_declared_value(self):
        """Valeur déclarée du colis, plafonnée : Packlink refuse les valeurs nulles."""
        self.ensure_one()
        order = self.sale_id
        if order:
            return max(order.amount_untaxed, 1.0)
        total = sum((move.product_id.standard_price or 0.0) * (move.quantity or 0.0)
                    for move in self.move_ids)
        return max(total, 1.0)

    def _packlink_fetch_label(self, api=None):
        """Récupère l'étiquette PDF et la joint au transfert."""
        self.ensure_one()
        if not self.packlink_shipment_ref:
            return False
        carrier = self.carrier_id
        started = time.time()
        try:
            api = api or carrier._packlink_account()._api()
            urls = api.get_labels(self.packlink_shipment_ref)
            if not urls:
                raise PacklinkApiError(_("Aucune étiquette disponible pour le moment."))
            content = api.download(urls[0])
        except PacklinkApiError as exc:
            # L'étiquette peut n'être prête que quelques secondes plus tard :
            # on trace sans faire échouer la validation du transfert.
            carrier._packlink_log("label", "error", time.time() - started, exc, picking=self,
                                  shipment_ref=self.packlink_shipment_ref)
            self.message_post(body=_("Étiquette Packlink non récupérée : %s") % exc)
            return False
        attachment = self.env["ir.attachment"].create({
            "name": "packlink-%s.pdf" % self.packlink_shipment_ref,
            "type": "binary",
            "datas": base64.b64encode(content),
            "mimetype": "application/pdf",
            "res_model": "stock.picking",
            "res_id": self.id,
        })
        self.write({"packlink_label_id": attachment.id})
        carrier._packlink_log("label", "ok", time.time() - started, picking=self,
                              shipment_ref=self.packlink_shipment_ref)
        return attachment

    def action_packlink_get_label(self):
        for picking in self:
            picking._packlink_fetch_label()
        return True

    def action_packlink_refresh_tracking(self):
        for picking in self.filtered("packlink_shipment_ref"):
            picking._packlink_refresh_tracking()
        return True

    def _packlink_refresh_tracking(self):
        self.ensure_one()
        carrier = self.carrier_id
        if not carrier or carrier.delivery_type != "packlink":
            return False
        started = time.time()
        try:
            api = carrier._packlink_account()._api()
            events = api.get_tracking(self.packlink_shipment_ref)
            shipment = api.get_shipment(self.packlink_shipment_ref) or {}
        except PacklinkApiError as exc:
            carrier._packlink_log("track", "error", time.time() - started, exc, picking=self,
                                  shipment_ref=self.packlink_shipment_ref)
            return False
        values = {}
        state = shipment.get("state") or shipment.get("status")
        if state and state != self.packlink_state:
            values["packlink_state"] = state
        url = shipment.get("tracking_url") or shipment.get("trackingurl")
        if url and url != self.packlink_tracking_url:
            values["packlink_tracking_url"] = url
        if values:
            self.write(values)
        if events:
            last = events[-1]
            self.message_post(body=_(
                "Suivi Packlink : %(status)s — %(date)s",
                status=last.get("description") or last.get("status") or state or "",
                date=last.get("timestamp") or last.get("date") or ""))
        carrier._packlink_log("track", "ok", time.time() - started, picking=self,
                              shipment_ref=self.packlink_shipment_ref)
        return True

    def _cron_packlink_refresh_tracking(self, limit=200):
        """Rafraîchit les expéditions encore en cours."""
        pickings = self.search([
            ("packlink_shipment_ref", "!=", False),
            ("state", "=", "done"),
            ("packlink_state", "not in", ("DELIVERED", "CANCELLED", "RETURNED")),
        ], limit=limit)
        for picking in pickings:
            try:
                picking._packlink_refresh_tracking()
            except Exception:  # noqa: BLE001 - une expédition ne bloque pas les suivantes
                _logger.exception("Suivi Packlink impossible pour %s", picking.name)
        return True

    # ------------------------------------------------------------------
    # Pont avec le connecteur Amazon Community
    # ------------------------------------------------------------------
    def _amazon_carrier_name(self):
        """Le nom du transporteur réel Packlink, normalisé pour Amazon.

        Surcharge le point d'extension du module ``amazon_connector_community``
        quand il est installé ; sans lui, la méthode n'est jamais appelée.
        """
        self.ensure_one()
        name = self.packlink_carrier_name or ""
        lowered = name.lower()
        for needle, amazon_name in AMAZON_CARRIER_MAP.items():
            if needle in lowered:
                return amazon_name
        # Amazon accepte un nom de transporteur libre : mieux vaut le nom réel
        # renvoyé par Packlink que le « Other » générique.
        if name:
            return name
        if hasattr(super(), "_amazon_carrier_name"):
            return super()._amazon_carrier_name()
        return "Other"
