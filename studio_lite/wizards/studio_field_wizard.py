# -*- coding: utf-8 -*-
"""Assistant de création d'un champ personnalisé et de son affichage."""

import re
import unicodedata

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from ..models.studio_common import FIELD_TYPES, RELATIONAL_TYPES


def slugify_field(label):
    """« Numéro de dossier » -> « x_numero_de_dossier »."""
    if not label:
        return False
    text = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    text = re.sub(r"_+", "_", text)
    if not text:
        return False
    return text if text.startswith("x_") else "x_%s" % text


class StudioFieldSelectionLine(models.TransientModel):
    """Une valeur de la liste de sélection, saisie ligne à ligne."""

    _name = "studio.field.selection.line"
    _description = "Studio Lite - valeur de sélection"
    _order = "sequence, id"

    wizard_id = fields.Many2one("studio.field.wizard", required=True, ondelete="cascade")
    sequence = fields.Integer(string="Séquence", default=10)
    value = fields.Char(string="Valeur technique", required=True)
    label = fields.Char(string="Libellé", required=True)

    @api.onchange("label")
    def _onchange_label(self):
        for line in self:
            if line.label and not line.value:
                slug = slugify_field(line.label)
                line.value = slug[2:] if slug else False


class StudioFieldWizard(models.TransientModel):
    """Crée un champ `x_...` et la vue héritée qui l'affiche, en une opération."""

    _name = "studio.field.wizard"
    _inherit = ["studio.mixin"]
    _description = "Studio Lite - nouveau champ"

    # --- cible ---------------------------------------------------------
    model_id = fields.Many2one(
        "ir.model", string="Modèle", required=True, ondelete="cascade",
        domain=[("transient", "=", False), ("abstract", "=", False)],
    )
    model_name = fields.Char(related="model_id.model", string="Modèle technique")

    # --- identité du champ --------------------------------------------
    field_label = fields.Char(string="Libellé du champ", required=True)
    field_name = fields.Char(
        string="Nom technique", compute="_compute_field_name",
        store=True, readonly=False,
        help="Déduit du libellé. Doit commencer par « x_ ».",
    )
    ttype = fields.Selection(FIELD_TYPES, string="Type", required=True, default="char")

    # --- options par type ---------------------------------------------
    relation_model_id = fields.Many2one(
        "ir.model", string="Modèle lié", ondelete="cascade",
        domain=[("transient", "=", False)],
    )
    relation_field_name = fields.Char(
        string="Champ inverse",
        help="Pour une liste liée (one2many) : nom du many2one sur le modèle lié.",
    )
    selection_line_ids = fields.One2many(
        "studio.field.selection.line", "wizard_id", string="Valeurs de sélection",
    )
    help_text = fields.Char(string="Info-bulle")
    required = fields.Boolean(string="Obligatoire")
    copied = fields.Boolean(string="Copié lors d'une duplication", default=True)
    tracked = fields.Boolean(string="Suivi au chatter")

    # --- placement ------------------------------------------------------
    view_id = fields.Many2one(
        "ir.ui.view", string="Vue cible", compute="_compute_view_id",
        store=True, readonly=False,
    )
    view_type = fields.Selection(
        [("form", "Formulaire"), ("list", "Liste")],
        string="Type de vue", required=True, default="form",
    )
    placement = fields.Selection(
        [("after", "Après un champ existant"),
         ("inside", "Dans un onglet"),
         ("end", "En fin de formulaire")],
        string="Emplacement", required=True, default="end",
    )
    anchor_field_id = fields.Many2one(
        "ir.model.fields", string="Après le champ",
        domain="[('model_id', '=', model_id), ('ttype', 'not in', ['one2many', 'many2many'])]",
    )
    page_name = fields.Char(string="Onglet")
    available_pages = fields.Char(
        string="Onglets disponibles", compute="_compute_available_pages", readonly=True,
    )

    # ------------------------------------------------------------------
    # Calculs
    # ------------------------------------------------------------------
    @api.depends("field_label")
    def _compute_field_name(self):
        for wizard in self:
            wizard.field_name = slugify_field(wizard.field_label)

    @api.depends("model_id", "view_type")
    def _compute_view_id(self):
        for wizard in self:
            wizard.view_id = False
            if not wizard.model_name:
                continue
            try:
                wizard.view_id = wizard._studio_get_target_view(
                    wizard.model_name, wizard.view_type)
            except ValidationError:
                wizard.view_id = False

    @api.depends("view_id")
    def _compute_available_pages(self):
        for wizard in self:
            if wizard.view_id and wizard.view_type == "form":
                pages = wizard._studio_available_pages(wizard.view_id)
                wizard.available_pages = ", ".join(pages) or _("aucun onglet")
            else:
                wizard.available_pages = False

    @api.onchange("view_type")
    def _onchange_view_type(self):
        for wizard in self:
            if wizard.view_type == "list" and wizard.placement == "inside":
                wizard.placement = "end"

    # ------------------------------------------------------------------
    # Contrôles
    # ------------------------------------------------------------------
    @api.constrains("field_name")
    def _check_field_name(self):
        for wizard in self:
            wizard._studio_check_field_name(wizard.field_name)

    def _studio_validate(self):
        self.ensure_one()
        self._studio_check_model(self.model_name)
        self._studio_check_field_name(self.field_name)
        self._studio_check_field_is_new(self.model_name, self.field_name)
        if self.ttype in RELATIONAL_TYPES and not self.relation_model_id:
            raise ValidationError(_(
                "Un champ de type « %s » exige un modèle lié.", self.ttype))
        if self.ttype == "one2many" and not self.relation_field_name:
            raise ValidationError(_(
                "Une liste liée (one2many) exige le nom du champ inverse sur le modèle lié."))
        if self.ttype == "selection" and not self.selection_line_ids:
            raise ValidationError(_(
                "Un champ de type sélection exige au moins une valeur."))
        if self.ttype == "selection":
            values = self.selection_line_ids.mapped("value")
            if len(set(values)) != len(values):
                raise ValidationError(_("Deux valeurs de sélection sont identiques."))
        if self.ttype == "monetary":
            model = self.env[self.model_name]
            if "currency_id" not in model._fields:
                raise ValidationError(_(
                    "Le modèle « %s » n'a pas de champ « currency_id » : un champ "
                    "monétaire ne peut pas y être ajouté.", self.model_name))
        if self.tracked and not self.env[self.model_name]._is_an_ordinary_table():
            raise ValidationError(_("Ce modèle ne supporte pas le suivi au chatter."))
        if self.tracked and "message_ids" not in self.env[self.model_name]._fields:
            raise ValidationError(_(
                "Le modèle « %s » n'a pas de chatter : le suivi est impossible.",
                self.model_name))
        if self.placement == "after" and not self.anchor_field_id:
            raise ValidationError(_("Choisissez le champ après lequel placer le nouveau champ."))
        if self.placement == "inside" and not self.page_name:
            raise ValidationError(_("Choisissez l'onglet dans lequel placer le nouveau champ."))
        if not self.view_id:
            raise ValidationError(_(
                "Aucune vue « %(type)s » n'a été trouvée pour « %(model)s ».",
                type=self.view_type, model=self.model_name))

    # ------------------------------------------------------------------
    # Création
    # ------------------------------------------------------------------
    def _studio_field_values(self):
        self.ensure_one()
        values = {
            "name": self.field_name,
            "field_description": self.field_label,
            "model_id": self.model_id.id,
            "model": self.model_name,
            "ttype": self.ttype,
            "state": "manual",
            "help": self.help_text or False,
            "required": self.required,
            "copied": self.copied,
        }
        if self.ttype in RELATIONAL_TYPES:
            values["relation"] = self.relation_model_id.model
        if self.ttype == "many2one":
            values["on_delete"] = "set null"
        if self.ttype == "one2many":
            values["relation_field"] = self.relation_field_name
            values["copied"] = False
        if self.ttype == "selection":
            values["selection_ids"] = [
                (0, 0, {"value": line.value, "name": line.label, "sequence": line.sequence})
                for line in self.selection_line_ids
            ]
        if self.tracked:
            values["tracking"] = 100
        return values

    def action_create_field(self):
        """Crée le champ, la vue héritée et la trace de personnalisation."""
        self.ensure_one()
        self._studio_validate()

        field = self.env["ir.model.fields"].sudo().create(self._studio_field_values())
        # le registre est rechargé par ir.model.fields.create ; on le confirme
        self.env.flush_all()
        self.env.registry.clear_cache()
        if self.field_name not in self.env[self.model_name]._fields:
            raise ValidationError(_(
                "Le champ « %s » n'a pas pu être enregistré dans le registre Odoo.",
                self.field_name))

        customization = self.env["studio.customization"].create({
            "name": self.field_label,
            "kind": "field",
            "model_id": self.model_id.id,
            "technical_name": self.field_name,
            "description": _(
                "Champ %(type)s « %(label)s » ajouté sur %(model)s.",
                type=self.ttype, label=self.field_label, model=self.model_name),
            "field_id": field.id,
        })
        try:
            self.env["studio.view.customization"].create({
                "name": "%s (%s)" % (self.field_label, self.field_name),
                "kind": "add",
                "model_id": self.model_id.id,
                "view_type": self.view_type,
                "field_name": self.field_name,
                "anchor_field": self.anchor_field_id.name if self.placement == "after" else False,
                "page_name": self.page_name if self.placement == "inside" else False,
                "position": self.placement,
                "inherit_view_id": self.view_id.id,
                "customization_id": customization.id,
            })
        except Exception:
            # aucune vue orpheline, aucun champ orphelin : on défait tout
            customization.with_context(studio_rollback=True).unlink()
            raise

        return {
            "type": "ir.actions.act_window",
            "res_model": "studio.customization",
            "res_id": customization.id,
            "view_mode": "form",
            "target": "current",
        }
