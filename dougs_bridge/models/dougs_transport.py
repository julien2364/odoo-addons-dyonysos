# -*- coding: utf-8 -*-
"""Transports used to hand a batch of accounting documents to the accountant.

Each transport receives the batch record, the ZIP bytes and the list of files
``[(filename, bytes, line_record_or_None)]`` and returns a human readable log
string. It raises ``DougsTransportError`` on failure.

Transports
----------
* download  – nothing is sent; the ZIP is attached to the batch for manual upload.
* email     – the ZIP is emailed to the accountant's collection address.
* folder    – files are written to a directory on the Odoo server (a synced
              Google Drive / Nextcloud / Dropbox folder, for example).
* sftp      – files are uploaded with SFTP (requires the ``paramiko`` package).
* apifirst  – documents are POSTed one by one to a REST endpoint (Dougs API First
              or any accountant API); paths and field names are configurable.
"""
import json
import logging
import os
import posixpath
import re

_logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None


class DougsTransportError(Exception):
    pass


def safe_filename(name):
    name = re.sub(r"[^\w.\-()]+", "_", name or "document")
    return name[:150]


class DougsTransport:
    def __init__(self, env):
        self.env = env
        self.icp = env["ir.config_parameter"].sudo()

    def param(self, key, default=""):
        return self.icp.get_param("dougs_bridge." + key, default) or default

    # ------------------------------------------------------------------
    def send(self, batch, zip_bytes, files):
        transport = batch.transport or self.param("transport", "download")
        handler = getattr(self, "_send_" + transport, None)
        if handler is None:
            raise DougsTransportError("Unknown transport %r" % transport)
        return handler(batch, zip_bytes, files)

    # ------------------------------------------------------------------
    def _send_download(self, batch, zip_bytes, files):
        return "ZIP ready for manual upload (%d files)." % len(files)

    def _send_email(self, batch, zip_bytes, files):
        email_to = self.param("email_to")
        if not email_to:
            raise DougsTransportError("No accountant email configured (Settings > Accounting > Dougs Bridge).")
        template = self.env.ref("dougs_bridge.mail_template_dougs_send")
        attachment = self.env["ir.attachment"].create({
            "name": "%s.zip" % batch.name,
            "raw": zip_bytes,
            "mimetype": "application/zip",
            "res_model": batch._name,
            "res_id": batch.id,
        })
        template.send_mail(batch.id, email_values={"email_to": email_to, "attachment_ids": [attachment.id]}, force_send=True)
        return "Batch emailed to %s (%d files, %.1f KB)." % (email_to, len(files), len(zip_bytes) / 1024.0)

    def _send_folder(self, batch, zip_bytes, files):
        root = self.param("folder_path")
        if not root:
            raise DougsTransportError("No export folder configured.")
        target = os.path.join(root, batch.name)
        try:
            os.makedirs(target, exist_ok=True)
            for filename, content, _line in files:
                with open(os.path.join(target, safe_filename(filename)), "wb") as fh:
                    fh.write(content)
        except OSError as e:
            raise DougsTransportError("Cannot write to %s: %s" % (target, e))
        return "%d files written to %s." % (len(files), target)

    def _send_sftp(self, batch, zip_bytes, files):
        try:
            import paramiko
        except ImportError:
            raise DougsTransportError("The 'paramiko' Python package is required for SFTP (pip install paramiko).")
        host = self.param("sftp_host")
        if not host:
            raise DougsTransportError("No SFTP host configured.")
        port = int(self.param("sftp_port", "22") or 22)
        user = self.param("sftp_user")
        password = self.param("sftp_password")
        root = self.param("sftp_path", "/") or "/"
        target = posixpath.join(root, batch.name)
        try:
            transport = paramiko.Transport((host, port))
            transport.connect(username=user, password=password)
            sftp = paramiko.SFTPClient.from_transport(transport)
            try:
                sftp.mkdir(target)
            except IOError:
                pass  # already exists
            for filename, content, _line in files:
                with sftp.open(posixpath.join(target, safe_filename(filename)), "wb") as fh:
                    fh.write(content)
            sftp.close()
            transport.close()
        except Exception as e:  # noqa: BLE001
            raise DougsTransportError("SFTP error: %s" % e)
        return "%d files uploaded to sftp://%s%s." % (len(files), host, target)

    def _send_apifirst(self, batch, zip_bytes, files):
        """Generic REST upload: one multipart POST per document.

        Settings > Accounting > Dougs Bridge:
          apifirst_base_url   e.g. https://api.apifirst.fr
          apifirst_api_key    Bearer token given by Dougs / API First
          apifirst_path_sale, apifirst_path_purchase, apifirst_path_expense
                              endpoint paths (defaults /v1/invoices/outgoing, /v1/invoices/incoming, /v1/receipts)
          apifirst_file_field name of the multipart file field (default "file")
        The JSON metadata of the document is sent in the "metadata" form field.
        """
        if requests is None:
            raise DougsTransportError("The 'requests' Python package is required.")
        base_url = self.param("apifirst_base_url").rstrip("/")
        api_key = self.param("apifirst_api_key")
        if not base_url or not api_key:
            raise DougsTransportError("API First base URL and API key must be configured.")
        paths = {
            "out": self.param("apifirst_path_sale", "/v1/invoices/outgoing"),
            "in": self.param("apifirst_path_purchase", "/v1/invoices/incoming"),
            "expense": self.param("apifirst_path_expense", "/v1/receipts"),
        }
        file_field = self.param("apifirst_file_field", "file")
        headers = {"Authorization": "Bearer " + api_key, "Accept": "application/json"}
        sent = 0
        errors = []
        for filename, content, line in files:
            if line is None or not filename.lower().endswith(".pdf"):
                continue  # journal.csv and companion XML files are not posted individually
            kind = "expense" if line.doc_type == "expense" else ("out" if line.doc_type.startswith("out") else "in")
            url = base_url + paths[kind]
            metadata = line._apifirst_metadata()
            try:
                resp = requests.post(
                    url, headers=headers, timeout=60,
                    files={file_field: (filename, content, "application/pdf")},
                    data={"metadata": json.dumps(metadata, ensure_ascii=False)},
                )
            except requests.RequestException as e:
                errors.append("%s: %s" % (filename, e))
                line._mark_error(str(e))
                continue
            if resp.status_code >= 400:
                msg = "HTTP %s %s" % (resp.status_code, resp.text[:300])
                errors.append("%s: %s" % (filename, msg))
                line._mark_error(msg)
                continue
            try:
                remote_id = (resp.json() or {}).get("id")
            except ValueError:
                remote_id = None
            line.write({"remote_id": str(remote_id) if remote_id else False})
            sent += 1
        log = "%d document(s) posted to %s." % (sent, base_url)
        if errors:
            log += "\nErrors:\n" + "\n".join(errors)
            if not sent:
                raise DougsTransportError(log)
        return log
