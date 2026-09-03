# -*- coding: utf-8 -*-
from odoo import api, fields, models


class McpAccessLog(models.Model):
    _name = "mcp.access.log"
    _description = "MCP access log"
    _order = "create_date desc, id desc"

    user_id = fields.Many2one("res.users", string="User", required=True, index=True, ondelete="cascade")
    client_name = fields.Char(string="MCP client")
    tool = fields.Char(required=True, index=True)
    model_name = fields.Char(string="Model", index=True)
    method = fields.Char()
    arguments = fields.Text()
    record_ids = fields.Char(string="Records")
    record_count = fields.Integer()
    state = fields.Selection([("done", "Done"), ("error", "Error"), ("denied", "Denied")],
                             required=True, default="done", index=True)
    error = fields.Text()
    duration = fields.Float(string="Duration (ms)", digits=(10, 1))
    ip = fields.Char(string="IP address")

    @api.autovacuum
    def _gc_logs(self):
        """Delete logs older than the retention configured (default 90 days)."""
        days = int(self.env["ir.config_parameter"].sudo().get_param("odoo_mcp_server.log_retention_days", "90") or 90)
        if days <= 0:
            return
        limit = fields.Datetime.subtract(fields.Datetime.now(), days=days)
        self.sudo().search([("create_date", "<", limit)]).unlink()

    @api.model
    def _cron_gc(self):
        self._gc_logs()
