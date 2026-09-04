# -*- coding: utf-8 -*-
import json
import logging

from markupsafe import Markup

from odoo import Command, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare

from .ai_extract_service import IMAGE_MIMETYPES, AiExtractError, AiExtractService

_logger = logging.getLogger(__name__)

AI_DECODER_PRIORITY = 5  # below UBL/CII structured XML (20), above "no decoder" (0)


class AccountMove(models.Model):
    _inherit = "account.move"

    ai_extract_state = fields.Selection(
        [("none", "Not extracted"), ("done", "Extracted"), ("error", "Error")],
        string="AI Extraction", default="none", copy=False, readonly=True)
    ai_extract_confidence = fields.Float(string="AI Confidence", digits=(3, 2), copy=False, readonly=True)

    # ------------------------------------------------------------------
    # Import framework hooks
    # ------------------------------------------------------------------
    @api.model
    def _get_import_file_type(self, file_data):
        res = super()._get_import_file_type(file_data)
        if res:
            return res
        if (file_data.get("mimetype") or "").lower() in IMAGE_MIMETYPES:
            return "image"
        return res

    def _get_edi_decoder(self, file_data, new=False):
        res = super()._get_edi_decoder(file_data, new=new)
        if res:
            return res
        if file_data.get("import_file_type") in ("pdf", "image") and self._ai_extract_enabled():
            return {"priority": AI_DECODER_PRIORITY, "decoder": self._ai_decode_invoice}
        return res

    def _ai_extract_enabled(self):
        icp = self.env["ir.config_parameter"].sudo()
        if icp.get_param("ai_document_extract.auto_invoices", "True") != "True":
            return False
        # Only purchase documents are extracted automatically; a sale invoice is what *we* issue.
        move_type = self.move_type or self.env.context.get("default_move_type") or ""
        return move_type in ("in_invoice", "in_refund", "in_receipt") or not move_type

    # ------------------------------------------------------------------
    # Decoder
    # ------------------------------------------------------------------
    def _ai_decode_invoice(self, invoice, file_data, new=False):
        """Decoder signature required by account.document.import.mixin.
        Returns None on success, or a string explaining why nothing was imported."""
        if invoice.state != "draft":
            return self.env._("the document is not in draft state.")
        if invoice.invoice_line_ids and not new:
            return self.env._("the bill already has lines; use the 'AI Extract' button to overwrite them.")
        return invoice._ai_run_extraction(file_data)

    def _ai_run_extraction(self, file_data, overwrite=False):
        self.ensure_one()
        service = AiExtractService(self.env)
        attachment = file_data.get("attachment")
        log_vals = {
            "res_model": self._name,
            "res_id": self.id,
            "attachment_id": attachment.id if attachment else False,
            "attachment_name": file_data.get("name"),
            "doc_type": "invoice",
            "provider": service.provider,
            "model": service.model,
        }
        try:
            result, meta = service.extract(file_data["raw"], file_data.get("mimetype"), file_data.get("name"), "invoice")
        except AiExtractError as e:
            self.env["ai.extract.log"].sudo().create({**log_vals, "state": "error", "error": str(e)})
            self.ai_extract_state = "error"
            return str(e)

        log_vals.update({
            "state": "done",
            "duration": meta["duration"],
            "input_tokens": meta["input_tokens"],
            "output_tokens": meta["output_tokens"],
            "confidence": result.get("confidence") or 0.0,
            "result_json": json.dumps(result, ensure_ascii=False, indent=1),
        })
        self.env["ai.extract.log"].sudo().create(log_vals)
        self._ai_apply_result(result, overwrite=overwrite)
        return None

    # ------------------------------------------------------------------
    # Apply extracted data
    # ------------------------------------------------------------------
    def _ai_apply_result(self, result, overwrite=False):
        self.ensure_one()
        warnings = []
        with self._get_edi_creation() as move:
            if result.get("document_type") == "credit_note" and move.move_type == "in_invoice":
                move.move_type = "in_refund"

            partner, partner_note = move._ai_find_or_create_partner(result.get("supplier") or {})
            if partner:
                move.partner_id = partner
            if partner_note:
                warnings.append(partner_note)

            if result.get("invoice_number"):
                move.ref = result["invoice_number"]
            if result.get("payment_reference"):
                move.payment_reference = result["payment_reference"]
            if result.get("invoice_date"):
                move.invoice_date = result["invoice_date"]
            if result.get("due_date"):
                move.invoice_date_due = result["due_date"]
            if result.get("currency"):
                currency = self.env["res.currency"].with_context(active_test=False).search(
                    [("name", "=", result["currency"])], limit=1)
                if currency and currency.active:
                    move.currency_id = currency
                elif currency:
                    warnings.append(self.env._("Currency %s is not active in this database.", currency.name))

            if overwrite and move.invoice_line_ids:
                move.invoice_line_ids = [Command.clear()]
            commands = []
            for line in result.get("lines") or []:
                taxes = move._ai_match_tax(line.get("tax_rate"))
                commands.append(Command.create({
                    "name": line["description"],
                    "quantity": line["quantity"],
                    "price_unit": line["unit_price"],
                    "tax_ids": [Command.set(taxes.ids)],
                }))
            if not commands and result.get("untaxed_amount") is not None:
                rate = None
                if result.get("tax_amount") and result["untaxed_amount"]:
                    rate = round(result["tax_amount"] / result["untaxed_amount"] * 100, 1)
                taxes = move._ai_match_tax(rate)
                commands.append(Command.create({
                    "name": self.env._("Invoice %s", result.get("invoice_number") or ""),
                    "quantity": 1.0,
                    "price_unit": result["untaxed_amount"],
                    "tax_ids": [Command.set(taxes.ids)],
                }))
            if commands:
                move.invoice_line_ids = commands

        expected_total = result.get("total_amount")
        if expected_total is not None:
            rounding = self.currency_id.rounding or 0.01
            if float_compare(self.amount_total, expected_total, precision_rounding=rounding) != 0:
                warnings.append(self.env._(
                    "Computed total %(computed).2f differs from the document total %(expected).2f: "
                    "please check taxes and lines.",
                    computed=self.amount_total, expected=expected_total,
                ))

        self.ai_extract_state = "done"
        self.ai_extract_confidence = result.get("confidence") or 0.0

        body = Markup("<b>%s</b>") % self.env._("AI digitization done")
        if result.get("confidence") is not None:
            body += Markup(" — %s") % self.env._("confidence %(conf)d%%", conf=round(result["confidence"] * 100))
        if warnings:
            body += Markup("<ul>%s</ul>") % Markup("").join(Markup("<li>%s</li>") % w for w in warnings)
        self.message_post(body=body)

    # ------------------------------------------------------------------
    # Matching helpers
    # ------------------------------------------------------------------
    def _ai_find_or_create_partner(self, supplier):
        """Return (partner, warning_message)."""
        Partner = self.env["res.partner"]
        name = supplier.get("name")
        vat = supplier.get("vat")
        email = supplier.get("email")
        if not (name or vat or email):
            return Partner, self.env._("No supplier identified on the document.")

        partner = Partner._retrieve_partner(name=name, vat=vat, email=email, company=self.company_id)
        if partner:
            return partner, None

        icp = self.env["ir.config_parameter"].sudo()
        if icp.get_param("ai_document_extract.create_partner", "True") != "True" or not name:
            return Partner, self.env._("Supplier '%s' not found; please select it manually.", name or vat or email)

        country = self.env["res.country"]
        if supplier.get("country_code"):
            country = country.search([("code", "=", supplier["country_code"].upper()[:2])], limit=1)
        vals = {
            "name": name,
            "is_company": True,
            "supplier_rank": 1,
            "email": email,
            "phone": supplier.get("phone"),
            "street": supplier.get("street"),
            "zip": supplier.get("zip"),
            "city": supplier.get("city"),
            "country_id": country.id if country else False,
        }
        if vat:
            vals["vat"] = vat
        try:
            with self.env.cr.savepoint():
                partner = Partner.create(vals)
        except Exception as e:  # noqa: BLE001 - e.g. VAT validation error
            _logger.info("AI extract: partner creation failed (%s), retrying without VAT", e)
            vals.pop("vat", None)
            partner = Partner.create(vals)
            if vat:
                partner.message_post(body=self.env._("VAT read on the invoice (not validated): %s", vat))
        # Deliberately NOT creating a res.partner.bank here: a bank account read from an
        # incoming document is the classic invoice-fraud vector. The IBAN is reported in the
        # chatter so a human decides whether to record it.
        note = self.env._("Supplier '%s' was created from the document.", name)
        if supplier.get("iban"):
            note += " " + self.env._(
                "An IBAN was read on the document (%s): check it against a trusted source before "
                "recording it as a bank account.", supplier["iban"])
        return partner, note

    def _ai_match_tax(self, rate):
        """Find the purchase tax of the company matching a percentage."""
        Tax = self.env["account.tax"]
        if rate is None:
            return Tax
        candidates = Tax.search([
            ("type_tax_use", "=", "purchase"),
            ("amount_type", "=", "percent"),
            ("company_id", "=", self.company_id.id),
        ])
        matches = candidates.filtered(lambda t: abs(t.amount - float(rate)) < 0.051)
        if not matches:
            return Tax
        default = self.company_id.account_purchase_tax_id
        if default and default in matches:
            return default
        return matches.sorted(lambda t: (len(t.name or ""), t.id))[:1]

    # ------------------------------------------------------------------
    # Manual action
    # ------------------------------------------------------------------
    def action_ai_extract(self):
        """Button: (re)run the AI extraction on the main attachment, overwriting lines."""
        for move in self:
            if move.state != "draft":
                raise UserError(self.env._("Only draft bills can be digitized."))
            attachment = move.message_main_attachment_id
            if not attachment:
                attachment = self.env["ir.attachment"].search(
                    [("res_model", "=", "account.move"), ("res_id", "=", move.id), ("res_field", "=", False)],
                    order="id desc", limit=1)
            if not attachment:
                raise UserError(self.env._("Attach a PDF or an image first."))
            file_data = move._to_files_data(attachment)[0]
            reason = move._ai_run_extraction(file_data, overwrite=True)
            if reason:
                raise UserError(reason)
        return True
