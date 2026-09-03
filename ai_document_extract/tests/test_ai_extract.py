# -*- coding: utf-8 -*-
import base64
import json
from unittest.mock import patch

from odoo.tests import TransactionCase, tagged

from odoo.addons.ai_document_extract.models.ai_extract_service import AiExtractError, AiExtractService

MINIMAL_PDF = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)

FAKE_RESULT = {
    "document_type": "invoice",
    "supplier": {"name": "Outlet PC SARL", "vat": "FR23334175221", "email": "compta@outletpc.example",
                 "phone": None, "iban": None, "street": "1 rue des Tests", "zip": "75001", "city": "Paris",
                 "country_code": "FR"},
    "invoice_number": "F-2026-0042",
    "invoice_date": "2026-08-28",
    "due_date": "2026-09-27",
    "currency": "EUR",
    "lines": [
        {"description": "Casque Nuk", "quantity": 2, "unit_price": 10.0, "tax_rate": 20, "total": 20.0},
        {"description": "Livre", "quantity": 1, "unit_price": 5.0, "tax_rate": 5.5, "total": 5.0},
    ],
    "untaxed_amount": 25.0,
    "tax_amount": 4.275,
    "total_amount": 29.28,
    "payment_reference": None,
    "notes": None,
    "confidence": 0.93,
}


def _fake_anthropic_response(payload):
    return {"content": [{"type": "text", "text": json.dumps(payload)}],
            "usage": {"input_tokens": 1200, "output_tokens": 300}}


@tagged("post_install", "-at_install")
class TestAiExtract(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        icp = cls.env["ir.config_parameter"].sudo()
        icp.set_param("ai_document_extract.provider", "anthropic")
        icp.set_param("ai_document_extract.api_key", "test-key")
        cls.company = cls.env.company
        Tax = cls.env["account.tax"]
        cls.tax20 = Tax.create({"name": "TVA 20% test", "amount": 20, "type_tax_use": "purchase", "company_id": cls.company.id})
        cls.tax55 = Tax.create({"name": "TVA 5.5% test", "amount": 5.5, "type_tax_use": "purchase", "company_id": cls.company.id})
        cls.purchase_journal = cls.env["account.journal"].search(
            [("type", "=", "purchase"), ("company_id", "=", cls.company.id)], limit=1)

    def _make_attachment(self, res_model, name="facture.pdf", raw=MINIMAL_PDF, mimetype="application/pdf"):
        return self.env["ir.attachment"].create({
            "name": name, "raw": raw, "mimetype": mimetype, "res_model": res_model, "res_id": 0,
        })

    def _purchase_env(self):
        return self.env["account.move"].with_context(
            default_move_type="in_invoice", default_journal_id=self.purchase_journal.id)

    def test_01_service_normalises_response(self):
        service = AiExtractService(self.env)
        with patch.object(AiExtractService, "_post", return_value=_fake_anthropic_response({
            **FAKE_RESULT, "invoice_date": "28/08/2026", "total_amount": "29,28 €",
        })):
            result, meta = service.extract(MINIMAL_PDF, "application/pdf", "f.pdf", "invoice")
        self.assertEqual(result["invoice_date"], "2026-08-28")
        self.assertAlmostEqual(result["total_amount"], 29.28)
        self.assertEqual(result["supplier"]["vat"], "FR23334175221")
        self.assertEqual(meta["input_tokens"], 1200)

    def test_02_vendor_bill_created_from_attachment(self):
        attachment = self._make_attachment("account.move")
        with patch.object(AiExtractService, "_post", return_value=_fake_anthropic_response(FAKE_RESULT)):
            moves = self._purchase_env()._create_records_from_attachments(attachment)
        self.assertEqual(len(moves), 1)
        move = moves[0]
        self.assertEqual(move.move_type, "in_invoice")
        self.assertEqual(move.ref, "F-2026-0042")
        self.assertEqual(str(move.invoice_date), "2026-08-28")
        self.assertEqual(move.partner_id.name, "Outlet PC SARL")
        self.assertEqual(move.partner_id.vat, "FR23334175221")
        self.assertEqual(len(move.invoice_line_ids), 2)
        self.assertEqual(move.invoice_line_ids[0].tax_ids, self.tax20)
        self.assertEqual(move.invoice_line_ids[1].tax_ids, self.tax55)
        self.assertAlmostEqual(move.amount_untaxed, 25.0)
        self.assertAlmostEqual(move.amount_total, 29.28, places=2)
        self.assertEqual(move.ai_extract_state, "done")
        log = self.env["ai.extract.log"].search([("res_model", "=", "account.move"), ("res_id", "=", move.id)])
        self.assertEqual(log.state, "done")
        self.assertEqual(log.input_tokens, 1200)

    def test_03_existing_partner_is_reused_by_vat(self):
        partner = self.env["res.partner"].create({"name": "Outlet PC (existing)", "vat": "FR23334175221", "is_company": True})
        attachment = self._make_attachment("account.move")
        with patch.object(AiExtractService, "_post", return_value=_fake_anthropic_response(FAKE_RESULT)):
            move = self._purchase_env()._create_records_from_attachments(attachment)[0]
        self.assertEqual(move.partner_id, partner)

    def test_04_credit_note_switches_move_type(self):
        attachment = self._make_attachment("account.move")
        with patch.object(AiExtractService, "_post", return_value=_fake_anthropic_response({**FAKE_RESULT, "document_type": "credit_note"})):
            move = self._purchase_env()._create_records_from_attachments(attachment)[0]
        self.assertEqual(move.move_type, "in_refund")

    def test_05_provider_error_is_logged_not_raised(self):
        attachment = self._make_attachment("account.move")
        with patch.object(AiExtractService, "_post", side_effect=AiExtractError("AI provider error 401: bad key")):
            move = self._purchase_env()._create_records_from_attachments(attachment)[0]
        self.assertEqual(move.ai_extract_state, "error")
        self.assertFalse(move.invoice_line_ids)
        log = self.env["ai.extract.log"].search([("res_model", "=", "account.move"), ("res_id", "=", move.id)])
        self.assertEqual(log.state, "error")
        self.assertIn("401", log.error)

    def test_06_sale_invoice_not_extracted(self):
        attachment = self._make_attachment("account.move")
        sale_journal = self.env["account.journal"].search([("type", "=", "sale"), ("company_id", "=", self.company.id)], limit=1)
        Move = self.env["account.move"].with_context(default_move_type="out_invoice", default_journal_id=sale_journal.id)
        with patch.object(AiExtractService, "_post", return_value=_fake_anthropic_response(FAKE_RESULT)) as post:
            move = Move._create_records_from_attachments(attachment)[0]
        post.assert_not_called()
        self.assertEqual(move.ai_extract_state, "none")

    def test_07_expense_from_receipt(self):
        self.env["product.product"].create({"name": "Frais divers", "can_be_expensed": True, "default_code": "EXP_GEN"})
        self.env["hr.employee"].create({"name": "Julien Test", "user_id": self.env.user.id})
        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")
        attachment = self._make_attachment("hr.expense", name="ticket.png", raw=png, mimetype="image/png")
        receipt = {**FAKE_RESULT, "document_type": "receipt", "lines": [
            {"description": "Carburant SP95", "quantity": 1, "unit_price": 50.0, "tax_rate": 20, "total": 50.0}],
            "untaxed_amount": 50.0, "tax_amount": 10.0, "total_amount": 60.0}
        with patch.object(AiExtractService, "_post", return_value=_fake_anthropic_response(receipt)):
            expense_ids = self.env["hr.expense"].create_expense_from_attachments(attachment.ids)
        expense = self.env["hr.expense"].browse(expense_ids)
        self.assertEqual(expense.name, "Outlet PC SARL")
        self.assertAlmostEqual(expense.total_amount_currency, 60.0)
        self.assertEqual(str(expense.date), "2026-08-28")
        self.assertEqual(expense.tax_ids, self.tax20)
        self.assertEqual(expense.ai_extract_state, "done")
