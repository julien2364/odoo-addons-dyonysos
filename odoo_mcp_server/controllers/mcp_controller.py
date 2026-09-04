# -*- coding: utf-8 -*-
"""Model Context Protocol endpoint served by Odoo itself.

Transport: Streamable HTTP (a single POST endpoint carrying JSON-RPC 2.0).
Authentication: an Odoo API key with scope ``odoo.mcp`` in the
``Authorization: Bearer <key>`` header. Every call then runs in the environment
of that key's user, so Odoo's groups, access rights, record rules and
multi-company rules apply exactly as they do in the web client.
"""
import json
import logging
import time

from odoo import _, http
from odoo.exceptions import AccessDenied, AccessError, UserError, ValidationError
from odoo.http import request

from odoo.addons.odoo_mcp_server.models.mcp_model_config import CREATING_METHODS

_logger = logging.getLogger(__name__)

MCP_SCOPE = "odoo.mcp"
PROTOCOL_VERSION = "2025-06-18"
SERVER_INFO = {"name": "odoo-mcp-server", "version": "19.0.1.0.0", "title": "Odoo"}

# JSON-RPC error codes (MCP reuses the JSON-RPC 2.0 ones).
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

MAX_BODY_BYTES = 2 * 1024 * 1024   # a JSON-RPC call never legitimately reaches this
MAX_IDS = 1000                     # cap on odoo_read / odoo_write / odoo_unlink
SECRET_HINTS = ("password", "passwd", "secret", "token", "api_key", "apikey",
                "private", "credential", "iban", "authorization")

_RATE_BUCKET = {}


def _redact(value):
    """Blank out anything that looks like a credential before it reaches the audit log."""
    if isinstance(value, dict):
        return {k: ("***" if any(h in str(k).lower() for h in SECRET_HINTS) else _redact(v))
                for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value


class McpError(Exception):
    def __init__(self, message, code=INTERNAL_ERROR):
        super().__init__(message)
        self.code = code


class OdooMcpController(http.Controller):

    # ==================================================================
    # HTTP plumbing
    # ==================================================================
    @http.route("/mcp", type="http", auth="none", methods=["POST", "OPTIONS"], csrf=False, save_session=False, cors="*", readonly=False)
    def mcp_endpoint(self, **kwargs):
        if request.httprequest.method == "OPTIONS":
            return request.make_response("", headers=[
                ("Access-Control-Allow-Origin", "*"),
                ("Access-Control-Allow-Methods", "POST, OPTIONS"),
                ("Access-Control-Allow-Headers", "Authorization, Content-Type, Mcp-Session-Id, MCP-Protocol-Version"),
            ])

        icp = request.env["ir.config_parameter"].sudo()
        if icp.get_param("odoo_mcp_server.enabled", "True") != "True":
            return self._json({"jsonrpc": "2.0", "id": None,
                               "error": {"code": INTERNAL_ERROR, "message": "MCP endpoint disabled"}}, status=503)

        content_length = request.httprequest.content_length or 0
        if content_length > MAX_BODY_BYTES:
            return self._json({"jsonrpc": "2.0", "id": None,
                               "error": {"code": INVALID_REQUEST, "message": "Request body too large"}},
                              status=413)
        raw_body = request.httprequest.get_data(cache=False, parse_form_data=False)
        if len(raw_body) > MAX_BODY_BYTES:
            return self._json({"jsonrpc": "2.0", "id": None,
                               "error": {"code": INVALID_REQUEST, "message": "Request body too large"}},
                              status=413)

        try:
            body = json.loads(raw_body or b"{}")
        except ValueError:
            return self._json({"jsonrpc": "2.0", "id": None,
                               "error": {"code": PARSE_ERROR, "message": "Parse error"}}, status=400)

        uid = self._authenticate()
        if not uid:
            return self._json({"jsonrpc": "2.0", "id": (body or {}).get("id") if isinstance(body, dict) else None,
                               "error": {"code": INVALID_REQUEST, "message": "Invalid or missing API key"}},
                              status=401, extra_headers=[("WWW-Authenticate", 'Bearer realm="odoo-mcp"')])
        request.update_env(user=uid)

        if not self._check_rate_limit(uid):
            return self._json({"jsonrpc": "2.0", "id": (body or {}).get("id") if isinstance(body, dict) else None,
                               "error": {"code": INTERNAL_ERROR, "message": "Rate limit exceeded"}}, status=429)

        if isinstance(body, list):
            responses = [r for r in (self._handle(msg) for msg in body) if r is not None]
            return self._json(responses) if responses else self._json("", status=202)
        response = self._handle(body)
        if response is None:  # notification: no body expected
            return self._json("", status=202)
        return self._json(response)

    @staticmethod
    def _json(data, status=200, extra_headers=None):
        headers = [("Access-Control-Allow-Origin", "*"), ("MCP-Protocol-Version", PROTOCOL_VERSION)]
        if extra_headers:
            headers += extra_headers
        if data == "":
            return request.make_response("", headers=headers, status=status)
        return request.make_json_response(data, headers=headers, status=status)

    @staticmethod
    def _authenticate():
        auth = request.httprequest.headers.get("Authorization", "")
        key = None
        if auth.lower().startswith("bearer "):
            key = auth[7:].strip()
        elif request.httprequest.headers.get("X-Api-Key"):
            key = request.httprequest.headers["X-Api-Key"].strip()
        if not key:
            return None
        try:
            return request.env["res.users.apikeys"].sudo()._check_credentials(scope=MCP_SCOPE, key=key)
        except Exception:  # noqa: BLE001 - never leak why authentication failed
            _logger.info("MCP: authentication failed from %s", request.httprequest.remote_addr)
            return None

    @staticmethod
    def _check_rate_limit(uid):
        limit = int(request.env["ir.config_parameter"].sudo().get_param("odoo_mcp_server.rate_limit", "120") or 120)
        if limit <= 0:
            return True
        minute = int(time.time() // 60)
        for key in [k for k in list(_RATE_BUCKET) if k[1] < minute]:
            _RATE_BUCKET.pop(key, None)
        bucket_key = (uid, minute)
        _RATE_BUCKET[bucket_key] = _RATE_BUCKET.get(bucket_key, 0) + 1
        return _RATE_BUCKET[bucket_key] <= limit

    # ==================================================================
    # JSON-RPC dispatch
    # ==================================================================
    def _handle(self, message):
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
            return {"jsonrpc": "2.0", "id": None,
                    "error": {"code": INVALID_REQUEST, "message": "Invalid Request"}}
        method = message.get("method")
        msg_id = message.get("id")
        params = message.get("params") or {}
        is_notification = "id" not in message

        try:
            if method == "initialize":
                result = self._on_initialize(params)
            elif method in ("notifications/initialized", "notifications/cancelled"):
                return None
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": self._tool_definitions()}
            elif method == "tools/call":
                result = self._on_tools_call(params)
            elif method == "resources/list":
                result = {"resources": self._resource_definitions()}
            elif method == "resources/read":
                result = self._on_resources_read(params)
            elif method == "prompts/list":
                result = {"prompts": []}
            else:
                if is_notification:
                    return None
                return {"jsonrpc": "2.0", "id": msg_id,
                        "error": {"code": METHOD_NOT_FOUND, "message": "Method not found: %s" % method}}
        except McpError as e:
            if is_notification:
                return None
            return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": e.code, "message": str(e)}}
        except Exception as e:  # noqa: BLE001
            _logger.exception("MCP: unhandled error on %s", method)
            if is_notification:
                return None
            return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": INTERNAL_ERROR, "message": str(e)}}

        if is_notification:
            return None
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}

    def _on_initialize(self, params):
        client = (params.get("clientInfo") or {}).get("name") or "unknown"
        try:
            request.session.mcp_client = client
        except Exception:  # noqa: BLE001 - sessionless transport
            pass
        return {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}, "resources": {"listChanged": False}},
            "serverInfo": SERVER_INFO,
            "instructions": (
                "This server exposes an Odoo ERP database. Call odoo_list_models first to discover what is "
                "available, then odoo_model_fields to learn a model's fields before searching or writing. "
                "Domains use the Odoo list syntax, e.g. "
                "[['state','=','posted'],['amount_total','>',100]]. Every call runs with the permissions of "
                "the Odoo user owning the API key and is written to an audit log."
            ),
        }

    # ==================================================================
    # Tools
    # ==================================================================
    def _writes_allowed(self):
        return request.env["ir.config_parameter"].sudo().get_param("odoo_mcp_server.allow_writes", "False") == "True"

    def _tool_definitions(self):
        model_enum = request.env["mcp.model.config"].sudo().search([]).mapped("model_name") or None
        tools = [
            {
                "name": "odoo_list_models",
                "title": "List available Odoo models",
                "description": "List the Odoo models exposed to this MCP server, with the operations allowed "
                               "on each. Always call this first.",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "odoo_model_fields",
                "title": "Describe a model",
                "description": "Return the fields of an Odoo model: technical name, label, type, required, "
                               "readonly, selection values and related model. Call it before searching or writing.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "model": {"type": "string", "description": "Technical model name", "enum": model_enum},
                        "attributes": {"type": "array", "items": {"type": "string"},
                                       "description": "Field attributes to return (default: a useful subset)"},
                    },
                    "required": ["model"],
                },
            },
            {
                "name": "odoo_search",
                "title": "Search records",
                "description": "Search records and return the requested fields. Combines search and read in one call.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "model": {"type": "string", "enum": model_enum},
                        "domain": {"type": "array", "description": "Odoo domain, e.g. [['name','ilike','acme']]"},
                        "fields": {"type": "array", "items": {"type": "string"}},
                        "limit": {"type": "integer"},
                        "offset": {"type": "integer"},
                        "order": {"type": "string", "description": "e.g. 'date desc, id desc'"},
                    },
                    "required": ["model"],
                },
            },
            {
                "name": "odoo_read",
                "title": "Read records by ID",
                "description": "Read specific records by their database ids.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "model": {"type": "string", "enum": model_enum},
                        "ids": {"type": "array", "items": {"type": "integer"}},
                        "fields": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["model", "ids"],
                },
            },
            {
                "name": "odoo_count",
                "title": "Count records",
                "description": "Count the records matching a domain, without reading them.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"model": {"type": "string", "enum": model_enum},
                                   "domain": {"type": "array"}},
                    "required": ["model"],
                },
            },
            {
                "name": "odoo_read_group",
                "title": "Aggregate records",
                "description": "Group and aggregate records, the way Odoo pivot views do. Use it for totals, "
                               "counts per period, sales per customer, and so on.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "model": {"type": "string", "enum": model_enum},
                        "domain": {"type": "array"},
                        "groupby": {"type": "array", "items": {"type": "string"},
                                    "description": "e.g. ['partner_id'] or ['invoice_date:month']"},
                        "aggregates": {"type": "array", "items": {"type": "string"},
                                       "description": "e.g. ['amount_total:sum', '__count']"},
                        "limit": {"type": "integer"},
                    },
                    "required": ["model", "groupby"],
                },
            },
        ]
        if self._writes_allowed():
            tools += [
                {
                    "name": "odoo_create",
                    "title": "Create a record",
                    "description": "Create one record. Returns its id and display name.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"model": {"type": "string", "enum": model_enum},
                                       "values": {"type": "object"}},
                        "required": ["model", "values"],
                    },
                },
                {
                    "name": "odoo_write",
                    "title": "Update records",
                    "description": "Update one or more records with the given values.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"model": {"type": "string", "enum": model_enum},
                                       "ids": {"type": "array", "items": {"type": "integer"}},
                                       "values": {"type": "object"}},
                        "required": ["model", "ids", "values"],
                    },
                },
                {
                    "name": "odoo_unlink",
                    "title": "Delete records",
                    "description": "Permanently delete records. Use with care; prefer archiving (active=false).",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"model": {"type": "string", "enum": model_enum},
                                       "ids": {"type": "array", "items": {"type": "integer"}}},
                        "required": ["model", "ids"],
                    },
                },
                {
                    "name": "odoo_call_method",
                    "title": "Call a business method",
                    "description": "Call a whitelisted method on records, e.g. action_post to validate an invoice.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"model": {"type": "string", "enum": model_enum},
                                       "ids": {"type": "array", "items": {"type": "integer"}},
                                       "method": {"type": "string"},
                                       "args": {"type": "array"}, "kwargs": {"type": "object"}},
                        "required": ["model", "method"],
                    },
                },
            ]
        return tools

    def _on_tools_call(self, params):
        name = params.get("name")
        args = params.get("arguments") or {}
        started = time.time()
        log_vals = {
            "user_id": request.env.uid,
            "client_name": getattr(request.session, "mcp_client", False) or "unknown",
            "tool": name or "?",
            "model_name": args.get("model"),
            "method": args.get("method"),
            "ip": request.httprequest.remote_addr,
        }
        icp = request.env["ir.config_parameter"].sudo()
        if icp.get_param("odoo_mcp_server.log_arguments", "True") == "True":
            log_vals["arguments"] = json.dumps(_redact(args), ensure_ascii=False, default=str)[:8000]

        handler = getattr(self, "_tool_" + (name or ""), None)
        if handler is None or not name or not name.startswith("odoo_"):
            self._log({**log_vals, "state": "denied", "error": "Unknown tool", "duration": 0})
            raise McpError("Unknown tool: %s" % name, INVALID_PARAMS)

        try:
            payload, touched = handler(args)
        except (AccessError, AccessDenied) as e:
            self._log({**log_vals, "state": "denied", "error": str(e), "duration": (time.time() - started) * 1000})
            return self._tool_error(_("Access denied: %s", e))
        except (UserError, ValidationError) as e:
            self._log({**log_vals, "state": "error", "error": str(e), "duration": (time.time() - started) * 1000})
            return self._tool_error(str(e))
        except McpError as e:
            self._log({**log_vals, "state": "denied", "error": str(e), "duration": (time.time() - started) * 1000})
            return self._tool_error(str(e))
        except Exception as e:  # noqa: BLE001
            _logger.exception("MCP: tool %s failed", name)
            self._log({**log_vals, "state": "error", "error": str(e), "duration": (time.time() - started) * 1000})
            return self._tool_error(_("Odoo error: %s", e))

        self._log({**log_vals, "state": "done", "duration": (time.time() - started) * 1000,
                   "record_ids": ",".join(str(i) for i in (touched or [])[:50]) or False,
                   "record_count": len(touched or [])})
        return {
            "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False, indent=1, default=str)}],
            "structuredContent": payload if isinstance(payload, dict) else {"result": payload},
            "isError": False,
        }

    @staticmethod
    def _tool_error(message):
        return {"content": [{"type": "text", "text": message}], "isError": True}

    @staticmethod
    def _log(vals):
        try:
            request.env["mcp.access.log"].sudo().create(vals)
        except Exception:  # noqa: BLE001 - logging must never break a call
            _logger.exception("MCP: could not write the access log")

    # ------------------------------------------------------------------
    # Guards
    # ------------------------------------------------------------------
    def _config(self, model_name, operation="read"):
        if not model_name:
            raise McpError("The 'model' argument is required.", INVALID_PARAMS)
        config = request.env["mcp.model.config"]._get_config(model_name)
        if not config:
            raise McpError("Model '%s' is not exposed to MCP. Call odoo_list_models to see what is."
                           % model_name, INVALID_PARAMS)
        if operation != "read" and not self._writes_allowed():
            raise McpError("Write operations are disabled on this Odoo (Settings > General > MCP Server).",
                           INVALID_PARAMS)
        if not config["allow_" + operation]:
            raise McpError("Operation '%s' is not allowed on %s." % (operation, model_name), INVALID_PARAMS)
        if model_name not in request.env:
            raise McpError("Unknown model %s." % model_name, INVALID_PARAMS)
        return config

    @staticmethod
    def _clean_ids(args):
        ids = [int(i) for i in (args.get("ids") or [])]
        if len(ids) > MAX_IDS:
            raise McpError("Too many ids in one call (%d, maximum %d)." % (len(ids), MAX_IDS), INVALID_PARAMS)
        return ids

    @staticmethod
    def _clean_fields(config, fields_arg, model):
        allowed = config._get_fields()
        if fields_arg:
            requested = [f for f in fields_arg if isinstance(f, str)]
            if allowed:
                refused = [f for f in requested if f not in allowed]
                if refused:
                    raise McpError(
                        "Field(s) not exposed on %s: %s. Allowed: %s"
                        % (model, ", ".join(refused), ", ".join(allowed)), INVALID_PARAMS)
        else:
            requested = allowed or [
                name for name, descr in request.env[model].fields_get().items()
                if descr.get("type") not in ("binary", "one2many", "many2many")
            ][:40]
        if allowed:
            requested = [f for f in requested if f in allowed]
        unknown = [f for f in requested if f not in request.env[model]._fields]
        if unknown:
            raise McpError("Unknown field(s) on %s: %s" % (model, ", ".join(unknown)), INVALID_PARAMS)
        return requested or ["display_name"]

    @staticmethod
    def _serialise(records, field_names):
        rows = records.read(field_names)
        for row in rows:
            for key, value in list(row.items()):
                if isinstance(value, tuple) and len(value) == 2:  # many2one → {id, name}
                    row[key] = {"id": value[0], "name": value[1]}
                elif isinstance(value, bytes):
                    row[key] = "<binary %d bytes>" % len(value)
        return rows

    # ------------------------------------------------------------------
    # Tool implementations. Each returns (payload, touched_ids)
    # ------------------------------------------------------------------
    def _tool_odoo_list_models(self, args):
        configs = request.env["mcp.model.config"].sudo().search([])
        writes = self._writes_allowed()
        models_payload = []
        for config in configs:
            if config.model_name not in request.env:
                continue
            try:
                request.env[config.model_name].check_access("read")
            except (AccessError, AccessDenied):
                continue
            models_payload.append({
                "model": config.model_name,
                "name": config.model_id.name,
                "description": config.description or "",
                "operations": {
                    "read": config.allow_read,
                    "create": bool(config.allow_create and writes),
                    "write": bool(config.allow_write and writes),
                    "unlink": bool(config.allow_unlink and writes),
                },
            })
        return {"models": models_payload, "write_operations_enabled": writes,
                "user": request.env.user.name, "company": request.env.company.name}, []

    def _tool_odoo_model_fields(self, args):
        config = self._config(args.get("model"))
        model = args["model"]
        attributes = args.get("attributes") or [
            "string", "type", "required", "readonly", "relation", "selection", "help", "store"]
        fields_info = request.env[model].fields_get(attributes=attributes)
        allowed = config._get_fields()
        if allowed:
            fields_info = {k: v for k, v in fields_info.items() if k in allowed}
        return {"model": model, "name": config.model_id.name, "fields": fields_info}, []

    def _tool_odoo_search(self, args):
        config = self._config(args.get("model"))
        model = args["model"]
        domain = list(args.get("domain") or []) + config._get_domain()
        limit = config._clamp_limit(args.get("limit"))
        field_names = self._clean_fields(config, args.get("fields"), model)
        records = request.env[model].search(
            domain, limit=limit, offset=int(args.get("offset") or 0), order=args.get("order") or None)
        total = request.env[model].search_count(domain)
        return {"model": model, "count": len(records), "total_matching": total,
                "records": self._serialise(records, field_names)}, records.ids

    def _tool_odoo_read(self, args):
        config = self._config(args.get("model"))
        model = args["model"]
        ids = self._clean_ids(args)
        if not ids:
            raise McpError("The 'ids' argument is required.", INVALID_PARAMS)
        field_names = self._clean_fields(config, args.get("fields"), model)
        records = request.env[model].browse(ids).exists()
        if config._get_domain():
            records = records.filtered_domain(config._get_domain())
        return {"model": model, "records": self._serialise(records, field_names)}, records.ids

    def _tool_odoo_count(self, args):
        config = self._config(args.get("model"))
        domain = list(args.get("domain") or []) + config._get_domain()
        return {"model": args["model"], "count": request.env[args["model"]].search_count(domain)}, []

    def _tool_odoo_read_group(self, args):
        config = self._config(args.get("model"))
        model = args["model"]
        domain = list(args.get("domain") or []) + config._get_domain()
        groupby = [g for g in (args.get("groupby") or []) if isinstance(g, str)]
        if not groupby:
            raise McpError("The 'groupby' argument is required.", INVALID_PARAMS)
        aggregates = [a for a in (args.get("aggregates") or ["__count"]) if isinstance(a, str)]
        rows = request.env[model]._read_group(
            domain, groupby=groupby, aggregates=aggregates, limit=config._clamp_limit(args.get("limit")))
        payload = []
        for row in rows:
            entry = {}
            for idx, key in enumerate(groupby + aggregates):
                value = row[idx]
                if hasattr(value, "ids"):  # a recordset came back for a many2one group
                    value = {"id": value.id, "name": value.display_name} if value else None
                entry[key] = value
            payload.append(entry)
        return {"model": model, "groups": payload}, []

    def _tool_odoo_create(self, args):
        self._config(args.get("model"), "create")
        values = args.get("values")
        if not isinstance(values, dict) or not values:
            raise McpError("The 'values' argument must be a non-empty object.", INVALID_PARAMS)
        record = request.env[args["model"]].create(values)
        return {"model": args["model"], "id": record.id, "display_name": record.display_name}, record.ids

    def _tool_odoo_write(self, args):
        config = self._config(args.get("model"), "write")
        ids = self._clean_ids(args)
        values = args.get("values")
        if not ids or not isinstance(values, dict) or not values:
            raise McpError("Both 'ids' and a non-empty 'values' object are required.", INVALID_PARAMS)
        records = request.env[args["model"]].browse(ids).exists()
        if config._get_domain():
            records = records.filtered_domain(config._get_domain())
        if not records:
            raise McpError("No record matches these ids within the allowed scope.", INVALID_PARAMS)
        records.write(values)
        return {"model": args["model"], "updated": records.ids}, records.ids

    def _tool_odoo_unlink(self, args):
        config = self._config(args.get("model"), "unlink")
        ids = [int(i) for i in (args.get("ids") or [])]
        if not ids:
            raise McpError("The 'ids' argument is required.", INVALID_PARAMS)
        records = request.env[args["model"]].browse(ids).exists()
        if config._get_domain():
            records = records.filtered_domain(config._get_domain())
        deleted = records.ids
        records.unlink()
        return {"model": args["model"], "deleted": deleted}, deleted

    def _tool_odoo_call_method(self, args):
        config = self._config(args.get("model"), "write")
        method = args.get("method")
        if not method or method.startswith("_"):
            raise McpError("Invalid method name.", INVALID_PARAMS)
        if method not in config._get_methods():
            raise McpError("Method '%s' is not allowed on %s. Allowed: %s"
                           % (method, args["model"], ", ".join(sorted(config._get_methods()))), INVALID_PARAMS)
        if method in CREATING_METHODS and not config.allow_create:
            raise McpError("Method '%s' creates records, which is not allowed on %s."
                           % (method, args["model"]), INVALID_PARAMS)
        records = request.env[args["model"]].browse(self._clean_ids(args)).exists()
        if config._get_domain():
            allowed = records.filtered_domain(config._get_domain())
            if allowed != records:
                raise McpError("Some records are outside the scope allowed for %s." % args["model"], INVALID_PARAMS)
            records = allowed
        target = getattr(records, method, None)
        if not callable(target):
            raise McpError("Model %s has no method %s." % (args["model"], method), INVALID_PARAMS)
        result = target(*(args.get("args") or []), **(args.get("kwargs") or {}))
        if hasattr(result, "ids"):
            result = {"records": result.ids}
        elif not isinstance(result, (dict, list, str, int, float, bool, type(None))):
            result = str(result)
        return {"model": args["model"], "method": method, "ids": records.ids, "result": result}, records.ids

    # ==================================================================
    # Resources
    # ==================================================================
    def _resource_definitions(self):
        resources = []
        for config in request.env["mcp.model.config"].sudo().search([]):
            resources.append({
                "uri": "odoo://model/%s" % config.model_name,
                "name": config.model_id.name,
                "description": config.description or ("Schema of the Odoo model %s" % config.model_name),
                "mimeType": "application/json",
            })
        return resources

    def _on_resources_read(self, params):
        uri = params.get("uri") or ""
        if not uri.startswith("odoo://model/"):
            raise McpError("Unknown resource: %s" % uri, INVALID_PARAMS)
        model = uri[len("odoo://model/"):]
        payload, _touched = self._tool_odoo_model_fields({"model": model})
        return {"contents": [{"uri": uri, "mimeType": "application/json",
                              "text": json.dumps(payload, ensure_ascii=False, indent=1, default=str)}]}
