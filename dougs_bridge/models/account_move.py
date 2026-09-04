# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    dougs_state = fields.Selection(
        [("none", "Not sent"), ("sent", "Sent to accountant"), ("error", "Error")],
        string="Accountant", compute="_compute_dougs_state", search="_search_dougs_state")
    dougs_sent_date = fields.Datetime(compute="_compute_dougs_state")

    def _compute_dougs_state(self):
        lines = self.env["dougs.export.line"].sudo().search(
            [("res_model", "=", "account.move"), ("res_id", "in", self.ids)], order="id desc")
        by_move = {}
        for line in lines:
            by_move.setdefault(line.res_id, []).append(line)
        for move in self:
            move_lines = by_move.get(move.id, [])
            sent = [l for l in move_lines if l.state == "sent"]
            if sent:
                move.dougs_state, move.dougs_sent_date = "sent", sent[0].sent_date
            elif any(l.state == "error" for l in move_lines):
                move.dougs_state, move.dougs_sent_date = "error", False
            else:
                move.dougs_state, move.dougs_sent_date = "none", False

    def _search_dougs_state(self, operator, value):
        sent_ids = self.env["dougs.export.line"].sudo().search(
            [("res_model", "=", "account.move"), ("state", "=", "sent")]).mapped("res_id")
        if (operator, value) in (("=", "sent"), ("!=", "none")):
            return [("id", "in", sent_ids)]
        if (operator, value) in (("=", "none"), ("!=", "sent")):
            return [("id", "not in", sent_ids)]
        return []

    def action_send_to_dougs(self):
        moves = self.filtered(lambda m: m.state == "posted" and m.is_invoice(include_receipts=False))
        if not moves:
            raise UserError(self.env._("Only posted invoices and bills can be sent to the accountant."))
        batch = self.env["dougs.export.batch"].create({"company_id": moves[0].company_id.id})
        Line = self.env["dougs.export.line"]
        Line.create([Line._vals_from_move(m, batch) for m in moves if m.dougs_state != "sent"])
        batch.action_send()
        return {"type": "ir.actions.act_window", "res_model": "dougs.export.batch", "res_id": batch.id, "view_mode": "form"}
