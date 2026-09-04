# -*- coding: utf-8 -*-
"""Tests du connecteur Packlink : tout le réseau est simulé."""
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from odoo.addons.dyo_packlink_connector.models.packlink_api import PacklinkApi, PacklinkApiError

SERVICES = [
    {"id": "1001", "name": "Chronopost Express", "carrier_name": "Chronopost",
     "price": {"total_price": 14.90}, "transit_time": "24"},
    {"id": "1002", "name": "Colissimo Domicile", "carrier_name": "Colissimo",
     "price": {"total_price": 8.50}, "transit_time": "48"},
    {"id": "1003", "name": "GLS Point Relais", "carrier_name": "GLS",
     "price": {"total_price": 6.20}, "transit_time": "72"},
]
LABEL_PDF = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, content=b"", text=""):
        self.status_code = status_code
        self._json = json_data
        self.content = content or (b"{}" if json_data is not None else b"")
        self.text = text

    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json


@tagged("post_install", "-at_install")
class TestPacklinkConnector(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account = cls.env["packlink.account"].create({
            "name": "Packlink Test", "api_key": "test-key",
        })
        cls.product = cls.env["product.product"].create({
            "name": "Pierre gravee", "type": "consu", "is_storable": True,
            "weight": 0.8, "list_price": 29.0, "standard_price": 10.0,
        })
        cls.customer = cls.env["res.partner"].create({
            "name": "Client Lyon", "street": "10 rue de la Republique", "city": "Lyon",
            "zip": "69001", "country_id": cls.env.ref("base.fr").id,
            "email": "client@example.com", "phone": "+33600000000",
        })
        cls.carrier = cls.env["delivery.carrier"].create({
            "name": "Packlink", "delivery_type": "packlink",
            "packlink_account_id": cls.account.id,
            "product_id": cls.env["product.product"].create({
                "name": "Livraison Packlink", "type": "service"}).id,
        })
        cls.order = cls.env["sale.order"].create({
            "partner_id": cls.customer.id,
            "order_line": [Command.create({"product_id": cls.product.id, "product_uom_qty": 2})],
        })

    # ------------------------------------------------------------------
    # Couche API
    # ------------------------------------------------------------------
    def test_01_auth_header_without_scheme(self):
        api = PacklinkApi("abc")
        self.assertEqual(api._headers()["Authorization"], "abc")
        self.assertEqual(PacklinkApi("abc", auth_scheme="Bearer")._headers()["Authorization"],
                         "Bearer abc")

    def test_02_missing_key_is_refused(self):
        with self.assertRaises(PacklinkApiError):
            PacklinkApi("")

    def test_03_http_error_is_readable(self):
        api = PacklinkApi("abc")
        response = FakeResponse(status_code=401, json_data={"message": "Invalid API key"})
        with patch("odoo.addons.dyo_packlink_connector.models.packlink_api.requests.request",
                   return_value=response):
            with self.assertRaises(PacklinkApiError) as err:
                api.get_services({"country": "FR", "zip": "75001"},
                                 {"country": "FR", "zip": "69001"}, [{"weight": 1}])
        self.assertIn("Invalid API key", str(err.exception))
        self.assertIn("401", str(err.exception))

    def test_04_server_error_is_retried_then_raised(self):
        api = PacklinkApi("abc")
        response = FakeResponse(status_code=503, text="down")
        with patch("odoo.addons.dyo_packlink_connector.models.packlink_api.time.sleep"), \
             patch("odoo.addons.dyo_packlink_connector.models.packlink_api.requests.request",
                   return_value=response) as request:
            with self.assertRaises(PacklinkApiError):
                api.get_shipment("REF")
        self.assertEqual(request.call_count, 3)

    def test_05_services_payload_flattens_packages(self):
        api = PacklinkApi("abc")
        with patch("odoo.addons.dyo_packlink_connector.models.packlink_api.requests.request",
                   return_value=FakeResponse(json_data={"services": SERVICES})) as request:
            services = api.get_services({"country": "FR", "zip": "75001"},
                                        {"country": "ES", "zip": "08001"},
                                        [{"weight": 2, "length": 30, "width": 20, "height": 10}])
        params = request.call_args.kwargs["params"]
        self.assertEqual(params["to[country]"], "ES")
        self.assertEqual(params["packages[0][weight]"], 2)
        self.assertEqual(len(services), 3)

    # ------------------------------------------------------------------
    # Choix du service
    # ------------------------------------------------------------------
    def test_06_cheapest_service_wins_by_default(self):
        service, price = self.carrier._packlink_pick_service(SERVICES)
        self.assertEqual(service["carrier_name"], "GLS")
        self.assertEqual(price, 6.20)

    def test_07_fastest_service_when_configured(self):
        self.account.postage_type = "fastest"
        service, _price = self.carrier._packlink_pick_service(SERVICES)
        self.assertEqual(service["carrier_name"], "Chronopost")

    def test_08_forced_service_is_honoured(self):
        self.carrier.packlink_service_id = "1002"
        service, price = self.carrier._packlink_pick_service(SERVICES)
        self.assertEqual(service["carrier_name"], "Colissimo")
        self.assertEqual(price, 8.50)
        self.carrier.packlink_service_id = "9999"
        self.assertEqual(self.carrier._packlink_pick_service(SERVICES), (None, None))

    def test_09_rate_shipment_applies_the_margin(self):
        self.carrier.margin = 10.0
        self.carrier.fixed_margin = 1.0
        with patch.object(PacklinkApi, "get_services", return_value=SERVICES):
            result = self.carrier.packlink_rate_shipment(self.order)
        self.assertTrue(result["success"])
        self.assertAlmostEqual(result["price"], 6.20 * 1.1 + 1.0, places=2)

    def test_10_rate_shipment_reports_the_api_error(self):
        with patch.object(PacklinkApi, "get_services",
                          side_effect=PacklinkApiError("Zone non desservie")):
            result = self.carrier.packlink_rate_shipment(self.order)
        self.assertFalse(result["success"])
        self.assertIn("Zone non desservie", result["error_message"])
        self.assertTrue(self.env["packlink.log"].search(
            [("operation", "=", "rate"), ("state", "=", "error")], limit=1))

    def test_11_rate_shipment_without_service(self):
        with patch.object(PacklinkApi, "get_services", return_value=[]):
            result = self.carrier.packlink_rate_shipment(self.order)
        self.assertFalse(result["success"])

    # ------------------------------------------------------------------
    # Expédition
    # ------------------------------------------------------------------
    def _confirm(self):
        self.order.set_delivery_line(self.carrier, 6.20)
        self.order.action_confirm()
        return self.order.picking_ids[:1]

    def test_12_send_shipping_creates_the_shipment_and_the_label(self):
        with patch.object(PacklinkApi, "get_services", return_value=SERVICES):
            picking = self._confirm()
        with patch.object(PacklinkApi, "get_services", return_value=SERVICES), \
             patch.object(PacklinkApi, "create_shipment",
                          return_value={"reference": "PKL-123", "tracking_number": "TRK-9"}), \
             patch.object(PacklinkApi, "get_labels", return_value=["https://label.example/1.pdf"]), \
             patch.object(PacklinkApi, "download", return_value=LABEL_PDF):
            result = self.carrier.packlink_send_shipping(picking)
        self.assertEqual(result[0]["tracking_number"], "TRK-9")
        self.assertEqual(picking.packlink_shipment_ref, "PKL-123")
        self.assertEqual(picking.packlink_carrier_name, "GLS")
        self.assertEqual(picking.carrier_tracking_ref, "TRK-9")
        self.assertTrue(picking.packlink_label_id)
        self.assertEqual(picking.packlink_label_id.mimetype, "application/pdf")

    def test_13_shipment_without_reference_is_refused(self):
        with patch.object(PacklinkApi, "get_services", return_value=SERVICES):
            picking = self._confirm()
        with patch.object(PacklinkApi, "get_services", return_value=SERVICES), \
             patch.object(PacklinkApi, "create_shipment", return_value={"status": "ok"}):
            with self.assertRaises(UserError):
                self.carrier.packlink_send_shipping(picking)
        self.assertFalse(picking.packlink_shipment_ref)

    def test_14_a_missing_label_does_not_break_the_shipment(self):
        with patch.object(PacklinkApi, "get_services", return_value=SERVICES):
            picking = self._confirm()
        with patch.object(PacklinkApi, "get_services", return_value=SERVICES), \
             patch.object(PacklinkApi, "create_shipment", return_value={"reference": "PKL-124"}), \
             patch.object(PacklinkApi, "get_labels", return_value=[]):
            self.carrier.packlink_send_shipping(picking)
        self.assertEqual(picking.packlink_shipment_ref, "PKL-124")
        self.assertFalse(picking.packlink_label_id)
        self.assertTrue(self.env["packlink.log"].search(
            [("operation", "=", "label"), ("state", "=", "error")], limit=1))

    def test_15_tracking_refresh_updates_state_and_posts(self):
        with patch.object(PacklinkApi, "get_services", return_value=SERVICES):
            picking = self._confirm()
        picking.write({"packlink_shipment_ref": "PKL-125"})
        before = len(picking.message_ids)
        with patch.object(PacklinkApi, "get_tracking",
                          return_value=[{"description": "Colis livre", "timestamp": "2026-09-03"}]), \
             patch.object(PacklinkApi, "get_shipment",
                          return_value={"state": "DELIVERED",
                                        "tracking_url": "https://track.example/9"}):
            picking._packlink_refresh_tracking()
        self.assertEqual(picking.packlink_state, "DELIVERED")
        self.assertEqual(picking.packlink_tracking_url, "https://track.example/9")
        self.assertGreater(len(picking.message_ids), before)

    def test_16_cron_skips_delivered_shipments(self):
        with patch.object(PacklinkApi, "get_services", return_value=SERVICES):
            picking = self._confirm()
        picking.write({"packlink_shipment_ref": "PKL-126", "packlink_state": "DELIVERED"})
        with patch.object(type(picking), "_packlink_refresh_tracking") as refresh:
            self.env["stock.picking"]._cron_packlink_refresh_tracking()
        refresh.assert_not_called()

    def test_17_cancel_clears_the_tracking(self):
        with patch.object(PacklinkApi, "get_services", return_value=SERVICES):
            picking = self._confirm()
        picking.write({"packlink_shipment_ref": "PKL-127", "carrier_tracking_ref": "TRK-9"})
        with patch.object(PacklinkApi, "cancel_shipment", return_value={}):
            self.carrier.packlink_cancel_shipment(picking)
        self.assertEqual(picking.packlink_state, "cancelled")
        self.assertFalse(picking.carrier_tracking_ref)

    def test_18_cancel_error_is_raised(self):
        with patch.object(PacklinkApi, "get_services", return_value=SERVICES):
            picking = self._confirm()
        picking.write({"packlink_shipment_ref": "PKL-128"})
        with patch.object(PacklinkApi, "cancel_shipment",
                          side_effect=PacklinkApiError("deja collectee")):
            with self.assertRaises(UserError):
                self.carrier.packlink_cancel_shipment(picking)

    # ------------------------------------------------------------------
    # Pont Amazon
    # ------------------------------------------------------------------
    def test_19_amazon_carrier_names_are_normalised(self):
        picking = self.env["stock.picking"].new({})
        for raw, expected in [("Chronopost Express", "Chronopost"),
                              ("colissimo domicile", "Colissimo"),
                              ("GLS Point Relais", "GLS"),
                              ("Transporteur inconnu", "Transporteur inconnu")]:
            picking.packlink_carrier_name = raw
            self.assertEqual(picking._amazon_carrier_name(), expected)

    def test_20_declared_value_is_never_zero(self):
        with patch.object(PacklinkApi, "get_services", return_value=SERVICES):
            picking = self._confirm()
        self.assertGreaterEqual(picking._packlink_declared_value(), 1.0)

    def test_20b_amazon_name_falls_back_without_packlink(self):
        """Sans expédition Packlink, le module ne casse pas la confirmation Amazon."""
        picking = self.env["stock.picking"].new({})
        self.assertTrue(picking._amazon_carrier_name())

    def test_21_connection_test_reports_a_bad_key(self):
        with patch.object(PacklinkApi, "get_services",
                          side_effect=PacklinkApiError("Invalid API key")):
            with self.assertRaises(UserError):
                self.account.action_test_connection()

    def test_22_log_purge_removes_old_entries(self):
        log = self.env["packlink.log"].create({
            "account_id": self.account.id, "operation": "rate", "state": "ok"})
        self.env.cr.execute("UPDATE packlink_log SET create_date = create_date - interval '200 days' WHERE id = %s", (log.id,))
        log.invalidate_recordset()
        self.env["packlink.log"]._cron_purge()
        self.assertFalse(log.exists())
