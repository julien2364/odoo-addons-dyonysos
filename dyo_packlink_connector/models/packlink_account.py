# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .packlink_api import (DEFAULT_AUTH_HEADER, DEFAULT_BASE_URL, DEFAULT_TIMEOUT,
                           PacklinkApi, PacklinkApiError)


class PacklinkAccount(models.Model):
    _name = "packlink.account"
    _description = "Compte Packlink PRO"
    _order = "name"

    name = fields.Char(required=True, default="Packlink PRO")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company", string="Société", required=True,
        default=lambda self: self.env.company)
    api_key = fields.Char(
        string="Clé API", required=True, groups="base.group_system",
        help="Clé API fournie par Packlink PRO (Paramètres → Intégrations).")
    base_url = fields.Char(
        string="URL de l'API", default=DEFAULT_BASE_URL, required=True,
        groups="base.group_system",
        help="À ne changer que si Packlink vous communique une autre URL.")
    auth_header = fields.Char(
        string="En-tête d'authentification", default=DEFAULT_AUTH_HEADER, required=True,
        groups="base.group_system")
    auth_scheme = fields.Char(
        string="Préfixe d'authentification", default="", groups="base.group_system",
        help="Laisser vide pour envoyer la clé telle quelle, ou saisir « Bearer ».")
    timeout = fields.Integer(string="Délai d'attente (s)", default=DEFAULT_TIMEOUT)

    warehouse_partner_id = fields.Many2one(
        "res.partner", string="Adresse d'expédition",
        help="Adresse de collecte transmise à Packlink. "
             "Par défaut, l'adresse de l'entrepôt du transfert, sinon celle de la société.")
    postage_type = fields.Selection(
        [("cheapest", "Le service le moins cher"),
         ("fastest", "Le service le plus rapide")],
        string="Sélection du service", default="cheapest", required=True)
    log_ids = fields.One2many("packlink.log", "account_id", string="Journal")

    _name_uniq = models.Constraint("unique(name, company_id)",
                                   "Un compte Packlink porte un nom unique par société.")

    def _api(self):
        self.ensure_one()
        return PacklinkApi.from_account(self.sudo())

    def action_test_connection(self):
        """Un appel de tarif à blanc : c'est le moyen le plus court de valider la clé."""
        self.ensure_one()
        try:
            self._api().get_services(
                {"country": "FR", "zip": "75001"},
                {"country": "FR", "zip": "69001"},
                [{"weight": 1, "length": 20, "width": 15, "height": 10}])
        except PacklinkApiError as exc:
            raise UserError(_("Connexion Packlink refusée : %s") % exc)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"type": "success", "sticky": False,
                       "message": _("Connexion Packlink établie.")},
        }

    @api.model
    def _default_account(self, company=None):
        company = company or self.env.company
        return self.search([("company_id", "=", company.id)], limit=1)
