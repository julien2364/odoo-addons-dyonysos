# -*- coding: utf-8 -*-
"""Tests fonctionnels de Studio Lite."""

from lxml import etree

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestStudioLite(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_model = cls.env["ir.model"]._get("res.partner")
        cls.users_model = cls.env["ir.model"]._get("res.users")
        cls.ir_model_model = cls.env["ir.model"]._get("ir.model")
        cls.follower_partner = cls.env["res.partner"].create({"name": "Abonné Studio Lite"})

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _wizard(self, **values):
        base = {
            "model_id": self.partner_model.id,
            "field_label": "Numéro de dossier",
            "ttype": "char",
            "placement": "end",
        }
        base.update(values)
        return self.env["studio.field.wizard"].create(base)

    def _customization_from(self, action):
        self.assertEqual(action["res_model"], "studio.customization")
        return self.env["studio.customization"].browse(action["res_id"])

    # ------------------------------------------------------------------
    # 1. Champ char + vue héritée
    # ------------------------------------------------------------------
    def test_01_create_char_field_and_view(self):
        wizard = self._wizard()
        self.assertEqual(wizard.field_name, "x_numero_de_dossier")
        customization = self._customization_from(wizard.action_create_field())

        self.assertIn("x_numero_de_dossier", self.env["res.partner"]._fields)
        self.assertEqual(customization.kind, "field")
        self.assertTrue(customization.field_id)
        self.assertEqual(customization.field_id.ttype, "char")

        view_customization = customization.view_customization_ids
        self.assertEqual(len(view_customization), 1)
        view = view_customization.view_id
        self.assertTrue(view)
        self.assertEqual(view.mode, "extension")
        self.assertIn("x_numero_de_dossier", view.arch)
        # la vue résultante reste valide pour le client web
        self.env["res.partner"].get_view(view_type="form")

    # ------------------------------------------------------------------
    # 2. Placement après un champ existant
    # ------------------------------------------------------------------
    def test_02_placement_after_existing_field(self):
        anchor = self.env["ir.model.fields"]._get("res.partner", "email")
        wizard = self._wizard(
            field_label="Code interne", placement="after", anchor_field_id=anchor.id)
        customization = self._customization_from(wizard.action_create_field())

        arch = etree.fromstring(customization.view_customization_ids.view_id.arch.encode())
        xpath_nodes = arch.xpath("//xpath")
        self.assertEqual(len(xpath_nodes), 1)
        self.assertEqual(xpath_nodes[0].get("expr"), "//field[@name='email']")
        self.assertEqual(xpath_nodes[0].get("position"), "after")
        self.assertEqual(xpath_nodes[0][0].get("name"), "x_code_interne")

    # ------------------------------------------------------------------
    # 3. Placement dans un onglet
    # ------------------------------------------------------------------
    def test_03_placement_inside_notebook_page(self):
        wizard = self._wizard(
            field_label="Commentaire interne", ttype="text",
            placement="inside", page_name="internal_notes")
        customization = self._customization_from(wizard.action_create_field())

        arch = customization.view_customization_ids.view_id.arch
        self.assertIn("//page[@name='internal_notes']", arch)
        self.assertIn("x_commentaire_interne", arch)

        # un onglet inexistant est refusé
        bad = self._wizard(field_label="Autre note", placement="inside", page_name="nope")
        with self.assertRaises(ValidationError):
            bad.action_create_field()

    # ------------------------------------------------------------------
    # 4. Champ selection
    # ------------------------------------------------------------------
    def test_04_create_selection_field(self):
        wizard = self._wizard(
            field_label="Niveau de risque", ttype="selection",
            selection_line_ids=[
                (0, 0, {"value": "low", "label": "Faible", "sequence": 10}),
                (0, 0, {"value": "high", "label": "Élevé", "sequence": 20}),
            ],
        )
        customization = self._customization_from(wizard.action_create_field())
        field = self.env["res.partner"]._fields["x_niveau_de_risque"]
        self.assertEqual(field.type, "selection")
        self.assertEqual(
            [value for value, _label in field.selection], ["low", "high"])
        self.assertEqual(len(customization.field_id.selection_ids), 2)

    def test_05_selection_requires_values(self):
        wizard = self._wizard(field_label="Sans valeur", ttype="selection")
        with self.assertRaises(ValidationError):
            wizard.action_create_field()

    # ------------------------------------------------------------------
    # 5. Champ many2one
    # ------------------------------------------------------------------
    def test_06_create_many2one_field(self):
        wizard = self._wizard(
            field_label="Chargé de compte", ttype="many2one",
            relation_model_id=self.users_model.id)
        self._customization_from(wizard.action_create_field())

        field = self.env["res.partner"]._fields["x_charge_de_compte"]
        self.assertEqual(field.type, "many2one")
        self.assertEqual(field.comodel_name, "res.users")

        # sans modèle lié, l'assistant refuse
        bad = self._wizard(field_label="Sans cible", ttype="many2one")
        with self.assertRaises(ValidationError):
            bad.action_create_field()

    # ------------------------------------------------------------------
    # 6. Contrôles de robustesse
    # ------------------------------------------------------------------
    def test_07_invalid_technical_name(self):
        with self.assertRaises(ValidationError):
            self._wizard(field_name="Mauvais Nom")
        with self.assertRaises(ValidationError):
            self._wizard(field_name="numero_sans_prefixe")

    def test_08_existing_field_is_refused(self):
        self._wizard(field_label="Doublon").action_create_field()
        duplicate = self._wizard(field_label="Doublon")
        self.assertEqual(duplicate.field_name, "x_doublon")
        with self.assertRaises(ValidationError):
            duplicate.action_create_field()

        # un champ standard existant est également protégé
        standard = self._wizard(field_label="Doublon standard")
        standard.field_name = "x_name"
        self.env["ir.model.fields"].sudo().create({
            "name": "x_name", "field_description": "X Name",
            "model_id": self.partner_model.id, "model": "res.partner",
            "ttype": "char", "state": "manual",
        })
        with self.assertRaises(ValidationError):
            standard.action_create_field()

    def test_09_technical_model_is_refused(self):
        wizard = self._wizard(model_id=self.ir_model_model.id, field_label="Interdit")
        with self.assertRaises(ValidationError):
            wizard.action_create_field()

    # ------------------------------------------------------------------
    # 7. Retouches de vues
    # ------------------------------------------------------------------
    def test_10_hide_existing_field(self):
        customization = self.env["studio.view.customization"].create({
            "name": "Masquer le site web",
            "kind": "hide",
            "model_id": self.partner_model.id,
            "view_type": "form",
            "field_name": "email",
            "position": "attributes",
        })
        self.assertTrue(customization.view_id)
        arch = etree.fromstring(customization.view_id.arch.encode())
        node = arch.xpath("//xpath")[0]
        self.assertEqual(node.get("position"), "attributes")
        self.assertEqual(node[0].get("name"), "invisible")
        self.assertEqual(node[0].text, "1")
        self.env["res.partner"].get_view(view_type="form")

    def test_11_required_and_readonly_tweaks(self):
        for kind, attribute in (("required", "required"), ("readonly", "readonly")):
            customization = self.env["studio.view.customization"].create({
                "name": "Champ %s" % kind,
                "kind": kind,
                "model_id": self.partner_model.id,
                "view_type": "form",
                "field_name": "function",
                "position": "attributes",
            })
            arch = etree.fromstring(customization.view_id.arch.encode())
            self.assertEqual(arch.xpath("//attribute")[0].get("name"), attribute)

    def test_12_unknown_field_tweak_is_refused(self):
        with self.assertRaises(ValidationError):
            self.env["studio.view.customization"].create({
                "name": "Champ inconnu",
                "kind": "hide",
                "model_id": self.partner_model.id,
                "view_type": "form",
                "field_name": "x_champ_inexistant",
                "position": "attributes",
            })

    # ------------------------------------------------------------------
    # 8. Automatisations
    # ------------------------------------------------------------------
    def test_13_create_automation_send_email(self):
        template = self.env["mail.template"].create({
            "name": "Bienvenue Studio Lite",
            "model_id": self.partner_model.id,
            "subject": "Bienvenue",
            "body_html": "<p>Bonjour</p>",
        })
        wizard = self.env["studio.automation.wizard"].create({
            "name": "Email à la création du contact",
            "model_id": self.partner_model.id,
            "trigger_kind": "create",
            "action_kind": "email",
            "mail_template_id": template.id,
        })
        customization = self._customization_from(wizard.action_create_automation())

        self.assertEqual(customization.kind, "automation")
        automation = customization.automation_id
        self.assertTrue(automation)
        self.assertEqual(automation.trigger, "on_create")
        self.assertEqual(automation.model_id, self.partner_model)
        action = customization.server_action_id
        self.assertTrue(action)
        self.assertEqual(action.state, "mail_post")
        self.assertEqual(action.template_id, template)
        self.assertEqual(action.base_automation_id, automation)

    def test_14_automation_update_field_and_validation(self):
        field = self.env["ir.model.fields"]._get("res.partner", "comment")
        wizard = self.env["studio.automation.wizard"].create({
            "name": "Marquer les contacts modifiés",
            "model_id": self.partner_model.id,
            "trigger_kind": "field_change",
            "trigger_field_id": self.env["ir.model.fields"]._get("res.partner", "name").id,
            "action_kind": "update",
            "update_field_id": field.id,
            "update_value": "Vérifié",
        })
        customization = self._customization_from(wizard.action_create_automation())
        automation = customization.automation_id
        self.assertEqual(automation.trigger, "on_create_or_write")
        self.assertIn("name", automation.trigger_field_ids.mapped("name"))
        self.assertEqual(customization.server_action_id.state, "object_write")

        # un déclencheur « champ change » sans champ est refusé
        bad = self.env["studio.automation.wizard"].create({
            "name": "Incomplète",
            "model_id": self.partner_model.id,
            "trigger_kind": "field_change",
            "action_kind": "update",
            "update_field_id": field.id,
        })
        with self.assertRaises(ValidationError):
            bad.action_create_automation()

    # ------------------------------------------------------------------
    # 9. Réversibilité
    # ------------------------------------------------------------------
    def test_15_remove_field_customization(self):
        wizard = self._wizard(field_label="À supprimer")
        customization = self._customization_from(wizard.action_create_field())
        field = customization.field_id
        view = customization.view_customization_ids.view_id
        self.assertIn("x_a_supprimer", self.env["res.partner"]._fields)

        customization.action_remove_customization()

        self.assertFalse(view.exists())
        self.assertFalse(field.exists())
        self.assertFalse(customization.exists())
        self.assertNotIn("x_a_supprimer", self.env["res.partner"]._fields)
        # la vue de base reste exploitable
        self.env["res.partner"].get_view(view_type="form")

    def test_16_remove_automation_customization(self):
        wizard = self.env["studio.automation.wizard"].create({
            "name": "Automatisation jetable",
            "model_id": self.partner_model.id,
            "trigger_kind": "create",
            "action_kind": "follower",
            "follower_partner_ids": [(6, 0, self.follower_partner.ids)],
        })
        customization = self._customization_from(wizard.action_create_automation())
        automation = customization.automation_id
        action = customization.server_action_id

        customization.action_remove_customization()

        self.assertFalse(automation.exists())
        self.assertFalse(action.exists())

    def test_17_toggle_view_customization(self):
        wizard = self._wizard(field_label="Champ bascule")
        customization = self._customization_from(wizard.action_create_field())
        view_customization = customization.view_customization_ids
        view = view_customization.view_id
        self.assertTrue(view.active)

        view_customization.action_toggle_active()
        self.assertFalse(view_customization.active)
        self.assertFalse(view.active)

        view_customization.action_toggle_active()
        self.assertTrue(view_customization.active)
        self.assertTrue(view.active)

    def test_18_toggle_customization_propagates(self):
        wizard = self._wizard(field_label="Champ propagé")
        customization = self._customization_from(wizard.action_create_field())
        view_customization = customization.with_context(active_test=False).view_customization_ids

        customization.action_toggle_active()
        self.assertFalse(customization.active)
        self.assertFalse(view_customization.active)
        self.assertFalse(view_customization.view_id.active)

        customization.with_context(active_test=False).action_toggle_active()
        self.assertTrue(view_customization.view_id.active)

    def test_19_standard_field_cannot_be_removed(self):
        customization = self.env["studio.customization"].create({
            "name": "Fausse trace",
            "kind": "field",
            "model_id": self.partner_model.id,
            "technical_name": "email",
            "field_id": self.env["ir.model.fields"]._get("res.partner", "email").id,
        })
        with self.assertRaises(ValidationError):
            customization.action_remove_customization()
        self.assertTrue(self.env["ir.model.fields"]._get("res.partner", "email").exists())

    def test_20_no_orphan_view_on_failure(self):
        """Si la vue ne peut pas être générée, le champ n'est pas laissé derrière."""
        wizard = self._wizard(
            field_label="Echec ancrage", placement="after",
            anchor_field_id=self.env["ir.model.fields"]._get("res.partner", "message_ids").id)
        views_before = self.env["ir.ui.view"].search_count([("model", "=", "res.partner")])
        with self.assertRaises(ValidationError):
            wizard.action_create_field()
        self.env.invalidate_all()
        self.assertEqual(
            views_before,
            self.env["ir.ui.view"].search_count([("model", "=", "res.partner")]))
        self.assertFalse(self.env["studio.customization"].search([
            ("technical_name", "=", "x_echec_ancrage")]))
