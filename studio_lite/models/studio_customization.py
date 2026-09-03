# -*- coding: utf-8 -*-
"""Journal central et réversible des personnalisations Studio Lite."""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

CUSTOMIZATION_KINDS = [
    ("field", "Champ personnalisé"),
    ("view", "Personnalisation de vue"),
    ("automation", "Automatisation"),
]


class StudioCustomization(models.Model):
    """Chaque objet créé par Studio Lite est tracé ici, et peut être défait."""

    _name = "studio.customization"
    _inherit = ["studio.mixin", "mail.thread"]
    _description = "Studio Lite - personnalisation"
    _order = "id desc"

    name = fields.Char(string="Nom", required=True, tracking=True)
    kind = fields.Selection(
        CUSTOMIZATION_KINDS, string="Type", required=True, default="field", tracking=True,
    )
    model_id = fields.Many2one(
        "ir.model", string="Modèle", required=True, ondelete="cascade",
        domain=[("transient", "=", False)],
    )
    model_name = fields.Char(related="model_id.model", string="Modèle technique", store=True)
    technical_name = fields.Char(string="Nom technique", tracking=True)
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Actif", default=True)

    field_id = fields.Many2one(
        "ir.model.fields", string="Champ créé", ondelete="set null", readonly=True, copy=False,
    )
    view_customization_ids = fields.One2many(
        "studio.view.customization", "customization_id", string="Vues générées",
        context={"active_test": False},
    )
    view_customization_count = fields.Integer(
        string="Vues", compute="_compute_view_customization_count",
    )
    automation_id = fields.Many2one(
        "base.automation", string="Règle d'automatisation", ondelete="set null",
        readonly=True, copy=False,
    )
    server_action_id = fields.Many2one(
        "ir.actions.server", string="Action serveur", ondelete="set null",
        readonly=True, copy=False,
    )

    _name_model_kind_uniq = models.Constraint(
        "UNIQUE(name, model_id, kind)",
        "Une personnalisation portant ce nom existe déjà pour ce modèle.",
    )

    @api.depends("view_customization_ids")
    def _compute_view_customization_count(self):
        for record in self:
            record.view_customization_count = len(
                record.with_context(active_test=False).view_customization_ids
            )

    # ------------------------------------------------------------------
    # Activation / désactivation
    # ------------------------------------------------------------------
    def write(self, vals):
        res = super().write(vals)
        if "active" in vals:
            for record in self:
                customizations = record.with_context(active_test=False).view_customization_ids
                if customizations:
                    customizations.write({"active": record.active})
                if record.automation_id:
                    record.automation_id.sudo().active = record.active
        return res

    def action_toggle_active(self):
        for record in self:
            record.active = not record.active
        return True

    # ------------------------------------------------------------------
    # Suppression réversible
    # ------------------------------------------------------------------
    def action_remove_customization(self):
        """Défait proprement la personnalisation : vues d'abord, objet ensuite."""
        for record in self:
            record._studio_undo()
        self.with_context(studio_undone=True).unlink()
        return {"type": "ir.actions.act_window_close"}

    def _studio_undo(self):
        """Supprime les objets créés, dans l'ordre inverse de leur création."""
        self.ensure_one()
        # 1. les vues héritées (aucune vue orpheline ne doit subsister)
        customizations = self.with_context(active_test=False).view_customization_ids
        if customizations:
            customizations.unlink()
        # 2. le champ personnalisé (jamais un champ standard)
        field = self.field_id.sudo().exists()
        if field:
            self._studio_check_removable_field(field)
            field.unlink()
        # 3. l'automatisation puis son action serveur
        automation = self.automation_id.sudo().exists()
        if automation:
            automation.unlink()
        action = self.server_action_id.sudo().exists()
        if action:
            action.unlink()
        self.env.invalidate_all()
        return True

    def unlink(self):
        """Nettoie systématiquement les objets restants avant de perdre la trace."""
        if not self.env.context.get("studio_undone"):
            for record in self:
                record._studio_undo()
        return super().unlink()

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def action_open_target(self):
        self.ensure_one()
        if self.kind == "field" and self.field_id:
            res_model, res_id = "ir.model.fields", self.field_id.id
        elif self.kind == "automation" and self.automation_id:
            res_model, res_id = "base.automation", self.automation_id.id
        elif self.view_customization_ids:
            res_model = "studio.view.customization"
            res_id = self.view_customization_ids[0].id
        else:
            raise ValidationError(_("Cette personnalisation ne référence plus aucun objet."))
        return {
            "type": "ir.actions.act_window",
            "res_model": res_model,
            "res_id": res_id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_customizations(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Vues générées"),
            "res_model": "studio.view.customization",
            "view_mode": "list,form",
            "domain": [("customization_id", "=", self.id)],
            "context": {"active_test": False, "default_customization_id": self.id},
        }
