# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.exceptions import UserError


class HrExpense(models.Model):
    _inherit = "hr.expense"

    dougs_state = fields.Selection(
        [("none", "Not sent"), ("sent", "Sent to accountant"), ("error", "Error")],
        string="Accountant", compute="_compute_dougs_state")

    def _compute_dougs_state(self):
        lines = self.env["dougs.export.line"].search(
            [("res_model", "=", "hr.expense"), ("res_id", "in", self.ids)], order="id desc")
        by_id = {}
        for line in lines:
            by_id.setdefault(line.res_id, []).append(line)
        for expense in self:
            states = [l.state for l in by_id.get(expense.id, [])]
            expense.dougs_state = "sent" if "sent" in states else ("error" if "error" in states else "none")

    def action_send_to_dougs(self):
        expenses = self.filtered(lambda e: e.state in ("approved", "posted", "done", "paid"))
        if not expenses:
            raise UserError(self.env._("Only approved expenses can be sent to the accountant."))
        batch = self.env["dougs.export.batch"].create({"company_id": expenses[0].company_id.id})
        Line = self.env["dougs.export.line"]
        Line.create([Line._vals_from_expense(e, batch) for e in expenses if e.dougs_state != "sent"])
        batch.action_send()
        return {"type": "ir.actions.act_window", "res_model": "dougs.export.batch", "res_id": batch.id, "view_mode": "form"}
