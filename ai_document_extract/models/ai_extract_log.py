# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AiExtractLog(models.Model):
    _name = "ai.extract.log"
    _description = "AI Extraction Log"
    _order = "create_date desc, id desc"

    res_model = fields.Char(string="Model", required=True, index=True)
    res_id = fields.Integer(string="Record ID", required=True, index=True)
    res_name = fields.Char(string="Record", compute="_compute_res_name")
    attachment_id = fields.Many2one("ir.attachment", string="Attachment", ondelete="set null")
    attachment_name = fields.Char(string="File")
    doc_type = fields.Selection(
        [("invoice", "Vendor Bill"), ("expense", "Expense")], string="Document Type", required=True, default="invoice")
    provider = fields.Char()
    model = fields.Char(string="AI Model")
    state = fields.Selection([("done", "Done"), ("error", "Error")], required=True, default="done", index=True)
    duration = fields.Float(string="Duration (s)", digits=(8, 2))
    input_tokens = fields.Integer()
    output_tokens = fields.Integer()
    confidence = fields.Float(digits=(3, 2))
    result_json = fields.Text(string="Extracted Data (JSON)")
    error = fields.Text()
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, index=True)

    @api.depends("res_model", "res_id")
    def _compute_res_name(self):
        for log in self:
            name = ""
            if log.res_model and log.res_id and log.res_model in self.env:
                record = self.env[log.res_model].browse(log.res_id).exists()
                if record:
                    name = record.display_name
            log.res_name = name

    @api.depends("attachment_name", "state")
    def _compute_display_name(self):
        for log in self:
            log.display_name = "%s (%s)" % (log.attachment_name or log.res_model, log.state)

    def action_open_record(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": self.res_model,
            "res_id": self.res_id,
            "view_mode": "form",
            "target": "current",
        }
