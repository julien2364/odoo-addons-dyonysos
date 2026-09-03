# -*- coding: utf-8 -*-
import json
import logging

from markupsafe import Markup

from odoo import Command, api, fields, models
from odoo.exceptions import UserError

from .ai_extract_service import AiExtractError, AiExtractService

_logger = logging.getLogger(__name__)


class HrExpense(models.Model):
    _inherit = "hr.expense"

    ai_extract_state = fields.Selection(
        [("none", "Not extracted"), ("done", "Extracted"), ("error", "Error")],
        string="AI Extraction", default="none", copy=False, readonly=True)
    ai_extract_confidence = fields.Float(string="AI Confidence", digits=(3, 2), copy=False, readonly=True)

    @api.model
    def create_expense_from_attachments(self, attachment_ids=None, view_type="list"):
        expense_ids = super().create_expense_from_attachments(attachment_ids=attachment_ids, view_type=view_type)
        icp = self.env["ir.config_parameter"].sudo()
        if icp.get_param("ai_document_extract.auto_expenses", "True") == "True":
            for expense in self.browse(expense_ids):
                try:
                    with self.env.cr.savepoint():
                        reason = expense._ai_extract_expense()
                        if reason:
                            expense.message_post(body=self.env._("AI digitization skipped: %s", reason))
                except Exception as e:  # noqa: BLE001 - never block the upload
                    _logger.exception("AI expense extraction failed")
                    expense.message_post(body=self.env._("AI digitization failed: %s", e))
        return expense_ids

    def action_ai_extract(self):
        for expense in self:
            if expense.state not in ("draft", "reported", "submitted"):
                raise UserError(self.env._("Only expenses not yet approved can be digitized."))
            reason = expense._ai_extract_expense()
            if reason:
                raise UserError(reason)
        return True

    def _ai_extract_expense(self):
        self.ensure_one()
        attachment = self.message_main_attachment_id or self.attachment_ids[:1]
        if not attachment:
            return self.env._("Attach a receipt (PDF or image) first.")
        service = AiExtractService(self.env)
        log_vals = {
            "res_model": self._name,
            "res_id": self.id,
            "attachment_id": attachment.id,
            "attachment_name": attachment.name,
            "doc_type": "expense",
            "provider": service.provider,
            "model": service.model,
        }
        try:
            result, meta = service.extract(attachment.raw, attachment.mimetype, attachment.name, "expense")
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
        self._ai_apply_expense_result(result)
        return None

    def _ai_apply_expense_result(self, result):
        self.ensure_one()
        vals = {}
        warnings = []
        supplier = result.get("supplier") or {}
        label = supplier.get("name") or (result.get("lines") or [{}])[0].get("description")
        if label:
            vals["name"] = label[:120]
        if result.get("invoice_date"):
            vals["date"] = result["invoice_date"]
        if result.get("currency"):
            currency = self.env["res.currency"].search([("name", "=", result["currency"]), ("active", "=", True)], limit=1)
            if currency:
                vals["currency_id"] = currency.id
        total = result.get("total_amount")
        if total is None and result.get("untaxed_amount") is not None:
            total = result["untaxed_amount"] + (result.get("tax_amount") or 0.0)
        if total is not None:
            vals["total_amount_currency"] = total
        rate = None
        rates = [l.get("tax_rate") for l in (result.get("lines") or []) if l.get("tax_rate") is not None]
        if rates:
            rate = max(set(rates), key=rates.count)
        elif result.get("tax_amount") and result.get("untaxed_amount"):
            rate = round(result["tax_amount"] / result["untaxed_amount"] * 100, 1)
        if rate is not None:
            taxes = self._ai_match_expense_tax(rate)
            if taxes:
                vals["tax_ids"] = [Command.set(taxes.ids)]
            else:
                warnings.append(self.env._("No purchase tax at %s%% found; tax left unchanged.", rate))
        if supplier.get("name"):
            partner = self.env["res.partner"]._retrieve_partner(
                name=supplier.get("name"), vat=supplier.get("vat"), email=supplier.get("email"), company=self.company_id)
            if partner:
                vals["vendor_id"] = partner.id
        if result.get("invoice_number"):
            vals["description"] = self.env._("Receipt/invoice no. %s", result["invoice_number"])

        self.write(vals)
        self.ai_extract_state = "done"
        self.ai_extract_confidence = result.get("confidence") or 0.0

        body = Markup("<b>%s</b>") % self.env._("AI digitization done")
        if result.get("confidence") is not None:
            body += Markup(" — %s") % self.env._("confidence %(conf)d%%", conf=round(result["confidence"] * 100))
        if warnings:
            body += Markup("<ul>%s</ul>") % Markup("").join(Markup("<li>%s</li>") % w for w in warnings)
        self.message_post(body=body)

    def _ai_match_expense_tax(self, rate):
        Tax = self.env["account.tax"]
        base_domain = [
            ("type_tax_use", "=", "purchase"),
            ("amount_type", "=", "percent"),
            ("company_id", "=", self.company_id.id),
        ]
        # Receipts are tax included: prefer a tax-included purchase tax when the company has one.
        candidates = Tax.search(base_domain + [("price_include_override", "=", "tax_included")]) or Tax.search(base_domain)
        matches = candidates.filtered(lambda t: abs(t.amount - float(rate)) < 0.051)
        return matches.sorted(lambda t: (len(t.name or ""), t.id))[:1]
