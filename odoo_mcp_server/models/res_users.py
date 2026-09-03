# -*- coding: utf-8 -*-
from odoo import _, fields, models

MCP_SCOPE = "odoo.mcp"


class ResUsers(models.Model):
    _inherit = "res.users"

    mcp_key_count = fields.Integer(string="MCP keys", compute="_compute_mcp_key_count")

    def _compute_mcp_key_count(self):
        for user in self:
            user.mcp_key_count = self.env["res.users.apikeys"].sudo().search_count(
                [("user_id", "=", user.id), ("scope", "=", MCP_SCOPE)])

    def action_mcp_new_key(self):
        """Open the standard Odoo API key wizard pre-filled with the MCP scope."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "res.users.apikeys.description",
            "name": _("New MCP API key"),
            "target": "new",
            "view_mode": "form",
            "context": {"default_name": _("MCP client"), "dialog_size": "medium", "scope": MCP_SCOPE},
        }
