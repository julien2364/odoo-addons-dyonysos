# -*- coding: utf-8 -*-
import csv
import io
import logging
import zipfile
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError

from .dougs_transport import DougsTransport, DougsTransportError, safe_filename

_logger = logging.getLogger(__name__)

TRANSPORTS = [
    ("download", "Download ZIP (manual upload)"),
    ("email", "Email to the accountant"),
    ("folder", "Shared folder on the server (Drive/Nextcloud sync)"),
    ("sftp", "SFTP"),
    ("apifirst", "API First (Dougs) / REST API"),
]

DOC_TYPES = [
    ("out_invoice", "Customer Invoice"),
    ("out_refund", "Customer Credit Note"),
    ("in_invoice", "Vendor Bill"),
    ("in_refund", "Vendor Credit Note"),
    ("expense", "Expense"),
]


class DougsExportBatch(models.Model):
    _name = "dougs.export.batch"
    _description = "Accounting export batch (Dougs Bridge)"
    _inherit = ["mail.thread"]
    _order = "id desc"

    name = fields.Char(required=True, default="New", copy=False, readonly=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    date_from = fields.Date()
    date_to = fields.Date()
    transport = fields.Selection(
        TRANSPORTS, required=True,
        default=lambda self: self.env["ir.config_parameter"].sudo().get_param("dougs_bridge.transport", "download"))
    state = fields.Selection(
        [("draft", "Draft"), ("sent", "Sent"), ("partial", "Partially sent"), ("error", "Error")],
        default="draft", required=True, tracking=True, copy=False)
    line_ids = fields.One2many("dougs.export.line", "batch_id", string="Documents")
    line_count = fields.Integer(compute="_compute_counts")
    count_out = fields.Integer(compute="_compute_counts", string="Customer invoices")
    count_in = fields.Integer(compute="_compute_counts", string="Vendor bills")
    count_expense = fields.Integer(compute="_compute_counts", string="Expenses")
    count_error = fields.Integer(compute="_compute_counts", string="Errors")
    zip_attachment_id = fields.Many2one("ir.attachment", string="ZIP", readonly=True, copy=False)
    sent_date = fields.Datetime(readonly=True, copy=False)
    log = fields.Text(readonly=True, copy=False)
    report_email = fields.Char(
        default=lambda self: self.env["ir.config_parameter"].sudo().get_param("dougs_bridge.report_email", ""))

    @api.depends("line_ids.doc_type", "line_ids.state")
    def _compute_counts(self):
        for batch in self:
            lines = batch.line_ids
            batch.line_count = len(lines)
            batch.count_out = len(lines.filtered(lambda l: l.doc_type.startswith("out")))
            batch.count_in = len(lines.filtered(lambda l: l.doc_type.startswith("in")))
            batch.count_expense = len(lines.filtered(lambda l: l.doc_type == "expense"))
            batch.count_error = len(lines.filtered(lambda l: l.state == "error"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == "New":
                vals["name"] = fields.Datetime.now().strftime("DOUGS-%Y%m%d-%H%M%S")
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Selection of documents
    # ------------------------------------------------------------------
    def _icp(self, key, default=""):
        return self.env["ir.config_parameter"].sudo().get_param("dougs_bridge." + key, default) or default

    def _exported_ids(self, model):
        lines = self.env["dougs.export.line"].search([
            ("res_model", "=", model), ("state", "=", "sent"), ("company_id", "=", self.company_id.id)])
        return set(lines.mapped("res_id"))

    def _candidate_moves(self):
        types = []
        if self._icp("include_sales", "True") == "True":
            types += ["out_invoice", "out_refund"]
        if self._icp("include_purchases", "True") == "True":
            types += ["in_invoice", "in_refund"]
        if not types:
            return self.env["account.move"]
        domain = [("state", "=", "posted"), ("move_type", "in", types), ("company_id", "=", self.company_id.id)]
        if self.date_from:
            domain.append(("invoice_date", ">=", self.date_from))
        if self.date_to:
            domain.append(("invoice_date", "<=", self.date_to))
        moves = self.env["account.move"].search(domain, order="invoice_date, id")
        done = self._exported_ids("account.move")
        return moves.filtered(lambda m: m.id not in done)

    def _candidate_expenses(self):
        if self._icp("include_expenses", "True") != "True":
            return self.env["hr.expense"]
        domain = [("company_id", "=", self.company_id.id), ("state", "in", ("approved", "posted", "done", "paid"))]
        if self.date_from:
            domain.append(("date", ">=", self.date_from))
        if self.date_to:
            domain.append(("date", "<=", self.date_to))
        expenses = self.env["hr.expense"].search(domain, order="date, id")
        done = self._exported_ids("hr.expense")
        return expenses.filtered(lambda e: e.id not in done)

    def action_collect(self):
        """Fill the batch with every document not yet sent."""
        self.ensure_one()
        if self.state not in ("draft", "error"):
            raise UserError(self.env._("Only draft batches can be (re)filled."))
        self.line_ids.filtered(lambda l: l.state != "sent").unlink()
        vals = []
        Line = self.env["dougs.export.line"]
        for move in self._candidate_moves():
            vals.append(Line._vals_from_move(move, self))
        for expense in self._candidate_expenses():
            vals.append(Line._vals_from_expense(expense, self))
        Line.create(vals)
        return True

    # ------------------------------------------------------------------
    # Build & send
    # ------------------------------------------------------------------
    def _build_files(self):
        """Return list of (filename, bytes, line) plus journal.csv."""
        self.ensure_one()
        files = []
        rows = []
        for line in self.line_ids.filtered(lambda l: l.state != "sent"):
            try:
                for fname, content in line._get_documents():
                    files.append((fname, content, line))
                rows.append(line._journal_row())
                line.state = "ready"
            except Exception as e:  # noqa: BLE001
                _logger.exception("Dougs Bridge: cannot build %s", line.display_name)
                line._mark_error(str(e))
        buf = io.StringIO()
        writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
        writer.writerow(["type", "date", "numero", "reference", "partenaire", "tva_intracom", "montant_ht",
                         "montant_tva", "montant_ttc", "devise", "echeance", "fichier", "odoo_model", "odoo_id"])
        writer.writerows(rows)
        files.append(("journal.csv", ("﻿" + buf.getvalue()).encode("utf-8"), None))
        return files

    @staticmethod
    def _zip(files):
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            for fname, content, _line in files:
                zf.writestr(safe_filename(fname), content)
        return out.getvalue()

    def _store_zip(self, zip_bytes):
        self.ensure_one()
        if self.zip_attachment_id:
            self.zip_attachment_id.unlink()
        self.zip_attachment_id = self.env["ir.attachment"].create({
            "name": "%s.zip" % self.name, "raw": zip_bytes, "mimetype": "application/zip",
            "res_model": self._name, "res_id": self.id,
        })

    def action_send(self):
        for batch in self:
            if not batch.line_ids:
                batch.action_collect()
            if not batch.line_ids:
                batch.write({"state": "sent", "log": self.env._("Nothing to send."), "sent_date": fields.Datetime.now()})
                continue
            files = batch._build_files()
            zip_bytes = batch._zip(files)
            batch._store_zip(zip_bytes)
            try:
                log = DougsTransport(self.env).send(batch, zip_bytes, files)
            except DougsTransportError as e:
                batch.line_ids.filtered(lambda l: l.state == "ready").write({"state": "error", "error": str(e)})
                batch.write({"state": "error", "log": str(e)})
                batch._send_report()
                continue
            batch.line_ids.filtered(lambda l: l.state == "ready").write(
                {"state": "sent", "sent_date": fields.Datetime.now(), "error": False})
            if not batch.count_error:
                state = "sent"
            elif batch.line_ids.filtered(lambda l: l.state == "sent"):
                state = "partial"
            else:
                state = "error"
            batch.write({"state": state, "log": log, "sent_date": fields.Datetime.now()})
            batch._send_report()
        return True

    def action_retry_errors(self):
        for batch in self:
            batch.line_ids.filtered(lambda l: l.state == "error").write({"state": "draft", "error": False})
            batch.state = "draft"
            batch.action_send()
        return True

    def action_download_zip(self):
        self.ensure_one()
        if not self.zip_attachment_id:
            self._store_zip(self._zip(self._build_files()))
        return {"type": "ir.actions.act_url", "url": "/web/content/%d?download=1" % self.zip_attachment_id.id, "target": "self"}

    def _send_report(self):
        self.ensure_one()
        if not self.report_email:
            return
        try:
            self.env.ref("dougs_bridge.mail_template_dougs_batch").send_mail(self.id, force_send=False)
        except Exception:  # noqa: BLE001
            _logger.exception("Dougs Bridge: report email failed")

    # ------------------------------------------------------------------
    # Cron
    # ------------------------------------------------------------------
    @api.model
    def _cron_run(self):
        for company in self.env["res.company"].search([]):
            delay = int(self._icp("cron_delay_days", "0") or 0)
            batch = self.with_company(company).create({
                "company_id": company.id,
                "date_to": fields.Date.context_today(self) - timedelta(days=delay),
            })
            batch.action_collect()
            if batch.line_ids:
                batch.action_send()
            else:
                batch.unlink()


class DougsExportLine(models.Model):
    _name = "dougs.export.line"
    _description = "Accounting export line (Dougs Bridge)"
    _order = "date, id"

    batch_id = fields.Many2one("dougs.export.batch", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="batch_id.company_id", store=True, index=True)
    res_model = fields.Char(required=True, index=True)
    res_id = fields.Integer(required=True, index=True)
    doc_type = fields.Selection(DOC_TYPES, required=True)
    name = fields.Char(string="Number")
    reference = fields.Char()
    date = fields.Date()
    date_due = fields.Date()
    partner_id = fields.Many2one("res.partner")
    partner_vat = fields.Char()
    amount_untaxed = fields.Float(digits="Account")
    amount_tax = fields.Float(digits="Account")
    amount_total = fields.Float(digits="Account")
    currency_id = fields.Many2one("res.currency")
    filename = fields.Char()
    state = fields.Selection(
        [("draft", "To send"), ("ready", "Ready"), ("sent", "Sent"), ("error", "Error")],
        default="draft", required=True, index=True)
    sent_date = fields.Datetime()
    remote_id = fields.Char(string="Remote ID")
    error = fields.Text()

    # ------------------------------------------------------------------
    @api.model
    def _vals_from_move(self, move, batch):
        date = move.invoice_date or move.date
        return {
            "batch_id": batch.id,
            "res_model": "account.move",
            "res_id": move.id,
            "doc_type": move.move_type,
            "name": move.name,
            "reference": move.ref or move.payment_reference,
            "date": date,
            "date_due": move.invoice_date_due,
            "partner_id": move.commercial_partner_id.id,
            "partner_vat": move.commercial_partner_id.vat,
            "amount_untaxed": move.amount_untaxed,
            "amount_tax": move.amount_tax,
            "amount_total": move.amount_total,
            "currency_id": move.currency_id.id,
            "filename": safe_filename("%s_%s_%s.pdf" % (move.move_type, date.isoformat() if date else "", move.name)),
        }

    @api.model
    def _vals_from_expense(self, expense, batch):
        return {
            "batch_id": batch.id,
            "res_model": "hr.expense",
            "res_id": expense.id,
            "doc_type": "expense",
            "name": expense.name,
            "reference": expense.description,
            "date": expense.date,
            "partner_id": expense.vendor_id.id,
            "partner_vat": expense.vendor_id.vat,
            "amount_untaxed": expense.untaxed_amount_currency,
            "amount_tax": expense.tax_amount_currency,
            "amount_total": expense.total_amount_currency,
            "currency_id": expense.currency_id.id,
            "filename": safe_filename("expense_%s_%s_%s.pdf" % (
                expense.date.isoformat() if expense.date else "", expense.id, expense.name)),
        }

    def _record(self):
        self.ensure_one()
        return self.env[self.res_model].browse(self.res_id).exists()

    def _mark_error(self, message):
        self.write({"state": "error", "error": message})

    def _journal_row(self):
        self.ensure_one()
        return [
            self.doc_type, self.date.isoformat() if self.date else "", self.name or "", self.reference or "",
            self.partner_id.name or "", self.partner_vat or "",
            "%.2f" % self.amount_untaxed, "%.2f" % self.amount_tax, "%.2f" % self.amount_total,
            self.currency_id.name or "", self.date_due.isoformat() if self.date_due else "",
            self.filename or "", self.res_model, self.res_id,
        ]

    def _apifirst_metadata(self):
        self.ensure_one()
        return {
            "type": self.doc_type,
            "number": self.name,
            "reference": self.reference,
            "date": self.date.isoformat() if self.date else None,
            "due_date": self.date_due.isoformat() if self.date_due else None,
            "partner": {"name": self.partner_id.name, "vat": self.partner_vat},
            "amount_untaxed": self.amount_untaxed,
            "amount_tax": self.amount_tax,
            "amount_total": self.amount_total,
            "currency": self.currency_id.name,
            "source": {"model": self.res_model, "id": self.res_id},
        }

    # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------
    def _get_documents(self):
        """Return [(filename, bytes)] for this line: the PDF, plus Factur-X XML for sales."""
        self.ensure_one()
        record = self._record()
        if not record:
            raise UserError(self.env._("Source document no longer exists."))
        if self.res_model == "account.move":
            return self._documents_for_move(record)
        return self._documents_for_expense(record)

    @staticmethod
    def _ext(attachment):
        if "pdf" in (attachment.mimetype or ""):
            return "pdf"
        return attachment.name.rsplit(".", 1)[-1].lower() if "." in (attachment.name or "") else "bin"

    def _documents_for_move(self, move):
        docs = []
        if move.is_sale_document():
            pdf = move.invoice_pdf_report_id.raw if move.invoice_pdf_report_id else None
            if not pdf:
                pdf, _type = self.env["ir.actions.report"]._render_qweb_pdf("account.account_invoices", res_ids=[move.id])
            docs.append((self.filename, pdf))
            if self.env["ir.config_parameter"].sudo().get_param("dougs_bridge.facturx", "True") == "True":
                try:
                    xml, _errors = self.env["account.edi.xml.cii"]._export_invoice(move)
                    if xml:
                        docs.append((self.filename[:-4] + "_facturx.xml", xml))
                except Exception as e:  # noqa: BLE001 - Factur-X is a bonus, never block the PDF
                    _logger.info("Dougs Bridge: Factur-X export failed for %s: %s", move.name, e)
        else:
            attachment = move.message_main_attachment_id
            if not attachment:
                attachment = self.env["ir.attachment"].search(
                    [("res_model", "=", "account.move"), ("res_id", "=", move.id), ("res_field", "=", False),
                     ("mimetype", "in", ("application/pdf", "image/png", "image/jpeg"))], order="id", limit=1)
            if attachment:
                self.filename = self.filename[:-4] + "." + self._ext(attachment)
                docs.append((self.filename, attachment.raw))
            else:
                # No supplier document attached: export the Odoo rendering so the accountant still gets a proof.
                pdf, _type = self.env["ir.actions.report"]._render_qweb_pdf("account.account_invoices", res_ids=[move.id])
                docs.append((self.filename, pdf))
        return docs

    def _documents_for_expense(self, expense):
        attachments = expense.attachment_ids or expense.message_main_attachment_id
        if not attachments:
            raise UserError(self.env._("Expense %s has no receipt attached.", expense.name))
        docs = []
        base = self.filename[:-4]
        for idx, attachment in enumerate(attachments):
            suffix = "" if idx == 0 else "_%d" % (idx + 1)
            fname = base + suffix + "." + self._ext(attachment)
            if idx == 0:
                self.filename = fname
            docs.append((fname, attachment.raw))
        return docs

    def action_open_record(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "res_model": self.res_model, "res_id": self.res_id, "view_mode": "form"}
