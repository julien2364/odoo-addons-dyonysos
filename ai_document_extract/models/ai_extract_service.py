# -*- coding: utf-8 -*-
"""Provider-agnostic document extraction service.

One public entry point: ``AiExtractService(env).extract(raw, mimetype, filename, doc_type)``
returns ``(result_dict, meta_dict)`` (see ``EMPTY_RESULT``) or raises ``AiExtractError``.

Providers
---------
* ``anthropic``  – Anthropic Messages API. PDF sent natively (document block), images as image block.
* ``openai``     – any OpenAI-compatible chat completions endpoint (OpenAI, xAI Grok, Mistral, Ollama…).
                   Images are sent as ``image_url``; PDFs are reduced to their text layer (pypdf), so
                   scanned PDFs work best with Anthropic.
"""
import base64
import io
import json
import logging
import re
import time

from odoo.tools import float_round

_logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover
    PdfReader = None


class AiExtractError(Exception):
    pass


EMPTY_RESULT = {
    "document_type": None,          # "invoice" | "credit_note" | "receipt" | "other"
    "supplier": {"name": None, "vat": None, "email": None, "phone": None, "iban": None,
                 "street": None, "zip": None, "city": None, "country_code": None},
    "invoice_number": None,
    "invoice_date": None,           # YYYY-MM-DD
    "due_date": None,               # YYYY-MM-DD
    "currency": None,               # ISO 4217
    "lines": [],                    # [{description, quantity, unit_price, tax_rate, total}]
    "untaxed_amount": None,
    "tax_amount": None,
    "total_amount": None,
    "payment_reference": None,
    "notes": None,
    "confidence": None,             # 0..1
}

SYSTEM_PROMPT = (
    "You are an accounting data-entry assistant. You read a supplier invoice, credit note or "
    "expense receipt and return ONLY a JSON object, no prose, no markdown fences. "
    "Dates must be ISO 8601 (YYYY-MM-DD). Amounts are numbers with a dot decimal separator, "
    "never strings. tax_rate is a percentage number (e.g. 20, 5.5, 0). If the document has no "
    "detailed lines, return a single line with the untaxed total. Use null when a value is absent. "
    "Never invent a VAT number: copy it exactly as printed or return null."
)

USER_PROMPT_TEMPLATE = (
    "Extract the data of this {doc_kind} into this exact JSON structure:\n"
    "{schema}\n"
    "Rules: 'supplier' is the company that issued the document (the seller), not the buyer "
    "({buyer_name}). 'document_type' is one of invoice, credit_note, receipt, other. "
    "For a credit note, amounts are positive. 'confidence' is your overall confidence between 0 and 1."
)

IMAGE_MIMETYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"}


class AiExtractService:
    def __init__(self, env):
        self.env = env
        icp = env["ir.config_parameter"].sudo()
        self.provider = icp.get_param("ai_document_extract.provider", "anthropic")
        self.api_key = icp.get_param("ai_document_extract.api_key", "")
        self.model = icp.get_param("ai_document_extract.model", "") or self.default_model(self.provider)
        self.base_url = icp.get_param("ai_document_extract.base_url", "") or self.default_base_url(self.provider)
        self.timeout = int(icp.get_param("ai_document_extract.timeout", "90") or 90)
        self.max_tokens = 4096

    # ------------------------------------------------------------------
    # Defaults
    # ------------------------------------------------------------------
    @staticmethod
    def default_model(provider):
        return {
            "anthropic": "claude-sonnet-4-5",
            "openai": "gpt-4.1-mini",
        }.get(provider, "")

    @staticmethod
    def default_base_url(provider):
        return {
            "anthropic": "https://api.anthropic.com",
            "openai": "https://api.openai.com/v1",
        }.get(provider, "")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def extract(self, raw, mimetype, filename, doc_type="invoice"):
        """Return (result_dict, meta_dict). Raises AiExtractError."""
        if requests is None:
            raise AiExtractError("The Python package 'requests' is required.")
        if not self.api_key:
            raise AiExtractError("No AI API key configured (Settings > Accounting > AI Digitization).")
        if not raw:
            raise AiExtractError("Empty attachment.")

        mimetype = (mimetype or "").lower()
        is_pdf = "pdf" in mimetype or (filename or "").lower().endswith(".pdf")
        is_image = mimetype in IMAGE_MIMETYPES
        if not (is_pdf or is_image):
            raise AiExtractError("Unsupported file type %s (PDF or image expected)." % mimetype)

        doc_kind = "expense receipt" if doc_type == "expense" else "supplier invoice"
        prompt = USER_PROMPT_TEMPLATE.format(
            doc_kind=doc_kind,
            schema=json.dumps(EMPTY_RESULT, indent=1),
            buyer_name=self.env.company.name,
        )

        started = time.time()
        if self.provider == "anthropic":
            text, usage = self._call_anthropic(raw, mimetype, is_pdf, prompt)
        elif self.provider == "openai":
            text, usage = self._call_openai(raw, mimetype, is_pdf, prompt)
        else:
            raise AiExtractError("Unknown AI provider %r." % self.provider)
        duration = time.time() - started

        result = self._normalise(self._parse_json(text))
        meta = {
            "provider": self.provider,
            "model": self.model,
            "duration": duration,
            "input_tokens": usage.get("input_tokens", 0) or 0,
            "output_tokens": usage.get("output_tokens", 0) or 0,
            "raw_response": text,
        }
        return result, meta

    # ------------------------------------------------------------------
    # Providers
    # ------------------------------------------------------------------
    def _call_anthropic(self, raw, mimetype, is_pdf, prompt):
        b64 = base64.b64encode(raw).decode()
        if is_pdf:
            block = {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": b64}}
        else:
            block = {"type": "image", "source": {"type": "base64", "media_type": mimetype, "data": b64}}
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": [block, {"type": "text", "text": prompt}]}],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        data = self._post(self.base_url.rstrip("/") + "/v1/messages", headers, payload)
        text = "".join(part.get("text", "") for part in data.get("content", []) if part.get("type") == "text")
        return text, data.get("usage", {}) or {}

    def _call_openai(self, raw, mimetype, is_pdf, prompt):
        content = [{"type": "text", "text": prompt}]
        if is_pdf:
            text_layer = self._pdf_text(raw)
            if not text_layer.strip():
                raise AiExtractError(
                    "This PDF has no text layer (scan). Use the Anthropic provider, which reads PDFs natively, "
                    "or upload an image of the document.")
            content.append({"type": "text", "text": "Document text:\n" + text_layer[:60000]})
        else:
            b64 = base64.b64encode(raw).decode()
            content.append({"type": "image_url", "image_url": {"url": "data:%s;base64,%s" % (mimetype, b64)}})
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
        }
        headers = {"Authorization": "Bearer " + self.api_key, "content-type": "application/json"}
        data = self._post(self.base_url.rstrip("/") + "/chat/completions", headers, payload)
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise AiExtractError("Unexpected response from the AI provider.")
        usage = data.get("usage", {}) or {}
        return text, {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
        }

    def _post(self, url, headers, payload):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        except requests.RequestException as e:
            raise AiExtractError("AI provider unreachable: %s" % e)
        if resp.status_code >= 400:
            raise AiExtractError("AI provider error %s: %s" % (resp.status_code, resp.text[:500]))
        try:
            return resp.json()
        except ValueError:
            raise AiExtractError("AI provider returned a non-JSON response.")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _pdf_text(raw):
        if PdfReader is None:
            return ""
        try:
            reader = PdfReader(io.BytesIO(raw))
            return "\n".join((page.extract_text() or "") for page in reader.pages[:20])
        except Exception as e:  # noqa: BLE001
            _logger.info("pypdf could not read the PDF: %s", e)
            return ""

    @staticmethod
    def _parse_json(text):
        text = (text or "").strip()
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.S)
        try:
            return json.loads(text)
        except ValueError:
            match = re.search(r"\{.*\}", text, flags=re.S)
            if match:
                try:
                    return json.loads(match.group(0))
                except ValueError:
                    pass
        raise AiExtractError("The AI response could not be parsed as JSON.")

    @staticmethod
    def _num(value):
        if value in (None, "", False):
            return None
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        s = str(value).strip().replace(" ", "").replace(" ", "").replace("\xa0", "")
        s = re.sub(r"[^\d,.\-]", "", s)
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
        elif "," in s:
            s = s.replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return None

    @staticmethod
    def _date(value):
        if not value:
            return None
        s = str(value).strip()
        if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
            return s
        m = re.match(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$", s)
        if m:
            d, mo, y = m.groups()
            return "%s-%02d-%02d" % (y, int(mo), int(d))
        return None

    def _normalise(self, data):
        if not isinstance(data, dict):
            raise AiExtractError("The AI response is not a JSON object.")
        result = json.loads(json.dumps(EMPTY_RESULT))
        result["document_type"] = data.get("document_type") or None
        supplier = data.get("supplier") or {}
        if isinstance(supplier, str):
            supplier = {"name": supplier}
        for key in result["supplier"]:
            val = supplier.get(key)
            result["supplier"][key] = (str(val).strip() or None) if val not in (None, False) else None
        if result["supplier"]["vat"]:
            result["supplier"]["vat"] = re.sub(r"[\s.-]", "", result["supplier"]["vat"]).upper()
        number = data.get("invoice_number")
        result["invoice_number"] = str(number).strip() or None if number not in (None, False) else None
        result["invoice_date"] = self._date(data.get("invoice_date"))
        result["due_date"] = self._date(data.get("due_date"))
        cur = data.get("currency")
        result["currency"] = str(cur).strip().upper()[:3] if cur else None
        lines = []
        for line in data.get("lines") or []:
            if not isinstance(line, dict):
                continue
            qty = self._num(line.get("quantity"))
            unit_price = self._num(line.get("unit_price"))
            total = self._num(line.get("total"))
            if unit_price is None and total is not None:
                unit_price = total / (qty or 1.0)
            if unit_price is None:
                continue
            lines.append({
                "description": str(line.get("description") or "").strip() or "Line",
                "quantity": qty if qty not in (None, 0) else 1.0,
                "unit_price": float_round(unit_price, precision_digits=4),
                "tax_rate": self._num(line.get("tax_rate")),
                "total": total,
            })
        result["lines"] = lines
        for key in ("untaxed_amount", "tax_amount", "total_amount"):
            result[key] = self._num(data.get(key))
        result["payment_reference"] = data.get("payment_reference") or None
        result["notes"] = data.get("notes") or None
        conf = self._num(data.get("confidence"))
        result["confidence"] = max(0.0, min(1.0, conf)) if conf is not None else None
        return result
