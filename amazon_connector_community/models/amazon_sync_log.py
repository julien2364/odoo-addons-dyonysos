# -*- coding: utf-8 -*-
from odoo import fields, models

OPERATION_SELECTION = [
    ("test", "Test de connexion"),
    ("import_orders", "Import des commandes"),
    ("push_stock", "Envoi du stock"),
    ("push_price", "Envoi des prix"),
    ("push_tracking", "Envoi du suivi"),
]


class AmazonSyncLog(models.Model):
    _name = "amazon.sync.log"
    _description = "Journal de synchronisation Amazon"
    _order = "create_date desc, id desc"

    account_id = fields.Many2one(
        "amazon.account.community", string="Compte Amazon",
        ondelete="cascade", index=True)
    marketplace_id = fields.Many2one(
        "amazon.marketplace.community", string="Place de marché")
    operation = fields.Selection(
        OPERATION_SELECTION, string="Opération", required=True, index=True)
    state = fields.Selection(
        [("done", "Terminé"), ("error", "Erreur")],
        string="Statut", required=True, default="done", index=True)
    item_count = fields.Integer(string="Éléments traités")
    duration = fields.Float(string="Durée (s)", digits=(10, 3))
    message = fields.Text(string="Message")
    reference = fields.Char(string="Référence", help="Commande ou SKU concerné.")

    def _compute_display_name(self):
        labels = dict(OPERATION_SELECTION)
        for log in self:
            log.display_name = "%s — %s" % (
                labels.get(log.operation, log.operation or ""),
                log.account_id.name or "",
            )

    @classmethod
    def _operation_labels(cls):
        return dict(OPERATION_SELECTION)
