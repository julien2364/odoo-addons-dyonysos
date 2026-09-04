# -*- coding: utf-8 -*-
"""Couche d'accès à l'API Packlink PRO.

Tous les appels réseau du module passent par :meth:`PacklinkApi._request` :
c'est le point unique qui porte l'authentification, le délai d'attente, les
tentatives et la traduction des erreurs HTTP en message lisible.

L'URL de base et l'en-tête d'authentification sont paramétrables sur le compte
Packlink : la documentation de l'API est livrée avec la clé et peut évoluer,
le module n'a donc rien de figé en dur.
"""
import logging
import time

_logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:  # pragma: no cover - dépendance déclarée au manifeste
    requests = None

DEFAULT_BASE_URL = "https://api.packlink.com/v1"
DEFAULT_AUTH_HEADER = "Authorization"
DEFAULT_TIMEOUT = 30
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = 1.0
# Une étiquette peut peser quelques centaines de kilo-octets ; au-delà, c'est
# une réponse inattendue que l'on refuse plutôt que de la stocker.
MAX_LABEL_BYTES = 10 * 1024 * 1024


class PacklinkApiError(Exception):
    """Erreur lisible remontée par la couche Packlink."""

    def __init__(self, message, status_code=None, payload=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload

    def __str__(self):
        if self.status_code:
            return "[HTTP %s] %s" % (self.status_code, self.message)
        return self.message


class PacklinkApi:
    """Client Packlink PRO minimal, instancié depuis un ``packlink.account``."""

    def __init__(self, api_key, base_url=None, auth_header=None, auth_scheme="",
                 timeout=DEFAULT_TIMEOUT):
        if not api_key:
            raise PacklinkApiError("Clé API Packlink manquante sur le compte.")
        self.api_key = api_key
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.auth_header = auth_header or DEFAULT_AUTH_HEADER
        self.auth_scheme = (auth_scheme or "").strip()
        self.timeout = timeout

    @classmethod
    def from_account(cls, account):
        return cls(
            api_key=account.api_key,
            base_url=account.base_url,
            auth_header=account.auth_header,
            auth_scheme=account.auth_scheme,
            timeout=account.timeout or DEFAULT_TIMEOUT,
        )

    # ------------------------------------------------------------------
    # Transport
    # ------------------------------------------------------------------
    def _headers(self, json_body=True):
        value = "%s %s" % (self.auth_scheme, self.api_key) if self.auth_scheme else self.api_key
        headers = {self.auth_header: value, "Accept": "application/json"}
        if json_body:
            headers["Content-Type"] = "application/json"
        return headers

    def _request(self, method, path, params=None, payload=None, raw=False):
        if requests is None:
            raise PacklinkApiError(
                "La bibliothèque Python « requests » est requise par le connecteur Packlink.")
        url = "%s%s" % (self.base_url, path)
        last_error = None
        for attempt in range(MAX_ATTEMPTS):
            try:
                response = requests.request(
                    method, url, headers=self._headers(json_body=payload is not None),
                    params=params, json=payload, timeout=self.timeout)
            except Exception as exc:  # noqa: BLE001 - réseau
                last_error = PacklinkApiError("Appel Packlink impossible : %s" % exc)
                time.sleep(BACKOFF_SECONDS * (attempt + 1))
                continue
            # 429 et 5xx : on retente, le reste est définitif.
            if response.status_code == 429 or 500 <= response.status_code < 600:
                last_error = PacklinkApiError(
                    self._error_message(response), status_code=response.status_code)
                time.sleep(BACKOFF_SECONDS * (attempt + 1))
                continue
            if response.status_code >= 400:
                raise PacklinkApiError(
                    self._error_message(response), status_code=response.status_code)
            if raw:
                content = response.content or b""
                if len(content) > MAX_LABEL_BYTES:
                    raise PacklinkApiError("Réponse Packlink anormalement volumineuse.")
                return content
            if not response.content:
                return {}
            try:
                return response.json()
            except ValueError:
                raise PacklinkApiError("Réponse Packlink illisible (JSON attendu).",
                                       status_code=response.status_code)
        raise last_error or PacklinkApiError("Appel Packlink échoué.")

    @staticmethod
    def _error_message(response):
        try:
            data = response.json()
        except ValueError:
            return (response.text or "")[:300] or "Erreur Packlink sans message."
        for key in ("message", "error", "detail", "messages"):
            value = data.get(key) if isinstance(data, dict) else None
            if value:
                return str(value)[:300]
        return str(data)[:300]

    # ------------------------------------------------------------------
    # Opérations
    # ------------------------------------------------------------------
    def get_services(self, origin, destination, parcels, source="PRO"):
        """Tarifs disponibles pour ce colis.

        ``origin`` / ``destination`` : {"country", "zip"}.
        ``parcels`` : liste de {"weight", "length", "width", "height"}.
        """
        params = {
            "from[country]": origin.get("country") or "",
            "from[zip]": origin.get("zip") or "",
            "to[country]": destination.get("country") or "",
            "to[zip]": destination.get("zip") or "",
            "source": source,
        }
        for index, parcel in enumerate(parcels or []):
            for key in ("weight", "length", "width", "height"):
                params["packages[%s][%s]" % (index, key)] = parcel.get(key) or 0
        data = self._request("GET", "/services", params=params)
        if isinstance(data, dict):
            data = data.get("services") or data.get("data") or []
        return [s for s in data if isinstance(s, dict)]

    def create_shipment(self, payload):
        return self._request("POST", "/shipments", payload=payload)

    def get_shipment(self, reference):
        return self._request("GET", "/shipments/%s" % reference)

    def get_labels(self, reference):
        """Retourne la liste des URL d'étiquettes, ou les octets du PDF."""
        data = self._request("GET", "/shipments/%s/labels" % reference)
        if isinstance(data, list):
            return [u for u in data if isinstance(u, str)]
        if isinstance(data, dict):
            urls = data.get("labels") or data.get("data") or []
            return [u for u in urls if isinstance(u, str)]
        return []

    def download(self, url):
        """Télécharge une étiquette servie sur une URL signée par Packlink."""
        if requests is None:
            raise PacklinkApiError("La bibliothèque Python « requests » est requise.")
        try:
            response = requests.get(url, timeout=self.timeout)
        except Exception as exc:  # noqa: BLE001
            raise PacklinkApiError("Téléchargement de l'étiquette impossible : %s" % exc)
        if response.status_code >= 400:
            raise PacklinkApiError("Étiquette indisponible.", status_code=response.status_code)
        content = response.content or b""
        if len(content) > MAX_LABEL_BYTES:
            raise PacklinkApiError("Étiquette anormalement volumineuse.")
        return content

    def get_tracking(self, reference):
        data = self._request("GET", "/shipments/%s/track" % reference)
        if isinstance(data, dict):
            data = data.get("events") or data.get("data") or []
        return [e for e in data if isinstance(e, dict)]

    def cancel_shipment(self, reference):
        return self._request("DELETE", "/shipments/%s" % reference)
