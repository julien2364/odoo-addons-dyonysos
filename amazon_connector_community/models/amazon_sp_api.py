# -*- coding: utf-8 -*-
"""Couche d'accès à l'API Amazon Selling Partner (SP-API).

Tous les appels réseau du module passent par :meth:`AmazonSpApi._request`.
Aucun autre endroit du code ne doit ouvrir de connexion HTTP : c'est ce point
unique qui gère le jeton LWA, les en-têtes, la limitation de débit et les
erreurs.
"""
import json
import logging
import time

from odoo import _

_logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:  # pragma: no cover - dépendance déclarée au manifeste
    requests = None

LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"

REGION_ENDPOINTS = {
    "eu": "https://sellingpartnerapi-eu.amazon.com",
    "na": "https://sellingpartnerapi-na.amazon.com",
    "fe": "https://sellingpartnerapi-fe.amazon.com",
}

MAX_ATTEMPTS = 3
BACKOFF_SECONDS = 1.0
DEFAULT_TIMEOUT = 30


class AmazonApiError(Exception):
    """Erreur lisible remontée par la couche SP-API."""

    def __init__(self, message, status_code=None, payload=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload

    def __str__(self):
        if self.status_code:
            return "[HTTP %s] %s" % (self.status_code, self.message)
        return self.message


class AmazonSpApi:
    """Client SP-API minimal, instancié depuis un ``amazon.account.community``."""

    def __init__(self, refresh_token, client_id, client_secret, seller_id,
                 region="eu", endpoint=None, timeout=DEFAULT_TIMEOUT):
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.seller_id = seller_id
        self.region = region or "eu"
        self.endpoint = endpoint or REGION_ENDPOINTS.get(self.region, REGION_ENDPOINTS["eu"])
        self.timeout = timeout
        # cache mémoire du jeton d'accès : (valeur, timestamp d'expiration)
        self._access_token = None
        self._access_token_expiry = 0.0

    # ------------------------------------------------------------------
    # Authentification LWA
    # ------------------------------------------------------------------
    @classmethod
    def from_account(cls, account):
        return cls(
            refresh_token=account.lwa_refresh_token,
            client_id=account.lwa_client_id,
            client_secret=account.lwa_client_secret,
            seller_id=account.seller_id,
            region=account.region,
            endpoint=account.endpoint_url,
        )

    def _get_access_token(self):
        """Retourne un access token LWA valide (cache mémoire)."""
        now = time.time()
        if self._access_token and now < self._access_token_expiry:
            return self._access_token
        if requests is None:
            raise AmazonApiError(_("La bibliothèque Python « requests » n'est pas installée."))
        try:
            response = requests.post(
                LWA_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=self.timeout,
            )
        except Exception as exc:  # pragma: no cover - dépend du réseau
            raise AmazonApiError(
                _("Impossible de contacter le service d'authentification Amazon : %s", exc)
            ) from exc
        if response.status_code != 200:
            # On ne journalise jamais le corps de la requête (il contient les secrets).
            raise AmazonApiError(
                _("Authentification Amazon refusée. Vérifiez le refresh token et "
                  "les identifiants de l'application LWA."),
                status_code=response.status_code,
            )
        data = response.json()
        self._access_token = data.get("access_token")
        self._access_token_expiry = now + float(data.get("expires_in", 3600)) - 60
        if not self._access_token:
            raise AmazonApiError(_("Amazon n'a pas retourné de jeton d'accès."))
        return self._access_token

    def invalidate_token(self):
        self._access_token = None
        self._access_token_expiry = 0.0

    # ------------------------------------------------------------------
    # Appel bas niveau — SEUL point réseau du module
    # ------------------------------------------------------------------
    def _request(self, method, path, params=None, body=None):
        """Exécute un appel SP-API et retourne le JSON décodé.

        Gère le jeton LWA, la limitation de débit (HTTP 429, 3 tentatives avec
        backoff) et lève :class:`AmazonApiError` avec un message lisible.
        """
        if requests is None:
            raise AmazonApiError(_("La bibliothèque Python « requests » n'est pas installée."))
        url = "%s%s" % (self.endpoint.rstrip("/"), path)
        last_error = None
        for attempt in range(MAX_ATTEMPTS):
            headers = {
                "x-amz-access-token": self._get_access_token(),
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "OdooAmazonConnectorCommunity/19.0 (Language=Python)",
            }
            try:
                response = requests.request(
                    method,
                    url,
                    params=params or None,
                    data=json.dumps(body) if body is not None else None,
                    headers=headers,
                    timeout=self.timeout,
                )
            except Exception as exc:  # pragma: no cover - dépend du réseau
                raise AmazonApiError(
                    _("Erreur réseau lors de l'appel à %(path)s : %(error)s",
                      path=path, error=exc)
                ) from exc

            status = response.status_code
            if status == 429:
                last_error = AmazonApiError(
                    _("Quota d'appels Amazon dépassé pour %s.", path), status_code=429
                )
                if attempt < MAX_ATTEMPTS - 1:
                    time.sleep(BACKOFF_SECONDS * (2 ** attempt))
                    continue
                raise last_error
            if status in (401, 403):
                self.invalidate_token()
                raise AmazonApiError(
                    _("Accès refusé par Amazon sur %s. Vérifiez les rôles accordés à "
                      "l'application et le vendeur sélectionné.", path),
                    status_code=status,
                )
            if status >= 400:
                raise AmazonApiError(
                    self._error_message(response), status_code=status
                )
            if not response.content:
                return {}
            try:
                return response.json()
            except ValueError as exc:
                raise AmazonApiError(
                    _("Réponse Amazon illisible pour %s.", path), status_code=status
                ) from exc
        raise last_error or AmazonApiError(_("Appel Amazon échoué pour %s.", path))

    @staticmethod
    def _error_message(response):
        try:
            payload = response.json()
        except ValueError:
            return _("Amazon a retourné une erreur HTTP %s.", response.status_code)
        errors = payload.get("errors") or []
        if errors:
            return " / ".join(
                filter(None, [e.get("message") or e.get("code") for e in errors])
            ) or _("Amazon a retourné une erreur HTTP %s.", response.status_code)
        return _("Amazon a retourné une erreur HTTP %s.", response.status_code)

    # ------------------------------------------------------------------
    # Méthodes métier
    # ------------------------------------------------------------------
    def test_connection(self):
        """Vérifie les identifiants en listant les places de marché du vendeur."""
        return self._request("GET", "/sellers/v1/marketplaceParticipations")

    def get_orders(self, since, marketplace_ids, next_token=None):
        """Liste les commandes créées ou modifiées depuis ``since``."""
        params = {"MarketplaceIds": ",".join(marketplace_ids)}
        if next_token:
            params["NextToken"] = next_token
        else:
            params["LastUpdatedAfter"] = self._format_date(since)
        return self._request("GET", "/orders/v0/orders", params=params)

    def get_order_items(self, order_id):
        return self._request("GET", "/orders/v0/orders/%s/orderItems" % order_id)

    def confirm_shipment(self, order_id, payload):
        return self._request(
            "POST",
            "/orders/v0/orders/%s/shipmentConfirmation" % order_id,
            body=payload,
        )

    def patch_listing_quantity(self, sku, quantity, marketplace_id):
        body = {
            "productType": "PRODUCT",
            "patches": [{
                "op": "replace",
                "path": "/attributes/fulfillment_availability",
                "value": [{
                    "fulfillment_channel_code": "DEFAULT",
                    "quantity": int(quantity),
                }],
            }],
        }
        return self._patch_listing(sku, marketplace_id, body)

    def patch_listing_price(self, sku, price, currency, marketplace_id):
        body = {
            "productType": "PRODUCT",
            "patches": [{
                "op": "replace",
                "path": "/attributes/purchasable_offer",
                "value": [{
                    "marketplace_id": marketplace_id,
                    "currency": currency,
                    "our_price": [{
                        "schedule": [{"value_with_tax": float(price)}],
                    }],
                }],
            }],
        }
        return self._patch_listing(sku, marketplace_id, body)

    def _patch_listing(self, sku, marketplace_id, body):
        path = "/listings/2021-08-01/items/%s/%s" % (self.seller_id, sku)
        return self._request(
            "PATCH", path,
            params={"marketplaceIds": marketplace_id},
            body=body,
        )

    @staticmethod
    def _format_date(value):
        if hasattr(value, "strftime"):
            return value.strftime("%Y-%m-%dT%H:%M:%SZ")
        return value
