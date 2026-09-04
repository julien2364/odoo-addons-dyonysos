# -*- coding: utf-8 -*-
import logging
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .amazon_sp_api import REGION_ENDPOINTS, AmazonApiError, AmazonSpApi

_logger = logging.getLogger(__name__)

SHIPPING_KEYS = ("ShippingPrice", "ShippingDiscount")


class AmazonAccountCommunity(models.Model):
    _name = "amazon.account.community"
    _description = "Compte vendeur Amazon"
    _inherit = ["mail.thread"]
    _order = "name"

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company", string="Société", required=True,
        default=lambda self: self.env.company)

    # --- Identifiants SP-API -------------------------------------------------
    seller_id = fields.Char(string="Seller ID", required=True, tracking=True)
    lwa_client_id = fields.Char(string="LWA Client ID", required=True, groups="base.group_system")
    lwa_client_secret = fields.Char(string="LWA Client Secret", required=True, groups="base.group_system")
    lwa_refresh_token = fields.Char(string="Refresh Token LWA", required=True, groups="base.group_system")
    region = fields.Selection(
        [("eu", "Europe"), ("na", "Amérique du Nord"), ("fe", "Extrême-Orient")],
        string="Région", default="eu", required=True)
    endpoint_url = fields.Char(
        string="Endpoint", compute="_compute_endpoint_url", store=True, readonly=False,
        groups="base.group_system",
        help="URL de base de l'API SP-API. Calculée depuis la région, modifiable pour le bac à sable. "
             "Réservée aux administrateurs système : une URL détournée exfiltrerait le jeton d'accès Amazon.")

    marketplace_ids = fields.Many2many(
        "amazon.marketplace.community", string="Places de marché",
        help="Places de marché interrogées lors de l'import des commandes.")

    # --- Paramétrage Odoo ----------------------------------------------------
    journal_id = fields.Many2one(
        "account.journal", string="Journal de vente",
        domain="[('type', '=', 'sale')]")
    team_id = fields.Many2one("crm.team", string="Équipe commerciale")
    warehouse_id = fields.Many2one(
        "stock.warehouse", string="Entrepôt",
        default=lambda self: self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1))
    pricelist_id = fields.Many2one(
        "product.pricelist", string="Liste de prix",
        help="Liste de prix utilisée pour l'envoi des prix vers Amazon.")
    shipping_product_id = fields.Many2one(
        "product.product", string="Article frais de port",
        domain="[('type', '=', 'service')]",
        help="Article utilisé pour la ligne de frais de port des commandes Amazon.")
    fiscal_position_id = fields.Many2one("account.fiscal.position", string="Position fiscale")
    auto_confirm_orders = fields.Boolean(
        string="Confirmer automatiquement", default=False,
        help="Confirme la commande de vente juste après son import.")
    import_days = fields.Integer(
        string="Antériorité (jours)", default=3,
        help="Fenêtre d'import utilisée lors de la toute première synchronisation.")

    # --- Suivi ---------------------------------------------------------------
    last_order_sync = fields.Datetime(string="Dernier import de commandes", readonly=True)
    last_stock_sync = fields.Datetime(string="Dernier envoi de stock", readonly=True)
    last_price_sync = fields.Datetime(string="Dernier envoi de prix", readonly=True)
    last_tracking_sync = fields.Datetime(string="Dernier envoi de suivi", readonly=True)
    order_count = fields.Integer(string="Commandes", compute="_compute_counts")
    log_count = fields.Integer(string="Journaux", compute="_compute_counts")

    _amazon_account_seller_uniq = models.Constraint(
        "UNIQUE(seller_id, company_id)",
        "Un compte Amazon existe déjà pour ce Seller ID dans cette société.",
    )

    # ------------------------------------------------------------------
    # Calculs
    # ------------------------------------------------------------------
    @api.depends("region")
    def _compute_endpoint_url(self):
        for account in self:
            account.endpoint_url = REGION_ENDPOINTS.get(account.region, REGION_ENDPOINTS["eu"])

    def _compute_counts(self):
        order_data = self.env["sale.order"]._read_group(
            [("amazon_account_id", "in", self.ids)], ["amazon_account_id"], ["__count"])
        orders = {account.id: count for account, count in order_data}
        log_data = self.env["amazon.sync.log"]._read_group(
            [("account_id", "in", self.ids)], ["account_id"], ["__count"])
        logs = {account.id: count for account, count in log_data}
        for account in self:
            account.order_count = orders.get(account.id, 0)
            account.log_count = logs.get(account.id, 0)

    # ------------------------------------------------------------------
    # Outils
    # ------------------------------------------------------------------
    def _get_api(self):
        """Retourne le client SP-API du compte (une instance par compte)."""
        self.ensure_one()
        account = self.sudo()
        return AmazonSpApi.from_account(account)

    def _log(self, operation, state="done", message=None, item_count=0,
             duration=0.0, marketplace=None, reference=None):
        """Écrit une entrée dans le journal de synchronisation."""
        self.ensure_one()
        return self.env["amazon.sync.log"].sudo().create({
            "account_id": self.id,
            "operation": operation,
            "state": state,
            "message": message,
            "item_count": item_count,
            "duration": duration,
            "marketplace_id": marketplace.id if marketplace else False,
            "reference": reference,
        })

    def _marketplace_ids_list(self):
        self.ensure_one()
        return [m.marketplace_id for m in self.marketplace_ids if m.marketplace_id]

    def _get_marketplace(self, marketplace_id):
        return self.marketplace_ids.filtered(lambda m: m.marketplace_id == marketplace_id)[:1] \
            or self.env["amazon.marketplace.community"].search(
                [("marketplace_id", "=", marketplace_id)], limit=1)

    # ------------------------------------------------------------------
    # Test de connexion
    # ------------------------------------------------------------------
    def action_test_connection(self):
        self.ensure_one()
        start = fields.Datetime.now()
        try:
            payload = self._get_api().test_connection()
        except AmazonApiError as exc:
            # On journalise l'échec puis on rend la main : lever une exception
            # annulerait la transaction, et donc l'entrée de journal.
            self._log("test", state="error", message=str(exc),
                      duration=(fields.Datetime.now() - start).total_seconds())
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "danger",
                    "title": _("Connexion Amazon"),
                    "message": _("Connexion impossible : %s", exc),
                    "sticky": True,
                },
            }
        participations = payload.get("payload") or []
        self._log("test", item_count=len(participations),
                  message=_("Connexion établie, %s place(s) de marché accessible(s).",
                            len(participations)),
                  duration=(fields.Datetime.now() - start).total_seconds())
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "title": _("Connexion Amazon"),
                "message": _("Connexion établie : %s place(s) de marché accessible(s).",
                             len(participations)),
                "sticky": False,
            },
        }

    # ------------------------------------------------------------------
    # Import des commandes
    # ------------------------------------------------------------------
    def action_import_orders(self):
        for account in self:
            account._import_orders()
        return True

    def _import_orders(self):
        """Importe les commandes Amazon en commandes de vente Odoo."""
        self.ensure_one()
        start = fields.Datetime.now()
        marketplace_ids = self._marketplace_ids_list()
        if not marketplace_ids:
            self._log("import_orders", state="error",
                      message=_("Aucune place de marché n'est configurée sur le compte."))
            return self.env["sale.order"]
        since = self.last_order_sync or (
            fields.Datetime.now() - timedelta(days=max(self.import_days or 1, 1)))
        api = self._get_api()
        try:
            payload = api.get_orders(since, marketplace_ids)
        except AmazonApiError as exc:
            self._log("import_orders", state="error", message=str(exc),
                      duration=(fields.Datetime.now() - start).total_seconds())
            return self.env["sale.order"]

        amazon_orders = (payload.get("payload") or payload).get("Orders") or []
        created = self.env["sale.order"]
        errors = 0
        for amazon_order in amazon_orders:
            order_ref = amazon_order.get("AmazonOrderId")
            if not order_ref:
                continue
            try:
                with self.env.cr.savepoint():
                    order = self._process_order(api, amazon_order)
                    if order:
                        created |= order
            except Exception as exc:  # une commande en échec n'arrête pas le lot
                errors += 1
                _logger.warning("Amazon: commande %s ignorée (%s)", order_ref, exc)
                self._log("import_orders", state="error", reference=order_ref,
                          message=_("Commande %(ref)s ignorée : %(error)s",
                                    ref=order_ref, error=exc))
        self.sudo().write({"last_order_sync": fields.Datetime.now()})
        self._log(
            "import_orders",
            state="error" if errors and not created else "done",
            item_count=len(created),
            message=_("%(ok)s commande(s) importée(s), %(ko)s en erreur.",
                      ok=len(created), ko=errors),
            duration=(fields.Datetime.now() - start).total_seconds(),
        )
        return created

    def _process_order(self, api, amazon_order):
        """Crée une commande de vente si elle n'existe pas déjà (idempotent)."""
        self.ensure_one()
        SaleOrder = self.env["sale.order"]
        order_ref = amazon_order["AmazonOrderId"]
        existing = SaleOrder.search([("amazon_order_ref", "=", order_ref)], limit=1)
        if existing:
            return SaleOrder
        marketplace = self._get_marketplace(amazon_order.get("MarketplaceId"))
        partner = self._find_or_create_partner(amazon_order, marketplace)
        items_payload = api.get_order_items(order_ref)
        items = (items_payload.get("payload") or items_payload).get("OrderItems") or []
        if not items:
            raise UserError(_("La commande Amazon %s ne contient aucune ligne.", order_ref))

        order_vals = {
            "partner_id": partner.id,
            "amazon_order_ref": order_ref,
            "amazon_account_id": self.id,
            "amazon_marketplace_id": marketplace.id if marketplace else False,
            "origin": _("Amazon %s", order_ref),
            "company_id": self.company_id.id,
        }
        if self.team_id:
            order_vals["team_id"] = self.team_id.id
        if self.warehouse_id:
            order_vals["warehouse_id"] = self.warehouse_id.id
        if self.pricelist_id:
            order_vals["pricelist_id"] = self.pricelist_id.id
        if self.fiscal_position_id:
            order_vals["fiscal_position_id"] = self.fiscal_position_id.id
        purchase_date = amazon_order.get("PurchaseDate")
        if purchase_date:
            order_vals["date_order"] = purchase_date.replace("T", " ").replace("Z", "")[:19]

        order = SaleOrder.create(order_vals)
        for item in items:
            self._create_order_lines(order, item)
        if self.auto_confirm_orders:
            order.action_confirm()
        return order

    def _create_order_lines(self, order, item):
        """Crée la ligne produit et, le cas échéant, la ligne de frais de port."""
        sku = item.get("SellerSKU")
        product = self._find_product(sku)
        quantity = float(item.get("QuantityOrdered") or 0.0)
        item_price = self._amount(item.get("ItemPrice"))
        unit_price = (item_price / quantity) if quantity else item_price
        line_vals = {
            "order_id": order.id,
            "product_id": product.id,
            "name": item.get("Title") or product.display_name,
            "product_uom_qty": quantity,
            "price_unit": unit_price,
            "amazon_item_ref": item.get("OrderItemId"),
        }
        line = self.env["sale.order.line"].create(line_vals)

        shipping = self._amount(item.get("ShippingPrice")) - self._amount(item.get("ShippingDiscount"))
        if shipping:
            shipping_product = self.shipping_product_id or self._default_shipping_product()
            self.env["sale.order.line"].create({
                "order_id": order.id,
                "product_id": shipping_product.id,
                "name": _("Frais de port Amazon"),
                "product_uom_qty": 1.0,
                "price_unit": shipping,
                "is_amazon_shipping": True,
                "amazon_item_ref": item.get("OrderItemId"),
            })
        return line

    def _find_product(self, sku):
        if not sku:
            raise UserError(_("Une ligne de commande Amazon est sans SKU vendeur."))
        Product = self.env["product.product"]
        product = Product.search([("amazon_sku", "=", sku)], limit=1)
        if not product:
            product = Product.search([("default_code", "=", sku)], limit=1)
        if not product:
            raise UserError(
                _("Aucun article Odoo ne correspond au SKU vendeur Amazon « %s ». "
                  "Renseignez ce SKU sur la fiche article.", sku))
        return product

    def _default_shipping_product(self):
        product = self.env.ref(
            "amazon_connector_community.product_amazon_shipping", raise_if_not_found=False)
        if product:
            return product
        raise UserError(
            _("Aucun article de frais de port n'est configuré sur le compte Amazon « %s ».",
              self.name))

    @staticmethod
    def _amount(money):
        if not money:
            return 0.0
        try:
            return float(money.get("Amount") or 0.0)
        except (AttributeError, TypeError, ValueError):
            return 0.0

    def _find_or_create_partner(self, amazon_order, marketplace):
        """Retrouve ou crée le client Amazon à partir de l'adresse de livraison."""
        Partner = self.env["res.partner"]
        address = amazon_order.get("ShippingAddress") or {}
        buyer = amazon_order.get("BuyerInfo") or {}
        name = address.get("Name") or buyer.get("BuyerName") or _("Client Amazon")
        email = buyer.get("BuyerEmail")
        domain = [("amazon_buyer_email", "=", email)] if email else \
            [("name", "=", name), ("amazon_marketplace_id", "=", marketplace.id if marketplace else False)]
        partner = Partner.search(domain, limit=1)
        country = self.env["res.country"].search(
            [("code", "=", (address.get("CountryCode") or "").upper())], limit=1)
        state = self.env["res.country.state"].search(
            [("code", "=", address.get("StateOrRegion")), ("country_id", "=", country.id)],
            limit=1) if country and address.get("StateOrRegion") else self.env["res.country.state"]
        vals = {
            "name": name,
            "street": address.get("AddressLine1"),
            "street2": address.get("AddressLine2"),
            "city": address.get("City"),
            "zip": address.get("PostalCode"),
            "country_id": country.id if country else False,
            "state_id": state.id if state else False,
            "phone": address.get("Phone"),
            "email": email,
            "amazon_buyer_email": email,
            "amazon_marketplace_id": marketplace.id if marketplace else False,
        }
        if partner:
            partner.write({k: v for k, v in vals.items() if v})
            return partner
        return Partner.create(vals)

    # ------------------------------------------------------------------
    # Envoi du stock et des prix
    # ------------------------------------------------------------------
    def action_push_offers(self):
        for account in self:
            account._push_stock()
            account._push_price()
        return True

    def _amazon_products(self):
        self.ensure_one()
        return self.env["product.product"].search([
            ("amazon_sync", "=", True),
            "|", ("company_id", "=", False), ("company_id", "=", self.company_id.id),
        ])

    def _push_stock(self):
        self.ensure_one()
        start = fields.Datetime.now()
        marketplace = self.marketplace_ids[:1]
        if not marketplace:
            self._log("push_stock", state="error",
                      message=_("Aucune place de marché n'est configurée sur le compte."))
            return 0
        api = self._get_api()
        products = self._amazon_products()
        sent, errors = 0, []
        # Warm the stock cache in one query instead of one per product.
        products.with_context(warehouse_id=self.warehouse_id.id or None).mapped("qty_available")
        for product in products:
            sku = product._amazon_effective_sku()
            if not sku:
                continue
            quantity = max(int(product.with_context(
                warehouse_id=self.warehouse_id.id or None).qty_available), 0)
            try:
                api.patch_listing_quantity(sku, quantity, marketplace.marketplace_id)
                sent += 1
            except AmazonApiError as exc:
                errors.append("%s: %s" % (sku, exc))
        self.sudo().write({"last_stock_sync": fields.Datetime.now()})
        self._log("push_stock", state="error" if errors and not sent else "done",
                  item_count=sent, marketplace=marketplace,
                  message="\n".join(errors) if errors else _("%s SKU mis à jour.", sent),
                  duration=(fields.Datetime.now() - start).total_seconds())
        return sent

    def _push_price(self):
        self.ensure_one()
        start = fields.Datetime.now()
        marketplace = self.marketplace_ids[:1]
        if not marketplace:
            self._log("push_price", state="error",
                      message=_("Aucune place de marché n'est configurée sur le compte."))
            return 0
        api = self._get_api()
        pricelist = self.pricelist_id
        currency = (marketplace.currency_id or pricelist.currency_id
                    or self.company_id.currency_id)
        products = self._amazon_products()
        sent, errors = 0, []
        for product in products:
            sku = product._amazon_effective_sku()
            if not sku:
                continue
            price = product.list_price
            if pricelist:
                price = pricelist._get_product_price(product, 1.0)
            try:
                api.patch_listing_price(sku, price, currency.name, marketplace.marketplace_id)
                sent += 1
            except AmazonApiError as exc:
                errors.append("%s: %s" % (sku, exc))
        self.sudo().write({"last_price_sync": fields.Datetime.now()})
        self._log("push_price", state="error" if errors and not sent else "done",
                  item_count=sent, marketplace=marketplace,
                  message="\n".join(errors) if errors else _("%s prix mis à jour.", sent),
                  duration=(fields.Datetime.now() - start).total_seconds())
        return sent

    # ------------------------------------------------------------------
    # Remontée du suivi
    # ------------------------------------------------------------------
    def action_push_tracking(self):
        for account in self:
            account._push_tracking()
        return True

    def _push_tracking(self):
        self.ensure_one()
        start = fields.Datetime.now()
        pickings = self.env["stock.picking"].search([
            ("state", "=", "done"),
            ("amazon_tracking_sent", "=", False),
            ("sale_id.amazon_account_id", "=", self.id),
        ])
        api = self._get_api()
        sent, errors = 0, []
        for picking in pickings:
            payload = picking._amazon_shipment_payload()
            if not payload:
                continue
            try:
                with self.env.cr.savepoint():
                    api.confirm_shipment(picking.sale_id.amazon_order_ref, payload)
                    picking.write({
                        "amazon_tracking_sent": True,
                        "amazon_tracking_date": fields.Datetime.now(),
                    })
                    sent += 1
            except Exception as exc:
                errors.append("%s: %s" % (picking.name, exc))
                self._log("push_tracking", state="error", reference=picking.name,
                          message=str(exc))
        self.sudo().write({"last_tracking_sync": fields.Datetime.now()})
        self._log("push_tracking", state="error" if errors and not sent else "done",
                  item_count=sent,
                  message="\n".join(errors) if errors else _("%s expédition(s) confirmée(s).", sent),
                  duration=(fields.Datetime.now() - start).total_seconds())
        return sent

    # ------------------------------------------------------------------
    # Actions planifiées
    # ------------------------------------------------------------------
    @api.model
    def _cron_import_orders(self):
        for account in self.search([]):
            account._import_orders()

    @api.model
    def _cron_push_offers(self):
        for account in self.search([]):
            account._push_stock()
            account._push_price()

    @api.model
    def _cron_push_tracking(self):
        for account in self.search([]):
            account._push_tracking()

    # ------------------------------------------------------------------
    # Boutons statistiques
    # ------------------------------------------------------------------
    def action_view_orders(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Commandes Amazon"),
            "res_model": "sale.order",
            "view_mode": "list,form",
            "domain": [("amazon_account_id", "=", self.id)],
        }

    def action_view_logs(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Journal de synchronisation"),
            "res_model": "amazon.sync.log",
            "view_mode": "list,form",
            "domain": [("account_id", "=", self.id)],
        }
