# -*- coding: utf-8 -*-
from odoo import fields, models


class PacklinkLog(models.Model):
    _name = "packlink.log"
    _description = "Journal des appels Packlink"
    _order = "create_date desc, id desc"
    _rec_name = "operation"

    account_id = fields.Many2one("packlink.account", string="Compte", ondelete="cascade",
                                 index=True)
    company_id = fields.Many2one(related="account_id.company_id", store=True, index=True)
    operation = fields.Selection(
        [("rate", "Tarif"), ("ship", "Création d'expédition"), ("label", "Étiquette"),
         ("track", "Suivi"), ("cancel", "Annulation")],
        string="Opération", required=True)
    picking_id = fields.Many2one("stock.picking", string="Transfert", ondelete="set null")
    shipment_ref = fields.Char(string="Expédition Packlink")
    state = fields.Selection([("ok", "Succès"), ("error", "Erreur")], required=True)
    duration = fields.Float(string="Durée (s)", digits=(6, 3))
    message = fields.Text()

    def _cron_purge(self, days=90):
        """Le journal est un outil de diagnostic, pas une archive comptable."""
        limit = fields.Datetime.subtract(fields.Datetime.now(), days=days)
        self.sudo().search([("create_date", "<", limit)]).unlink()
