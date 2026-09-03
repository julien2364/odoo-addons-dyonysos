# -*- coding: utf-8 -*-
"""Community fix: the stock Factur-X (CII) exporter reads ``deferred_start_date`` /
``deferred_end_date`` on invoice lines, fields that only exist with Enterprise's
deferred-entries feature. Without this override the export crashes on Community."""
from odoo import models


class AccountEdiXmlCII(models.AbstractModel):
    _inherit = "account.edi.xml.cii"

    def _cii_get_billing_specified_period_node(self, vals):
        invoice = vals["invoice"]
        Line = self.env["account.move.line"]
        if "deferred_start_date" in Line._fields and "deferred_end_date" in Line._fields:
            return super()._cii_get_billing_specified_period_node(vals)
        start_date = invoice.invoice_date or None
        end_date = invoice.invoice_date_due or None
        return {
            "ram:StartDateTime": self._cii_get_date_time_string_node(vals, start_date) if start_date else None,
            "ram:EndDateTime": self._cii_get_date_time_string_node(vals, end_date) if end_date else None,
        }
