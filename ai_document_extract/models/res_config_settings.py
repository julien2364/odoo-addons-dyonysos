# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ai_extract_provider = fields.Selection(
        [("anthropic", "Anthropic (Claude) — reads PDF natively"),
         ("openai", "OpenAI-compatible API (OpenAI, xAI Grok, Mistral, Ollama…)")],
        string="AI Provider", default="anthropic",
        config_parameter="ai_document_extract.provider")
    ai_extract_api_key = fields.Char(string="AI API Key", config_parameter="ai_document_extract.api_key")
    ai_extract_model = fields.Char(
        string="AI Model", config_parameter="ai_document_extract.model",
        help="Leave empty to use the provider default (claude-sonnet-4-5 / gpt-4.1-mini).")
    ai_extract_base_url = fields.Char(
        string="API Base URL", config_parameter="ai_document_extract.base_url",
        help="Leave empty for the provider default. For xAI Grok: https://api.x.ai/v1 ; "
             "for Mistral: https://api.mistral.ai/v1 ; for a local Ollama: http://localhost:11434/v1")
    ai_extract_auto_invoices = fields.Boolean(
        string="Digitize vendor bills automatically", default=True,
        config_parameter="ai_document_extract.auto_invoices",
        help="Run the AI on every PDF/image received on a purchase journal (mail alias, upload, drag & drop).")
    ai_extract_auto_expenses = fields.Boolean(
        string="Digitize expense receipts automatically", default=True,
        config_parameter="ai_document_extract.auto_expenses")
    ai_extract_create_partner = fields.Boolean(
        string="Create unknown suppliers", default=True,
        config_parameter="ai_document_extract.create_partner")
