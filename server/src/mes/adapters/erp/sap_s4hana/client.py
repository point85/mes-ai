"""
SAP S/4HANA: HTTP client for OData V4 APIs.

Handles OAuth2 token management, request/response handling, CSRF token
negotiation, OData pagination, and error mapping.

This client is used by the SAP adapter implementations to communicate
with S/4HANA APIs.
"""

from __future__ import annotations

import logging
import time
from typing import Any
from urllib.parse import urlencode

import httpx

from mes.adapters.erp.exceptions import ERPConnectionError, ERPOutboundError, ERPSyncError
from mes.config import settings

from .config import sap_settings

logger = logging.getLogger("mes.adapters.erp.sap_s4hana.client")


class SAPS4HANAClient:
    """
    HTTP client for SAP S/4HANA OData V4 APIs.

    Supports three auth modes (configured via MES_ERP_AUTH_TYPE):
      - oauth2: Client credentials flow (production)
      - basic: HTTP Basic auth (development/testing)
      - api_key: API key header (SAP API Business Hub sandbox)

    Token lifecycle is managed internally: tokens are cached and
    refreshed 60 seconds before expiry.
    """

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._access_token: str | None = None
        self._token_expiry: float = 0.0
        self._csrf_token: str | None = None

    async def connect(self) -> None:
        """Create the HTTP client and acquire initial auth token."""
        if not settings.ERP_BASE_URL:
            raise ERPConnectionError(message="MES_ERP_BASE_URL is not configured")

        self._client = httpx.AsyncClient(
            base_url=settings.ERP_BASE_URL.rstrip("/"),
            timeout=httpx.Timeout(sap_settings.SAP_REQUEST_TIMEOUT_SEC),
            verify=True,
        )

        if settings.ERP_AUTH_TYPE == "oauth2":
            await self._acquire_oauth2_token()
        elif settings.ERP_AUTH_TYPE == "basic":
            # Basic auth is set per-request via headers
            pass

        logger.info("SAP S/4HANA client connected to %s", settings.ERP_BASE_URL)

    async def disconnect(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._access_token = None
        self._token_expiry = 0.0
        self._csrf_token = None
        logger.info("SAP S/4HANA client disconnected")

    async def health_check(self) -> bool:
        """Check connectivity by hitting the base URL metadata endpoint."""
        if not self._client:
            return False
        try:
            resp = await self._client.get(
                "/$metadata",
                headers=self._build_headers(),
            )
            return resp.status_code < 500
        except httpx.HTTPError:
            return False

    # ── OData query methods ──────────────────────────────────────

    async def get_list(
        self,
        path: str,
        *,
        params: dict[str, str] | None = None,
        filter_expr: str | None = None,
        top: int | None = None,
        skip: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Execute an OData GET for a collection.

        Handles server-driven paging via @odata.nextLink.
        Returns flattened list of all entity dicts.
        """
        query: dict[str, str] = {}
        if filter_expr:
            query["$filter"] = filter_expr
        if top is None:
            top = sap_settings.SAP_PAGE_SIZE
        query["$top"] = str(top)
        if skip:
            query["$skip"] = str(skip)
        if params:
            query.update(params)

        results: list[dict[str, Any]] = []
        url = f"{path}?{urlencode(query)}" if query else path

        while url:
            data = await self._request("GET", url)
            values = data.get("value", [])
            results.extend(values)

            # Server-driven paging
            next_link = data.get("@odata.nextLink")
            if next_link and len(values) > 0:
                url = next_link
            else:
                url = ""

        return results

    async def get_entity(
        self,
        path: str,
        *,
        expand: str | None = None,
    ) -> dict[str, Any]:
        """Execute an OData GET for a single entity with optional $expand."""
        query: dict[str, str] = {}
        if expand:
            query["$expand"] = expand
        url = f"{path}?{urlencode(query)}" if query else path
        return await self._request("GET", url)

    async def post(
        self,
        path: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute an OData POST (create/action)."""
        return await self._request("POST", path, json_body=payload)

    # ── Internal request handling ────────────────────────────────

    async def _request(
        self,
        method: str,
        url: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute an HTTP request with auth, CSRF, and error handling."""
        if not self._client:
            raise ERPConnectionError(message="SAP client is not connected")

        # Refresh OAuth2 token if near expiry
        if settings.ERP_AUTH_TYPE == "oauth2" and time.monotonic() >= self._token_expiry - 60:
            await self._acquire_oauth2_token()

        headers = self._build_headers()

        # For write operations, fetch CSRF token first
        if method in ("POST", "PUT", "PATCH", "DELETE") and not self._csrf_token:
            await self._fetch_csrf_token()
        if self._csrf_token:
            headers["X-CSRF-Token"] = self._csrf_token

        try:
            resp = await self._client.request(
                method,
                url,
                headers=headers,
                json=json_body,
            )
        except httpx.HTTPError as exc:
            raise ERPConnectionError(
                message=f"SAP HTTP request failed: {exc}",
            ) from exc

        if resp.status_code >= 400:
            self._handle_error(resp)

        if resp.status_code == 204:  # No Content
            return {}
        return resp.json()

    def _build_headers(self) -> dict[str, str]:
        """Build request headers based on auth mode."""
        headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        if settings.ERP_AUTH_TYPE == "oauth2" and self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        elif settings.ERP_AUTH_TYPE == "basic":
            import base64
            credentials = base64.b64encode(
                f"{settings.ERP_CLIENT_ID}:{settings.ERP_CLIENT_SECRET}".encode(),
            ).decode()
            headers["Authorization"] = f"Basic {credentials}"
        elif settings.ERP_AUTH_TYPE == "api_key":
            headers[sap_settings.SAP_API_KEY_HEADER] = settings.ERP_CLIENT_SECRET

        return headers

    async def _acquire_oauth2_token(self) -> None:
        """Acquire an OAuth2 token using client credentials flow."""
        token_url = sap_settings.SAP_TOKEN_URL or settings.ERP_TOKEN_URL
        if not token_url:
            raise ERPConnectionError(
                message="OAuth2 token URL not configured (MES_SAP_TOKEN_URL or MES_ERP_TOKEN_URL)",
            )

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(15)) as token_client:
                resp = await token_client.post(
                    token_url,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": settings.ERP_CLIENT_ID,
                        "client_secret": settings.ERP_CLIENT_SECRET,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
        except httpx.HTTPError as exc:
            raise ERPConnectionError(
                message=f"Failed to acquire OAuth2 token: {exc}",
            ) from exc

        if resp.status_code != 200:
            raise ERPConnectionError(
                message=f"OAuth2 token request failed with status {resp.status_code}",
            )

        token_data = resp.json()
        self._access_token = token_data["access_token"]
        expires_in = int(token_data.get("expires_in", 3600))
        self._token_expiry = time.monotonic() + expires_in
        logger.debug("OAuth2 token acquired, expires in %d seconds", expires_in)

    async def _fetch_csrf_token(self) -> None:
        """Fetch a CSRF token from SAP (required for write operations)."""
        try:
            resp = await self._client.head(  # type: ignore[union-attr]
                "/",
                headers={
                    **self._build_headers(),
                    "X-CSRF-Token": "Fetch",
                },
            )
            self._csrf_token = resp.headers.get("x-csrf-token")
        except httpx.HTTPError:
            logger.warning("Failed to fetch CSRF token; write operations may fail")

    def _handle_error(self, resp: httpx.Response) -> None:
        """Map SAP HTTP error responses to MES exceptions."""
        try:
            body = resp.json()
            error_msg = (
                body.get("error", {}).get("message", {}).get("value", "")
                or body.get("error", {}).get("message", "")
                or str(body)
            )
        except Exception:
            error_msg = resp.text[:500] if resp.text else f"HTTP {resp.status_code}"

        if resp.status_code in (401, 403):
            raise ERPConnectionError(
                message=f"SAP authentication/authorization failed: {error_msg}",
            )
        if resp.status_code < 500:
            raise ERPSyncError(
                message=f"SAP request error ({resp.status_code}): {error_msg}",
            )
        raise ERPOutboundError(
            message=f"SAP server error ({resp.status_code}): {error_msg}",
        )
