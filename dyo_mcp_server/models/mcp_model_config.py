# -*- coding: utf-8 -*-
"""Whitelist of Odoo models exposed through the MCP endpoint.

Nothing is reachable by an MCP client unless a ``mcp.model.config`` record
enables it. Each record carries per-operation flags and an optional domain that
is ANDed with every search performed by an AI client, on top of Odoo's own
access rights and record rules (which always apply, since the request runs as
the API key's user).
"""
import ast
import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

# Methods an MCP client may call through odoo_call_method, per model or globally.
# Anything not listed here is refused, whatever the user's rights.
# Methods that create records: only reachable when the model also allows creation.
CREATING_METHODS = {"name_create", "copy"}

DEFAULT_SAFE_METHODS = [
    "name_search", "default_get", "fields_get",
    "action_post", "action_confirm", "action_done", "action_cancel",
    "button_confirm", "button_validate", "message_post",
]


class McpModelConfig(models.Model):
    _name = "mcp.model.config"
    _description = "MCP exposed model"
    _order = "sequence, id"
    _rec_name = "model_id"

    sequence = fields.Integer(default=10)
    model_id = fields.Many2one("ir.model", string="Model", required=True, ondelete="cascade",
                               domain=[("transient", "=", False)])
    model_name = fields.Char(related="model_id.model", store=True, index=True, string="Technical name")
    active = fields.Boolean(default=True)
    description = fields.Char(help="Shown to the AI client to explain what this model holds.")
    allow_read = fields.Boolean(default=True, string="Read")
    allow_create = fields.Boolean(default=False, string="Create")
    allow_write = fields.Boolean(default=False, string="Update")
    allow_unlink = fields.Boolean(default=False, string="Delete")
    domain = fields.Char(string="Restriction domain", default="[]",
                         help="Extra domain ANDed with every search, e.g. [('state','!=','cancel')].")
    field_names = fields.Char(
        string="Exposed fields",
        help="Comma-separated whitelist of field names. Empty = all fields readable by the user.")
    method_names = fields.Char(
        string="Callable methods",
        help="Comma-separated methods allowed through odoo_call_method for this model, "
             "on top of the global safe list.")
    limit_default = fields.Integer(string="Default limit", default=50)
    limit_max = fields.Integer(string="Maximum limit", default=500)

    _model_uniq = models.Constraint("unique(model_id)", "This model is already exposed to MCP.")

    @api.constrains("domain")
    def _check_domain(self):
        for rec in self:
            try:
                parsed = ast.literal_eval(rec.domain or "[]")
                assert isinstance(parsed, list)
            except Exception:
                raise ValidationError(_("The restriction domain of %s is not a valid Odoo domain.", rec.display_name))

    @api.constrains("limit_default", "limit_max")
    def _check_limits(self):
        for rec in self:
            if rec.limit_max <= 0 or rec.limit_default <= 0:
                raise ValidationError(_("Limits must be strictly positive."))
            if rec.limit_default > rec.limit_max:
                raise ValidationError(_("The default limit cannot exceed the maximum limit."))

    # ------------------------------------------------------------------
    # Helpers used by the controller
    # ------------------------------------------------------------------
    @api.model
    def _get_config(self, model_name):
        """Return the active config for a model, or an empty recordset."""
        return self.sudo().search([("model_name", "=", model_name)], limit=1)

    def _get_domain(self):
        self.ensure_one()
        try:
            return ast.literal_eval(self.domain or "[]")
        except Exception:  # noqa: BLE001 - guarded by the constraint, defensive here
            _logger.warning("MCP: invalid domain on %s, ignoring", self.display_name)
            return []

    def _get_fields(self):
        self.ensure_one()
        if not self.field_names:
            return None
        return [f.strip() for f in self.field_names.split(",") if f.strip()]

    def _get_methods(self):
        self.ensure_one()
        extra = [m.strip() for m in (self.method_names or "").split(",") if m.strip()]
        return set(DEFAULT_SAFE_METHODS) | set(extra)

    def _clamp_limit(self, limit):
        self.ensure_one()
        if not limit:
            return self.limit_default
        return max(1, min(int(limit), self.limit_max))

    def action_open_records(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": self.model_name,
            "view_mode": "list,form",
            "name": self.model_id.name,
        }
