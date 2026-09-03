# -*- coding: utf-8 -*-
"""Assistant « quand ... alors ... » au-dessus de base.automation."""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

TRIGGER_KINDS = [
    ("create", "Un enregistrement est créé"),
    ("write", "Un enregistrement est modifié"),
    ("field_change", "Un champ change de valeur"),
    ("condition", "Une condition devient vraie"),
]

ACTION_KINDS = [
    ("email", "Envoyer un email (modèle de courriel)"),
    ("update", "Mettre à jour un champ"),
    ("activity", "Créer une activité"),
    ("follower", "Ajouter un abonné"),
]

#: Actions qui exigent un modèle doté d'un chatter.
MAIL_THREAD_ACTIONS = ("email", "activity", "follower")

TRIGGER_MAP = {
    "create": "on_create",
    "write": "on_write",
    "field_change": "on_create_or_write",
    "condition": "on_create_or_write",
}


class StudioAutomationWizard(models.TransientModel):
    """Crée une base.automation et son ir.actions.server sans écrire de code."""

    _name = "studio.automation.wizard"
    _inherit = ["studio.mixin"]
    _description = "Studio Lite - nouvelle automatisation"

    name = fields.Char(string="Nom de la règle", required=True)
    model_id = fields.Many2one(
        "ir.model", string="Modèle", required=True, ondelete="cascade",
        domain=[("transient", "=", False), ("abstract", "=", False)],
    )
    model_name = fields.Char(related="model_id.model", string="Modèle technique")
    model_is_mail_thread = fields.Boolean(related="model_id.is_mail_thread")

    # --- QUAND ----------------------------------------------------------
    trigger_kind = fields.Selection(
        TRIGGER_KINDS, string="Déclencheur", required=True, default="create",
    )
    trigger_field_id = fields.Many2one(
        "ir.model.fields", string="Champ surveillé",
        domain="[('model_id', '=', model_id), ('store', '=', True)]",
    )
    filter_domain = fields.Char(
        string="Condition", default="[]",
        help="Filtre Odoo appliqué à l'enregistrement, par exemple [('state','=','done')].",
    )

    # --- ALORS ----------------------------------------------------------
    action_kind = fields.Selection(
        ACTION_KINDS, string="Action", required=True, default="email",
    )
    mail_template_id = fields.Many2one(
        "mail.template", string="Modèle de courriel",
        domain="[('model_id', '=', model_id)]",
    )
    update_field_id = fields.Many2one(
        "ir.model.fields", string="Champ à mettre à jour",
        domain="[('model_id', '=', model_id), ('store', '=', True), "
               "('ttype', 'not in', ['one2many', 'many2many', 'binary'])]",
    )
    update_value = fields.Char(string="Nouvelle valeur")
    activity_type_id = fields.Many2one("mail.activity.type", string="Type d'activité")
    activity_summary = fields.Char(string="Titre de l'activité")
    activity_user_id = fields.Many2one("res.users", string="Responsable de l'activité")
    follower_partner_ids = fields.Many2many("res.partner", string="Abonnés à ajouter")

    # ------------------------------------------------------------------
    # Contrôles
    # ------------------------------------------------------------------
    def _studio_validate(self):
        self.ensure_one()
        self._studio_check_model(self.model_name)
        if self.action_kind in MAIL_THREAD_ACTIONS and not self.model_id.is_mail_thread:
            raise ValidationError(_(
                "Le modèle « %s » n'a pas de chatter : les actions d'email, "
                "d'activité et d'abonnés ne s'y appliquent pas.", self.model_name))
        if self.trigger_kind == "field_change" and not self.trigger_field_id:
            raise ValidationError(_("Choisissez le champ à surveiller."))
        if self.trigger_kind == "condition" and (not self.filter_domain or self.filter_domain == "[]"):
            raise ValidationError(_("Saisissez la condition à surveiller."))
        if self.action_kind == "email" and not self.mail_template_id:
            raise ValidationError(_("Choisissez le modèle de courriel à envoyer."))
        if self.action_kind == "update" and not self.update_field_id:
            raise ValidationError(_("Choisissez le champ à mettre à jour."))
        if self.action_kind == "activity" and not self.activity_type_id:
            raise ValidationError(_("Choisissez le type d'activité à créer."))
        if self.action_kind == "activity" and not self.activity_user_id:
            raise ValidationError(_("Choisissez le responsable de l'activité."))
        if self.action_kind == "follower" and not self.follower_partner_ids:
            raise ValidationError(_("Choisissez au moins un abonné à ajouter."))

    # ------------------------------------------------------------------
    # Valeurs générées
    # ------------------------------------------------------------------
    def _studio_automation_values(self):
        self.ensure_one()
        values = {
            "name": self.name,
            "model_id": self.model_id.id,
            "trigger": TRIGGER_MAP[self.trigger_kind],
            "active": True,
        }
        if self.trigger_kind == "field_change":
            values["trigger_field_ids"] = [(6, 0, [self.trigger_field_id.id])]
        if self.trigger_kind == "condition":
            values["filter_domain"] = self.filter_domain
        return values

    def _studio_server_action_values(self, automation):
        self.ensure_one()
        values = {
            "name": self.name,
            "model_id": self.model_id.id,
            "base_automation_id": automation.id,
            "usage": "base_automation",
        }
        if self.action_kind == "email":
            values.update({
                "state": "mail_post",
                "template_id": self.mail_template_id.id,
                "mail_post_method": "email",
            })
        elif self.action_kind == "update":
            values.update({
                "state": "object_write",
                "update_path": self.update_field_id.name,
                "evaluation_type": "value",
                "value": self.update_value or "",
            })
        elif self.action_kind == "activity":
            values.update({
                "state": "next_activity",
                "activity_type_id": self.activity_type_id.id,
                "activity_summary": self.activity_summary or self.name,
                "activity_user_type": "specific",
                "activity_user_id": self.activity_user_id.id,
            })
        else:
            values.update({
                "state": "followers",
                "followers_type": "specific",
                "partner_ids": [(6, 0, self.follower_partner_ids.ids)],
            })
        return values

    def _studio_description(self):
        self.ensure_one()
        trigger = dict(TRIGGER_KINDS)[self.trigger_kind]
        action = dict(ACTION_KINDS)[self.action_kind]
        return _("Quand : %(trigger)s sur %(model)s — Alors : %(action)s.",
                 trigger=trigger, model=self.model_name, action=action)

    # ------------------------------------------------------------------
    # Création
    # ------------------------------------------------------------------
    def action_create_automation(self):
        self.ensure_one()
        self._studio_validate()

        automation = self.env["base.automation"].sudo().create(self._studio_automation_values())
        try:
            server_action = self.env["ir.actions.server"].sudo().create(
                self._studio_server_action_values(automation))
        except Exception:
            automation.unlink()
            raise

        customization = self.env["studio.customization"].create({
            "name": self.name,
            "kind": "automation",
            "model_id": self.model_id.id,
            "technical_name": "base.automation/%s" % automation.id,
            "description": self._studio_description(),
            "automation_id": automation.id,
            "server_action_id": server_action.id,
        })
        return {
            "type": "ir.actions.act_window",
            "res_model": "studio.customization",
            "res_id": customization.id,
            "view_mode": "form",
            "target": "current",
        }
