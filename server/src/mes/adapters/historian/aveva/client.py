"""
AVEVA Historian Adapter: Async HTTP client for the Data REST API v2.

Wraps httpx to provide OData-based queries against the AVEVA Historian
iHistory web service.  Supports Windows Negotiate (NTLM/Kerberos),
Bearer token, and Basic authentication.

API resources used:
  /v2/ProcessValues   — VTQ records (value + time + quality)
  /v2/AnalogSummary   — Time-weighted aggregates (avg, stddev, min, max, integral)
  /v2/StateSummary    — State duration analysis (total, count, avg per state)
  /v2/Tags            — Tag metadata (FQN, TagType, EngUnit, Description)
  /v2/TagSearch       — Search/autocomplete tag FQNs

Ref: https://docs.aveva.com/bundle/sp-historian/page/259532.html
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

from .config import AVEVAHistorianSettings

logger = logging.getLogger("mes.adapters.historian.aveva")

# OPC quality code → MES quality string
_OPC_QUALITY_MAP: dict[int, str] = {
    192: "good",
    0: "bad",
    64: "uncertain",
}


def _opc_quality_to_str(opc_quality: int) -> str:
    """Map OPC quality code to canonical string."""
    if opc_quality >= 192:
        return "good"
    if opc_quality >= 64:
        return "uncertain"
    return "bad"


def _to_iso_utc(dt: datetime) -> str:
    """Format datetime as ISO 8601 UTC string with Z designator."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _encode_fqn(fqn: str) -> str:
    """URL-encode an FQN for use in OData $filter expressions."""
    return fqn.replace("'", "''")


class AVEVAHistorianClient:
    """
    Async HTTP client for the AVEVA Historian Data REST API v2.

    Lifecycle: create → connect() → query methods → disconnect()
    """

    def __init__(self, settings: AVEVAHistorianSettings | None = None) -> None:
        self._settings = settings or AVEVAHistorianSettings()
        self._http: Any = None  # httpx.AsyncClient

    @property
    def base_url(self) -> str:
        return self._settings.AVEVA_BASE_URL.rstrip("/")

    async def connect(self) -> None:
        """Create the httpx.AsyncClient with appropriate auth."""
        import httpx

        auth = self._build_auth()
        self._http = httpx.AsyncClient(
            base_url=self.base_url,
            auth=auth,
            verify=self._settings.AVEVA_VERIFY_SSL,
            timeout=httpx.Timeout(self._settings.AVEVA_TIMEOUT_SEC),
            headers=self._build_headers(),
        )
        logger.info(
            "AVEVA Historian client connected: %s (auth=%s)",
            self.base_url,
            self._settings.AVEVA_AUTH_MODE,
        )

    async def disconnect(self) -> None:
        """Close the HTTP client."""
        if self._http:
            await self._http.aclose()
            self._http = None
            logger.info("AVEVA Historian client disconnected")

    async def health_check(self) -> bool:
        """Verify connectivity by fetching one tag."""
        if not self._http:
            return False
        try:
            resp = await self._http.get("/Tags", params={"$top": "1"})
            return resp.status_code == 200
        except Exception:
            logger.debug("AVEVA Historian health check failed", exc_info=True)
            return False

    # ── Tag Metadata ──────────────────────────────────────────

    async def get_tags(
        self,
        source: str | None = None,
        tag_filter: str | None = None,
        top: int = 1000,
    ) -> list[dict[str, Any]]:
        """
        Retrieve tag metadata.

        Args:
            source: Filter by data source name.
            tag_filter: OData TagFilter expression (startswith, endswith, contains).
            top: Maximum number of results.

        Returns:
            List of tag metadata dicts: {FQN, Source, TagName, TagType, Description, EngUnit, ...}
        """
        params: dict[str, str] = {"$top": str(top)}
        if source:
            params["$filter"] = f"Source eq '{_encode_fqn(source)}'"
        if tag_filter:
            params["TagFilter"] = tag_filter
        return await self._get_odata("/Tags", params)

    async def search_tags(self, pattern: str, top: int = 100) -> list[dict[str, Any]]:
        """
        Search tags by FQN pattern using TagSearch.

        Args:
            pattern: Search term for tag FQN.
            top: Maximum results.
        """
        params: dict[str, str] = {"$top": str(top)}
        params["$filter"] = f"startswith(FQN,'{_encode_fqn(pattern)}')"
        return await self._get_odata("/Tags", params)

    # ── Process Values (VTQ) ──────────────────────────────────

    async def get_process_values(
        self,
        fqn: str,
        start: datetime | None = None,
        end: datetime | None = None,
        retrieval_mode: str | None = None,
        resolution: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve process value records (value + time + quality).

        Args:
            fqn: Fully qualified name (datasource.tagname).
            start: Start time (UTC). None → historian default (1h before end).
            end: End time (UTC). None → now.
            retrieval_mode: Average|Cyclic|Full|Interpolated|BestFit|Delta|
                           Minimum|Maximum|Counter|Integral|Slope
            resolution: Resolution in milliseconds.

        Returns:
            List of VTQ dicts: {FQN, DateTime, OpcQuality, Value, Text, Unit}

        Ref: https://docs.aveva.com/bundle/sp-historian/page/259561.html
        """
        filter_parts = [f"FQN eq '{_encode_fqn(fqn)}'"]
        if start:
            filter_parts.append(f"DateTime ge {_to_iso_utc(start)}")
        if end:
            filter_parts.append(f"DateTime le {_to_iso_utc(end)}")

        params: dict[str, str] = {"$filter": " and ".join(filter_parts)}
        if retrieval_mode:
            params["RetrievalMode"] = retrieval_mode
        if resolution:
            params["Resolution"] = str(resolution)

        return await self._get_odata("/ProcessValues", params)

    async def get_current_value(self, fqn: str) -> dict[str, Any] | None:
        """
        Get the current (latest) value for a tag.

        Calls ProcessValues with no time range → returns current value.

        Returns:
            Single VTQ dict or None if tag not found.
        """
        results = await self.get_process_values(fqn)
        return results[0] if results else None

    async def get_process_values_by_filter(
        self,
        tag_filter: str,
        start: datetime | None = None,
        end: datetime | None = None,
        retrieval_mode: str | None = None,
        resolution: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Query process values for multiple tags using TagFilter.

        Args:
            tag_filter: OData expression, e.g. "startswith(FQN,'Baytown.Line1.')"
            start: Start time.
            end: End time.

        Ref: https://docs.aveva.com/bundle/sp-historian/page/259561.html (Scenario 4-7)
        """
        filter_parts: list[str] = []
        if start:
            filter_parts.append(f"DateTime ge {_to_iso_utc(start)}")
        if end:
            filter_parts.append(f"DateTime le {_to_iso_utc(end)}")

        params: dict[str, str] = {"TagFilter": tag_filter}
        if filter_parts:
            params["$filter"] = " and ".join(filter_parts)
        if retrieval_mode:
            params["RetrievalMode"] = retrieval_mode
        if resolution:
            params["Resolution"] = str(resolution)

        return await self._get_odata("/ProcessValues", params)

    # ── Analog Summary ────────────────────────────────────────

    async def get_analog_summary(
        self,
        fqn: str,
        start: datetime | None = None,
        end: datetime | None = None,
        resolution: int | None = None,
        retrieval_mode: str = "Cyclic",
        slice_by: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve analog summary (time-weighted aggregates) for a tag.

        Returns fields: Average, StdDev, Minimum, Maximum, First, Last,
        Integral, PercentGood, Count, StartDateTime, EndDateTime.

        Args:
            fqn: Fully qualified name.
            start: Start time.
            end: End time.
            resolution: Resolution in milliseconds (e.g. 3600000 = 1 hour).
            retrieval_mode: Cyclic (default) or Full.
            slice_by: FQN of a tag to slice/batch results by value.

        Ref: https://docs.aveva.com/bundle/sp-historian/page/275756.html
        """
        filter_parts = [f"FQN eq '{_encode_fqn(fqn)}'"]
        if start:
            filter_parts.append(f"StartDateTime ge {_to_iso_utc(start)}")
        if end:
            filter_parts.append(f"EndDateTime le {_to_iso_utc(end)}")

        params: dict[str, str] = {
            "$filter": " and ".join(filter_parts),
            "RetrievalMode": retrieval_mode,
        }
        if resolution:
            params["Resolution"] = str(resolution)
        if slice_by:
            params["SliceBy"] = slice_by

        return await self._get_odata("/AnalogSummary", params)

    # ── State Summary ─────────────────────────────────────────

    async def get_state_summary(
        self,
        fqn: str,
        start: datetime | None = None,
        end: datetime | None = None,
        resolution: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve state summary (time-in-state durations) for a discrete tag.

        Returns fields per state: Text (state name), Count, Total,
        Average, Minimum, Maximum, PercentGood, StartDateTime, EndDateTime.

        Particularly useful for OEE Availability calculation.

        Ref: https://docs.aveva.com/bundle/sp-historian/page/275757.html
        """
        filter_parts = [f"FQN eq '{_encode_fqn(fqn)}'"]
        if start:
            filter_parts.append(f"StartDateTime ge {_to_iso_utc(start)}")
        if end:
            filter_parts.append(f"EndDateTime le {_to_iso_utc(end)}")

        params: dict[str, str] = {"$filter": " and ".join(filter_parts)}
        if resolution:
            params["Resolution"] = str(resolution)

        return await self._get_odata("/StateSummary", params)

    # ── Events ────────────────────────────────────────────────

    async def get_events(
        self,
        fqn: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        top: int = 1000,
    ) -> list[dict[str, Any]]:
        """
        Retrieve event records.

        Ref: https://docs.aveva.com/bundle/sp-historian/page/72365.html
        """
        filter_parts: list[str] = []
        if fqn:
            filter_parts.append(f"FQN eq '{_encode_fqn(fqn)}'")
        if start:
            filter_parts.append(f"DateTime ge {_to_iso_utc(start)}")
        if end:
            filter_parts.append(f"DateTime le {_to_iso_utc(end)}")

        params: dict[str, str] = {"$top": str(top)}
        if filter_parts:
            params["$filter"] = " and ".join(filter_parts)

        return await self._get_odata("/Events", params)

    # ── Internal helpers ──────────────────────────────────────

    def _build_auth(self) -> Any:
        """Build httpx auth object based on configured auth_mode."""
        mode = self._settings.AVEVA_AUTH_MODE.lower()

        if mode == "negotiate":
            try:
                from httpx_ntlm import HttpNtlmAuth

                return HttpNtlmAuth(
                    self._settings.AVEVA_USERNAME,
                    self._settings.AVEVA_PASSWORD,
                )
            except ImportError:
                logger.warning(
                    "httpx-ntlm not installed; falling back to basic auth. "
                    "Install with: pip install httpx-ntlm"
                )
                import httpx

                return httpx.BasicAuth(
                    self._settings.AVEVA_USERNAME,
                    self._settings.AVEVA_PASSWORD,
                )

        if mode == "basic":
            import httpx

            return httpx.BasicAuth(
                self._settings.AVEVA_USERNAME,
                self._settings.AVEVA_PASSWORD,
            )

        # bearer — auth header set in _build_headers()
        return None

    def _build_headers(self) -> dict[str, str]:
        """Build HTTP headers including auth token if bearer mode."""
        headers: dict[str, str] = {
            "Accept": "application/json",
        }
        if self._settings.AVEVA_AUTH_MODE.lower() == "bearer":
            token = self._settings.AVEVA_BEARER_TOKEN
            if token:
                headers["Authorization"] = f"Bearer {token}"
        return headers

    async def _get_odata(
        self, resource: str, params: dict[str, str],
    ) -> list[dict[str, Any]]:
        """
        Execute a GET request against an OData resource and return the value array.

        AVEVA Historian REST API returns OData-style responses:
        {"@odata.context": "...", "value": [...]}
        """
        if not self._http:
            msg = "Client not connected — call connect() first"
            raise RuntimeError(msg)

        resp = await self._http.get(resource, params=params)
        resp.raise_for_status()
        data = resp.json()

        # OData response wraps results in "value" array
        if isinstance(data, dict):
            return data.get("value", [])
        if isinstance(data, list):
            return data
        return []
