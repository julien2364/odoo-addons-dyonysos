# -*- coding: utf-8 -*-
"""Personnalisations de vues générées par Studio Lite (vues héritées)."""

from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

VIEW_KINDS = [
    ("add", "Ajout d'un champ"),
    ("hide", "Champ masqué"),
    ("required", "Champ obligatoire"),
    ("readonly", "Champ en lecture seule"),
]

VIEW_POSITIONS = [
    ("after", "Après un champ existant"),
    ("before", "Avant un champ existant"),
    ("inside", "Dans un onglet"),
    ("end", "En fin de formulaire"),
    ("attributes", "Modification d'attributs"),
]


class StudioViewCustomization(models.Model):
    """Une vue héritée générée par Studio Lite, activable et supprimable."""

    _name = "studio.view.customization"
    _inherit = ["studio.mixin"]
    _description = "Studio Lite - personnalisation de vue"
    _order = "id desc"

    name = fields.Char(string="Nom", required=True)
    kind = fields.Selection(VIEW_KINDS, string="Type", required=True, default="add")
    model_id = fields.Many2one(
        "ir.model", string="Modèle", required=True, ondelete="cascade",
        domain=[("transient", "=", False)],
    )
    model_name = fields.Char(related="model_id.model", string="Modèle technique", store=True)
    view_type = fields.Selection(
        [("form", "Formulaire"), ("list", "Liste"), ("kanban", "Kanban"), ("search", "Recherche")],
        string="Type de vue", required=True, default="form",
    )
    field_name = fields.Char(string="Champ concerné", required=True)
    anchor_field = fields.Char(string="Champ d'ancrage")
    page_name = fields.Char(string="Onglet")
    position = fields.Selection(VIEW_POSITIONS, string="Position", required=True, default="after")
    inherit_view_id = fields.Many2one("ir.ui.view", string="Vue de base", ondelete="set null")
    view_id = fields.Many2one(
        "ir.ui.view", string="Vue héritée", ondelete="set null", readonly=True, copy=False,
    )
    arch_preview = fields.Text(
        string="XML généré", compute="_compute_arch_preview", readonly=True,
    )
    customization_id = fields.Many2one(
        "studio.customization", string="Personnalisation", ondelete="cascade", copy=False,
    )
    active = fields.Boolean(string="Actif", default=True)

    @api.depends("view_id", "view_id.arch_db")
    def _compute_arch_preview(self):
        for record in self:
            record.arch_preview = record.view_id.sudo().arch if record.view_id else False

    # ------------------------------------------------------------------
    # Génération de l'arch
    # ------------------------------------------------------------------
    def _studio_field_element(self):
        """Élément <field> à insérer (mode « add »)."""
        self.ensure_one()
        node = etree.Element("field", name=self.field_name)
        if self.view_type == "list":
            node.set("optional", "show")
        return node

    def _studio_build_arch(self):
        """Construit l'arch XML de la vue héritée, par etree."""
        self.ensure_one()
        root = etree.Element("data")
        if self.kind == "add":
            if self.position in ("after", "before"):
                if not self.anchor_field:
                    raise ValidationError(_("Un champ d'ancrage est obligatoire pour cette position."))
                xpath = etree.SubElement(
                    root, "xpath",
                    expr="//field[@name='%s']" % self.anchor_field,
                    position=self.position,
                )
                xpath.append(self._studio_field_element())
            elif self.position == "inside":
                if not self.page_name:
                    raise ValidationError(_("Un onglet doit être choisi pour cette position."))
                xpath = etree.SubElement(
                    root, "xpath",
                    expr="//page[@name='%s']" % self.page_name,
                    position="inside",
                )
                group = etree.SubElement(xpath, "group")
                group.append(self._studio_field_element())
            elif self.position == "end":
                base_arch = self._studio_combined_arch(self.inherit_view_id)
                anchor_expr = "//sheet" if base_arch.xpath("//sheet") else "//%s" % base_arch.tag
                xpath = etree.SubElement(root, "xpath", expr=anchor_expr, position="inside")
                if self.view_type == "form":
                    container = etree.SubElement(xpath, "group", string="Personnalisations")
                    container.append(self._studio_field_element())
                else:
                    xpath.append(self._studio_field_element())
            else:
                raise ValidationError(_("Position « %s » incompatible avec un ajout de champ.", self.position))
        else:
            attribute = {"hide": "invisible", "required": "required", "readonly": "readonly"}[self.kind]
            xpath = etree.SubElement(
                root, "xpath",
                expr="//field[@name='%s']" % self.field_name,
                position="attributes",
            )
            attr = etree.SubElement(xpath, "attribute", name=attribute)
            attr.text = "1"
        return etree.tostring(root, pretty_print=True, encoding="unicode")

    def _studio_create_view(self):
        """Crée (ou recrée) la vue héritée correspondant à l'enregistrement."""
        self.ensure_one()
        self._studio_check_model(self.model_name)
        base_view = self.inherit_view_id or self._studio_get_target_view(self.model_name, self.view_type)
        if base_view.model != self.model_name:
            raise ValidationError(_(
                "La vue de base « %(view)s » ne concerne pas le modèle « %(model)s ».",
                view=base_view.name, model=self.model_name,
            ))
        self.inherit_view_id = base_view
        if self.kind != "add":
            # Le champ doit exister sur le modèle ET être présent dans la vue.
            self._studio_check_field_exists(self.model_name, self.field_name)
            self._studio_check_anchor(base_view, self.field_name)
        elif self.position in ("after", "before"):
            self._studio_check_anchor(base_view, self.anchor_field)
        elif self.position == "inside":
            available = self._studio_available_pages(base_view)
            if self.page_name not in available:
                raise ValidationError(_(
                    "L'onglet « %(page)s » n'existe pas dans la vue. Onglets disponibles : %(pages)s",
                    page=self.page_name or "", pages=", ".join(available) or _("aucun"),
                ))
        view = self.env["ir.ui.view"].sudo().create({
            "name": "Studio Lite: %s" % self.name,
            "model": self.model_name,
            "type": self.view_type,
            "inherit_id": base_view.id,
            "mode": "extension",
            "priority": 99,
            "arch": self._studio_build_arch(),
            "active": self.active,
        })
        self.view_id = view.id
        return view

    # ------------------------------------------------------------------
    # ORM
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if not record.view_id:
                record._studio_create_view()
        return records

    def write(self, vals):
        res = super().write(vals)
        if "active" in vals:
            for record in self:
                if record.view_id:
                    record.view_id.sudo().active = record.active
        return res

    def unlink(self):
        views = self.mapped("view_id").sudo()
        res = super().unlink()
        if views:
            views.unlink()
        return res

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_toggle_active(self):
        for record in self:
            record.active = not record.active
        return True

    def action_open_view(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "ir.ui.view",
            "res_id": self.view_id.id,
            "view_mode": "form",
            "target": "current",
        }
