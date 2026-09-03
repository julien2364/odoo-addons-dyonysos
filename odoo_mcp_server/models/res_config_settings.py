# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    mcp_enabled = fields.Boolean(
        string="Enable the MCP endpoint", default=True, config_parameter="odoo_mcp_server.enabled",
        help="When disabled, /mcp answers 503 and no AI client can reach this database.")
    mcp_allow_writes = fields.Boolean(
        string="Allow write operations", default=False, config_parameter="odoo_mcp_server.allow_writes",
        help="Global kill switch: when off, create/update/delete tools are hidden and refused, "
             "whatever each model's configuration says.")
    mcp_log_arguments = fields.Boolean(
        string="Log call arguments", default=True, config_parameter="odoo_mcp_server.log_arguments")
    mcp_log_retention_days = fields.Char(
        string="Log retention (days)", default="90", config_parameter="odoo_mcp_server.log_retention_days")
    mcp_rate_limit = fields.Char(
        string="Max calls per minute and per key", default="120", config_parameter="odoo_mcp_server.rate_limit")

    def action_mcp_open_models(self):
        return self.env["ir.actions.act_window"]._for_xml_id("odoo_mcp_server.mcp_model_config_action")
