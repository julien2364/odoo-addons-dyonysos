# -*- coding: utf-8 -*-
"""Validations et utilitaires partagés par les modèles et assistants Studio Lite."""

import re

from odoo import _, models
from odoo.exceptions import ValidationError

#: Nom technique autorisé pour un champ personnalisé.
FIELD_NAME_RE = re.compile(r"^x_[a-z0-9_]+$")

#: Préfixes de modèles techniques sur lesquels toute opération est refusée.
FORBIDDEN_MODEL_PREFIXES = ("ir.", "base.", "bus.", "studio.")

#: Modèles explicitement protégés (sécurité / infrastructure).
FORBIDDEN_MODELS = (
    "res.groups",
    "res.groups.privilege",
    "res.users",
    "res.users.settings",
    "res.company",
    "ir.model",
    "ir.model.fields",
    "ir.ui.view",
    "ir.actions.server",
    "base.automation",
)

#: Types de champs proposés par l'assistant.
FIELD_TYPES = [
    ("char", "Texte court"),
    ("text", "Texte long"),
    ("integer", "Nombre entier"),
    ("float", "Nombre décimal"),
    ("monetary", "Montant"),
    ("boolean", "Case à cocher"),
    ("date", "Date"),
    ("datetime", "Date et heure"),
    ("selection", "Sélection"),
    ("many2one", "Lien vers un enregistrement"),
    ("one2many", "Liste liée"),
    ("many2many", "Liens multiples"),
    ("html", "HTML"),
    ("binary", "Fichier"),
]

RELATIONAL_TYPES = ("many2one", "one2many", "many2many")


class StudioMixin(models.AbstractModel):
    """Contrôles communs : modèles autorisés, noms techniques, ancrages de vue."""

    _name = "studio.mixin"
    _description = "Studio Lite - contrôles communs"

    # ------------------------------------------------------------------
    # Modèles
    # ------------------------------------------------------------------
    def _studio_check_model(self, model_name):
        """Refuse les modèles techniques et transients. Renvoie le modèle."""
        if not model_name:
            raise ValidationError(_("Aucun modèle sélectionné."))
        if model_name in FORBIDDEN_MODELS or model_name.startswith(FORBIDDEN_MODEL_PREFIXES):
            raise ValidationError(_(
                "Le modèle « %s » est un modèle technique d'Odoo : Studio Lite refuse "
                "de le modifier pour ne pas compromettre le fonctionnement de la base.",
                model_name,
            ))
        model = self.env.get(model_name)
        if model is None:
            raise ValidationError(_("Le modèle « %s » n'existe pas.", model_name))
        if model._transient:
            raise ValidationError(_(
                "Le modèle « %s » est un modèle temporaire (assistant) : "
                "il ne peut pas recevoir de personnalisation durable.",
                model_name,
            ))
        if model._abstract:
            raise ValidationError(_(
                "Le modèle « %s » est abstrait : il ne peut pas être personnalisé.",
                model_name,
            ))
        return model

    # ------------------------------------------------------------------
    # Noms techniques
    # ------------------------------------------------------------------
    def _studio_check_field_name(self, field_name):
        if not field_name or not FIELD_NAME_RE.match(field_name):
            raise ValidationError(_(
                "Le nom technique « %s » est invalide. Il doit commencer par « x_ » "
                "et ne contenir que des minuscules, des chiffres et des « _ » "
                "(exemple : x_numero_dossier).",
                field_name or "",
            ))
        return field_name

    def _studio_check_field_is_new(self, model_name, field_name):
        model = self.env[model_name]
        if field_name in model._fields:
            raise ValidationError(_(
                "Le champ « %(field)s » existe déjà sur le modèle « %(model)s ». "
                "Choisissez un autre nom.",
                field=field_name, model=model_name,
            ))
        existing = self.env["ir.model.fields"].sudo().search_count([
            ("model", "=", model_name), ("name", "=", field_name),
        ])
        if existing:
            raise ValidationError(_(
                "Le champ « %(field)s » est déjà déclaré sur « %(model)s ».",
                field=field_name, model=model_name,
            ))

    def _studio_check_field_exists(self, model_name, field_name):
        model = self._studio_check_model(model_name)
        if field_name not in model._fields:
            raise ValidationError(_(
                "Le champ « %(field)s » n'existe pas sur le modèle « %(model)s ».",
                field=field_name, model=model_name,
            ))
        return model._fields[field_name]

    def _studio_check_removable_field(self, field):
        """Interdit la suppression d'un champ standard (non préfixé x_)."""
        if not field:
            return
        if not field.name.startswith("x_") or field.state != "manual":
            raise ValidationError(_(
                "Le champ « %s » n'a pas été créé par Studio Lite : sa suppression "
                "est refusée.", field.name,
            ))

    # ------------------------------------------------------------------
    # Vues
    # ------------------------------------------------------------------
    def _studio_get_target_view(self, model_name, view_type="form"):
        """Renvoie la vue de base (sans parent hérité) du modèle pour ce type."""
        self._studio_check_model(model_name)
        view = self.env["ir.ui.view"].sudo().search([
            ("model", "=", model_name),
            ("type", "=", view_type),
            ("inherit_id", "=", False),
            ("mode", "=", "primary"),
        ], order="priority, id", limit=1)
        if not view:
            raise ValidationError(_(
                "Aucune vue « %(type)s » de base n'a été trouvée pour le modèle "
                "« %(model)s ».", type=view_type, model=model_name,
            ))
        return view

    def _studio_combined_arch(self, view):
        return view.sudo()._get_combined_arch()

    def _studio_check_anchor(self, view, field_name):
        """Vérifie que le champ d'ancrage est bien présent dans la vue cible."""
        arch = self._studio_combined_arch(view)
        if not arch.xpath("//field[@name='%s']" % field_name):
            raise ValidationError(_(
                "Le champ d'ancrage « %(field)s » n'est pas affiché dans la vue "
                "« %(view)s » : impossible d'y accrocher la personnalisation.",
                field=field_name, view=view.name,
            ))
        return True

    def _studio_available_pages(self, view):
        """Noms des onglets (`<page name="...">`) disponibles dans la vue."""
        arch = self._studio_combined_arch(view)
        return [p.get("name") for p in arch.xpath("//page[@name]") if p.get("name")]
