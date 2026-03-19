"""
Oracle Cloud ERP: HTTP client for Fusion REST APIs.

Handles OAuth2 token management, request/response handling,
offset/limit pagination, and error mapping.

Oracle Cloud ERP uses standard REST (no CSRF tokens required).
Base URL format: https://<pod>.fa.us2.oraclecloud.com
"""

from __future__ import annotations

import base64
import logging
import time
from typing import Any
from urllib.parse import urlencode

import httpx

from mes.adapters.erp.exceptions import ERPConnectionError, ERPOutboundError, ERPSyncError
from mes.config import settings

from .config import oracle_settings

logger = logging.getLogger("mes.adapters.erp.oracle.client")


class OracleClient:
    """
    HTTP client for Oracle Cloud ERP (Fusion) REST APIs.

    Supports three auth modes (configured via MES_ERP_AUTH_TYPE):
      - oauth2: Client credentials flow via Oracle IDCS/OCI IAM (production)
      - basic: HTTP Basic auth (development/testing)
      - api_key: API key header (sandbox/integration testing)

    Token lifecycle is managed internally: tokens are cached and
    refreshed 60 seconds before expiry.
    """

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._access_token: str | None = None
        self._token_expiry: float = 0.0

    async def connect(self) -> None:
        """Create the HTTP client and acquire initial auth token."""
        if not settings.ERP_BASE_URL:
            raise ERPConnectionError(message="MES_ERP_BASE_URL is not configured")

        self._client = httpx.AsyncClient(
            base_url=settings.ERP_BASE_URL.rstrip("/"),
            timeout=httpx.Timeout(oracle_settings.ORACLE_REQUEST_TIMEOUT_SEC),
            verify=True,
        )

        if settings.ERP_AUTH_TYPE == "oauth2":
            await self._acquire_oauth2_token()
        elif settings.ERP_AUTH_TYPE == "basic":
            # Basic auth is set per-request via headers
            pass

        logger.info("Oracle Cloud ERP client connected to %s", settings.ERP_BASE_URL)

    async def disconnect(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._access_token = None
        self._token_expiry = 0.0
        logger.info("Oracle Cloud ERP client disconnected")

    async def health_check(self) -> bool:
        """Check connectivity by hitting the base REST API path."""
        if not self._client:
            return False
        try:
            resp = await self._client.get(
                "/fscmRestApi/resources",
                headers=self._build_headers(),
            )
            return resp.status_code < 500
        except httpx.HTTPError:
            return False

    # ── REST query methods ──────────────────────────────────────

    async def get_list(
        self,
        path: str,
        *,
        params: dict[str, str] | None = None,
        q_filter: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Execute a REST GET for a collection.

        Handles pagination via offset/limit (Oracle REST uses ?offset=&limit=).
        Returns flattened list of all entity dicts.
        """
        if limit is None:
            limit = oracle_settings.ORACLE_PAGE_SIZE

        results: list[dict[str, Any]] = []
        current_offset = offset

        while True:
            query: dict[str, str] = {
                "limit": str(limit),
                "offset": str(current_offset),
            }
            if q_filter:
                query["q"] = q_filter
            if params:
                query.update(params)

            url = f"{path}?{urlencode(query)}"
            data = await self._request("GET", url)

            items = data.get("items", [])
            results.extend(items)

            # Oracle signals more data with hasMore or count
            has_more = data.get("hasMore", False)
            if has_more and len(items) > 0:
                current_offset += len(items)
            else:
                break

        return results

    async def get_entity(
        self,
        path: str,
        *,
        expand: str | None = None,
    ) -> dict[str, Any]:
        """Execute a REST GET for a single entity with optional expand."""
        query: dict[str, str] = {}
        if expand:
            query["expand"] = expand
        url = f"{path}?{urlencode(query)}" if query else path
        return await self._request("GET", url)

    async def post(
        self,
        path: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a REST POST (create/action)."""
        return await self._request("POST", path, json_body=payload)

    # ── Internal request handling ────────────────────────────────

    async def _request(
        self,
        method: str,
        url: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute an HTTP request with auth and error handling."""
        if not self._client:
            raise ERPConnectionError(message="Oracle client is not connected")

        # Refresh OAuth2 token if near expiry
        if settings.ERP_AUTH_TYPE == "oauth2" and time.monotonic() >= self._token_expiry - 60:
            await self._acquire_oauth2_token()

        headers = self._build_headers()

        try:
            resp = await self._client.request(
                method,
                url,
                headers=headers,
                json=json_body,
            )
        except httpx.HTTPError as exc:
            raise ERPConnectionError(
                message=f"Oracle HTTP request failed: {exc}",
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
            credentials = base64.b64encode(
                f"{settings.ERP_CLIENT_ID}:{settings.ERP_CLIENT_SECRET}".encode(),
            ).decode()
            headers["Authorization"] = f"Basic {credentials}"
        elif settings.ERP_AUTH_TYPE == "api_key":
            headers["X-Api-Key"] = settings.ERP_CLIENT_SECRET

        return headers

    async def _acquire_oauth2_token(self) -> None:
        """Acquire an OAuth2 token using client credentials flow (Oracle IDCS/OCI IAM)."""
        token_url = oracle_settings.ORACLE_TOKEN_URL or settings.ERP_TOKEN_URL
        if not token_url:
            raise ERPConnectionError(
                message="OAuth2 token URL not configured (MES_ORACLE_TOKEN_URL or MES_ERP_TOKEN_URL)",
            )

        token_data_body: dict[str, str] = {
            "grant_type": "client_credentials",
            "client_id": settings.ERP_CLIENT_ID,
            "client_secret": settings.ERP_CLIENT_SECRET,
        }
        if oracle_settings.ORACLE_TOKEN_SCOPE:
            token_data_body["scope"] = oracle_settings.ORACLE_TOKEN_SCOPE

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(15)) as token_client:
                resp = await token_client.post(
                    token_url,
                    data=token_data_body,
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

    def _handle_error(self, resp: httpx.Response) -> None:
        """Map Oracle HTTP error responses to MES exceptions."""
        try:
            body = resp.json()
            # Oracle REST errors: {"type":"...", "title":"...", "detail":"...", "o:errorCode":"..."}
            error_msg = (
                body.get("detail", "")
                or body.get("title", "")
                or body.get("message", "")
                or str(body)
            )
        except Exception:
            error_msg = resp.text[:500] if resp.text else f"HTTP {resp.status_code}"

        if resp.status_code in (401, 403):
            raise ERPConnectionError(
                message=f"Oracle authentication/authorization failed: {error_msg}",
            )
        if resp.status_code < 500:
            raise ERPSyncError(
                message=f"Oracle request error ({resp.status_code}): {error_msg}",
            )
        raise ERPOutboundError(
            message=f"Oracle server error ({resp.status_code}): {error_msg}",
        )
