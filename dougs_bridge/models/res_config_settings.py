# -*- coding: utf-8 -*-
from odoo import fields, models
from .dougs_export import TRANSPORTS


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    dougs_transport = fields.Selection(TRANSPORTS, string="Transport", default="download", config_parameter="dougs_bridge.transport")
    dougs_email_to = fields.Char(string="Accountant email", config_parameter="dougs_bridge.email_to",
                                 help="Collection address given by your accountant (Dougs or other).")
    dougs_report_email = fields.Char(string="Report email", config_parameter="dougs_bridge.report_email",
                                     help="Receives a summary after each batch (e.g. your own address).")
    dougs_folder_path = fields.Char(string="Export folder", config_parameter="dougs_bridge.folder_path",
                                    help="Directory on the Odoo server, e.g. a synced Drive/Nextcloud folder.")
    dougs_sftp_host = fields.Char(string="SFTP host", config_parameter="dougs_bridge.sftp_host")
    dougs_sftp_port = fields.Char(string="SFTP port", config_parameter="dougs_bridge.sftp_port", default="22")
    dougs_sftp_user = fields.Char(string="SFTP user", config_parameter="dougs_bridge.sftp_user")
    dougs_sftp_password = fields.Char(string="SFTP password", config_parameter="dougs_bridge.sftp_password")
    dougs_sftp_path = fields.Char(string="SFTP path", config_parameter="dougs_bridge.sftp_path", default="/")
    dougs_apifirst_base_url = fields.Char(string="API base URL", config_parameter="dougs_bridge.apifirst_base_url")
    dougs_apifirst_api_key = fields.Char(string="API key", config_parameter="dougs_bridge.apifirst_api_key")
    dougs_apifirst_path_sale = fields.Char(string="Path: customer invoices", config_parameter="dougs_bridge.apifirst_path_sale", default="/v1/invoices/outgoing")
    dougs_apifirst_path_purchase = fields.Char(string="Path: vendor bills", config_parameter="dougs_bridge.apifirst_path_purchase", default="/v1/invoices/incoming")
    dougs_apifirst_path_expense = fields.Char(string="Path: receipts", config_parameter="dougs_bridge.apifirst_path_expense", default="/v1/receipts")
    dougs_apifirst_file_field = fields.Char(string="File field name", config_parameter="dougs_bridge.apifirst_file_field", default="file")
    dougs_include_sales = fields.Boolean(string="Customer invoices & credit notes", default=True, config_parameter="dougs_bridge.include_sales")
    dougs_include_purchases = fields.Boolean(string="Vendor bills & credit notes", default=True, config_parameter="dougs_bridge.include_purchases")
    dougs_include_expenses = fields.Boolean(string="Approved expenses", default=True, config_parameter="dougs_bridge.include_expenses")
    dougs_facturx = fields.Boolean(string="Add Factur-X XML for customer invoices", default=True, config_parameter="dougs_bridge.facturx")
    dougs_cron_delay_days = fields.Char(string="Days before a document is exported", default="0", config_parameter="dougs_bridge.cron_delay_days",
                                        help="Grace period so that a just-posted invoice can still be corrected before it leaves Odoo.")
