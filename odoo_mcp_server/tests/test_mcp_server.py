# -*- coding: utf-8 -*-
import json

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestMcpServer(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.icp = cls.env["ir.config_parameter"].sudo()
        cls.icp.set_param("odoo_mcp_server.enabled", "True")
        cls.icp.set_param("odoo_mcp_server.allow_writes", "False")
        cls.icp.set_param("odoo_mcp_server.rate_limit", "0")
        cls.mcp_user = cls.env["res.users"].create({
            "name": "MCP Bot", "login": "mcp-bot",
            "group_ids": [(6, 0, [
                cls.env.ref("base.group_user").id,
                cls.env.ref("odoo_mcp_server.group_mcp_user").id,
                cls.env.ref("base.group_partner_manager").id,
            ])],
        })
        cls.key = cls.env["res.users.apikeys"].with_user(cls.mcp_user).sudo()._generate(
            "odoo.mcp", "test key", False)
        cls.partner = cls.env["res.partner"].create({"name": "MCP Test Partner", "email": "mcp@example.com"})

    # ------------------------------------------------------------------
    def _rpc(self, method, params=None, key=None, msg_id=1):
        payload = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        if msg_id is not None:
            payload["id"] = msg_id
        headers = {"Content-Type": "application/json"}
        token = self.key if key is None else key
        if token:
            headers["Authorization"] = "Bearer %s" % token
        return self.url_open("/mcp", data=json.dumps(payload), headers=headers)

    def _call_tool(self, name, arguments=None):
        response = self._rpc("tools/call", {"name": name, "arguments": arguments or {}})
        self.assertEqual(response.status_code, 200)
        result = response.json()["result"]
        if result.get("isError"):
            return result, None
        return result, json.loads(result["content"][0]["text"])

    # ------------------------------------------------------------------
    def test_01_requires_a_valid_key(self):
        self.assertEqual(self._rpc("tools/list", key=False).status_code, 401)
        self.assertEqual(self._rpc("tools/list", key="not-a-real-key").status_code, 401)

    def test_02_initialize_handshake(self):
        response = self._rpc("initialize", {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "claude-desktop", "version": "1.0"},
        })
        self.assertEqual(response.status_code, 200)
        result = response.json()["result"]
        self.assertEqual(result["protocolVersion"], "2025-06-18")
        self.assertEqual(result["serverInfo"]["name"], "odoo-mcp-server")
        self.assertIn("tools", result["capabilities"])
        self.assertIn("odoo_list_models", result["instructions"])

    def test_03_notification_returns_202_without_body(self):
        response = self._rpc("notifications/initialized", {}, msg_id=None)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.text, "")

    def test_04_tools_list_hides_writes_when_disabled(self):
        names = [t["name"] for t in self._rpc("tools/list").json()["result"]["tools"]]
        self.assertIn("odoo_search", names)
        self.assertIn("odoo_read_group", names)
        self.assertNotIn("odoo_create", names)
        self.assertNotIn("odoo_unlink", names)

        self.icp.set_param("odoo_mcp_server.allow_writes", "True")
        try:
            names = [t["name"] for t in self._rpc("tools/list").json()["result"]["tools"]]
            self.assertIn("odoo_create", names)
            self.assertIn("odoo_call_method", names)
        finally:
            self.icp.set_param("odoo_mcp_server.allow_writes", "False")

    def test_05_list_models_and_search(self):
        _result, payload = self._call_tool("odoo_list_models")
        self.assertIn("res.partner", [m["model"] for m in payload["models"]])
        self.assertFalse(payload["write_operations_enabled"])
        self.assertEqual(payload["user"], "MCP Bot")

        _result, payload = self._call_tool("odoo_search", {
            "model": "res.partner", "domain": [["name", "=", "MCP Test Partner"]],
            "fields": ["name", "email"],
        })
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["records"][0]["email"], "mcp@example.com")

    def test_06_unexposed_model_is_refused(self):
        result, _payload = self._call_tool("odoo_search", {"model": "ir.cron"})
        self.assertTrue(result["isError"])
        self.assertIn("not exposed", result["content"][0]["text"])

    def test_07_write_refused_when_globally_disabled(self):
        config = self.env["mcp.model.config"]._get_config("res.partner")
        config.allow_write = True
        try:
            result, _payload = self._call_tool("odoo_write", {
                "model": "res.partner", "ids": [self.partner.id], "values": {"phone": "+3200"}})
            self.assertTrue(result["isError"])
            self.partner.invalidate_recordset()
            self.assertFalse(self.partner.phone)
        finally:
            config.allow_write = False

    def test_08_write_allowed_when_enabled_on_both_levels(self):
        self.icp.set_param("odoo_mcp_server.allow_writes", "True")
        config = self.env["mcp.model.config"]._get_config("res.partner")
        config.write({"allow_write": True, "allow_create": True})
        try:
            result, payload = self._call_tool("odoo_write", {
                "model": "res.partner", "ids": [self.partner.id], "values": {"phone": "+3212345"}})
            self.assertFalse(result.get("isError"), result["content"][0]["text"])
            self.assertEqual(payload["updated"], [self.partner.id])
            self.partner.invalidate_recordset()
            self.assertEqual(self.partner.phone, "+3212345")

            _result, payload = self._call_tool("odoo_create", {
                "model": "res.partner", "values": {"name": "Created by MCP"}})
            self.assertTrue(payload["id"])
            self.assertEqual(payload["display_name"], "Created by MCP")
        finally:
            self.icp.set_param("odoo_mcp_server.allow_writes", "False")
            config.write({"allow_write": False, "allow_create": False})

    def test_09_field_whitelist_is_enforced(self):
        config = self.env["mcp.model.config"]._get_config("res.users")
        self.assertTrue(config.field_names)
        result, _payload = self._call_tool("odoo_search", {"model": "res.users", "fields": ["password"]})
        self.assertTrue(result["isError"])

    def test_10_read_group_aggregates(self):
        _result, payload = self._call_tool("odoo_read_group", {
            "model": "res.partner", "domain": [], "groupby": ["is_company"], "aggregates": ["__count"]})
        self.assertTrue(payload["groups"])
        self.assertIn("__count", payload["groups"][0])

    def test_11_every_call_is_logged(self):
        Log = self.env["mcp.access.log"]
        before = Log.search_count([])
        self._call_tool("odoo_count", {"model": "res.partner"})
        self.assertEqual(Log.search_count([]), before + 1)
        log = Log.search([], order="id desc", limit=1)
        self.assertEqual(log.tool, "odoo_count")
        self.assertEqual(log.state, "done")
        self.assertEqual(log.user_id, self.mcp_user)

    def test_12_resources_expose_schemas(self):
        resources = self._rpc("resources/list").json()["result"]["resources"]
        self.assertIn("odoo://model/res.partner", [r["uri"] for r in resources])
        content = self._rpc("resources/read", {"uri": "odoo://model/res.partner"}).json()["result"]["contents"][0]
        schema = json.loads(content["text"])
        self.assertIn("email", schema["fields"])

    def test_13_endpoint_can_be_switched_off(self):
        self.icp.set_param("odoo_mcp_server.enabled", "False")
        try:
            self.assertEqual(self._rpc("tools/list").status_code, 503)
        finally:
            self.icp.set_param("odoo_mcp_server.enabled", "True")

    def test_14_unknown_method_and_tool(self):
        error = self._rpc("does/not/exist").json()["error"]
        self.assertEqual(error["code"], -32601)
        response = self._rpc("tools/call", {"name": "odoo_drop_database", "arguments": {}})
        self.assertEqual(response.json()["error"]["code"], -32602)
        denied = self.env["mcp.access.log"].search(
            [("tool", "=", "odoo_drop_database")], order="id desc", limit=1)
        self.assertEqual(denied.state, "denied")

    def test_15_call_method_whitelist(self):
        self.icp.set_param("odoo_mcp_server.allow_writes", "True")
        config = self.env["mcp.model.config"]._get_config("res.partner")
        config.allow_write = True
        try:
            result, _payload = self._call_tool("odoo_call_method", {
                "model": "res.partner", "ids": [self.partner.id], "method": "unlink"})
            self.assertTrue(result["isError"])
            self.assertIn("not allowed", result["content"][0]["text"])
            self.assertTrue(self.partner.exists())
        finally:
            self.icp.set_param("odoo_mcp_server.allow_writes", "False")
            config.allow_write = False

    # ------------------------------------------------------------------
    # Security regressions (audit of 2026-09-04)
    # ------------------------------------------------------------------
    def test_16_oversized_body_is_refused_before_authentication(self):
        payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping",
                              "params": {"padding": "x" * (3 * 1024 * 1024)}})
        response = self.url_open("/mcp", data=payload, headers={"Content-Type": "application/json"})
        self.assertEqual(response.status_code, 413)

    def test_17_name_create_cannot_bypass_the_create_flag(self):
        self.icp.set_param("odoo_mcp_server.allow_writes", "True")
        config = self.env["mcp.model.config"]._get_config("res.partner")
        config.write({"allow_write": True, "allow_create": False, "method_names": "name_create"})
        before = self.env["res.partner"].search_count([])
        try:
            result, _payload = self._call_tool("odoo_call_method", {
                "model": "res.partner", "method": "name_create", "args": ["Ghost supplier"]})
            self.assertTrue(result["isError"])
            self.assertIn("creates records", result["content"][0]["text"])
            self.assertEqual(self.env["res.partner"].search_count([]), before)
        finally:
            self.icp.set_param("odoo_mcp_server.allow_writes", "False")
            config.write({"allow_write": False, "method_names": False})

    def test_18_call_method_respects_the_restriction_domain(self):
        self.icp.set_param("odoo_mcp_server.allow_writes", "True")
        config = self.env["mcp.model.config"]._get_config("res.partner")
        config.write({"allow_write": True, "domain": "[('is_company', '=', True)]",
                      "method_names": "message_post"})
        try:
            self.assertFalse(self.partner.is_company)
            result, _payload = self._call_tool("odoo_call_method", {
                "model": "res.partner", "ids": [self.partner.id], "method": "message_post",
                "kwargs": {"body": "out of scope"}})
            self.assertTrue(result["isError"])
            self.assertIn("outside the scope", result["content"][0]["text"])
        finally:
            self.icp.set_param("odoo_mcp_server.allow_writes", "False")
            config.write({"allow_write": False, "domain": "[]", "method_names": False})

    def test_19_secrets_are_redacted_from_the_audit_log(self):
        self.icp.set_param("odoo_mcp_server.allow_writes", "True")
        config = self.env["mcp.model.config"]._get_config("res.partner")
        config.allow_write = True
        try:
            self._call_tool("odoo_write", {
                "model": "res.partner", "ids": [self.partner.id],
                "values": {"comment": "ok", "api_key": "sk-do-not-store-me"}})
            log = self.env["mcp.access.log"].search([("tool", "=", "odoo_write")], order="id desc", limit=1)
            self.assertNotIn("sk-do-not-store-me", log.arguments or "")
            self.assertIn("***", log.arguments or "")
        finally:
            self.icp.set_param("odoo_mcp_server.allow_writes", "False")
            config.allow_write = False

    def test_20_too_many_ids_is_refused(self):
        result, _payload = self._call_tool("odoo_read", {
            "model": "res.partner", "ids": list(range(1, 1502))})
        self.assertTrue(result["isError"])
        self.assertIn("Too many ids", result["content"][0]["text"])
