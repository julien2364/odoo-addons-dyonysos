# -*- coding: utf-8 -*-
import io
import os
import tempfile
import zipfile
from unittest.mock import MagicMock, patch

from odoo import Command, fields
from odoo.tests import TransactionCase, tagged

MINIMAL_PDF = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)


@tagged("post_install", "-at_install")
class TestDougsBridge(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.icp = cls.env["ir.config_parameter"].sudo()
        cls.icp.set_param("dougs_bridge.transport", "download")
        cls.company = cls.env.company
        cls.customer = cls.env["res.partner"].create({"name": "Client Test", "email": "client@example.com"})
        cls.supplier = cls.env["res.partner"].create({"name": "Fournisseur Test", "vat": "FR23334175221"})
        cls.tax20 = cls.env["account.tax"].create({"name": "TVA 20 (test)", "amount": 20, "type_tax_use": "sale", "company_id": cls.company.id})
        cls.out_invoice = cls.env["account.move"].create({
            "move_type": "out_invoice", "partner_id": cls.customer.id, "invoice_date": fields.Date.today(),
            "invoice_line_ids": [Command.create({"name": "Pet Stone", "quantity": 2, "price_unit": 24.92, "tax_ids": [Command.set(cls.tax20.ids)]})],
        })
        cls.out_invoice.action_post()
        cls.in_invoice = cls.env["account.move"].create({
            "move_type": "in_invoice", "partner_id": cls.supplier.id, "invoice_date": fields.Date.today(), "ref": "F-0042",
            "invoice_line_ids": [Command.create({"name": "Stock", "quantity": 1, "price_unit": 100.0})],
        })
        cls.in_invoice.action_post()
        cls.bill_attachment = cls.env["ir.attachment"].create({
            "name": "facture-fournisseur.pdf", "raw": MINIMAL_PDF, "mimetype": "application/pdf",
            "res_model": "account.move", "res_id": cls.in_invoice.id,
        })
        cls.in_invoice._message_set_main_attachment_id(cls.bill_attachment, force=True)

    def _patch_pdf(self):
        # wkhtmltopdf may be missing in CI: render a stub PDF.
        return patch.object(type(self.env["ir.actions.report"]), "_render_qweb_pdf", return_value=(MINIMAL_PDF, "pdf"))

    def test_01_collect_and_download(self):
        batch = self.env["dougs.export.batch"].create({})
        batch.action_collect()
        types = set(batch.line_ids.mapped("doc_type"))
        self.assertIn("out_invoice", types)
        self.assertIn("in_invoice", types)
        with self._patch_pdf():
            batch.action_send()
        self.assertEqual(batch.state, "sent")
        self.assertTrue(batch.zip_attachment_id)
        with zipfile.ZipFile(io.BytesIO(batch.zip_attachment_id.raw)) as zf:
            names = zf.namelist()
            self.assertIn("journal.csv", names)
            self.assertTrue(any(n.startswith("out_invoice_") and n.endswith(".pdf") for n in names))
            self.assertTrue(any(n.startswith("out_invoice_") and n.endswith("_facturx.xml") for n in names))
            self.assertTrue(any(n.startswith("in_invoice_") for n in names))
            journal = zf.read("journal.csv").decode("utf-8-sig")
        self.assertIn("F-0042", journal)
        self.assertIn("Fournisseur Test", journal)
        self.assertEqual(self.in_invoice.dougs_state, "sent")
        self.assertEqual(self.out_invoice.dougs_state, "sent")

    def test_02_already_sent_documents_are_skipped(self):
        batch = self.env["dougs.export.batch"].create({})
        with self._patch_pdf():
            batch.action_send()
        self.assertEqual(batch.state, "sent")
        second = self.env["dougs.export.batch"].create({})
        second.action_collect()
        self.assertFalse(second.line_ids.filtered(lambda l: l.res_id in (self.in_invoice.id, self.out_invoice.id)))

    def test_03_folder_transport(self):
        tmp = tempfile.mkdtemp()
        self.icp.set_param("dougs_bridge.folder_path", tmp)
        batch = self.env["dougs.export.batch"].create({"transport": "folder"})
        with self._patch_pdf():
            batch.action_send()
        self.assertEqual(batch.state, "sent", batch.log)
        written = os.listdir(os.path.join(tmp, batch.name))
        self.assertIn("journal.csv", written)
        self.assertGreaterEqual(len(written), 3)

    def test_04_email_transport(self):
        self.icp.set_param("dougs_bridge.email_to", "collecte@cabinet.example")
        batch = self.env["dougs.export.batch"].create({"transport": "email"})
        with self._patch_pdf(), patch.object(type(self.env["mail.template"]), "send_mail", return_value=1) as send_mail:
            batch.action_send()
        self.assertEqual(batch.state, "sent", batch.log)
        self.assertTrue(send_mail.called)
        kwargs = send_mail.call_args.kwargs
        self.assertEqual(kwargs["email_values"]["email_to"], "collecte@cabinet.example")

    def test_05_apifirst_transport(self):
        self.icp.set_param("dougs_bridge.apifirst_base_url", "https://api.example.test")
        self.icp.set_param("dougs_bridge.apifirst_api_key", "secret")
        batch = self.env["dougs.export.batch"].create({"transport": "apifirst"})
        response = MagicMock(status_code=201)
        response.json.return_value = {"id": "doc_123"}
        with self._patch_pdf(), patch("odoo.addons.dougs_bridge.models.dougs_transport.requests.post", return_value=response) as post:
            batch.action_send()
        self.assertEqual(batch.state, "sent", batch.log)
        self.assertGreaterEqual(post.call_count, 2)
        urls = {c.args[0] for c in post.call_args_list}
        self.assertIn("https://api.example.test/v1/invoices/outgoing", urls)
        self.assertIn("https://api.example.test/v1/invoices/incoming", urls)
        self.assertTrue(all(l.remote_id == "doc_123" for l in batch.line_ids))

    def test_06_apifirst_error_marks_lines(self):
        self.icp.set_param("dougs_bridge.apifirst_base_url", "https://api.example.test")
        self.icp.set_param("dougs_bridge.apifirst_api_key", "secret")
        batch = self.env["dougs.export.batch"].create({"transport": "apifirst"})
        response = MagicMock(status_code=401, text="unauthorized")
        with self._patch_pdf(), patch("odoo.addons.dougs_bridge.models.dougs_transport.requests.post", return_value=response):
            batch.action_send()
        self.assertEqual(batch.state, "error")
        self.assertTrue(all(l.state == "error" for l in batch.line_ids))
        self.assertIn("401", batch.log)

    def test_07_button_on_invoice(self):
        with self._patch_pdf():
            action = self.in_invoice.action_send_to_dougs()
        batch = self.env["dougs.export.batch"].browse(action["res_id"])
        self.assertEqual(batch.state, "sent")
        self.assertEqual(batch.line_ids.res_id, self.in_invoice.id)

    def test_08_cron_creates_and_sends_batch(self):
        before = self.env["dougs.export.batch"].search_count([])
        with self._patch_pdf():
            self.env["dougs.export.batch"]._cron_run()
        after = self.env["dougs.export.batch"].search_count([])
        self.assertEqual(after, before + 1)

    def test_09_plain_employee_can_open_an_invoice(self):
        """Regression: dougs_state must not raise for a user without accounting rights."""
        employee = self.env["res.users"].create({
            "name": "Employe Lambda", "login": "employe-lambda",
            "group_ids": [Command.set([self.env.ref("base.group_user").id])],
        })
        invoice = self.out_invoice.with_user(employee)
        self.assertIn(invoice.dougs_state, ("none", "sent", "error"))
        expense = self.env["hr.expense"].sudo().create({
            "name": "Peage", "product_id": self.env["product.product"].sudo().create(
                {"name": "Frais", "can_be_expensed": True}).id,
            "employee_id": self.env["hr.employee"].sudo().create(
                {"name": "Employe Lambda", "user_id": employee.id}).id,
            "total_amount_currency": 12.0,
        })
        self.assertIn(expense.with_user(employee).dougs_state, ("none", "sent", "error"))

    def test_10_batch_name_cannot_escape_the_export_folder(self):
        """Regression: batch.name is writable over RPC, it must not drive a path traversal."""
        tmp = tempfile.mkdtemp()
        self.icp.set_param("dougs_bridge.folder_path", tmp)
        batch = self.env["dougs.export.batch"].create({"transport": "folder"})
        batch.sudo().write({"name": "../../escaped"})
        with self._patch_pdf():
            batch.action_send()
        self.assertFalse(os.path.exists(os.path.join(os.path.dirname(tmp), "escaped")))
        self.assertTrue(os.path.isdir(os.path.join(tmp, ".._.._escaped")))
