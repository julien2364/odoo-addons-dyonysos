# -*- coding: utf-8 -*-
"""Tests du connecteur Amazon.

Aucun appel réseau : ``AmazonSpApi._request`` est systématiquement mocké, ce
qui garantit aussi qu'aucun autre point du module n'ouvre de connexion.
"""
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from odoo.addons.amazon_connector_community.models.amazon_sp_api import (
    AmazonApiError,
    AmazonSpApi,
)

ORDER_1 = {
    "AmazonOrderId": "402-1234567-1234567",
    "PurchaseDate": "2026-08-20T09:15:00Z",
    "MarketplaceId": "A13V1IB3VIYZZH",
    "OrderStatus": "Unshipped",
    "BuyerInfo": {"BuyerEmail": "acheteur1@marketplace.amazon.fr", "BuyerName": "Camille Durand"},
    "ShippingAddress": {
        "Name": "Camille Durand",
        "AddressLine1": "12 rue des Lilas",
        "City": "Lyon",
        "PostalCode": "69003",
        "CountryCode": "FR",
        "Phone": "+33 6 11 22 33 44",
    },
}

ORDER_2 = {
    "AmazonOrderId": "402-7654321-7654321",
    "PurchaseDate": "2026-08-21T14:02:00Z",
    "MarketplaceId": "A13V1IB3VIYZZH",
    "OrderStatus": "Unshipped",
    "BuyerInfo": {"BuyerEmail": "acheteur2@marketplace.amazon.fr", "BuyerName": "Paul Meunier"},
    "ShippingAddress": {
        "Name": "Paul Meunier",
        "AddressLine1": "3 avenue Gambetta",
        "City": "Nantes",
        "PostalCode": "44000",
        "CountryCode": "FR",
    },
}

ITEMS_1 = {
    "payload": {
        "AmazonOrderId": "402-1234567-1234567",
        "OrderItems": [{
            "OrderItemId": "1111111111",
            "SellerSKU": "AMZ-SKU-A",
            "Title": "Carnet A5 recyclé",
            "QuantityOrdered": 2,
            "ItemPrice": {"CurrencyCode": "EUR", "Amount": "24.00"},
            "ShippingPrice": {"CurrencyCode": "EUR", "Amount": "4.90"},
        }],
    }
}

ITEMS_2 = {
    "payload": {
        "AmazonOrderId": "402-7654321-7654321",
        "OrderItems": [{
            "OrderItemId": "2222222222",
            "SellerSKU": "AMZ-SKU-B",
            "Title": "Stylo plume laiton",
            "QuantityOrdered": 1,
            "ItemPrice": {"CurrencyCode": "EUR", "Amount": "39.50"},
        }],
    }
}

ORDERS_PAYLOAD = {"payload": {"Orders": [ORDER_1, ORDER_2]}}


@tagged("post_install", "-at_install")
class TestAmazonConnector(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.marketplace_fr = cls.env.ref("amazon_connector_community.marketplace_fr")
        cls.shipping_product = cls.env.ref("amazon_connector_community.product_amazon_shipping")
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1)
        cls.product_a = cls.env["product.product"].create({
            "name": "Carnet A5 recyclé",
            "type": "consu",
            "is_storable": True,
            "default_code": "AMZ-SKU-A",
            "list_price": 12.00,
            "amazon_sync": True,
        })
        cls.product_b = cls.env["product.product"].create({
            "name": "Stylo plume laiton",
            "type": "consu",
            "is_storable": True,
            "default_code": "AMZ-SKU-B",
            "list_price": 39.50,
            "amazon_sync": True,
        })
        cls.product_offline = cls.env["product.product"].create({
            "name": "Article hors Amazon",
            "type": "consu",
            "default_code": "NO-AMZ",
            "list_price": 5.00,
            "amazon_sync": False,
        })
        cls.pricelist = cls.env["product.pricelist"].create({
            "name": "Tarif Amazon",
            "currency_id": cls.env.ref("base.EUR").id,
            "item_ids": [(0, 0, {
                "applied_on": "0_product_variant",
                "product_id": cls.product_a.id,
                "compute_price": "fixed",
                "fixed_price": 17.90,
            })],
        })
        cls.account = cls.env["amazon.account.community"].create({
            "name": "Boutique test",
            "seller_id": "A2TESTSELLER",
            "lwa_client_id": "amzn1.application-oa2-client.test",
            "lwa_client_secret": "secret-test",
            "lwa_refresh_token": "Atzr|refresh-test",
            "region": "eu",
            "marketplace_ids": [(6, 0, cls.marketplace_fr.ids)],
            "warehouse_id": cls.warehouse.id,
            "pricelist_id": cls.pricelist.id,
            "shipping_product_id": cls.shipping_product.id,
        })

    # ------------------------------------------------------------------
    # Outils de mock
    # ------------------------------------------------------------------
    @staticmethod
    def _router(orders_payload=None, items=None, error_on=None):
        """Construit un faux ``_request`` qui route selon le chemin appelé."""
        items = items or {}
        calls = []

        def _fake_request(self, method, path, params=None, body=None):
            calls.append({"method": method, "path": path, "params": params, "body": body})
            if error_on and error_on(method, path):
                raise AmazonApiError("Erreur simulée", status_code=500)
            if path == "/sellers/v1/marketplaceParticipations":
                return {"payload": [{"marketplace": {"id": "A13V1IB3VIYZZH"}}]}
            if path == "/orders/v0/orders":
                return orders_payload or {"payload": {"Orders": []}}
            if path.endswith("/orderItems"):
                order_id = path.split("/")[-2]
                return items.get(order_id, {"payload": {"OrderItems": []}})
            return {}

        _fake_request.calls = calls
        return _fake_request

    def _import(self, orders_payload=ORDERS_PAYLOAD, items=None, error_on=None):
        items = items if items is not None else {
            ORDER_1["AmazonOrderId"]: ITEMS_1,
            ORDER_2["AmazonOrderId"]: ITEMS_2,
        }
        fake = self._router(orders_payload, items, error_on)
        with patch.object(AmazonSpApi, "_request", fake):
            self.account._import_orders()
        return fake.calls

    # ------------------------------------------------------------------
    # 1 / 2 — test de connexion
    # ------------------------------------------------------------------
    def test_01_connection_success(self):
        fake = self._router()
        with patch.object(AmazonSpApi, "_request", fake):
            result = self.account.action_test_connection()
        self.assertEqual(result["type"], "ir.actions.client")
        log = self.env["amazon.sync.log"].search(
            [("account_id", "=", self.account.id), ("operation", "=", "test")], limit=1)
        self.assertEqual(log.state, "done")
        self.assertEqual(log.item_count, 1)

    def test_02_connection_failure(self):
        def _boom(self, method, path, params=None, body=None):
            raise AmazonApiError("Authentification Amazon refusée.", status_code=401)

        with patch.object(AmazonSpApi, "_request", _boom):
            result = self.account.action_test_connection()
        self.assertEqual(result["params"]["type"], "danger")
        log = self.env["amazon.sync.log"].search(
            [("account_id", "=", self.account.id), ("operation", "=", "test")], limit=1)
        self.assertEqual(log.state, "error")
        self.assertIn("401", log.message)

    # ------------------------------------------------------------------
    # 3 — import de deux commandes
    # ------------------------------------------------------------------
    def test_03_import_two_orders(self):
        self._import()
        orders = self.env["sale.order"].search(
            [("amazon_account_id", "=", self.account.id)], order="amazon_order_ref")
        self.assertEqual(len(orders), 2)

        order1 = orders.filtered(lambda o: o.amazon_order_ref == ORDER_1["AmazonOrderId"])
        self.assertEqual(order1.partner_id.name, "Camille Durand")
        self.assertEqual(order1.partner_id.city, "Lyon")
        self.assertEqual(order1.amazon_marketplace_id, self.marketplace_fr)
        product_line = order1.order_line.filtered(lambda l: l.product_id == self.product_a)
        self.assertEqual(product_line.product_uom_qty, 2)
        # 24,00 € pour 2 unités => 12,00 € l'unité
        self.assertAlmostEqual(product_line.price_unit, 12.00, places=2)
        self.assertAlmostEqual(
            sum(order1.order_line.mapped("price_subtotal")), 28.90, places=2)

        order2 = orders.filtered(lambda o: o.amazon_order_ref == ORDER_2["AmazonOrderId"])
        self.assertEqual(len(order2.order_line), 1)
        self.assertAlmostEqual(order2.order_line.price_unit, 39.50, places=2)
        self.assertEqual(order2.partner_id.name, "Paul Meunier")

    # ------------------------------------------------------------------
    # 4 — idempotence
    # ------------------------------------------------------------------
    def test_04_reimport_is_idempotent(self):
        self._import()
        self.assertEqual(self.env["sale.order"].search_count(
            [("amazon_account_id", "=", self.account.id)]), 2)
        self._import()
        self.assertEqual(self.env["sale.order"].search_count(
            [("amazon_account_id", "=", self.account.id)]), 2)

    # ------------------------------------------------------------------
    # 5 — SKU inconnu : la commande fautive est journalisée, l'autre passe
    # ------------------------------------------------------------------
    def test_05_unknown_sku_does_not_break_batch(self):
        bad_items = dict(ITEMS_1)
        bad_items = {
            ORDER_1["AmazonOrderId"]: {"payload": {"OrderItems": [{
                "OrderItemId": "9999999999",
                "SellerSKU": "SKU-INEXISTANT",
                "Title": "Article inconnu",
                "QuantityOrdered": 1,
                "ItemPrice": {"CurrencyCode": "EUR", "Amount": "10.00"},
            }]}},
            ORDER_2["AmazonOrderId"]: ITEMS_2,
        }
        self._import(items=bad_items)
        orders = self.env["sale.order"].search([("amazon_account_id", "=", self.account.id)])
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders.amazon_order_ref, ORDER_2["AmazonOrderId"])
        error_log = self.env["amazon.sync.log"].search([
            ("account_id", "=", self.account.id),
            ("operation", "=", "import_orders"),
            ("state", "=", "error"),
            ("reference", "=", ORDER_1["AmazonOrderId"]),
        ])
        self.assertEqual(len(error_log), 1)
        self.assertIn("SKU-INEXISTANT", error_log.message)
        with self.assertRaises(UserError):
            self.account._find_product("SKU-INEXISTANT")

    # ------------------------------------------------------------------
    # 6 — frais de port sur une ligne distincte
    # ------------------------------------------------------------------
    def test_06_shipping_line_is_separate(self):
        self._import()
        order1 = self.env["sale.order"].search(
            [("amazon_order_ref", "=", ORDER_1["AmazonOrderId"])])
        self.assertEqual(len(order1.order_line), 2)
        shipping = order1.order_line.filtered("is_amazon_shipping")
        self.assertEqual(len(shipping), 1)
        self.assertEqual(shipping.product_id, self.shipping_product)
        self.assertAlmostEqual(shipping.price_unit, 4.90, places=2)
        self.assertEqual(shipping.product_uom_qty, 1)
        # la commande 2 n'a pas de frais de port
        order2 = self.env["sale.order"].search(
            [("amazon_order_ref", "=", ORDER_2["AmazonOrderId"])])
        self.assertFalse(order2.order_line.filtered("is_amazon_shipping"))

    # ------------------------------------------------------------------
    # 7 — push du stock
    # ------------------------------------------------------------------
    def test_07_push_stock(self):
        self.env["stock.quant"]._update_available_quantity(
            self.product_a, self.warehouse.lot_stock_id, 7)
        fake = self._router()
        with patch.object(AmazonSpApi, "_request", fake):
            self.account._push_stock()
        patches = [c for c in fake.calls if c["method"] == "PATCH"]
        skus = [c["path"].rsplit("/", 1)[-1] for c in patches]
        self.assertIn("AMZ-SKU-A", skus)
        self.assertIn("AMZ-SKU-B", skus)
        self.assertNotIn("NO-AMZ", skus)  # produit non marqué : ignoré
        call_a = next(c for c in patches if c["path"].endswith("AMZ-SKU-A"))
        value = call_a["body"]["patches"][0]["value"][0]
        self.assertEqual(value["quantity"], 7)
        self.assertEqual(call_a["params"]["marketplaceIds"], "A13V1IB3VIYZZH")
        self.assertTrue(self.account.last_stock_sync)

    # ------------------------------------------------------------------
    # 8 — push des prix depuis la liste de prix
    # ------------------------------------------------------------------
    def test_08_push_price_uses_pricelist(self):
        fake = self._router()
        with patch.object(AmazonSpApi, "_request", fake):
            self.account._push_price()
        patches = [c for c in fake.calls if c["method"] == "PATCH"]
        call_a = next(c for c in patches if c["path"].endswith("AMZ-SKU-A"))
        offer = call_a["body"]["patches"][0]["value"][0]
        self.assertAlmostEqual(
            offer["our_price"][0]["schedule"][0]["value_with_tax"], 17.90, places=2)
        self.assertEqual(offer["currency"], "EUR")
        call_b = next(c for c in patches if c["path"].endswith("AMZ-SKU-B"))
        offer_b = call_b["body"]["patches"][0]["value"][0]
        self.assertAlmostEqual(
            offer_b["our_price"][0]["schedule"][0]["value_with_tax"], 39.50, places=2)

    # ------------------------------------------------------------------
    # 9 — remontée du suivi après validation du picking
    # ------------------------------------------------------------------
    def test_09_push_tracking_after_picking(self):
        self._import()
        order = self.env["sale.order"].search(
            [("amazon_order_ref", "=", ORDER_2["AmazonOrderId"])])
        order.action_confirm()
        picking = order.picking_ids[:1]
        self.assertTrue(picking, "La commande doit générer un bon de livraison")
        picking.carrier_tracking_ref = "1Z-TEST-999"
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
        picking.move_ids.picked = True
        fake = self._router()
        with patch.object(AmazonSpApi, "_request", fake):
            picking.button_validate()
        self.assertEqual(picking.state, "done")
        self.assertTrue(picking.amazon_tracking_sent)
        posts = [c for c in fake.calls if c["path"].endswith("shipmentConfirmation")]
        self.assertEqual(len(posts), 1)
        detail = posts[0]["body"]["packageDetail"]
        self.assertEqual(detail["trackingNumber"], "1Z-TEST-999")
        self.assertEqual(detail["orderItems"][0]["orderItemId"], "2222222222")
        log = self.env["amazon.sync.log"].search(
            [("account_id", "=", self.account.id), ("operation", "=", "push_tracking")], limit=1)
        self.assertEqual(log.state, "done")

    # ------------------------------------------------------------------
    # 10 — HTTP 429 puis succès : une seule commande créée
    # ------------------------------------------------------------------
    def test_10_retry_on_rate_limit(self):
        state = {"attempts": 0}
        single = {"payload": {"Orders": [ORDER_2]}}

        def _flaky(self, method, path, params=None, body=None):
            if path == "/orders/v0/orders":
                state["attempts"] += 1
                if state["attempts"] == 1:
                    raise AmazonApiError("Quota dépassé", status_code=429)
                return single
            if path.endswith("/orderItems"):
                return ITEMS_2
            return {}

        with patch.object(AmazonSpApi, "_request", _flaky):
            self.account._import_orders()
            self.assertEqual(self.env["sale.order"].search_count(
                [("amazon_account_id", "=", self.account.id)]), 0)
            self.account._import_orders()
        self.assertEqual(state["attempts"], 2)
        orders = self.env["sale.order"].search([("amazon_account_id", "=", self.account.id)])
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders.amazon_order_ref, ORDER_2["AmazonOrderId"])

    # ------------------------------------------------------------------
    # 11 — le backoff HTTP 429 est bien géré au niveau du transport
    # ------------------------------------------------------------------
    def test_11_transport_retries_http_429(self):
        api = AmazonSpApi("rt", "cid", "secret", "A2TESTSELLER", region="eu")
        api._access_token = "token"
        api._access_token_expiry = float("inf")
        responses = []

        class _Resp:
            def __init__(self, status, payload=None):
                self.status_code = status
                self._payload = payload or {}
                self.content = b"{}"

            def json(self):
                return self._payload

        def _fake_http(method, url, **kwargs):
            responses.append(url)
            if len(responses) < 3:
                return _Resp(429)
            return _Resp(200, {"payload": {"Orders": []}})

        with patch("odoo.addons.amazon_connector_community.models.amazon_sp_api.requests") as req:
            req.request.side_effect = _fake_http
            with patch("odoo.addons.amazon_connector_community.models.amazon_sp_api.BACKOFF_SECONDS", 0):
                result = api._request("GET", "/orders/v0/orders")
        self.assertEqual(len(responses), 3)
        self.assertEqual(result, {"payload": {"Orders": []}})

    # ------------------------------------------------------------------
    # 12 — chaque opération écrit dans le journal de synchronisation
    # ------------------------------------------------------------------
    def test_12_every_operation_is_logged(self):
        Log = self.env["amazon.sync.log"]
        before = Log.search_count([("account_id", "=", self.account.id)])
        fake = self._router(ORDERS_PAYLOAD, {
            ORDER_1["AmazonOrderId"]: ITEMS_1,
            ORDER_2["AmazonOrderId"]: ITEMS_2,
        })
        with patch.object(AmazonSpApi, "_request", fake):
            self.account.action_test_connection()
            self.account._import_orders()
            self.account._push_stock()
            self.account._push_price()
            self.account._push_tracking()
        logs = Log.search([("account_id", "=", self.account.id)])
        self.assertGreater(len(logs) - before, 4)
        self.assertEqual(
            {"test", "import_orders", "push_stock", "push_price", "push_tracking"},
            set(logs.mapped("operation")))
        import_log = logs.filtered(lambda log: log.operation == "import_orders")[:1]
        self.assertEqual(import_log.item_count, 2)
        self.assertGreaterEqual(import_log.duration, 0.0)

    # ------------------------------------------------------------------
    # 13 — le SKU Amazon prime sur la référence interne
    # ------------------------------------------------------------------
    def test_13_amazon_sku_overrides_default_code(self):
        self.product_b.amazon_sku = "SKU-SPECIFIQUE"
        fake = self._router()
        with patch.object(AmazonSpApi, "_request", fake):
            self.account._push_stock()
        skus = [c["path"].rsplit("/", 1)[-1] for c in fake.calls if c["method"] == "PATCH"]
        self.assertIn("SKU-SPECIFIQUE", skus)
        self.assertNotIn("AMZ-SKU-B", skus)

    # ------------------------------------------------------------------
    # 14 — erreur d'appel sur l'import : journal en erreur, aucune commande
    # ------------------------------------------------------------------
    def test_14_orders_api_error_is_logged(self):
        self._import(error_on=lambda method, path: path == "/orders/v0/orders")
        self.assertEqual(self.env["sale.order"].search_count(
            [("amazon_account_id", "=", self.account.id)]), 0)
        log = self.env["amazon.sync.log"].search([
            ("account_id", "=", self.account.id),
            ("operation", "=", "import_orders"),
            ("state", "=", "error"),
        ], limit=1)
        self.assertTrue(log)
        self.assertIn("Erreur simulée", log.message)

    # ------------------------------------------------------------------
    # 15 — sans place de marché, rien n'est appelé
    # ------------------------------------------------------------------
    def test_15_no_marketplace_no_call(self):
        self.account.marketplace_ids = [(5, 0, 0)]
        fake = self._router()
        with patch.object(AmazonSpApi, "_request", fake):
            self.account._import_orders()
            self.account._push_stock()
        self.assertFalse(fake.calls)
        logs = self.env["amazon.sync.log"].search([
            ("account_id", "=", self.account.id), ("state", "=", "error")])
        self.assertEqual(len(logs), 2)
